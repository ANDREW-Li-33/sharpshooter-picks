import sys
from pathlib import Path
import pandas as pd
import time
from datetime import datetime, timedelta
import logging
import random
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import argparse
import json
import os
from typing import List, Dict, Optional, Union, Tuple, Set
from tqdm import tqdm
import backoff
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text

# Add the backend directory to the path so we can import from models
backend_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(backend_dir))

from nba_api.stats.static import players
from nba_api.stats.endpoints import leaguegamefinder
from sqlalchemy.orm import Session
from db_models.db_schema import PlayerStats, Player
from db_config import engine

# Configure logging
log_dir = Path(__file__).parent / 'logs'
log_dir.mkdir(exist_ok=True)
log_file = log_dir / f'nba_stats_ingestion_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("NBADataIngestion")

# Create a function decorator to handle retries with exponential backoff
def with_retry(max_attempts=5, initial_wait=2.0, backoff_factor=2.0):
    """Decorator for functions that should be retried with exponential backoff."""
    def decorator(func):
        @backoff.on_exception(
            backoff.expo,
            (requests.exceptions.RequestException, 
             ConnectionError, 
             TimeoutError),
            max_tries=max_attempts,
            factor=backoff_factor,
            base=initial_wait,
            jitter=backoff.full_jitter,
            on_backoff=lambda details: logger.warning(
                f"Retrying {func.__name__} in {details['wait']:.2f}s after {details['tries']} attempts due to {details['exception']}"
            )
        )
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper
    return decorator

class NBADataIngestion:
    def __init__(self, config=None):
        """
        Initialize the NBA data ingestion module with configurable parameters.
        
        Args:
            config (dict, optional): Configuration parameters for customization
        """
        # Default configuration
        self.default_config = {
            "seasons_to_fetch": 5,  # Number of past seasons to fetch
            "request_delay_min": 1.0,  # Minimum delay between requests in seconds
            "request_delay_max": 3.0,  # Maximum delay between requests in seconds
            "batch_size": 10,  # Number of players to process in a batch before committing
            "data_cache_dir": str(Path(__file__).parent / "cache"),  # Directory to cache API responses
            "user_agents": [  # Rotating user agents to avoid API blocks
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
                'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36'
            ],
            "enable_caching": True,  # Enable data caching to reduce API calls
            "verify_data": True,  # Perform data validation after ingestion
            "clean_duplicates": True,  # Remove duplicate entries after ingestion
            "retry_queue_persistence": True,  # Enable saving/loading the retry queue
            "max_retries": 5,  # Maximum number of retries for failed requests
            "base_wait_time": 300  # Base wait time between retries (seconds)
        }
        
        # Initialize retry queue
        self.retry_queue = []

        # Update with provided config
        self.config = self.default_config.copy()
        if config:
            self.config.update(config)
        
        # Create cache directory if enabled
        if self.config["enable_caching"]:
            os.makedirs(self.config["data_cache_dir"], exist_ok=True)
        
        # Set up current season and past seasons to fetch
        self.current_season = datetime.now().year
        self.seasons = [
            f"{year}-{str(year + 1)[-2:]}" 
            for year in range(self.current_season - self.config["seasons_to_fetch"], self.current_season)
        ]
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=5,
            backoff_factor=2,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"]
        )

        # Set up session with retry adapter
        self.http_adapter = HTTPAdapter(max_retries=retry_strategy)
        self.http_session = requests.Session()
        self.http_session.mount("https://", self.http_adapter)
        
        # Set initial user agent
        self.rotate_user_agent()
        
        # Track processed players and games to avoid duplicates
        self.processed_player_ids = set()
        self.processed_game_ids = set()
        
        # Session factory for database connections
        self.db_session = None
        
        # Stats for monitoring
        self.stats = {
            "players_processed": 0,
            "games_processed": 0,
            "api_requests": 0,
            "cache_hits": 0,
            "db_inserts": 0,
            "db_updates": 0,
            "errors": 0,
            "rate_limit_hits": 0,
            "start_time": None,
            "end_time": None,
            "last_update_time": None,
            "last_timer_check": None,
            "timer_interval": 60  # How often to update timer (in seconds)
        }
        
        # Load retry queue if persistence is enabled
        if self.config["retry_queue_persistence"]:
            self.load_retry_queue()
        
        logger.info(f"Initialized NBA Data Ingestion with seasons: {', '.join(self.seasons)}")
        logger.info(f"Configuration: {json.dumps({k: v for k, v in self.config.items() if k != 'user_agents'}, indent=2)}")
    
    def rotate_user_agent(self):
        """Rotate the user agent to avoid API blocks."""
        user_agent = random.choice(self.config["user_agents"])
        # Add specific headers that NBA.com expects
        self.http_session.headers.update({
            'User-Agent': user_agent,
            'Referer': 'https://stats.nba.com/',
            'Origin': 'https://stats.nba.com',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'x-nba-stats-origin': 'stats',
            'x-nba-stats-token': 'true'
        })
        return user_agent
    
    def get_cache_path(self, cache_type: str, identifier: str, season: Optional[str] = None) -> Path:
        """
        Get the path for a cached file.
        
        Args:
            cache_type: Type of cache ('players', 'games')
            identifier: Identifier (player_id, etc.)
            season: Season string if applicable
            
        Returns:
            Path to the cache file
        """
        if season:
            return Path(self.config["data_cache_dir"]) / f"{cache_type}_{identifier}_{season}.json"
        return Path(self.config["data_cache_dir"]) / f"{cache_type}_{identifier}.json"
    
    def save_to_cache(self, data: Union[List, Dict], cache_type: str, identifier: str, season: Optional[str] = None) -> bool:
        """
        Save data to cache file.
        
        Args:
            data: Data to cache
            cache_type: Type of cache ('players', 'games')
            identifier: Identifier (player_id, etc.)
            season: Season string if applicable
            
        Returns:
            Success status
        """
        if not self.config["enable_caching"]:
            return False
            
        try:
            cache_path = self.get_cache_path(cache_type, identifier, season)
            with open(cache_path, 'w') as f:
                json.dump(data, f)
            return True
        except Exception as e:
            logger.warning(f"Failed to cache {cache_type} data: {e}")
            return False
    
    def load_from_cache(self, cache_type: str, identifier: str, season: Optional[str] = None) -> Optional[Union[List, Dict]]:
        """
        Load data from cache if available.
        
        Args:
            cache_type: Type of cache ('players', 'games')
            identifier: Identifier (player_id, etc.)
            season: Season string if applicable
            
        Returns:
            Cached data or None if not available
        """
        if not self.config["enable_caching"]:
            return None
            
        cache_path = self.get_cache_path(cache_type, identifier, season)
        if not cache_path.exists():
            return None
            
        try:
            with open(cache_path, 'r') as f:
                data = json.load(f)
            self.stats["cache_hits"] += 1
            return data
        except Exception as e:
            logger.warning(f"Failed to load cached {cache_type} data: {e}")
            return None
    
    def save_retry_queue(self):
        """Save the retry queue to disk."""
        if not self.retry_queue or not self.config["retry_queue_persistence"]:
            return
        
        try:
            queue_path = Path(self.config["data_cache_dir"]) / "retry_queue.json"
            # Convert datetime objects to strings for JSON serialization
            serializable_queue = []
            for item in self.retry_queue:
                item_copy = item.copy()
                item_copy['last_attempt'] = item_copy['last_attempt'].isoformat()
                serializable_queue.append(item_copy)
                
            with open(queue_path, 'w') as f:
                json.dump(serializable_queue, f)
            logger.info(f"Saved {len(self.retry_queue)} items to retry queue")
        except Exception as e:
            logger.error(f"Failed to save retry queue: {e}")

    def load_retry_queue(self):
        """Load the retry queue from disk if available."""
        queue_path = Path(self.config["data_cache_dir"]) / "retry_queue.json"
        if not queue_path.exists():
            return
            
        try:
            with open(queue_path, 'r') as f:
                serialized_queue = json.load(f)
            
            # Convert string dates back to datetime objects
            for item in serialized_queue:
                item['last_attempt'] = datetime.fromisoformat(item['last_attempt'])
                
            self.retry_queue = serialized_queue
            logger.info(f"Loaded {len(self.retry_queue)} items from retry queue")
        except Exception as e:
            logger.error(f"Failed to load retry queue: {e}")
    
    @with_retry(max_attempts=5, initial_wait=2.0, backoff_factor=2.0)
    def get_active_players(self) -> List[Dict]:
        """
        Get a list of all active NBA players.
        
        Returns:
            List of player dictionaries
        """
        cached_players = self.load_from_cache("players", "active")
        if cached_players:
            logger.info(f"Loaded {len(cached_players)} active players from cache")
            return cached_players
            
        try:
            # Rotate user agent before making request
            user_agent = self.rotate_user_agent()
            logger.info(f"Fetching active players with user agent: {user_agent[:30]}...")
            
            # Add randomness for human-like behavior
            human_like_delay = random.uniform(1.5, 5.0)
            time.sleep(human_like_delay)
            
            self.stats["api_requests"] += 1
            active_players = players.get_active_players()
            
            if active_players:
                logger.info(f"Found {len(active_players)} active players")
                # Cache the results
                self.save_to_cache(active_players, "players", "active")
                return active_players
            else:
                logger.warning("API returned empty player list")
                return []
                
        except requests.exceptions.HTTPError as e:
            if hasattr(e, 'response') and e.response.status_code == 429:
                logger.warning("Rate limit exceeded when fetching active players")
                self.stats["rate_limit_hits"] += 1
            logger.error(f"HTTP error fetching active players: {e}")
            self.stats["errors"] += 1
            return []
        except Exception as e:
            logger.error(f"Error fetching active players: {e}")
            self.stats["errors"] += 1
            return []
    
    @with_retry(max_attempts=5, initial_wait=2.0, backoff_factor=2.0)
    def get_player_games(self, player_id: int, season: str) -> Optional[pd.DataFrame]:
        """
        Get games for a specific player and season.
        
        Args:
            player_id: NBA player ID
            season: Season string (e.g. '2022-23')
            
        Returns:
            DataFrame of player games, empty DataFrame if no games found,
            or None if an error occurred
        """
        # Try to load from cache first
        cached_games = self.load_from_cache("games", player_id, season)
        if cached_games:
            logger.debug(f"Loaded {len(cached_games)} games for player {player_id} in {season} from cache")
            return pd.DataFrame(cached_games)
        
        # Add randomness between season requests for the same player
        human_like_delay = random.uniform(1.5, 7.0)
        time.sleep(human_like_delay)
        
        # Implement exponential backoff with jitter
        delay = self.config["request_delay_min"] + random.uniform(0, self.config["request_delay_max"] - self.config["request_delay_min"])
        time.sleep(delay)
        
        try:
            # Rotate user agent
            user_agent = self.rotate_user_agent()
            logger.debug(f"Fetching games for player {player_id} in {season} with user agent: {user_agent[:30]}...")
            
            self.stats["api_requests"] += 1
            player_games_query = leaguegamefinder.LeagueGameFinder(
                player_or_team_abbreviation="P",
                player_id_nullable=player_id,
                season_nullable=season,
                season_type_nullable="Regular Season",
                timeout=180  # Extended timeout
            )
            
            games_df = player_games_query.get_data_frames()[0]
            
            if not games_df.empty:
                logger.info(f"Successfully retrieved {len(games_df)} games for player {player_id} in {season}")
                
                # Cache the results as a list of dictionaries
                games_data = games_df.to_dict('records')
                self.save_to_cache(games_data, "games", player_id, season)
                
                return games_df
            else:
                # This means we got a valid empty response (player didn't play that season)
                logger.info(f"No games found for player {player_id} in {season}")
                return pd.DataFrame()
                    
        except requests.exceptions.HTTPError as e:
            if hasattr(e, 'response') and e.response.status_code == 429:
                # Rate limit exceeded
                logger.warning(f"Rate limit exceeded for player {player_id} in {season}. Adding to retry queue with longer delay.")
                self.stats["rate_limit_hits"] += 1
                self.stats["errors"] += 1
                return None
            else:
                logger.error(f"HTTP error fetching games for player {player_id} in {season}: {e}")
                self.stats["errors"] += 1
                return None
        except requests.exceptions.Timeout as e:
            # Explicitly handle timeouts differently
            logger.error(f"Timeout error fetching games for player {player_id} in {season}: {e}")
            self.stats["errors"] += 1
            # Return None to indicate an error occurred (not an empty result)
            return None
        except Exception as e:
            logger.error(f"Error fetching games for player {player_id} in {season}: {e}")
            self.stats["errors"] += 1
            # Return None to indicate an error occurred
            return None

    def process_game_data(self, game_data: pd.Series, season: str) -> Dict:
        """
        Format raw game data into a Python Dictionary.
        
        Args:
            game_data: Series containing game statistics
            season: Season string
            
        Returns:
            Dictionary with formatted game data
        """
        try:
            processed_data = {
                'game_id': game_data['GAME_ID'],
                'player_id': game_data['PLAYER_ID'],
                'game_date': pd.to_datetime(game_data['GAME_DATE']),
                'season': season,
                'is_home_game': '@' not in game_data['MATCHUP'],
                'minutes_played': game_data['MIN'],
                'points': game_data['PTS'],
                'rebounds': game_data['REB'],
                'assists': game_data['AST'],
                'steals': game_data['STL'],
                'blocks': game_data['BLK'],
                'turnovers': game_data['TOV'],
                'plus_minus': game_data['PLUS_MINUS'],
                'fg_made': game_data['FGM'],
                'fg_attempted': game_data['FGA'],
                'fg3_made': game_data['FG3M'],
                'fg3_attempted': game_data['FG3A'],
                'ft_made': game_data['FTM'],
                'ft_attempted': game_data['FTA']
            }
            
            # Validate data
            for key, value in processed_data.items():
                if key != 'game_date' and isinstance(value, (int, float)) and pd.isna(value):
                    logger.warning(f"NaN value detected for {key} in game {game_data['GAME_ID']} for player {game_data['PLAYER_ID']}")
                    processed_data[key] = 0
            
            return processed_data
            
        except Exception as e:
            logger.error(f"Error processing game data: {e}")
            self.stats["errors"] += 1
            return None

    def get_or_create_db_session(self):
        """Get an existing db session or create a new one."""
        if self.db_session is None:
            self.db_session = Session(engine)
        return self.db_session
    
    def store_player_data(self, player: Dict) -> bool:
        """
        Store player data in database.
        
        Args:
            player: Player dictionary
            
        Returns:
            Success status
        """
        if player['id'] in self.processed_player_ids:
            logger.debug(f"Player {player['id']} ({player['full_name']}) already processed, skipping")
            return True
            
        session = self.get_or_create_db_session()
        try:
            existing_player = session.query(Player).filter_by(player_id=player['id']).first()
            
            if existing_player:
                # Update existing player
                existing_player.full_name = player['full_name']
                existing_player.is_active = True
                self.stats["db_updates"] += 1
                logger.debug(f"Updated player: {player['full_name']} (ID: {player['id']})")
            else:
                # Create new player
                player_record = Player(
                    player_id=player['id'],
                    full_name=player['full_name'],
                    is_active=True
                )
                session.add(player_record)
                self.stats["db_inserts"] += 1
                logger.debug(f"Added new player: {player['full_name']} (ID: {player['id']})")
            

            # Add to processed set
            self.processed_player_ids.add(player['id'])
            self.stats["players_processed"] += 1
            session.commit()
            
            return True
            
        except SQLAlchemyError as e:
            logger.error(f"Database error storing player {player['full_name']}: {e}")
            session.rollback()
            self.stats["errors"] += 1
            return False
        except Exception as e:
            logger.error(f"Error storing player data for {player['full_name']}: {e}")
            session.rollback()
            self.stats["errors"] += 1
            return False

    def store_game_stats(self, stats_data: Dict) -> bool:
        """
        Insert or update game stats in the database.
        
        Args:
            stats_data: Game statistics dictionary
            
        Returns:
            Success status
        """
        if not stats_data:
            return False
            
        # Check if this game has already been processed
        game_player_key = f"{stats_data['game_id']}_{stats_data['player_id']}"
        if game_player_key in self.processed_game_ids:
            logger.debug(f"Game {game_player_key} already processed, skipping")
            return True
            
        session = self.get_or_create_db_session()
        try:
            # Check if this game already exists
            existing_game = session.query(PlayerStats).filter_by(
                game_id=stats_data['game_id'],
                player_id=stats_data['player_id']
            ).first()
            
            if existing_game:
                # Update fields instead of using merge to avoid potential issues
                for key, value in stats_data.items():
                    if key != 'id':  # Skip primary key
                        setattr(existing_game, key, value)
                self.stats["db_updates"] += 1
            else:
                # Create new game stats record
                stats = PlayerStats(**stats_data)
                session.add(stats)
                self.stats["db_inserts"] += 1
            
            # Add to processed set
            self.processed_game_ids.add(game_player_key)
            self.stats["games_processed"] += 1

            session.commit()
            
            return True
            
        except SQLAlchemyError as e:
            logger.error(f"Database error storing game stats: {e}")
            session.rollback()
            self.stats["errors"] += 1
            return False
        except Exception as e:
            logger.error(f"Error storing game stats: {e}")
            session.rollback()
            self.stats["errors"] += 1
            return False
    
    def commit_batch(self):
        """Commit the current batch of database operations."""
        if self.db_session:
            try:
                self.db_session.commit()
                logger.debug("Committed batch of database operations")
            except SQLAlchemyError as e:
                logger.error(f"Error committing batch: {e}")
                self.db_session.rollback()
                self.stats["errors"] += 1

    def close_session(self):
        """Close the database session."""
        if self.db_session:
            self.db_session.close()
            self.db_session = None
            logger.debug("Closed database session")
    
    def process_player(self, player: Dict) -> Tuple[int, int]:
        """
        Process a single player's data for all seasons.
        
        Args:
            player: Player dictionary
            
        Returns:
            Tuple of (games processed, errors)
        """
        player_name = player['full_name']
        player_id = player['id']
        
        logger.info(f"Processing player {player_name} (ID: {player_id})")
        games_processed = 0
        errors = 0
        
        # Store player info
        if not self.store_player_data(player):
            logger.error(f"Failed to store player data for {player_name}")
            errors += 1
            return games_processed, errors
        
        # Process each season
        for season in self.seasons:
            try:
                logger.info(f"Fetching games for {player_name} in {season}")
                games_df = self.get_player_games(player_id, season)

                if games_df is None:
                    # Add to retry queue
                    self.retry_queue.append({
                        'player_id': player_id,
                        'player_name': player_name,
                        'season': season,
                        'retries': 0,
                        'last_attempt': datetime.now()
                    })
                    logger.warning(f"Added {player_name} in {season} to retry queue due to API errors")
                    continue
                
                if games_df.empty:
                    logger.info(f"No games found for {player_name} in {season}")
                    continue
                
                logger.info(f"Processing {len(games_df)} games for {player_name} in {season}")
                
                # Process each game
                for _, game in games_df.iterrows():
                    try:
                        processed_data = self.process_game_data(game, season)
                        if processed_data:
                            if self.store_game_stats(processed_data):
                                games_processed += 1
                            else:
                                errors += 1
                    except Exception as e:
                        logger.error(f"Error processing game for {player_name}: {e}")
                        errors += 1
                
                logger.info(f"Completed {games_processed} games for {player_name} in {season}")
                
            except Exception as e:
                logger.error(f"Error processing season {season} for {player_name}: {e}")
                errors += 1
                continue
        
        # Commit after each player to save progress
        self.commit_batch()
        
        return games_processed, errors
    
    def calculate_time_remaining(self, processed_count, total_count):
        """
        Calculate and format estimated time remaining for the process.
        
        Args:
            processed_count: Number of items processed so far
            total_count: Total number of items to process
            
        Returns:
            Formatted string with estimated time remaining
        """
        if processed_count == 0:
            return "Calculating..."
            
        current_time = datetime.now()
        elapsed = (current_time - self.stats["start_time"]).total_seconds()
        
        # Calculate time per item and estimate remaining time
        time_per_item = elapsed / processed_count
        items_remaining = total_count - processed_count
        seconds_remaining = time_per_item * items_remaining
        
        # Format remaining time
        remaining_time = timedelta(seconds=int(seconds_remaining))
        hours, remainder = divmod(remaining_time.total_seconds(), 3600)
        minutes, seconds = divmod(remainder, 60)
        
        # Format as HH:MM:SS
        time_str = f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"
        
        return time_str
        
    def update_timer(self, processed_count, total_count, force=False):
        """
        Update the timer display if the interval has passed.
        
        Args:
            processed_count: Number of items processed so far
            total_count: Total number of items to process
            force: Force update regardless of timer interval
        """
        current_time = datetime.now()
        
        # Initialize last timer check if needed
        if self.stats["last_timer_check"] is None:
            self.stats["last_timer_check"] = current_time
            return
            
        time_since_check = (current_time - self.stats["last_timer_check"]).total_seconds()
        
        # Update timer if interval passed or forced
        if force or time_since_check >= self.stats["timer_interval"]:
            remaining_str = self.calculate_time_remaining(processed_count, total_count)
            elapsed = (current_time - self.stats["start_time"]).total_seconds()
            hours, remainder = divmod(elapsed, 3600)
            minutes, seconds = divmod(remainder, 60)
            elapsed_str = f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"
            
            progress_pct = (processed_count / total_count) * 100 if total_count > 0 else 0
            
            logger.info(f"Progress: {processed_count}/{total_count} players ({progress_pct:.1f}%)")
            logger.info(f"Elapsed time: {elapsed_str} | Time remaining: {remaining_str}")
            logger.info(f"Rate limit hits: {self.stats['rate_limit_hits']} | Retry queue size: {len(self.retry_queue)}")
            
            # Update timer check timestamp
            self.stats["last_timer_check"] = current_time
            
            # Save retry queue periodically
            if self.config["retry_queue_persistence"] and self.retry_queue:
                self.save_retry_queue()
            
            return remaining_str
        
        return None
    
    def process_retry_queue(self, max_retries=None, base_wait_time=None):
        """
        Process items in the retry queue with a sufficient delay between attempts.
        
        Args:
            max_retries: Maximum number of retries (default: from config)
            base_wait_time: Base wait time between retries (default: from config)
        """
        if not self.retry_queue:
            logger.info("Retry queue is empty")
            return
        
        # Use config values if not provided
        max_retries = max_retries or self.config["max_retries"]
        base_wait_time = base_wait_time or self.config["base_wait_time"]
            
        logger.info(f"Processing retry queue with {len(self.retry_queue)} items")
        current_time = datetime.now()
        
        # Copy queue to avoid modification during iteration
        queue_copy = self.retry_queue.copy()
        self.retry_queue = []
        
        for item in queue_copy:
            # Calculate exponential backoff wait time
            required_wait_time = base_wait_time * (2 ** item['retries'])
            time_since_last = (current_time - item['last_attempt']).total_seconds()
            
            if time_since_last < required_wait_time:
                # Not waited long enough, put back in queue
                self.retry_queue.append(item)
                continue
                
            if item['retries'] >= max_retries:
                logger.warning(f"Giving up on {item['player_name']} in {item['season']} after {max_retries} attempts")
                continue
                
            logger.info(f"Retrying {item['player_name']} in {item['season']} (attempt {item['retries'] + 1})")
            
            # Execute with a longer timeout
            try:
                # Rotate user agent
                self.rotate_user_agent()
                
                # Add human-like randomness
                human_like_delay = random.uniform(2.0, 8.0)
                time.sleep(human_like_delay)
                
                # Use a direct API call with longer timeout
                player_games_query = leaguegamefinder.LeagueGameFinder(
                    player_or_team_abbreviation="P",
                    player_id_nullable=item['player_id'],
                    season_nullable=item['season'],
                    season_type_nullable="Regular Season",
                    timeout=300  # Extended timeout for retries
                )
                
                games_df = player_games_query.get_data_frames()[0]
                
                if not games_df.empty:
                    logger.info(f"Retry successful! Retrieved {len(games_df)} games for {item['player_name']} in {item['season']}")
                    
                    # Cache the results
                    games_data = games_df.to_dict('records')
                    self.save_to_cache(games_data, "games", item['player_id'], item['season'])
                    
                    # Process the games
                    games_processed = 0
                    for _, game in games_df.iterrows():
                        processed_data = self.process_game_data(game, item['season'])
                        if processed_data and self.store_game_stats(processed_data):
                            games_processed += 1
                    
                    logger.info(f"Processed {games_processed} games from retry for {item['player_name']} in {item['season']}")
                    
                else:
                    logger.info(f"Retry successful but no games found for {item['player_name']} in {item['season']}")
                    
            except Exception as e:
                # Increment retry count and put back in queue
                item['retries'] += 1
                item['last_attempt'] = datetime.now()
                self.retry_queue.append(item)
                logger.error(f"Retry failed for {item['player_name']} in {item['season']}: {e}")
        
        # Save updated retry queue
        if self.config["retry_queue_persistence"] and self.retry_queue:
            self.save_retry_queue()
            
        logger.info(f"Retry queue processing complete. {len(self.retry_queue)} items remaining")
    
    def run_ingestion(self, start_player=0, end_player=None):
        """
        Run ingestion process for a specific range of players.
        
        Args:
            start_player: Index of the first player to process (0-based)
            end_player: Index of the last player to process (exclusive)
        """
        logger.info("Starting data ingestion")
        logger.info(f"Will collect data for seasons: {', '.join(self.seasons)}")
        logger.info("=" * 80)
        
        self.stats["start_time"] = datetime.now()
        self.stats["last_update_time"] = self.stats["start_time"]
        self.stats["last_timer_check"] = self.stats["start_time"]
        
        # Get active players
        active_players = self.get_active_players()
        
        if not active_players:
            logger.error("Failed to retrieve active players list")
            return
        
        # Apply range selection
        if end_player is not None:
            active_players = active_players[start_player:end_player]
        elif start_player > 0:
            active_players = active_players[start_player:]
        
        # Log the player range being processed
        player_range_info = f"Processing players {start_player}"
        if end_player is not None:
            player_range_info += f" to {end_player-1}"
        logger.info(player_range_info)
        
        total_players = len(active_players)
        logger.info(f"Processing {total_players} players sequentially")
        logger.info(f"Initial timer estimate: {self.calculate_time_remaining(1, total_players)}")
        
        # Track progress for better visibility
        progress = tqdm(total=total_players, desc="Processing players")
        
        # Process each player one at a time
        successful_players = 0
        failed_players = 0
        
        # Add rate limiting tracker
        rate_limit_hits = 0
        consecutive_timeouts = 0
        
        for idx, player in enumerate(active_players, 1):
            # If we've hit rate limits multiple times in succession, take a longer break
            if consecutive_timeouts > 3:
                logger.warning(f"Detected multiple consecutive timeouts. Taking a longer break (120s)")
                time.sleep(120)
                consecutive_timeouts = 0
                
            # Take a longer defensive break every 50 players
            if idx > 0 and idx % 50 == 0:
                cooling_period = random.uniform(180, 300)  # 3-5 minute break
                logger.info(f"Taking a defensive cooling break of {cooling_period:.1f}s after {idx} players")
                time.sleep(cooling_period)
                
            try:
                player_name = player['full_name']
                logger.info(f"Processing player {idx}/{total_players}: {player_name}")
                
                games_processed, errors = self.process_player(player)
                
                if games_processed > 0:
                    successful_players += 1
                    consecutive_timeouts = 0  # Reset timeout counter on success
                    logger.info(f"Successfully processed {games_processed} games for {player_name} with {errors} errors")
                else:
                    # If no games were processed but we didn't hit an exception
                    if errors == 0:
                        logger.info(f"No games found for {player_name}")
                        consecutive_timeouts = 0  # Also reset on valid empty responses
                    else:
                        failed_players += 1
                        consecutive_timeouts += 1
                        logger.warning(f"Failed to process any games for {player_name} with {errors} errors")
                
                # Commit at regular intervals to save progress
                if (idx % self.config["batch_size"]) == 0:
                    logger.info(f"Checkpoint: Processed {idx}/{total_players} players, committing batch")
                    self.commit_batch()
                    
                    # Update timer information
                    self.update_timer(idx, total_players)
                
                # Add random delay between players to avoid API rate limits
                # Use a longer delay if we've recently hit rate limits
                if self.stats["rate_limit_hits"] > rate_limit_hits:
                    # We hit a new rate limit in this iteration
                    logger.warning("Rate limit detected, increasing delay")
                    delay = random.uniform(
                        self.config["request_delay_max"], 
                        self.config["request_delay_max"] * 2
                    )
                    rate_limit_hits = self.stats["rate_limit_hits"]
                else:
                    delay = random.uniform(
                        self.config["request_delay_min"], 
                        self.config["request_delay_max"]
                    )
                
                time.sleep(delay)
                
            except Exception as e:
                failed_players += 1
                consecutive_timeouts += 1
                logger.error(f"Error processing player {player['full_name']}: {str(e)}")
                self.stats["errors"] += 1
            finally:
                # Update progress bar regardless of success/failure
                progress.update(1)
        
        progress.close()
        
        # Final commit for any remaining changes
        self.commit_batch()

        # Process retry queue if there are items
        if self.retry_queue:
            logger.info(f"Processing {len(self.retry_queue)} items in retry queue")
            self.process_retry_queue()
            self.commit_batch()
        
        # Final timer update
        self.update_timer(total_players, total_players, force=True)
        
        logger.info(f"Player processing completed: {successful_players} successful, {failed_players} failed")
        
        # Run cleanup operations if configured
        if self.config["clean_duplicates"]:
            logger.info("Running duplicate cleanup...")
            self.clean_duplicate_entries()
        
        if self.config["verify_data"]:
            logger.info("Verifying data integrity...")
            self.verify_ingested_data()
        
        self.stats["end_time"] = datetime.now()
        self.print_stats()
        
        # Close the database session
        self.close_session()
        
        logger.info("Data ingestion completed successfully")
    
    def clean_duplicate_entries(self):
        """Remove duplicate game entries from the database."""
        logger.info("Cleaning duplicate entries from the database")
        session = self.get_or_create_db_session()
        
        try:
            # First, identify duplicates
            find_duplicates_query = text("""
                SELECT player_id, game_id, COUNT(*) as count
                FROM player_stats
                GROUP BY player_id, game_id
                HAVING COUNT(*) > 1
            """)
            
            duplicate_result = session.execute(find_duplicates_query)
            duplicates = [{"player_id": row[0], "game_id": row[1], "count": row[2]} for row in duplicate_result]
            
            if not duplicates:
                logger.info("No duplicates found. Database is clean.")
                return
                
            logger.info(f"Found {len(duplicates)} sets of duplicate entries")
            
            # For each set of duplicates, keep the earliest entry and delete the rest
            total_deleted = 0
            for dup in duplicates:
                # Get all duplicate entries for this player-game combination
                find_entries_query = text(f"""
                    SELECT id FROM player_stats
                    WHERE player_id = {dup['player_id']} AND game_id = '{dup['game_id']}'
                    ORDER BY id ASC
                """)
                
                entries_result = session.execute(find_entries_query)
                entry_ids = [row[0] for row in entries_result]
                
                # Keep the first one (with the lowest ID), delete the rest
                if len(entry_ids) > 1:
                    ids_to_delete = entry_ids[1:]
                    delete_query = text(f"""
                        DELETE FROM player_stats
                        WHERE id IN ({','.join(str(id) for id in ids_to_delete)})
                    """)
                    
                    result = session.execute(delete_query)
                    deleted_count = result.rowcount
                    total_deleted += deleted_count
                    
                    logger.info(f"Deleted {deleted_count} duplicates for player {dup['player_id']}, game {dup['game_id']}")
            
            session.commit()
            logger.info(f"Successfully removed {total_deleted} duplicate entries")
            
            # Verify the cleanup was successful
            verify_query = text("""
                SELECT player_id, game_id, COUNT(*) as count
                FROM player_stats
                GROUP BY player_id, game_id
                HAVING COUNT(*) > 1
            """)
            
            verify_result = session.execute(verify_query)
            remaining_duplicates = [row for row in verify_result]
            
            if remaining_duplicates:
                logger.warning(f"There are still {len(remaining_duplicates)} sets of duplicates remaining")
            else:
                logger.info("All duplicates successfully removed")
                
        except Exception as e:
            logger.error(f"Error cleaning up database: {e}")
            session.rollback()
    
    def verify_ingested_data(self):
        """Verify the integrity of ingested data."""
        logger.info("Verifying ingested data")
        session = self.get_or_create_db_session()
        
        try:
            # 1. Check for players with more than 82 games in a season
            query = text("""
                SELECT p.player_id, p.full_name, ps.season, COUNT(*) as game_count
                FROM players p
                JOIN player_stats ps ON p.player_id = ps.player_id
                GROUP BY p.player_id, p.full_name, ps.season
                HAVING COUNT(*) > 82
                ORDER BY game_count DESC
            """)
            
            result = session.execute(query)
            issues = [{"player_id": row[0], "name": row[1], "season": row[2], "count": row[3]} 
                    for row in result]
            
            if issues:
                logger.warning(f"Found {len(issues)} player-seasons with more than 82 games:")
                for issue in issues[:10]:  # Show only first 10 to avoid log spam
                    logger.warning(f"  {issue['name']} (ID: {issue['player_id']}): {issue['count']} games in {issue['season']}")
            else:
                logger.info("All player-seasons have 82 or fewer games - data looks valid")
            
            # 2. Check for missing essential data
            missing_data_query = text("""
                SELECT COUNT(*) FROM player_stats 
                WHERE points IS NULL OR rebounds IS NULL OR assists IS NULL
            """)
            missing_count = session.execute(missing_data_query).scalar()
            
            if missing_count > 0:
                logger.warning(f"Found {missing_count} records with missing essential stats")
            else:
                logger.info("No records with missing essential stats - data looks valid")
            
            # 3. Check for players without any game data
            orphaned_query = text("""
                SELECT p.player_id, p.full_name
                FROM players p
                LEFT JOIN player_stats ps ON p.player_id = ps.player_id
                WHERE ps.id IS NULL
            """)
            
            orphan_result = session.execute(orphaned_query)
            orphans = [{"player_id": row[0], "name": row[1]} for row in orphan_result]
            
            if orphans:
                logger.warning(f"Found {len(orphans)} players with no game data:")
                for orphan in orphans[:10]:  # Show only first 10
                    logger.warning(f"  {orphan['name']} (ID: {orphan['player_id']})")
            else:
                logger.info("All players have associated game data - data looks valid")
                
        except Exception as e:
            logger.error(f"Error verifying data: {e}")
    
    def print_stats(self):
        """Print statistics about the ingestion process."""
        if not self.stats["start_time"] or not self.stats["end_time"]:
            logger.warning("Cannot print stats: missing start or end time")
            return
            
        duration = self.stats["end_time"] - self.stats["start_time"]
        hours, remainder = divmod(duration.total_seconds(), 3600)
        minutes, seconds = divmod(remainder, 60)
        
        logger.info("=" * 50)
        logger.info("INGESTION STATISTICS")
        logger.info("=" * 50)
        logger.info(f"Duration: {int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}")
        logger.info(f"Players processed: {self.stats['players_processed']}")
        logger.info(f"Games processed: {self.stats['games_processed']}")
        logger.info(f"API requests: {self.stats['api_requests']}")
        logger.info(f"Cache hits: {self.stats['cache_hits']}")
        logger.info(f"Database inserts: {self.stats['db_inserts']}")
        logger.info(f"Database updates: {self.stats['db_updates']}")
        logger.info(f"Errors: {self.stats['errors']}")
        logger.info(f"Rate limit hits: {self.stats['rate_limit_hits']}")
        logger.info(f"Items remaining in retry queue: {len(self.retry_queue)}")
        
        if self.stats["games_processed"] > 0:
            success_rate = 100 * (1 - (self.stats["errors"] / (self.stats["games_processed"] + self.stats["errors"])))
            logger.info(f"Success rate: {success_rate:.2f}%")
        
        if duration.total_seconds() > 0:
            games_per_second = self.stats["games_processed"] / duration.total_seconds()
            logger.info(f"Processing rate: {games_per_second:.2f} games/second")
        
        logger.info("=" * 50)

def main():
    """Main entrypoint for running the ingestion process."""
    parser = argparse.ArgumentParser(description="NBA Data Ingestion Tool")
    parser.add_argument("--seasons", type=int, default=5, help="Number of seasons to fetch")
    parser.add_argument("--no-cache", action="store_true", help="Disable caching")
    parser.add_argument("--no-verify", action="store_true", help="Skip data verification")
    parser.add_argument("--no-retry-queue", action="store_true", help="Disable retry queue persistence")
    parser.add_argument("--start-player", type=int, default=0, help="Index of the first player to process (0-based)")
    parser.add_argument("--end-player", type=int, default=None, help="Index of the last player to process (exclusive)")
    args = parser.parse_args()
    
    # Create configuration with simplified parameters and fixed defaults
    config = {
        "seasons_to_fetch": args.seasons,
        "batch_size": 10,              
        "enable_caching": not args.no_cache,
        "clean_duplicates": True,      
        "verify_data": not args.no_verify,
        "retry_queue_persistence": not args.no_retry_queue,
        "max_retries": 5,           
        "timer_interval": 60
    }
    
    # Initialize and run ingestion
    ingestion = NBADataIngestion(config)
    ingestion.run_ingestion(start_player=args.start_player, end_player=args.end_player)

if __name__ == "__main__":
    main()
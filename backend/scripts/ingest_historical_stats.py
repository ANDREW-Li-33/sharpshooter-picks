import sys
from pathlib import Path

# Add the backend directory to the path so we can import from models
backend_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(backend_dir))

from nba_api.stats.static import players
from nba_api.stats.endpoints import leaguegamefinder
import pandas as pd
import time
from datetime import datetime
from typing import List, Dict
from sqlalchemy.orm import Session
from backend.models.db_schema import PlayerStats, Player, engine
import logging
import random
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

log_path = Path(__file__).parent / 'nba_stats_ingestion.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('nba_stats_ingestion.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class NBADataIngestion:
    def __init__(self):
        """Initialize the NBA data ingestion module."""
        self.current_season = datetime.now().year
        self.seasons = [
            f"{year}-{str(year + 1)[-2:]}" 
            for year in range(self.current_season - 5, self.current_season)
        ]
        
        retry_strategy = Retry(
            total=5,
            backoff_factor=2,
            status_forcelist=[429, 500, 502, 503, 504]
        )

        self.http_adapter = HTTPAdapter(max_retries=retry_strategy)
        self.http_session = requests.Session()
        self.http_session.mount("https://", self.http_adapter)
        self.http_session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
    def get_active_players(self) -> List[Dict]:
        try:
            active_players = players.get_active_players()
            logger.info(f"Found {len(active_players)} active players")
            return active_players
        except Exception as e:
            logger.error(f"Error fetching active players: {e}")
            return []

    def get_player_games(self, player_id: int, season: str) -> pd.DataFrame:
        max_retries = 5  
        current_retry = 0
        base_delay = 2 
        
        while current_retry < max_retries:
            try:
                delay = base_delay * (2 ** current_retry) + random.uniform(1.0, 3.0)
                time.sleep(delay)
                
                player_games_query = leaguegamefinder.LeagueGameFinder(
                    player_or_team_abbreviation="P",
                    player_id_nullable=player_id,
                    season_nullable=season,
                    season_type_nullable="Regular Season",
                    timeout=180 
                )
                
                headers = {
                    'User-Agent': f'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/{random.randint(80, 108)}.0.0.0'
                }
                self.http_session.headers.update(headers)
                
                games_df = player_games_query.get_data_frames()[0]
                if not games_df.empty:
                    logger.info(f"Successfully retrieved data for player {player_id}")
                    return games_df
                
                return pd.DataFrame()
                    
            except Exception as e:
                current_retry += 1
                if current_retry < max_retries:
                    logger.warning(f"Attempt {current_retry} failed: {e}")
                    continue
                else:
                    logger.error(f"Failed after {max_retries} attempts: {e}")
                    return pd.DataFrame()

    def process_game_data(self, game_data: pd.Series, season: str) -> Dict:
        try:
            return {
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
        except Exception as e:
            logger.error(f"Error processing game data: {e}")
            return None

    def store_player_data(self, player: Dict):
        with Session(engine) as session:
            try:
                existing_player = session.query(Player).filter_by(player_id=player['id']).first()
                
                if existing_player:
                    existing_player.full_name = player['full_name']
                    existing_player.is_active = True
                else:
                    player_record = Player(
                        player_id=player['id'],
                        full_name=player['full_name'],
                        is_active=True
                    )
                    session.add(player_record)
                
                session.commit()
            except Exception as e:
                logger.error(f"Error storing player data: {e}")
                session.rollback()

    def store_game_stats(self, stats_data: Dict):
        if not stats_data:
            return
            
        with Session(engine) as session:
            try:
                stats = PlayerStats(**stats_data)
                session.merge(stats)
                session.commit()
            except Exception as e:
                logger.error(f"Error storing game stats: {e}")
                session.rollback()

    def run_ingestion(self):
        logger.info("Starting historical data ingestion")
        logger.info(f"Will collect data for seasons: {', '.join(self.seasons)}")
        logger.info("=" * 80)
        
        active_players = self.get_active_players()
        total_players = len(active_players)
        
        for idx, player in enumerate(active_players, 1):
            try:
                logger.info(f"Processing player {idx}/{total_players}: {player['full_name']}")
                self.store_player_data(player)
                for season in self.seasons:
                    games_df = self.get_player_games(player['id'], season)
                    
                    if games_df.empty:
                        continue
                    
                    for _, game in games_df.iterrows():
                        processed_data = self.process_game_data(game, season)
                        self.store_game_stats(processed_data)
                    
                    logger.info(f"Processed {len(games_df)} games for {player['full_name']} in {season}")
                
            except Exception as e:
                logger.error(f"Error processing player {player['full_name']}: {e}")
                continue
            
            time.sleep(random.uniform(1, 3))
            logger.info("=" * 80)

        logger.info("Historical data ingestion completed")

if __name__ == "__main__":
    ingestion = NBADataIngestion()
    ingestion.run_ingestion()

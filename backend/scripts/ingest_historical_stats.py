import sys
from pathlib import Path

# Add the backend directory to the path so we can import from models
backend_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(backend_dir))

from nba_api.stats.endpoints import playergamelog, commonplayerinfo, leaguegamefinder
from nba_api.stats.static import players
from nba_api.stats.library.parameters import SeasonTypeAllStar
import pandas as pd
import time
from datetime import datetime
from typing import List, Dict, Set
from sqlalchemy.orm import Session
from models.database import Game, PlayerStats, engine
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('nba_stats_ingestion.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class PlayerStatsIngestion:
    def __init__(self):
        """Initialize the player stats ingestion module."""
        self.current_season = datetime.now().year
        self.seasons = [
            f"{year}-{str(year + 1)[-2:]}" 
            for year in range(self.current_season - 5, self.current_season)
        ]
        
    def get_active_players(self) -> List[Dict]:
        """Get list of currently active NBA players."""
        try:
            all_players = players.get_active_players()
            logger.info(f"Found {len(all_players)} active players")
            return all_players
        except Exception as e:
            logger.error(f"Error fetching active players: {e}")
            return []

    def get_player_game_logs(self, player_id: int, seasons: List[str]) -> pd.DataFrame:
        """
        Fetch game logs for a specific player across multiple seasons.
        
        Args:
            player_id (int): NBA API player ID
            seasons (List[str]): List of seasons in format "YYYY-YY"
            
        Returns:
            pd.DataFrame: DataFrame containing player's game logs
        """
        all_games = []
        
        for season in seasons:
            try:
                # Add delay to respect API rate limits
                time.sleep(1)
                
                # Fetch regular season games only
                gamelog = playergamelog.PlayerGameLog(
                    player_id=player_id,
                    season=season,
                    season_type_all_star=SeasonTypeAllStar.regular
                )
                
                games_df = gamelog.get_data_frames()[0]
                if not games_df.empty:
                    games_df['SEASON'] = season
                    all_games.append(games_df)
                    
                logger.info(f"Fetched {len(games_df)} games for player {player_id} in season {season}")
                
            except Exception as e:
                logger.error(f"Error fetching games for player {player_id} in season {season}: {e}")
                continue
        
        return pd.concat(all_games) if all_games else pd.DataFrame()

    def process_game_data(self, game_data: pd.Series) -> Dict:
        """
        Process raw game data into structured format.
        
        Args:
            game_data (pd.Series): Single game data
            
        Returns:
            Dict: Processed game data
        """
        return {
            'game_id': game_data['Game_ID'],
            'player_id': game_data['Player_ID'],
            'season': game_data['SEASON'],
            'game_date': pd.to_datetime(game_data['GAME_DATE']),
            'home_game': 'vs.' in game_data['MATCHUP'],
            'team_id': game_data['Team_ID'],
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

    def store_player_stats(self, stats_data: Dict):
        """
        Store player stats in the database.
        
        Args:
            stats_data (Dict): Processed game statistics
        """
        with Session(engine) as session:
            try:
                stats = PlayerStats(
                    game_id=stats_data['game_id'],
                    player_id=stats_data['player_id'],
                    minutes_played=stats_data['minutes_played'],
                    points=stats_data['points'],
                    rebounds=stats_data['rebounds'],
                    assists=stats_data['assists'],
                    steals=stats_data['steals'],
                    blocks=stats_data['blocks'],
                    turnovers=stats_data['turnovers'],
                    plus_minus=stats_data['plus_minus'],
                    fg_made=stats_data['fg_made'],
                    fg_attempted=stats_data['fg_attempted'],
                    fg3_made=stats_data['fg3_made'],
                    fg3_attempted=stats_data['fg3_attempted'],
                    ft_made=stats_data['ft_made'],
                    ft_attempted=stats_data['ft_attempted'],
                    is_home_game=stats_data['home_game']
                )
                
                session.merge(stats)
                session.commit()
                
            except Exception as e:
                logger.error(f"Error storing stats data: {e}")
                session.rollback()

    def run_ingestion(self):
        """Run the complete historical stats ingestion process."""
        logger.info("Starting historical stats ingestion")
        logger.info(f"Will collect data for seasons: {', '.join(self.seasons)}")
        
        active_players = self.get_active_players()
        total_players = len(active_players)
        
        for idx, player in enumerate(active_players, 1):
            try:
                logger.info(f"Processing player {idx}/{total_players}: {player['full_name']}")
                
                # Get all game logs for player
                game_logs = self.get_player_game_logs(player['id'], self.seasons)
                
                if game_logs.empty:
                    continue
                
                # Process and store each game
                for _, game in game_logs.iterrows():
                    processed_data = self.process_game_data(game)
                    self.store_player_stats(processed_data)
                
                logger.info(f"Completed processing {len(game_logs)} games for {player['full_name']}")
                
            except Exception as e:
                logger.error(f"Error processing player {player['full_name']}: {e}")
                continue
        
        logger.info("Historical stats ingestion completed")

if __name__ == "__main__":
    ingestion = PlayerStatsIngestion()
    ingestion.run_ingestion()
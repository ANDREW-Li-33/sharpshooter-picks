import sys
import random
from pathlib import Path
import unittest
import pandas as pd
from datetime import datetime
from sqlalchemy.orm import Session

script_dir = Path(__file__).resolve().parent  # .../backend/scripts
backend_dir = script_dir.parent               # .../backend
project_root = backend_dir.parent             # .../Sharpshooter Picks
sys.path.append(str(project_root))            # Add the actual project root

# Import with relative paths
from ingest_historical_stats import NBADataIngestion  # Same directory import
from db_config import engine  # From parent directory
from db_models.db_schema import Player, PlayerStats  # From parent's subdirectory

class TestNBAIngestion:
    """Class for testing components of the NBA data ingestion process"""
    
    def __init__(self):
        self.ingestion = NBADataIngestion()
        self.session = Session(engine)
    
    def cleanup(self):
        """Clean up resources"""
        self.session.close()
    
    def test_player_api(self):
        """Test the NBA API player retrieval"""
        print("\n----- Testing NBA API Player Retrieval -----")
        active_players = self.ingestion.get_active_players()
        
        if not active_players:
            print("❌ Failed to retrieve active players")
            return False
        
        print(f"✅ Successfully retrieved {len(active_players)} active players")
        
        # Print a few sample players to verify data structure
        if active_players:
            print("\nSample player data:")
            for i, player in enumerate(random.sample(active_players, min(3, len(active_players)))):
                print(f"  {i+1}. {player['full_name']} (ID: {player['id']})")
                
        return len(active_players) > 0
    
    def test_game_api(self, player_id=None, season="2023-24"):
        """Test the NBA API game retrieval for a specific player"""
        print(f"\n----- Testing NBA API Game Retrieval for Season {season} -----")
        
        # If no player_id is provided, get one from the API
        if player_id is None:
            active_players = self.ingestion.get_active_players()
            if not active_players:
                print("❌ Failed to retrieve players to test game API")
                return False
            
            # Select a popular player who will likely have games
            popular_players = ["LeBron James", "Stephen Curry", "Kevin Durant", "Jayson Tatum", "Luka Doncic"]
            player = None
            
            for name in popular_players:
                for p in active_players:
                    if p['full_name'] == name:
                        player = p
                        break
                if player:
                    break
                    
            if not player:
                # Just pick a random player if none of the popular ones are found
                player = random.choice(active_players)
            
            player_id = player['id']
            print(f"Selected player: {player['full_name']} (ID: {player_id})")
        
        # Retrieve games for the player
        games_df = self.ingestion.get_player_games(player_id, season)
        
        if games_df is None or games_df.empty:
            print(f"❌ Failed to retrieve games for player ID {player_id} in season {season}")
            return False
        
        print(f"✅ Successfully retrieved {len(games_df)} games for player ID {player_id}")
        
        # Print available columns to understand the data structure
        print("\nAvailable columns:")
        print(", ".join(games_df.columns.tolist()))
        
        # Print a sample game
        if not games_df.empty:
            print("\nSample game data:")
            sample_game = games_df.iloc[0]
            
            relevant_cols = [
                'GAME_ID', 'GAME_DATE', 'MATCHUP', 'WL', 
                'MIN', 'PTS', 'REB', 'AST', 'STL', 'BLK', 
                'TOV', 'PLUS_MINUS', 'FGM', 'FGA', 'FG3M', 'FG3A', 
                'FTM', 'FTA'
            ]
            
            # Only show columns that exist in the dataframe
            cols_to_show = [col for col in relevant_cols if col in sample_game.index]
            
            for col in cols_to_show:
                print(f"  {col}: {sample_game[col]}")
        
        return not games_df.empty
    
    def test_process_game_data(self, player_id=None, season="2023-24"):
        """Test the game data processing functionality"""
        print("\n----- Testing Game Data Processing -----")
        
        # First, get a real game to process
        if player_id is None:
            # Get a player
            active_players = self.ingestion.get_active_players()
            if not active_players:
                print("❌ Failed to retrieve players to test data processing")
                return False
            
            # Select a popular player
            player = None
            for p in active_players:
                if p['full_name'] in ["LeBron James", "Stephen Curry", "Giannis Antetokounmpo"]:
                    player = p
                    break
            
            if not player:
                player = random.choice(active_players)
            
            player_id = player['id']
        
        # Get games for the player
        games_df = self.ingestion.get_player_games(player_id, season)
        
        if games_df is None or games_df.empty:
            print(f"❌ No games found for player ID {player_id} in season {season}")
            return False
        
        # Select a random game
        sample_game = games_df.iloc[random.randint(0, len(games_df) - 1)]
        
        # Process the game data
        processed_data = self.ingestion.process_game_data(sample_game, season)
        
        if processed_data is None:
            print("❌ Failed to process game data")
            return False
        
        print("✅ Successfully processed game data")
        print("\nProcessed game fields:")
        
        # Print the processed fields
        for key, value in processed_data.items():
            print(f"  {key}: {value}")
        
        # Verify all required fields are present
        expected_fields = [
            'game_id', 'player_id', 'game_date', 'season', 'is_home_game',
            'minutes_played', 'points', 'rebounds', 'assists', 'steals',
            'blocks', 'turnovers', 'plus_minus', 'fg_made', 'fg_attempted',
            'fg3_made', 'fg3_attempted', 'ft_made', 'ft_attempted'
        ]
        
        missing_fields = [field for field in expected_fields if field not in processed_data]
        
        if missing_fields:
            print(f"❌ Missing fields in processed data: {', '.join(missing_fields)}")
            return False
        
        print("✅ All required fields are present in the processed data")
        return True
    
    def test_db_connection_and_schema(self):
        """Test database connection and verify schema"""
        print("\n----- Testing Database Connection and Schema -----")
        
        try:
            # Check if we can query the database
            player_count = self.session.query(Player).count()
            stats_count = self.session.query(PlayerStats).count()
            
            print(f"✅ Database connection successful")
            print(f"  Current database contains {player_count} players and {stats_count} game stats records")
            
            # Check Player table columns
            player_columns = [column.name for column in Player.__table__.columns]
            print("\nPlayer table columns:", ", ".join(player_columns))
            
            # Check PlayerStats table columns
            stats_columns = [column.name for column in PlayerStats.__table__.columns]
            print("\nPlayerStats table columns:", ", ".join(stats_columns))
            
            return True
            
        except Exception as e:
            print(f"❌ Database connection error: {e}")
            return False
    
    def test_single_player_ingestion(self, player_id=None, season="2023-24", limit_games=2):
        """Test the ingestion process for a single player with limited games"""
        print("\n----- Testing Single Player Ingestion Process -----")
        
        # Get a player to test
        if player_id is None:
            active_players = self.ingestion.get_active_players()
            if not active_players:
                print("❌ Failed to retrieve players for testing")
                return False
            
            # Select a random player
            player = random.choice(active_players)
            player_id = player['id']
            print(f"Selected player: {player['full_name']} (ID: {player_id})")
        else:
            # Get player info
            active_players = self.ingestion.get_active_players()
            player = next((p for p in active_players if p['id'] == player_id), None)
            if player:
                print(f"Using player: {player['full_name']} (ID: {player_id})")
            else:
                print(f"Using player ID: {player_id} (name unknown)")
        
        # Store player in database
        print("\nStoring player in database...")
        if player:
            self.ingestion.store_player_data(player)
        else:
            # Create a minimal player record if the player info wasn't found
            self.ingestion.store_player_data({
                'id': player_id,
                'full_name': f"TestPlayer_{player_id}",
                'is_active': True
            })
        
        # Verify player was stored
        db_player = self.session.query(Player).filter_by(player_id=player_id).first()
        if not db_player:
            print("❌ Failed to store player in database")
            return False
        
        print(f"✅ Player stored successfully: {db_player.full_name}")
        
        # Get games for the player
        print(f"\nRetrieving games for player from season {season}...")
        games_df = self.ingestion.get_player_games(player_id, season)
        
        if games_df is None or games_df.empty:
            print(f"❌ No games found for player ID {player_id} in season {season}")
            return False
        
        # Limit the number of games for testing
        games_to_process = games_df.head(limit_games)
        print(f"✅ Retrieved {len(games_df)} games, will process {len(games_to_process)}")
        
        # Process and store each game
        successful_games = 0
        for _, game in games_to_process.iterrows():
            try:
                processed_data = self.ingestion.process_game_data(game, season)
                if processed_data:
                    self.ingestion.store_game_stats(processed_data)
                    successful_games += 1
            except Exception as e:
                print(f"❌ Error processing game: {e}")
        
        print(f"✅ Successfully processed and stored {successful_games} out of {len(games_to_process)} games")
        
        # Verify games were stored
        db_stats = self.session.query(PlayerStats).filter_by(player_id=player_id).all()
        
        if not db_stats:
            print("❌ No game stats were stored in the database")
            return False
        
        print(f"✅ Found {len(db_stats)} games in database for player {player_id}")
        
        # Show a sample of the stored data
        if db_stats:
            print("\nSample of stored game data:")
            sample_stat = db_stats[0]
            print(f"  Game ID: {sample_stat.game_id}")
            print(f"  Date: {sample_stat.game_date}")
            print(f"  Points: {sample_stat.points}")
            print(f"  Rebounds: {sample_stat.rebounds}")
            print(f"  Assists: {sample_stat.assists}")
        
        return successful_games > 0
    
    def verify_data_in_tables(self, player_id=None):
        """Verify the data in the database tables"""
        print("\n----- Verifying Data in Database Tables -----")
        
        # Get stats for a specific player if provided
        if player_id:
            player = self.session.query(Player).filter_by(player_id=player_id).first()
            if not player:
                print(f"❌ Player ID {player_id} not found in database")
                return False
            
            print(f"Found player: {player.full_name} (ID: {player.player_id})")
            
            stats = self.session.query(PlayerStats).filter_by(player_id=player_id).all()
            print(f"Found {len(stats)} game stats for this player")
            
            if stats:
                print("\nSeason breakdown:")
                stats_by_season = {}
                for stat in stats:
                    if stat.season not in stats_by_season:
                        stats_by_season[stat.season] = 0
                    stats_by_season[stat.season] += 1
                
                for season, count in stats_by_season.items():
                    print(f"  {season}: {count} games")
        else:
            # Get overall database stats
            player_count = self.session.query(Player).count()
            active_player_count = self.session.query(Player).filter_by(is_active=True).count()
            stats_count = self.session.query(PlayerStats).count()
            
            print(f"Total players in database: {player_count} ({active_player_count} active)")
            print(f"Total game stats in database: {stats_count}")
            
            # Get some sample players
            sample_players = self.session.query(Player).limit(5).all()
            if sample_players:
                print("\nSample players in database:")
                for i, p in enumerate(sample_players):
                    stats_count = self.session.query(PlayerStats).filter_by(player_id=p.player_id).count()
                    print(f"  {i+1}. {p.full_name} (ID: {p.player_id}): {stats_count} games")
        
        return True
    
    def run_all_tests(self, player_id=None):
        """Run all tests"""
        print("=" * 60)
        print("RUNNING ALL NBA DATA INGESTION TESTS")
        print("=" * 60)
        
        tests = [
            self.test_player_api,
            self.test_game_api,
            self.test_process_game_data,
            self.test_db_connection_and_schema,
            lambda: self.test_single_player_ingestion(player_id=player_id),
            lambda: self.verify_data_in_tables(player_id=player_id)
        ]
        
        success_count = 0
        
        for test in tests:
            try:
                if test():
                    success_count += 1
            except Exception as e:
                print(f"❌ Test failed with exception: {e}")
        
        print("\n" + "=" * 60)
        print(f"TEST SUMMARY: {success_count}/{len(tests)} tests passed")
        print("=" * 60)

if __name__ == "__main__":
    # Parse command line arguments
    import argparse
    
    parser = argparse.ArgumentParser(description="Test the NBA data ingestion process")
    parser.add_argument("--player-id", type=int, help="Specific player ID to test with")
    parser.add_argument("--test", choices=["all", "api", "process", "db", "ingestion", "verify"], 
                        default="all", help="Specific test to run")
    parser.add_argument("--season", type=str, default="2023-24", help="Season to use for testing")
    
    args = parser.parse_args()
    
    tester = TestNBAIngestion()
    
    try:
        if args.test == "all":
            tester.run_all_tests(player_id=args.player_id)
        elif args.test == "api":
            tester.test_player_api()
            tester.test_game_api(player_id=args.player_id, season=args.season)
        elif args.test == "process":
            tester.test_process_game_data(player_id=args.player_id, season=args.season)
        elif args.test == "db":
            tester.test_db_connection_and_schema()
        elif args.test == "ingestion":
            tester.test_single_player_ingestion(player_id=args.player_id, season=args.season)
        elif args.test == "verify":
            tester.verify_data_in_tables(player_id=args.player_id)
    finally:
        tester.cleanup()
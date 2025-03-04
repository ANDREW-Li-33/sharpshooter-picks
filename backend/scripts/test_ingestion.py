import argparse
import random
import pandas as pd
import sys
from pathlib import Path
from typing import List, Dict

from sqlalchemy.orm import Session

script_dir = Path(__file__).resolve().parent  # .../backend/scripts
backend_dir = script_dir.parent               # .../backend
project_root = backend_dir.parent             # .../Sharpshooter Picks
sys.path.append(str(project_root))            #  the actual project root

from ingest_historical_stats import NBADataIngestion  # Same directory import
from backend.db_config import engine  # From parent directory
from backend.db_models.db_schema import Player, PlayerStats  # From parent's subdirectory

class TestNBAIngestion:
    
    def __init__(self):
        self.ingestion = NBADataIngestion()
        self.session = Session(engine)

        self.active_players = self.ingestion.get_active_players() or []
    
    def closeSession(self) -> None:
        """releases any resources tied up in the open connection"""
        self.session.close()
    
    def test_player_api(self) -> List[Dict]:
        """test nba-api player retrieval"""
        print("\n----- Testing NBA API Player Retrieval -----")
        
        if not self.active_players:
            print("❌ Failed to retrieve active players")
            return []
        
        print(f"✅ Successfully retrieved {len(self.active_players)} active players")
        
        # Print five sample players to verify data structure
        print("\nSample player data:")
        for player in random.sample(self.active_players, 5):
            print(f"  {player['full_name']} (ID: {player['id']})")
                
        return self.active_players
    
    def test_game_api(self, player_name=None, season="2024-25") -> pd.Series:
        """Test the NBA API game retrieval for a specific player"""
        print(f"\n----- Testing NBA API Game Retrieval for Season {season} -----")

        player = None
        
        # If no player_id is provided, get one from test_player_api
        if player_name is None:
            print("Since no player name was specified in the command line arguments, I'm going to choose a random player from test_player_api() \n")

            # an empty list evaluates to false in python
            if not self.test_player_api():
                print("❌ Failed to retrieve players to test game API")
                return None


            player = random.choice(self.active_players)
            
            player_id = player['id']
            player_name = player['full_name']
            print(f"Selected player: {player['full_name']} (ID: {player_id})")
        else:
            player = next((p for p in self.active_players if p['full_name'].lower() == player_name.lower()), None)

            if player is None:
                print(f"❌ Failed to find {player_name} in the database. Please make sure your spelling is correct, including accents and capitalization!")
                return None
            player_id = player['id']
                

        # Retrieve games for the player
        games_df = self.ingestion.get_player_games(player_id, season)
        
        if games_df is None or games_df.empty:
            print(f"❌ Failed to retrieve games for {player_name} in season {season}")
            return None
        
        print(f"✅ Successfully retrieved {len(games_df)} games for {player['full_name']}")
        

        print("\nAvailable columns:")
        print(", ".join(games_df.columns.tolist()))
        

        print("\nSample game data:")
        sample_game = games_df.iloc[random.randint(0, len(games_df) - 1)]
        
        relevant_cols = [
            'GAME_ID', 'GAME_DATE', 'MATCHUP', 'WL', 
            'MIN', 'PTS', 'REB', 'AST', 'STL', 'BLK', 
            'TOV', 'PLUS_MINUS', 'FGM', 'FGA', 'FG3M', 'FG3A', 
            'FTM', 'FTA'
        ]
        
        # only show columns that exist in the dataframe
        cols_to_show = [col for col in relevant_cols if col in sample_game.index]
        
        for col in cols_to_show:
            print(f"  {col}: {sample_game[col]}")
        
        return sample_game
    
    def test_process_game_data(self, player_name=None, season="2024-25") -> bool:
        """Test the game data processing functionality"""
        print("\n----- Testing Game Data Processing -----")


        # get a game
        sample_game = self.test_game_api(player_name=player_name, season="2024-25")

        if sample_game is None:
            print("❌ test_game_api() failed!")
            return False    
        
        # Process the game data
        processed_data = self.ingestion.process_game_data(sample_game, season)
        
        if processed_data is None:
            print("❌ Failed to process game data")
            return False
        
        print("✅ Successfully processed game data")
        print("\nProcessed game fields:")
        
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
    
    def test_db_connection_and_schema(self) -> bool:
        """Test database connection and verify schema"""
        print("\n----- Testing Database Connection and Schema -----")
        
        try:
            # check if we can query the database
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
    
    def test_single_player_ingestion(self, player_name=None, season="2024-25", limit_games=5) -> bool:
        """Test the ingestion process for a single player with limited games"""
        print("\n----- Testing Single Player Ingestion Process -----")

        # an empty list evaluates to false in python
        if not self.test_player_api():
            print("❌ Failed to retrieve players to test single player ingestion")
            return False
        
        player_id = None
        
        # Get a player to test
        if player_name is None:
            print("Since no player name was specified in the command line arguments, I'm going to choose a random player from test_player_api() \n")

            player = random.choice(self.active_players)
            
            player_name = player['full_name']
            print(f"Selected player: {player['full_name']} (ID: {player_id})")
        else:
            player = next((p for p in self.active_players if p['full_name'].lower() == player_name.lower()), None)

            if player is None:
                print(f"❌ Failed to find {player_name} in the database. Please make sure your spelling is correct, including accents and capitalization!")
                return False
            
            print(f"Selected player: {player['full_name']} (ID: {player['id']})")
        
        player_id = player['id']

        print("\nStoring player in database...")
        self.ingestion.store_player_data(player)
        
        # Verify player was stored
        db_player = self.session.query(Player).filter_by(player_id=player_id).first()
        if not db_player:
            print("❌ Failed to store player in database")
            return False
        
        print(f"✅ {db_player.full_name} stored successfully: ")
        
        # Get games for the player
        print(f"\n Retrieving games for player from season {season}...")
        games_df = self.ingestion.get_player_games(player_id, season)
        
        if games_df is None or games_df.empty:
            print(f"❌ No games found for player ID {player_id} in season {season}")
            return False
        
        # head(<int n>) gives the first n rows 
        games_to_process = games_df.head(limit_games)
        print(f"✅ Retrieved {len(games_df)} games, will process {len(games_to_process)}")
        
        # Process and store each game
        successful_games = 0
        # iterrows() returns a generator that yields tuples, where the first item is the row index, and the second item is the row data as a Pandas Series.
        for _, game in games_to_process.iterrows(): # _ indicates we don't need to index, which iterrows returns 
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
        
        
        if db_stats:
            print("\nSample of stored game data:")
            sample_stat = db_stats[0]
            print(f"  Game ID: {sample_stat.game_id}")
            print(f"  Date: {sample_stat.game_date}")
            print(f"  Points: {sample_stat.points}")
            print(f"  Rebounds: {sample_stat.rebounds}")
            print(f"  Assists: {sample_stat.assists}")
        
        return successful_games > 0
    
    def verify_data_in_tables(self, player_name) -> bool:
        """Verify the data in the database tables"""
        print("\n----- Verifying Data in Database Tables -----")
        
        # Get stats for a specific player if provided
        if player_name:
            player = self.session.query(Player).filter_by(full_name=player_name).first()
            if not player:
                print(f"❌ {player_name} not found in database")
                return False
                        
            print(f"Found player: {player.full_name} (ID: {player.player_id})")
            
            stats = self.session.query(PlayerStats).filter_by(player_id=player.player_id).all()
            print(f"Found {len(stats)} game stats for this player")
            
            if stats:
                print("\nSeason breakdown:")
                stats_by_season = {}
                for stat in stats:
                    if stat.season not in stats_by_season:
                        stats_by_season[stat.season] = 0
                    stats_by_season[stat.season] += 1
                
                error = False

                for season, count in stats_by_season.items():
                    if count > 82:
                        print(f"  found {count} games in the {season} regular season. This is not possible!")
                        error = True
                    else:
                        print(f"  {season}: {count} games")

                if error:
                    print(f"❌ error in verifying table data")
                    return False
        else:
            print(f"❌ Please enter a player name! \n Add --player-name <PLAYER_NAME> to your arguments")
            return False
        
        return True
    
    def run_all_tests(self, player_name=None) -> None:
        """Run all tests"""
        print("=" * 60)
        print("RUNNING ALL NBA DATA INGESTION TESTS")
        print("=" * 60)
        
        # Define tests with their success conditions
        test_configs = [
            {
                "name": "Player API", 
                "func": self.test_player_api, 
                "args": [], 
                "success": lambda result: bool(result)
            },
            {
                "name": "Game API", 
                "func": self.test_game_api, 
                "args": [player_name], 
                "success": lambda result: result is not None
            },
            {
                "name": "Process Game Data", 
                "func": self.test_process_game_data, 
                "args": [player_name],
                "success": lambda result: bool(result)
            },
            {
                "name": "DB Connection", 
                "func": self.test_db_connection_and_schema, 
                "args": [], 
                "success": lambda result: bool(result)
            },
            {
                "name": "Single Player Ingestion", 
                "func": self.test_single_player_ingestion, 
                "args": [player_name], 
                "success": lambda result: bool(result)
            },
            {
                "name": "Verify Data", 
                "func": self.verify_data_in_tables, 
                "args": [player_name], 
                "success": lambda result: bool(result)
            }
        ]
        
        failed_tests = []

        success_count = 0
        
        for test in test_configs:
            try:
                # * is an unpacking operator. tells Python to unpack the list and pass each element as a separate argument
                result = test["func"](*test["args"]) # ex. test["func"] = self.test_game_api(player_name)
                if test["success"](result):
                    success_count += 1
                else:
                    failed_tests.append(test["name"])
            except Exception as e:
                print(f"❌ Test failed with exception: {e}")
        
        print("\n" + "=" * 60)
        print(f"TEST SUMMARY: {success_count}/{len(test_configs)} tests passed")
        print("Failed tests: ")
        print([test for test in failed_tests])
        print("=" * 60)
        return None
    
if __name__ == "__main__":
    
    parser = argparse.ArgumentParser(description="Test the NBA data ingestion process")
    parser.add_argument("--player-name", type=str, help="Specific player to test with identified by name")
    parser.add_argument("--test", choices=["all", "playerAPI", "gameAPI", "process", "db", "ingestion", "verify"], 
                        default="all", help="Specific test to run")
    parser.add_argument("--season", type=str, default="2024-25", help="Season to use for testing")
    
    # note that --help / -h are built in
    args = parser.parse_args()
    
    tester = TestNBAIngestion()


    try:
        if args.test == "all":
            tester.run_all_tests(player_name=args.player_name)
        elif args.test == "playerAPI":
            tester.test_player_api()
        elif args.test == "gameAPI":
            tester.test_game_api(player_name=args.player_name, season=args.season)
        elif args.test == "process":
            tester.test_process_game_data(player_name=args.player_name, season=args.season)
        elif args.test == "db":
            tester.test_db_connection_and_schema()
        elif args.test == "ingestion":
            tester.test_single_player_ingestion(player_name=args.player_name, season=args.season)
        elif args.test == "verify":
            tester.verify_data_in_tables(player_name=args.player_name)
    finally:
        tester.closeSession()
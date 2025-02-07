import os
import sys
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy_utils import database_exists, create_database
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import your models
from models.database import Base, Player, PlayerStats

def init_database():
    """Initialize the database and create all tables if they don't exist."""
    # Get database URL from environment variable
    DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://localhost:5432/nba_betting')
    
    try:
        # Create engine
        engine = create_engine(DATABASE_URL)
        
        # Create database if it doesn't exist
        if not database_exists(engine.url):
            logger.info(f"Creating database at {engine.url}")
            create_database(engine.url)
        
        # Create tables
        logger.info("Creating tables if they don't exist...")
        Base.metadata.create_all(engine)
        
        # Verify tables were created
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        logger.info("Created tables: " + ", ".join(tables))
        
        # Create a test session to verify connection
        Session = sessionmaker(bind=engine)
        session = Session()
        session.execute(text("SELECT 1"))  # Using text() for SQL expression
        session.close()
        
        logger.info("Database initialization completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        return False

def verify_tables():
    """Verify that all required tables exist and have the correct schema."""
    DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://localhost:5432/nba_betting')
    engine = create_engine(DATABASE_URL)
    inspector = inspect(engine)
    
    required_tables = {
        'players': {
            'id', 'player_id', 'full_name', 'is_active'
        },
        'player_stats': {
            'id', 'game_id', 'player_id', 'game_date', 'season',
            'is_home_game', 'minutes_played', 'points', 'assists',
            'rebounds', 'steals', 'blocks', 'turnovers', 'plus_minus',
            'fg_made', 'fg_attempted', 'fg3_made', 'fg3_attempted',
            'ft_made', 'ft_attempted'
        }
    }
    
    all_good = True
    
    for table, required_columns in required_tables.items():
        if table not in inspector.get_table_names():
            logger.error(f"Missing table: {table}")
            all_good = False
            continue
            
        columns = {c['name'] for c in inspector.get_columns(table)}
        missing_columns = required_columns - columns
        
        if missing_columns:
            logger.error(f"Table {table} is missing columns: {missing_columns}")
            all_good = False
    
    return all_good

if __name__ == "__main__":
    logger.info("Starting database initialization...")
    
    if init_database():
        logger.info("Verifying database schema...")
        if verify_tables():
            logger.info("Database setup completed successfully!")
            sys.exit(0)
        else:
            logger.error("Database schema verification failed!")
            sys.exit(1)
    else:
        logger.error("Database initialization failed!")
        sys.exit(1)
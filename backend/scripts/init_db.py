import os
import sys
from pathlib import Path
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy_utils import database_exists, create_database
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

script_dir = Path(__file__).resolve().parent  # .../backend/scripts
backend_dir = script_dir.parent               # .../backend
project_root = backend_dir.parent             # .../Sharpshooter Picks
sys.path.append(str(project_root))

from db_config import Base, engine  
from db_models.db_schema import Player, PlayerStats

def init_database():
    try:
        logger.info(f"Using database URL: {engine.url}")
        inspector = inspect(engine)
        tables_before = inspector.get_table_names()
        logger.info(f"Tables before drop: {tables_before}")
        
        logger.info("Dropping existing tables...")
        Base.metadata.drop_all(engine)

        inspector = inspect(engine)
        tables_after = inspector.get_table_names()
        logger.info(f"Tables after drop: {tables_after}")
        
        if not database_exists(engine.url):
            logger.info(f"Creating database at {engine.url}")
            create_database(engine.url)
        
        logger.info("Creating tables if they don't exist...")
        Base.metadata.create_all(engine)
        
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        logger.info("Created tables: " + ", ".join(tables))
        
        Session = sessionmaker(bind=engine)
        session = Session()
        session.execute(text("SELECT 1"))
        session.close()
        
        logger.info("Database initialization completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        return False

if __name__ == "__main__":
    if init_database():
        logger.info("Database is ready!")
    else:
        logger.error("Database initialization failed!")
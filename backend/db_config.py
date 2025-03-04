import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Default to localhost for local development
host = os.getenv('DB_HOST', 'localhost')

# Construct the database URL
DATABASE_URL = f'postgresql://postgres:postgres@{host}:5432/nba_betting'

engine = create_engine(DATABASE_URL)
Base = declarative_base()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
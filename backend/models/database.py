# sqlalchemy simply provides a Python interface to interact with PostgreSQL
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean
from sqlalchemy.orm import declarative_base
import os

DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://localhost:5432/nba_betting')
engine = create_engine(DATABASE_URL)
Base = declarative_base()

# use Python classes instead of directly using SQL to create tables
class Player(Base):
    # __tablename__ is used by SQLAlchemy to create the table name
    __tablename__ = 'players'
    
    id = Column(Integer, primary_key=True)
    player_id = Column(Integer, unique=True)
    full_name = Column(String)
    is_active = Column(Boolean, default=True)

class PlayerStats(Base):
    __tablename__ = 'player_stats'
    
    id = Column(Integer, primary_key=True)
    game_id = Column(String)
    player_id = Column(Integer)
    game_date = Column(DateTime)
    season = Column(String)
    is_home_game = Column(Boolean)
    minutes_played = Column(String)
    points = Column(Integer)
    assists = Column(Integer)
    rebounds = Column(Integer)
    steals = Column(Integer)
    blocks = Column(Integer)
    turnovers = Column(Integer)
    plus_minus = Column(Integer)
    fg_made = Column(Integer)
    fg_attempted = Column(Integer)
    fg3_made = Column(Integer)
    fg3_attempted = Column(Integer)
    ft_made = Column(Integer)
    ft_attempted = Column(Integer)
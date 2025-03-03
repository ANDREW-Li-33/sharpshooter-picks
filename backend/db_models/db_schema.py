from sqlalchemy import Column, Integer, String, DateTime, Boolean, UniqueConstraint
from backend.db_config import Base

class Player(Base):
    __tablename__ = 'players'
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    player_id = Column(Integer, unique=True)
    full_name = Column(String)
    is_active = Column(Boolean, default=True)

class PlayerStats(Base):
    __tablename__ = 'player_stats'
    __table_args__ = (
        UniqueConstraint('player_id', 'game_id', name='uix_player_game'),
        {'extend_existing': True}
    )

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

import matplotlib.pyplot as plt
import pandas as pd
from sqlalchemy.orm import Session
from models.database import PlayerStats, engine

def plot_player_points(player_id):
    # Open a session and load the data for the given player
    with Session(engine) as session:
        query = session.query(PlayerStats).filter(PlayerStats.player_id == player_id)
        df = pd.read_sql(query.statement, session.bind)

    if df.empty:
        print(f"No data found for player {player_id}")
        return

    # Ensure the game_date column is in datetime format and sort by date
    df['game_date'] = pd.to_datetime(df['game_date'])
    df = df.sort_values('game_date')

    # Plotting the points over time
    plt.figure(figsize=(10, 6))
    plt.plot(df['game_date'], df['points'], marker='o', linestyle='-', color='blue')
    plt.title(f'Points Over Time for Player {player_id}')
    plt.xlabel('Game Date')
    plt.ylabel('Points')
    plt.grid(True)
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    plot_player_points(1626164)

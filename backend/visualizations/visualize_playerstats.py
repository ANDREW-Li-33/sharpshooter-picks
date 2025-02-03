import pandas as pd
from IPython.display import HTML, display
from sqlalchemy.orm import Session
from models.database import Player, PlayerStats, engine

def display_player_table(player_id):
    with Session(engine) as session:
        query = session.query(PlayerStats).filter(PlayerStats.player_id == player_id)
        df = pd.read_sql(query.statement, session.bind)
        player_info = session.query(Player).filter(Player.player_id == player_id).first()
        player_name = player_info.full_name if player_info else f"Player {player_id}"

    if df.empty:
        print(f"No data found for {player_name}")
        return

    df['game_date'] = pd.to_datetime(df['game_date'])
    df = df.sort_values('game_date')

    html_table = df.to_html(index=False, justify='center')
    html_code = f"""
        <h3>Data Entries for {player_name}</h3>
        <div style="max-height: 500px; overflow-y: auto; border: 1px solid #ccc;">
            {html_table}
        </div>
    """

    # Save HTML to a file
    with open("visualizations/outputs/player_table.html", "w") as file:
        file.write(html_code)
    print("HTML table saved to player_table.html. Open this file in your browser to view the table.")


if __name__ == "__main__":
    display_player_table(1626164)

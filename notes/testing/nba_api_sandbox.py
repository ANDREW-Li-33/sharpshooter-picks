from nba_api.stats.static import players
from nba_api.stats.endpoints import leaguegamefinder
import pandas as pd

# Step 1: Get active players and select one.
active_players = players.get_active_players()

king_james = [player for player in active_players if player['full_name'] == "LeBron James"][0]
player_id = king_james['id']
print(f"Selected Player: {king_james['full_name']} (ID: {player_id})")

# Step 2: Retrieve games for the player.
# We omit the date filter and allow games from multiple seasons.
gamefinder = leaguegamefinder.LeagueGameFinder(
    player_or_team_abbreviation="P",
    player_id_nullable=player_id
)
games_df = gamefinder.get_data_frames()[0]
print(f"Found {len(games_df)} games for {king_james['full_name']}.")

# Step 3: Filter to the last five NBA seasons.
# (Adjust this logic depending on how the season is formatted in your DataFrame.)
#
# For example, if SEASON_ID is a string like "22017" (where the last 2-4 digits indicate the season year),
# you can extract the season portion. In some datasets, the last 4 characters represent the ending year
# (e.g., "2017" for the 2016-17 season). Here, we assume that is the case.

# First, ensure the SEASON_ID column is a string.
games_df['SEASON_ID'] = games_df['SEASON_ID'].astype(str)

# Extract the last four characters as the "season end year" (e.g., "2017" from "22017").
games_df['season_end_year'] = games_df['SEASON_ID'].str[-4:]

# Get a sorted list of unique season end years in descending order.
unique_seasons = sorted(games_df['season_end_year'].unique(), reverse=True)
print("Unique season end years found:", unique_seasons)

# Select the five most recent seasons.
last_five_seasons = unique_seasons[:5]
print("Filtering to seasons ending in:", last_five_seasons)

# Filter the games DataFrame to only include rows from these seasons.
games_last5 = games_df[games_df['season_end_year'].isin(last_five_seasons)]
print(f"Found {len(games_last5)} games in the last five seasons for {king_james['full_name']}.")

# Optionally, display a few columns.
print(games_last5[['GAME_ID', 'GAME_DATE', 'MATCHUP', 'season_end_year']].head())

# Step 4: Retrieve Box Score Stats for each game.
# For each unique game_id, use the BoxScore endpoint.
from nba_api.live.nba.endpoints.boxscore import BoxScore

boxscore_stats = {}
for game_id in games_last5['GAME_ID'].unique():
    try:
        box = BoxScore(game_id=game_id)
        # BoxScore returns a list of DataFrames (e.g., one for each team or for play-by-play)
        box_dfs = box.get_data_frames()
        boxscore_stats[game_id] = box_dfs
    except Exception as e:
        print(f"Error retrieving box score for game {game_id}: {e}")

print(f"Retrieved box score data for {len(boxscore_stats)} games.")

# (Optional) Display sample box score data for one game.
sample_game_id = list(boxscore_stats.keys())[0]
print(f"\nSample box score data for game {sample_game_id}:")
for idx, df in enumerate(boxscore_stats[sample_game_id]):
    print(f"\nDataFrame {idx}:")
    print(df.head())

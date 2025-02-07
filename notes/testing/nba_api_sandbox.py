from nba_api.stats.static import players
from nba_api.stats.endpoints import leaguegamefinder
import pandas as pd
import random

# Step 1: get active players and select one
active_players = players.get_active_players()

king_james = [player for player in active_players if player['full_name'] == "Jayson Tatum"][0]
player_id = king_james['id']
print(f"Selected Player: {king_james['full_name']} (ID: {player_id})")

# Step 2: retrieve games for the player

seasons = [
   "2024-25",
   "2023-24",
   "2022-23", 
   "2021-22",
   "2020-21"
]

for season in seasons:

    gamefinder = leaguegamefinder.LeagueGameFinder(
        player_or_team_abbreviation="P",
        player_id_nullable=player_id,
        season_type_nullable="Regular Season",
        season_nullable=season
    ) 

    # converts gamefinder into a pandas dataframe
    games_df = gamefinder.get_data_frames()[0]

    print(games_df.head()) # first 5 rows
    print(games_df.columns) # gives column labels (ex. plyer names, points scored)
    print(games_df.index) # gives row index
    print(games_df.index.tolist()) 

    season_id = games_df['SEASON_ID'].iloc[0]  # '22019'
    year = int(season_id[1:])  # 2019
    formatted_year = f"{year}-{str(year+1)[2:]}" # '2019-20'

    print(f"Found {len(games_df)} games for {king_james['full_name']} during the {formatted_year} regular season.")

minimum_season = 0
max_season = len(seasons) - 1
random_season = seasons[random.randint(minimum_season, max_season)]

print(random_season)

gamefinder = leaguegamefinder.LeagueGameFinder(
    player_or_team_abbreviation="P",
    player_id_nullable=player_id,
    season_type_nullable="Regular Season",
    season_nullable=random_season
)

games_df = gamefinder.get_data_frames()[0]

cols_to_describe = [col for col in games_df.columns if col != "TEAM_ID"]
print(games_df[cols_to_describe].describe())

print(games_df['MIN'])
print(games_df.iloc[1]) # (integer location) accesses the second row

# games_df = gamefinder.get_data_frames()[0]

# minimum_game = 0
# maximum_game = len(games_df) - 1 # number of total games played that season
# random_game = games_df.iloc[random.randint(minimum_game, maximum_game)]
# print(random_game)




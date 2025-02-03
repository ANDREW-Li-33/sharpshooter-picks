![package structure](images/image.png)


##### finding all active players
- from nba_api.stats.static import players
- players._get_active_players()
```JSON
    player = {
        'id': player_id,
        'full_name': full_name,
        'first_name': first_name,
        'last_name': last_name,
        'is_active': True or False
    }
``` 



##### finding all games a certain player has played within the last 5 years
- 
accessing basic box score stats for each game that player has played






#### finding a game
##### nba_api -> live -> endpoints
- [BoxScore](https://github.com/swar/nba_api/blob/master/docs/nba_api/live/endpoints/boxscore.md)


###### nba_api -> stats -> endpoints
- [CumeStatsPlayerGames](https://github.com/swar/nba_api/blob/master/docs/nba_api/stats/endpoints/cumestatsplayergames.md)
- [LeagueGameFinder](https://github.com/swar/nba_api/blob/master/docs/nba_api/stats/endpoints/leaguegamefinder.md)
can be used to retrieve every game a player has played 
    ```python
    gamefinder = leaguegamefinder.LeagueGameFinder(
        player_or_team_abbreviation="P",
        player_id_nullable=player_id
    )   
    ```

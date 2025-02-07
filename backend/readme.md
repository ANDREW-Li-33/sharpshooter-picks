## <u> backend </u>

### backend structure

backend/  
├── models/  
│   └── database.py        
├── scripts/  
│   └── ingest_historical_stats.py  
├── visualizations/  
│   ├── outputs/          
│   └── visualize_playerstats.py    
├── app.py  
├── dockerfile                 
├── init_db.py                   
└── requirements.txt     
<hr>

### <u>database.py </u>
defines the SQLAlchemy ORM models for the player stats database

ORM (Object-Relational Mapping) models allow us to interact with database records with Python objects without writing SQL queries

example:  
instead of 
```sql 
SELECT * FROM players WHERE player_id = 123;
```
we can write
```python
player = Player.query.filter_by(player_id=123).first()
```
<hr>

### <u>  ingest_historical_stats.py </u>
fetches and stores player statistics from the last 5 regular seasons making calls to [nba_api](https://github.com/swar/nba_api) (created by [swar](https://github.com/swar))

- comprehensive logging functionality
- batch processing with rate limiting  

#### Core components
##### NBADataIngestion

- Manages player data retrieval and processing
- Implements session management

##### Database Storage

- table ```players```: basic player information  
- table ```player_stats```: per-game statistics for each player


<hr>


### <u> init_db.py </u>
Initializes PostgreSQL database for the app

- Sets up required tables and schema
- database configuration verification
- detailed logging


#### Database Schema
<u>Players Table</u>

```properties
id: Primary key
player_id: Unique NBA ID
full_name: Player name
is_active: Active status
```


<u> PlayerStats Table </u>

```properties
id: Primary key
game_id: Game identifier
player_id: Foreign key to Players
game_date: DateTime
season: String
is_home_game: Boolean
minutes_played: String
points: Integer
assists: Integer
rebounds: Integer
steals: Integer
blocks: Integer
turnovers: Integer
plus_minus: Integer
fg_made: Integer
fg_attempted: Integer
fg3_made: Integer
fg3_attempted: Integer
ft_made: Integer
ft_attempted: Integer
```
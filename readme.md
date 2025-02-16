# Welcome to Sharpshooter Picks! 
<hr>

## Description:
**Sharpshooter Picks** 🏀 is a full stack web-app built for selecting the **best NBA player proposition bets** using **Machine Learning**.
Models are trained on [nba_api](https://github.com/swar/nba_api)  and picks are found using [odds-api](https://the-odds-api.com/).


Users can also individually choose from the most popular bookmakers, including DraftKings, Fanduel, and BetMGM

<hr>

## 🛠️ Tech Stack

### Frontend

- Framework: Next.js (React)
- UI Components:
  - shadcn/ui components
  - Radix UI primitives
  - Lucide React icons


- Styling: Tailwind CSS
- Data Fetching: Native fetch API with interval updates

### Backend

- Framework: Flask (Python)
- Database: PostgreSQL with SQLAlchemy ORM
- Data Sources:
  - NBA API for historical player statistics
  - The Odds API for live betting odds


- Machine Learning: PyTorch

- Key Libraries:
  - pandas
  - numpy
  - requests
  - python-dotenv



### DevOps

- Containerization: Docker / Docker Compose
- Repomix (converts the entire project into a .txt file)
    - from the root directory, run ```repomix --ignore "frontend/node_modules/**,frontend/.next/**,player_stats.csv,players.csv"```

<hr>


## 📊 Data Pipeline

1. Gather all currently active players from nba_api (One time)
2. For each player, gather stats for every game for that player within the last 5 years (One time)
3. Machine learning model training (One time)
4. Real time fetching of  player proposition bets for the day from all bookmakers listed in odds-api that support player prop betting 
5. Confidence score calculation, calculates which bets have the highest chance of hitting
6. Frontend displays bets with the highest confidence score and updates 


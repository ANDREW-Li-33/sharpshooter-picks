# Welcome to Sharpshooter Picks! 
<hr>

## Description:
**Sharpshooter Picks** 🏀 is a full stack web-app built for selecting the **best NBA player proposition bets** using **Machine Learning**.
Models are trained on [nba_api](https://github.com/swar/nba_api)  and picks are found using [odds-api](https://the-odds-api.com/).


<hr>

## Tech Stack
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



### Frontend

- Framework: Next.js (React)
- UI Components:
  - shadcn/ui components
  - Radix UI primitives
  - Lucide React icons


- Styling: Tailwind CSS
- Data Fetching: Native fetch API with interval updates

### DevOps

- Containerization: Docker / Docker Compose
- Repomix (converts the entire project into a .txt file)
    - from the root directory, run ```repomix --ignore "frontend/node_modules/**,frontend/.next/**,player_stats.csv,players.csv"```

<hr>



from flask import Flask, jsonify
from flask_cors import CORS # allows frontend to make request to the server
import requests
from datetime import datetime
import os
from dotenv import load_dotenv  

load_dotenv()  # loads environment variables from .env file

app = Flask(__name__) # initialize Flask application, __name__ represents the name of the current module
CORS(app) # enables Cross-Origin Resource Sharing, allow requests from different origins


API_KEY = os.getenv('ODDS_API_KEY')
if not API_KEY: # if API_KEY is empty or falsy
    raise ValueError("Missing ODDS_API_KEY environment variable. Make sure you have a .env file with this value.")

BASE_URL = "https://api.the-odds-api.com/v4"

def calculate_confidence(odds):
    """
    Calculate confidence score based on betting odds.
    Returns a value between 0 and 1.
    """
    try:
        if odds > 0:
            probability = 100 / (odds + 100)
        else:
            probability = abs(odds) / (abs(odds) + 100)
        return round(probability, 3)
    except (TypeError, ZeroDivisionError):
        return None

# decorator, get_picks() will run when a HTTP request hits the server with the path "/api/picks", return value is sent back to client
@app.route("/api/picks", methods=["GET"]) # methods=["GET"] is not necssary since it is the default HTTP method, included for clarity
def get_picks():
    try:
        response = requests.get(
            # f-string
            f"{BASE_URL}/sports/basketball_nba/odds",
            params={
                "apiKey": API_KEY,
                "regions": "us",
                "markets": "h2h",
                "oddsFormat": "american"
            }
        )

        if response.status_code != 200: # 200 indicates a successful request
            print(f"API Error: {response.status_code}", response.text)
            # HTTP status code for the response, 500 indicates Internal Server Error
            return jsonify({"error": "Failed to fetch from Odds API"}), 500
            
        games = response.json()
        processed_games = []
        
        for idx, game in enumerate(games):
            try:
                # Skip games without odds data
                if not game.get('bookmakers'):
                    continue
                    
                bookmaker = game['bookmakers'][0]
                odds = bookmaker['markets'][0]['outcomes']
                
                # Find home and away team odds
                home_odds = None
                away_odds = None
                for odd in odds:
                    if odd['name'] == game['home_team']:
                        home_odds = odd['price']
                        break

                for odd in odds:
                    if odd['name'] == game['away_team']:
                        away_odds = odd['price']
                        break
                
                if home_odds is None or away_odds is None:
                    continue
                
                # Calculate confidence scores
                home_confidence = calculate_confidence(home_odds)
                away_confidence = calculate_confidence(away_odds)
                
                if home_confidence is None or away_confidence is None:
                    continue
                
                # Determine prediction
                if home_confidence > away_confidence:
                    predicted_winner = game['home_team']
                    confidence = home_confidence
                else:
                    predicted_winner = game['away_team']
                    confidence = away_confidence

                processed_games.append({
                    "id": str(idx + 1),
                    "team": game['home_team'],
                    "opponent": game['away_team'],
                    "prediction": f"{predicted_winner} Win",
                    "confidence": confidence,
                    "start_time": game['commence_time'],
                    "odds": {
                        "home_odds": home_odds,
                        "away_odds": away_odds
                    }
                })
                
            except Exception as e:
                print(f"Error processing game {idx}: {str(e)}")
                continue
        
        return jsonify(processed_games)

    except requests.exceptions.RequestException as e:
        print(f"Request error: {str(e)}")
        return jsonify({"error": "Failed to fetch game data"}), 500
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return jsonify({"error": "An unexpected error occurred"}), 500
    

@app.route("/api/props", methods=["GET"])
def get_player_props():
    try:
        # Get all NBA games
        games_response = requests.get(
            f"{BASE_URL}/sports/basketball_nba/events",
            params={
                "apiKey": API_KEY
            }
        )
        
        if games_response.status_code != 200:
            print(f"Games API Error: {games_response.status_code}", games_response.text)
            return jsonify({"error": "Failed to fetch games"}), 500
            
        games = games_response.json()
        processed_props = []
        
        # For each game, get player props
        for game in games:
            try:
                props_response = requests.get(
                    f"{BASE_URL}/sports/basketball_nba/events/{game['id']}/odds",
                    params={
                        "apiKey": API_KEY,
                        "regions": "us",
                        "markets": "player_points,player_rebounds,player_assists",
                        "oddsFormat": "american",
                        "bookmakers": "draftkings"
                    }
                )
                
                if props_response.status_code != 200:
                    continue
                    
                props_data = props_response.json()
                
                # Process bookmaker data
                if not props_data.get('bookmakers'):
                    continue
                    
                bookmaker = props_data['bookmakers'][0]  # DraftKings
                
                for market in bookmaker['markets']:
                    for outcome in market['outcomes']:
                        confidence = calculate_confidence(outcome['price'])
                        if confidence is None:
                            continue
                            
                        processed_props.append({
                            "id": f"{game['id']}-{market['key']}-{outcome['name']}",
                            "game": f"{game['home_team']} vs {game['away_team']}",
                            "start_time": game['commence_time'],
                            "name": outcome['name'], 
                            "player": outcome['description'],
                            "market": market['key'].replace('player_', '').title(),
                            "line": outcome['point'],
                            "odds": outcome['price'],
                            "confidence": confidence
                        })
                        
            except Exception as e:
                print(f"Error processing props for game {game['id']}: {str(e)}")
                continue

        # Sort by confidence descending
        processed_props.sort(key=lambda x: x['confidence'], reverse=True)
        
        # Return top 10 most confident props
        return jsonify(processed_props[:10])

    except requests.exceptions.RequestException as e:
        print(f"Request error: {str(e)}")
        return jsonify({"error": "Failed to fetch prop data"}), 500
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return jsonify({"error": "An unexpected error occurred"}), 500

if __name__ == "__main__": # starts the Flask Development Server
    app.run(debug=True, host='0.0.0.0')
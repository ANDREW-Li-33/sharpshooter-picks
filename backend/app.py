from flask import Flask, jsonify
from flask_cors import CORS
import requests
from datetime import datetime
import os

app = Flask(__name__)
CORS(app)

API_KEY = "ed1a2b920da4501697efc5b43a5407e4"
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

@app.route("/api/picks", methods=["GET"])
def get_picks():
    try:
        # Fetch NBA games with odds
        response = requests.get(
            f"{BASE_URL}/sports/basketball_nba/odds",
            params={
                "apiKey": API_KEY,
                "regions": "us",
                "markets": "h2h",
                "oddsFormat": "american"
            }
        )
        
        if response.status_code != 200:
            print(f"API Error: {response.status_code}", response.text)
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
                home_odds = next((odd['price'] for odd in odds if odd['name'] == game['home_team']), None)
                away_odds = next((odd['price'] for odd in odds if odd['name'] == game['away_team']), None)
                
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

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0')
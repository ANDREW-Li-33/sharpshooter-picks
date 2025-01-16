from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route("/")
def home():
    return "Welcome to NBA Betting Generator"

@app.route("/api/picks", methods=["GET"])
def get_picks():
    try:
        # Placeholder data - replace with actual database query
        picks = [
            {"id": 1, "team": "Lakers", "opponent": "Celtics", "prediction": "Win", "confidence": 0.85},
            {"id": 2, "team": "Warriors", "opponent": "Suns", "prediction": "Win", "confidence": 0.75}
        ]
        return jsonify(picks)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
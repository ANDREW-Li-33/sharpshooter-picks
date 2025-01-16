import { useState, useEffect } from 'react';

export default function TopPicks({ onGameSelect }) {
    // State to store our game data and loading status
    const [games, setGames] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState(null);

    // Fetch game data when the component mounts
    useEffect(() => {
        async function fetchGames() {
            try {
                // We'll connect this to your backend API later
                const response = await fetch('http://localhost:5001/api/picks');
                if (!response.ok) {
                    throw new Error('Failed to fetch games');
                }
                const data = await response.json();
                setGames(data);
            } catch (err) {
                setError(err.message);
            } finally {
                setIsLoading(false);
            }
        }

        fetchGames();
    }, []); // Empty dependency array means this runs once when component mounts

    // Show loading state while fetching data
    if (isLoading) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
            </div>
        );
    }

    // Show error state if something went wrong
    if (error) {
        return (
            <div className="text-red-500 p-4 rounded-lg bg-red-50">
                Error loading games: {error}
            </div>
        );
    }

    // Calculate win probability color based on confidence
    function getConfidenceColor(confidence) {
        if (confidence >= 0.7) return 'text-green-600';
        if (confidence >= 0.5) return 'text-yellow-600';
        return 'text-red-600';
    }

    return (
        <div className="space-y-4">
            {games.map((game) => (
                <div
                    key={game.id}
                    className="border rounded-lg p-4 hover:shadow-lg transition-shadow cursor-pointer"
                    onClick={() => onGameSelect(game)}
                >
                    {/* Game matchup header */}
                    <div className="flex justify-between items-center mb-2">
                        <h3 className="text-lg font-medium">{game.team} vs {game.opponent}</h3>
                        <span className={`font-bold ${getConfidenceColor(game.confidence)}`}>
                            {(game.confidence * 100).toFixed(1)}%
                        </span>
                    </div>

                    {/* Prediction details */}
                    <div className="mt-2 text-sm text-gray-600">
                        <p>Prediction: <span className="font-medium">{game.prediction}</span></p>
                        
                        {/* Key factors that influenced the prediction */}
                        <div className="mt-2">
                            <p className="text-xs text-gray-500">Key Factors:</p>
                            <ul className="list-disc list-inside text-xs pl-2">
                                <li>Recent team performance</li>
                                <li>Head-to-head history</li>
                                <li>Player availability</li>
                            </ul>
                        </div>
                    </div>
                </div>
            ))}

            {/* Show message if no games are available */}
            {games.length === 0 && (
                <div className="text-gray-500 text-center py-8">
                    No games available for today
                </div>
            )}
        </div>
    );
}
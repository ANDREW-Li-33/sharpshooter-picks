import { useState, useEffect } from 'react';

export default function TopPicks({ onGameSelect }) {
    const [games, setGames] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const fetchGames = async () => {
            try {
                const response = await fetch('http://localhost:5001/api/picks');
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                const data = await response.json();
                setGames(data);
            } catch (e) {
                setError('Failed to load picks: ' + e.message);
            } finally {
                setIsLoading(false);
            }
        };

        fetchGames();
        // Refresh data every 5 minutes
        const interval = setInterval(fetchGames, 300000);
        return () => clearInterval(interval);
    }, []);

    const formatDate = (dateString) => {
        return new Date(dateString).toLocaleString('en-US', {
            weekday: 'short',
            month: 'short',
            day: 'numeric',
            hour: 'numeric',
            minute: '2-digit'
        });
    };

    // Format odds for display
    const formatOdds = (odds) => {
        return odds > 0 ? `+${odds}` : odds;
    };

    if (isLoading) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="text-red-500 p-4 rounded-lg bg-red-50">
                {error}
            </div>
        );
    }

    return (
        <div className="space-y-4">
            {games.map((game) => (
                <div
                    key={game.id}
                    className="border rounded-lg p-4 hover:shadow-lg transition-shadow cursor-pointer bg-white"
                    onClick={() => onGameSelect(game)}
                >
                    {/* Game Header */}
                    <div className="flex justify-between items-center mb-2">
                        <div>
                            <h3 className="text-lg font-medium">
                                {game.team} vs {game.opponent}
                            </h3>
                            <p className="text-sm text-gray-500">
                                {formatDate(game.start_time)}
                            </p>
                        </div>
                        <div className="text-right">
                            <span className={`text-lg font-bold ${
                                game.confidence > 0.7 ? 'text-green-600' : 
                                game.confidence > 0.5 ? 'text-yellow-600' : 
                                'text-red-600'
                            }`}>
                                {(game.confidence * 100).toFixed(1)}%
                            </span>
                        </div>
                    </div>

                    {/* Prediction & Odds */}
                    <div className="mt-2 space-y-2">
                        <div className="flex justify-between text-sm">
                            <span className="text-gray-600">Prediction:</span>
                            <span className="font-medium">{game.prediction}</span>
                        </div>
                        <div className="flex justify-between text-sm">
                            <span className="text-gray-600">Odds:</span>
                            <span>
                                {game.team}: {formatOdds(game.odds.home)} | {game.opponent}: {formatOdds(game.odds.away)}
                            </span>
                        </div>
                    </div>
                </div>
            ))}

            {games.length === 0 && (
                <div className="text-gray-500 text-center py-8">
                    No games available at the moment
                </div>
            )}
        </div>
    );
}
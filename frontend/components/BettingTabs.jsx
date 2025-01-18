import { useState, useEffect } from 'react';
import * as Tabs from '@radix-ui/react-tabs';

export default function BettingTabs() {
    const [propsData, setPropsData] = useState([]);
    const [games, setGames] = useState([]);

    const [isLoadingProps, setIsLoadingProps] = useState(true);
    const [isLoadingGames, setIsLoadingGames] = useState(true);

    const [error, setError] = useState(null);

    useEffect(() => {
        const fetchProps = async () => {
            try {
                const response = await fetch('http://localhost:5001/api/props');
                if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
                const data = await response.json();
                setPropsData(data);
            } catch (e) {
                setError('Failed to load props: ' + e.message);
            } finally {
                setIsLoadingProps(false);
            }
        };

        const fetchGames = async () => {
            try {
                const response = await fetch('http://localhost:5001/api/picks');
                if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
                const data = await response.json();
                setGames(data);
            } catch (e) {
                setError('Failed to load games: ' + e.message);
            } finally {
                setIsLoadingGames(false);
            }
        };

        fetchProps();
        fetchGames();

        // Refresh data every 5 minutes
        const interval = setInterval(() => {
            fetchProps();
            fetchGames();
        }, 300000);

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

    const formatOdds = (odds) => (odds > 0 ? `+${odds}` : odds);

    return (
        <Tabs.Root defaultValue="games" className="w-full">
            {/* --- Tabs List --- */}
            <Tabs.List className="flex border-b border-gray-200">
                <Tabs.Trigger 
                    value="games" 
                    className="px-4 py-2 text-sm font-medium text-gray-600 hover:text-gray-900 cursor-pointer border-b-2 border-transparent data-[state=active]:border-blue-500 data-[state=active]:text-blue-600"
                >
                    Game Lines
                </Tabs.Trigger>
                <Tabs.Trigger 
                    value="props"
                    className="px-4 py-2 text-sm font-medium text-gray-600 hover:text-gray-900 cursor-pointer border-b-2 border-transparent data-[state=active]:border-blue-500 data-[state=active]:text-blue-600"
                >
                    Player Props
                </Tabs.Trigger>
            </Tabs.List>

            {/* --- GAMES TAB CONTENT --- */}
            <Tabs.Content value="games" className="mt-4">
                {isLoadingGames ? (
                    <div className="flex items-center justify-center h-64">
                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
                    </div>
                ) : error ? (
                    <div className="text-red-500 p-4 rounded-lg bg-red-50">
                        {error}
                    </div>
                ) : (
                    <div className="space-y-4">
                        {games.map((game) => (
                            <div key={game.id} className="border rounded-lg p-4 hover:shadow-lg transition-shadow bg-white">
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

                                <div className="mt-2 space-y-2">
                                    <div className="flex justify-between text-sm">
                                        <span className="text-gray-600">Prediction:</span>
                                        <span className="font-medium">{game.prediction}</span>
                                    </div>
                                    <div className="flex justify-between text-sm">
                                        <span className="text-gray-600">Odds:</span>
                                        <span>
                                            {game.team}: {formatOdds(game.odds.home_odds)} | {game.opponent}: {formatOdds(game.odds.away_odds)}
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
                )}
            </Tabs.Content>

            {/* --- PROPS TAB CONTENT --- */}
            <Tabs.Content value="props" className="mt-4">
                {isLoadingProps ? (
                    <div className="flex items-center justify-center h-64">
                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
                    </div>
                ) : error ? (
                    <div className="text-red-500 p-4 rounded-lg bg-red-50">
                        {error}
                    </div>
                ) : (
                    <div className="space-y-4">
                        {propsData.map((prop) => (
                            <div
                                key={prop.id}
                                className="border rounded-lg p-4 hover:shadow-lg transition-shadow bg-white"
                            >
                                <div className="flex justify-between items-center mb-2">
                                    <div>
                                        <h3 className="text-lg font-medium">{prop.player}</h3>
                                        <p className="text-sm text-gray-500">
                                            {prop.game}
                                        </p>
                                        <p className="text-sm text-gray-500">
                                            {formatDate(prop.start_time)}
                                        </p>
                                    </div>
                                    <div className="text-right">
                                        <span
                                            className={`text-lg font-bold ${
                                                prop.confidence > 0.7
                                                    ? 'text-green-600'
                                                    : prop.confidence > 0.5
                                                    ? 'text-yellow-600'
                                                    : 'text-red-600'
                                            }`}
                                        >
                                            {(prop.confidence * 100).toFixed(1)}%
                                        </span>
                                    </div>
                                </div>

                                <div className="mt-2 space-y-1 text-sm">
                                    <div className="flex justify-between">
                                        <span className='text-gray-600'>
                                            Over/Under:
                                        </span>
                                        <span className='font-medium'>
                                            {prop.name}
                                        </span> 
                                    </div>
                                    <div className="flex justify-between">
                                        <span className="text-gray-600">
                                            Market:
                                        </span>
                                        <span className="font-medium">
                                            {prop.market} ({prop.line})
                                        </span>
                                    </div>
                                    <div className="flex justify-between">
                                        <span className="text-gray-600">
                                            Odds:
                                        </span>
                                        <span>
                                            {formatOdds(prop.odds)}
                                        </span>
                                    </div>
                                </div>
                            </div>
                        ))}

                        {propsData.length === 0 && (
                            <div className="text-gray-500 text-center py-8">
                                No player props available at the moment
                            </div>
                        )}
                    </div>
                )}
            </Tabs.Content>
        </Tabs.Root>
    );
}

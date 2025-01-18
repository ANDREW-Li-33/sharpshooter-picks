import { useState } from 'react';
import BettingTabs from '../components/BettingTabs';

export default function Home() {
    const [selectedGame, setSelectedGame] = useState(null);

    return (
        <div className="min-h-screen bg-gray-50">
            <header className="bg-white shadow">
                <div className="max-w-7xl mx-auto py-6 px-4">
                    <h1 className="text-3xl font-bold text-gray-900">
                        NBA Betting Generator
                    </h1>
                </div>
            </header>

            <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
                <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
                    {/* Left column: Betting Tabs */}
                    <div className="bg-white shadow rounded-lg p-6">
                        <BettingTabs />
                    </div>

                    {/* Right column: Detailed Analysis */}
                    <div className="bg-white shadow rounded-lg p-6">
                        <h2 className="text-xl font-semibold mb-4">Detailed Analysis</h2>
                        {selectedGame ? (
                            <div className="space-y-4">
                                <h3 className="text-lg font-medium">
                                    {selectedGame.team} vs {selectedGame.opponent}
                                </h3>
                                <p>Detailed analysis coming soon...</p>
                            </div>
                        ) : (
                            <p className="text-gray-500">Select a game to view detailed analysis</p>
                        )}
                    </div>
                </div>
            </main>
        </div>
    );
}
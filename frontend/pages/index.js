import BettingDashboard from '../components/BettingDashboard';

export default function Home() {
    return (
        <div className="min-h-screen bg-gray-50">
            <header className="bg-white shadow">
                <div className="max-w-7xl mx-auto py-6 px-4">
                    <h1 className="text-3xl font-bold text-gray-900">
                        NBA Betting Dashboard
                    </h1>
                </div>
            </header>

            <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
                <BettingDashboard />
            </main>
        </div>
    );
}
import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { AlertCircle, TrendingUp, DollarSign } from 'lucide-react';

const BettingDashboard = () => {
  // State to hold betting data for different categories
  const [bets, setBets] = useState({
    overall: [],
    draftkings: [],
    fanduel: []
  });
  // Loading state to indicate if data is being fetched
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Simulate fetching betting data (replace with real API calls)
    const fetchBets = async () => {
      try {
        setIsLoading(true);
        // Simulate API delay
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        // Mock data for demonstration purposes
        const mockData = {
          overall: [
            {
              id: 1,
              game: "Celtics vs Lakers",
              pick: "Celtics -5.5",
              odds: -110,
              confidence: 0.85,
              time: "7:30 PM ET",
              book: "DraftKings"
            },
            {
              id: 2,
              game: "Warriors vs Suns",
              pick: "Over 235.5",
              odds: -105,
              confidence: 0.82,
              time: "10:00 PM ET",
              book: "FanDuel"
            }
          ],
          draftkings: [
            {
              id: 3,
              game: "Celtics vs Lakers",
              pick: "Celtics -5.5",
              odds: -110,
              confidence: 0.85,
              time: "7:30 PM ET"
            }
          ],
          fanduel: [
            {
              id: 4,
              game: "Warriors vs Suns",
              pick: "Over 235.5",
              odds: -105,
              confidence: 0.82,
              time: "10:00 PM ET"
            }
          ]
        };
        
        // Update state with the fetched (or mocked) data
        setBets(mockData);
      } catch (error) {
        console.error('Error fetching bets:', error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchBets();
  }, []);

  // Component to render an individual bet card
  const BetCard = ({ bet }) => (
    <Card className="mb-4 hover:shadow-lg transition-shadow">
      <CardContent className="pt-6">
        {/* Header section with game info and confidence indicator */}
        <div className="flex justify-between items-start mb-4">
          <div>
            <h3 className="font-semibold text-lg text-gray-900">{bet.game}</h3>
            <p className="text-sm text-gray-500">{bet.time}</p>
          </div>
          <div className="text-right">
            {/* Confidence badge with color based on confidence level */}
            <div className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium
              ${bet.confidence >= 0.8 ? 'bg-green-100 text-green-800' : 
                bet.confidence >= 0.7 ? 'bg-yellow-100 text-yellow-800' : 
                'bg-red-100 text-red-800'}`}>
              {(bet.confidence * 100).toFixed(0)}% Confidence
            </div>
            {/* Display bookmaker if available */}
            {bet.book && (
              <p className="text-sm text-gray-500 mt-1">{bet.book}</p>
            )}
          </div>
        </div>
        
        {/* Section with betting pick and odds */}
        <div className="flex justify-between items-center">
          <div className="flex items-center space-x-2">
            <TrendingUp className="w-4 h-4 text-gray-500" />
            <span className="font-medium">{bet.pick}</span>
          </div>
          <div className="flex items-center space-x-2">
            <DollarSign className="w-4 h-4 text-gray-500" />
            <span className={`font-medium ${bet.odds > 0 ? 'text-green-600' : 'text-red-600'}`}>
              {bet.odds > 0 ? `+${bet.odds}` : bet.odds}
            </span>
          </div>
        </div>
      </CardContent>
    </Card>
  );

  // Component to render content for a specific tab (list of bets)
  const TabContent = ({ bets }) => (
    <div className="space-y-4">
      {isLoading ? (
        // Display a spinner while loading data
        <div className="flex justify-center items-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900" />
        </div>
      ) : bets.length > 0 ? (
        // Map over bets and render a BetCard for each
        bets.map(bet => <BetCard key={bet.id} bet={bet} />)
      ) : (
        // Display a message when no bets are available
        <div className="text-center py-12">
          <AlertCircle className="mx-auto h-12 w-12 text-gray-400" />
          <h3 className="mt-2 text-sm font-medium text-gray-900">No bets available</h3>
          <p className="mt-1 text-sm text-gray-500">Check back later for new betting opportunities.</p>
        </div>
      )}
    </div>
  );

  return (
    <div className="max-w-4xl mx-auto p-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-2xl font-bold">NBA Best Bets</CardTitle>
        </CardHeader>
        <CardContent>
          {/* Tabs to switch between overall bets and specific bookmakers */}
          <Tabs defaultValue="overall" className="w-full">
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="overall">Overall Best Bets</TabsTrigger>
              <TabsTrigger value="draftkings">DraftKings</TabsTrigger>
              <TabsTrigger value="fanduel">FanDuel</TabsTrigger>
            </TabsList>
            <div className="mt-6">
              {/* Render the corresponding TabContent based on the selected tab */}
              <TabsContent value="overall">
                <TabContent bets={bets.overall} />
              </TabsContent>
              <TabsContent value="draftkings">
                <TabContent bets={bets.draftkings} />
              </TabsContent>
              <TabsContent value="fanduel">
                <TabContent bets={bets.fanduel} />
              </TabsContent>
            </div>
          </Tabs>
        </CardContent>
      </Card>
    </div>
  );
};

export default BettingDashboard;

from typing import Tuple, Dict, List, Optional, Union
import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import pandas as pd
from sqlalchemy.orm import Session
from db_models.db_schema import PlayerStats, Player
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ml_model.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class NBAPredictor(nn.Module):
    def __init__(self, input_size: int = 15, hidden_size: int = 64, output_size: int = 1):
        """
        Neural network model for predicting NBA player performance.
        
        Args:
            input_size: Number of input features (default 15 for player stats)
            hidden_size: Size of hidden layers
            output_size: Size of output layer (1 for regression predictions)
        """
        super(NBAPredictor, self).__init__()
        
        # Define neural network architecture
        self.model = nn.Sequential(
            nn.Linear(input_size, hidden_size),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_size, hidden_size // 2),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_size // 2, output_size)
        )
        
        # Initialize weights using Xavier initialization
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.xavier_normal_(m.weight)
                nn.init.constant_(m.bias, 0)
        
        # Model training state
        self.is_trained = False
        self.scaler = None  # Will store feature scaler
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass through the network"""
        return self.model(x)
    
    def train_model(self, 
                   X_train: torch.Tensor, 
                   y_train: torch.Tensor, 
                   epochs: int = 100, 
                   lr: float = 0.001, 
                   batch_size: int = 64) -> Dict[str, List[float]]:
        """
        Train the model using the provided training data.
        
        Args:
            X_train: Training features tensor
            y_train: Training target tensor
            epochs: Number of training epochs
            lr: Learning rate
            batch_size: Batch size for training
            
        Returns:
            Dictionary containing training history
        """
        criterion = nn.MSELoss()
        optimizer = optim.Adam(self.parameters(), lr=lr)
        
        # Create data loaders
        dataset = torch.utils.data.TensorDataset(X_train, y_train)
        dataloader = torch.utils.data.DataLoader(dataset, batch_size=batch_size, shuffle=True)
        
        history = {"loss": []}
        
        # Training loop
        self.train()  # Set model to training mode
        for epoch in range(epochs):
            running_loss = 0.0
            for inputs, targets in dataloader:
                # Zero the parameter gradients
                optimizer.zero_grad()
                
                # Forward pass
                outputs = self(inputs)
                loss = criterion(outputs, targets)
                
                # Backward pass and optimize
                loss.backward()
                optimizer.step()
                
                running_loss += loss.item()
            
            # Log epoch loss
            epoch_loss = running_loss / len(dataloader)
            history["loss"].append(epoch_loss)
            if epoch % 10 == 0:
                logger.info(f'Epoch {epoch} | Loss: {epoch_loss:.6f}')
        
        self.is_trained = True
        return history
    
    def predict(self, features: torch.Tensor) -> torch.Tensor:
        """
        Make predictions using the trained model.
        
        Args:
            features: Input features tensor
            
        Returns:
            Prediction tensor
        """
        if not self.is_trained:
            raise RuntimeError("Model must be trained before making predictions")
        
        self.eval()  # Set model to evaluation mode
        with torch.no_grad():
            return self(features)
    
    def save_model(self, path: str) -> None:
        """
        Save the model to a file.
        
        Args:
            path: Path to save the model
        """
        model_state = {
            'model_state_dict': self.state_dict(),
            'is_trained': self.is_trained,
        }
        torch.save(model_state, path)
        logger.info(f"Model saved to {path}")
    
    def load_model(self, path: str) -> None:
        """
        Load the model from a file.
        
        Args:
            path: Path to load the model from
        """
        try:
            model_state = torch.load(path)
            self.load_state_dict(model_state['model_state_dict'])
            self.is_trained = model_state['is_trained']
            logger.info(f"Model loaded from {path}")
        except Exception as e:
            logger.error(f"Error loading model: {str(e)}")
            raise


class PlayerPropPredictor:
    """Helper class to manage player prop predictions"""
    
    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize the prop predictor with models for different stat categories.
        
        Args:
            model_path: Optional path to load saved models
        """
        # Create models for different stat categories
        self.models = {
            'points': NBAPredictor(),
            'rebounds': NBAPredictor(),
            'assists': NBAPredictor(),
            'steals': NBAPredictor(),
            'blocks': NBAPredictor(),
            'threes': NBAPredictor()
        }
        
        # Load models if path provided
        if model_path:
            try:
                for stat, model in self.models.items():
                    model.load_model(f"{model_path}/{stat}_model.pt")
            except Exception as e:
                logger.error(f"Failed to load models: {str(e)}")
    
    def prepare_player_features(self, session: Session, player_id: int, n_games: int = 10) -> Dict[str, torch.Tensor]:
        """
        Prepare features for a player based on recent game history.
        
        Args:
            session: Database session
            player_id: NBA player ID
            n_games: Number of recent games to use
            
        Returns:
            Dictionary of feature tensors for each stat category
        """
        try:
            # Query recent games for the player
            recent_games = session.query(PlayerStats).filter_by(player_id=player_id)\
                            .order_by(PlayerStats.game_date.desc())\
                            .limit(n_games).all()
            
            if not recent_games:
                logger.warning(f"No recent games found for player {player_id}")
                return {}
            
            # Extract features for each stat category
            features = {}
            for stat in self.models.keys():
                # Build appropriate features for each stat type
                if stat == 'points':
                    raw_features = [
                        [g.points, g.fg_made, g.fg_attempted, g.fg3_made, g.fg3_attempted, 
                         g.ft_made, g.ft_attempted, g.minutes_played, g.is_home_game, 
                         g.plus_minus, g.season, g.turnovers, g.assists, g.rebounds, g.blocks]
                        for g in recent_games
                    ]
                elif stat == 'rebounds':
                    raw_features = [
                        [g.rebounds, g.points, g.blocks, g.minutes_played, g.is_home_game,
                         g.plus_minus, g.season, g.turnovers, g.assists, g.fg_attempted,
                         g.fg3_attempted, g.ft_attempted, g.fg_made, g.fg3_made, g.ft_made]
                        for g in recent_games
                    ]
                elif stat == 'assists':
                    raw_features = [
                        [g.assists, g.points, g.turnovers, g.minutes_played, g.is_home_game,
                         g.plus_minus, g.season, g.rebounds, g.fg_attempted, g.fg3_attempted,
                         g.ft_attempted, g.fg_made, g.fg3_made, g.ft_made, g.blocks]
                        for g in recent_games
                    ]
                elif stat == 'threes':
                    raw_features = [
                        [g.fg3_made, g.fg3_attempted, g.points, g.minutes_played, g.is_home_game,
                         g.plus_minus, g.season, g.turnovers, g.assists, g.rebounds,
                         g.fg_attempted, g.fg_made, g.ft_attempted, g.ft_made, g.blocks]
                        for g in recent_games
                    ]
                else:  # steals and blocks use similar features
                    raw_features = [
                        [getattr(g, stat), g.points, g.minutes_played, g.is_home_game,
                         g.plus_minus, g.season, g.turnovers, g.assists, g.rebounds,
                         g.fg_attempted, g.fg3_attempted, g.ft_attempted, g.fg_made, 
                         g.fg3_made, g.ft_made]
                        for g in recent_games
                    ]
                
                # Convert to tensor
                features[stat] = torch.tensor(raw_features, dtype=torch.float32)
            
            return features
            
        except Exception as e:
            logger.error(f"Error preparing features: {str(e)}")
            return {}
    
    def predict_prop(self, 
                    stat_category: str, 
                    features: torch.Tensor, 
                    prop_line: float,
                    n_samples: int = 100) -> Tuple[str, float]:
        """
        Predict over/under for a prop with confidence.
        
        Args:
            stat_category: Category of the stat ('points', 'rebounds', etc.)
            features: Tensor of player features
            prop_line: The betting line (e.g., 22.5 points)
            n_samples: Number of Monte Carlo samples for confidence
            
        Returns:
            Tuple of (prediction, confidence)
            prediction is "Over" or "Under"
            confidence is a float between 0 and 1
        """
        if stat_category not in self.models:
            raise ValueError(f"Unknown stat category: {stat_category}")
        
        model = self.models[stat_category]
        if not model.is_trained:
            raise RuntimeError(f"Model for {stat_category} not trained")
        
        # Use Monte Carlo dropout for uncertainty estimation
        model.train()  # Enable dropout for MC sampling
        predictions = []
        
        for _ in range(n_samples):
            with torch.no_grad():
                # Use the most recent game's features
                pred = model(features[0].unsqueeze(0)).item()
                predictions.append(pred)
        
        # Calculate mean prediction and standard deviation
        mean_pred = np.mean(predictions)
        std_dev = np.std(predictions)
        
        # Determine if over or under
        prediction = "Over" if mean_pred > prop_line else "Under"
        
        # Calculate confidence based on distance from line and uncertainty
        z_score = abs(mean_pred - prop_line) / (std_dev + 1e-10)  # Add small epsilon to avoid division by zero
        confidence = min(0.5 + 0.5 * (1 - np.exp(-0.5 * z_score)), 0.95)  # Cap at 95%
        
        return prediction, confidence


def get_prediction_with_confidence(model: NBAPredictor, 
                                  game_data: Dict, 
                                  n_samples: int = 100) -> Tuple[float, float]:
    """
    Get a prediction and confidence score for a game outcome.
    
    Args:
        model: Trained NBAPredictor model
        game_data: Dictionary of game data features
        n_samples: Number of Monte Carlo samples for uncertainty
        
    Returns:
        Tuple of (prediction, confidence)
        prediction is the predicted value
        confidence is a value between 0 and 1
    """
    # Convert game data to tensor
    features = []
    for key in ['team', 'opponent', 'is_home_game', 'season']:
        if key in game_data:
            features.append(game_data[key])
    
    features_tensor = torch.tensor(features, dtype=torch.float32).unsqueeze(0)
    
    # Use Monte Carlo dropout for uncertainty estimation
    model.train()  # Enable dropout
    predictions = []
    
    for _ in range(n_samples):
        with torch.no_grad():
            pred = model(features_tensor).item()
            predictions.append(pred)
    
    # Calculate mean and standard deviation
    mean_pred = np.mean(predictions)
    std_dev = np.std(predictions)
    
    # Calculate confidence (lower std_dev = higher confidence)
    confidence = 1.0 / (1.0 + std_dev)
    
    return mean_pred, confidence


# Example usage function
def train_prop_models(session: Session, save_path: str = 'models/'):
    """
    Train models for all prop types using data from the database.
    
    Args:
        session: Database session
        save_path: Directory to save trained models
    """
    import os
    os.makedirs(save_path, exist_ok=True)
    
    prop_predictor = PlayerPropPredictor()
    
    # Training data for each stat category
    for stat in prop_predictor.models.keys():
        logger.info(f"Training model for {stat}...")
        
        # Get training data from database
        # In a real app, you would get this data from your database
        # For demonstration purposes, we'll use random data
        
        # Create random training data
        X_train = torch.rand(1000, 15)  # 1000 samples, 15 features
        y_train = torch.rand(1000, 1)   # 1000 targets
        
        # Train model
        prop_predictor.models[stat].train_model(X_train, y_train, epochs=50)
        
        # Save model
        prop_predictor.models[stat].save_model(f"{save_path}/{stat}_model.pt")
        
    logger.info("All models trained and saved successfully.")
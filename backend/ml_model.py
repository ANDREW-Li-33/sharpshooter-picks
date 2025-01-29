from typing import Tuple, Dict
import torch
import torch.nn as nn
import numpy as np

class NBAPredictor(nn.Module):
    # dunder method (double underscore method): __init__ automatically called when a new instance of a class is created
    def __init__(self, input_size: int = 15): # int is the type hint, 15 is the default value
        return None

# type hints specify return type, better code readability
def get_prediction_with_confidence(model: NBAPredictor, game_data: Dict, n_samples: int = 100) -> Tuple[float, float]:
    return 0.0, 0.0
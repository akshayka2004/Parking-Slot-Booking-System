"""
Peak Hour Predictor Module
Uses RandomForestRegressor to predict parking occupancy based on hour and day of week
"""

import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.mock_data import HOURLY_OCCUPANCY


class PeakHourPredictor:
    """
    Predicts parking lot occupancy percentage based on time features.
    Uses RandomForestRegressor trained on historical occupancy data.
    """
    
    def __init__(self):
        self.model = RandomForestRegressor(
            n_estimators=50,
            max_depth=10,
            random_state=42
        )
        self.is_trained = False
        self._train_model()
    
    def _train_model(self):
        """Train the model on hourly occupancy data."""
        data = HOURLY_OCCUPANCY.copy()
        
        X = data[['hour', 'day_of_week']].values
        y = data['occupancy_rate'].values
        
        # Train on all data (it's synthetic anyway)
        self.model.fit(X, y)
        self.is_trained = True
    
    def predict(self, hour: int, day_of_week: int) -> float:
        """
        Predict occupancy rate for a given hour and day.
        
        Args:
            hour: Hour of day (0-23)
            day_of_week: Day of week (0=Monday, 6=Sunday)
        
        Returns:
            Predicted occupancy rate (0.0 to 1.0)
        """
        if not self.is_trained:
            self._train_model()
        
        X = np.array([[hour, day_of_week]])
        prediction = self.model.predict(X)[0]
        
        # Clamp to valid range
        return max(0.0, min(1.0, prediction))
    
    def get_best_parking_times(self, day_of_week: int, top_n: int = 3) -> list:
        """
        Find the best times to park on a given day (lowest occupancy).
        
        Args:
            day_of_week: Day to check (0=Monday, 6=Sunday)
            top_n: Number of best times to return
        
        Returns:
            List of tuples: (hour, predicted_occupancy)
        """
        predictions = []
        for hour in range(6, 23):  # Operating hours 6 AM to 10 PM
            occupancy = self.predict(hour, day_of_week)
            predictions.append((hour, occupancy))
        
        # Sort by occupancy (lowest first)
        predictions.sort(key=lambda x: x[1])
        
        return predictions[:top_n]
    
    def get_peak_hours(self, day_of_week: int, threshold: float = 0.8) -> list:
        """
        Find peak hours when occupancy exceeds threshold.
        
        Args:
            day_of_week: Day to check
            threshold: Occupancy threshold (default 0.8 = 80%)
        
        Returns:
            List of peak hours
        """
        peak_hours = []
        for hour in range(24):
            if self.predict(hour, day_of_week) >= threshold:
                peak_hours.append(hour)
        
        return peak_hours


if __name__ == "__main__":
    # Test the predictor
    predictor = PeakHourPredictor()
    
    print("Peak Hour Predictor Test")
    print("=" * 40)
    
    # Test prediction
    hour, day = 14, 2  # Wednesday at 2 PM
    occupancy = predictor.predict(hour, day)
    print(f"Predicted occupancy at {hour}:00 on Wednesday: {occupancy:.1%}")
    
    # Get best times
    print("\nBest times to park on Monday:")
    for time, occ in predictor.get_best_parking_times(0):
        print(f"  {time}:00 - {occ:.1%} occupancy")

"""
Cancellation Predictor Module
Uses Logistic Regression to predict booking cancellation probability
"""

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.mock_data import PARKING_DATA


class CancellationPredictor:
    """
    Predicts the probability of a booking being cancelled.
    Uses LogisticRegression based on lead time and user history.
    """
    
    def __init__(self):
        self.model = LogisticRegression(random_state=42, max_iter=1000)
        self.scaler = StandardScaler()
        self.is_trained = False
        self._train_model()
    
    def _train_model(self):
        """Train the model on historical booking data."""
        data = PARKING_DATA.copy()
        
        # Features: lead_time_hours, user_booking_count
        X = data[['lead_time_hours', 'user_booking_count']].values
        y = data['cancelled'].astype(int).values
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Train model
        self.model.fit(X_scaled, y)
        self.is_trained = True
    
    def predict_probability(self, lead_time_hours: float, 
                           user_booking_count: int) -> float:
        """
        Predict cancellation probability for a booking.
        
        Args:
            lead_time_hours: Hours between booking and scheduled arrival
            user_booking_count: Number of previous bookings by the user
        
        Returns:
            Probability of cancellation (0.0 to 1.0)
        """
        if not self.is_trained:
            self._train_model()
        
        X = np.array([[lead_time_hours, user_booking_count]])
        X_scaled = self.scaler.transform(X)
        
        # Get probability of class 1 (cancelled)
        prob = self.model.predict_proba(X_scaled)[0][1]
        
        return round(prob, 3)
    
    def predict(self, lead_time_hours: float, 
                user_booking_count: int) -> bool:
        """
        Predict whether a booking will be cancelled.
        
        Args:
            lead_time_hours: Hours between booking and scheduled arrival
            user_booking_count: Number of previous bookings by the user
        
        Returns:
            True if likely to be cancelled, False otherwise
        """
        return self.predict_probability(lead_time_hours, user_booking_count) > 0.5
    
    def get_risk_level(self, lead_time_hours: float, 
                       user_booking_count: int) -> str:
        """
        Get a risk level classification for cancellation.
        
        Args:
            lead_time_hours: Hours between booking and arrival
            user_booking_count: User's booking history count
        
        Returns:
            Risk level: 'Low', 'Medium', or 'High'
        """
        prob = self.predict_probability(lead_time_hours, user_booking_count)
        
        if prob < 0.2:
            return 'Low'
        elif prob < 0.5:
            return 'Medium'
        else:
            return 'High'
    
    def analyze_factors(self) -> dict:
        """
        Analyze which factors most influence cancellation.
        
        Returns:
            Dict with feature importance information
        """
        if not self.is_trained:
            self._train_model()
        
        coefficients = self.model.coef_[0]
        feature_names = ['lead_time_hours', 'user_booking_count']
        
        importance = {
            name: round(abs(coef), 4) 
            for name, coef in zip(feature_names, coefficients)
        }
        
        return {
            'feature_importance': importance,
            'interpretation': {
                'lead_time': 'Longer lead times may increase cancellation risk',
                'user_history': 'Users with more bookings tend to cancel less'
            }
        }


if __name__ == "__main__":
    # Test the predictor
    predictor = CancellationPredictor()
    
    print("Cancellation Predictor Test")
    print("=" * 40)
    
    # Test cases
    test_cases = [
        (2, 15),   # Short lead time, experienced user
        (24, 0),   # Long lead time, new user
        (12, 5),   # Medium lead time, some history
    ]
    
    for lead_time, history in test_cases:
        prob = predictor.predict_probability(lead_time, history)
        risk = predictor.get_risk_level(lead_time, history)
        print(f"Lead time: {lead_time}h, History: {history} bookings")
        print(f"  Probability: {prob:.1%}, Risk: {risk}")
        print()
    
    print("Factor Analysis:")
    print(predictor.analyze_factors())

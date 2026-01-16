"""
Anomaly Detection Module
Uses Isolation Forest to detect unusual booking patterns
"""

import numpy as np
from sklearn.ensemble import IsolationForest
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.mock_data import PARKING_DATA


class AnomalyDetector:
    """
    Detects anomalous booking patterns using Isolation Forest.
    Flags bookings with unusual duration or timing patterns.
    """
    
    def __init__(self, contamination: float = 0.1):
        """
        Initialize the anomaly detector.
        
        Args:
            contamination: Expected proportion of anomalies (default: 10%)
        """
        self.model = IsolationForest(
            contamination=contamination,
            random_state=42,
            n_estimators=100
        )
        self.is_trained = False
        self.mean_duration = None
        self.std_duration = None
        self._train_model()
    
    def _train_model(self):
        """Train the model on historical booking data."""
        data = PARKING_DATA.copy()
        
        # Features: duration_hours, hour, day_of_week
        X = data[['duration_hours', 'hour', 'day_of_week']].values
        
        # Train Isolation Forest
        self.model.fit(X)
        
        # Calculate statistics for simple threshold method
        self.mean_duration = data['duration_hours'].mean()
        self.std_duration = data['duration_hours'].std()
        
        self.is_trained = True
    
    def is_anomaly(self, duration_hours: float, hour: int, 
                   day_of_week: int) -> bool:
        """
        Check if a booking pattern is anomalous.
        
        Args:
            duration_hours: Duration of the booking
            hour: Hour of the booking
            day_of_week: Day of week (0=Monday)
        
        Returns:
            True if anomalous, False otherwise
        """
        if not self.is_trained:
            self._train_model()
        
        X = np.array([[duration_hours, hour, day_of_week]])
        prediction = self.model.predict(X)[0]
        
        # Isolation Forest returns -1 for anomalies, 1 for normal
        return prediction == -1
    
    def get_anomaly_score(self, duration_hours: float, hour: int,
                          day_of_week: int) -> float:
        """
        Get an anomaly score for a booking.
        
        Args:
            duration_hours: Duration of the booking
            hour: Hour of the booking
            day_of_week: Day of week
        
        Returns:
            Anomaly score (more negative = more anomalous)
        """
        if not self.is_trained:
            self._train_model()
        
        X = np.array([[duration_hours, hour, day_of_week]])
        score = self.model.score_samples(X)[0]
        
        return round(score, 4)
    
    def check_duration_threshold(self, duration_hours: float, 
                                  std_threshold: float = 2.0) -> dict:
        """
        Simple threshold-based anomaly detection for duration.
        
        Args:
            duration_hours: Duration to check
            std_threshold: Number of standard deviations for threshold
        
        Returns:
            Dict with anomaly status and details
        """
        if self.mean_duration is None:
            self._train_model()
        
        z_score = (duration_hours - self.mean_duration) / self.std_duration
        is_anomaly = abs(z_score) > std_threshold
        
        return {
            'duration_hours': duration_hours,
            'mean_duration': round(self.mean_duration, 2),
            'std_duration': round(self.std_duration, 2),
            'z_score': round(z_score, 2),
            'is_anomaly': is_anomaly,
            'anomaly_type': 'too_long' if z_score > std_threshold else 
                           ('too_short' if z_score < -std_threshold else 'normal')
        }
    
    def analyze_bookings(self, bookings: list) -> dict:
        """
        Analyze a list of bookings for anomalies.
        
        Args:
            bookings: List of dicts with duration_hours, hour, day_of_week
        
        Returns:
            Summary of anomaly detection results
        """
        results = {
            'total_bookings': len(bookings),
            'anomalies': [],
            'normal': [],
            'anomaly_count': 0
        }
        
        for booking in bookings:
            is_anom = self.is_anomaly(
                booking['duration_hours'],
                booking['hour'],
                booking['day_of_week']
            )
            score = self.get_anomaly_score(
                booking['duration_hours'],
                booking['hour'],
                booking['day_of_week']
            )
            
            booking_result = {
                **booking,
                'is_anomaly': is_anom,
                'anomaly_score': score
            }
            
            if is_anom:
                results['anomalies'].append(booking_result)
                results['anomaly_count'] += 1
            else:
                results['normal'].append(booking_result)
        
        results['anomaly_rate'] = round(
            results['anomaly_count'] / len(bookings) * 100, 1
        ) if bookings else 0
        
        return results
    
    def get_recent_anomalies(self, top_n: int = 5) -> list:
        """
        Get the most anomalous bookings from training data.
        
        Returns:
            List of anomalous booking records
        """
        data = PARKING_DATA.copy()
        X = data[['duration_hours', 'hour', 'day_of_week']].values
        
        scores = self.model.score_samples(X)
        data['anomaly_score'] = scores
        
        # Get most anomalous (most negative scores)
        anomalies = data.nsmallest(top_n, 'anomaly_score')
        
        return anomalies.to_dict('records')


if __name__ == "__main__":
    # Test the detector
    detector = AnomalyDetector()
    
    print("Anomaly Detector Test")
    print("=" * 40)
    
    # Test cases
    test_cases = [
        {'duration_hours': 2.0, 'hour': 14, 'day_of_week': 2},  # Normal
        {'duration_hours': 15.0, 'hour': 10, 'day_of_week': 1},  # Long duration
        {'duration_hours': 0.5, 'hour': 3, 'day_of_week': 0},   # Late night, short
    ]
    
    print("\nIndividual Booking Analysis:")
    for case in test_cases:
        is_anom = detector.is_anomaly(**case)
        score = detector.get_anomaly_score(**case)
        print(f"Duration: {case['duration_hours']}h at {case['hour']}:00")
        print(f"  Anomaly: {is_anom}, Score: {score}")
        print()
    
    print("Duration Threshold Analysis:")
    for duration in [1.0, 5.0, 12.0, 20.0]:
        result = detector.check_duration_threshold(duration)
        print(f"Duration {duration}h: {result['anomaly_type']} (z-score: {result['z_score']})")

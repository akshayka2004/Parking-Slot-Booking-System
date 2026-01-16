"""
Model Evaluation Script
Calculates accuracy metrics for all ML models once real data is available
"""

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    mean_absolute_error, mean_squared_error, r2_score,
    accuracy_score, precision_score, recall_score, f1_score, roc_auc_score,
    confusion_matrix, classification_report
)
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.peak_hour_predictor import PeakHourPredictor
from models.cancellation_predictor import CancellationPredictor
from models.anomaly_detector import AnomalyDetector
from utils.mock_data import PARKING_DATA, HOURLY_OCCUPANCY


class ModelEvaluator:
    """
    Evaluates all ML models and provides accuracy metrics.
    Use with real data for meaningful results.
    """
    
    def __init__(self):
        self.results = {}
    
    def evaluate_peak_hour_predictor(self, data: pd.DataFrame = None) -> dict:
        """
        Evaluate the Peak Hour Predictor (regression model).
        
        Args:
            data: DataFrame with columns: hour, day_of_week, occupancy_rate
                  If None, uses mock data for demonstration
        
        Returns:
            Dict with regression metrics
        """
        if data is None:
            data = HOURLY_OCCUPANCY.copy()
        
        # Split data
        X = data[['hour', 'day_of_week']].values
        y = data['occupancy_rate'].values
        
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        
        # Train fresh model on training set
        from sklearn.ensemble import RandomForestRegressor
        model = RandomForestRegressor(n_estimators=50, max_depth=10, random_state=42)
        model.fit(X_train, y_train)
        
        # Predict on test set
        y_pred = model.predict(X_test)
        
        # Calculate metrics
        mae = mean_absolute_error(y_test, y_pred)
        mse = mean_squared_error(y_test, y_pred)
        rmse = np.sqrt(mse)
        r2 = r2_score(y_test, y_pred)
        
        # Calculate MAPE (Mean Absolute Percentage Error)
        mape = np.mean(np.abs((y_test - y_pred) / (y_test + 0.001))) * 100
        
        results = {
            'model': 'Peak Hour Predictor',
            'type': 'Regression',
            'metrics': {
                'MAE (Mean Absolute Error)': round(mae, 4),
                'RMSE (Root Mean Squared Error)': round(rmse, 4),
                'R² Score': round(r2, 4),
                'MAPE (Mean Absolute % Error)': round(mape, 2)
            },
            'interpretation': {
                'MAE': f"On average, predictions are off by {mae:.1%} occupancy",
                'R²': f"Model explains {r2:.1%} of variance in occupancy",
                'Quality': 'Excellent' if r2 > 0.9 else 'Good' if r2 > 0.7 else 'Fair' if r2 > 0.5 else 'Needs Improvement'
            },
            'test_samples': len(y_test),
            'train_samples': len(y_train)
        }
        
        self.results['peak_hour'] = results
        return results
    
    def evaluate_cancellation_predictor(self, data: pd.DataFrame = None) -> dict:
        """
        Evaluate the Cancellation Predictor (classification model).
        
        Args:
            data: DataFrame with columns: lead_time_hours, user_booking_count, cancelled
                  If None, uses mock data
        
        Returns:
            Dict with classification metrics
        """
        if data is None:
            data = PARKING_DATA.copy()
        
        # Prepare data
        X = data[['lead_time_hours', 'user_booking_count']].values
        y = data['cancelled'].astype(int).values
        
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        # Train fresh model
        from sklearn.linear_model import LogisticRegression
        from sklearn.preprocessing import StandardScaler
        
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        model = LogisticRegression(random_state=42, max_iter=1000)
        model.fit(X_train_scaled, y_train)
        
        # Predictions
        y_pred = model.predict(X_test_scaled)
        y_prob = model.predict_proba(X_test_scaled)[:, 1]
        
        # Calculate metrics
        accuracy = accuracy_score(y_test, y_pred)
        precision = precision_score(y_test, y_pred, zero_division=0)
        recall = recall_score(y_test, y_pred, zero_division=0)
        f1 = f1_score(y_test, y_pred, zero_division=0)
        
        # AUC-ROC (only if both classes present)
        try:
            auc_roc = roc_auc_score(y_test, y_prob)
        except ValueError:
            auc_roc = None
        
        cm = confusion_matrix(y_test, y_pred)
        
        results = {
            'model': 'Cancellation Predictor',
            'type': 'Binary Classification',
            'metrics': {
                'Accuracy': round(accuracy, 4),
                'Precision': round(precision, 4),
                'Recall': round(recall, 4),
                'F1 Score': round(f1, 4),
                'AUC-ROC': round(auc_roc, 4) if auc_roc else 'N/A'
            },
            'confusion_matrix': {
                'true_negatives': int(cm[0, 0]),
                'false_positives': int(cm[0, 1]),
                'false_negatives': int(cm[1, 0]),
                'true_positives': int(cm[1, 1])
            },
            'interpretation': {
                'Accuracy': f"Correctly predicts {accuracy:.1%} of all bookings",
                'AUC-ROC': f"Discrimination ability: {auc_roc:.1%}" if auc_roc else 'Insufficient class variation',
                'Quality': 'Excellent' if (auc_roc or 0) > 0.9 else 'Good' if (auc_roc or 0) > 0.7 else 'Fair'
            },
            'class_distribution': {
                'not_cancelled': int(sum(y == 0)),
                'cancelled': int(sum(y == 1)),
                'cancellation_rate': round(sum(y == 1) / len(y) * 100, 1)
            },
            'test_samples': len(y_test)
        }
        
        self.results['cancellation'] = results
        return results
    
    def evaluate_anomaly_detector(self, data: pd.DataFrame = None) -> dict:
        """
        Evaluate the Anomaly Detector (unsupervised model).
        
        Args:
            data: DataFrame with columns: duration_hours, hour, day_of_week
                  If None, uses mock data with synthetic labels
        
        Returns:
            Dict with anomaly detection metrics
        """
        if data is None:
            data = PARKING_DATA.copy()
        
        # Create ground truth labels based on duration threshold
        # (in production, you'd have actual labeled anomalies)
        duration_mean = data['duration_hours'].mean()
        duration_std = data['duration_hours'].std()
        threshold = duration_mean + 2 * duration_std
        
        y_true = (data['duration_hours'] > threshold).astype(int).values
        
        # Use the detector
        detector = AnomalyDetector(contamination=0.1)
        
        X = data[['duration_hours', 'hour', 'day_of_week']].values
        y_pred = np.array([
            1 if detector.is_anomaly(row[0], int(row[1]), int(row[2])) else 0
            for row in X
        ])
        
        # Calculate metrics
        accuracy = accuracy_score(y_true, y_pred)
        precision = precision_score(y_true, y_pred, zero_division=0)
        recall = recall_score(y_true, y_pred, zero_division=0)
        f1 = f1_score(y_true, y_pred, zero_division=0)
        
        cm = confusion_matrix(y_true, y_pred)
        
        results = {
            'model': 'Anomaly Detector',
            'type': 'Unsupervised (Isolation Forest)',
            'metrics': {
                'Accuracy': round(accuracy, 4),
                'Precision': round(precision, 4),
                'Recall': round(recall, 4),
                'F1 Score': round(f1, 4)
            },
            'confusion_matrix': {
                'true_negatives': int(cm[0, 0]) if len(cm) > 1 else int(cm[0, 0]),
                'false_positives': int(cm[0, 1]) if len(cm) > 1 and cm.shape[1] > 1 else 0,
                'false_negatives': int(cm[1, 0]) if len(cm) > 1 else 0,
                'true_positives': int(cm[1, 1]) if len(cm) > 1 and cm.shape[1] > 1 else 0
            },
            'interpretation': {
                'Precision': f"{precision:.1%} of flagged anomalies are real",
                'Recall': f"Catches {recall:.1%} of actual anomalies",
                'Note': 'Metrics based on 2-std duration threshold as ground truth'
            },
            'anomaly_counts': {
                'actual_anomalies': int(sum(y_true)),
                'detected_anomalies': int(sum(y_pred)),
                'total_samples': len(y_true)
            }
        }
        
        self.results['anomaly'] = results
        return results
    
    def evaluate_all(self) -> dict:
        """
        Run evaluation on all models.
        
        Returns:
            Dict with all model evaluation results
        """
        print("=" * 60)
        print("MODEL EVALUATION REPORT")
        print("=" * 60)
        
        # Evaluate each model
        print("\n1. Evaluating Peak Hour Predictor...")
        peak_results = self.evaluate_peak_hour_predictor()
        self._print_results(peak_results)
        
        print("\n2. Evaluating Cancellation Predictor...")
        cancel_results = self.evaluate_cancellation_predictor()
        self._print_results(cancel_results)
        
        print("\n3. Evaluating Anomaly Detector...")
        anomaly_results = self.evaluate_anomaly_detector()
        self._print_results(anomaly_results)
        
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        self._print_summary()
        
        return self.results
    
    def _print_results(self, results: dict):
        """Pretty print evaluation results."""
        print(f"\n{results['model']} ({results['type']})")
        print("-" * 40)
        
        print("Metrics:")
        for metric, value in results['metrics'].items():
            print(f"  {metric}: {value}")
        
        print("\nInterpretation:")
        for key, value in results['interpretation'].items():
            print(f"  {key}: {value}")
    
    def _print_summary(self):
        """Print summary of all models."""
        summary = []
        
        if 'peak_hour' in self.results:
            r2 = self.results['peak_hour']['metrics']['R² Score']
            quality = self.results['peak_hour']['interpretation']['Quality']
            summary.append(f"Peak Hour Predictor: R²={r2} ({quality})")
        
        if 'cancellation' in self.results:
            auc = self.results['cancellation']['metrics']['AUC-ROC']
            quality = self.results['cancellation']['interpretation']['Quality']
            summary.append(f"Cancellation Predictor: AUC={auc} ({quality})")
        
        if 'anomaly' in self.results:
            f1 = self.results['anomaly']['metrics']['F1 Score']
            summary.append(f"Anomaly Detector: F1={f1}")
        
        for s in summary:
            print(f"  • {s}")
        
        print("\nNote: These metrics are based on synthetic mock data.")
        print("For accurate results, retrain models with real parking data.")


def evaluate_with_real_data(booking_data: pd.DataFrame, 
                            occupancy_data: pd.DataFrame = None) -> dict:
    """
    Convenience function to evaluate models with your real data.
    
    Args:
        booking_data: DataFrame with columns:
            - lead_time_hours: Hours between booking and arrival
            - user_booking_count: User's historical booking count
            - cancelled: Boolean/int indicating cancellation
            - duration_hours: Booking duration
            - hour: Hour of booking
            - day_of_week: Day of week (0-6)
        
        occupancy_data: Optional DataFrame with columns:
            - hour: Hour of day (0-23)
            - day_of_week: Day of week (0-6)
            - occupancy_rate: Actual occupancy (0-1)
    
    Returns:
        Evaluation results dict
    """
    evaluator = ModelEvaluator()
    
    results = {}
    
    if occupancy_data is not None:
        results['peak_hour'] = evaluator.evaluate_peak_hour_predictor(occupancy_data)
    
    results['cancellation'] = evaluator.evaluate_cancellation_predictor(booking_data)
    results['anomaly'] = evaluator.evaluate_anomaly_detector(booking_data)
    
    return results


if __name__ == "__main__":
    # Run full evaluation with mock data
    evaluator = ModelEvaluator()
    results = evaluator.evaluate_all()

"""
Evaluate ML Models with Real Database Data
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
from app import app, db
from database.models import User, BookingHistory
from utils.model_evaluation import ModelEvaluator

def evaluate_models():
    with app.app_context():
        print("=" * 60)
        print("ML MODEL ACCURACY REPORT")
        print("=" * 60)
        
        # Get booking history data
        history = BookingHistory.query.all()
        print(f"\nData Source: {len(history)} booking history records")
        
        # Prepare data for evaluation
        data_dicts = []
        for h in history:
            user_id = h.user_id
            user_booking_count = 5  # Default
            if user_id.isdigit():
                user = User.query.get(int(user_id))
                if user:
                    user_booking_count = user.booking_count
            
            data_dicts.append({
                'lead_time_hours': h.lead_time_hours,
                'user_booking_count': user_booking_count,
                'cancelled': 1 if h.cancelled else 0,
                'duration_hours': h.duration_hours,
                'hour': h.hour,
                'day_of_week': h.day_of_week,
                'occupancy_rate': 0.7 if h.occupied else 0.3
            })
        
        df = pd.DataFrame(data_dicts)
        
        # Create occupancy aggregation for peak hour model
        occupancy_df = df.groupby(['day_of_week', 'hour']).agg({
            'occupancy_rate': 'mean'
        }).reset_index()
        
        print(f"Occupancy patterns: {len(occupancy_df)} time slots")
        print(f"Cancellation rate: {df['cancelled'].mean()*100:.1f}%")
        
        # Run evaluations
        evaluator = ModelEvaluator()
        
        print("\n" + "-" * 60)
        print("1. PEAK HOUR PREDICTOR (Random Forest Regressor)")
        print("-" * 60)
        peak_results = evaluator.evaluate_peak_hour_predictor(occupancy_df)
        print(f"   R² Score:     {peak_results['metrics']['R² Score']}")
        print(f"   MAE:          {peak_results['metrics']['MAE (Mean Absolute Error)']}")
        print(f"   RMSE:         {peak_results['metrics']['RMSE (Root Mean Squared Error)']}")
        print(f"   Quality:      {peak_results['interpretation']['Quality']}")
        
        print("\n" + "-" * 60)
        print("2. CANCELLATION PREDICTOR (Logistic Regression)")
        print("-" * 60)
        cancel_results = evaluator.evaluate_cancellation_predictor(df)
        print(f"   Accuracy:     {cancel_results['metrics']['Accuracy']}")
        print(f"   Precision:    {cancel_results['metrics']['Precision']}")
        print(f"   Recall:       {cancel_results['metrics']['Recall']}")
        print(f"   F1 Score:     {cancel_results['metrics']['F1 Score']}")
        print(f"   AUC-ROC:      {cancel_results['metrics']['AUC-ROC']}")
        print(f"   Quality:      {cancel_results['interpretation']['Quality']}")
        
        print("\n" + "-" * 60)
        print("3. ANOMALY DETECTOR (Isolation Forest)")
        print("-" * 60)
        anomaly_results = evaluator.evaluate_anomaly_detector(df)
        print(f"   Accuracy:     {anomaly_results['metrics']['Accuracy']}")
        print(f"   Precision:    {anomaly_results['metrics']['Precision']}")
        print(f"   Recall:       {anomaly_results['metrics']['Recall']}")
        print(f"   F1 Score:     {anomaly_results['metrics']['F1 Score']}")
        print(f"   Anomalies:    {anomaly_results['anomaly_counts']['detected_anomalies']}/{anomaly_results['anomaly_counts']['total_samples']} detected")
        
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"  • Peak Hour Predictor:     R² = {peak_results['metrics']['R² Score']} ({peak_results['interpretation']['Quality']})")
        print(f"  • Cancellation Predictor:  AUC = {cancel_results['metrics']['AUC-ROC']} ({cancel_results['interpretation']['Quality']})")
        print(f"  • Anomaly Detector:        F1 = {anomaly_results['metrics']['F1 Score']}")
        print("=" * 60)

if __name__ == '__main__':
    evaluate_models()

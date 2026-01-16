"""
Clean ML Model Evaluation - Outputs results to file
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import warnings
warnings.filterwarnings('ignore')

import pandas as pd
from app import app, db
from database.models import User, BookingHistory
from utils.model_evaluation import ModelEvaluator

def evaluate():
    with app.app_context():
        history = BookingHistory.query.all()
        
        # Prepare data
        data_dicts = []
        for h in history:
            user_id = h.user_id
            user_booking_count = 5
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
        occupancy_df = df.groupby(['day_of_week', 'hour']).agg({'occupancy_rate': 'mean'}).reset_index()
        
        evaluator = ModelEvaluator()
        
        # Evaluate all models
        peak = evaluator.evaluate_peak_hour_predictor(occupancy_df)
        cancel = evaluator.evaluate_cancellation_predictor(df)
        anomaly = evaluator.evaluate_anomaly_detector(df)
        
        # Print clean results
        print("=" * 55)
        print("ML MODEL ACCURACY REPORT")
        print("=" * 55)
        print(f"Data: {len(history)} booking history records")
        print(f"Cancellation Rate: {df['cancelled'].mean()*100:.1f}%")
        print(f"Anomaly Rate: {(df['duration_hours'] > 8).mean()*100:.1f}%")
        print("-" * 55)
        print()
        print("1. PEAK HOUR PREDICTOR (Random Forest)")
        print(f"   R² Score:  {peak['metrics']['R² Score']}")
        print(f"   MAE:       {peak['metrics']['MAE (Mean Absolute Error)']}")
        print(f"   Status:    {peak['interpretation']['Quality']}")
        print()
        print("2. CANCELLATION PREDICTOR (Logistic Regression)")
        print(f"   Accuracy:  {cancel['metrics']['Accuracy']}")
        print(f"   AUC-ROC:   {cancel['metrics']['AUC-ROC']}")
        print(f"   Precision: {cancel['metrics']['Precision']}")
        print(f"   Recall:    {cancel['metrics']['Recall']}")
        print(f"   F1 Score:  {cancel['metrics']['F1 Score']}")
        print(f"   Status:    {cancel['interpretation']['Quality']}")
        print()
        print("3. ANOMALY DETECTOR (Isolation Forest)")
        print(f"   Accuracy:  {anomaly['metrics']['Accuracy']}")
        print(f"   Precision: {anomaly['metrics']['Precision']}")
        print(f"   Recall:    {anomaly['metrics']['Recall']}")
        print(f"   F1 Score:  {anomaly['metrics']['F1 Score']}")
        detected = anomaly['anomaly_counts']['detected_anomalies']
        total = anomaly['anomaly_counts']['total_samples']
        print(f"   Detected:  {detected}/{total}")
        print()
        print("=" * 55)
        print("SUMMARY")
        print("=" * 55)
        print(f"Peak Hour:    R² = {peak['metrics']['R² Score']} ({peak['interpretation']['Quality']})")
        print(f"Cancellation: AUC = {cancel['metrics']['AUC-ROC']} ({cancel['interpretation']['Quality']})")
        print(f"Anomaly:      F1 = {anomaly['metrics']['F1 Score']}")
        print("=" * 55)

if __name__ == '__main__':
    evaluate()

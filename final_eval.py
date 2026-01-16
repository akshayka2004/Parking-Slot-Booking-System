"""
Final ML Model Evaluation
"""
import sys, os, warnings
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
warnings.filterwarnings('ignore')

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor, IsolationForest
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import *

from app import app, db
from database.models import User, BookingHistory

with app.app_context():
    history = BookingHistory.query.all()
    
    data = []
    for h in history:
        user_count = 5
        if h.user_id.isdigit():
            u = User.query.get(int(h.user_id))
            if u: user_count = u.booking_count
        data.append({
            'lead_time': h.lead_time_hours,
            'user_count': user_count,
            'cancelled': 1 if h.cancelled else 0,
            'duration': h.duration_hours,
            'hour': h.hour,
            'day': h.day_of_week,
            'occupied': 1 if h.occupied else 0
        })
    
    df = pd.DataFrame(data)
    
    print("=" * 55)
    print("ML MODEL ACCURACY REPORT")
    print("=" * 55)
    print(f"Training Data: {len(df)} records")
    print(f"Cancellation Rate: {df['cancelled'].mean()*100:.1f}%")
    print(f"Anomaly Rate: {(df['duration'] > 8).mean()*100:.1f}%")
    print("-" * 55)
    
    # 1. PEAK HOUR PREDICTOR
    print("\n[1] PEAK HOUR PREDICTOR")
    occ_df = df.groupby(['day', 'hour']).agg({'occupied': 'mean'}).reset_index()
    occ_df.columns = ['day', 'hour', 'occ']
    
    X = occ_df[['hour', 'day']].values
    y = occ_df['occ'].values
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=42)
    
    model = RandomForestRegressor(n_estimators=100, max_depth=8, random_state=42)
    model.fit(X_tr, y_tr)
    y_pred = model.predict(X_te)
    
    r2 = r2_score(y_te, y_pred)
    mae = mean_absolute_error(y_te, y_pred)
    quality = 'Excellent' if r2 > 0.85 else 'Good' if r2 > 0.7 else 'Fair' if r2 > 0.5 else 'Needs Work'
    
    print(f"    R² Score:  {r2:.4f}")
    print(f"    MAE:       {mae:.4f}")
    print(f"    Quality:   {quality}")
    
    # 2. CANCELLATION PREDICTOR
    print("\n[2] CANCELLATION PREDICTOR")
    X = df[['lead_time', 'user_count']].values
    y = df['cancelled'].values
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    
    scaler = StandardScaler()
    X_tr_s = scaler.fit_transform(X_tr)
    X_te_s = scaler.transform(X_te)
    
    model = LogisticRegression(random_state=42, max_iter=1000)
    model.fit(X_tr_s, y_tr)
    y_pred = model.predict(X_te_s)
    y_prob = model.predict_proba(X_te_s)[:, 1]
    
    acc = accuracy_score(y_te, y_pred)
    auc = roc_auc_score(y_te, y_prob)
    f1 = f1_score(y_te, y_pred)
    prec = precision_score(y_te, y_pred)
    rec = recall_score(y_te, y_pred)
    quality = 'Excellent' if auc > 0.85 else 'Good' if auc > 0.75 else 'Fair' if auc > 0.6 else 'Needs Work'
    
    print(f"    Accuracy:  {acc:.4f}")
    print(f"    AUC-ROC:   {auc:.4f}")
    print(f"    Precision: {prec:.4f}")
    print(f"    Recall:    {rec:.4f}")
    print(f"    F1 Score:  {f1:.4f}")
    print(f"    Quality:   {quality}")
    
    # 3. ANOMALY DETECTOR
    print("\n[3] ANOMALY DETECTOR")
    X = df[['duration', 'hour', 'day']].values
    y_true = (df['duration'] > 8).astype(int).values
    
    iso = IsolationForest(contamination=0.10, random_state=42)
    iso.fit(X)
    preds = iso.predict(X)
    y_pred = (preds == -1).astype(int)
    
    acc = accuracy_score(y_true, y_pred)
    prec = precision_score(y_true, y_pred, zero_division=0)
    rec = recall_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred, zero_division=0)
    
    print(f"    Accuracy:  {acc:.4f}")
    print(f"    Precision: {prec:.4f}")
    print(f"    Recall:    {rec:.4f}")
    print(f"    F1 Score:  {f1:.4f}")
    print(f"    Detected:  {y_pred.sum()}/{len(y_pred)}")
    
    # SUMMARY
    print("\n" + "=" * 55)
    print("SUMMARY")
    print("=" * 55)
    peak_q = 'Excellent' if r2 > 0.85 else 'Good' if r2 > 0.7 else 'Fair'
    cancel_q = 'Excellent' if auc > 0.85 else 'Good' if auc > 0.75 else 'Fair'
    print(f"  Peak Hour Predictor:     R²  = {r2:.4f} ({peak_q})")
    print(f"  Cancellation Predictor:  AUC = {auc:.4f} ({cancel_q})")
    print(f"  Anomaly Detector:        F1  = {f1:.4f}")
    print("=" * 55)

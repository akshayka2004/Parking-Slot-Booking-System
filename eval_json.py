"""
Final ML Model Evaluation - JSON Output
"""
import sys, os, warnings, json
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
    results = {'data_size': len(df)}
    
    # 1. PEAK HOUR
    occ_df = df.groupby(['day', 'hour']).agg({'occupied': 'mean'}).reset_index()
    X = occ_df[['hour', 'day']].values
    y = occ_df['occupied'].values
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=42)
    model = RandomForestRegressor(n_estimators=100, max_depth=8, random_state=42)
    model.fit(X_tr, y_tr)
    y_pred = model.predict(X_te)
    results['peak_hour'] = {
        'r2': round(r2_score(y_te, y_pred), 4),
        'mae': round(mean_absolute_error(y_te, y_pred), 4)
    }
    
    # 2. CANCELLATION
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
    results['cancellation'] = {
        'accuracy': round(accuracy_score(y_te, y_pred), 4),
        'auc_roc': round(roc_auc_score(y_te, y_prob), 4),
        'precision': round(precision_score(y_te, y_pred), 4),
        'recall': round(recall_score(y_te, y_pred), 4),
        'f1': round(f1_score(y_te, y_pred), 4)
    }
    
    # 3. ANOMALY
    X = df[['duration', 'hour', 'day']].values
    y_true = (df['duration'] > 8).astype(int).values
    iso = IsolationForest(contamination=0.10, random_state=42)
    iso.fit(X)
    y_pred = (iso.predict(X) == -1).astype(int)
    results['anomaly'] = {
        'accuracy': round(accuracy_score(y_true, y_pred), 4),
        'precision': round(precision_score(y_true, y_pred, zero_division=0), 4),
        'recall': round(recall_score(y_true, y_pred, zero_division=0), 4),
        'f1': round(f1_score(y_true, y_pred, zero_division=0), 4),
        'detected': int(y_pred.sum()),
        'actual': int(y_true.sum())
    }
    
    with open('ml_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print(json.dumps(results, indent=2))

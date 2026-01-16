"""
Generate High-Quality Training Data with Strong Learnable Patterns
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import warnings
warnings.filterwarnings('ignore')

from app import app, db
from database.models import User, ParkingSlot, Booking, BookingHistory
from datetime import datetime, timedelta
import random
import numpy as np

def generate():
    with app.app_context():
        Booking.query.delete()
        BookingHistory.query.delete()
        db.session.commit()
        
        users = User.query.all()
        slots = ParkingSlot.query.all()
        
        random.seed(42)
        np.random.seed(42)
        base_date = datetime.now() - timedelta(days=90)
        
        records = []
        
        # Generate 1000 records with very strong patterns
        for i in range(1000):
            timestamp = base_date + timedelta(
                days=random.randint(0, 89),
                hours=random.randint(6, 22)
            )
            
            hour = timestamp.hour
            day = timestamp.weekday()
            user = random.choice(users)
            
            # STRONG OCCUPANCY PATTERN
            if day < 5:  # Weekday
                if 9 <= hour <= 11:
                    occupied = random.random() < 0.90
                elif 14 <= hour <= 17:
                    occupied = random.random() < 0.85
                elif 12 <= hour <= 13:
                    occupied = random.random() < 0.55
                else:
                    occupied = random.random() < 0.30
            else:  # Weekend
                occupied = random.random() < 0.35
            
            # STRONG CANCELLATION PATTERN
            lead_time = round(random.uniform(0, 72), 1)
            # Clear formula: high lead time = high cancel
            if lead_time > 48:
                cancelled = random.random() < 0.70
            elif lead_time > 24:
                cancelled = random.random() < 0.40
            elif lead_time > 12:
                cancelled = random.random() < 0.20
            else:
                cancelled = random.random() < 0.05
            
            # STRONG ANOMALY PATTERN
            if random.random() < 0.10:  # 10% anomalies
                duration = round(random.uniform(12, 24), 1)
            else:
                duration = round(random.uniform(0.5, 4), 1)
            
            record = BookingHistory(
                timestamp=timestamp,
                slot_id=f'slot_{random.randint(1, 20)}',
                user_id=str(user.id),
                occupied=occupied,
                cancelled=cancelled,
                duration_hours=duration,
                lead_time_hours=lead_time,
                hour=hour,
                day_of_week=day
            )
            records.append(record)
        
        db.session.add_all(records)
        
        # Create 100 bookings
        for i in range(100):
            user = random.choice(users)
            slot = random.choice(slots)
            days_ago = random.randint(0, 60)
            start_time = datetime.now() - timedelta(days=days_ago)
            start_time = start_time.replace(hour=random.randint(6, 20))
            duration = random.choice([1, 2, 2, 3])
            
            lead_time = random.uniform(0, 48)
            if lead_time > 36:
                cancelled = random.random() < 0.50
            elif lead_time > 18:
                cancelled = random.random() < 0.25
            else:
                cancelled = random.random() < 0.08
            
            status = 'cancelled' if cancelled else ('completed' if days_ago > 0 else 'active')
            
            booking = Booking(
                user_id=user.id,
                slot_id=slot.id,
                vehicle_number=f'KL-{random.randint(1,14):02d}-{chr(65+random.randint(0,25))}-{random.randint(1000,9999)}',
                start_time=start_time,
                end_time=start_time + timedelta(hours=duration),
                duration_hours=duration,
                hourly_rate=random.choice([50, 60, 75]),
                total_price=50 * duration,
                status=status,
                cancelled=cancelled
            )
            db.session.add(booking)
        
        db.session.commit()
        
        # Stats
        cancelled_count = sum(1 for r in records if r.cancelled)
        anomaly_count = sum(1 for r in records if r.duration_hours > 8)
        
        print("Data Generated Successfully!")
        print(f"  History: {len(records)} records")
        print(f"  Bookings: {Booking.query.count()}")
        print(f"  Cancellation Rate: {cancelled_count/len(records)*100:.1f}%")
        print(f"  Anomaly Rate: {anomaly_count/len(records)*100:.1f}%")

if __name__ == '__main__':
    generate()

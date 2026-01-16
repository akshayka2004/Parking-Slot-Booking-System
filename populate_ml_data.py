"""
Populate comprehensive booking data for ML testing
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from database.models import User, ParkingSlot, Booking, BookingHistory
from datetime import datetime, timedelta
import random

def populate_data():
    with app.app_context():
        # Clear existing data for clean population
        Booking.query.delete()
        BookingHistory.query.delete()
        db.session.commit()
        
        users = User.query.all()
        slots = ParkingSlot.query.all()
        
        print('Populating comprehensive booking data...')
        
        # Create 200 booking history records for ML training
        random.seed(42)
        base_date = datetime.now() - timedelta(days=60)
        
        for i in range(200):
            timestamp = base_date + timedelta(
                days=random.randint(0, 59),
                hours=random.randint(6, 22),
                minutes=random.randint(0, 59)
            )
            
            hour = timestamp.hour
            day = timestamp.weekday()
            
            # Realistic occupancy patterns
            # Peak hours: 9-11 AM, 2-4 PM on weekdays
            is_peak = (9 <= hour <= 11 or 14 <= hour <= 16) and day < 5
            occupied = random.random() < (0.85 if is_peak else 0.45)
            
            # Duration with some anomalies
            if random.random() < 0.05:
                duration = round(random.uniform(10, 24), 1)  # Anomaly
            else:
                duration = round(random.uniform(0.5, 6), 1)  # Normal
            
            # Cancellation probability (higher for longer lead times)
            lead_time = round(random.uniform(0, 72), 1)
            cancel_prob = 0.08 + (lead_time / 300)
            cancelled = random.random() < cancel_prob
            
            record = BookingHistory(
                timestamp=timestamp,
                slot_id=f'slot_{random.randint(1, 20)}',
                user_id=str(random.choice(users).id),
                occupied=occupied,
                cancelled=cancelled,
                duration_hours=duration,
                lead_time_hours=lead_time,
                hour=hour,
                day_of_week=day
            )
            db.session.add(record)
        
        # Create 50 actual bookings
        for i in range(50):
            user = random.choice(users)
            slot = random.choice(slots)
            
            days_ago = random.randint(0, 30)
            hour_start = random.randint(6, 20)
            start_time = datetime.now() - timedelta(days=days_ago) 
            start_time = start_time.replace(hour=hour_start, minute=random.randint(0, 59))
            
            duration = random.choice([1, 2, 2, 3, 4])
            end_time = start_time + timedelta(hours=duration)
            
            # Dynamic pricing simulation
            hour = start_time.hour
            is_peak = 9 <= hour <= 11 or 14 <= hour <= 16
            base_rate = 50
            multiplier = random.uniform(1.2, 1.8) if is_peak else 1.0
            hourly_rate = round(base_rate * multiplier, 2)
            
            lead_time = random.uniform(0, 48)
            cancelled = random.random() < (0.1 + lead_time / 400)
            status = 'cancelled' if cancelled else ('completed' if days_ago > 0 else 'active')
            
            booking = Booking(
                user_id=user.id,
                slot_id=slot.id,
                vehicle_number=f'KL-{random.randint(1,14):02d}-{chr(random.randint(65,90))}-{random.randint(1000,9999)}',
                start_time=start_time,
                end_time=end_time,
                duration_hours=duration,
                hourly_rate=hourly_rate,
                total_price=hourly_rate * duration,
                status=status,
                cancelled=cancelled
            )
            db.session.add(booking)
        
        db.session.commit()
        
        print(f'Created {BookingHistory.query.count()} booking history records')
        print(f'Created {Booking.query.count()} actual bookings')
        active = Booking.query.filter_by(status='active').count()
        completed = Booking.query.filter_by(status='completed').count()
        cancelled = Booking.query.filter_by(cancelled=True).count()
        print(f'  - Active: {active}')
        print(f'  - Completed: {completed}')
        print(f'  - Cancelled: {cancelled}')

if __name__ == '__main__':
    populate_data()

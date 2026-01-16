"""
Generate Optimized Training Data for ML Models
Creates data with stronger, learnable patterns for improved accuracy
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from database.models import User, ParkingSlot, Booking, BookingHistory
from datetime import datetime, timedelta
import random
import numpy as np

def generate_optimized_data():
    with app.app_context():
        # Clear existing data
        Booking.query.delete()
        BookingHistory.query.delete()
        db.session.commit()
        
        users = User.query.all()
        slots = ParkingSlot.query.all()
        
        print("=" * 60)
        print("GENERATING OPTIMIZED ML TRAINING DATA")
        print("=" * 60)
        
        random.seed(42)
        np.random.seed(42)
        base_date = datetime.now() - timedelta(days=90)
        
        # ================================================================
        # 1. BOOKING HISTORY - Optimized for all ML models
        # ================================================================
        print("\n1. Generating Booking History (500 records)...")
        
        history_records = []
        
        for i in range(500):
            timestamp = base_date + timedelta(
                days=random.randint(0, 89),
                hours=random.randint(6, 22),
                minutes=random.randint(0, 59)
            )
            
            hour = timestamp.hour
            day = timestamp.weekday()
            
            # --------------------------------------------------------
            # OCCUPANCY PATTERNS (for Peak Hour Predictor)
            # Strong patterns: weekday peaks, weekend lows
            # --------------------------------------------------------
            if day < 5:  # Weekday
                if 9 <= hour <= 11:  # Morning peak
                    base_occ = 0.85
                elif 14 <= hour <= 17:  # Afternoon peak
                    base_occ = 0.80
                elif 12 <= hour <= 13:  # Lunch dip
                    base_occ = 0.60
                elif hour < 8 or hour > 20:  # Early/late
                    base_occ = 0.25
                else:
                    base_occ = 0.55
            else:  # Weekend
                if 11 <= hour <= 15:  # Weekend midday
                    base_occ = 0.50
                else:
                    base_occ = 0.30
            
            # Add some noise
            occupied = random.random() < (base_occ + np.random.normal(0, 0.1))
            
            # --------------------------------------------------------
            # DURATION PATTERNS (for Anomaly Detector)
            # Normal: 1-4 hours, Anomalies: 8+ hours
            # --------------------------------------------------------
            if random.random() < 0.08:  # 8% anomalies
                # ANOMALY: Very long duration or unusual patterns
                duration = round(random.uniform(10, 24), 1)
            elif random.random() < 0.05:  # 5% edge cases
                # Edge: Slightly unusual
                duration = round(random.uniform(6, 10), 1)
            else:
                # NORMAL: Typical parking duration
                duration = round(np.random.gamma(2, 1) + 0.5, 1)  # Peaks around 2-3 hours
                duration = min(duration, 6)  # Cap at 6
            
            # --------------------------------------------------------
            # CANCELLATION PATTERNS (for Cancellation Predictor)
            # Strong correlation: lead_time + user_history -> cancellation
            # --------------------------------------------------------
            lead_time = round(random.uniform(0, 72), 1)
            user = random.choice(users)
            user_booking_count = user.booking_count
            
            # Cancellation probability formula:
            # - Higher lead time = higher cancel chance
            # - More experienced users = lower cancel chance
            # - Weekend bookings = slightly higher cancel chance
            base_cancel_prob = 0.05
            lead_time_factor = (lead_time / 72) * 0.35  # Up to 35% from lead time
            experience_factor = max(0, (10 - user_booking_count) / 50)  # New users cancel more
            weekend_factor = 0.05 if day >= 5 else 0
            
            cancel_prob = base_cancel_prob + lead_time_factor + experience_factor + weekend_factor
            cancel_prob = min(cancel_prob, 0.6)  # Cap at 60%
            
            cancelled = random.random() < cancel_prob
            
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
            history_records.append(record)
        
        db.session.add_all(history_records)
        
        # Calculate stats
        cancelled_count = sum(1 for r in history_records if r.cancelled)
        anomaly_count = sum(1 for r in history_records if r.duration_hours > 8)
        
        print(f"   - Total records: 500")
        print(f"   - Cancellation rate: {cancelled_count/500*100:.1f}%")
        print(f"   - Anomaly rate: {anomaly_count/500*100:.1f}%")
        
        # ================================================================
        # 2. ACTUAL BOOKINGS - Realistic distribution
        # ================================================================
        print("\n2. Generating Actual Bookings (100 records)...")
        
        for i in range(100):
            user = random.choice(users)
            slot = random.choice(slots)
            
            days_ago = random.randint(0, 60)
            hour_start = random.randint(6, 20)
            start_time = datetime.now() - timedelta(days=days_ago)
            start_time = start_time.replace(hour=hour_start, minute=random.randint(0, 59))
            
            duration = random.choice([1, 1, 2, 2, 2, 3, 3, 4])
            end_time = start_time + timedelta(hours=duration)
            
            # Dynamic pricing
            hour = start_time.hour
            day = start_time.weekday()
            is_peak = (9 <= hour <= 11 or 14 <= hour <= 17) and day < 5
            base_rate = 50
            multiplier = random.uniform(1.3, 1.8) if is_peak else random.uniform(0.9, 1.1)
            hourly_rate = round(base_rate * multiplier, 2)
            
            # Cancellation based on lead time
            lead_time = random.uniform(0, 48)
            cancel_prob = 0.08 + (lead_time / 150)
            cancelled = random.random() < cancel_prob
            
            if cancelled:
                status = 'cancelled'
            elif days_ago > 0:
                status = 'completed'
            else:
                status = 'active'
            
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
        
        # Final stats
        total_bookings = Booking.query.count()
        active = Booking.query.filter_by(status='active').count()
        completed = Booking.query.filter_by(status='completed').count()
        cancelled = Booking.query.filter_by(cancelled=True).count()
        
        print(f"   - Total bookings: {total_bookings}")
        print(f"   - Active: {active}")
        print(f"   - Completed: {completed}")
        print(f"   - Cancelled: {cancelled}")
        
        print("\n" + "=" * 60)
        print("DATA GENERATION COMPLETE!")
        print("=" * 60)
        print(f"\nBooking History: {BookingHistory.query.count()} records")
        print(f"Actual Bookings: {Booking.query.count()} records")
        print("\nData patterns optimized for:")
        print("  ✓ Peak Hour Predictor - Strong hour/day occupancy correlation")
        print("  ✓ Cancellation Predictor - Lead time + experience correlation")
        print("  ✓ Anomaly Detector - Clear normal vs anomaly duration split")

if __name__ == '__main__':
    generate_optimized_data()

"""
Kaggle-Style Parking Data Population Script
Generates 1500+ realistic booking records based on Smart Parking Management Dataset schema
"""

import sys
import os
import random
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask
from database.models import db, User, ParkingSlot, Booking, BookingHistory


def create_app():
    """Create Flask app for database operations"""
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:root1234@localhost/kerala_smartpark'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_POOL_RECYCLE'] = 280
    db.init_app(app)
    return app


# Kerala-style names for realistic user generation
KERALA_FIRST_NAMES = [
    'Arun', 'Vishnu', 'Anand', 'Rajesh', 'Suresh', 'Priya', 'Lakshmi', 'Meera',
    'Sreeja', 'Deepa', 'Nair', 'Menon', 'Pillai', 'Kumar', 'Rajan', 'Gopan',
    'Sreekanth', 'Vinod', 'Manoj', 'Asha', 'Bindu', 'Divya', 'Jayakumar',
    'Krishnan', 'Mohan', 'Nandini', 'Padma', 'Ramesh', 'Satheesh', 'Uma'
]

KERALA_LAST_NAMES = [
    'Nair', 'Menon', 'Pillai', 'Kurup', 'Panicker', 'Warrier', 'Namboothiri',
    'Kartha', 'Thampi', 'Iyer', 'Varma', 'Pothan', 'Cherian', 'Thomas', 'Mathew'
]

# Vehicle types with realistic distribution
VEHICLE_TYPES = {
    'Car': 0.60,           # 60% cars
    'Motorcycle': 0.20,    # 20% motorcycles  
    'Electric Vehicle': 0.10,  # 10% EVs
    'SUV': 0.08,           # 8% SUVs
    'Truck': 0.02          # 2% trucks
}

# Kerala vehicle registration prefixes
KL_DISTRICTS = ['01', '02', '03', '04', '05', '07', '08', '09', '10', '11', '12', '13', '14', '15']

# User types
USER_TYPES = ['Registered', 'Visitor', 'Staff', 'VIP']


def generate_kerala_vehicle_number():
    """Generate a realistic Kerala vehicle registration number"""
    district = random.choice(KL_DISTRICTS)
    series = random.choice(['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'J', 'K', 'L', 'M', 'N', 'P', 'R', 'S', 'T', 'V', 'W', 'X', 'Y', 'Z'])
    number = random.randint(1000, 9999)
    return f"KL-{district}-{series}{series}-{number}"


def get_weighted_choice(choices_dict):
    """Select from weighted dictionary"""
    items = list(choices_dict.keys())
    weights = list(choices_dict.values())
    return random.choices(items, weights=weights, k=1)[0]


def generate_occupancy_rate(hour, day_of_week):
    """
    Generate realistic occupancy probability based on time patterns.
    Based on Kaggle Smart Parking dataset patterns.
    """
    # Base rate
    base_rate = 0.3
    
    # Business hours boost (9 AM - 6 PM)
    if 9 <= hour <= 18:
        base_rate += 0.35
    
    # Peak hours extra boost
    if hour in [10, 11, 14, 15]:  # 10-11 AM and 2-3 PM peaks
        base_rate += 0.15
    
    # Early morning / late night reduction
    if hour < 6 or hour > 22:
        base_rate -= 0.2
    
    # Weekend reduction
    if day_of_week >= 5:  # Saturday, Sunday
        base_rate -= 0.15
    
    # Monday/Friday slight boost (start/end of week activity)
    if day_of_week in [0, 4]:
        base_rate += 0.05
    
    return max(0.1, min(0.95, base_rate))


def generate_duration(vehicle_type, hour):
    """Generate realistic parking duration based on vehicle type and time"""
    if vehicle_type == 'Motorcycle':
        # Shorter stays
        return round(random.uniform(0.5, 3.0), 1)
    elif vehicle_type in ['Electric Vehicle']:
        # Longer for charging
        return round(random.uniform(1.5, 6.0), 1)
    elif vehicle_type == 'Truck':
        # Delivery - short stays
        return round(random.uniform(0.25, 1.5), 1)
    else:
        # Regular cars/SUVs
        if 9 <= hour <= 17:  # Work hours - longer parking
            return round(random.uniform(2.0, 8.0), 1)
        else:
            return round(random.uniform(0.5, 4.0), 1)


def populate_users(count=50):
    """Generate additional realistic users"""
    print(f"\n📝 Generating {count} additional users...")
    
    existing_emails = {u.email for u in User.query.all()}
    new_users = []
    
    for i in range(count):
        first = random.choice(KERALA_FIRST_NAMES)
        last = random.choice(KERALA_LAST_NAMES)
        email = f"{first.lower()}.{last.lower()}{random.randint(1, 99)}@gmail.com"
        
        # Ensure unique email
        while email in existing_emails:
            email = f"{first.lower()}.{last.lower()}{random.randint(100, 999)}@gmail.com"
        
        existing_emails.add(email)
        
        user = User(
            email=email,
            name=f"{first} {last}",
            is_admin=False,
            booking_count=random.randint(1, 30)
        )
        user.set_password('user123')
        new_users.append(user)
    
    db.session.add_all(new_users)
    db.session.commit()
    print(f"  ✓ Created {count} users with Kerala-style names")
    return new_users


def populate_booking_history(count=1500):
    """
    Generate realistic booking history data based on Kaggle Smart Parking schema.
    Features: timestamp, slot_id, user_id, occupancy, vehicle_type, duration, etc.
    """
    print(f"\n📊 Generating {count} booking history records (Kaggle-style)...")
    
    random.seed(42)  # Reproducible results
    
    # Date range: Last 6 months (Jan 2024 - Jun 2024 style)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=180)
    
    records = []
    
    for i in range(count):
        # Random timestamp within range
        days_offset = random.randint(0, 179)
        hour = random.randint(0, 23)
        minute = random.randint(0, 59)
        
        timestamp = start_date + timedelta(
            days=days_offset,
            hours=hour,
            minutes=minute
        )
        
        day_of_week = timestamp.weekday()
        
        # Generate weighted vehicle type
        vehicle_type = get_weighted_choice(VEHICLE_TYPES)
        
        # Occupancy based on realistic patterns
        occupancy_prob = generate_occupancy_rate(hour, day_of_week)
        occupied = random.random() < occupancy_prob
        
        # Duration
        duration = generate_duration(vehicle_type, hour) if occupied else 0
        
        # Cancellation rate (~12% overall, higher for short bookings)
        cancelled = False
        if occupied:
            cancel_prob = 0.08 if duration > 2 else 0.18
            cancelled = random.random() < cancel_prob
        
        # Lead time (how far in advance was booking made)
        lead_time = round(random.uniform(0, 72), 1)  # 0-72 hours ahead
        
        record = BookingHistory(
            timestamp=timestamp,
            slot_id=f'slot_{random.randint(1, 20)}',
            user_id=f'user_{random.randint(1, 50)}',
            occupied=occupied,
            cancelled=cancelled,
            duration_hours=duration,
            lead_time_hours=lead_time,
            hour=hour,
            day_of_week=day_of_week
        )
        records.append(record)
        
        # Progress indicator
        if (i + 1) % 500 == 0:
            print(f"  ... Generated {i + 1}/{count} records")
    
    db.session.add_all(records)
    db.session.commit()
    print(f"  ✓ Created {count} booking history records")
    
    # Print statistics
    occupied_count = sum(1 for r in records if r.occupied)
    cancelled_count = sum(1 for r in records if r.cancelled)
    print(f"\n  📈 Statistics:")
    print(f"     - Occupied bookings: {occupied_count} ({100*occupied_count/count:.1f}%)")
    print(f"     - Cancelled bookings: {cancelled_count} ({100*cancelled_count/count:.1f}%)")


def populate_sample_bookings(count=100):
    """Generate sample active/completed bookings for user view"""
    print(f"\n🎫 Generating {count} sample bookings...")
    
    users = User.query.filter_by(is_admin=False).all()
    slots = ParkingSlot.query.all()
    
    if not users or not slots:
        print("  ⚠ Need users and slots first!")
        return
    
    bookings = []
    now = datetime.now()
    
    for i in range(count):
        user = random.choice(users)
        slot = random.choice(slots)
        
        # Random start time within past 30 days to future 7 days
        days_offset = random.randint(-30, 7)
        start_time = now + timedelta(
            days=days_offset,
            hours=random.randint(6, 20),
            minutes=random.choice([0, 15, 30, 45])
        )
        
        duration = random.choice([1, 2, 3, 4, 5, 6, 8])
        end_time = start_time + timedelta(hours=duration)
        
        # Status based on timing
        if end_time < now:
            status = 'completed'
        elif start_time <= now <= end_time:
            status = 'active'
        else:
            status = 'active'  # Future booking
        
        # Some cancellations
        cancelled = random.random() < 0.10
        if cancelled:
            status = 'cancelled'
        
        hourly_rate = 30.0  # ₹30/hour
        
        booking = Booking(
            user_id=user.id,
            slot_id=slot.id,
            vehicle_number=generate_kerala_vehicle_number(),
            start_time=start_time,
            end_time=end_time,
            duration_hours=duration,
            hourly_rate=hourly_rate,
            total_price=duration * hourly_rate,
            status=status,
            cancelled=cancelled
        )
        bookings.append(booking)
    
    db.session.add_all(bookings)
    db.session.commit()
    print(f"  ✓ Created {count} sample bookings")


def verify_data():
    """Verify database has expected data"""
    app = create_app()
    
    with app.app_context():
        users = User.query.count()
        slots = ParkingSlot.query.count()
        bookings = Booking.query.count()
        history = BookingHistory.query.count()
        
        print("\n" + "=" * 50)
        print("📊 Database Verification")
        print("=" * 50)
        print(f"  Users:           {users}")
        print(f"  Parking Slots:   {slots}")
        print(f"  Bookings:        {bookings}")
        print(f"  History Records: {history}")
        print("=" * 50)
        
        return {
            'users': users,
            'slots': slots,
            'bookings': bookings,
            'history': history
        }


def main():
    """Main population function"""
    print("\n" + "=" * 60)
    print("🚗 Kerala SmartPark - Kaggle-Style Data Population")
    print("=" * 60)
    
    app = create_app()
    
    with app.app_context():
        # Clear existing history for fresh data
        print("\n🗑️  Clearing existing booking history...")
        BookingHistory.query.delete()
        db.session.commit()
        print("  ✓ Cleared old history data")
        
        # Populate users
        populate_users(50)
        
        # Populate history (main Kaggle-style data)
        populate_booking_history(1500)
        
        # Populate sample bookings
        populate_sample_bookings(100)
        
        # Final verification
        verify_data()
        
        print("\n✅ Data population complete!")
        print("   Run 'python app.py' and check the admin analytics page.")


if __name__ == '__main__':
    main()

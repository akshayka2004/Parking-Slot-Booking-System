"""
Comprehensive Data Population Script
Generates realistic parking data based on patterns from Kaggle parking datasets
Populates: users, bookings, booking_history with thousands of records
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask
from database.models import db, User, ParkingSlot, Booking, BookingHistory
from datetime import datetime, timedelta
import random
import numpy as np

# Kerala-style names for realistic user data
KERALA_FIRST_NAMES = [
    "Arun", "Vijay", "Sreejith", "Anoop", "Rajesh", "Suresh", "Mahesh", "Ramesh",
    "Priya", "Lakshmi", "Anjali", "Divya", "Nisha", "Meera", "Deepa", "Ammu",
    "Vishnu", "Krishna", "Hari", "Gopan", "Sajan", "Biju", "Rajan", "Mohan",
    "Athira", "Arya", "Aparna", "Reshma", "Sreelakshmi", "Pooja", "Kavya", "Maya"
]

KERALA_LAST_NAMES = [
    "Nair", "Menon", "Pillai", "Kurup", "Panicker", "Varma", "Kumar", "Iyer",
    "Krishnan", "Rajan", "Mohan", "Gopal", "Subramaniam", "Chandran", "Kutty",
    "Das", "Sen", "Thomas", "Joseph", "Abraham", "Mathew", "George", "John"
]

# Kerala vehicle registration patterns (KL-XX-Y-XXXX)
KERALA_RTO_CODES = ["01", "02", "03", "04", "05", "07", "08", "09", "10", "11", 
                    "12", "13", "14", "15", "16", "17", "18", "19", "20", "21"]

def generate_kerala_vehicle():
    """Generate a random Kerala vehicle registration number"""
    rto = random.choice(KERALA_RTO_CODES)
    series = random.choice(["A", "B", "C", "D", "E", "F", "G", "H", "J", "K", "L", "M", "N", "P", "R", "S", "T", "U", "V", "W", "X", "Y", "Z"])
    series2 = random.choice(["A", "B", "C", "D", "E", "F", "G", "H", "J", "K", "L", "M", "N", "P", "R", "S", "T", "U", "V", "W", "X", "Y", "Z"])
    number = random.randint(1000, 9999)
    return f"KL-{rto}-{series}{series2}-{number}"

def generate_email(first_name, last_name, index):
    """Generate realistic email"""
    domains = ["gmail.com", "yahoo.com", "outlook.com", "hotmail.com"]
    patterns = [
        f"{first_name.lower()}.{last_name.lower()}@{random.choice(domains)}",
        f"{first_name.lower()}{random.randint(1, 999)}@{random.choice(domains)}",
        f"{first_name.lower()}_{last_name.lower()}@{random.choice(domains)}",
    ]
    return random.choice(patterns)

def create_app():
    """Create Flask app for database operations"""
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:root1234@localhost/kerala_smartpark'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_POOL_RECYCLE'] = 280
    db.init_app(app)
    return app

def populate_users(count=100):
    """Create realistic Kerala users"""
    print(f"\n📝 Creating {count} users...")
    
    users_created = 0
    for i in range(count):
        first_name = random.choice(KERALA_FIRST_NAMES)
        last_name = random.choice(KERALA_LAST_NAMES)
        name = f"{first_name} {last_name}"
        email = generate_email(first_name, last_name, i)
        
        # Check if email already exists
        if User.query.filter_by(email=email).first():
            continue
        
        user = User(
            email=email,
            name=name,
            is_admin=False,
            booking_count=random.randint(0, 50)
        )
        user.set_password("user123")  # Default password for demo
        db.session.add(user)
        users_created += 1
    
    db.session.commit()
    print(f"   ✓ Created {users_created} users")
    return users_created

def populate_bookings(count=500):
    """Create realistic booking data spanning 6 months"""
    print(f"\n📅 Creating {count} bookings...")
    
    users = User.query.filter_by(is_admin=False).all()
    slots = ParkingSlot.query.all()
    
    if not users or not slots:
        print("   ✗ No users or slots found!")
        return 0
    
    # Time range: last 6 months to now
    end_date = datetime.now()
    start_date = end_date - timedelta(days=180)
    
    # Pricing based on time of day
    base_price = 50  # ₹50/hr
    
    bookings_created = 0
    
    for _ in range(count):
        # Random date within range
        days_ago = random.randint(0, 180)
        booking_date = end_date - timedelta(days=days_ago)
        
        # Peak hours have more bookings (9-11 AM, 12-2 PM, 5-7 PM)
        hour_weights = [0.2, 0.1, 0.1, 0.1, 0.1, 0.3,  # 0-5 AM
                       0.5, 0.8, 1.5, 2.0, 1.8, 1.5,  # 6-11 AM
                       1.8, 1.5, 1.2, 1.0, 1.5, 2.0,  # 12-5 PM
                       1.8, 1.5, 1.0, 0.8, 0.5, 0.3]  # 6-11 PM
        hours = list(range(24))
        hour = random.choices(hours, weights=hour_weights)[0]
        
        start_time = booking_date.replace(hour=hour, minute=random.randint(0, 59), second=0, microsecond=0)
        
        # Duration: mostly 1-4 hours, some longer
        duration_weights = [0.3, 0.4, 0.2, 0.05, 0.03, 0.01, 0.01]
        durations = [1, 2, 3, 4, 6, 8, 10]
        duration = random.choices(durations, weights=duration_weights)[0]
        
        end_time = start_time + timedelta(hours=duration)
        
        # Calculate price with dynamic pricing
        occupancy_rate = random.uniform(0.3, 0.9)
        if occupancy_rate > 0.8:
            multiplier = 2.0
        elif occupancy_rate > 0.6:
            multiplier = 1.5
        else:
            multiplier = 1.0
        
        hourly_rate = base_price * multiplier
        total_price = hourly_rate * duration
        
        # 15% cancellation rate
        cancelled = random.random() < 0.15
        status = 'cancelled' if cancelled else ('completed' if start_time < datetime.now() else 'active')
        
        # Create booking
        booking = Booking(
            user_id=random.choice(users).id,
            slot_id=random.choice(slots).id,
            vehicle_number=generate_kerala_vehicle(),
            start_time=start_time,
            end_time=end_time,
            duration_hours=duration,
            hourly_rate=hourly_rate,
            total_price=total_price,
            status=status,
            cancelled=cancelled,
            created_at=start_time - timedelta(hours=random.randint(1, 48))
        )
        
        db.session.add(booking)
        bookings_created += 1
        
        if bookings_created % 100 == 0:
            db.session.commit()
            print(f"   ... {bookings_created} bookings created")
    
    db.session.commit()
    print(f"   ✓ Created {bookings_created} bookings")
    return bookings_created

def populate_booking_history(count=2000):
    """Create extensive historical data for ML model training"""
    print(f"\n📊 Creating {count} historical records for ML...")
    
    # Time range: last 12 months
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    
    records_created = 0
    
    for _ in range(count):
        days_ago = random.randint(0, 365)
        timestamp = end_date - timedelta(
            days=days_ago,
            hours=random.randint(6, 22),
            minutes=random.randint(0, 59)
        )
        
        hour = timestamp.hour
        day_of_week = timestamp.weekday()
        
        # Simulate realistic occupancy patterns
        # Weekdays busier during work hours
        if day_of_week < 5:  # Weekday
            if 9 <= hour <= 18:
                occupied = random.random() < 0.75
            else:
                occupied = random.random() < 0.35
        else:  # Weekend
            if 10 <= hour <= 20:
                occupied = random.random() < 0.65
            else:
                occupied = random.random() < 0.25
        
        # Duration with some anomalies for ML detection
        if random.random() < 0.05:  # 5% anomalies
            duration = round(random.uniform(10, 24), 1)
        else:
            duration = round(random.uniform(0.5, 6), 1)
        
        # Lead time (hours before booking)
        lead_time = round(random.uniform(0, 72), 1)
        
        record = BookingHistory(
            timestamp=timestamp,
            slot_id=f'slot_{random.randint(1, 20)}',
            user_id=f'user_{random.randint(1, 100)}',
            occupied=occupied,
            cancelled=random.random() < 0.15,
            duration_hours=duration,
            lead_time_hours=lead_time,
            hour=hour,
            day_of_week=day_of_week
        )
        
        db.session.add(record)
        records_created += 1
        
        if records_created % 500 == 0:
            db.session.commit()
            print(f"   ... {records_created} history records created")
    
    db.session.commit()
    print(f"   ✓ Created {records_created} historical records")
    return records_created

def update_user_booking_counts():
    """Update booking counts based on actual bookings"""
    print("\n🔄 Updating user booking counts...")
    
    users = User.query.filter_by(is_admin=False).all()
    for user in users:
        count = Booking.query.filter_by(user_id=user.id).count()
        user.booking_count = count
    
    db.session.commit()
    print("   ✓ Updated all user booking counts")

def calculate_statistics():
    """Print database statistics"""
    print("\n" + "=" * 50)
    print("DATABASE STATISTICS")
    print("=" * 50)
    
    total_users = User.query.count()
    total_slots = ParkingSlot.query.count()
    total_bookings = Booking.query.count()
    total_history = BookingHistory.query.count()
    
    cancelled_bookings = Booking.query.filter_by(cancelled=True).count()
    completed_bookings = Booking.query.filter_by(status='completed').count()
    
    total_revenue = db.session.query(db.func.sum(Booking.total_price)).filter_by(cancelled=False).scalar() or 0
    avg_duration = db.session.query(db.func.avg(Booking.duration_hours)).scalar() or 0
    
    print(f"Users: {total_users}")
    print(f"Parking Slots: {total_slots}")
    print(f"Total Bookings: {total_bookings}")
    print(f"  - Completed: {completed_bookings}")
    print(f"  - Cancelled: {cancelled_bookings}")
    print(f"  - Cancellation Rate: {cancelled_bookings/total_bookings*100:.1f}%")
    print(f"Historical Records (ML): {total_history}")
    print(f"Total Revenue: ₹{total_revenue:,.2f}")
    print(f"Average Duration: {avg_duration:.1f} hours")
    print("=" * 50)

def main():
    """Main function to populate all data"""
    app = create_app()
    
    with app.app_context():
        print("=" * 50)
        print("KERALA SMARTPARK - DATA POPULATION")
        print("=" * 50)
        
        # Clear existing booking data (keep users and slots)
        print("\n🗑️  Clearing existing booking data...")
        Booking.query.delete()
        BookingHistory.query.delete()
        db.session.commit()
        print("   ✓ Cleared old data")
        
        # Populate data - SCALED UP for ML training accuracy
        populate_users(200)           # 200 users
        populate_bookings(2000)       # 2000 bookings (6 months)
        populate_booking_history(10000)  # 10,000 ML training records (1 year)
        update_user_booking_counts()
        
        # Show statistics
        calculate_statistics()
        
        print("\n✅ DATA POPULATION COMPLETE!")
        print("Check phpMyAdmin to see your data.")

if __name__ == '__main__':
    main()

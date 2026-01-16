"""
Database Initialization Script
Creates tables and seeds initial data
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask
from database.models import db, User, ParkingSlot, Booking, BookingHistory
from datetime import datetime, timedelta
import random


def create_app():
    """Create Flask app for database initialization"""
    app = Flask(__name__)
    # SQLite for local development
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///parking.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    return app


def init_database():
    """Initialize database with tables"""
    app = create_app()
    
    with app.app_context():
        # Create all tables
        db.create_all()
        print("✓ Database tables created")
        
        # Check if already seeded
        if User.query.first() is not None:
            print("! Database already contains data. Skipping seed.")
            return
        
        # Seed users
        seed_users()
        
        # Seed parking slots
        seed_slots()
        
        # Seed historical data for ML
        seed_booking_history()
        
        print("\n✓ Database initialization complete!")
        print(f"  Database file: parking.db")


def seed_users():
    """Create default admin and demo user"""
    print("\nSeeding users...")
    
    # Admin user
    admin = User(
        email='admin@parking.com',
        name='Admin User',
        is_admin=True,
        booking_count=50
    )
    admin.set_password('admin123')
    db.session.add(admin)
    
    # Demo user
    user = User(
        email='user@parking.com',
        name='John Doe',
        is_admin=False,
        booking_count=5
    )
    user.set_password('user123')
    db.session.add(user)
    
    db.session.commit()
    print(f"  ✓ Created admin: admin@parking.com / admin123")
    print(f"  ✓ Created user: user@parking.com / user123")


def seed_slots():
    """Create 20 parking slots"""
    print("\nSeeding parking slots...")
    
    for i in range(1, 21):
        row = (i - 1) // 4 + 1
        col = (i - 1) % 4 + 1
        
        slot = ParkingSlot(
            slot_number=f'slot_{i}',
            row=row,
            column=col,
            is_occupied=False
        )
        db.session.add(slot)
    
    db.session.commit()
    print(f"  ✓ Created 20 parking slots (5 rows x 4 columns)")


def seed_booking_history():
    """Generate historical booking data for ML models"""
    print("\nSeeding booking history for ML training...")
    
    random.seed(42)
    base_date = datetime.now() - timedelta(days=30)
    
    records = []
    for _ in range(100):
        timestamp = base_date + timedelta(
            days=random.randint(0, 29),
            hours=random.randint(6, 22),
            minutes=random.randint(0, 59)
        )
        
        # Peak hour occupancy simulation
        hour = timestamp.hour
        if 9 <= hour <= 18:
            occupied = random.random() < 0.7
        else:
            occupied = random.random() < 0.4
        
        # Duration with some anomalies
        if random.random() < 0.05:
            duration = round(random.uniform(10, 24), 1)  # Anomaly
        else:
            duration = round(random.uniform(0.5, 8), 1)  # Normal
        
        record = BookingHistory(
            timestamp=timestamp,
            slot_id=f'slot_{random.randint(1, 20)}',
            user_id=f'user_{random.randint(1, 50)}',
            occupied=occupied,
            cancelled=random.random() < 0.15,
            duration_hours=duration,
            lead_time_hours=round(random.uniform(0, 48), 1),
            hour=hour,
            day_of_week=timestamp.weekday()
        )
        records.append(record)
    
    db.session.add_all(records)
    db.session.commit()
    print(f"  ✓ Created 100 historical booking records")


def reset_database():
    """Drop and recreate all tables (use with caution!)"""
    app = create_app()
    
    with app.app_context():
        print("⚠ Dropping all tables...")
        db.drop_all()
        print("✓ Tables dropped")
        
        print("\nRecreating database...")
        init_database()


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Initialize parking database')
    parser.add_argument('--reset', action='store_true', 
                        help='Reset database (drops all data!)')
    args = parser.parse_args()
    
    print("=" * 50)
    print("Smart Parking System - Database Initialization")
    print("=" * 50)
    
    if args.reset:
        confirm = input("⚠ This will DELETE all data. Type 'yes' to confirm: ")
        if confirm.lower() == 'yes':
            reset_database()
        else:
            print("Cancelled.")
    else:
        init_database()

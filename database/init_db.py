"""
Database Initialization Script
Creates tables and seeds initial data for multi-location parking system
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask
from database.models import db, User, Location, ParkingLot, ParkingLevel, ParkingSlot, Booking, BookingHistory, ParkingConfiguration
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
        
        # Seed parking configurations
        seed_configurations()
        
        # Seed location hierarchy
        seed_locations()
        
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


def seed_configurations():
    """Create parking configuration templates"""
    print("\nSeeding parking configurations...")
    
    configs = [
        ParkingConfiguration(
            name='Compact',
            description='Small lot with 4×4 grid per level',
            num_levels=2,
            rows_per_level=4,
            columns_per_level=4
        ),
        ParkingConfiguration(
            name='Standard',
            description='Medium lot with 6×5 grid per level',
            num_levels=2,
            rows_per_level=6,
            columns_per_level=5
        ),
        ParkingConfiguration(
            name='Large',
            description='Large lot with 8×6 grid per level',
            num_levels=3,
            rows_per_level=8,
            columns_per_level=6
        ),
        ParkingConfiguration(
            name='Express',
            description='Single level quick access lot',
            num_levels=1,
            rows_per_level=5,
            columns_per_level=4
        )
    ]
    
    db.session.add_all(configs)
    db.session.commit()
    print(f"  ✓ Created {len(configs)} parking configurations")


def seed_locations():
    """Create locations, parking lots, levels, and slots with varied configurations"""
    print("\nSeeding locations and parking hierarchy...")
    
    # Get configurations
    compact = ParkingConfiguration.query.filter_by(name='Compact').first()
    standard = ParkingConfiguration.query.filter_by(name='Standard').first()
    large = ParkingConfiguration.query.filter_by(name='Large').first()
    express = ParkingConfiguration.query.filter_by(name='Express').first()
    
    # Define locations with their details and configurations
    locations_data = [
        {
            'name': 'City Mall',
            'address': '123 Shopping Boulevard, Downtown',
            'description': 'Premium shopping destination with multi-level parking',
            'icon': 'bi-building',
            'lots': [
                {
                    'name': 'Basement Parking', 
                    'description': 'Underground parking with direct mall access', 
                    'config': compact,
                    'levels': ['B1', 'B2']
                },
                {
                    'name': 'Rooftop Parking', 
                    'description': 'Open-air parking with scenic views', 
                    'config': large,
                    'levels': ['R1', 'R2', 'R3']
                }
            ]
        },
        {
            'name': 'Airport Terminal',
            'address': '1 Aviation Way, Airport District',
            'description': 'Convenient parking for domestic and international travelers',
            'icon': 'bi-airplane',
            'lots': [
                {
                    'name': 'Short-Term Parking', 
                    'description': 'Hourly parking for quick pickups', 
                    'config': standard,
                    'levels': ['A', 'B']
                },
                {
                    'name': 'Long-Term Parking', 
                    'description': 'Daily/weekly parking for travelers', 
                    'config': large,
                    'levels': ['P1', 'P2', 'P3', 'P4']
                }
            ]
        },
        {
            'name': 'Central Hospital',
            'address': '500 Healthcare Drive, Medical District',
            'description': 'Parking for patients, visitors, and staff',
            'icon': 'bi-hospital',
            'lots': [
                {
                    'name': 'Visitor Parking', 
                    'description': 'Convenient parking near main entrance', 
                    'config': compact,
                    'levels': ['V1', 'V2']
                },
                {
                    'name': 'Emergency Parking', 
                    'description': 'Quick access to emergency department', 
                    'config': express,
                    'levels': ['E1']
                }
            ]
        }
    ]
    
    total_slots = 0
    total_levels = 0
    
    for loc_data in locations_data:
        # Create location
        location = Location(
            name=loc_data['name'],
            address=loc_data['address'],
            description=loc_data['description'],
            icon=loc_data['icon']
        )
        db.session.add(location)
        db.session.flush()
        
        for lot_data in loc_data['lots']:
            config = lot_data['config']
            
            # Create parking lot with configuration
            lot = ParkingLot(
                location_id=location.id,
                configuration_id=config.id,
                name=lot_data['name'],
                description=lot_data['description'],
                total_levels=len(lot_data['levels'])
            )
            db.session.add(lot)
            db.session.flush()
            
            for level_idx, level_name in enumerate(lot_data['levels']):
                # Create level with configuration-based dimensions
                level = ParkingLevel(
                    lot_id=lot.id,
                    level_name=level_name,
                    level_order=level_idx,
                    rows=config.rows_per_level,
                    columns=config.columns_per_level,
                    capacity=config.rows_per_level * config.columns_per_level
                )
                db.session.add(level)
                db.session.flush()
                total_levels += 1
                
                # Create slots based on configuration
                for row in range(1, config.rows_per_level + 1):
                    for col in range(1, config.columns_per_level + 1):
                        slot_num = (row - 1) * config.columns_per_level + col
                        slot = ParkingSlot(
                            level_id=level.id,
                            slot_number=f'{level_name}_{slot_num}',
                            row=row,
                            column=col,
                            is_occupied=False
                        )
                        db.session.add(slot)
                        total_slots += 1
    
    db.session.commit()
    print(f"  ✓ Created 3 locations")
    print(f"  ✓ Created 6 parking lots with varied configurations")
    print(f"  ✓ Created {total_levels} levels")
    print(f"  ✓ Created {total_slots} parking slots")


def seed_booking_history():
    """Generate historical booking data for ML models"""
    print("\nSeeding booking history for ML training...")
    
    random.seed(42)
    base_date = datetime.now() - timedelta(days=30)
    
    # Get some slots to reference
    slots = ParkingSlot.query.limit(50).all()
    if not slots:
        print("  ! No slots found, skipping booking history")
        return
    
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
        
        slot = random.choice(slots)
        record = BookingHistory(
            timestamp=timestamp,
            slot_id=slot.slot_number,
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

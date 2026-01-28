"""
Database Models for Smart Parking System
SQLAlchemy models for User, ParkingSlot, and Booking
"""

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

# Initialize SQLAlchemy (will be bound to app in app.py)
db = SQLAlchemy()


class User(UserMixin, db.Model):
    """User model for authentication and booking history"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    booking_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship to bookings
    bookings = db.relationship('Booking', backref='user', lazy='dynamic')
    
    def set_password(self, password):
        """Hash and set the user's password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Verify password against hash"""
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.email}>'


# ============================================================================
# Location Hierarchy Models
# ============================================================================

class ParkingConfiguration(db.Model):
    """Configuration template for parking lot grid layouts"""
    __tablename__ = 'parking_configurations'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)  # e.g., "Compact", "Standard", "Large"
    description = db.Column(db.String(200))
    num_levels = db.Column(db.Integer, default=2)
    rows_per_level = db.Column(db.Integer, default=6)
    columns_per_level = db.Column(db.Integer, default=5)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    parking_lots = db.relationship('ParkingLot', backref='configuration', lazy='dynamic')
    
    @property
    def slots_per_level(self):
        return self.rows_per_level * self.columns_per_level
    
    @property
    def total_capacity(self):
        return self.num_levels * self.slots_per_level
    
    def __repr__(self):
        return f'<ParkingConfiguration {self.name}>'


class Location(db.Model):
    """Geographic location (e.g., Mall, Airport, Hospital)"""
    __tablename__ = 'locations'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(255))
    description = db.Column(db.Text)
    image_url = db.Column(db.String(255))
    icon = db.Column(db.String(50), default='bi-geo-alt')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    parking_lots = db.relationship('ParkingLot', backref='location', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Location {self.name}>'


class ParkingLot(db.Model):
    """Parking lot within a location"""
    __tablename__ = 'parking_lots'
    
    id = db.Column(db.Integer, primary_key=True)
    location_id = db.Column(db.Integer, db.ForeignKey('locations.id'), nullable=False, index=True)
    configuration_id = db.Column(db.Integer, db.ForeignKey('parking_configurations.id'), nullable=True, index=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    total_levels = db.Column(db.Integer, default=2)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    levels = db.relationship('ParkingLevel', backref='parking_lot', lazy='dynamic', cascade='all, delete-orphan')
    
    def get_total_slots(self):
        """Get total number of slots in this lot"""
        return sum(level.slots.count() for level in self.levels)
    
    def get_available_slots(self):
        """Get number of available slots (calculated from active bookings)"""
        from datetime import datetime
        now = datetime.now()
        total = 0
        for level in self.levels:
            for slot in level.slots:
                # Check if slot has active booking
                active = Booking.query.filter(
                    Booking.slot_id == slot.id,
                    Booking.cancelled == False,
                    Booking.start_time <= now,
                    Booking.end_time > now
                ).first()
                if not active:
                    total += 1
        return total
    
    def __repr__(self):
        return f'<ParkingLot {self.name}>'


class ParkingLevel(db.Model):
    """Level within a parking lot (e.g., Level A, Level B)"""
    __tablename__ = 'parking_levels'
    
    id = db.Column(db.Integer, primary_key=True)
    lot_id = db.Column(db.Integer, db.ForeignKey('parking_lots.id'), nullable=False, index=True)
    level_name = db.Column(db.String(10), nullable=False)  # "A", "B", etc.
    level_order = db.Column(db.Integer, default=0)  # For sorting
    rows = db.Column(db.Integer, default=6)  # Number of rows in this level
    columns = db.Column(db.Integer, default=5)  # Number of columns in this level
    capacity = db.Column(db.Integer, default=30)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    slots = db.relationship('ParkingSlot', backref='level', lazy='dynamic', cascade='all, delete-orphan')
    
    def get_available_count(self):
        """Get number of available slots on this level"""
        from datetime import datetime
        now = datetime.now()
        available = 0
        for slot in self.slots:
            active = Booking.query.filter(
                Booking.slot_id == slot.id,
                Booking.cancelled == False,
                Booking.start_time <= now,
                Booking.end_time > now
            ).first()
            if not active:
                available += 1
        return available
    
    def __repr__(self):
        return f'<ParkingLevel {self.level_name}>'


class ParkingSlot(db.Model):
    """Parking slot model"""
    __tablename__ = 'parking_slots'
    
    id = db.Column(db.Integer, primary_key=True)
    level_id = db.Column(db.Integer, db.ForeignKey('parking_levels.id'), nullable=True, index=True)
    slot_number = db.Column(db.String(20), nullable=False)  # e.g., "A-01", "B-15"
    row = db.Column(db.Integer, nullable=False)
    column = db.Column(db.Integer, nullable=False)
    is_occupied = db.Column(db.Boolean, default=False)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship to bookings
    bookings = db.relationship('Booking', backref='slot', lazy='dynamic')
    
    @property
    def coordinates(self):
        """Get slot coordinates as tuple"""
        return (self.row, self.column)
    
    @property 
    def display_name(self):
        """Get human-readable slot name"""
        if self.level:
            return f"{self.level.level_name}-{self.slot_number.split('_')[-1].zfill(2)}"
        return self.slot_number
    
    def __repr__(self):
        return f'<ParkingSlot {self.slot_number}>'


class Booking(db.Model):
    """Booking model for parking reservations"""
    __tablename__ = 'bookings'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    slot_id = db.Column(db.Integer, db.ForeignKey('parking_slots.id'), nullable=False, index=True)
    
    vehicle_number = db.Column(db.String(20), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    duration_hours = db.Column(db.Float, nullable=False)
    
    # Pricing
    hourly_rate = db.Column(db.Float, nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    
    # Status
    status = db.Column(db.String(20), default='active')  # active, completed, cancelled
    cancelled = db.Column(db.Boolean, default=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    @property
    def is_active(self):
        """Check if booking is currently active"""
        now = datetime.utcnow()
        return (self.status == 'active' and 
                self.start_time <= now <= self.end_time and 
                not self.cancelled)
    
    def cancel(self):
        """Cancel the booking"""
        self.cancelled = True
        self.status = 'cancelled'
        # Update slot availability
        if self.slot:
            self.slot.is_occupied = False
    
    def __repr__(self):
        return f'<Booking {self.id} - Slot {self.slot_id}>'


class BookingHistory(db.Model):
    """Historical booking data for ML model training"""
    __tablename__ = 'booking_history'
    
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, nullable=False, index=True)
    slot_id = db.Column(db.String(20), nullable=False)
    user_id = db.Column(db.String(50), nullable=False)
    
    occupied = db.Column(db.Boolean, default=True)
    cancelled = db.Column(db.Boolean, default=False)
    duration_hours = db.Column(db.Float, nullable=False)
    lead_time_hours = db.Column(db.Float, default=0)
    
    hour = db.Column(db.Integer, nullable=False)  # 0-23
    day_of_week = db.Column(db.Integer, nullable=False)  # 0-6
    
    def __repr__(self):
        return f'<BookingHistory {self.id}>'

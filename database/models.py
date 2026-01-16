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


class ParkingSlot(db.Model):
    """Parking slot model"""
    __tablename__ = 'parking_slots'
    
    id = db.Column(db.Integer, primary_key=True)
    slot_number = db.Column(db.String(20), unique=True, nullable=False)  # e.g., "slot_1"
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

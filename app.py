"""
AI-Powered Smart Parking & Slot Booking System
Main Flask Application with SQLite Database
"""

from flask import Flask, render_template, redirect, url_for, request, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from datetime import datetime, timedelta
import random
import os

# Import Database
from database.models import db, User, Location, ParkingLot, ParkingLevel, ParkingSlot, Booking, BookingHistory, ParkingConfiguration

# Import ML Models
from models.peak_hour_predictor import PeakHourPredictor
from models.slot_recommender import SlotRecommender
from models.cancellation_predictor import CancellationPredictor
from models.dynamic_pricing import DynamicPricing
from models.anomaly_detector import AnomalyDetector

# Import CV Module
from cv.occupancy_detection import OccupancyDetector

# ============================================================================
# Flask App Configuration
# ============================================================================

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'

# Database Configuration - SQLite (local development)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///parking.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize Database
db.init_app(app)

# Flask-Login Setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Jinja2 filter for formatting slot numbers (A_1 -> A-01)
@app.template_filter('format_slot')
def format_slot(slot_number):
    """Convert A_1 to A-01 format"""
    if slot_number and '_' in slot_number:
        parts = slot_number.split('_')
        if len(parts) == 2:
            return f'{parts[0]}-{parts[1].zfill(2)}'
    return slot_number

# ============================================================================
# Initialize ML Models
# ============================================================================

peak_hour_predictor = PeakHourPredictor()
slot_recommender = SlotRecommender()
cancellation_predictor = CancellationPredictor()
dynamic_pricing = DynamicPricing()
anomaly_detector = AnomalyDetector()
occupancy_detector = OccupancyDetector()

# ============================================================================
# Helper Functions
# ============================================================================

def get_slots_data():
    """Get parking slots from database with current status based on active bookings"""
    slots = ParkingSlot.query.order_by(ParkingSlot.id).all()
    
    # If no slots in database, return empty list
    if not slots:
        return []
    
    now = datetime.now()
    slot_list = []
    for slot in slots:
        # Check if slot has an active booking right now
        active_booking = Booking.query.filter(
            Booking.slot_id == slot.id,
            Booking.cancelled == False,
            Booking.start_time <= now,
            Booking.end_time > now
        ).first()
        
        is_currently_occupied = active_booking is not None
        
        slot_list.append({
            'id': slot.slot_number,
            'db_id': slot.id,
            'row': slot.row,
            'column': slot.column,
            'occupied': is_currently_occupied,
            'distance': slot_recommender.get_slot_distance(slot.slot_number)
        })
    
    return slot_list

def get_parking_stats(slots):
    """Calculate parking statistics"""
    total = len(slots)
    occupied = sum(1 for s in slots if s['occupied'])
    available = total - occupied
    occupancy_rate = round(occupied / total * 100, 1) if total > 0 else 0
    
    return {
        'total': total,
        'occupied': occupied,
        'available': available,
        'occupancy_rate': occupancy_rate
    }

def update_slot_status(slot_id, is_occupied):
    """Update a slot's occupancy status"""
    slot = ParkingSlot.query.filter_by(slot_number=slot_id).first()
    if slot:
        slot.is_occupied = is_occupied
        db.session.commit()

def is_slot_available(slot_db_id, start_time, end_time):
    """Check if a slot is available for the given time range (no overlapping bookings)"""
    # Find any overlapping active bookings
    overlapping = Booking.query.filter(
        Booking.slot_id == slot_db_id,
        Booking.cancelled == False,
        Booking.start_time < end_time,  # Existing booking starts before new ends
        Booking.end_time > start_time   # Existing booking ends after new starts
    ).first()
    
    return overlapping is None

# ============================================================================
# Authentication Routes
# ============================================================================

@app.route('/')
def index():
    """Home page - redirect to features or login"""
    if current_user.is_authenticated:
        return redirect(url_for('features'))
    return redirect(url_for('login'))

@app.route('/features')
@login_required
def features():
    """Features landing page - showcases all system capabilities"""
    return render_template('features.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = request.form.get('remember', False)
        
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            login_user(user, remember=bool(remember))
            flash('Welcome back!', 'success')
            
            next_page = request.args.get('next')
            return redirect(next_page or url_for('features'))
        else:
            flash('Invalid email or password.', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Validation
        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'error')
            return render_template('register.html')
        
        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('register.html')
        
        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'error')
            return render_template('register.html')
        
        # Create new user in database
        new_user = User(email=email, name=name, is_admin=False, booking_count=0)
        new_user.set_password(password)
        
        db.session.add(new_user)
        db.session.commit()
        
        flash('Account created successfully! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    """User logout"""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

# ============================================================================
# Location Selection Routes
# ============================================================================

@app.route('/locations')
@login_required
def locations():
    """Location selection page"""
    all_locations = Location.query.all()
    
    # Calculate stats for each location
    locations_data = []
    for loc in all_locations:
        total_slots = 0
        available_slots = 0
        for lot in loc.parking_lots:
            total_slots += lot.get_total_slots()
            available_slots += lot.get_available_slots()
        
        locations_data.append({
            'id': loc.id,
            'name': loc.name,
            'address': loc.address,
            'description': loc.description,
            'icon': loc.icon,
            'total_slots': total_slots,
            'available_slots': available_slots,
            'lot_count': loc.parking_lots.count()
        })
    
    return render_template('locations.html', locations=locations_data)


@app.route('/location/<int:location_id>')
@login_required
def parking_lots(location_id):
    """Parking lots at a specific location"""
    location = Location.query.get_or_404(location_id)
    
    lots_data = []
    for lot in location.parking_lots:
        total_slots = lot.get_total_slots()
        available_slots = lot.get_available_slots()
        
        # Get level info
        levels_info = []
        for level in lot.levels.order_by(ParkingLevel.level_order):
            levels_info.append({
                'id': level.id,
                'name': level.level_name,
                'rows': level.rows,
                'columns': level.columns,
                'total': level.slots.count(),
                'available': level.get_available_count()
            })
        
        # Get configuration info
        config_name = lot.configuration.name if lot.configuration else 'Standard'
        
        lots_data.append({
            'id': lot.id,
            'name': lot.name,
            'description': lot.description,
            'total_levels': lot.total_levels,
            'total_slots': total_slots,
            'available_slots': available_slots,
            'occupancy_rate': round((total_slots - available_slots) / total_slots * 100) if total_slots > 0 else 0,
            'levels': levels_info,
            'config_name': config_name
        })
    
    return render_template('parking_lots.html', location=location, lots=lots_data)


@app.route('/lot/<int:lot_id>')
@login_required
def levels(lot_id):
    """Levels within a parking lot"""
    lot = ParkingLot.query.get_or_404(lot_id)
    location = lot.location
    
    levels_data = []
    for level in lot.levels.order_by(ParkingLevel.level_order):
        total = level.slots.count()
        available = level.get_available_count()
        
        levels_data.append({
            'id': level.id,
            'name': level.level_name,
            'order': level.level_order,
            'rows': level.rows,
            'columns': level.columns,
            'total': total,
            'available': available,
            'occupancy_rate': round((total - available) / total * 100) if total > 0 else 0
        })
    
    config_name = lot.configuration.name if lot.configuration else 'Standard'
    
    return render_template('levels.html', lot=lot, location=location, levels=levels_data, config_name=config_name)


# ============================================================================
# Dashboard Route (Level-Specific)
# ============================================================================

@app.route('/dashboard')
@login_required
def dashboard():
    """Redirect to locations - dashboard now requires a level"""
    return redirect(url_for('locations'))


@app.route('/level/<int:level_id>/dashboard')
@login_required
def level_dashboard(level_id):
    """Main dashboard with parking grid and ML insights for a specific level"""
    
    level = ParkingLevel.query.get_or_404(level_id)
    lot = level.parking_lot
    location = lot.location
    
    # Get slots for this level
    slots = []
    now = datetime.now()
    for slot in level.slots.order_by(ParkingSlot.row, ParkingSlot.column):
        # Check if slot has an active booking right now
        active_booking = Booking.query.filter(
            Booking.slot_id == slot.id,
            Booking.cancelled == False,
            Booking.start_time <= now,
            Booking.end_time > now
        ).first()
        
        is_currently_occupied = active_booking is not None
        
        slots.append({
            'id': slot.slot_number,
            'db_id': slot.id,
            'row': slot.row,
            'column': slot.column,
            'occupied': is_currently_occupied,
            'display_name': slot.display_name
        })
    
    stats = get_parking_stats(slots)
    
    # Get current time info
    current_hour = now.hour
    current_day = now.weekday()
    
    # Get ML predictions - Best times to park today
    best_times_raw = peak_hour_predictor.get_best_parking_times(current_day, top_n=3)
    best_times = [
        {'hour': hour, 'occupancy': round(occ * 100)}
        for hour, occ in best_times_raw
    ]
    
    # Current pricing based on predicted occupancy
    current_occupancy = peak_hour_predictor.predict(current_hour, current_day)
    price_info = dynamic_pricing.get_price(current_occupancy)
    tier = dynamic_pricing.get_price_tier(current_occupancy)
    
    pricing = {
        'hourly_rate': price_info['hourly_rate'],
        'multiplier': price_info['multiplier'],
        'is_surge_pricing': price_info['is_surge_pricing'],
        'tier': tier,
        'occupancy': round(current_occupancy * 100)
    }
    
    # Slot recommendations from available slots on this level
    available_slots = [s['id'] for s in slots if not s['occupied']]
    
    # Build recommendations manually since slot_recommender uses old data
    recommendations = []
    for s in slots:
        if not s['occupied']:
            recommendations.append({
                'slot_id': s['id'],
                'display_name': s['display_name'],
                'distance': s['row'] + s['column']  # Simple distance metric
            })
    recommendations.sort(key=lambda x: x['distance'])
    recommendations = recommendations[:5]
    
    # Breadcrumb data
    breadcrumb = {
        'location': {'id': location.id, 'name': location.name},
        'lot': {'id': lot.id, 'name': lot.name},
        'level': {'id': level.id, 'name': f'Level {level.level_name}'}
    }
    
    return render_template('dashboard.html',
                          slots=slots,
                          stats=stats,
                          best_times=best_times,
                          pricing=pricing,
                          recommendations=recommendations,
                          level=level,
                          lot=lot,
                          location=location,
                          breadcrumb=breadcrumb)

# ============================================================================
# Booking Route
# ============================================================================

@app.route('/book/<slot_id>', methods=['GET', 'POST'])
@login_required
def book_slot(slot_id):
    """Book a parking slot"""
    
    # Get slot from database
    slot_db = ParkingSlot.query.filter_by(slot_number=slot_id).first()
    if not slot_db:
        flash('Invalid slot selected.', 'error')
        return redirect(url_for('locations'))
    
    # Get level, lot, location context
    level = slot_db.level
    lot = level.parking_lot if level else None
    location = lot.location if lot else None
    
    # Get pricing
    now = datetime.now()
    current_occupancy = peak_hour_predictor.predict(now.hour, now.weekday())
    price_info = dynamic_pricing.get_price(current_occupancy)
    
    pricing = {
        'base_price': price_info['base_price'],
        'hourly_rate': price_info['hourly_rate'],
        'multiplier': price_info['multiplier'],
        'is_surge_pricing': price_info['is_surge_pricing']
    }
    
    # Get cancellation risk
    lead_time = 2
    user_history = current_user.booking_count
    cancel_prob = cancellation_predictor.predict_probability(lead_time, user_history)
    cancel_risk = {
        'probability': round(cancel_prob * 100),
        'level': cancellation_predictor.get_risk_level(lead_time, user_history)
    }
    
    if request.method == 'POST':
        vehicle_number = request.form.get('vehicle_number')
        start_time_str = request.form.get('start_time')
        duration = int(request.form.get('duration', 2))
        
        # Parse start time
        try:
            start_time = datetime.strptime(start_time_str, '%Y-%m-%dT%H:%M')
        except:
            flash('Invalid date/time format.', 'error')
            return redirect(url_for('book_slot', slot_id=slot_id))
        
        end_time = start_time + timedelta(hours=duration)
        
        # VALIDATION 1: Check if start time is in the past
        if start_time < datetime.now():
            flash('Cannot book for past date/time. Please select a future time.', 'error')
            return redirect(url_for('book_slot', slot_id=slot_id))
        
        # VALIDATION 2: Check for time conflicts with existing bookings
        if not is_slot_available(slot_db.id, start_time, end_time):
            flash('This slot is already booked for the selected time. Please choose a different time.', 'error')
            return redirect(url_for('book_slot', slot_id=slot_id))
        
        total_price = pricing['hourly_rate'] * duration
        
        # Create booking in database
        booking = Booking(
            user_id=current_user.id,
            slot_id=slot_db.id,
            vehicle_number=vehicle_number,
            start_time=start_time,
            end_time=end_time,
            duration_hours=duration,
            hourly_rate=pricing['hourly_rate'],
            total_price=total_price,
            status='active'
        )
        
        # Update user booking count
        current_user.booking_count += 1
        
        # Add to booking history for ML
        history = BookingHistory(
            timestamp=start_time,
            slot_id=slot_id,
            user_id=str(current_user.id),
            occupied=True,
            cancelled=False,
            duration_hours=duration,
            lead_time_hours=(start_time - datetime.now()).total_seconds() / 3600,
            hour=start_time.hour,
            day_of_week=start_time.weekday()
        )
        
        db.session.add(booking)
        db.session.add(history)
        db.session.commit()
        
        # Redirect to confirmation page with booking details
        return redirect(url_for('booking_confirmation', booking_id=booking.id))
    
    slot = {
        'id': slot_id,
        'display_name': slot_db.display_name,
        'row': slot_db.row,
        'column': slot_db.column,
        'distance': slot_db.row + slot_db.column  # Simple distance metric
    }
    
    # Breadcrumb data
    breadcrumb = None
    if location and lot and level:
        breadcrumb = {
            'location': {'id': location.id, 'name': location.name},
            'lot': {'id': lot.id, 'name': lot.name},
            'level': {'id': level.id, 'name': f'Level {level.level_name}'}
        }
    
    return render_template('book_slot.html',
                          slot=slot,
                          pricing=pricing,
                          cancel_risk=cancel_risk,
                          level=level,
                          lot=lot,
                          location=location,
                          breadcrumb=breadcrumb)

# ============================================================================
# Booking Confirmation & Receipt Route
# ============================================================================

@app.route('/booking/confirmation/<int:booking_id>')
@login_required
def booking_confirmation(booking_id):
    """Show booking confirmation page with download option"""
    booking = Booking.query.get_or_404(booking_id)
    
    # Ensure user can only see their own booking (or admin can see all)
    if booking.user_id != current_user.id and not current_user.is_admin:
        flash('Unauthorized access.', 'error')
        return redirect(url_for('my_bookings'))
    
    return render_template('booking_confirmation.html', booking=booking)

@app.route('/booking/<int:booking_id>/receipt')
@login_required
def download_receipt(booking_id):
    """Generate and download PDF receipt for a booking"""
    from flask import Response
    from utils.pdf_generator import generate_booking_receipt
    
    booking = Booking.query.get_or_404(booking_id)
    
    # Ensure user can only download their own receipt (or admin can download all)
    if booking.user_id != current_user.id and not current_user.is_admin:
        flash('Unauthorized access.', 'error')
        return redirect(url_for('my_bookings'))
    
    # Generate PDF
    pdf_buffer = generate_booking_receipt(booking)
    
    # Return as downloadable file
    return Response(
        pdf_buffer.getvalue(),
        mimetype='application/pdf',
        headers={
            'Content-Disposition': f'attachment; filename=ParkHub_Receipt_{booking.id}.pdf'
        }
    )

# ============================================================================
# My Bookings Route
# ============================================================================

@app.route('/my-bookings')
@login_required
def my_bookings():
    """View user's booking history"""
    bookings = Booking.query.filter_by(user_id=current_user.id)\
                           .order_by(Booking.created_at.desc())\
                           .limit(20).all()
    
    return render_template('my_bookings.html', bookings=bookings)

@app.route('/cancel-booking/<int:booking_id>', methods=['POST'])
@login_required
def cancel_booking(booking_id):
    """Cancel a booking - users can cancel their own, admins can cancel any"""
    booking = Booking.query.get_or_404(booking_id)
    
    # Check authorization: owner or admin
    if booking.user_id != current_user.id and not current_user.is_admin:
        flash('Unauthorized action.', 'error')
        return redirect(url_for('my_bookings'))
    
    if booking.cancelled:
        flash('Booking already cancelled.', 'info')
        redirect_url = url_for('admin_bookings') if current_user.is_admin else url_for('my_bookings')
        return redirect(redirect_url)
    
    # Cancel booking - update status and cancelled flag
    booking.cancelled = True
    booking.status = 'cancelled'
    
    # Free up the slot
    slot = ParkingSlot.query.get(booking.slot_id)
    if slot:
        slot.is_occupied = False
    
    db.session.commit()
    
    flash('Booking cancelled successfully.', 'success')
    
    # Redirect based on user type
    if current_user.is_admin:
        return redirect(url_for('admin_bookings'))
    return redirect(url_for('my_bookings'))


# ============================================================================
# Admin All Bookings Route
# ============================================================================

@app.route('/admin/bookings')
@login_required
def admin_bookings():
    """Admin view of all bookings with filtering"""
    
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    # Get filter parameters
    status_filter = request.args.get('status', 'all')
    date_filter = request.args.get('date', 'all')
    peak_filter = request.args.get('peak', 'all')
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Base query
    query = Booking.query
    
    # Apply status filter
    if status_filter == 'active':
        query = query.filter_by(status='active', cancelled=False)
    elif status_filter == 'completed':
        query = query.filter_by(status='completed')
    elif status_filter == 'cancelled':
        query = query.filter_by(cancelled=True)
    
    # Apply date filter
    now = datetime.now()
    if date_filter == 'today':
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        query = query.filter(Booking.created_at >= start_of_day)
    elif date_filter == 'week':
        start_of_week = now - timedelta(days=now.weekday())
        start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
        query = query.filter(Booking.created_at >= start_of_week)
    elif date_filter == 'month':
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        query = query.filter(Booking.created_at >= start_of_month)
    
    # Apply peak time filter (bookings during peak hours: 9-11 AM, 2-3 PM)
    if peak_filter == 'peak':
        # Filter by start_time hour being in peak ranges
        from sqlalchemy import extract, or_
        peak_hours = [9, 10, 11, 14, 15]
        query = query.filter(extract('hour', Booking.start_time).in_(peak_hours))
    elif peak_filter == 'off_peak':
        from sqlalchemy import extract
        peak_hours = [9, 10, 11, 14, 15]
        query = query.filter(~extract('hour', Booking.start_time).in_(peak_hours))
    
    # Order and paginate
    query = query.order_by(Booking.created_at.desc())
    
    # Get total count for stats
    total_count = query.count()
    
    # Paginate
    bookings = query.offset((page - 1) * per_page).limit(per_page).all()
    total_pages = (total_count + per_page - 1) // per_page
    
    # Calculate stats for current filter
    active_count = Booking.query.filter_by(status='active', cancelled=False).count()
    completed_count = Booking.query.filter_by(status='completed').count()
    cancelled_count = Booking.query.filter_by(cancelled=True).count()
    
    stats = {
        'total': Booking.query.count(),
        'active': active_count,
        'completed': completed_count,
        'cancelled': cancelled_count,
        'filtered': total_count
    }
    
    return render_template('admin_bookings.html',
                          bookings=bookings,
                          stats=stats,
                          status_filter=status_filter,
                          date_filter=date_filter,
                          peak_filter=peak_filter,
                          page=page,
                          total_pages=total_pages)

# ============================================================================
# Predictions Route
# ============================================================================

@app.route('/predictions')
@login_required
def predictions():
    """ML predictions dashboard"""
    
    now = datetime.now()
    current_day = now.weekday()
    
    # Weekly forecast
    day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    weekly_forecast = []
    
    for day in range(7):
        peak_hours = peak_hour_predictor.get_peak_hours(day, threshold=0.75)
        
        occupancies = [peak_hour_predictor.predict(h, day) for h in range(6, 22)]
        avg_occ = sum(occupancies) / len(occupancies)
        
        recommendation = "Good for parking" if avg_occ < 0.6 else \
                        "Plan ahead" if avg_occ < 0.8 else "Expect delays"
        
        weekly_forecast.append({
            'name': day_names[day],
            'peak_hours': peak_hours[:3] if peak_hours else [],
            'avg_occupancy': round(avg_occ * 100),
            'recommendation': recommendation
        })
    
    # Today's hourly predictions
    hourly_predictions = []
    for hour in range(6, 22):
        occ = peak_hour_predictor.predict(hour, current_day)
        hourly_predictions.append({
            'time': f"{hour}:00",
            'occupancy': round(occ * 100)
        })
    
    # Best and worst times
    all_times = [(h, peak_hour_predictor.predict(h, current_day)) for h in range(6, 22)]
    sorted_times = sorted(all_times, key=lambda x: x[1])
    
    best_times = []
    for hour, occ in sorted_times[:3]:
        price = dynamic_pricing.get_price(occ)
        best_times.append({
            'hour': hour,
            'occupancy': round(occ * 100),
            'price': price['hourly_rate']
        })
    
    worst_times = []
    for hour, occ in sorted_times[-3:]:
        price = dynamic_pricing.get_price(occ)
        worst_times.append({
            'hour': hour,
            'occupancy': round(occ * 100),
            'price': price['hourly_rate']
        })
    
    return render_template('predictions.html',
                          weekly_forecast=weekly_forecast,
                          hourly_predictions=hourly_predictions,
                          best_times=best_times,
                          worst_times=worst_times)

# ============================================================================
# Admin Analytics Route
# ============================================================================

@app.route('/admin-analytics')
@login_required
def admin_analytics():
    """Admin analytics dashboard"""
    
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    # Get real data from database
    total_bookings = Booking.query.count()
    cancelled_bookings = Booking.query.filter_by(cancelled=True).count()
    cancellation_rate = round(cancelled_bookings / total_bookings * 100, 1) if total_bookings > 0 else 0
    
    # Calculate total revenue
    completed = Booking.query.filter_by(cancelled=False).all()
    total_revenue = sum(b.total_price for b in completed)
    
    # Average duration
    all_bookings = Booking.query.all()
    avg_duration = round(sum(b.duration_hours for b in all_bookings) / len(all_bookings), 1) if all_bookings else 0
    
    stats = {
        'total_bookings': total_bookings,
        'total_revenue': round(total_revenue, 2),
        'cancellation_rate': cancellation_rate,
        'avg_duration': avg_duration
    }
    
    # Anomaly detection from booking history
    history_data = BookingHistory.query.all()
    anomalies = []
    for record in history_data[-50:]:  # Check last 50
        if anomaly_detector.is_anomaly(record.duration_hours, record.hour, record.day_of_week):
            score = anomaly_detector.get_anomaly_score(record.duration_hours, record.hour, record.day_of_week)
            anomalies.append({
                'slot_id': record.slot_id,
                'duration_hours': record.duration_hours,
                'hour': record.hour,
                'anomaly_score': round(score, 4)
            })
    anomalies = anomalies[:5]  # Top 5
    
    # Slot utilization using real data (Last 30 days)
    import pandas as pd
    from utils.model_evaluation import ModelEvaluator
    
    # 1. Calculate Real Slot Utilization
    slots = ParkingSlot.query.all()
    slot_utilization = []
    
    # Define time window (e.g., last 30 days, 12 operating hours/day)
    days_window = 30
    operating_hours = 16  # 6 AM to 10 PM
    total_potential_hours = days_window * operating_hours
    
    start_date = datetime.now() - timedelta(days=days_window)
    
    for slot in slots:
        # Sum duration of all completed/active bookings in window
        bookings = Booking.query.filter(
            Booking.slot_id == slot.id,
            Booking.created_at >= start_date,
            Booking.cancelled == False
        ).all()
        
        total_booked_hours = sum(b.duration_hours for b in bookings)
        
        # Calculate percentage
        utilization = 0
        if total_potential_hours > 0:
            utilization = round((total_booked_hours / total_potential_hours) * 100, 1)
            # Cap at 100% just in case of overlaps or logic quirks
            utilization = min(100, utilization)
            
        slot_utilization.append({
            'slot_id': slot.slot_number,
            'utilization': utilization,
            'hours_booked': round(total_booked_hours, 1)
        })
    
    slot_utilization.sort(key=lambda x: x['utilization'], reverse=True)
    slot_utilization = slot_utilization[:10]  # Top 10
    
    # 2. Get Real Model Accuracy Metrics
    evaluator = ModelEvaluator()
    model_metrics = {}
    
    # Prepare data for evaluation if we have enough history
    history = BookingHistory.query.all()
    if len(history) > 10:
        # Convert to DataFrame
        data_dicts = [{
            'lead_time_hours': h.lead_time_hours,
            'user_booking_count': User.query.get(int(h.user_id)).booking_count if h.user_id.isdigit() else 0,
            'cancelled': 1 if h.cancelled else 0,
            'duration_hours': h.duration_hours,
            'hour': h.hour,
            'day_of_week': h.day_of_week,
            'occupancy_rate': 0.5 # Placeholder, in real sys would link to concurrent bookings
        } for h in history]
        
        df = pd.DataFrame(data_dicts)
        
        # We need a proper occupancy column for peak hour prediction
        # For now, let's derive it by grouping by hour/day
        if not df.empty:
            occupancy_df = df.groupby(['day_of_week', 'hour']).size().reset_index(name='count')
            max_count = occupancy_df['count'].max() or 1
            occupancy_df['occupancy_rate'] = occupancy_df['count'] / max_count
            
            # Run evaluations
            try:
                # Peak Hour (Regression R2)
                peak_res = evaluator.evaluate_peak_hour_predictor(occupancy_df)
                model_metrics['peak_hour_r2'] = peak_res['metrics']['R² Score']
                model_metrics['peak_hour_mae'] = peak_res['metrics']['MAE (Mean Absolute Error)']
                
                # Cancellation (Accuracy)
                cancel_res = evaluator.evaluate_cancellation_predictor(df)
                model_metrics['cancellation_acc'] = cancel_res['metrics']['Accuracy']
                
                # Anomaly (F1)
                anomaly_res = evaluator.evaluate_anomaly_detector(df)
                model_metrics['anomaly_f1'] = anomaly_res['metrics']['F1 Score']
                
            except Exception as e:
                print(f"Evaluation error: {e}")
                model_metrics = {'error': 'Insufficient data for robust evaluation'}
    else:
        # Fallback to demo/mock evaluation if no data
        results = evaluator.evaluate_all()
        model_metrics['peak_hour_r2'] = results['peak_hour']['metrics']['R² Score']
        model_metrics['cancellation_acc'] = results['cancellation']['metrics']['Accuracy']
        model_metrics['anomaly_f1'] = results['anomaly']['metrics']['F1 Score']
        model_metrics['is_demo'] = True
    
    # Peak hours analysis
    day_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    now = datetime.now()
    current_day = now.weekday()
    
    peak_analysis = []
    for day in range(7):
        peak_hours = peak_hour_predictor.get_peak_hours(day, threshold=0.8)
        if peak_hours:
            peak_hour = peak_hours[0]
            peak_occ = peak_hour_predictor.predict(peak_hour, day)
        else:
            all_hours = [(h, peak_hour_predictor.predict(h, day)) for h in range(6, 22)]
            peak_hour, peak_occ = max(all_hours, key=lambda x: x[1])
        
        peak_analysis.append({
            'name': day_names[day],
            'peak_hour': peak_hour,
            'peak_occupancy': round(peak_occ * 100),
            'is_today': day == current_day
        })
    
    # Recent bookings from database
    recent = Booking.query.order_by(Booking.created_at.desc()).limit(10).all()
    recent_bookings = []
    for b in recent:
        recent_bookings.append({
            'timestamp': b.created_at.strftime('%Y-%m-%d %H:%M'),
            'slot_id': b.slot.slot_number if b.slot else 'N/A',
            'user_id': b.user.email if b.user else 'N/A',
            'duration_hours': b.duration_hours,
            'cancelled': b.cancelled
        })
    

    
    return render_template('admin_analytics.html',
                          stats=stats,
                          anomalies=anomalies,
                          slot_utilization=slot_utilization,
                          peak_analysis=peak_analysis,
                          recent_bookings=recent_bookings,
                          model_metrics=model_metrics)

# ============================================================================
# Run Application
# ============================================================================

if __name__ == '__main__':
    # Ensure database exists
    with app.app_context():
        db.create_all()
    
    print("=" * 60)
    print("AI-Powered Smart Parking & Slot Booking System")
    print("=" * 60)
    print("\nStarting Flask development server...")
    print("\nDemo Credentials:")
    print("  User:  user@parking.com / user123")
    print("  Admin: admin@parking.com / admin123")
    print("\nAccess the application at: http://127.0.0.1:5000")
    print("=" * 60)
    
    app.run(debug=True, port=5000)

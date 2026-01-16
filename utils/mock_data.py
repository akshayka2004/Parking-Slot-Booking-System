"""
Mock Data Generator for Smart Parking System
Generates historical parking data for ML model training
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random


def generate_parking_data(num_records: int = 100) -> pd.DataFrame:
    """
    Generate mock historical parking data for ML model training.
    
    Args:
        num_records: Number of records to generate (default: 100)
    
    Returns:
        DataFrame with columns: timestamp, slot_id, occupied, user_id, 
                                cancelled, duration_hours, lead_time_hours
    """
    np.random.seed(42)
    random.seed(42)
    
    # Generate base timestamps over the last 30 days
    base_date = datetime.now() - timedelta(days=30)
    timestamps = [
        base_date + timedelta(
            days=random.randint(0, 29),
            hours=random.randint(6, 22),
            minutes=random.randint(0, 59)
        )
        for _ in range(num_records)
    ]
    
    # Slot IDs (1-20 slots)
    slot_ids = [f"slot_{random.randint(1, 20)}" for _ in range(num_records)]
    
    # Occupancy status (70% occupied during peak hours, 40% otherwise)
    occupied = []
    for ts in timestamps:
        if 9 <= ts.hour <= 18:  # Peak hours
            occupied.append(random.random() < 0.7)
        else:
            occupied.append(random.random() < 0.4)
    
    # User IDs
    user_ids = [f"user_{random.randint(1, 50)}" for _ in range(num_records)]
    
    # Cancellation status (15% cancellation rate)
    cancelled = [random.random() < 0.15 for _ in range(num_records)]
    
    # Duration in hours (between 0.5 and 8 hours, with some anomalies)
    durations = []
    for _ in range(num_records):
        if random.random() < 0.05:  # 5% anomalies (very long stays)
            durations.append(round(random.uniform(10, 24), 1))
        else:
            durations.append(round(random.uniform(0.5, 8), 1))
    
    # Lead time (hours between booking and arrival)
    lead_times = [round(random.uniform(0, 48), 1) for _ in range(num_records)]
    
    # User booking history count
    user_history = [random.randint(0, 20) for _ in range(num_records)]
    
    df = pd.DataFrame({
        'timestamp': timestamps,
        'slot_id': slot_ids,
        'occupied': occupied,
        'user_id': user_ids,
        'cancelled': cancelled,
        'duration_hours': durations,
        'lead_time_hours': lead_times,
        'user_booking_count': user_history,
        'hour': [ts.hour for ts in timestamps],
        'day_of_week': [ts.weekday() for ts in timestamps]
    })
    
    return df.sort_values('timestamp').reset_index(drop=True)


def get_hourly_occupancy_data() -> pd.DataFrame:
    """
    Generate hourly occupancy statistics for peak hour prediction.
    
    Returns:
        DataFrame with hour, day_of_week, and occupancy_rate
    """
    data = []
    for day in range(7):  # 0=Monday to 6=Sunday
        for hour in range(24):
            # Simulate realistic occupancy patterns
            if day < 5:  # Weekdays
                if 9 <= hour <= 11:
                    occupancy = random.uniform(0.7, 0.95)
                elif 12 <= hour <= 14:
                    occupancy = random.uniform(0.8, 0.98)
                elif 15 <= hour <= 18:
                    occupancy = random.uniform(0.75, 0.9)
                elif 6 <= hour <= 8 or 19 <= hour <= 21:
                    occupancy = random.uniform(0.4, 0.6)
                else:
                    occupancy = random.uniform(0.1, 0.3)
            else:  # Weekends
                if 10 <= hour <= 20:
                    occupancy = random.uniform(0.5, 0.75)
                else:
                    occupancy = random.uniform(0.1, 0.35)
            
            data.append({
                'hour': hour,
                'day_of_week': day,
                'occupancy_rate': round(occupancy, 2)
            })
    
    return pd.DataFrame(data)


# Pre-generated data for immediate use
PARKING_DATA = generate_parking_data(100)
HOURLY_OCCUPANCY = get_hourly_occupancy_data()


if __name__ == "__main__":
    # Test data generation
    print("Sample Parking Data:")
    print(PARKING_DATA.head(10))
    print(f"\nTotal records: {len(PARKING_DATA)}")
    print(f"\nColumns: {list(PARKING_DATA.columns)}")
    print(f"\nCancellation rate: {PARKING_DATA['cancelled'].mean():.2%}")

"""
Seed script to populate MongoDB with full year availability data (2026)
This creates availability slots based on restaurant operating hours from restaurant_data.json
"""

from datetime import datetime, timedelta, timezone
import json
from config import get_availability_collection, STORE_ID, IST
from logging_config import request_logger

def parse_time_slots(time_str):
    """
    Parse time string like '12:00 PM - 11:30 PM' or '12:30 AM' into time slots
    Returns list of time strings in HH:MM format (24-hour)
    """
    try:
        parts = time_str.split("-")
        if len(parts) != 2:
            print(f"Warning: Could not parse time string: {time_str}")
            return []
        
        start_str = parts[0].strip()
        end_str = parts[1].strip()
        
        # Parse start time
        start_time = datetime.strptime(start_str, "%I:%M %p").time()
        
        # For end time, handle next-day times (e.g., 12:30 AM)
        end_dt = datetime.strptime(end_str, "%I:%M %p")
        end_time = end_dt.time()
        
        # Check if end time is actually next day (e.g., 12:30 AM is before 12:00 PM)
        is_next_day = end_time < start_time
        
        # Generate 30-minute slots
        slots = []
        current = datetime.combine(datetime.today(), start_time)
        end_full = datetime.combine(datetime.today(), end_time)
        
        if is_next_day:
            end_full += timedelta(days=1)
        
        while current <= end_full:
            slots.append(current.strftime("%H:%M"))
            current += timedelta(minutes=30)
        
        return slots
    except Exception as e:
        print(f"Error parsing time slots '{time_str}': {e}")
        return []

# Load restaurant configuration
def load_restaurant_config():
    """Load restaurant data including operating hours"""
    try:
        with open("restaurant_data.json", "r") as f:
            restaurant_data = json.load(f)
        return restaurant_data
    except Exception as e:
        print(f"Error loading restaurant_data.json: {e}")
        return None

restaurant_data = load_restaurant_config()
operating_hours = restaurant_data.get("operating_hours", {}) if restaurant_data else {}

# Parse operating hours from restaurant data
WEEKDAY_HOURS = operating_hours.get("weekdays", "12:00 PM - 11:30 PM")
WEEKEND_HOURS = operating_hours.get("weekends", "12:00 PM - 12:30 AM")

# Generate time slots based on operating hours
WEEKDAY_SLOTS = parse_time_slots(WEEKDAY_HOURS)
WEEKEND_SLOTS = parse_time_slots(WEEKEND_HOURS)

# Fallback if parsing fails
if not WEEKDAY_SLOTS:
    WEEKDAY_SLOTS = ["12:00", "12:30", "13:00", "13:30", "14:00", "14:30", "15:00", "18:00", "18:30", "19:00", "19:30", "20:00", "20:30", "21:00", "21:30"]
    print(f"⚠️  Using default weekday slots")

if not WEEKEND_SLOTS:
    WEEKEND_SLOTS = WEEKDAY_SLOTS
    print(f"⚠️  Using weekday slots for weekends")

# Table covers available
COVERS = [1, 2, 3, 4, 5, 6, 8, 9, 10]

# Number of tables for each cover size (inventory capacity)
TABLE_INVENTORY = {
    1: 15,
    2: 18,
    3: 16,
    4: 15,
    5: 14,
    6: 13,
    8: 12,
    9: 10,
    10: 8
}

# Days to exclude (restaurant closed) - empty means open all days
CLOSED_DAYS = []

def seed_availability():
    """Populate MongoDB with a full year of availability slots based on restaurant hours"""
    try:
        availability_col = get_availability_collection()
        
        # Clear existing data
        availability_col.delete_many({"store_id": STORE_ID})
        request_logger.info(f"Cleared existing availability data for store {STORE_ID}")
        
        # Generate dates for the entire year 2026
        start_date = datetime(2026, 1, 1, tzinfo=IST)
        end_date = datetime(2026, 12, 31, tzinfo=IST)
        
        current_date = start_date
        slots_created = 0
        weekday_count = 0
        weekend_count = 0
        
        while current_date <= end_date:
            # Skip closed days (e.g., Mondays)
            if current_date.weekday() not in CLOSED_DAYS:
                date_str = current_date.strftime("%Y-%m-%d")
                
                # Determine if weekday (0-4) or weekend (5-6)
                is_weekend = current_date.weekday() >= 5
                time_slots = WEEKEND_SLOTS if is_weekend else WEEKDAY_SLOTS
                
                # Add slots based on operating hours
                for time_slot in time_slots:
                    for covers in COVERS:
                        slot_doc = {
                            "date": date_str,
                            "time": time_slot,
                            "covers": covers,
                            "store_id": STORE_ID,
                            "is_available": True,
                            # 'available_tables' tracks the number of TABLES available for this specific party size ('covers')
                            # Decremented by 1 per booking in reservation_db.py
                            "available_tables": TABLE_INVENTORY.get(covers, 1),
                            "max_capacity": TABLE_INVENTORY.get(covers, 1),
                            "day_type": "weekend" if is_weekend else "weekday",
                            "created_at": datetime.now(IST).isoformat()
                        }
                        availability_col.insert_one(slot_doc)
                        slots_created += 1
                
                if is_weekend:
                    weekend_count += 1
                else:
                    weekday_count += 1
            
            # Move to next day

            current_date += timedelta(days=1)
        
        # Create indices for better performance
        availability_col.create_index([("date", 1), ("time", 1), ("covers", 1)])
        availability_col.create_index([("date", 1), ("is_available", 1)])
        availability_col.create_index([("store_id", 1), ("date", 1)])
        
        request_logger.info(f"Successfully seeded {slots_created} availability slots for year 2026")
        print(f"✓ Successfully created {slots_created} availability slots for the entire year 2026")
        print(f"  - Operating Hours (from restaurant_data.json):")
        print(f"    Weekdays: {WEEKDAY_HOURS}")
        print(f"    Weekends: {WEEKEND_HOURS}")
        print(f"  - Weekday slots: {len(WEEKDAY_SLOTS)} times/day × {len(COVERS)} covers × {weekday_count} days")
        print(f"  - Weekend slots: {len(WEEKEND_SLOTS)} times/day × {len(COVERS)} covers × {weekend_count} days")
        print(f"  - Cover sizes: {COVERS}")
        print(f"  - Store ID: {STORE_ID}")
        return True
        
    except Exception as e:
        request_logger.error(f"Error seeding availability data: {e}")
        print(f"✗ Error seeding availability: {e}")
        return False

def verify_seeding():
    """Verify that the data has been properly seeded"""
    try:
        availability_col = get_availability_collection()
        
        # Get stats
        total_slots = availability_col.count_documents({"store_id": STORE_ID})
        available_slots = availability_col.count_documents({
            "store_id": STORE_ID,
            "is_available": True
        })
        unique_dates = len(list(availability_col.distinct("date", {"store_id": STORE_ID})))
        unique_times = len(list(availability_col.distinct("time", {"store_id": STORE_ID})))
        
        print(f"\n📊 Seeding Verification:")
        print(f"  Total slots: {total_slots}")
        print(f"  Available slots: {available_slots}")
        print(f"  Unique dates: {unique_dates}")
        print(f"  Unique time slots: {unique_times}")
        
        # Show sample slots
        sample_slots = list(availability_col.find({"store_id": STORE_ID}).limit(5))
        print(f"\n📋 Sample slots:")
        for slot in sample_slots:
            day_type = slot.get('day_type', 'unknown')
            print(f"  - {slot['date']} at {slot['time']} for {slot['covers']} covers ({day_type})")
        
        return True
        
    except Exception as e:
        request_logger.error(f"Error verifying seeding: {e}")
        print(f"✗ Error verifying seeding: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting MongoDB availability seeding for 2026...\n")
    
    if seed_availability():
        verify_seeding()
        print("\n✅ Seeding completed successfully!")
    else:
        print("\n❌ Seeding failed!")

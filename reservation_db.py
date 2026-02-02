import time
from datetime import datetime, timedelta, timezone
import json
from config import IST, get_reservations_collection, get_availability_collection, STORE_ID
from logging_config import request_logger

# In-memory storage for mapping booking IDs to MongoDB IDs
BOOKING_ID_MAP = {}

def get_inventory(date_str, start_time, end_time, covers):
    """
    Checks availability from MongoDB for a date within a time range.
    date_str: "YYYY-MM-DD"
    start_time: "HH:MM" (24 hour format)
    end_time: "HH:MM" (24 hour format)
    covers: Number of guests
    
    Returns all available slots between start_time and end_time.
    Automatically filters out any slots that are in the past.
    """
    try:
        availability_col = get_availability_collection()
        
        # Parse inputs
        start_dt_str = f"{date_str} {start_time}"
        end_dt_str = f"{date_str} {end_time}"
        
        start_naive = datetime.strptime(start_dt_str, "%Y-%m-%d %H:%M")
        end_naive = datetime.strptime(end_dt_str, "%Y-%m-%d %H:%M")
        
        start_dt = start_naive.replace(tzinfo=IST)
        end_dt = end_naive.replace(tzinfo=IST)
        
        current_time = datetime.now(IST)
        
        # Query availability from MongoDB
        query = {
            "date": date_str,
            "store_id": STORE_ID,
            "covers": covers,
            "is_available": True,
            "available_tables": {"$gt": 0}
        }
        
        slots = list(availability_col.find(query))
        
        # Filter slots that are within the requested time range and in the future
        filtered_slots = []
        for slot in slots:
            slot_time_str = f"{date_str} {slot['time']}"
            slot_naive = datetime.strptime(slot_time_str, "%Y-%m-%d %H:%M")
            slot_dt = slot_naive.replace(tzinfo=IST)
            
            # Check if slot is within range and in the future
            if start_dt <= slot_dt <= end_dt and slot_dt > current_time:
                filtered_slots.append({
                    "startTime": slot['time'],
                    "slotId": str(slot.get('_id', '')),
                    "availableTables": slot.get('available_tables', covers),
                    "explanation": f"{slot.get('available_tables', covers)} tables available, each fits {covers} people"
                })
        
        request_logger.info(f"Inventory check: date={date_str}, found {len(filtered_slots)} available slots for {covers} covers")
        
        return {
            "slot_details": filtered_slots,
            "date": date_str,
            "covers": covers,
            "covers": covers,
            "total_slots": len(filtered_slots),
            "human_readable_message": f"There are {len(filtered_slots)} time slots available where we can accommodate a party of {covers} people."
        }
    
    except Exception as e:
        request_logger.error(f"Error in get_inventory: {e}")
        return {"error": str(e), "slot_details": []}

def create_booking(name, phone, email, date_str, time_str, covers, notes=None):
    """
    Creates a reservation in MongoDB.
    """
    try:
        reservations_col = get_reservations_collection()
        availability_col = get_availability_collection()
        
        # Generate a unique booking ID using milliseconds (not seconds) to avoid collisions
        booking_id = f"BK-{int(time.time() * 1000)}"
        
        dt_str = f"{date_str} {time_str}"
        naive_dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
        slot_start_time = naive_dt.replace(tzinfo=IST)
        
        # Create booking document
        booking_doc = {
            "booking_id": booking_id,
            "status": "confirmed",
            "customer_details": {
                "name": name,
                "contact_number": phone,
                "email_address": email,
                "contact_number_with_isd_code": phone if phone.startswith("+") else f"+91{phone}"
            },
            "reservation_details": {
                "date": date_str,
                "time": time_str,
                "covers": int(covers),
                "duration": 60,  # Default 60 minutes
                "notes": notes if notes else []
            },
            "store_id": STORE_ID,
            "created_at": datetime.now(IST).isoformat(),
            "slot_start_time": int(slot_start_time.timestamp())
        }
        
        # Insert booking
        result = reservations_col.insert_one(booking_doc)
        booking_doc_id = str(result.inserted_id)
        
        # Update availability - mark slot as unavailable
        availability_col.update_one(
            {
                "date": date_str,
                "time": time_str,
                "covers": covers,
                "store_id": STORE_ID
            },
            {
                "$inc": {"available_tables": -1}
            }
        )
        
        # Store the mapping
        BOOKING_ID_MAP[booking_id] = booking_doc_id
        
        request_logger.info(f"Booking created: {booking_id} for {name} on {date_str} at {time_str} for {covers} covers")
        
        return {
            "status": "success",
            "booking_id": booking_id,
            "partner_booking_id": booking_doc_id,
            "generated_booking_id": booking_id,
            "confirmation_message": f"Your reservation has been confirmed for {covers} guests on {date_str} at {time_str}",
            "customer_name": name,
            "date": date_str,
            "time": time_str,
            "covers": covers
        }
    
    except Exception as e:
        request_logger.error(f"Error in create_booking: {e}")
        return {"error": str(e), "status": "failed"}

def cancel_booking(booking_id, reason="User requested cancellation"):
    """
    Cancels a booking in MongoDB.
    """
    try:
        reservations_col = get_reservations_collection()
        availability_col = get_availability_collection()
        
        # Find the booking
        booking = reservations_col.find_one({"booking_id": booking_id})
        
        if not booking:
            return {
                "error": "Booking not found",
                "booking_id": booking_id,
                "status": "not_found"
            }
        
        # Update booking status
        reservations_col.update_one(
            {"booking_id": booking_id},
            {
                "$set": {
                    "status": "cancelled",
                    "cancelled_at": datetime.now(IST).isoformat(),
                    "cancellation_reason": reason
                }
            }
        )
        
        # Restore availability
        reservation_details = booking.get("reservation_details", {})
        availability_col.update_one(
            {
                "date": reservation_details.get("date"),
                "time": reservation_details.get("time"),
                "covers": reservation_details.get("covers"),
                "store_id": STORE_ID
            },
            {
                "$set": {"is_available": True},
                "$inc": {"available_tables": 1}
            }
        )
        
        request_logger.info(f"Booking cancelled: {booking_id} - Reason: {reason}")
        
        return {
            "status": "success",
            "booking_id": booking_id,
            "message": f"Your booking {booking_id} has been successfully cancelled"
        }
    
    except Exception as e:
        request_logger.error(f"Error in cancel_booking: {e}")
        return {"error": str(e), "status": "failed"}

def get_booking_status(booking_id):
    """
    Checks status of a booking from MongoDB.
    """
    try:
        reservations_col = get_reservations_collection()
        
        booking = reservations_col.find_one({"booking_id": booking_id})
        
        if not booking:
            return {
                "status": "not_found",
                "message": f"Booking {booking_id} not found"
            }
        
        # Format response
        reservation_details = booking.get("reservation_details", {})
        customer_details = booking.get("customer_details", {})
        
        return {
            "status": booking.get("status", "unknown"),
            "booking_id": booking_id,
            "customer_name": customer_details.get("name"),
            "date": reservation_details.get("date"),
            "time": reservation_details.get("time"),
            "covers": reservation_details.get("covers"),
            "created_at": booking.get("created_at"),
            "message": f"Your booking {booking_id} is {booking.get('status', 'unknown').lower()}"
        }
    
    except Exception as e:
        request_logger.error(f"Error in get_booking_status: {e}")
        return {"error": str(e), "status": "failed"}

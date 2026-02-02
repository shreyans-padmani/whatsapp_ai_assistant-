import os
from datetime import timezone, timedelta
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from logging_config import request_logger
from dotenv import load_dotenv
load_dotenv()  

# --- TIMEZONE CONFIGURATION ---
IST = timezone(timedelta(hours=5, minutes=30))

# --- CEREBRAS API CONFIGURATION ---
CEREBRAS_API_KEY = os.environ.get("CEREBRAS_API_KEY")
CEREBRAS_BASE_URL = "https://api.cerebras.ai/v1"
MODEL_ID = "qwen-3-235b-a22b-instruct-2507"

# --- MONGODB CONFIGURATION ---
MONGO_URI = os.environ.get("MONGO_URI")
MONGO_DB = os.environ.get("MONGO_DB")
MONGO_COLLECTION = "conversations"
MONGO_RESERVATIONS_COLLECTION = "reservations"
MONGO_AVAILABILITY_COLLECTION = "availability"

# --- RESTAURANT CONFIGURATION ---
STORE_ID = os.environ.get("STORE_ID", "2u8zw0on")

# --- MONGODB CONNECTION ---
def get_mongo_client():
    """Initialize and return MongoDB client"""
    try:
        mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        mongo_client.admin.command('ping')
        request_logger.info("Connected to MongoDB successfully")
        return mongo_client
    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        request_logger.error(f"Failed to connect to MongoDB: {e}")
        raise

def get_conversations_collection():
    """Get conversations collection and create index"""
    try:
        mongo_client = get_mongo_client()
        db = mongo_client[MONGO_DB]
        conversations_collection = db[MONGO_COLLECTION]
        conversations_collection.create_index([("contact_number", 1), ("restaurant_id", 1)])
        return conversations_collection
    except Exception as e:
        request_logger.error(f"Failed to get conversations collection: {e}")
        raise

def get_reservations_collection():
    """Get reservations collection and create indices"""
    try:
        mongo_client = get_mongo_client()
        db = mongo_client[MONGO_DB]
        reservations_collection = db[MONGO_RESERVATIONS_COLLECTION]
        reservations_collection.create_index([("booking_id", 1)])
        reservations_collection.create_index([("customer_details.contact_number", 1)])
        reservations_collection.create_index([("reservation_details.date", 1)])
        return reservations_collection
    except Exception as e:
        request_logger.error(f"Failed to get reservations collection: {e}")
        raise

def get_availability_collection():
    """Get availability collection and create indices"""
    try:
        mongo_client = get_mongo_client()
        db = mongo_client[MONGO_DB]
        availability_collection = db[MONGO_AVAILABILITY_COLLECTION]
        availability_collection.create_index([("date", 1), ("time", 1), ("covers", 1)])
        availability_collection.create_index([("date", 1), ("is_available", 1)])
        return availability_collection
    except Exception as e:
        request_logger.error(f"Failed to get availability collection: {e}")
        raise

from datetime import datetime
from typing import List, Dict
from logging_config import request_logger
from config import IST, get_conversations_collection

conversations_collection = get_conversations_collection()

def get_history(user_id: str, restaurant_id: str) -> List[Dict[str, str]]:
    """Fetch conversation history from MongoDB for a specific user and restaurant"""
    try:
        conversation = conversations_collection.find_one({
            "contact_number": user_id,
            "restaurant_id": restaurant_id
        })
        if conversation and "messages" in conversation:
            messages = conversation["messages"]
            recent_messages = messages[-5:] if len(messages) > 5 else messages
            request_logger.info(f"Fetched history for user {user_id} | restaurant {restaurant_id} | Total: {len(messages)} | Recent: {len(recent_messages)}")
            return recent_messages
        return []
    except Exception as e:
        request_logger.error(f"Error fetching history for user {user_id} | restaurant {restaurant_id}: {e}")
        return []

def update_history(user_id: str, restaurant_id: str, role: str, content: str) -> None:
    """Update conversation history in MongoDB for a specific user and restaurant"""
    try:
        current_ist_time = datetime.now(IST).isoformat()
        message = {
            "role": role,
            "content": content,
            "timestamp": current_ist_time
        }
        
        conversations_collection.update_one(
            {
                "contact_number": user_id,
                "restaurant_id": restaurant_id
            },
            [
                {
                    "$set": {
                        "messages": {
                            "$concatArrays": [
                                {"$ifNull": ["$messages", []]},
                                [message]
                            ]
                        },
                        "last_updated": current_ist_time,
                        "contact_number": user_id,
                        "restaurant_id": restaurant_id
                    }
                }
            ],
            upsert=True
        )
        
        request_logger.info(f"History updated for user {user_id} | restaurant {restaurant_id}")
    except Exception as e:
        request_logger.error(f"Error updating history for user {user_id} | restaurant {restaurant_id}: {e}")

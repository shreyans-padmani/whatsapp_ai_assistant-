from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from openai import OpenAI
import json
from datetime import datetime
from typing import Optional, List, Dict
import time
from logging_config import request_logger
from agent import RestaurantAgent
from config import (
    IST, 
    CEREBRAS_API_KEY, 
    CEREBRAS_BASE_URL, 
    MODEL_ID
)
from database import get_history, update_history

# --- INITIALIZATION ---
app = FastAPI(title="Restaurant AI API")

# Enable CORS for web UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files directory for web UI
app.mount("/static", StaticFiles(directory="static"), name="static")

# Initialize Cerebras client
cerebras_client = OpenAI(
    api_key=CEREBRAS_API_KEY,
    base_url=CEREBRAS_BASE_URL
)

# Initialize Agent
agent = RestaurantAgent(cerebras_client, MODEL_ID)

# --- DATA MODELS ---
class ChatRequest(BaseModel):
    message_id: str
    restaurant_id: str
    store_id: Optional[str] = ""
    contact_number: str
    message: str

class ChatResponse(BaseModel):
    message_id: str
    response: str
    status: str = "success"

class ConversationMessage(BaseModel):
    role: str
    content: str
    timestamp: str = Field(default_factory=lambda: datetime.now(IST).isoformat())

# --- SYSTEM PROMPT ---
with open("prompt_v1.txt", "r") as f:
    SYSTEM_PROMPT = f.read()

# Load restaurant data from JSON file
with open("restaurant_data.json", "r", encoding="utf-8") as f:
    restaurant_data = json.load(f)

SYSTEM_PROMPT = SYSTEM_PROMPT + "\n---\n## RESTAURANT DATA:\n" + json.dumps(restaurant_data, ensure_ascii=False, indent=2)

# --- API ENDPOINTS ---
@app.get("/")
async def root():
    """
    Serve the web UI
    """
    return FileResponse("static/index.html")

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Process a chat message from a user with agentic loop support.
    """
    request_start_time = time.time()
    message_id = request.message_id
    
    try:
        user_id = request.contact_number
        restaurant_id = request.restaurant_id
        message_body = request.message
        current_ist_time = datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")
        
        print("=="*20)

        # Log incoming request with full body
        request_logger.info(message_id, f"[REQUEST_INCOMING] User: {user_id} | Restaurant: {restaurant_id} | IST: {current_ist_time}")
        request_logger.info(message_id, f"[REQUEST_BODY] {json.dumps(request.dict(), indent=2)}")
        request_logger.info(message_id, f"[REQUEST_MESSAGE] Content: {message_body}")
        
        # 1. Update History with User Message
        history_start = time.time()
        update_history(user_id, restaurant_id, "user", message_body)
        history_time = time.time() - history_start
        request_logger.info(message_id, f"[COMPONENT_HISTORY_UPDATE] Time: {history_time:.4f}s | User: {user_id} | Restaurant: {restaurant_id} | History Length: {len(get_history(user_id, restaurant_id))}")
        
        # 2. Prepare Context
        system_prompt = SYSTEM_PROMPT.replace("{current_time}", current_ist_time)
        conversation_history = get_history(user_id, restaurant_id)
        request_logger.info(message_id, f"[COMPONENT_CONTEXT_PREP] Messages Prepared: {len(conversation_history)} | User: {user_id} | Restaurant: {restaurant_id}")
        
        # 3. Process with Agent
        agent_start = time.time()
        final_reply = agent.process_message(
            system_prompt=system_prompt,
            conversation_history=conversation_history,
            message_id=message_id,
            user_id=user_id,
            restaurant_id=restaurant_id
        )
        agent_time = time.time() - agent_start
        request_logger.info(message_id, f"[COMPONENT_AGENT] Time: {agent_time:.4f}s | User: {user_id} | Restaurant: {restaurant_id}")
        
        # 4. Update History with Reply
        history_reply_start = time.time()
        update_history(user_id, restaurant_id, "assistant", final_reply)
        history_reply_time = time.time() - history_reply_start
        request_logger.info(message_id, f"[COMPONENT_HISTORY_UPDATE] Reply Update Time: {history_reply_time:.4f}s | User: {user_id} | Restaurant: {restaurant_id}")
        
        # Total request time
        total_time = time.time() - request_start_time
        request_logger.info(message_id, f"[REQUEST_COMPLETE] User: {user_id} | Restaurant: {restaurant_id} | Total Time: {total_time:.4f}s | Response Length: {len(final_reply)}")
        
        return ChatResponse(
            message_id=request.message_id,
            response=final_reply,
            status="success"
        )

    except Exception as e:
        error_time = time.time() - request_start_time
        request_logger.error(message_id, f"[REQUEST_ERROR] User: {request.contact_number} | Restaurant: {request.restaurant_id} | Error: {str(e)} | Time: {error_time:.4f}s")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health_check():
    return {"status": "running"}
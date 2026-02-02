import json
import time
from openai import OpenAI
import reservation_db as reservation_api
from logging_config import request_logger

class RestaurantAgent:
    """Agent for handling restaurant reservations and inquiries using agentic loop"""
    
    def __init__(self, cerebras_client: OpenAI, model_id: str):
        self.client = cerebras_client
        self.model_id = model_id
        self.logger = request_logger
        self.max_iterations = 5
    
    def define_tools(self):
        """Define tools available to the agent"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "check_inventory",
                    "description": "Check available table slots for a date within a time range.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "date": {"type": "string", "description": "Date in YYYY-MM-DD format"},
                            "start_time": {"type": "string", "description": "Start time in HH:MM format (24 hour)"},
                            "end_time": {"type": "string", "description": "End time in HH:MM format (24 hour)"},
                            "covers": {"type": "integer", "description": "Number of guests"}
                        },
                        "required": ["date", "start_time", "end_time", "covers"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "create_booking",
                    "description": "Create a new table reservation.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "Customer Name"},
                            "phone": {"type": "string", "description": "Customer Phone Number"},
                            "email": {"type": "string", "description": "Customer Email"},
                            "date": {"type": "string", "description": "Date in YYYY-MM-DD format"},
                            "time": {"type": "string", "description": "Time in HH:MM format"},
                            "covers": {"type": "integer", "description": "Number of guests"}
                        },
                        "required": ["name", "phone", "email", "date", "time", "covers"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "cancel_booking",
                    "description": "Cancel an existing reservation. Requires both the Booking Reference (BK-...) and the System ID.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "booking_id": {"type": "string", "description": "The Booking Reference ID (e.g., BK-174...)"},
                            "reason": {"type": "string", "description": "Reason for cancellation"}
                        },
                        "required": ["booking_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_booking_status",
                    "description": "Get status of a booking using the Partner Booking ID.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "booking_id": {"type": "string", "description": "The unique booking ID provided during confirmation"}
                        },
                        "required": ["booking_id"]
                    }
                }
            }
        ]
    
    def execute_tool_call(self, tool_call):
        """Execute the requested tool"""
        try:
            func_name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)
            self.logger.info(f"Executing tool: {func_name} with args: {args}")

            if func_name == "check_inventory":
                return reservation_api.get_inventory(args["date"], args["start_time"], args["end_time"], args["covers"])
            elif func_name == "create_booking":
                return reservation_api.create_booking(
                    args["name"], args["phone"], args["email"], 
                    args["date"], args["time"], args["covers"]
                )
            elif func_name == "cancel_booking":
                return reservation_api.cancel_booking(
                    args["booking_id"], args.get("reason", "User request")
                )
            elif func_name == "get_booking_status":
                return reservation_api.get_booking_status(args["booking_id"])
            
            return {"error": "Unknown function"}
        except Exception as e:
            self.logger.error(f"Tool execution failed: {e}")
            return {"error": str(e)}
    
    def process_message(self, system_prompt: str, conversation_history: list, message_id: str, user_id: str, restaurant_id: str) -> str:
        """
        Process a message through the agentic loop.
        
        Args:
            system_prompt: System prompt for the LLM
            conversation_history: List of message dicts with role and content
            message_id: Message ID for logging
            user_id: User ID for logging
            restaurant_id: Restaurant ID for logging
        
        Returns:
            Final response string from the agent
        """
        tools = self.define_tools()
        llm_call_count = 0
        final_reply = ""
        
        # Build messages list: system prompt + conversation history
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(conversation_history)
        
        # Agentic loop
        while llm_call_count < self.max_iterations:
            llm_call_count += 1
            llm_call_start = time.time()
            self.logger.info(message_id, f"[LLM_CALL_START] Call {llm_call_count} | User: {user_id} | Restaurant: {restaurant_id} | Model: {self.model_id}")
            
            response = self.client.chat.completions.create(
                model=self.model_id,
                messages=messages,
                tools=tools,
                tool_choice="auto",
                temperature=0.0
            )
            
            llm_call_time = time.time() - llm_call_start
            self.logger.info(message_id, f"[LLM_CALL_COMPLETE] Call {llm_call_count} - Time: {llm_call_time:.4f}s | User: {user_id} | Restaurant: {restaurant_id}")
            
            assistant_msg = response.choices[0].message
            
            # If no tool calls, this is the final response
            if not assistant_msg.tool_calls:
                self.logger.info(message_id, f"[NO_TOOL_CALLS] Final response at iteration {llm_call_count} | User: {user_id} | Restaurant: {restaurant_id}")
                final_reply = assistant_msg.content
                break
            
            # Handle tool calls
            self.logger.info(message_id, f"[TOOL_CALLS_DETECTED] Count: {len(assistant_msg.tool_calls)} | Iteration: {llm_call_count} | User: {user_id} | Restaurant: {restaurant_id}")
            
            # Append assistant message with tool calls to conversation
            messages.append(assistant_msg)
            
            # Execute each tool call
            for idx, tool_call in enumerate(assistant_msg.tool_calls, 1):
                tool_start = time.time()
                self.logger.info(message_id, f"[TOOL_EXECUTION_START] Tool {idx}/{len(assistant_msg.tool_calls)} | Name: {tool_call.function.name} | Iteration: {llm_call_count} | User: {user_id} | Restaurant: {restaurant_id}")
                
                tool_result = self.execute_tool_call(tool_call)
                
                tool_time = time.time() - tool_start
                result_str = json.dumps(tool_result)
                self.logger.info(message_id, f"[TOOL_EXECUTION_COMPLETE] Tool {idx} - Time: {tool_time:.4f}s | Result: {result_str}{'...' if len(result_str) > 100 else ''}")
                
                # Append tool result to conversation
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result_str
                })
            
            # Loop will continue to next iteration to process tool results
        
        if llm_call_count >= self.max_iterations:
            self.logger.warning(message_id, f"[MAX_ITERATIONS_REACHED] Stopping at {self.max_iterations} iterations | User: {user_id} | Restaurant: {restaurant_id}")
            final_reply = "I'm taking too long to process this. Please try again."
        
        self.logger.info(message_id, f"[FINAL_REPLY] Content: {final_reply}")
        self.logger.info(message_id, f"[AGENT_COMPLETE] Total LLM Calls: {llm_call_count} | User: {user_id} | Restaurant: {restaurant_id}")
        
        return final_reply

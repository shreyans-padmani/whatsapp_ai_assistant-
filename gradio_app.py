import gradio as gr
import json
from datetime import datetime
from typing import List, Tuple
from config import IST
from agent import RestaurantAgent
from openai import OpenAI
from logging_config import request_logger
import uuid
from config import CEREBRAS_API_KEY, CEREBRAS_BASE_URL, MODEL_ID

# Initialize Cerebras client
cerebras_client = OpenAI(
    api_key=CEREBRAS_API_KEY,
    base_url=CEREBRAS_BASE_URL
)

# Initialize Agent
agent = RestaurantAgent(cerebras_client, MODEL_ID)

# Load system prompt
with open("prompt_v1.txt", "r") as f:
    SYSTEM_PROMPT = f.read()

# Load restaurant data
with open("restaurant_data.json", "r", encoding="utf-8") as f:
    restaurant_data = json.load(f)

SYSTEM_PROMPT = SYSTEM_PROMPT + "\n---\n## RESTAURANT DATA:\n" + json.dumps(restaurant_data, ensure_ascii=False, indent=2)

# class SimpleChatApp:
#     def __init__(self):
#         self.conversation_history: List[Tuple[str, str]] = []
        
#     def send_message(self, user_message: str) -> List[Tuple[str, str]]:
#         """Send message to agent and update conversation history."""
        
#         if not user_message.strip():
#             return self.conversation_history
        
#         try:
#             current_ist_time = datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")
#             message_id = str(uuid.uuid4())
            
#             # Prepare system prompt with current time
#             system_prompt = SYSTEM_PROMPT.replace("{current_time}", current_ist_time)
            
#             # Format conversation history for agent
#             formatted_history = [
#                 {"role": "user" if user else "assistant", "content": msg}
#                 for user, assistant in self.conversation_history
#                 for user, msg in [(True, user), (False, assistant)]
#             ]
            
#             # Add current user message
#             formatted_history.append({"role": "user", "content": user_message})
            
#             # Process with agent
#             response = agent.process_message(
#                 system_prompt=system_prompt,
#                 conversation_history=formatted_history,
#                 message_id=message_id,
#                 user_id="user",
#                 restaurant_id="test"
#             )
            
#             # Update conversation history
#             self.conversation_history.append((user_message, response))
            
#             return self.conversation_history
            
#         except Exception as e:
#             error_msg = f"Error: {str(e)}"
#             self.conversation_history.append((user_message, error_msg))
#             return self.conversation_history
    
#     def clear_history(self):
#         """Clear conversation history."""
#         self.conversation_history = []
#         return []

class SimpleChatApp:
    def __init__(self):
        # Gradio now expects a list of dicts: [{"role": "user", "content": "..."}, ...]
        self.conversation_history: List[dict] = []
        
    def send_message(self, user_message: str) -> List[dict]:
        """Send message to agent and update conversation history."""
        
        if not user_message.strip():
            return self.conversation_history
        
        try:
            current_ist_time = datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")
            message_id = str(uuid.uuid4())
            
            # Prepare system prompt
            system_prompt = SYSTEM_PROMPT.replace("{current_time}", current_ist_time)
            
            # Use current history directly (since it's already in role/content format)
            # but add the new user message first
            self.conversation_history.append({"role": "user", "content": user_message})
            
            # Process with agent
            response = agent.process_message(
                system_prompt=system_prompt,
                conversation_history=self.conversation_history, # Already formatted!
                message_id=message_id,
                user_id="user",
                restaurant_id="test"
            )
            
            # Update history with assistant response
            self.conversation_history.append({"role": "assistant", "content": response})
            
            return self.conversation_history
            
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            self.conversation_history.append({"role": "assistant", "content": error_msg})
            return self.conversation_history
    
    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history = []
        return []

# Initialize app
chat_app = SimpleChatApp()

# # Create Gradio interface
# with gr.Blocks(title="Restaurant AI Assistant", theme=gr.themes.Soft()) as demo:
#     gr.Markdown("# 🍽️ Restaurant AI Assistant")
#     gr.Markdown("Chat with your restaurant assistant")
    
#     chatbot = gr.Chatbot(
#         label="Chat",
#         height=500,
#         show_copy_button=True
#     )
    
#     user_input = gr.Textbox(
#         label="Your Message",
#         placeholder="Type your message here ",
#         lines=2,
#         max_lines=10
#     )
    
#     clear_btn = gr.Button("Clear History", variant="secondary")
    
#     # Define interactions
#     user_input.submit(
#         fn=chat_app.send_message,
#         inputs=[user_input],
#         outputs=[chatbot]
#     ).then(
#         lambda: "",
#         outputs=user_input
#     )
    
#     clear_btn.click(
#         fn=chat_app.clear_history,
#         outputs=[chatbot]
#     )

# if __name__ == "__main__":
#     demo.launch(share=True)

# Create Gradio interface
# Move theme=gr.themes.Soft() out of here
with gr.Blocks(title="Restaurant AI Assistant") as demo:
    gr.Markdown("# 🍽️ Restaurant AI Assistant")
    gr.Markdown("Chat with your restaurant assistant")
    
    chatbot = gr.Chatbot(
        label="Chat",
        height=500,
        # Removed show_copy_button to avoid TypeError
        # If you need it, check 'gradio --version' to ensure compatibility
    )
    
    user_input = gr.Textbox(
        label="Your Message",
        placeholder="Type your message here",
        lines=2,
        max_lines=10
    )
    
    clear_btn = gr.Button("Clear History", variant="secondary")
    
    # Define interactions
    user_input.submit(
        fn=chat_app.send_message,
        inputs=[user_input],
        outputs=[chatbot]
    ).then(
        lambda: "",
        outputs=user_input
    )
    
    clear_btn.click(
        fn=chat_app.clear_history,
        outputs=[chatbot]
    )

if __name__ == "__main__":
    # Pass the theme here to satisfy Gradio 6.0 requirements
    demo.launch(share=True, theme=gr.themes.Soft())
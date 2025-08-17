import gradio as gr
from cerebras_client import CerebrasClient
from chat_history import ChatHistory

def create_chat_interface():
    """Create and configure the Gradio chat interface"""
    
    # Initialize Cerebras client and chat history
    try:
        cerebras = CerebrasClient()
        chat_history = ChatHistory()
    except ValueError as e:
        print(f"Error initializing Cerebras client: {e}")
        print("Please make sure you have a .env file with CEREBRAS_API_KEY")
        return None
    
    # Current conversation state
    current_conversation_id = None
    
    def chat_function(message, history):
        """
        Handle chat messages from Gradio interface with streaming
        
        Args:
            message: Current user message
            history: List of previous [user_message, bot_response] pairs
            
        Yields:
            String chunks of the streaming response
        """
        nonlocal current_conversation_id
        
        try:
            # Create new conversation if none exists
            if current_conversation_id is None:
                # Generate title from first message (truncated)
                title = message[:50] + "..." if len(message) > 50 else message
                current_conversation_id = chat_history.create_conversation(title)
            
            # Save user message to database
            chat_history.add_message(current_conversation_id, "user", message)
            
            # Convert Gradio history format to Cerebras messages format
            messages = []
            
            # Add conversation history
            for user_msg, bot_msg in history:
                messages.append({"role": "user", "content": user_msg})
                if bot_msg:  # bot_msg might be None if conversation was interrupted
                    messages.append({"role": "assistant", "content": bot_msg})
            
            # Add current message
            messages.append({"role": "user", "content": message})
            
            # Get streaming response
            stream = cerebras.chat_completion(messages=messages, stream=True)
            
            # Yield chunks for real-time streaming
            partial_response = ""
            for chunk in cerebras.chat_stream_generator(stream):
                partial_response += chunk
                yield partial_response
            
            # Save complete bot response to database
            chat_history.add_message(current_conversation_id, "assistant", partial_response)
            
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            yield error_msg
    
    # Create the chat interface
    chat_interface = gr.ChatInterface(
        fn=chat_function,
        title="Albin's Console based on Qwen-3-Coder-480B",
        theme=gr.themes.Soft(),
        retry_btn=None,
        undo_btn=None,
        css="""
            footer { display: none !important; }
            .gradio-container h1 { 
                font-size: 1.2rem !important; 
                margin: 0.5rem 0 !important; 
                padding: 0 !important; 
            }
            .chatbot { 
                height: 82vh !important; 
                margin-bottom: 0.5rem !important;
            }
            .chat-interface { padding-bottom: 0.5rem !important; }
            .input-container { 
                margin-bottom: 0.5rem !important; 
                padding-bottom: 0 !important;
            }
            .form > .wrap {
                display: flex !important;
                flex-direction: row !important;
                gap: 0.5rem !important;
                align-items: flex-end !important;
                margin-bottom: 0 !important;
                padding-bottom: 0 !important;
            }
            .form > .wrap > button {
                height: 40px !important;
                min-height: 40px !important;
                padding: 8px 16px !important;
                margin: 0 !important;
                flex-shrink: 0 !important;
            }
            .gradio-container {
                padding-bottom: 0 !important;
                margin-bottom: 0 !important;
            }
        """,
        additional_inputs=[],
    )
    
    
    return chat_interface

if __name__ == "__main__":
    # Create and launch the chat interface
    interface = create_chat_interface()
    
    if interface:
        print("Starting Cerebras Chat Interface...")
        print("Open your browser to the URL shown below")
        interface.launch(
            server_name="0.0.0.0",  # Allow external access
            server_port=7860,       # Default Gradio port
            share=False,            # Set to True to create public link
            debug=True              # Enable debug mode
        )
    else:
        print("Failed to create chat interface. Please check your configuration.")
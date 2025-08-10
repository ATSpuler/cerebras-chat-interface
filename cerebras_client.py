from dotenv import load_dotenv
import os
from cerebras.cloud.sdk import Cerebras

load_dotenv()

class CerebrasClient:
    def __init__(self):
        self.api_key = os.getenv('CEREBRAS_API_KEY')
        if not self.api_key:
            raise ValueError("CEREBRAS_API_KEY not found in environment variables")
        self.client = Cerebras(api_key=self.api_key)
    
    def chat_completion(self, messages, model="qwen-3-coder-480b", stream=True, 
                       max_completion_tokens=40000, temperature=0.7, top_p=0.8):
        """
        Create a chat completion with the Cerebras API
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            model: Model name to use
            stream: Whether to stream responses
            max_completion_tokens: Maximum tokens in response
            temperature: Sampling temperature
            top_p: Top-p sampling parameter
            
        Returns:
            Generator for streaming or completion object for non-streaming
        """
        return self.client.chat.completions.create(
            messages=messages,
            model=model,
            stream=stream,
            max_completion_tokens=max_completion_tokens,
            temperature=temperature,
            top_p=top_p
        )
    
    def chat_stream_to_text(self, stream):
        """Convert streaming response to full text"""
        full_response = ""
        for chunk in stream:
            content = chunk.choices[0].delta.content or ""
            full_response += content
        return full_response
    
    def chat_stream_generator(self, stream):
        """Generator that yields each chunk of streaming response"""
        for chunk in stream:
            content = chunk.choices[0].delta.content or ""
            if content:
                yield content
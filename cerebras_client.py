from dotenv import load_dotenv
import os
import json
from cerebras.cloud.sdk import Cerebras
from typing import List, Dict, Optional

load_dotenv()

class CerebrasClient:
    def __init__(self, agent_db=None):
        self.api_key = os.getenv('CEREBRAS_API_KEY')
        if not self.api_key:
            raise ValueError("CEREBRAS_API_KEY not found in environment variables")
        self.client = Cerebras(api_key=self.api_key)
        self.agent_db = agent_db
        self.current_conversation_id = None
    
    def set_conversation_context(self, conversation_id: str):
        """Set current conversation context for database integration"""
        self.current_conversation_id = conversation_id
    
    def get_enhanced_context(self, messages: List[Dict]) -> List[Dict]:
        """Enhance messages with database context if available"""
        if not self.agent_db or not self.current_conversation_id:
            return messages
        
        # Get conversation context from database
        context = self.agent_db.get_conversation_context(self.current_conversation_id)
        
        # Build enhanced context
        enhanced_messages = []
        
        # Add system message with context if we have relevant information
        if context.get('agent_state') or context.get('tasks'):
            system_context = []
            
            # Add user preferences
            user_prefs = context.get('agent_state', {}).get('user_preferences')
            if user_prefs:
                system_context.append(f"User preferences: {json.dumps(user_prefs)}")
            
            # Add active tasks
            active_tasks = context.get('tasks', [])
            if active_tasks:
                task_summary = [f"- {task['task_name']}: {task['status']}" for task in active_tasks[:3]]
                system_context.append(f"Active tasks:\n" + "\n".join(task_summary))
            
            # Add relevant memories
            memories = context.get('memories', {})
            if memories:
                important_facts = memories.get('important_facts', [])[:2]
                if important_facts:
                    facts = [fact['content'] for fact in important_facts]
                    system_context.append(f"Important context: {'; '.join(facts)}")
            
            if system_context:
                enhanced_messages.append({
                    "role": "system",
                    "content": "Context from previous interactions:\n" + "\n".join(system_context)
                })
        
        # Add original messages
        enhanced_messages.extend(messages)
        
        return enhanced_messages
    
    def chat_completion(self, messages, model="qwen-3-coder-480b", stream=True, 
                       max_completion_tokens=40000, temperature=0.7, top_p=0.8,
                       use_enhanced_context=True):
        """
        Create a chat completion with the Cerebras API
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            model: Model name to use
            stream: Whether to stream responses
            max_completion_tokens: Maximum tokens in response
            temperature: Sampling temperature
            top_p: Top-p sampling parameter
            use_enhanced_context: Whether to enhance with database context
            
        Returns:
            Generator for streaming or completion object for non-streaming
        """
        # Enhance messages with database context if enabled
        if use_enhanced_context:
            messages = self.get_enhanced_context(messages)
        
        # Store decision context if database is available
        if self.agent_db and self.current_conversation_id:
            decision_context = f"Model: {model}, Temperature: {temperature}, Messages: {len(messages)}"
            self.agent_db.track_agent_decision(
                self.current_conversation_id,
                decision_context,
                "chat_completion_request"
            )
        
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
        
        # Store response metrics if database available
        if self.agent_db and self.current_conversation_id and full_response:
            self.agent_db.store_memory(
                self.current_conversation_id,
                'response_metrics',
                json.dumps({
                    'response_length': len(full_response),
                    'word_count': len(full_response.split()),
                    'has_code': '```' in full_response
                }),
                importance=1
            )
        
        return full_response
    
    def chat_stream_generator(self, stream, store_chunks=False):
        """Generator that yields each chunk of streaming response"""
        full_response = ""
        for chunk in stream:
            content = chunk.choices[0].delta.content or ""
            if content:
                full_response += content
                yield content
        
        # Store final response context if requested
        if store_chunks and self.agent_db and self.current_conversation_id:
            self.agent_db.store_memory(
                self.current_conversation_id,
                'response_patterns',
                f"Response length: {len(full_response)} chars",
                importance=1
            )
    
    def analyze_user_pattern(self, user_message: str):
        """Analyze user message for patterns and preferences"""
        if not self.agent_db or not self.current_conversation_id:
            return
        
        # Simple pattern detection - could be enhanced with NLP
        patterns = {
            'prefers_code': any(word in user_message.lower() for word in ['code', 'function', 'class', 'method']),
            'asks_questions': user_message.strip().endswith('?'),
            'requests_explanation': any(word in user_message.lower() for word in ['explain', 'how', 'why', 'what']),
            'message_length': len(user_message)
        }
        
        # Store patterns as preferences
        for pattern, detected in patterns.items():
            if detected and pattern != 'message_length':
                current_count = self.agent_db.get_user_preference(self.current_conversation_id, f'{pattern}_count', 0)
                self.agent_db.store_user_preference(self.current_conversation_id, f'{pattern}_count', current_count + 1)
        
        # Store average message length
        avg_length = self.agent_db.get_user_preference(self.current_conversation_id, 'avg_message_length', 0)
        msg_count = self.agent_db.get_user_preference(self.current_conversation_id, 'message_count', 0)
        new_avg = (avg_length * msg_count + patterns['message_length']) / (msg_count + 1)
        self.agent_db.store_user_preference(self.current_conversation_id, 'avg_message_length', int(new_avg))
        self.agent_db.store_user_preference(self.current_conversation_id, 'message_count', msg_count + 1)
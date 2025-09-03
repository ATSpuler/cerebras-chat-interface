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
        """Enhance messages with comprehensive memory-aware system prompts"""
        if not self.agent_db or not self.current_conversation_id:
            return messages
        
        # Get conversation context from database
        context = self.agent_db.get_conversation_context(self.current_conversation_id)
        
        # Build enhanced context
        enhanced_messages = []
        
        # Add comprehensive system message with memory instructions
        if context.get('agent_state') or context.get('tasks') or context.get('memories'):
            system_prompt = self._build_memory_aware_system_prompt(context)
            if system_prompt:
                enhanced_messages.append({
                    "role": "system",
                    "content": system_prompt
                })
        
        # Add original messages
        enhanced_messages.extend(messages)
        
        return enhanced_messages
    
    def _build_memory_aware_system_prompt(self, context: Dict) -> str:
        """Build comprehensive system prompt with memory utilization instructions"""
        prompt_sections = []
        
        # Core memory instructions
        prompt_sections.append("""You are an AI assistant with access to conversation history and learned user preferences. 

MEMORY UTILIZATION INSTRUCTIONS:
• Reference previous conversations naturally when relevant
• Adapt your communication style based on learned user preferences
• Acknowledge patterns you've observed about the user
• Continue or reference active tasks from previous sessions
• Prioritize information based on importance and recency

BEHAVIORAL ADAPTATION GUIDELINES:""")
        
        # User preferences section
        user_prefs = context.get('agent_state', {}).get('user_preferences')
        if user_prefs:
            pref_instructions = ["• ADAPT YOUR RESPONSES based on these learned preferences:"]
            for key, value in user_prefs.items():
                if 'prefers_code' in key and value > 2:
                    pref_instructions.append("  - User frequently requests code examples - provide them proactively")
                elif 'asks_questions' in key and value > 3:
                    pref_instructions.append("  - User asks many questions - be thorough in explanations")
                elif 'requests_explanation' in key and value > 2:
                    pref_instructions.append("  - User values detailed explanations - provide comprehensive answers")
                elif 'avg_message_length' in key and value > 100:
                    pref_instructions.append("  - User writes detailed messages - match with substantial responses")
                elif key in ['language', 'framework', 'tool'] and isinstance(value, str):
                    pref_instructions.append(f"  - User prefers {key}: {value} - reference when relevant")
            
            if len(pref_instructions) > 1:
                prompt_sections.append("\n".join(pref_instructions))
        
        # Active tasks section
        active_tasks = context.get('tasks', [])
        if active_tasks:
            task_instructions = ["• ACTIVE TASKS to reference or continue:"]
            for task in active_tasks[:3]:
                status = task.get('status', 'unknown')
                name = task.get('task_name', 'Unnamed task')
                desc = task.get('description', '')[:50]
                priority = task.get('priority', 1)
                
                priority_indicator = "🔥" if priority >= 3 else "⭐" if priority >= 2 else "📋"
                task_instructions.append(f"  {priority_indicator} {name} ({status}) - {desc}")
            
            task_instructions.append("  - Reference these tasks when providing related assistance")
            task_instructions.append("  - Offer to continue or update task progress when appropriate")
            prompt_sections.append("\n".join(task_instructions))
        
        # Important memories section
        memories = context.get('memories', {})
        if memories:
            memory_instructions = ["• IMPORTANT CONTEXT to acknowledge:"]
            
            # Important facts
            important_facts = memories.get('important_facts', [])[:2]
            if important_facts:
                for fact in important_facts:
                    content = fact['content'][:100]  # Truncate long facts
                    importance = fact.get('importance', 1)
                    indicator = "🔥" if importance >= 3 else "💡"
                    memory_instructions.append(f"  {indicator} {content}")
            
            # User patterns
            patterns = memories.get('patterns', [])[:2]
            if patterns:
                memory_instructions.append("  📊 Observed patterns:")
                for pattern in patterns:
                    memory_instructions.append(f"    - {pattern['content'][:80]}")
            
            # Successful interactions
            successful = memories.get('successful_interactions', [])[:1]
            if successful:
                memory_instructions.append(f"  ✅ Previous success: {successful[0]['content'][:60]}")
            
            prompt_sections.append("\n".join(memory_instructions))
        
        # Response guidelines
        prompt_sections.append("""
RESPONSE GUIDELINES:
• Build on previous conversations - reference past discussions naturally
• Use learned information to personalize responses
• When relevant, acknowledge what you remember about the user's work/interests
• If continuing a task, reference previous progress
• Maintain consistency with established preferences and patterns

Remember: Use this context to provide more helpful, personalized responses while maintaining natural conversation flow.""")
        
        return "\n".join(prompt_sections)
    
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
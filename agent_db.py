import apsw
import json
import uuid
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Any
from chat_history import ChatHistory

class AgentMemoryManager:
    """Helper class for advanced memory operations"""
    
    def __init__(self, agent_db):
        self.db = agent_db
    
    def consolidate_memories(self, memory_type: str, similarity_threshold: float = 0.8):
        """Consolidate similar memories to reduce redundancy"""
        memories = self.db.retrieve_memories(memory_type, limit=100)
        # Simple consolidation - in production, use embeddings/similarity
        unique_contents = set()
        for memory in memories:
            content = memory['content'].lower().strip()
            if content not in unique_contents:
                unique_contents.add(content)
        
    def promote_memory_importance(self, conversation_id: str, content_pattern: str):
        """Increase importance of memories matching a pattern"""
        cursor = self.db.connection.cursor()
        cursor.execute('''
            UPDATE agent_memory 
            SET importance = importance + 1
            WHERE conversation_id = ? AND content LIKE ?
        ''', (conversation_id, f'%{content_pattern}%'))

class AgentDB(ChatHistory):
    """Enhanced database class combining chat history with agent state management"""
    
    def __init__(self, db_path: str = "chat_history.db"):
        super().__init__(db_path)
        self.init_agent_tables()
    
    def init_agent_tables(self):
        """Create agent-specific tables"""
        cursor = self.connection.cursor()
        
        # Agent state table - stores agent's current state and context
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS agent_state (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                state_type TEXT NOT NULL,
                state_data TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES conversations (id)
            )
        ''')
        
        # Task tracking table - stores task plans and progress
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL,
                task_name TEXT NOT NULL,
                description TEXT,
                status TEXT DEFAULT 'pending',
                priority INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES conversations (id)
            )
        ''')
        
        # Agent memory table - stores long-term context and learnings
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS agent_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT,
                memory_type TEXT NOT NULL,
                content TEXT NOT NULL,
                importance INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES conversations (id)
            )
        ''')
        
        # Session data table - stores session-specific information
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL,
                session_data TEXT NOT NULL,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES conversations (id)
            )
        ''')
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_agent_state_conv ON agent_state(conversation_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tasks_conv ON tasks(conversation_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_memory_conv ON agent_memory(conversation_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_sessions_conv ON sessions(conversation_id)')
    
    def store_agent_state(self, conversation_id: str, state_type: str, state_data: Dict):
        """Store agent's current state"""
        cursor = self.connection.cursor()
        cursor.execute('''
            INSERT INTO agent_state (conversation_id, state_type, state_data)
            VALUES (?, ?, ?)
        ''', (conversation_id, state_type, json.dumps(state_data)))
    
    def get_agent_state(self, conversation_id: str, state_type: str) -> Optional[Dict]:
        """Retrieve latest agent state of specific type"""
        cursor = self.connection.cursor()
        result = list(cursor.execute('''
            SELECT state_data FROM agent_state
            WHERE conversation_id = ? AND state_type = ?
            ORDER BY timestamp DESC LIMIT 1
        ''', (conversation_id, state_type)))
        
        if result:
            return json.loads(result[0][0])
        return None
    
    def create_task(self, conversation_id: str, task_name: str, description: str = "", priority: int = 1) -> str:
        """Create a new task"""
        task_id = str(uuid.uuid4())
        cursor = self.connection.cursor()
        cursor.execute('''
            INSERT INTO tasks (id, conversation_id, task_name, description, priority)
            VALUES (?, ?, ?, ?, ?)
        ''', (task_id, conversation_id, task_name, description, priority))
        return task_id
    
    def update_task_status(self, task_id: str, status: str):
        """Update task status"""
        cursor = self.connection.cursor()
        cursor.execute('''
            UPDATE tasks SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (status, task_id))
    
    def get_active_tasks(self, conversation_id: str) -> List[Dict]:
        """Get all active (non-completed) tasks for conversation"""
        cursor = self.connection.cursor()
        tasks = []
        for row in cursor.execute('''
            SELECT id, task_name, description, status, priority, created_at, updated_at
            FROM tasks
            WHERE conversation_id = ? AND status != 'completed'
            ORDER BY priority DESC, created_at ASC
        ''', (conversation_id,)):
            tasks.append({
                'id': row[0],
                'task_name': row[1],
                'description': row[2],
                'status': row[3],
                'priority': row[4],
                'created_at': row[5],
                'updated_at': row[6]
            })
        return tasks
    
    def store_memory(self, conversation_id: str, memory_type: str, content: str, importance: int = 1):
        """Store long-term memory"""
        cursor = self.connection.cursor()
        cursor.execute('''
            INSERT INTO agent_memory (conversation_id, memory_type, content, importance)
            VALUES (?, ?, ?, ?)
        ''', (conversation_id, memory_type, content, importance))
    
    def retrieve_memories(self, memory_type: str, limit: int = 10) -> List[Dict]:
        """Retrieve memories by type, ordered by importance and recency"""
        cursor = self.connection.cursor()
        memories = []
        for row in cursor.execute('''
            SELECT content, importance, created_at, conversation_id
            FROM agent_memory
            WHERE memory_type = ?
            ORDER BY importance DESC, created_at DESC
            LIMIT ?
        ''', (memory_type, limit)):
            memories.append({
                'content': row[0],
                'importance': row[1],
                'created_at': row[2],
                'conversation_id': row[3]
            })
        return memories
    
    def create_session(self, conversation_id: str, session_data: Dict) -> str:
        """Create new session"""
        session_id = str(uuid.uuid4())
        cursor = self.connection.cursor()
        cursor.execute('''
            INSERT INTO sessions (id, conversation_id, session_data)
            VALUES (?, ?, ?)
        ''', (session_id, conversation_id, json.dumps(session_data)))
        return session_id
    
    def update_session(self, session_id: str, session_data: Dict):
        """Update session data and last_active timestamp"""
        cursor = self.connection.cursor()
        cursor.execute('''
            UPDATE sessions 
            SET session_data = ?, last_active = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (json.dumps(session_data), session_id))
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        """Retrieve session data"""
        cursor = self.connection.cursor()
        result = list(cursor.execute('''
            SELECT conversation_id, session_data, started_at, last_active
            FROM sessions WHERE id = ?
        ''', (session_id,)))
        
        if result:
            row = result[0]
            return {
                'conversation_id': row[0],
                'session_data': json.loads(row[1]),
                'started_at': row[2],
                'last_active': row[3]
            }
        return None
    
    def get_conversation_context(self, conversation_id: str) -> Dict:
        """Get comprehensive context for conversation including messages, tasks, and state"""
        context = {
            'messages': self.get_conversation_messages(conversation_id),
            'tasks': self.get_active_tasks(conversation_id),
            'agent_state': {},
            'memories': {}
        }
        
        # Get various agent states
        state_types = ['current_task', 'user_preferences', 'conversation_summary']
        for state_type in state_types:
            state = self.get_agent_state(conversation_id, state_type)
            if state:
                context['agent_state'][state_type] = state
        
        # Get relevant memories
        memory_types = ['user_preferences', 'important_facts', 'patterns']
        for memory_type in memory_types:
            memories = self.retrieve_memories(memory_type, 5)
            if memories:
                context['memories'][memory_type] = memories
        
        return context
    
    def store_user_preference(self, conversation_id: str, preference_key: str, preference_value: Any):
        """Store user preference"""
        preferences = self.get_agent_state(conversation_id, 'user_preferences') or {}
        preferences[preference_key] = preference_value
        self.store_agent_state(conversation_id, 'user_preferences', preferences)
    
    def get_user_preference(self, conversation_id: str, preference_key: str, default=None):
        """Get user preference"""
        preferences = self.get_agent_state(conversation_id, 'user_preferences') or {}
        return preferences.get(preference_key, default)
    
    def summarize_conversation(self, conversation_id: str, max_messages: int = 50):
        """Create and store conversation summary for context management"""
        messages = self.get_conversation_messages(conversation_id)
        if len(messages) > max_messages:
            # Store summary for context efficiency
            summary_data = {
                'total_messages': len(messages),
                'last_summarized': datetime.now().isoformat(),
                'key_topics': [],  # Could be enhanced with NLP
                'user_requests': [],  # Track common user patterns
            }
            self.store_agent_state(conversation_id, 'conversation_summary', summary_data)
    
    def track_agent_decision(self, conversation_id: str, decision_context: str, decision_made: str):
        """Track agent decisions for learning and improvement"""
        self.store_memory(
            conversation_id, 
            'agent_decisions', 
            json.dumps({
                'context': decision_context,
                'decision': decision_made,
                'timestamp': datetime.now().isoformat()
            }), 
            importance=2
        )
    
    def cleanup_old_states(self, days: int = 30):
        """Clean up old agent states older than specified days"""
        cursor = self.connection.cursor()
        cursor.execute('''
            DELETE FROM agent_state 
            WHERE timestamp < datetime('now', '-{} days')
        '''.format(days))
        
        cursor.execute('''
            DELETE FROM agent_memory 
            WHERE created_at < datetime('now', '-{} days') AND importance < 3
        '''.format(days * 2))  # Keep important memories longer
    
    def get_agent_stats(self) -> Dict:
        """Get comprehensive statistics about agent usage"""
        cursor = self.connection.cursor()
        
        # Basic stats from parent class
        base_stats = self.get_conversation_stats()
        
        # Agent-specific stats
        total_tasks = list(cursor.execute('SELECT COUNT(*) FROM tasks'))[0][0]
        completed_tasks = list(cursor.execute("SELECT COUNT(*) FROM tasks WHERE status = 'completed'"))[0][0]
        total_memories = list(cursor.execute('SELECT COUNT(*) FROM agent_memory'))[0][0]
        active_sessions = list(cursor.execute(
            "SELECT COUNT(*) FROM sessions WHERE last_active > datetime('now', '-1 day')"
        ))[0][0]
        
        return {
            **base_stats,
            'total_tasks': total_tasks,
            'completed_tasks': completed_tasks,
            'task_completion_rate': completed_tasks / total_tasks if total_tasks > 0 else 0,
            'total_memories': total_memories,
            'active_sessions': active_sessions
        }
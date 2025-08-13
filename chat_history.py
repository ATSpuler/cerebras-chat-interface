import apsw
import json
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import uuid

class ChatHistory:
    def __init__(self, db_path: str = "chat_history.db"):
        """Initialize chat history with APSW SQLite database"""
        self.db_path = db_path
        self.connection = apsw.Connection(db_path)
        self.init_database()
    
    def init_database(self):
        """Create tables if they don't exist"""
        cursor = self.connection.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES conversations (id)
            )
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_messages_conversation 
            ON messages(conversation_id, timestamp)
        ''')
    
    def create_conversation(self, title: str = None) -> str:
        """Create a new conversation and return its ID"""
        conversation_id = str(uuid.uuid4())
        if not title:
            title = f"Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        cursor = self.connection.cursor()
        cursor.execute('''
            INSERT INTO conversations (id, title) VALUES (?, ?)
        ''', (conversation_id, title))
        
        return conversation_id
    
    def add_message(self, conversation_id: str, role: str, content: str):
        """Add a message to a conversation"""
        cursor = self.connection.cursor()
        cursor.execute('''
            INSERT INTO messages (conversation_id, role, content) 
            VALUES (?, ?, ?)
        ''', (conversation_id, role, content))
        
        # Update conversation timestamp
        cursor.execute('''
            UPDATE conversations 
            SET updated_at = CURRENT_TIMESTAMP 
            WHERE id = ?
        ''', (conversation_id,))
    
    def get_conversation_messages(self, conversation_id: str) -> List[Tuple[str, str]]:
        """Get all messages from a conversation in Gradio format [(user_msg, bot_msg)]"""
        cursor = self.connection.cursor()
        messages = list(cursor.execute('''
            SELECT role, content FROM messages 
            WHERE conversation_id = ? 
            ORDER BY timestamp ASC
        ''', (conversation_id,)))
        
        # Convert to Gradio format: [(user_message, bot_response), ...]
        history = []
        current_pair = [None, None]  # [user_msg, bot_msg]
        
        for role, content in messages:
            if role == "user":
                if current_pair[0] is not None:
                    # Save previous pair if it exists
                    history.append(tuple(current_pair))
                current_pair = [content, None]
            elif role == "assistant":
                current_pair[1] = content
                history.append(tuple(current_pair))
                current_pair = [None, None]
        
        # Handle case where last message is from user (no response yet)
        if current_pair[0] is not None and current_pair[1] is None:
            history.append((current_pair[0], None))
        
        return history
    
    def get_conversations(self) -> List[Dict]:
        """Get all conversations ordered by most recent"""
        cursor = self.connection.cursor()
        conversations = []
        
        for row in cursor.execute('''
            SELECT id, title, created_at, updated_at 
            FROM conversations 
            ORDER BY updated_at DESC
        '''):
            conversations.append({
                'id': row[0],
                'title': row[1],
                'created_at': row[2],
                'updated_at': row[3]
            })
        
        return conversations
    
    def delete_conversation(self, conversation_id: str):
        """Delete a conversation and all its messages"""
        cursor = self.connection.cursor()
        cursor.execute('DELETE FROM messages WHERE conversation_id = ?', (conversation_id,))
        cursor.execute('DELETE FROM conversations WHERE id = ?', (conversation_id,))
    
    def update_conversation_title(self, conversation_id: str, title: str):
        """Update conversation title"""
        cursor = self.connection.cursor()
        cursor.execute('''
            UPDATE conversations 
            SET title = ?, updated_at = CURRENT_TIMESTAMP 
            WHERE id = ?
        ''', (title, conversation_id))
    
    def search_conversations(self, query: str) -> List[Dict]:
        """Search conversations by title or message content"""
        cursor = self.connection.cursor()
        conversations = []
        
        for row in cursor.execute('''
            SELECT DISTINCT c.id, c.title, c.created_at, c.updated_at
            FROM conversations c
            LEFT JOIN messages m ON c.id = m.conversation_id
            WHERE c.title LIKE ? OR m.content LIKE ?
            ORDER BY c.updated_at DESC
        ''', (f'%{query}%', f'%{query}%')):
            conversations.append({
                'id': row[0],
                'title': row[1],
                'created_at': row[2],
                'updated_at': row[3]
            })
        
        return conversations
    
    def get_conversation_stats(self) -> Dict:
        """Get statistics about conversations"""
        cursor = self.connection.cursor()
        
        # Total conversations
        total_conversations = list(cursor.execute(
            'SELECT COUNT(*) FROM conversations'
        ))[0][0]
        
        # Total messages
        total_messages = list(cursor.execute(
            'SELECT COUNT(*) FROM messages'
        ))[0][0]
        
        # Most recent conversation
        recent = list(cursor.execute('''
            SELECT title, updated_at FROM conversations 
            ORDER BY updated_at DESC LIMIT 1
        '''))
        
        return {
            'total_conversations': total_conversations,
            'total_messages': total_messages,
            'most_recent': {
                'title': recent[0][0] if recent else None,
                'updated_at': recent[0][1] if recent else None
            }
        }
    
    def close(self):
        """Close the database connection"""
        self.connection.close()
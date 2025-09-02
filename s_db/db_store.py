# db_store.py

import apsw
import time

def store_conversation(db_path, conversation_id, title):
    """
    Stores a new conversation entry in the 'conversations' table.
    """
    conn = apsw.Connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR IGNORE INTO conversations (id, title) 
        VALUES (?, ?)
    """, (conversation_id, title))
    print(f"[DB] Conversation '{title}' stored with ID: {conversation_id}")

def store_message(db_path, conversation_id, role, content):
    """
    Stores a message (user or assistant) in the 'messages' table.
    """
    conn = apsw.Connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO messages (conversation_id, role, content) 
        VALUES (?, ?, ?)
    """, (conversation_id, role, content))
    print(f"[DB] Message stored: {role} -> {content[:50]}...")
# db_retrieve.py

import apsw

def list_conversations(db_path):
    """
    Lists all conversations in the database.
    Returns a list of tuples: (id, title, created_at)
    """
    conn = apsw.Connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, created_at FROM conversations")
    results = cursor.fetchall()
    print("[DB] Conversations listed:")
    for row in results:
        print(f"  - {row[1]} (ID: {row[0]}, Created: {row[2]})")
    return results

def read_conversation(db_path, conversation_id):
    """
    Reads all messages in a given conversation.
    Returns a list of tuples: (role, content, timestamp)
    """
    conn = apsw.Connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT role, content, timestamp 
        FROM messages 
        WHERE conversation_id = ? 
        ORDER BY timestamp
    """, (conversation_id,))
    results = cursor.fetchall()
    print(f"[DB] Messages in conversation {conversation_id}:")
    for row in results:
        print(f"  [{row[0]}] ({row[2]}): {row[1]}")
    return results

def search_messages(db_path, keyword):
    """
    Searches all messages for a keyword.
    Returns a list of matching messages.
    """
    conn = apsw.Connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT conversation_id, role, content, timestamp 
        FROM messages 
        WHERE content LIKE ?
    """, (f"%{keyword}%",))
    results = cursor.fetchall()
    print(f"[DB] Messages matching '{keyword}':")
    for row in results:
        print(f"  [{row[1]}] ({row[3]}) in {row[0]}: {row[2][:60]}...")
    return results
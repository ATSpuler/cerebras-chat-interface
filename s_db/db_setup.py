# db_setup.py

import apsw  # Use APSW for SQLite access

def setup_database(db_path):
    """
    Sets up the required tables in the SQLite database.
    If tables already exist, this function does nothing.
    """
    # Open a connection to the SQLite database
    conn = apsw.Connection(db_path)
    cursor = conn.cursor()

    # Create the 'conversations' table if it doesn't exist
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create the 'messages' table if it doesn't exist
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT NOT NULL,
            role TEXT NOT NULL,          -- 'user' or 'assistant'
            content TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (conversation_id) REFERENCES conversations (id)
        )
    """)

    # Create an index to speed up message queries by conversation and time
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_messages_conversation 
        ON messages(conversation_id, timestamp)
    """)

    print(f"[DB] Database schema ensured at {db_path}")
# db_explorer.py

import apsw
import json

# -----------------------------
# 1. Show Full Conversation History
# -----------------------------
def show_full_history(db_path, conversation_id):
    """
    Displays the entire conversation log (user + assistant) in order.
    Useful for reviewing how goals and responses evolved.
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
    print(f"\n[Full History] for conversation '{conversation_id}':")
    for role, content, timestamp in results:
        print(f"  [{role}] ({timestamp}): {content}")
    return results

# -----------------------------
# 2. Summarize Roles in a Conversation
# -----------------------------
def summarize_roles(db_path, conversation_id):
    """
    Counts how many messages were sent by 'user' vs 'assistant'.
    Helps audit interaction balance.
    """
    conn = apsw.Connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT role, COUNT(*) 
        FROM messages 
        WHERE conversation_id = ? 
        GROUP BY role
    """, (conversation_id,))
    results = cursor.fetchall()
    print(f"\n[Role Summary] for conversation '{conversation_id}':")
    for role, count in results:
        print(f"  Role '{role}': {count} messages")
    return results

# -----------------------------
# 3. Search for Specific Keywords
# -----------------------------
def search_keyword(db_path, keyword):
    """
    Finds all messages containing a keyword.
    Useful for tracking how tools or terms were used.
    """
    conn = apsw.Connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT conversation_id, role, content, timestamp 
        FROM messages 
        WHERE content LIKE ?
    """, (f"%{keyword}%",))
    results = cursor.fetchall()
    print(f"\n[Keyword Search] for '{keyword}':")
    for conv_id, role, content, ts in results:
        print(f"  [{role}] in {conv_id} at {ts}: {content[:100]}...")
    return results

# -----------------------------
# 4. Extract All Task Plans (JSON)
# -----------------------------
def extract_task_plans(db_path):
    """
    Retrieves all stored task plans (JSON blobs from assistant).
    Helps analyze how goals are being decomposed over time.
    """
    conn = apsw.Connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT conversation_id, content, timestamp
        FROM messages
        WHERE role = 'assistant' AND content LIKE '[%'
        ORDER BY timestamp
    """)
    plans = cursor.fetchall()
    print("\n[Task Plans] found in DB:")
    for conv_id, content, ts in plans:
        print(f"\n--- Plan in '{conv_id}' at {ts} ---")
        try:
            task_list = json.loads(content)
            for task in task_list:
                print(f"  [{task['id']}] {task['description']} → {task['status']}")
        except json.JSONDecodeError:
            print("  (Invalid JSON content)")
    return plans

# -----------------------------
# 5. Get Most Recent User Goal
# -----------------------------
def get_last_user_goal(db_path, conversation_id):
    """
    Gets the last message sent by the user in a conversation.
    Useful for context-aware task regeneration.
    """
    conn = apsw.Connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT content FROM messages
        WHERE conversation_id = ? AND role = 'user'
        ORDER BY timestamp DESC LIMIT 1
    """, (conversation_id,))
    result = cursor.fetchone()
    if result:
        print(f"\n[Last User Goal] in '{conversation_id}': {result[0]}")
        return result[0]
    else:
        print(f"\n[No user goals found] in '{conversation_id}'")
        return None

# -----------------------------
# 6. List All Conversation Titles
# -----------------------------
def list_titles(db_path):
    """
    Lists all conversation titles for quick browsing.
    """
    conn = apsw.Connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, created_at FROM conversations")
    results = cursor.fetchall()
    print("\n[Conversation Titles]:")
    for conv_id, title, created_at in results:
        print(f"  - {title} (ID: {conv_id}, Created: {created_at})")
    return results

# -----------------------------
# 7. Show Task Execution Timeline
# -----------------------------
def task_timeline(db_path, conversation_id):
    """
    Parses and displays the sequence of tasks and their statuses.
    Useful for debugging agent workflows.
    """
    from db_session import load_task_plan
    tasks = load_task_plan(db_path, conversation_id)
    print(f"\n[Task Timeline] for '{conversation_id}':")
    for task in tasks:
        print(f"  [{task['id']}] {task['description']} → {task['status']}")
    return tasks
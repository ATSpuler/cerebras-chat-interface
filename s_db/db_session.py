# db_session.py
# Tracks current session tasks and statuses.
import apsw
import json

def store_task_plan(db_path, conversation_id, task_list):
    """
    Stores the task plan as a message in the DB under the assistant's role.
    task_list is a list of task dictionaries.
    """
    task_json = json.dumps(task_list, indent=2)
    store_message(db_path, conversation_id, "assistant", task_json)

def load_task_plan(db_path, conversation_id):
    """
    Loads the most recent task plan for a conversation.
    Returns a list of task dictionaries.
    """
    conn = apsw.Connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT content FROM messages
        WHERE conversation_id = ? AND role = 'assistant'
        ORDER BY timestamp DESC LIMIT 1
    """, (conversation_id,))
    result = cursor.fetchone()
    if result:
        return json.loads(result[0])
    else:
        print("[DB] No task plan found.")
        return []

def update_task_status(db_path, conversation_id, task_id, new_status):
    """
    Updates the status of a specific task in the latest plan.
    """
    task_list = load_task_plan(db_path, conversation_id)
    for task in task_list:
        if task["id"] == task_id:
            task["status"] = new_status
            break
    store_task_plan(db_path, conversation_id, task_list)
    print(f"[DB] Task {task_id} updated to '{new_status}'")
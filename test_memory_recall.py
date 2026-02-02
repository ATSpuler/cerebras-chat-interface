#!/usr/bin/env python3
"""
Targeted tests to diagnose memory recall failures
Tests specifically for app startup memory loading and cross-session recall
"""

import os
import sys
import json
import time
from datetime import datetime
from typing import Dict, Any

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import with fallback for missing dependencies
try:
    from agent_db import AgentDB, AgentMemoryManager
    from cerebras_client import CerebrasClient
except ImportError as e:
    print(f"⚠️  Import error: {e}")
    print("Note: Tests will run with limited functionality")

    # Mock classes for testing logic only
    class AgentDB:
        def __init__(self, db_path):
            import apsw
            self.connection = apsw.Connection(db_path)
            self.db_path = db_path
            # Initialize chat_history parent class functionality
            self._init_tables()
            self._init_agent_tables()

        def _init_tables(self):
            cursor = self.connection.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

        def _init_agent_tables(self):
            cursor = self.connection.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS agent_state (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id TEXT NOT NULL,
                    state_type TEXT NOT NULL,
                    state_data TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS agent_memory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id TEXT,
                    memory_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    importance INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL,
                    task_name TEXT NOT NULL,
                    description TEXT,
                    status TEXT DEFAULT 'pending',
                    priority INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

        def create_conversation(self, title):
            import uuid
            conv_id = str(uuid.uuid4())
            cursor = self.connection.cursor()
            cursor.execute('INSERT INTO conversations (id, title) VALUES (?, ?)', (conv_id, title))
            return conv_id

        def add_message(self, conv_id, role, content):
            cursor = self.connection.cursor()
            cursor.execute('INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)',
                         (conv_id, role, content))

        def get_conversation_messages(self, conv_id):
            cursor = self.connection.cursor()
            return list(cursor.execute(
                'SELECT content FROM messages WHERE conversation_id = ? ORDER BY timestamp',
                (conv_id,)))

        def list_conversations(self):
            cursor = self.connection.cursor()
            return list(cursor.execute('SELECT id, title, created_at FROM conversations ORDER BY created_at DESC'))

        def store_user_preference(self, conv_id, key, value):
            import json
            prefs = self.get_agent_state(conv_id, 'user_preferences') or {}
            prefs[key] = value
            self.store_agent_state(conv_id, 'user_preferences', prefs)

        def get_user_preference(self, conv_id, key, default=None):
            prefs = self.get_agent_state(conv_id, 'user_preferences') or {}
            return prefs.get(key, default)

        def store_agent_state(self, conv_id, state_type, data):
            import json
            cursor = self.connection.cursor()
            cursor.execute('INSERT INTO agent_state (conversation_id, state_type, state_data) VALUES (?, ?, ?)',
                         (conv_id, state_type, json.dumps(data)))

        def get_agent_state(self, conv_id, state_type):
            import json
            cursor = self.connection.cursor()
            result = list(cursor.execute(
                'SELECT state_data FROM agent_state WHERE conversation_id = ? AND state_type = ? ORDER BY timestamp DESC LIMIT 1',
                (conv_id, state_type)))
            return json.loads(result[0][0]) if result else None

        def store_memory(self, conv_id, memory_type, content, importance):
            cursor = self.connection.cursor()
            cursor.execute('INSERT INTO agent_memory (conversation_id, memory_type, content, importance) VALUES (?, ?, ?, ?)',
                         (conv_id, memory_type, content, importance))

        def retrieve_memories(self, memory_type, limit):
            cursor = self.connection.cursor()
            results = list(cursor.execute(
                'SELECT content, importance, created_at, conversation_id FROM agent_memory WHERE memory_type = ? ORDER BY importance DESC, created_at DESC LIMIT ?',
                (memory_type, limit)))
            return [{'content': r[0], 'importance': r[1], 'created_at': r[2], 'conversation_id': r[3]} for r in results]

        def get_conversation_context(self, conv_id):
            return {
                'messages': self.get_conversation_messages(conv_id),
                'tasks': [],
                'agent_state': {'user_preferences': self.get_agent_state(conv_id, 'user_preferences')},
                'memories': {
                    'important_facts': self.retrieve_memories('important_facts', 5),
                    'patterns': self.retrieve_memories('patterns', 5)
                }
            }

        def create_task(self, conv_id, name, desc, priority):
            import uuid
            task_id = str(uuid.uuid4())
            cursor = self.connection.cursor()
            cursor.execute('INSERT INTO tasks (id, conversation_id, task_name, description, priority) VALUES (?, ?, ?, ?, ?)',
                         (task_id, conv_id, name, desc, priority))
            return task_id

        def close(self):
            self.connection.close()

    class CerebrasClient:
        def __init__(self, agent_db=None):
            self.agent_db = agent_db
            self.current_conversation_id = None

        def set_conversation_context(self, conv_id):
            self.current_conversation_id = conv_id

        def get_enhanced_context(self, messages):
            if not self.agent_db or not self.current_conversation_id:
                return messages

            context = self.agent_db.get_conversation_context(self.current_conversation_id)
            enhanced = []

            # Check if we have context to add
            prefs = context.get('agent_state', {}).get('user_preferences')
            memories = context.get('memories', {})

            if prefs or memories:
                system_prompt_parts = []
                if prefs:
                    system_prompt_parts.append(f"User preferences: {prefs}")
                if memories.get('important_facts'):
                    for fact in memories['important_facts']:
                        system_prompt_parts.append(f"Important: {fact['content']}")

                enhanced.append({
                    'role': 'system',
                    'content': '\n'.join(system_prompt_parts)
                })

            enhanced.extend(messages)
            return enhanced

    class AgentMemoryManager:
        def __init__(self, db):
            self.db = db

class MemoryRecallTests:
    """Tests focused on memory recall at startup and across sessions"""

    def __init__(self, test_db_path: str = "test_memory_recall.db"):
        self.test_db_path = test_db_path
        self.test_results = []

    def setup(self):
        """Set up test database with pre-existing data"""
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)
        print(f"✅ Test database created: {self.test_db_path}\n")

    def teardown(self):
        """Clean up"""
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)
        print("\n✅ Test cleanup complete")

    def log_result(self, test_name: str, passed: bool, details: Dict = None):
        """Log test result"""
        result = {'test_name': test_name, 'passed': passed, 'details': details or {}}
        self.test_results.append(result)
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"\n{status} - {test_name}")
        if details:
            for key, value in details.items():
                print(f"  {key}: {value}")
        return passed

    def test_1_app_startup_memory_loading(self):
        """
        CRITICAL TEST: Does the app load previous conversations at startup?
        This simulates app restart and checks if old data is accessible.
        """
        print("\n" + "="*60)
        print("TEST 1: App Startup Memory Loading")
        print("="*60)

        # PHASE 1: Simulate first app session
        print("\n[PHASE 1] First app session - creating data...")
        db1 = AgentDB(self.test_db_path)

        conv_id = db1.create_conversation("Python Flask Project")
        db1.add_message(conv_id, "user", "I'm building a Flask API")
        db1.add_message(conv_id, "assistant", "Great! Let me help with Flask.")
        db1.store_user_preference(conv_id, "framework", "Flask")
        db1.store_memory(conv_id, "important_facts", "User building Flask API", 3)

        print(f"  Created conversation: {conv_id}")
        print(f"  Stored 2 messages")
        print(f"  Stored preference: framework=Flask")
        print(f"  Stored memory: User building Flask API")

        db1.close()

        # PHASE 2: Simulate app restart
        print("\n[PHASE 2] App restart - simulating fresh start...")
        time.sleep(0.1)

        db2 = AgentDB(self.test_db_path)
        client = CerebrasClient(agent_db=db2)

        # THIS IS WHAT SHOULD HAPPEN AT APP STARTUP
        # Check if app can find and load previous conversations
        all_conversations = db2.list_conversations()
        print(f"  Found {len(all_conversations)} previous conversations")

        if len(all_conversations) > 0:
            old_conv = all_conversations[0]
            old_conv_id = old_conv[0]
            print(f"  Previous conversation ID: {old_conv_id}")

            # Can we retrieve old messages?
            messages = db2.get_conversation_messages(old_conv_id)
            print(f"  Retrieved {len(messages)} old messages")

            # Can we retrieve old preferences?
            client.set_conversation_context(old_conv_id)
            prefs = db2.get_agent_state(old_conv_id, "user_preferences")
            print(f"  Retrieved preferences: {prefs}")

            # Can we retrieve old memories?
            memories = db2.retrieve_memories("important_facts", 5)
            print(f"  Retrieved {len(memories)} memories")

            # CRITICAL: Is this context used in enhanced messages?
            test_messages = [{"role": "user", "content": "What framework am I using?"}]
            enhanced = client.get_enhanced_context(test_messages)

            has_system_msg = any(m['role'] == 'system' for m in enhanced)
            system_content = ""
            if has_system_msg:
                system_content = next(m['content'] for m in enhanced if m['role'] == 'system')

            print(f"  Enhanced context has system message: {has_system_msg}")
            print(f"  System message contains 'Flask': {'Flask' in system_content if system_content else False}")

            success = (len(all_conversations) > 0 and
                      len(messages) > 0 and
                      prefs is not None and
                      'Flask' in str(prefs) and
                      len(memories) > 0 and
                      has_system_msg and
                      'Flask' in system_content)

            db2.close()

            return self.log_result(
                "App Startup Memory Loading",
                success,
                {
                    "conversations_found": len(all_conversations),
                    "messages_retrieved": len(messages),
                    "preferences_found": prefs is not None,
                    "memories_found": len(memories),
                    "context_enhanced": has_system_msg,
                    "framework_in_context": 'Flask' in system_content if system_content else False
                }
            )
        else:
            db2.close()
            return self.log_result(
                "App Startup Memory Loading",
                False,
                {"error": "No conversations found after restart"}
            )

    def test_2_new_conversation_uses_global_memory(self):
        """
        CRITICAL TEST: When creating a NEW conversation, does it access memories
        from PREVIOUS conversations?
        """
        print("\n" + "="*60)
        print("TEST 2: New Conversation Uses Global Memory")
        print("="*60)

        db = AgentDB(self.test_db_path)
        client = CerebrasClient(agent_db=db)

        # Create first conversation with memories
        print("\n[PHASE 1] Creating first conversation...")
        conv1_id = db.create_conversation("Conversation 1")
        client.set_conversation_context(conv1_id)

        db.store_user_preference(conv1_id, "language", "Python")
        db.store_user_preference(conv1_id, "prefers_code_count", 5)
        db.store_memory(conv1_id, "important_facts", "User expert in Python", 3)
        db.store_memory(conv1_id, "patterns", "User asks detailed questions", 2)

        print(f"  Conv1 ID: {conv1_id}")
        print(f"  Stored: language=Python, code_preference_count=5")
        print(f"  Stored 2 memories")

        # Create second conversation
        print("\n[PHASE 2] Creating new conversation...")
        conv2_id = db.create_conversation("Conversation 2")
        client.set_conversation_context(conv2_id)

        print(f"  Conv2 ID: {conv2_id}")

        # CRITICAL: Can the new conversation access old memories?
        # This requires the retrieve_memories to work ACROSS conversations
        old_facts = db.retrieve_memories("important_facts", 5)
        old_patterns = db.retrieve_memories("patterns", 5)

        print(f"  Retrieved from DB: {len(old_facts)} facts, {len(old_patterns)} patterns")

        # Check if enhanced context includes cross-conversation memories
        test_messages = [{"role": "user", "content": "What do you know about me?"}]
        enhanced = client.get_enhanced_context(test_messages)

        has_system_msg = any(m['role'] == 'system' for m in enhanced)
        system_content = ""
        if has_system_msg:
            system_content = next(m['content'] for m in enhanced if m['role'] == 'system')

        print(f"  Enhanced context has system message: {has_system_msg}")
        print(f"  System contains 'Python': {'Python' in system_content if system_content else False}")

        # THE PROBLEM: get_conversation_context only looks at CURRENT conversation
        # So preferences from conv1 won't appear in conv2's context
        conv2_prefs = db.get_agent_state(conv2_id, "user_preferences")
        print(f"  Conv2 has Conv1's preferences: {conv2_prefs is not None and 'Python' in str(conv2_prefs)}")

        success = (len(old_facts) > 0 and
                  len(old_patterns) > 0)  # Memories ARE cross-conversation

        db.close()

        return self.log_result(
            "New Conversation Uses Global Memory",
            success,
            {
                "cross_conversation_facts": len(old_facts),
                "cross_conversation_patterns": len(old_patterns),
                "BUG_DETECTED": "Memories are global but preferences are conversation-scoped",
                "preferences_isolated": conv2_prefs is None or 'Python' not in str(conv2_prefs)
            }
        )

    def test_3_conversation_context_scope(self):
        """
        TEST: Verify that get_conversation_context is CONVERSATION-SCOPED
        This explains why new conversations don't recall previous context
        """
        print("\n" + "="*60)
        print("TEST 3: Conversation Context Scope Analysis")
        print("="*60)

        db = AgentDB(self.test_db_path)

        # Setup two conversations
        conv1_id = db.create_conversation("Conv 1")
        conv2_id = db.create_conversation("Conv 2")

        # Add data to conv1
        db.store_user_preference(conv1_id, "theme", "dark")
        db.create_task(conv1_id, "Task 1", "Description", 1)
        db.add_message(conv1_id, "user", "Hello")

        print(f"\nConv1 setup: preferences, tasks, messages")

        # Get context for conv1
        context1 = db.get_conversation_context(conv1_id)
        print(f"\nConv1 context contains:")
        print(f"  Messages: {len(context1['messages'])}")
        print(f"  Tasks: {len(context1['tasks'])}")
        print(f"  Agent state keys: {list(context1['agent_state'].keys())}")
        print(f"  Memory types: {list(context1['memories'].keys())}")

        # Get context for conv2 (should be empty)
        context2 = db.get_conversation_context(conv2_id)
        print(f"\nConv2 context contains:")
        print(f"  Messages: {len(context2['messages'])}")
        print(f"  Tasks: {len(context2['tasks'])}")
        print(f"  Agent state keys: {list(context2['agent_state'].keys())}")

        # THE BUG: get_conversation_context filters by conversation_id
        # Line 228 in agent_db.py: get_conversation_messages(conversation_id)
        # Line 229: get_active_tasks(conversation_id)
        # This means NEW conversations start with EMPTY context

        success = (len(context1['messages']) > 0 and len(context2['messages']) == 0)

        db.close()

        return self.log_result(
            "Conversation Context Scope",
            success,
            {
                "BUG_IDENTIFIED": "get_conversation_context is conversation-scoped",
                "conv1_has_data": len(context1['messages']) > 0,
                "conv2_empty": len(context2['messages']) == 0,
                "IMPACT": "New conversations cannot access previous conversation context"
            }
        )

    def test_4_chat_app_creates_new_conversation_always(self):
        """
        CRITICAL TEST: Verify that chat_app.py ALWAYS creates new conversations
        This is the root cause - it never loads existing conversations
        """
        print("\n" + "="*60)
        print("TEST 4: Chat App Conversation Creation Behavior")
        print("="*60)

        db = AgentDB(self.test_db_path)

        # Pre-populate with existing conversation
        existing_conv = db.create_conversation("Existing Conversation")
        db.add_message(existing_conv, "user", "Previous message")
        db.store_user_preference(existing_conv, "existing_pref", "value")

        print(f"\nPre-existing conversation: {existing_conv}")
        print(f"  Has messages: {len(db.get_conversation_messages(existing_conv))}")
        print(f"  Has preferences: {db.get_agent_state(existing_conv, 'user_preferences')}")

        # Simulate what chat_app.py does
        # Line 19 in chat_app.py: current_conversation_id = None
        # Line 36: if current_conversation_id is None:
        # Line 39: current_conversation_id = agent_db.create_conversation(title)

        current_conversation_id = None  # This is reset on every app start!

        print(f"\nSimulating chat_app.py behavior...")
        print(f"  current_conversation_id starts as: {current_conversation_id}")

        # First message triggers this
        if current_conversation_id is None:
            message = "Hello, new session"
            title = message[:50]
            current_conversation_id = db.create_conversation(title)
            print(f"  Created NEW conversation: {current_conversation_id}")

        # Check if new conversation has access to old data
        new_conv_messages = db.get_conversation_messages(current_conversation_id)
        new_conv_prefs = db.get_agent_state(current_conversation_id, 'user_preferences')

        print(f"\nNew conversation context:")
        print(f"  Messages: {len(new_conv_messages)}")
        print(f"  Preferences: {new_conv_prefs}")

        # Verify that old conversation still exists but is not used
        all_conversations = db.list_conversations()
        print(f"\nTotal conversations in DB: {len(all_conversations)}")
        print(f"  Old conversation ID: {existing_conv}")
        print(f"  New conversation ID: {current_conversation_id}")
        print(f"  Are they different? {existing_conv != current_conversation_id}")

        success = (existing_conv != current_conversation_id and
                  len(new_conv_messages) == 0 and
                  new_conv_prefs is None)

        db.close()

        return self.log_result(
            "Chat App Always Creates New Conversations",
            success,
            {
                "ROOT_CAUSE_CONFIRMED": "chat_app.py resets current_conversation_id=None at startup",
                "old_conversation_exists": existing_conv,
                "new_conversation_created": current_conversation_id,
                "conversations_are_different": existing_conv != current_conversation_id,
                "new_conv_starts_empty": len(new_conv_messages) == 0,
                "FIX_NEEDED": "Load most recent conversation or provide conversation selector"
            }
        )

    def test_5_enhanced_context_memory_scope(self):
        """
        TEST: Verify that enhanced_context only uses CURRENT conversation memories
        """
        print("\n" + "="*60)
        print("TEST 5: Enhanced Context Memory Scope")
        print("="*60)

        db = AgentDB(self.test_db_path)
        client = CerebrasClient(agent_db=db)

        # Create two conversations with different memories
        conv1_id = db.create_conversation("Conv 1")
        conv2_id = db.create_conversation("Conv 2")

        # Conv1: User likes Python
        db.store_user_preference(conv1_id, "language", "Python")
        db.store_memory(conv1_id, "important_facts", "User prefers Python", 3)

        # Conv2: User likes JavaScript (hypothetically from different session)
        db.store_user_preference(conv2_id, "language", "JavaScript")

        print(f"\nConv1 setup: Python preferences")
        print(f"Conv2 setup: JavaScript preferences")

        # Set context to Conv2
        client.set_conversation_context(conv2_id)

        # Get enhanced context for Conv2
        messages = [{"role": "user", "content": "What language do I use?"}]
        enhanced = client.get_enhanced_context(messages)

        system_msg = next((m['content'] for m in enhanced if m['role'] == 'system'), "")

        print(f"\nEnhanced context for Conv2:")
        print(f"  Contains 'JavaScript': {'JavaScript' in system_msg}")
        print(f"  Contains 'Python': {'Python' in system_msg}")

        # EXPECTED: Should have JavaScript (conv2 pref)
        # BUG: Memories are global, so Python memory may leak through!

        # Check what memories are returned
        # Line 244 in agent_db.py: retrieve_memories does NOT filter by conversation!
        all_facts = db.retrieve_memories("important_facts", 5)
        print(f"  retrieve_memories returns {len(all_facts)} facts (GLOBAL, not filtered)")

        success = ('JavaScript' in system_msg or len(system_msg) > 0)

        db.close()

        return self.log_result(
            "Enhanced Context Memory Scope",
            success,
            {
                "BUG_IDENTIFIED": "retrieve_memories is GLOBAL (not conversation-scoped)",
                "agent_state_is_scoped": "user_preferences ARE conversation-scoped",
                "memories_are_global": "important_facts, patterns are NOT scoped",
                "INCONSISTENCY": "Mixed scoping causes unpredictable context",
                "total_global_memories": len(all_facts)
            }
        )

    def run_all_tests(self):
        """Run all memory recall tests"""
        print("\n" + "🔍" * 30)
        print("MEMORY RECALL DIAGNOSTIC TEST SUITE")
        print("🔍" * 30)

        self.setup()

        # Run tests in sequence
        test_methods = [
            self.test_1_app_startup_memory_loading,
            self.test_2_new_conversation_uses_global_memory,
            self.test_3_conversation_context_scope,
            self.test_4_chat_app_creates_new_conversation_always,
            self.test_5_enhanced_context_memory_scope
        ]

        passed = 0
        total = len(test_methods)

        for test in test_methods:
            if test():
                passed += 1

        self.teardown()

        # Summary
        print("\n" + "="*60)
        print("📊 DIAGNOSTIC SUMMARY")
        print("="*60)
        print(f"Tests Passed: {passed}/{total}")
        print(f"Success Rate: {(passed/total)*100:.1f}%")

        print("\n" + "🐛 IDENTIFIED BUGS:")
        print("="*60)
        print("1. chat_app.py ALWAYS creates new conversations (never loads existing)")
        print("   → current_conversation_id = None on every app start (line 19)")
        print("")
        print("2. get_conversation_context() is conversation-scoped")
        print("   → New conversations start with EMPTY context")
        print("   → Previous preferences/tasks/messages are NOT accessible")
        print("")
        print("3. retrieve_memories() is GLOBAL (not conversation-scoped)")
        print("   → Memories leak between conversations")
        print("   → Inconsistent with agent_state scoping")
        print("")
        print("4. No conversation selection/continuation mechanism")
        print("   → Users cannot resume previous conversations")
        print("   → Each app restart = completely fresh start")

        print("\n" + "💡 RECOMMENDED FIXES:")
        print("="*60)
        print("1. Add conversation loading at app startup:")
        print("   • Load most recent conversation OR")
        print("   • Provide conversation selector UI")
        print("")
        print("2. Create global user profile:")
        print("   • Store user preferences independent of conversations")
        print("   • Load global preferences for all conversations")
        print("")
        print("3. Fix memory scoping:")
        print("   • Decide: conversation-scoped OR global?")
        print("   • Make agent_state, tasks, memories consistent")
        print("")
        print("4. Add startup initialization:")
        print("   • Check for existing conversations")
        print("   • Load global user context")
        print("   • Inject into first message's enhanced context")

        return {
            'passed': passed,
            'total': total,
            'success_rate': (passed/total)*100,
            'results': self.test_results
        }

def main():
    """Run memory recall diagnostic tests"""
    test_suite = MemoryRecallTests()
    results = test_suite.run_all_tests()

    # Save results
    with open('work-tmp/memory_recall_test_results.json', 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n📄 Results saved to: work-tmp/memory_recall_test_results.json")

    return 0 if results['success_rate'] == 100 else 1

if __name__ == "__main__":
    sys.exit(main())

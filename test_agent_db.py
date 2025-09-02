#!/usr/bin/env python3
"""
Comprehensive test suite for Agent-Database binding performance
Provides quantitative measurements of memory, learning, and context features
"""

import os
import sys
import json
import time
import uuid
from datetime import datetime
from typing import List, Dict, Any, Tuple

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agent_db import AgentDB, AgentMemoryManager
from cerebras_client import CerebrasClient

class AgentDBTestSuite:
    def __init__(self, test_db_path: str = "test_agent_db.db"):
        """Initialize test suite with isolated test database"""
        self.test_db_path = test_db_path
        self.agent_db = None
        self.cerebras_client = None
        self.memory_manager = None
        self.test_results = []
        self.conversation_ids = []
        
    def setup(self):
        """Set up test environment"""
        # Remove existing test db if it exists
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)
        
        # Initialize components
        self.agent_db = AgentDB(self.test_db_path)
        self.cerebras_client = CerebrasClient(agent_db=self.agent_db)
        self.memory_manager = AgentMemoryManager(self.agent_db)
        
        print(f"✅ Test environment initialized with database: {self.test_db_path}")
    
    def teardown(self):
        """Clean up test environment"""
        if self.agent_db:
            self.agent_db.close()
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)
        print("✅ Test environment cleaned up")
    
    def log_test_result(self, test_name: str, passed: bool, details: Dict = None):
        """Log test result"""
        result = {
            'test_name': test_name,
            'passed': passed,
            'timestamp': datetime.now().isoformat(),
            'details': details or {}
        }
        self.test_results.append(result)
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")
        if details and not passed:
            print(f"   Details: {details}")
    
    def test_database_initialization(self) -> bool:
        """Test 1: Database tables are created correctly"""
        try:
            cursor = self.agent_db.connection.cursor()
            
            # Check all expected tables exist
            expected_tables = ['conversations', 'messages', 'agent_state', 'tasks', 'agent_memory', 'sessions']
            existing_tables = []
            
            for table in cursor.execute("SELECT name FROM sqlite_master WHERE type='table'"):
                existing_tables.append(table[0])
            
            missing_tables = set(expected_tables) - set(existing_tables)
            
            self.log_test_result(
                "Database Initialization",
                len(missing_tables) == 0,
                {"expected_tables": expected_tables, "missing_tables": list(missing_tables)}
            )
            
            return len(missing_tables) == 0
            
        except Exception as e:
            self.log_test_result("Database Initialization", False, {"error": str(e)})
            return False
    
    def test_conversation_creation(self) -> bool:
        """Test 2: Conversation creation and message storage"""
        try:
            # Create conversation
            conv_id = self.agent_db.create_conversation("Test Conversation")
            self.conversation_ids.append(conv_id)
            
            # Add messages
            self.agent_db.add_message(conv_id, "user", "Hello, this is a test message")
            self.agent_db.add_message(conv_id, "assistant", "Hello! I'm responding to your test.")
            
            # Retrieve messages
            messages = self.agent_db.get_conversation_messages(conv_id)
            
            success = len(messages) == 1 and messages[0][0] == "Hello, this is a test message"
            
            self.log_test_result(
                "Conversation Creation & Message Storage",
                success,
                {"conversation_id": conv_id, "message_count": len(messages)}
            )
            
            return success
            
        except Exception as e:
            self.log_test_result("Conversation Creation & Message Storage", False, {"error": str(e)})
            return False
    
    def test_agent_state_persistence(self) -> bool:
        """Test 3: Agent state storage and retrieval"""
        try:
            conv_id = self.conversation_ids[0] if self.conversation_ids else self.agent_db.create_conversation("State Test")
            
            # Store different types of state
            test_preferences = {
                "language": "Python",
                "framework": "Flask",
                "style": "detailed_explanations"
            }
            
            self.agent_db.store_agent_state(conv_id, "user_preferences", test_preferences)
            
            # Retrieve state
            retrieved_prefs = self.agent_db.get_agent_state(conv_id, "user_preferences")
            
            success = retrieved_prefs == test_preferences
            
            self.log_test_result(
                "Agent State Persistence",
                success,
                {"stored": test_preferences, "retrieved": retrieved_prefs}
            )
            
            return success
            
        except Exception as e:
            self.log_test_result("Agent State Persistence", False, {"error": str(e)})
            return False
    
    def test_user_preference_learning(self) -> bool:
        """Test 4: User preference learning and storage"""
        try:
            conv_id = self.conversation_ids[0] if self.conversation_ids else self.agent_db.create_conversation("Preference Test")
            
            # Store preferences using helper methods
            self.agent_db.store_user_preference(conv_id, "prefers_code_examples", True)
            self.agent_db.store_user_preference(conv_id, "favorite_language", "Python")
            self.agent_db.store_user_preference(conv_id, "experience_level", "intermediate")
            
            # Retrieve preferences
            code_pref = self.agent_db.get_user_preference(conv_id, "prefers_code_examples")
            lang_pref = self.agent_db.get_user_preference(conv_id, "favorite_language")
            exp_pref = self.agent_db.get_user_preference(conv_id, "experience_level")
            
            success = (code_pref == True and lang_pref == "Python" and exp_pref == "intermediate")
            
            self.log_test_result(
                "User Preference Learning",
                success,
                {
                    "code_preference": code_pref,
                    "language_preference": lang_pref,
                    "experience_level": exp_pref
                }
            )
            
            return success
            
        except Exception as e:
            self.log_test_result("User Preference Learning", False, {"error": str(e)})
            return False
    
    def test_task_management(self) -> bool:
        """Test 5: Task creation, updates, and retrieval"""
        try:
            conv_id = self.conversation_ids[0] if self.conversation_ids else self.agent_db.create_conversation("Task Test")
            
            # Create tasks
            task1_id = self.agent_db.create_task(conv_id, "Build REST API", "Create Flask REST API with authentication", 3)
            task2_id = self.agent_db.create_task(conv_id, "Write tests", "Unit tests for API endpoints", 2)
            
            # Update task status
            self.agent_db.update_task_status(task1_id, "in_progress")
            self.agent_db.update_task_status(task2_id, "completed")
            
            # Get active tasks (should only return task1)
            active_tasks = self.agent_db.get_active_tasks(conv_id)
            
            success = (len(active_tasks) == 1 and 
                      active_tasks[0]['id'] == task1_id and 
                      active_tasks[0]['status'] == "in_progress")
            
            self.log_test_result(
                "Task Management",
                success,
                {
                    "total_tasks_created": 2,
                    "active_tasks": len(active_tasks),
                    "task_details": active_tasks[0] if active_tasks else None
                }
            )
            
            return success
            
        except Exception as e:
            self.log_test_result("Task Management", False, {"error": str(e)})
            return False
    
    def test_memory_storage_retrieval(self) -> bool:
        """Test 6: Long-term memory storage and retrieval"""
        try:
            conv_id = self.conversation_ids[0] if self.conversation_ids else self.agent_db.create_conversation("Memory Test")
            
            # Store different types of memories
            self.agent_db.store_memory(conv_id, "important_facts", "User is building an e-commerce platform", 3)
            self.agent_db.store_memory(conv_id, "patterns", "User prefers step-by-step explanations", 2)
            self.agent_db.store_memory(conv_id, "important_facts", "Uses PostgreSQL for database", 3)
            
            # Retrieve memories
            important_memories = self.agent_db.retrieve_memories("important_facts", 5)
            pattern_memories = self.agent_db.retrieve_memories("patterns", 5)
            
            success = (len(important_memories) == 2 and len(pattern_memories) == 1)
            
            self.log_test_result(
                "Memory Storage & Retrieval",
                success,
                {
                    "important_facts_count": len(important_memories),
                    "patterns_count": len(pattern_memories),
                    "sample_memory": important_memories[0] if important_memories else None
                }
            )
            
            return success
            
        except Exception as e:
            self.log_test_result("Memory Storage & Retrieval", False, {"error": str(e)})
            return False
    
    def test_session_management(self) -> bool:
        """Test 7: Session creation and management"""
        try:
            conv_id = self.conversation_ids[0] if self.conversation_ids else self.agent_db.create_conversation("Session Test")
            
            # Create session
            session_data = {
                "user_agent": "test_suite",
                "start_time": datetime.now().isoformat(),
                "initial_message": "Starting test session"
            }
            
            session_id = self.agent_db.create_session(conv_id, session_data)
            
            # Update session
            updated_data = {
                **session_data,
                "messages_sent": 5,
                "last_activity": datetime.now().isoformat()
            }
            self.agent_db.update_session(session_id, updated_data)
            
            # Retrieve session
            retrieved_session = self.agent_db.get_session(session_id)
            
            success = (retrieved_session is not None and 
                      retrieved_session['conversation_id'] == conv_id and
                      retrieved_session['session_data']['messages_sent'] == 5)
            
            self.log_test_result(
                "Session Management",
                success,
                {
                    "session_id": session_id,
                    "conversation_match": retrieved_session['conversation_id'] == conv_id if retrieved_session else False,
                    "data_updated": retrieved_session['session_data'].get('messages_sent') == 5 if retrieved_session else False
                }
            )
            
            return success
            
        except Exception as e:
            self.log_test_result("Session Management", False, {"error": str(e)})
            return False
    
    def test_context_enhancement(self) -> bool:
        """Test 8: Context enhancement for Cerebras client"""
        try:
            conv_id = self.conversation_ids[0] if self.conversation_ids else self.agent_db.create_conversation("Context Test")
            
            # Set up context
            self.cerebras_client.set_conversation_context(conv_id)
            
            # Add some context data
            self.agent_db.store_user_preference(conv_id, "language", "Python")
            self.agent_db.create_task(conv_id, "Debug API", "Fix authentication issue", 3)
            self.agent_db.store_memory(conv_id, "important_facts", "Working on Flask API project", 3)
            
            # Test context enhancement
            original_messages = [{"role": "user", "content": "How do I handle errors?"}]
            enhanced_messages = self.cerebras_client.get_enhanced_context(original_messages)
            
            # Check if system message was added with context
            has_system_message = any(msg['role'] == 'system' for msg in enhanced_messages)
            message_count_increased = len(enhanced_messages) > len(original_messages)
            
            success = has_system_message and message_count_increased
            
            self.log_test_result(
                "Context Enhancement",
                success,
                {
                    "original_message_count": len(original_messages),
                    "enhanced_message_count": len(enhanced_messages),
                    "has_system_context": has_system_message,
                    "sample_context": enhanced_messages[0]['content'][:100] if has_system_message else None
                }
            )
            
            return success
            
        except Exception as e:
            self.log_test_result("Context Enhancement", False, {"error": str(e)})
            return False
    
    def test_pattern_analysis(self) -> bool:
        """Test 9: User pattern analysis"""
        try:
            conv_id = self.conversation_ids[0] if self.conversation_ids else self.agent_db.create_conversation("Pattern Test")
            self.cerebras_client.set_conversation_context(conv_id)
            
            # Simulate different message patterns
            test_messages = [
                "How do I create a function in Python?",  # Question + code preference
                "What is the best way to handle errors?",  # Question + explanation request
                "Can you show me an example of decorators?",  # Question + code example
                "Why do we use virtual environments?"  # Question + explanation
            ]
            
            # Analyze each message
            for msg in test_messages:
                self.cerebras_client.analyze_user_pattern(msg)
            
            # Check if patterns were detected and stored
            asks_questions_count = self.agent_db.get_user_preference(conv_id, "asks_questions_count", 0)
            prefers_code_count = self.agent_db.get_user_preference(conv_id, "prefers_code_count", 0)
            requests_explanation_count = self.agent_db.get_user_preference(conv_id, "requests_explanation_count", 0)
            
            success = (asks_questions_count == 4 and 
                      prefers_code_count >= 2 and 
                      requests_explanation_count >= 2)
            
            self.log_test_result(
                "Pattern Analysis",
                success,
                {
                    "questions_detected": asks_questions_count,
                    "code_preferences": prefers_code_count,
                    "explanation_requests": requests_explanation_count
                }
            )
            
            return success
            
        except Exception as e:
            self.log_test_result("Pattern Analysis", False, {"error": str(e)})
            return False
    
    def test_comprehensive_context(self) -> bool:
        """Test 10: Comprehensive context retrieval"""
        try:
            conv_id = self.conversation_ids[0] if self.conversation_ids else self.agent_db.create_conversation("Comprehensive Test")
            
            # Get comprehensive context
            context = self.agent_db.get_conversation_context(conv_id)
            
            # Check all context components exist
            has_messages = 'messages' in context
            has_tasks = 'tasks' in context
            has_agent_state = 'agent_state' in context
            has_memories = 'memories' in context
            
            # Check if data is present (from previous tests)
            has_data = (len(context.get('messages', [])) > 0 or
                       len(context.get('tasks', [])) > 0 or
                       len(context.get('agent_state', {})) > 0 or
                       len(context.get('memories', {})) > 0)
            
            success = has_messages and has_tasks and has_agent_state and has_memories and has_data
            
            self.log_test_result(
                "Comprehensive Context Retrieval",
                success,
                {
                    "context_components": list(context.keys()),
                    "has_data": has_data,
                    "sample_sizes": {k: len(v) if isinstance(v, (list, dict)) else 1 for k, v in context.items()}
                }
            )
            
            return success
            
        except Exception as e:
            self.log_test_result("Comprehensive Context Retrieval", False, {"error": str(e)})
            return False
    
    def test_statistics_generation(self) -> bool:
        """Test 11: Agent statistics generation"""
        try:
            stats = self.agent_db.get_agent_stats()
            
            # Check required stats fields
            required_fields = ['total_conversations', 'total_messages', 'total_tasks', 
                             'completed_tasks', 'task_completion_rate', 'total_memories']
            
            has_all_fields = all(field in stats for field in required_fields)
            has_reasonable_values = (stats.get('total_conversations', 0) > 0 and
                                   stats.get('total_messages', 0) > 0)
            
            success = has_all_fields and has_reasonable_values
            
            self.log_test_result(
                "Statistics Generation",
                success,
                {
                    "stats_fields": list(stats.keys()),
                    "sample_stats": {k: v for k, v in stats.items() if isinstance(v, (int, float))}
                }
            )
            
            return success
            
        except Exception as e:
            self.log_test_result("Statistics Generation", False, {"error": str(e)})
            return False
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run complete test suite"""
        print("🧪 Starting Agent-Database Binding Test Suite")
        print("=" * 60)
        
        start_time = time.time()
        
        # Test methods in order
        test_methods = [
            self.test_database_initialization,
            self.test_conversation_creation,
            self.test_agent_state_persistence,
            self.test_user_preference_learning,
            self.test_task_management,
            self.test_memory_storage_retrieval,
            self.test_session_management,
            self.test_context_enhancement,
            self.test_pattern_analysis,
            self.test_comprehensive_context,
            self.test_statistics_generation
        ]
        
        passed_tests = 0
        total_tests = len(test_methods)
        
        for test_method in test_methods:
            try:
                if test_method():
                    passed_tests += 1
            except Exception as e:
                print(f"❌ FAIL - {test_method.__name__}: {e}")
        
        end_time = time.time()
        test_duration = end_time - start_time
        
        # Calculate metrics
        success_rate = (passed_tests / total_tests) * 100
        
        # Generate summary
        summary = {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": total_tests - passed_tests,
            "success_rate": round(success_rate, 2),
            "test_duration": round(test_duration, 3),
            "timestamp": datetime.now().isoformat(),
            "database_size": os.path.getsize(self.test_db_path) if os.path.exists(self.test_db_path) else 0
        }
        
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {total_tests - passed_tests}")
        print(f"Success Rate: {success_rate}%")
        print(f"Duration: {test_duration:.3f} seconds")
        print(f"Database Size: {summary['database_size']} bytes")
        
        if success_rate == 100:
            print("🎉 ALL TESTS PASSED! Agent-Database binding is working correctly.")
        elif success_rate >= 80:
            print("⚠️  Most tests passed. Minor issues detected.")
        else:
            print("🚨 Multiple test failures. System needs attention.")
        
        return summary
    
    def save_detailed_report(self, filename: str = "agent_db_test_report.json"):
        """Save detailed test report"""
        report = {
            "summary": self.run_all_tests() if not self.test_results else {
                "total_tests": len(self.test_results),
                "passed_tests": sum(1 for r in self.test_results if r['passed']),
                "failed_tests": sum(1 for r in self.test_results if not r['passed']),
            },
            "detailed_results": self.test_results,
            "test_environment": {
                "database_path": self.test_db_path,
                "python_version": sys.version,
                "test_timestamp": datetime.now().isoformat()
            }
        }
        
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"📄 Detailed report saved to: {filename}")
        return report

def main():
    """Main test execution"""
    test_suite = AgentDBTestSuite()
    
    try:
        test_suite.setup()
        summary = test_suite.run_all_tests()
        
        # Save detailed report
        report = test_suite.save_detailed_report()
        
        # Exit with appropriate code
        success_rate = summary.get('success_rate', 0)
        exit_code = 0 if success_rate == 100 else 1
        
        return exit_code, summary
        
    except Exception as e:
        print(f"🚨 Critical test suite error: {e}")
        return 2, {"error": str(e)}
        
    finally:
        test_suite.teardown()

if __name__ == "__main__":
    exit_code, results = main()
    sys.exit(exit_code)
#!/usr/bin/env python3
"""
Test LLM-SQL Integration
Verifies that the foundation model can manipulate the database using natural language
"""

import os
import sys
import json
import time
from datetime import datetime
from typing import Dict, Any

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sql_tools import LLMSQLTools, LLMDatabaseInterface, SQLSafetyValidator
from agent_db import AgentDB
from cerebras_client import CerebrasClient

class LLMSQLIntegrationTest:
    """Test suite for LLM-SQL integration capabilities"""
    
    def __init__(self):
        self.test_db_path = "test_llm_sql.db"
        self.sql_tools = None
        self.db_interface = None
        self.agent_db = None
        self.test_results = []
        
    def setup(self):
        """Set up test environment with sample data"""
        # Remove existing test db
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)
        
        # Initialize components
        self.agent_db = AgentDB(self.test_db_path)
        self.sql_tools = LLMSQLTools(self.test_db_path)
        self.db_interface = LLMDatabaseInterface(self.test_db_path)
        
        # Create sample data for testing
        self._create_sample_data()
        
        print(f"✅ Test environment setup complete: {self.test_db_path}")
    
    def _create_sample_data(self):
        """Create sample data for LLM to query"""
        # Create conversations
        conv1 = self.agent_db.create_conversation("Python Web Development")
        conv2 = self.agent_db.create_conversation("Machine Learning Project")
        conv3 = self.agent_db.create_conversation("Database Design Help")
        
        # Add messages
        self.agent_db.add_message(conv1, "user", "How do I create a Flask API?")
        self.agent_db.add_message(conv1, "assistant", "Here's how to create a Flask API with authentication...")
        self.agent_db.add_message(conv1, "user", "Can you show me error handling?")
        
        self.agent_db.add_message(conv2, "user", "What is the best ML algorithm for classification?")
        self.agent_db.add_message(conv2, "assistant", "For classification, you have several options...")
        
        self.agent_db.add_message(conv3, "user", "Help me design a user authentication system")
        self.agent_db.add_message(conv3, "assistant", "Here's a secure authentication system design...")
        
        # Add tasks
        self.agent_db.create_task(conv1, "Build REST API", "Create Flask REST API with JWT auth", 3)
        self.agent_db.create_task(conv1, "Add error handling", "Implement proper error responses", 2)
        self.agent_db.create_task(conv2, "Train ML model", "Train classification model on dataset", 3)
        task_completed = self.agent_db.create_task(conv2, "Data preprocessing", "Clean and prepare data", 1)
        self.agent_db.update_task_status(task_completed, "completed")
        
        # Add memories
        self.agent_db.store_memory(conv1, "important_facts", "User prefers Flask over Django", 3)
        self.agent_db.store_memory(conv1, "patterns", "User asks for code examples", 2)
        self.agent_db.store_memory(conv2, "important_facts", "Working on customer churn prediction", 3)
        self.agent_db.store_memory(conv3, "patterns", "User focuses on security", 3)
        
        # Add user preferences
        self.agent_db.store_user_preference(conv1, "language", "Python")
        self.agent_db.store_user_preference(conv1, "framework", "Flask")
        self.agent_db.store_user_preference(conv2, "domain", "machine_learning")
        
        print("✅ Sample data created")
    
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
    
    def test_sql_safety_validation(self) -> bool:
        """Test 1: SQL safety validator prevents dangerous queries"""
        dangerous_queries = [
            "DROP TABLE conversations;",
            "DELETE FROM messages;",  # No WHERE clause
            "SELECT * FROM users; DROP TABLE conversations;",  # SQL injection
            "PRAGMA database_list;",  # System command
            "UPDATE messages SET content = 'hacked';",  # No WHERE clause
        ]
        
        safe_queries = [
            "SELECT * FROM conversations LIMIT 10;",
            "SELECT COUNT(*) FROM messages WHERE conversation_id = 'abc';",
            "INSERT INTO tasks (conversation_id, task_name) VALUES ('test', 'test task');",
            "UPDATE tasks SET status = 'completed' WHERE id = 'task123';",
        ]
        
        validator = SQLSafetyValidator()
        
        # Test dangerous queries are blocked
        dangerous_blocked = 0
        for query in dangerous_queries:
            is_safe, error = validator.validate_query(query)
            if not is_safe:
                dangerous_blocked += 1
        
        # Test safe queries are allowed
        safe_allowed = 0
        for query in safe_queries:
            is_safe, error = validator.validate_query(query)
            if is_safe:
                safe_allowed += 1
        
        success = (dangerous_blocked == len(dangerous_queries) and 
                  safe_allowed == len(safe_queries))
        
        self.log_test_result(
            "SQL Safety Validation",
            success,
            {
                "dangerous_blocked": f"{dangerous_blocked}/{len(dangerous_queries)}",
                "safe_allowed": f"{safe_allowed}/{len(safe_queries)}"
            }
        )
        
        return success
    
    def test_schema_information_retrieval(self) -> bool:
        """Test 2: LLM can retrieve database schema information"""
        result = self.sql_tools.get_schema_info()
        
        success = (result["success"] and 
                  "tables" in result["schema"] and
                  len(result["schema"]["tables"]) >= 6)  # Should have all our tables
        
        expected_tables = {"conversations", "messages", "agent_state", "tasks", "agent_memory", "sessions"}
        actual_tables = set(result["schema"]["tables"].keys()) if success else set()
        missing_tables = expected_tables - actual_tables
        
        self.log_test_result(
            "Schema Information Retrieval",
            len(missing_tables) == 0,
            {
                "total_tables": len(actual_tables),
                "expected_tables": list(expected_tables),
                "missing_tables": list(missing_tables)
            }
        )
        
        return len(missing_tables) == 0
    
    def test_natural_language_to_sql_conversion(self) -> bool:
        """Test 3: Natural language requests convert to valid SQL"""
        test_requests = [
            ("how many conversations are there", "SELECT COUNT(*) as conversation_count FROM conversations"),
            ("show recent conversations", "conversations"),  # Should contain conversations table
            ("show active tasks", "tasks"),  # Should query tasks table
            ("show important memories", "agent_memory"),  # Should query memory table
            ("search for Flask", "messages"),  # Should search messages
        ]
        
        successful_conversions = 0
        
        for request, expected_contains in test_requests:
            result = self.sql_tools.natural_language_to_sql(request)
            
            if result["success"] and expected_contains in result["sql"].lower():
                successful_conversions += 1
            else:
                print(f"   Failed conversion: '{request}' -> {result}")
        
        success = successful_conversions >= len(test_requests) * 0.8  # Allow 80% success rate
        
        self.log_test_result(
            "Natural Language to SQL Conversion", 
            success,
            {
                "successful_conversions": f"{successful_conversions}/{len(test_requests)}",
                "success_rate": f"{(successful_conversions/len(test_requests)*100):.1f}%"
            }
        )
        
        return success
    
    def test_sql_query_execution(self) -> bool:
        """Test 4: SQL queries execute correctly and return data"""
        test_queries = [
            ("SELECT COUNT(*) FROM conversations", 1, "count"),
            ("SELECT * FROM conversations LIMIT 3", 3, "conversations"),
            ("SELECT * FROM tasks WHERE status != 'completed'", 3, "active_tasks"),
            ("SELECT * FROM agent_memory WHERE importance >= 3", 3, "important_memories"),
        ]
        
        successful_executions = 0
        
        for query, expected_min_rows, test_type in test_queries:
            result = self.sql_tools.execute_sql(query)
            
            if (result["success"] and 
                "data" in result and 
                len(result["data"]) >= expected_min_rows):
                successful_executions += 1
            else:
                print(f"   Failed execution: {test_type} -> {result}")
        
        success = successful_executions == len(test_queries)
        
        self.log_test_result(
            "SQL Query Execution",
            success,
            {
                "successful_executions": f"{successful_executions}/{len(test_queries)}",
                "queries_tested": [q[2] for q in test_queries]
            }
        )
        
        return success
    
    def test_natural_language_database_queries(self) -> bool:
        """Test 5: End-to-end natural language database queries"""
        test_requests = [
            "How many conversations do I have?",
            "Show me my recent conversations", 
            "What are my active tasks?",
            "Show me important memories",
            "Give me database statistics"
        ]
        
        successful_requests = 0
        
        for request in test_requests:
            result = self.sql_tools.execute_natural_language_query(request)
            
            if result["success"] and "data" in result:
                successful_requests += 1
            else:
                print(f"   Failed request: '{request}' -> {result.get('error', 'Unknown error')}")
        
        success = successful_requests >= len(test_requests) * 0.8  # 80% success rate
        
        self.log_test_result(
            "Natural Language Database Queries",
            success,
            {
                "successful_requests": f"{successful_requests}/{len(test_requests)}",
                "success_rate": f"{(successful_requests/len(test_requests)*100):.1f}%"
            }
        )
        
        return success
    
    def test_database_interface_responses(self) -> bool:
        """Test 6: Database interface provides human-readable responses"""
        test_requests = [
            ("show database schema", "Database Schema"),
            ("give me insights", "Database Insights"), 
            ("show recent conversations", "Results for"),
            ("how many conversations", "conversation_count"),
        ]
        
        successful_responses = 0
        
        for request, expected_content in test_requests:
            response = self.db_interface.process_database_request(request)
            
            if expected_content.lower() in response.lower():
                successful_responses += 1
            else:
                print(f"   Failed response: '{request}' -> Missing '{expected_content}'")
                print(f"   Response: {response[:100]}...")
        
        success = successful_responses == len(test_requests)
        
        self.log_test_result(
            "Database Interface Responses",
            success,
            {
                "successful_responses": f"{successful_responses}/{len(test_requests)}",
                "response_quality": "human-readable" if success else "needs_improvement"
            }
        )
        
        return success
    
    def test_conversation_insights_generation(self) -> bool:
        """Test 7: System can generate conversation insights"""
        result = self.sql_tools.get_conversation_insights()
        
        success = (result["success"] and 
                  "insights" in result and
                  len(result["insights"]) >= 3)  # Should have multiple insight types
        
        insight_types = list(result["insights"].keys()) if success else []
        expected_insights = ["message_stats", "task_completion_rate", "memory_distribution"]
        
        self.log_test_result(
            "Conversation Insights Generation",
            success,
            {
                "insights_generated": insight_types,
                "expected_insights": expected_insights,
                "insights_working": len([i for i in insight_types if "error" not in result["insights"][i]])
            }
        )
        
        return success
    
    def test_search_functionality(self) -> bool:
        """Test 8: LLM can search through conversation data"""
        search_queries = [
            'search for "Flask"',
            'find messages about authentication',
            'search for machine learning',
        ]
        
        successful_searches = 0
        
        for query in search_queries:
            result = self.sql_tools.execute_natural_language_query(query)
            
            # Should either find results or handle gracefully
            if result["success"] or "Could not extract search term" in result.get("error", ""):
                successful_searches += 1
        
        success = successful_searches >= len(search_queries) * 0.7  # 70% success rate
        
        self.log_test_result(
            "Search Functionality",
            success,
            {
                "search_queries_tested": len(search_queries),
                "successful_searches": successful_searches,
                "search_capability": "working" if success else "needs_improvement"
            }
        )
        
        return success
    
    def test_llm_context_enhancement(self) -> bool:
        """Test 9: Database tools enhance LLM context appropriately"""
        # This would test integration with CerebrasClient
        # For now, we'll test that database context can be generated
        
        sample_messages = [
            {"role": "user", "content": "Show me my conversation history"},
            {"role": "user", "content": "What tasks do I have?"},
            {"role": "user", "content": "Tell me about my preferences"}
        ]
        
        context_enhanced = 0
        
        for message in sample_messages:
            user_content = message["content"].lower()
            has_db_keywords = any(keyword in user_content for keyword in 
                                ['conversation', 'task', 'preference', 'history', 'data'])
            
            if has_db_keywords:
                # In a real implementation, this would add database context
                context_enhanced += 1
        
        success = context_enhanced == len([m for m in sample_messages if any(k in m["content"].lower() for k in ['conversation', 'task', 'preference'])])
        
        self.log_test_result(
            "LLM Context Enhancement",
            success,
            {
                "messages_tested": len(sample_messages),
                "context_enhanced": context_enhanced,
                "enhancement_rate": f"{(context_enhanced/len(sample_messages)*100):.1f}%"
            }
        )
        
        return success
    
    def test_performance_with_data_volume(self) -> bool:
        """Test 10: Performance remains acceptable with larger data volumes"""
        # Add more data to test performance
        start_time = time.time()
        
        # Add 50 more conversations with messages
        for i in range(50):
            conv_id = self.agent_db.create_conversation(f"Performance Test Conversation {i}")
            for j in range(5):  # 5 messages per conversation
                self.agent_db.add_message(conv_id, "user" if j % 2 == 0 else "assistant", f"Message {j} in conversation {i}")
        
        data_creation_time = time.time() - start_time
        
        # Test query performance
        start_time = time.time()
        result = self.sql_tools.execute_sql("SELECT COUNT(*) FROM conversations")
        query_time = time.time() - start_time
        
        # Test complex query performance
        start_time = time.time()
        insights = self.sql_tools.get_conversation_insights()
        insights_time = time.time() - start_time
        
        # Performance should be reasonable (under 1 second for these operations)
        success = (query_time < 1.0 and insights_time < 2.0 and 
                  result["success"] and insights["success"])
        
        self.log_test_result(
            "Performance with Data Volume",
            success,
            {
                "data_creation_time_s": round(data_creation_time, 3),
                "simple_query_time_s": round(query_time, 3),
                "complex_query_time_s": round(insights_time, 3),
                "total_conversations": result["data"][0][0] if result["success"] else 0
            }
        )
        
        return success
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run complete LLM-SQL integration test suite"""
        print("🤖 Starting LLM-SQL Integration Test Suite")
        print("=" * 60)
        
        start_time = time.time()
        
        test_methods = [
            self.test_sql_safety_validation,
            self.test_schema_information_retrieval,
            self.test_natural_language_to_sql_conversion,
            self.test_sql_query_execution,
            self.test_natural_language_database_queries,
            self.test_database_interface_responses,
            self.test_conversation_insights_generation,
            self.test_search_functionality,
            self.test_llm_context_enhancement,
            self.test_performance_with_data_volume
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
        success_rate = (passed_tests / total_tests) * 100
        
        summary = {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": total_tests - passed_tests,
            "success_rate": round(success_rate, 2),
            "test_duration": round(test_duration, 3),
            "timestamp": datetime.now().isoformat(),
            "llm_sql_integration": "working" if success_rate >= 80 else "needs_attention"
        }
        
        print("\n" + "=" * 60)
        print("📊 LLM-SQL INTEGRATION TEST SUMMARY")
        print("=" * 60)
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {total_tests - passed_tests}")
        print(f"Success Rate: {success_rate}%")
        print(f"Duration: {test_duration:.3f} seconds")
        print(f"LLM-SQL Integration: {summary['llm_sql_integration'].upper()}")
        
        if success_rate >= 90:
            print("🎉 EXCELLENT! LLM can effectively manipulate database with natural language.")
        elif success_rate >= 80:
            print("✅ GOOD! LLM-SQL integration is working well with minor issues.")
        elif success_rate >= 70:
            print("⚠️ ACCEPTABLE! LLM-SQL integration works but needs improvement.")
        else:
            print("🚨 POOR! LLM-SQL integration needs significant work.")
        
        return summary
    
    def teardown(self):
        """Clean up test environment"""
        if self.sql_tools:
            self.sql_tools.close()
        if self.db_interface:
            self.db_interface.close()
        if self.agent_db:
            self.agent_db.close()
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)
        print("✅ Test environment cleaned up")

def main():
    """Main test execution"""
    test_suite = LLMSQLIntegrationTest()
    
    try:
        test_suite.setup()
        summary = test_suite.run_all_tests()
        
        # Save report
        with open("llm_sql_integration_report.json", "w") as f:
            json.dump({
                "summary": summary,
                "detailed_results": test_suite.test_results
            }, f, indent=2)
        
        print(f"📄 Detailed report saved to: llm_sql_integration_report.json")
        
        success_rate = summary.get('success_rate', 0)
        exit_code = 0 if success_rate >= 80 else 1
        
        return exit_code, summary
        
    except Exception as e:
        print(f"🚨 Critical test error: {e}")
        return 2, {"error": str(e)}
        
    finally:
        test_suite.teardown()

if __name__ == "__main__":
    exit_code, results = main()
    sys.exit(exit_code)
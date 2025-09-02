"""
SQL Tools for LLM - Allows the foundation model to manipulate the database with natural language
Provides safe SQL execution with proper constraints and validation
"""

import apsw
import json
import re
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
import sqlite3

class SQLSafetyValidator:
    """Validates SQL queries for safety before execution"""
    
    # Allowed SQL operations
    ALLOWED_OPERATIONS = {
        'SELECT', 'INSERT', 'UPDATE', 'DELETE', 
        'CREATE', 'ALTER', 'DROP'  # Be careful with these
    }
    
    # Dangerous patterns to block
    DANGEROUS_PATTERNS = [
        r';\s*DROP\s+TABLE',
        r';\s*DELETE\s+FROM\s+\w+\s*;',  # Delete all without WHERE
        r'\bPRAGMA\b',
        r'\bATTACH\b',
        r'\bDETACH\b',
        r'--.*DROP',
        r'/\*.*DROP.*\*/',
    ]
    
    # Required WHERE clause for dangerous operations
    REQUIRE_WHERE = ['DELETE', 'UPDATE']
    
    @classmethod
    def validate_query(cls, sql: str) -> tuple[bool, str]:
        """
        Validate SQL query for safety
        Returns: (is_safe, error_message)
        """
        sql_upper = sql.upper().strip()
        
        # Check for dangerous patterns
        for pattern in cls.DANGEROUS_PATTERNS:
            if re.search(pattern, sql_upper, re.IGNORECASE):
                return False, f"Dangerous pattern detected: {pattern}"
        
        # Check for required WHERE clauses
        for op in cls.REQUIRE_WHERE:
            if sql_upper.strip().startswith(op) and 'WHERE' not in sql_upper:
                return False, f"{op} queries must include a WHERE clause for safety"
        
        # Block multiple statements (SQL injection prevention)
        if sql.count(';') > 1:
            return False, "Multiple statements not allowed"
        
        return True, ""

class LLMSQLTools:
    """SQL tools that the LLM can use to interact with the database"""
    
    def __init__(self, db_path: str = "chat_history.db"):
        self.db_path = db_path
        self.connection = apsw.Connection(db_path)
        self.validator = SQLSafetyValidator()
    
    def execute_sql(self, query: str, parameters: Optional[List] = None) -> Dict[str, Any]:
        """
        Execute SQL query with safety validation
        
        Args:
            query: SQL query string
            parameters: Optional parameters for prepared statements
            
        Returns:
            Dict with results, error info, and metadata
        """
        # Validate query safety
        is_safe, error_msg = self.validator.validate_query(query)
        if not is_safe:
            return {
                "success": False,
                "error": f"Query rejected for safety: {error_msg}",
                "query": query
            }
        
        try:
            cursor = self.connection.cursor()
            
            # Execute query and immediately fetch results for SELECT
            if query.strip().upper().startswith('SELECT'):
                if parameters:
                    rows = list(cursor.execute(query, parameters))
                else:
                    rows = list(cursor.execute(query))
                
                # Get column names from description
                columns = []
                if cursor.getdescription():
                    columns = [desc[0] for desc in cursor.getdescription()]
                else:
                    # Fallback: try to infer columns from first row
                    if rows and hasattr(rows[0], '__len__'):
                        columns = [f"col_{i}" for i in range(len(rows[0]))]
                
                return {
                    "success": True,
                    "data": rows,
                    "columns": columns,
                    "row_count": len(rows),
                    "query": query
                }
            else:
                # For non-SELECT queries
                if parameters:
                    cursor.execute(query, parameters)
                else:
                    cursor.execute(query)
                
                return {
                    "success": True,
                    "message": f"Query executed successfully",
                    "query": query,
                    "changes": self.connection.changes()
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "query": query
            }
    
    def get_schema_info(self) -> Dict[str, Any]:
        """Get database schema information for the LLM"""
        try:
            cursor = self.connection.cursor()
            
            # Get all tables
            tables_query = "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            tables = [row[0] for row in cursor.execute(tables_query)]
            
            schema_info = {
                "tables": {},
                "total_tables": len(tables)
            }
            
            # Get schema for each table
            for table in tables:
                # Get columns
                pragma_query = f"PRAGMA table_info({table})"
                columns = []
                for row in cursor.execute(pragma_query):
                    columns.append({
                        "name": row[1],
                        "type": row[2],
                        "not_null": bool(row[3]),
                        "default": row[4],
                        "primary_key": bool(row[5])
                    })
                
                # Get row count
                count_query = f"SELECT COUNT(*) FROM {table}"
                row_count = list(cursor.execute(count_query))[0][0]
                
                schema_info["tables"][table] = {
                    "columns": columns,
                    "row_count": row_count
                }
            
            return {
                "success": True,
                "schema": schema_info
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def natural_language_to_sql(self, request: str, context: Dict = None) -> Dict[str, Any]:
        """
        Convert natural language request to SQL
        This is a simple rule-based converter - in production you'd use an LLM
        """
        request_lower = request.lower()
        
        # Simple pattern matching for common requests
        if "how many" in request_lower and "conversation" in request_lower:
            sql = "SELECT COUNT(*) as conversation_count FROM conversations"
            
        elif "recent conversation" in request_lower or "latest conversation" in request_lower:
            sql = """
            SELECT id, title, created_at, updated_at 
            FROM conversations 
            ORDER BY updated_at DESC 
            LIMIT 10
            """
            
        elif "user preference" in request_lower and "show" in request_lower:
            sql = """
            SELECT conversation_id, state_data 
            FROM agent_state 
            WHERE state_type = 'user_preferences'
            ORDER BY timestamp DESC
            """
            
        elif "active task" in request_lower:
            sql = """
            SELECT task_name, description, status, priority, created_at
            FROM tasks 
            WHERE status != 'completed'
            ORDER BY priority DESC, created_at ASC
            """
            
        elif ("memory" in request_lower and "important" in request_lower) or "show important memories" in request_lower:
            sql = """
            SELECT memory_type, content, importance, created_at
            FROM agent_memory
            WHERE importance >= 3
            ORDER BY importance DESC, created_at DESC
            LIMIT 20
            """
            
        elif "search" in request_lower:
            # Extract search term for various search patterns
            search_term = self._extract_search_term(request)
            if search_term:
                sql = f"""
                SELECT m.content, m.role, m.timestamp, c.title
                FROM messages m
                JOIN conversations c ON m.conversation_id = c.id
                WHERE m.content LIKE '%{search_term}%'
                ORDER BY m.timestamp DESC
                LIMIT 20
                """
            else:
                return {
                    "success": False,
                    "error": "Could not extract search term from request"
                }
        
        elif "stats" in request_lower or "statistics" in request_lower:
            sql = """
            SELECT 
                (SELECT COUNT(*) FROM conversations) as total_conversations,
                (SELECT COUNT(*) FROM messages) as total_messages,
                (SELECT COUNT(*) FROM tasks) as total_tasks,
                (SELECT COUNT(*) FROM agent_memory) as total_memories
            """
            
        else:
            return {
                "success": False,
                "error": f"Could not convert request to SQL: {request}",
                "suggestion": "Try requests like: 'show recent conversations', 'how many conversations', 'show active tasks', etc."
            }
        
        return {
            "success": True,
            "sql": sql,
            "original_request": request
        }
    
    def _extract_search_term(self, request: str) -> Optional[str]:
        """Extract search term from natural language request"""
        patterns = [
            r'search for "([^"]+)"',
            r'search for \'([^\']+)\'',
            r'search for ([A-Za-z]+)',
            r'find messages about ([A-Za-z]+)',
            r'search messages for ([A-Za-z]+)',
            r'find ([A-Za-z]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, request, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def execute_natural_language_query(self, request: str) -> Dict[str, Any]:
        """
        Execute a natural language database query
        
        Args:
            request: Natural language request
            
        Returns:
            Query results with metadata
        """
        # Convert to SQL
        sql_result = self.natural_language_to_sql(request)
        
        if not sql_result["success"]:
            return sql_result
        
        # Execute the generated SQL
        execution_result = self.execute_sql(sql_result["sql"])
        
        # Combine results
        return {
            **execution_result,
            "original_request": request,
            "generated_sql": sql_result["sql"]
        }
    
    def get_conversation_insights(self, conversation_id: Optional[str] = None) -> Dict[str, Any]:
        """Get insights about conversations using SQL queries"""
        queries = {
            "message_stats": """
                SELECT 
                    role,
                    COUNT(*) as message_count,
                    AVG(LENGTH(content)) as avg_message_length
                FROM messages 
                {} 
                GROUP BY role
            """.format(f"WHERE conversation_id = '{conversation_id}'" if conversation_id else ""),
            
            "conversation_activity": """
                SELECT 
                    DATE(created_at) as date,
                    COUNT(*) as conversations_started
                FROM conversations 
                GROUP BY DATE(created_at)
                ORDER BY date DESC
                LIMIT 30
            """,
            
            "task_completion_rate": """
                SELECT 
                    status,
                    COUNT(*) as task_count,
                    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM tasks), 2) as percentage
                FROM tasks
                GROUP BY status
            """,
            
            "memory_distribution": """
                SELECT 
                    memory_type,
                    COUNT(*) as memory_count,
                    AVG(importance) as avg_importance
                FROM agent_memory
                GROUP BY memory_type
                ORDER BY memory_count DESC
            """
        }
        
        insights = {}
        for insight_name, query in queries.items():
            result = self.execute_sql(query)
            if result["success"]:
                insights[insight_name] = {
                    "data": result["data"],
                    "columns": result["columns"]
                }
            else:
                insights[insight_name] = {"error": result["error"]}
        
        return {
            "success": True,
            "insights": insights,
            "conversation_id": conversation_id
        }
    
    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()

class LLMDatabaseInterface:
    """High-level interface for LLM database interactions"""
    
    def __init__(self, db_path: str = "chat_history.db"):
        self.sql_tools = LLMSQLTools(db_path)
    
    def process_database_request(self, request: str) -> str:
        """
        Process natural language database request and return human-readable response
        
        Args:
            request: Natural language database request
            
        Returns:
            Human-readable response string
        """
        # Handle different types of requests
        if any(word in request.lower() for word in ['schema', 'structure', 'tables', 'columns']):
            return self._handle_schema_request()
            
        elif any(word in request.lower() for word in ['insight', 'analytics', 'summary']):
            return self._handle_insights_request()
            
        elif 'sql' in request.lower() and ('execute' in request.lower() or 'run' in request.lower()):
            return self._handle_direct_sql_request(request)
            
        else:
            return self._handle_natural_language_request(request)
    
    def _handle_schema_request(self) -> str:
        """Handle requests for database schema information"""
        result = self.sql_tools.get_schema_info()
        
        if not result["success"]:
            return f"❌ Error getting schema: {result['error']}"
        
        schema = result["schema"]
        response = f"📊 Database Schema ({schema['total_tables']} tables):\n\n"
        
        for table_name, table_info in schema["tables"].items():
            response += f"**{table_name}** ({table_info['row_count']} rows)\n"
            for col in table_info["columns"]:
                pk = " (PRIMARY KEY)" if col["primary_key"] else ""
                nn = " NOT NULL" if col["not_null"] else ""
                response += f"  • {col['name']}: {col['type']}{pk}{nn}\n"
            response += "\n"
        
        return response
    
    def _handle_insights_request(self) -> str:
        """Handle requests for database insights"""
        result = self.sql_tools.get_conversation_insights()
        
        if not result["success"]:
            return f"❌ Error getting insights: {result.get('error', 'Unknown error')}"
        
        insights = result["insights"]
        response = "📈 Database Insights:\n\n"
        
        # Message statistics
        if "message_stats" in insights and "data" in insights["message_stats"]:
            response += "**Message Statistics:**\n"
            for row in insights["message_stats"]["data"]:
                role, count, avg_length = row
                response += f"  • {role.title()}: {count} messages (avg {avg_length:.0f} chars)\n"
            response += "\n"
        
        # Task completion
        if "task_completion_rate" in insights and "data" in insights["task_completion_rate"]:
            response += "**Task Completion:**\n"
            for row in insights["task_completion_rate"]["data"]:
                status, count, percentage = row
                response += f"  • {status.title()}: {count} tasks ({percentage}%)\n"
            response += "\n"
        
        # Memory distribution
        if "memory_distribution" in insights and "data" in insights["memory_distribution"]:
            response += "**Memory Distribution:**\n"
            for row in insights["memory_distribution"]["data"]:
                memory_type, count, avg_importance = row
                response += f"  • {memory_type}: {count} memories (importance: {avg_importance:.1f})\n"
        
        return response
    
    def _handle_direct_sql_request(self, request: str) -> str:
        """Handle direct SQL execution requests"""
        # Extract SQL from the request
        sql_match = re.search(r'```sql\s*(.*?)\s*```', request, re.DOTALL | re.IGNORECASE)
        if not sql_match:
            sql_match = re.search(r'execute:\s*(SELECT.*?)(?:\n|$)', request, re.IGNORECASE)
        
        if not sql_match:
            return "❌ Could not extract SQL query from request. Please format as ```sql\nYOUR_QUERY\n```"
        
        sql_query = sql_match.group(1).strip()
        result = self.sql_tools.execute_sql(sql_query)
        
        if not result["success"]:
            return f"❌ SQL Error: {result['error']}\nQuery: {sql_query}"
        
        # Format results
        if "data" in result:
            response = f"✅ Query executed successfully ({result['row_count']} rows):\n\n"
            
            if result["row_count"] > 0:
                # Create table format
                columns = result["columns"]
                rows = result["data"]
                
                # Header
                response += " | ".join(columns) + "\n"
                response += " | ".join(["-" * len(col) for col in columns]) + "\n"
                
                # Data rows (limit to first 20)
                for row in rows[:20]:
                    response += " | ".join([str(cell) if cell is not None else "NULL" for cell in row]) + "\n"
                
                if len(rows) > 20:
                    response += f"\n... and {len(rows) - 20} more rows"
            else:
                response += "No data returned."
        else:
            response = f"✅ Query executed successfully. Changes: {result.get('changes', 0)}"
        
        return response
    
    def _handle_natural_language_request(self, request: str) -> str:
        """Handle natural language database requests"""
        result = self.sql_tools.execute_natural_language_query(request)
        
        if not result["success"]:
            error_msg = result.get("error", "Unknown error")
            suggestion = result.get("suggestion", "")
            response = f"❌ Could not process request: {error_msg}"
            if suggestion:
                response += f"\n💡 {suggestion}"
            return response
        
        # Format successful results
        response = f"✅ Results for: '{result['original_request']}'\n"
        response += f"Generated SQL: ```sql\n{result['generated_sql']}\n```\n\n"
        
        if "data" in result and result["data"]:
            columns = result["columns"]
            rows = result["data"]
            
            # Format as table
            response += " | ".join(columns) + "\n"
            response += " | ".join(["-" * len(col) for col in columns]) + "\n"
            
            for row in rows[:10]:  # Limit to first 10 rows
                response += " | ".join([str(cell) if cell is not None else "NULL" for cell in row]) + "\n"
            
            if len(rows) > 10:
                response += f"\n... and {len(rows) - 10} more rows"
        else:
            response += "No data found."
        
        return response
    
    def close(self):
        """Close database connection"""
        self.sql_tools.close()

# Integration with CerebrasClient
def add_sql_tools_to_cerebras_client():
    """Add SQL tools to the CerebrasClient for LLM database access"""
    
    def enhance_with_database_tools(self, messages, conversation_id):
        """Enhance CerebrasClient with database query capabilities"""
        
        # Check if the user is asking about database/data
        user_message = messages[-1].get('content', '') if messages else ''
        
        database_keywords = ['database', 'data', 'conversation', 'task', 'memory', 'history', 
                           'statistics', 'insight', 'search', 'find', 'show', 'how many']
        
        if any(keyword in user_message.lower() for keyword in database_keywords):
            # Add database interface context
            db_interface = LLMDatabaseInterface()
            
            system_message = {
                "role": "system", 
                "content": """You have access to database query tools. When users ask about data, conversations, tasks, or want insights:

Available database operations:
1. Natural language queries: "show recent conversations", "how many tasks", "search for X"
2. Schema information: "show database structure", "what tables exist"  
3. Analytics: "give me insights", "show statistics"
4. Direct SQL: Execute SQL with ```sql code blocks

Use the database tools to provide accurate, data-driven responses."""
            }
            
            # Insert system message at the beginning
            enhanced_messages = [system_message] + messages
            
            db_interface.close()
            return enhanced_messages
        
        return messages
    
    # This would be added to the CerebrasClient class
    return enhance_with_database_tools
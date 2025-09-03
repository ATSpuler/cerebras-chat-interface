#!/usr/bin/env python3
"""
Test script to validate enhanced memory-aware prompts
"""
import sys
import os
sys.path.append(os.path.dirname(__file__))

from cerebras_client import CerebrasClient
from agent_db import AgentDB
import json

def test_memory_prompt_generation():
    """Test the new memory-aware prompt generation"""
    
    # Create test database and client
    agent_db = AgentDB(":memory:")  # In-memory database for testing
    client = CerebrasClient(agent_db=agent_db)
    
    # Create test conversation
    conv_id = agent_db.create_conversation("Test Memory Prompts")
    client.set_conversation_context(conv_id)
    
    print("🧪 Testing Memory-Aware Prompt Generation\n")
    
    # Add test data to database
    print("📝 Setting up test data...")
    
    # User preferences
    agent_db.store_user_preference(conv_id, "prefers_code_count", 5)
    agent_db.store_user_preference(conv_id, "asks_questions_count", 4) 
    agent_db.store_user_preference(conv_id, "requests_explanation_count", 3)
    agent_db.store_user_preference(conv_id, "avg_message_length", 150)
    agent_db.store_user_preference(conv_id, "language", "Python")
    agent_db.store_user_preference(conv_id, "framework", "Flask")
    
    # Active tasks
    agent_db.create_task(conv_id, "Build REST API", "Create Flask API for user authentication", priority=3)
    agent_db.create_task(conv_id, "Database design", "Design SQLite schema for user data", priority=2)
    
    # Important memories
    agent_db.store_memory(conv_id, "important_facts", "User is building a Flask authentication system", 3)
    agent_db.store_memory(conv_id, "patterns", "User prefers detailed code examples with explanations", 2)
    agent_db.store_memory(conv_id, "successful_interactions", "Provided Flask-SQLAlchemy example that user implemented successfully", 2)
    
    # Test message history
    test_messages = [
        {"role": "user", "content": "How should I structure my Flask authentication routes?"}
    ]
    
    print("✅ Test data created\n")
    
    # Generate enhanced context
    print("🔍 Generating enhanced context...")
    enhanced_messages = client.get_enhanced_context(test_messages)
    
    # Analyze results
    print("📊 Analysis Results:\n")
    
    if len(enhanced_messages) > len(test_messages):
        system_message = enhanced_messages[0]
        if system_message.get("role") == "system":
            system_content = system_message["content"]
            
            print(f"✅ System message generated ({len(system_content)} characters)")
            print(f"📏 Estimated tokens: ~{len(system_content.split())}")
            print()
            
            # Check for key components
            checks = {
                "Memory instructions": "MEMORY UTILIZATION INSTRUCTIONS" in system_content,
                "Behavioral adaptation": "BEHAVIORAL ADAPTATION GUIDELINES" in system_content,
                "User preferences": "ADAPT YOUR RESPONSES" in system_content,
                "Active tasks": "ACTIVE TASKS" in system_content,
                "Important context": "IMPORTANT CONTEXT" in system_content,
                "Response guidelines": "RESPONSE GUIDELINES" in system_content
            }
            
            print("🔍 Component Analysis:")
            for component, present in checks.items():
                status = "✅" if present else "❌"
                print(f"  {status} {component}")
            
            print()
            
            # Show sample system prompt
            print("📄 Generated System Prompt Preview:")
            print("-" * 80)
            lines = system_content.split('\n')
            for i, line in enumerate(lines[:20]):  # Show first 20 lines
                print(f"{i+1:2d}: {line}")
            if len(lines) > 20:
                print(f"... ({len(lines) - 20} more lines)")
            print("-" * 80)
            
            # Token efficiency analysis
            original_simple = "Context from previous interactions:\nUser preferences: {...}\nActive tasks: [...]\nImportant context: ..."
            improvement_ratio = len(system_content) / len(original_simple)
            
            print(f"\n📈 Prompt Enhancement Metrics:")
            print(f"  • Original basic prompt: ~{len(original_simple.split())} tokens")
            print(f"  • Enhanced prompt: ~{len(system_content.split())} tokens")
            print(f"  • Enhancement ratio: {improvement_ratio:.1f}x")
            print(f"  • Instructions-to-context ratio: {system_content.count('•') / max(1, system_content.count(':')):.1f}")
            
            return True
        else:
            print("❌ System message not found in first position")
            return False
    else:
        print("❌ No system message was added to context")
        return False

def test_context_adaptation():
    """Test context adaptation based on different user patterns"""
    
    print("\n🎯 Testing Context Adaptation\n")
    
    test_scenarios = [
        {
            "name": "Code-Heavy User",
            "prefs": {"prefers_code_count": 10, "language": "Python", "framework": "Django"}
        },
        {
            "name": "Question-Heavy User", 
            "prefs": {"asks_questions_count": 15, "requests_explanation_count": 8}
        },
        {
            "name": "Minimal Context User",
            "prefs": {"message_count": 2}
        }
    ]
    
    for scenario in test_scenarios:
        print(f"📋 Scenario: {scenario['name']}")
        
        # Create test environment
        agent_db = AgentDB(":memory:")
        client = CerebrasClient(agent_db=agent_db)
        conv_id = agent_db.create_conversation(f"Test {scenario['name']}")
        client.set_conversation_context(conv_id)
        
        # Apply preferences
        for key, value in scenario["prefs"].items():
            agent_db.store_user_preference(conv_id, key, value)
        
        # Generate context
        test_messages = [{"role": "user", "content": "Help me with my project"}]
        enhanced = client.get_enhanced_context(test_messages)
        
        if len(enhanced) > 1 and enhanced[0].get("role") == "system":
            content = enhanced[0]["content"]
            
            # Check adaptations
            adaptations = []
            if "code examples" in content:
                adaptations.append("Code-focused adaptation")
            if "thorough in explanations" in content:
                adaptations.append("Explanation-focused adaptation") 
            if "Django" in content:
                adaptations.append("Framework-specific adaptation")
            
            print(f"  ✅ Generated {len(content.split())} token prompt")
            print(f"  🎯 Adaptations: {', '.join(adaptations) if adaptations else 'Generic prompt'}")
        else:
            print("  ❌ No system prompt generated")
        
        print()

if __name__ == "__main__":
    print("🚀 Memory-Aware Prompt Testing Suite\n")
    
    try:
        success = test_memory_prompt_generation()
        test_context_adaptation()
        
        if success:
            print("🎉 All tests completed successfully!")
            print("\n💡 Next steps:")
            print("  1. Run the chat application to test with real conversations")
            print("  2. Monitor response quality improvements")
            print("  3. Adjust prompt templates based on user feedback")
        else:
            print("⚠️  Some tests failed - check implementation")
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
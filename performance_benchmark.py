#!/usr/bin/env python3
"""
Performance benchmark for Agent-Database binding
Measures quantitative performance improvements
"""

import os
import sys
import time
import json
import statistics
from typing import List, Dict, Any, Tuple
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agent_db import AgentDB
from cerebras_client import CerebrasClient
from chat_history import ChatHistory

class PerformanceBenchmark:
    def __init__(self):
        self.results = {}
        
    def benchmark_database_operations(self, iterations: int = 1000) -> Dict[str, float]:
        """Benchmark core database operations"""
        print(f"🚀 Benchmarking database operations ({iterations} iterations)")
        
        # Test with AgentDB
        agent_db = AgentDB("benchmark_agent.db")
        agent_times = []
        
        # Test with basic ChatHistory  
        basic_db = ChatHistory("benchmark_basic.db")
        basic_times = []
        
        # Benchmark conversation creation and message insertion
        for i in range(iterations):
            # AgentDB timing
            start = time.perf_counter()
            conv_id = agent_db.create_conversation(f"Benchmark Conversation {i}")
            agent_db.add_message(conv_id, "user", f"Test message {i}")
            agent_db.add_message(conv_id, "assistant", f"Response {i}")
            agent_times.append(time.perf_counter() - start)
            
            # Basic DB timing
            start = time.perf_counter()
            basic_conv_id = basic_db.create_conversation(f"Benchmark Conversation {i}")
            basic_db.add_message(basic_conv_id, "user", f"Test message {i}")
            basic_db.add_message(basic_conv_id, "assistant", f"Response {i}")
            basic_times.append(time.perf_counter() - start)
        
        # Calculate statistics
        agent_avg = statistics.mean(agent_times) * 1000  # Convert to milliseconds
        basic_avg = statistics.mean(basic_times) * 1000
        overhead = ((agent_avg - basic_avg) / basic_avg) * 100
        
        # Cleanup
        agent_db.close()
        basic_db.close()
        os.remove("benchmark_agent.db")
        os.remove("benchmark_basic.db")
        
        results = {
            "agent_db_avg_ms": round(agent_avg, 3),
            "basic_db_avg_ms": round(basic_avg, 3),
            "overhead_percentage": round(overhead, 2),
            "iterations": iterations
        }
        
        print(f"   AgentDB: {agent_avg:.3f}ms avg")
        print(f"   BasicDB: {basic_avg:.3f}ms avg")
        print(f"   Overhead: {overhead:.2f}%")
        
        return results
    
    def benchmark_memory_operations(self, iterations: int = 500) -> Dict[str, float]:
        """Benchmark memory storage and retrieval"""
        print(f"🧠 Benchmarking memory operations ({iterations} iterations)")
        
        agent_db = AgentDB("benchmark_memory.db")
        conv_id = agent_db.create_conversation("Memory Benchmark")
        
        # Benchmark memory storage
        storage_times = []
        for i in range(iterations):
            start = time.perf_counter()
            agent_db.store_memory(conv_id, "benchmark_facts", f"Important fact {i}", importance=2)
            storage_times.append(time.perf_counter() - start)
        
        # Benchmark memory retrieval
        retrieval_times = []
        for i in range(iterations):
            start = time.perf_counter()
            memories = agent_db.retrieve_memories("benchmark_facts", limit=10)
            retrieval_times.append(time.perf_counter() - start)
        
        # Benchmark context building
        context_times = []
        for i in range(100):  # Fewer iterations for complex operation
            start = time.perf_counter()
            context = agent_db.get_conversation_context(conv_id)
            context_times.append(time.perf_counter() - start)
        
        storage_avg = statistics.mean(storage_times) * 1000
        retrieval_avg = statistics.mean(retrieval_times) * 1000
        context_avg = statistics.mean(context_times) * 1000
        
        # Cleanup
        agent_db.close()
        os.remove("benchmark_memory.db")
        
        results = {
            "memory_storage_ms": round(storage_avg, 3),
            "memory_retrieval_ms": round(retrieval_avg, 3),
            "context_building_ms": round(context_avg, 3),
            "storage_iterations": iterations,
            "retrieval_iterations": iterations,
            "context_iterations": 100
        }
        
        print(f"   Memory Storage: {storage_avg:.3f}ms avg")
        print(f"   Memory Retrieval: {retrieval_avg:.3f}ms avg")
        print(f"   Context Building: {context_avg:.3f}ms avg")
        
        return results
    
    def benchmark_context_enhancement(self, iterations: int = 100) -> Dict[str, Any]:
        """Benchmark context enhancement impact"""
        print(f"🔍 Benchmarking context enhancement ({iterations} iterations)")
        
        agent_db = AgentDB("benchmark_context.db")
        client = CerebrasClient(agent_db=agent_db)
        conv_id = agent_db.create_conversation("Context Benchmark")
        client.set_conversation_context(conv_id)
        
        # Set up context data
        agent_db.store_user_preference(conv_id, "language", "Python")
        agent_db.store_user_preference(conv_id, "experience", "intermediate")
        agent_db.create_task(conv_id, "Build API", "REST API development", 3)
        agent_db.store_memory(conv_id, "important_facts", "Working on Flask project", 3)
        
        # Test messages
        test_messages = [{"role": "user", "content": "How do I handle database connections?"}]
        
        # Benchmark without enhancement
        no_enhance_times = []
        for i in range(iterations):
            start = time.perf_counter()
            result = client.get_enhanced_context(test_messages)  # This will return original if no context
            no_enhance_times.append(time.perf_counter() - start)
        
        # Benchmark with enhancement
        enhance_times = []
        message_length_increases = []
        
        for i in range(iterations):
            start = time.perf_counter()
            enhanced = client.get_enhanced_context(test_messages)
            enhance_times.append(time.perf_counter() - start)
            
            # Measure context addition
            original_length = len(json.dumps(test_messages))
            enhanced_length = len(json.dumps(enhanced))
            message_length_increases.append(enhanced_length - original_length)
        
        no_enhance_avg = statistics.mean(no_enhance_times) * 1000
        enhance_avg = statistics.mean(enhance_times) * 1000
        avg_length_increase = statistics.mean(message_length_increases)
        enhancement_overhead = ((enhance_avg - no_enhance_avg) / no_enhance_avg) * 100 if no_enhance_avg > 0 else 0
        
        # Cleanup
        agent_db.close()
        os.remove("benchmark_context.db")
        
        results = {
            "base_processing_ms": round(no_enhance_avg, 3),
            "enhanced_processing_ms": round(enhance_avg, 3),
            "enhancement_overhead_pct": round(enhancement_overhead, 2),
            "avg_context_size_increase_chars": round(avg_length_increase, 0),
            "iterations": iterations
        }
        
        print(f"   Base Processing: {no_enhance_avg:.3f}ms avg")
        print(f"   Enhanced Processing: {enhance_avg:.3f}ms avg")
        print(f"   Enhancement Overhead: {enhancement_overhead:.2f}%")
        print(f"   Avg Context Size Increase: {avg_length_increase:.0f} chars")
        
        return results
    
    def benchmark_learning_effectiveness(self) -> Dict[str, Any]:
        """Benchmark learning and pattern recognition effectiveness"""
        print("🎓 Benchmarking learning effectiveness")
        
        agent_db = AgentDB("benchmark_learning.db")
        client = CerebrasClient(agent_db=agent_db)
        conv_id = agent_db.create_conversation("Learning Benchmark")
        client.set_conversation_context(conv_id)
        
        # Simulate user interaction patterns
        coding_messages = [
            "How do I create a class in Python?",
            "Show me an example of inheritance",
            "What's the difference between list and tuple?",
            "Can you write a function that sorts a list?",
            "How do I handle exceptions in Python?"
        ]
        
        question_messages = [
            "What is machine learning?",
            "How does a neural network work?",
            "What are the benefits of cloud computing?",
            "Why should I use version control?",
            "What's the difference between SQL and NoSQL?"
        ]
        
        # Process messages and measure learning
        start_preferences = agent_db.get_agent_state(conv_id, "user_preferences") or {}
        
        # Simulate coding-focused interactions
        for msg in coding_messages:
            client.analyze_user_pattern(msg)
        
        # Simulate question-focused interactions  
        for msg in question_messages:
            client.analyze_user_pattern(msg)
        
        # Measure learned patterns
        final_preferences = agent_db.get_agent_state(conv_id, "user_preferences") or {}
        
        # Calculate learning metrics
        patterns_learned = len(final_preferences) - len(start_preferences)
        code_preference_count = agent_db.get_user_preference(conv_id, "prefers_code_count", 0)
        question_count = agent_db.get_user_preference(conv_id, "asks_questions_count", 0)
        
        # Test memory storage
        memories_before = len(agent_db.retrieve_memories("patterns", 100))
        agent_db.store_memory(conv_id, "patterns", "User prefers Python examples", 3)
        agent_db.store_memory(conv_id, "patterns", "User asks theoretical questions", 2)
        memories_after = len(agent_db.retrieve_memories("patterns", 100))
        
        # Cleanup
        agent_db.close()
        os.remove("benchmark_learning.db")
        
        results = {
            "patterns_learned": patterns_learned,
            "code_preferences_detected": code_preference_count,
            "questions_detected": question_count,
            "memory_storage_working": memories_after > memories_before,
            "learning_accuracy_pct": round((code_preference_count / len(coding_messages)) * 100, 1),
            "total_interactions_processed": len(coding_messages) + len(question_messages)
        }
        
        print(f"   Patterns Learned: {patterns_learned}")
        print(f"   Code Preferences Detected: {code_preference_count}/{len(coding_messages)}")
        print(f"   Questions Detected: {question_count}/{len(question_messages)}")
        print(f"   Learning Accuracy: {results['learning_accuracy_pct']}%")
        
        return results
    
    def benchmark_scalability(self) -> Dict[str, Any]:
        """Benchmark system scalability with growing data"""
        print("📈 Benchmarking scalability")
        
        agent_db = AgentDB("benchmark_scale.db")
        
        # Test performance with increasing data volume
        data_points = [100, 500, 1000, 2000]
        scalability_results = {}
        
        for data_size in data_points:
            print(f"   Testing with {data_size} records...")
            
            # Create conversations and data
            conv_ids = []
            for i in range(data_size):
                conv_id = agent_db.create_conversation(f"Scale Test {i}")
                conv_ids.append(conv_id)
                agent_db.add_message(conv_id, "user", f"User message {i}")
                agent_db.add_message(conv_id, "assistant", f"Assistant response {i}")
                
                if i % 10 == 0:  # Add some memories and tasks
                    agent_db.store_memory(conv_id, "facts", f"Important fact {i}", 2)
                    agent_db.create_task(conv_id, f"Task {i}", f"Description {i}", 1)
            
            # Measure retrieval performance
            start = time.perf_counter()
            stats = agent_db.get_agent_stats()
            stats_time = time.perf_counter() - start
            
            start = time.perf_counter()
            conversations = agent_db.get_conversations()
            list_time = time.perf_counter() - start
            
            start = time.perf_counter()
            context = agent_db.get_conversation_context(conv_ids[0])
            context_time = time.perf_counter() - start
            
            scalability_results[data_size] = {
                "stats_query_ms": round(stats_time * 1000, 3),
                "list_conversations_ms": round(list_time * 1000, 3),
                "context_retrieval_ms": round(context_time * 1000, 3),
                "database_size_kb": round(os.path.getsize("benchmark_scale.db") / 1024, 2)
            }
        
        # Calculate scalability trends
        stats_times = [scalability_results[size]["stats_query_ms"] for size in data_points]
        list_times = [scalability_results[size]["list_conversations_ms"] for size in data_points]
        db_sizes = [scalability_results[size]["database_size_kb"] for size in data_points]
        
        # Cleanup
        agent_db.close()
        os.remove("benchmark_scale.db")
        
        results = {
            "data_points_tested": data_points,
            "performance_by_size": scalability_results,
            "stats_query_trend": "linear" if max(stats_times) / min(stats_times) < 3 else "exponential",
            "database_growth_trend": "expected" if max(db_sizes) / min(db_sizes) < 50 else "concerning",
            "max_database_size_kb": max(db_sizes),
            "performance_degradation_pct": round(((max(stats_times) - min(stats_times)) / min(stats_times)) * 100, 1)
        }
        
        print(f"   Database Growth: {min(db_sizes):.1f}KB → {max(db_sizes):.1f}KB")
        print(f"   Performance Degradation: {results['performance_degradation_pct']}%")
        
        return results
    
    def run_full_benchmark(self) -> Dict[str, Any]:
        """Run complete performance benchmark suite"""
        print("🏃‍♂️ Starting Full Performance Benchmark Suite")
        print("=" * 70)
        
        start_time = time.time()
        
        # Run all benchmarks
        self.results = {
            "database_operations": self.benchmark_database_operations(),
            "memory_operations": self.benchmark_memory_operations(), 
            "context_enhancement": self.benchmark_context_enhancement(),
            "learning_effectiveness": self.benchmark_learning_effectiveness(),
            "scalability": self.benchmark_scalability()
        }
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        # Generate performance score
        score_factors = {
            "database_overhead": max(0, 100 - self.results["database_operations"]["overhead_percentage"]),
            "memory_performance": min(100, 1000 / max(1, self.results["memory_operations"]["memory_storage_ms"])),
            "context_efficiency": max(0, 100 - self.results["context_enhancement"]["enhancement_overhead_pct"]),
            "learning_accuracy": self.results["learning_effectiveness"]["learning_accuracy_pct"],
            "scalability_score": max(0, 100 - self.results["scalability"]["performance_degradation_pct"])
        }
        
        overall_score = statistics.mean(score_factors.values())
        
        # Summary
        summary = {
            "overall_performance_score": round(overall_score, 1),
            "benchmark_duration_seconds": round(total_duration, 2),
            "score_breakdown": {k: round(v, 1) for k, v in score_factors.items()},
            "timestamp": datetime.now().isoformat(),
            "recommendation": self._get_performance_recommendation(overall_score)
        }
        
        print("\n" + "=" * 70)
        print("📊 PERFORMANCE BENCHMARK SUMMARY")
        print("=" * 70)
        print(f"Overall Performance Score: {overall_score:.1f}/100")
        print(f"Benchmark Duration: {total_duration:.2f} seconds")
        print("\nScore Breakdown:")
        for factor, score in score_factors.items():
            print(f"  {factor.replace('_', ' ').title()}: {score:.1f}/100")
        print(f"\nRecommendation: {summary['recommendation']}")
        
        return {**summary, "detailed_results": self.results}
    
    def _get_performance_recommendation(self, score: float) -> str:
        """Get performance recommendation based on score"""
        if score >= 90:
            return "Excellent performance! System is production-ready."
        elif score >= 80:
            return "Good performance with minor optimization opportunities."
        elif score >= 70:
            return "Acceptable performance but consider optimizations."
        elif score >= 60:
            return "Performance issues detected. Optimization needed."
        else:
            return "Poor performance. Significant optimization required."
    
    def save_benchmark_report(self, filename: str = "agent_db_performance_report.json"):
        """Save detailed benchmark report"""
        if not self.results:
            print("No benchmark results to save. Run benchmark first.")
            return
        
        report = self.run_full_benchmark() if not hasattr(self, '_summary') else self.results
        
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"📄 Performance report saved to: {filename}")
        return report

def main():
    """Main benchmark execution"""
    benchmark = PerformanceBenchmark()
    
    try:
        results = benchmark.run_full_benchmark()
        benchmark.save_benchmark_report()
        
        # Return appropriate exit code based on performance
        score = results.get("overall_performance_score", 0)
        exit_code = 0 if score >= 70 else 1
        
        return exit_code, results
        
    except Exception as e:
        print(f"🚨 Benchmark error: {e}")
        return 2, {"error": str(e)}

if __name__ == "__main__":
    exit_code, results = main()
    sys.exit(exit_code)
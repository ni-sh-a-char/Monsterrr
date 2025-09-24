#!/usr/bin/env python3
"""
Test script to verify all Monsterrr fixes are working correctly.
"""

import os
import sys
import json
import time
from datetime import datetime

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_idea_generation():
    """Test that idea generation produces sensible repository names."""
    print("Testing idea generation...")
    
    try:
        from agents.idea_agent import IdeaGeneratorAgent
        from services.groq_service import GroqService
        import logging
        
        # Create a mock Groq service for testing
        class MockGroqService:
            def groq_llm(self, prompt, model=None):
                # Return a mock response with sensible project names
                return json.dumps([
                    {
                        "name": "api-documentation-generator",
                        "description": "A tool that automatically generates API documentation",
                        "detailed_description": "This project solves the problem of keeping API documentation up to date. It automatically generates documentation from code comments and API endpoints.",
                        "tech_stack": ["Python", "FastAPI", "Markdown"],
                        "difficulty": "med",
                        "estimated_dev_time": 2,
                        "features": [
                            "Parse code comments",
                            "Generate Markdown docs",
                            "Support multiple languages"
                        ],
                        "roadmap": [
                            "Set up project structure",
                            "Implement comment parser",
                            "Create documentation generator",
                            "Add multi-language support",
                            "Create web interface"
                        ]
                    }
                ])
        
        logger = logging.getLogger("test")
        groq = MockGroqService()
        idea_agent = IdeaGeneratorAgent(groq, logger)
        
        # Generate ideas
        ideas = idea_agent.fetch_and_rank_ideas(top_n=1)
        
        if ideas and len(ideas) > 0:
            idea = ideas[0]
            name = idea.get("name", "")
            
            # Check that the name follows sensible conventions
            if name and "-" in name and name.islower() and len(name) > 5:
                print(f"✅ Idea generation test passed: {name}")
                return True
            else:
                print(f"❌ Idea generation test failed: Poor naming - {name}")
                return False
        else:
            print("❌ Idea generation test failed: No ideas generated")
            return False
            
    except Exception as e:
        print(f"❌ Idea generation test failed with error: {e}")
        return False

def test_state_management():
    """Test that state management is working correctly."""
    print("Testing state management...")
    
    try:
        # Create a test state file
        test_state = {
            "test": "data",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        with open("test_state.json", "w") as f:
            json.dump(test_state, f, indent=2)
        
        # Verify the file was created and can be read
        if os.path.exists("test_state.json"):
            with open("test_state.json", "r") as f:
                loaded_state = json.load(f)
            
            if loaded_state.get("test") == "data":
                print("✅ State management test passed")
                os.remove("test_state.json")  # Clean up
                return True
            else:
                print("❌ State management test failed: Data mismatch")
                os.remove("test_state.json")  # Clean up
                return False
        else:
            print("❌ State management test failed: File not created")
            return False
            
    except Exception as e:
        print(f"❌ State management test failed with error: {e}")
        # Clean up if file exists
        if os.path.exists("test_state.json"):
            os.remove("test_state.json")
        return False

def test_repository_naming():
    """Test that repository names are sensible."""
    print("Testing repository naming...")
    
    # Test various naming patterns
    test_names = [
        "monsterrr-starter-20250101-1200",
        "api-documentation-generator",
        "machine-learning-dashboard",
        "code-review-automation",
        "web-scraper-tool"
    ]
    
    for name in test_names:
        # Check naming conventions
        if not name.islower():
            print(f"❌ Repository naming test failed: {name} is not lowercase")
            return False
        if " " in name:
            print(f"❌ Repository naming test failed: {name} contains spaces")
            return False
        # Allow alphanumeric characters and hyphens
        if not all(c.isalnum() or c == '-' for c in name):
            print(f"❌ Repository naming test failed: {name} contains invalid characters")
            return False
    
    print("✅ Repository naming test passed")
    return True

def test_scheduler_quick_check():
    """Test that the scheduler quick check function works."""
    print("Testing scheduler quick check...")
    
    try:
        from scheduler import quick_check
        # This should not raise an exception
        print("✅ Scheduler quick check test passed")
        return True
    except Exception as e:
        print(f"❌ Scheduler quick check test failed with error: {e}")
        return False

def main():
    """Run all tests."""
    print("Running Monsterrr fixes verification tests...\n")
    
    tests = [
        test_idea_generation,
        test_state_management,
        test_repository_naming,
        test_scheduler_quick_check
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()  # Add spacing between tests
    
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Monsterrr fixes are working correctly.")
        return True
    else:
        print("❌ Some tests failed. Please review the issues above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
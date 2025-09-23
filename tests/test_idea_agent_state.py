"""
Test for IdeaGeneratorAgent state management.
"""

import pytest
import json
import os
from unittest.mock import MagicMock
from agents.idea_agent import IdeaGeneratorAgent

@pytest.fixture
def agent():
    groq = MagicMock()
    logger = MagicMock()
    return IdeaGeneratorAgent(groq, logger)

def test_load_state_empty_file(agent):
    """Test loading state when file doesn't exist."""
    # Make sure the file doesn't exist
    if os.path.exists("test_state.json"):
        os.remove("test_state.json")
    
    # Temporarily change the IDEA_FILE for testing
    original_file = agent.IDEA_FILE
    agent.IDEA_FILE = "test_state.json"
    
    state = agent._load_state()
    assert state == {}
    
    # Restore original file path
    agent.IDEA_FILE = original_file

def test_save_and_load_state(agent):
    """Test saving and loading state."""
    # Temporarily change the IDEA_FILE for testing
    original_file = agent.IDEA_FILE
    agent.IDEA_FILE = "test_state.json"
    
    # Clean up any existing test file
    if os.path.exists("test_state.json"):
        os.remove("test_state.json")
    
    # Test saving state
    test_state = {
        "ideas": {
            "generated_at": "2023-01-01T00:00:00",
            "top_ideas": [
                {"name": "Test Idea", "description": "A test idea"}
            ]
        }
    }
    
    agent._save_state(test_state)
    
    # Test loading state
    loaded_state = agent._load_state()
    assert loaded_state == test_state
    
    # Clean up
    if os.path.exists("test_state.json"):
        os.remove("test_state.json")
    
    # Restore original file path
    agent.IDEA_FILE = original_file

def test_load_state_corrupted_file(agent):
    """Test loading state when file is corrupted."""
    # Temporarily change the IDEA_FILE for testing
    original_file = agent.IDEA_FILE
    agent.IDEA_FILE = "test_state.json"
    
    # Create a corrupted file
    with open("test_state.json", "w") as f:
        f.write("invalid json content")
    
    state = agent._load_state()
    assert state == {}
    
    # Clean up
    if os.path.exists("test_state.json"):
        os.remove("test_state.json")
    
    # Restore original file path
    agent.IDEA_FILE = original_file
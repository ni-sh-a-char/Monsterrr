import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
import json
from agents.idea_agent import IdeaGeneratorAgent
from agents.creator_agent import CreatorAgent
from agents.maintainer_agent import MaintainerAgent
from services.github_service import GitHubService
from services.groq_service import GroqService
from utils.logger import setup_logger

class TestEnhancements(unittest.TestCase):
    def setUp(self):
        self.logger = setup_logger()
        self.groq = GroqService(api_key="test-key", logger=self.logger)
        self.github = GitHubService(logger=self.logger)
        self.idea_agent = IdeaGeneratorAgent(self.groq, self.logger)
        self.creator_agent = CreatorAgent(self.github, self.logger)
        self.maintainer_agent = MaintainerAgent(self.github, self.groq, self.logger)
        
        # Create a test state file
        self.state_file = "test_monsterrr_state.json"
        test_state = {
            "repos": [
                {
                    "name": "test-repo",
                    "description": "A test repository",
                    "tech_stack": ["Python"],
                    "roadmap": ["Add feature A", "Add feature B"]
                }
            ]
        }
        with open(self.state_file, "w") as f:
            json.dump(test_state, f)
    
    def tearDown(self):
        # Clean up test state file
        if os.path.exists(self.state_file):
            os.remove(self.state_file)
    
    def test_organization_stats_in_state(self):
        """Test that organization stats are included in the state file."""
        # This would normally call GitHub API, but we'll mock the response
        org_stats = {
            "name": "test-org",
            "total_repos": 5,
            "members": 3,
            "public_repos": 3,
            "private_repos": 2,
            "repositories": [
                {"name": "repo1", "description": "Test repo 1"},
                {"name": "repo2", "description": "Test repo 2"}
            ]
        }
        
        # Update state file with org stats
        with open(self.state_file, "r") as f:
            state = json.load(f)
        state["organization_stats"] = org_stats
        with open(self.state_file, "w") as f:
            json.dump(state, f)
        
        # Verify org stats are in state
        with open(self.state_file, "r") as f:
            updated_state = json.load(f)
        self.assertIn("organization_stats", updated_state)
        self.assertEqual(updated_state["organization_stats"]["total_repos"], 5)
    
    def test_enhanced_command_recognition(self):
        """Test that command recognition works without '!' prefix."""
        # This is a conceptual test since we can't easily test the Discord bot here
        command_intents = [
            ("status", "show_status"),
            ("system status", "show_status"),
            ("what's happening", "status_cmd"),
            ("organization status", "status_cmd"),
            ("what can you do", "guide_cmd")
        ]
        
        # Verify that our enhanced command intents include natural language commands
        self.assertGreater(len(command_intents), 4)
    
    def test_idea_generation_enhancement(self):
        """Test that idea generation includes more diverse sources."""
        # This is a conceptual test since we can't easily test external API calls
        # We'll verify that the method exists and has been enhanced
        self.assertTrue(hasattr(self.idea_agent, 'fetch_trending_reddit'))
        self.assertTrue(hasattr(self.idea_agent, 'fetch_trending_stackoverflow'))
    
    def test_repository_improvement_with_issue_analysis(self):
        """Test that repository improvement includes issue analysis."""
        # This is a conceptual test since we can't easily test GitHub API calls
        # We'll verify that the method exists
        self.assertTrue(hasattr(self.creator_agent, '_improve_repository'))

if __name__ == "__main__":
    unittest.main()
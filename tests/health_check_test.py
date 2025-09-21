import unittest
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Simple test to verify health endpoints exist in the app
from main import app

class TestHealthEndpoints(unittest.TestCase):
    def test_health_endpoint_exists(self):
        """Test that the health endpoint exists"""
        # Check if the health endpoint is registered in the app
        health_routes = [route for route in app.routes if route.path == "/health"]
        self.assertTrue(len(health_routes) > 0, "Health endpoint should exist")
        
    def test_healthz_endpoint_exists(self):
        """Test that the healthz endpoint exists"""
        # Check if the healthz endpoint is registered in the app
        healthz_routes = [route for route in app.routes if route.path == "/healthz"]
        self.assertTrue(len(healthz_routes) > 0, "Healthz endpoint should exist")

if __name__ == "__main__":
    unittest.main()
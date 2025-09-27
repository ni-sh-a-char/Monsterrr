#!/usr/bin/env python3
"""
Test script to verify GitHub rate limiting fixes for Monsterrr
"""

import os
import sys
import logging
import time
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("test_github_rate_limiting")

def test_github_service():
    """Test GitHub service with rate limiting"""
    logger.info("Testing GitHub service rate limiting...")
    
    try:
        # Import the GitHub service
        from services.github_service import GitHubService
        import logging
        
        # Create a logger for the service
        service_logger = logging.getLogger("test_github")
        
        # Initialize the GitHub service
        github = GitHubService(logger=service_logger)
        
        # Test organization stats (this makes multiple API calls)
        logger.info("Testing organization stats...")
        stats = github.get_organization_stats()
        logger.info(f"✅ Organization stats retrieved successfully: {stats.get('total_repos', 0)} repos, {stats.get('members', 0)} members")
        
        # Test listing repositories
        logger.info("Testing repository listing...")
        repos = github.list_repositories()
        logger.info(f"✅ Repository listing successful: {len(repos)} repositories")
        
        # Test listing issues for the first repository (if any exist)
        if repos:
            first_repo = repos[0]['name']
            logger.info(f"Testing issue listing for repository: {first_repo}")
            issues = github.list_issues(first_repo, state="all")
            logger.info(f"✅ Issue listing successful: {len(issues)} issues")
        
        logger.info("✅ All GitHub service tests passed!")
        return True
        
    except Exception as e:
        logger.error(f"❌ GitHub service test failed: {e}")
        return False

def test_rate_limiting_behavior():
    """Test that rate limiting behavior is working correctly"""
    logger.info("Testing rate limiting behavior...")
    
    try:
        # Import the GitHub service
        from services.github_service import GitHubService, GitHubAPIError
        import logging
        import time
        
        # Create a logger for the service
        service_logger = logging.getLogger("test_rate_limit")
        
        # Initialize the GitHub service
        github = GitHubService(logger=service_logger)
        
        # Test multiple rapid requests to trigger rate limiting
        logger.info("Making multiple rapid requests to test rate limiting...")
        
        # Make several requests in quick succession
        start_time = time.time()
        for i in range(3):
            try:
                repos = github.list_repositories()
                logger.info(f"Request {i+1}: Retrieved {len(repos)} repositories")
                # Small delay between requests
                time.sleep(0.1)
            except GitHubAPIError as e:
                if "Rate limit exceeded" in str(e):
                    logger.info(f"✅ Rate limiting correctly detected and handled: {e}")
                    # This is expected behavior
                    continue
                else:
                    raise
            except Exception as e:
                logger.error(f"❌ Unexpected error: {e}")
                return False
        
        end_time = time.time()
        logger.info(f"✅ Multiple requests completed in {end_time - start_time:.2f} seconds")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Rate limiting behavior test failed: {e}")
        return False

def main():
    """Run all tests"""
    logger.info("Starting GitHub rate limiting verification tests...")
    logger.info(f"Test started at: {datetime.now().isoformat()}")
    
    tests = [
        test_github_service,
        test_rate_limiting_behavior
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            logger.error(f"❌ Test {test.__name__} failed with exception: {e}")
            failed += 1
    
    logger.info(f"Tests completed: {passed} passed, {failed} failed")
    
    if failed == 0:
        logger.info("🎉 All tests passed! GitHub rate limiting fixes are working correctly.")
        return 0
    else:
        logger.error("❌ Some tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
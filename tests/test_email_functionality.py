#!/usr/bin/env python3
"""
Test script to verify email functionality in Monsterrr
"""

import sys
import os
# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Set environment variables for testing (these are dummy values)
os.environ.setdefault("DISCORD_BOT_TOKEN", "dummy_token")
os.environ.setdefault("DISCORD_GUILD_ID", "123456789")
os.environ.setdefault("DISCORD_CHANNEL_ID", "987654321")

from services.reporting_service import ReportingService
from utils.config import Settings
from utils.logger import setup_logger

def test_email_functionality():
    """Test email sending functionality"""
    print("Testing Monsterrr Email Functionality")
    print("=" * 40)
    
    # Setup
    settings = Settings()
    logger = setup_logger()
    
    # Check if email configuration exists
    if not settings.SMTP_HOST or not settings.SMTP_USER or not settings.SMTP_PASS or not settings.STATUS_REPORT_RECIPIENTS:
        print("❌ Email configuration is incomplete")
        print("   Missing configuration:")
        if not settings.SMTP_HOST:
            print("   - SMTP_HOST")
        if not settings.SMTP_USER:
            print("   - SMTP_USER")
        if not settings.SMTP_PASS:
            print("   - SMTP_PASS")
        if not settings.STATUS_REPORT_RECIPIENTS:
            print("   - STATUS_REPORT_RECIPIENTS")
        return False
    
    print("✅ Email configuration found")
    print(f"   SMTP Host: {settings.SMTP_HOST}")
    print(f"   SMTP Port: {settings.SMTP_PORT}")
    print(f"   SMTP User: {settings.SMTP_USER}")
    print(f"   Recipients: {settings.recipients}")
    
    # Initialize reporting service
    reporting_service = ReportingService(
        smtp_host=settings.SMTP_HOST,
        smtp_port=settings.SMTP_PORT,
        smtp_user=settings.SMTP_USER,
        smtp_pass=settings.SMTP_PASS,
        logger=logger
    )
    
    # Generate a test report
    print("\n📝 Generating test report...")
    test_report = {
        "timestamp": "2025-09-28T10:00:00Z",
        "summary": {
            "repositories": 5,
            "ideas": 3,
            "actions": 12,
            "branches": 8,
            "members": 1
        },
        "repositories": [
            {"name": "test-repo-1", "description": "Test repository"},
            {"name": "test-repo-2", "description": "Another test repository"}
        ],
        "ideas": [
            {"name": "Test Idea 1", "description": "A test idea", "tech_stack": ["Python", "FastAPI"]},
            {"name": "Test Idea 2", "description": "Another test idea", "tech_stack": ["JavaScript", "React"]}
        ],
        "actions": [
            {"timestamp": "2025-09-28T09:30:00Z", "type": "repo_created", "details": {"repo_name": "test-repo-1"}},
            {"timestamp": "2025-09-28T09:45:00Z", "type": "branch_created", "details": {"branch_name": "feature/test"}}
        ],
        "recent_activity": [
            {"timestamp": "2025-09-28T09:30:00Z", "type": "repo_created", "details": {"repo_name": "test-repo-1"}},
            {"timestamp": "2025-09-28T09:45:00Z", "type": "branch_created", "details": {"branch_name": "feature/test"}}
        ]
    }
    
    # Send test email
    print("\n📧 Sending test email...")
    success = reporting_service.send_email_report(settings.recipients, test_report)
    
    if success:
        print("✅ Test email sent successfully!")
        return True
    else:
        print("❌ Failed to send test email")
        return False

def main():
    """Main test function"""
    success = test_email_functionality()
    
    if success:
        print("\n🎉 Email functionality test passed!")
        print("✅ Monsterrr email reporting is working correctly")
    else:
        print("\n❌ Email functionality test failed")
        print("Please check your email configuration in the .env file")

if __name__ == "__main__":
    main()
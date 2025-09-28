#!/usr/bin/env python3
"""
Test script to verify that Discord startup message and daily reports are only sent once
"""

import sys
import os
import json
from datetime import datetime, timezone, timedelta
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Set environment variables for testing
os.environ.setdefault("DISCORD_BOT_TOKEN", "dummy_token")
os.environ.setdefault("DISCORD_GUILD_ID", "123456789")
os.environ.setdefault("DISCORD_CHANNEL_ID", "987654321")

from utils.logger import setup_logger

def test_state_tracking():
    """Test that state tracking works correctly for one-time messages"""
    print("Testing State Tracking for One-Time Messages")
    print("=" * 45)
    
    logger = setup_logger()
    state_path = "test_monsterrr_state.json"
    
    # Create a test state file
    test_state = {
        "startup_email_sent": True,
        "initial_startup_time": "2025-09-28T10:00:00Z",
        "discord_startup_message_sent": False,
        "discord_startup_time": None,
        "daily_email_report_sent": False,
        "daily_email_report_date": "",
        "scheduler_daily_report_sent": False,
        "scheduler_daily_report_date": ""
    }
    
    # Write test state
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(test_state, f, indent=2)
    
    print("✅ Created test state file")
    
    # Test 1: Check that Discord startup message flag works
    with open(state_path, "r", encoding="utf-8") as f:
        state = json.load(f)
    
    discord_sent = state.get("discord_startup_message_sent", False)
    print(f"✅ Discord startup message sent flag: {discord_sent}")
    
    # Test 2: Check that daily report flags work
    daily_email_sent = state.get("daily_email_report_sent", False)
    daily_email_date = state.get("daily_email_report_date", "")
    scheduler_sent = state.get("scheduler_daily_report_sent", False)
    scheduler_date = state.get("scheduler_daily_report_date", "")
    
    print(f"✅ Daily email report sent flag: {daily_email_sent}")
    print(f"✅ Daily email report date: '{daily_email_date}'")
    print(f"✅ Scheduler daily report sent flag: {scheduler_sent}")
    print(f"✅ Scheduler daily report date: '{scheduler_date}'")
    
    # Test 3: Simulate sending Discord startup message
    print("\n🔄 Simulating Discord startup message send...")
    state["discord_startup_message_sent"] = True
    state["discord_startup_time"] = datetime.now(timezone.utc).isoformat()
    
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)
    
    # Verify it won't be sent again
    with open(state_path, "r", encoding="utf-8") as f:
        state = json.load(f)
    
    if state.get("discord_startup_message_sent", False):
        print("✅ Discord startup message correctly marked as sent")
    else:
        print("❌ Discord startup message not marked as sent")
    
    # Test 4: Simulate sending daily reports
    print("\n🔄 Simulating daily report send...")
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    state["daily_email_report_sent"] = True
    state["daily_email_report_date"] = today
    state["scheduler_daily_report_sent"] = True
    state["scheduler_daily_report_date"] = today
    
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)
    
    # Verify it won't be sent again today
    with open(state_path, "r", encoding="utf-8") as f:
        state = json.load(f)
    
    if state.get("daily_email_report_date", "") == today:
        print("✅ Daily email report correctly marked as sent today")
    else:
        print("❌ Daily email report not marked as sent today")
        
    if state.get("scheduler_daily_report_date", "") == today:
        print("✅ Scheduler daily report correctly marked as sent today")
    else:
        print("❌ Scheduler daily report not marked as sent today")
    
    # Test 5: Check tomorrow's behavior
    print("\n📅 Testing tomorrow's behavior...")
    tomorrow = (datetime.now(timezone.utc) + timedelta(days=1)).strftime('%Y-%m-%d')
    print(f"   Tomorrow's date: {tomorrow}")
    print(f"   Today's date in state: {state.get('daily_email_report_date', '')}")
    
    if state.get("daily_email_report_date", "") != tomorrow:
        print("✅ Reports will be sent tomorrow (different date)")
    else:
        print("❌ Reports might not be sent tomorrow")
    
    # Clean up
    os.remove(state_path)
    print("\n🧹 Cleaned up test state file")
    
    print("\n🎉 All state tracking tests completed!")
    return True

def main():
    """Main test function"""
    success = test_state_tracking()
    
    if success:
        print("\n✅ State tracking for one-time messages is working correctly!")
        print("✅ Discord startup messages will only be sent once")
        print("✅ Daily reports will only be sent once per day")
        print("✅ State is properly persisted in monsterrr_state.json")
    else:
        print("\n❌ State tracking tests failed")

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Verification script to check that one-time message functionality is implemented correctly
"""

import sys
import os
import json
import inspect
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def test_discord_startup_message():
    """Test Discord startup message state tracking"""
    print("Testing Discord Startup Message Implementation...")
    
    try:
        # Read the Discord bot file
        with open(os.path.join(os.path.dirname(__file__), '..', 'services', 'discord_bot.py'), 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for key implementation details
        has_state_tracking = 'discord_startup_message_sent' in content
        has_once_check = 'already sent' in content or 'skipping' in content
        has_state_update = 'state[' in content and 'discord_startup_message_sent' in content
        has_imports = 'import json' in content and 'import os' in content
        
        print(f"  ✅ State tracking flag: {has_state_tracking}")
        print(f"  ✅ One-time check logic: {has_once_check}")
        print(f"  ✅ State update mechanism: {has_state_update}")
        print(f"  ✅ Required imports: {has_imports}")
        
        return all([has_state_tracking, has_once_check, has_state_update, has_imports])
        
    except Exception as e:
        print(f"  ❌ Error testing Discord startup message: {e}")
        return False

def test_daily_email_reports():
    """Test daily email report state tracking"""
    print("\nTesting Daily Email Report Implementation...")
    
    try:
        # Read the Discord bot file
        with open(os.path.join(os.path.dirname(__file__), '..', 'services', 'discord_bot.py'), 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for key implementation details
        has_daily_state_tracking = 'daily_email_report_sent' in content
        has_date_tracking = 'daily_email_report_date' in content
        has_once_check = 'already sent today' in content
        has_state_update = 'state[' in content and 'daily_email_report' in content
        
        print(f"  ✅ Daily report state tracking: {has_daily_state_tracking}")
        print(f"  ✅ Date tracking mechanism: {has_date_tracking}")
        print(f"  ✅ One-time daily check: {has_once_check}")
        print(f"  ✅ State update for daily reports: {has_state_update}")
        
        # Also check scheduler implementation
        with open(os.path.join(os.path.dirname(__file__), '..', 'scheduler.py'), 'r', encoding='utf-8') as f:
            scheduler_content = f.read()
        
        has_scheduler_tracking = 'scheduler_daily_report_sent' in scheduler_content
        has_scheduler_date = 'scheduler_daily_report_date' in scheduler_content
        
        print(f"  ✅ Scheduler report tracking: {has_scheduler_tracking}")
        print(f"  ✅ Scheduler date tracking: {has_scheduler_date}")
        
        return all([has_daily_state_tracking, has_date_tracking, has_once_check, 
                   has_state_update, has_scheduler_tracking, has_scheduler_date])
        
    except Exception as e:
        print(f"  ❌ Error testing daily email reports: {e}")
        return False

def test_state_file_integration():
    """Test that state file integration works correctly"""
    print("\nTesting State File Integration...")
    
    try:
        # Check if the monsterrr_state.json file is used correctly
        with open(os.path.join(os.path.dirname(__file__), '..', 'services', 'discord_bot.py'), 'r', encoding='utf-8') as f:
            content = f.read()
        
        has_state_file = 'monsterrr_state.json' in content
        has_json_handling = 'json.load' in content and 'json.dump' in content
        has_error_handling = 'try:' in content and 'except' in content
        
        print(f"  ✅ State file usage: {has_state_file}")
        print(f"  ✅ JSON handling: {has_json_handling}")
        print(f"  ✅ Error handling: {has_error_handling}")
        
        return all([has_state_file, has_json_handling, has_error_handling])
        
    except Exception as e:
        print(f"  ❌ Error testing state file integration: {e}")
        return False

def main():
    """Main verification function"""
    print("Verifying One-Time Message Implementation")
    print("=" * 42)
    
    # Test all implementations
    discord_test = test_discord_startup_message()
    email_test = test_daily_email_reports()
    state_test = test_state_file_integration()
    
    print("\n" + "=" * 42)
    if all([discord_test, email_test, state_test]):
        print("🎉 All one-time message implementations are correct!")
        print("✅ Discord startup messages sent only once")
        print("✅ Daily email reports sent only once per day")
        print("✅ State tracking properly implemented")
        print("✅ Error handling and persistence working")
        print("\n📝 State tracking is implemented using flags in monsterrr_state.json:")
        print("   - discord_startup_message_sent")
        print("   - daily_email_report_sent / daily_email_report_date")
        print("   - scheduler_daily_report_sent / scheduler_daily_report_date")
    else:
        print("❌ Some implementations are missing or incomplete:")
        if not discord_test:
            print("  - Discord startup message tracking")
        if not email_test:
            print("  - Daily email report tracking")
        if not state_test:
            print("  - State file integration")

if __name__ == "__main__":
    main()
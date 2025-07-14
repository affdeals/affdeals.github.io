#!/usr/bin/env python3
"""
Time Configuration Update Utility
Helper script to update the time limit in time.json
"""

import json
import sys
import os
import re


def validate_time_format(time_str):
    """Validate time format HH:MM"""
    pattern = r'^([0-1][0-9]|2[0-3]):([0-5][0-9])$'
    return re.match(pattern, time_str) is not None


def update_time_config(new_time, config_file="time.json"):
    """Update time configuration in time.json"""
    
    if not validate_time_format(new_time):
        print(f"❌ Invalid time format: {new_time}")
        print("   Please use HH:MM format (e.g., 05:30)")
        return False
    
    try:
        # Create new configuration
        config = [{"time": new_time}]
        
        # Write to file
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Successfully updated {config_file}")
        print(f"⏱️  New time limit: {new_time}")
        
        # Parse and show in different formats
        hours, minutes = map(int, new_time.split(':'))
        total_minutes = hours * 60 + minutes
        total_seconds = total_minutes * 60
        
        print(f"📊 Time breakdown:")
        print(f"   Hours: {hours}")
        print(f"   Minutes: {minutes}")
        print(f"   Total minutes: {total_minutes}")
        print(f"   Total seconds: {total_seconds}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error updating configuration: {e}")
        return False


def show_current_config(config_file="time.json"):
    """Show current time configuration"""
    try:
        if not os.path.exists(config_file):
            print(f"⚠️  {config_file} not found")
            return False
        
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        if not isinstance(config, list) or len(config) == 0:
            print(f"⚠️  Invalid configuration format in {config_file}")
            return False
        
        current_time = config[0].get("time", "05:00")
        print(f"⏱️  Current time limit: {current_time}")
        
        # Parse and show breakdown
        hours, minutes = map(int, current_time.split(':'))
        total_minutes = hours * 60 + minutes
        total_seconds = total_minutes * 60
        
        print(f"📊 Time breakdown:")
        print(f"   Hours: {hours}")
        print(f"   Minutes: {minutes}")
        print(f"   Total minutes: {total_minutes}")
        print(f"   Total seconds: {total_seconds}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error reading configuration: {e}")
        return False


def main():
    """Main function for time configuration utility"""
    print("=== Time Configuration Update Utility ===")
    
    if len(sys.argv) == 1:
        print("\n📋 Usage:")
        print("  python update_time_config.py show              - Show current configuration")
        print("  python update_time_config.py set HH:MM         - Set new time limit")
        print("  python update_time_config.py help              - Show this help")
        print("\n📝 Examples:")
        print("  python update_time_config.py set 05:30         - Set 5 hours 30 minutes")
        print("  python update_time_config.py set 02:00         - Set 2 hours")
        print("  python update_time_config.py set 08:45         - Set 8 hours 45 minutes")
        return
    
    command = sys.argv[1].lower()
    
    if command == "show":
        show_current_config()
    
    elif command == "set":
        if len(sys.argv) < 3:
            print("❌ Please provide time in HH:MM format")
            print("   Example: python update_time_config.py set 05:30")
            return
        
        new_time = sys.argv[2]
        update_time_config(new_time)
    
    elif command == "help":
        print("\n📋 Time Configuration Help:")
        print("   The time.json file controls how long the GitHub Actions workflow runs.")
        print("   Format: HH:MM where HH is hours (00-23) and MM is minutes (00-59)")
        print("")
        print("   Examples:")
        print("   - 05:00 = 5 hours")
        print("   - 02:30 = 2 hours 30 minutes")
        print("   - 08:45 = 8 hours 45 minutes")
        print("   - 01:15 = 1 hour 15 minutes")
        print("")
        print("   The workflow will:")
        print("   1. Run for the specified time")
        print("   2. Save progress every product processed")
        print("   3. Start graceful shutdown 5 minutes before limit")
        print("   4. Commit and push all completed work")
        print("   5. Exit successfully")
    
    else:
        print(f"❌ Unknown command: {command}")
        print("   Use 'python update_time_config.py help' for usage information")


if __name__ == "__main__":
    main()
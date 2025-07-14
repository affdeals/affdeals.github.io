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


def update_time_config(new_time, new_grace=None, config_file="time.json"):
    """Update time configuration in time.json"""
    
    if not validate_time_format(new_time):
        print(f"❌ Invalid time format: {new_time}")
        print("   Please use HH:MM format (e.g., 05:30)")
        return False
    
    if new_grace and not validate_time_format(new_grace):
        print(f"❌ Invalid grace period format: {new_grace}")
        print("   Please use HH:MM format (e.g., 00:05)")
        return False
    
    try:
        # Load existing configuration if it exists
        existing_config = {}
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                    if isinstance(config_data, list) and len(config_data) > 0:
                        existing_config = config_data[0]
            except:
                pass
        
        # Create new configuration
        config_obj = {"time": new_time}
        
        # Use provided grace period or keep existing one or use default
        if new_grace:
            config_obj["grace"] = new_grace
        elif "grace" in existing_config:
            config_obj["grace"] = existing_config["grace"]
        else:
            config_obj["grace"] = "00:05"  # Default 5 minutes
        
        config = [config_obj]
        
        # Write to file
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Successfully updated {config_file}")
        print(f"⏱️  New time limit: {config_obj['time']}")
        print(f"⏱️  Grace period: {config_obj['grace']}")
        
        # Parse and show in different formats
        time_hours, time_minutes = map(int, config_obj['time'].split(':'))
        grace_hours, grace_minutes = map(int, config_obj['grace'].split(':'))
        
        time_total_seconds = (time_hours * 3600) + (time_minutes * 60)
        grace_total_seconds = (grace_hours * 3600) + (grace_minutes * 60)
        
        print(f"📊 Time breakdown:")
        print(f"   Time limit: {time_hours}h {time_minutes}m ({time_total_seconds} seconds)")
        print(f"   Grace period: {grace_hours}h {grace_minutes}m ({grace_total_seconds} seconds)")
        print(f"   Graceful shutdown starts at: {time_total_seconds - grace_total_seconds} seconds")
        
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
        current_grace = config[0].get("grace", "00:05")
        
        print(f"⏱️  Current time limit: {current_time}")
        print(f"⏱️  Current grace period: {current_grace}")
        
        # Parse and show breakdown
        time_hours, time_minutes = map(int, current_time.split(':'))
        grace_hours, grace_minutes = map(int, current_grace.split(':'))
        
        time_total_seconds = (time_hours * 3600) + (time_minutes * 60)
        grace_total_seconds = (grace_hours * 3600) + (grace_minutes * 60)
        
        print(f"📊 Time breakdown:")
        print(f"   Time limit: {time_hours}h {time_minutes}m ({time_total_seconds} seconds)")
        print(f"   Grace period: {grace_hours}h {grace_minutes}m ({grace_total_seconds} seconds)")
        print(f"   Graceful shutdown starts at: {time_total_seconds - grace_total_seconds} seconds")
        
        return True
        
    except Exception as e:
        print(f"❌ Error reading configuration: {e}")
        return False


def main():
    """Main function for time configuration utility"""
    print("=== Time Configuration Update Utility ===")
    
    if len(sys.argv) == 1:
        print("\n📋 Usage:")
        print("  python update_time_config.py show                    - Show current configuration")
        print("  python update_time_config.py set HH:MM              - Set new time limit (keep existing grace)")
        print("  python update_time_config.py set HH:MM HH:MM        - Set time limit and grace period")
        print("  python update_time_config.py help                   - Show this help")
        print("\n📝 Examples:")
        print("  python update_time_config.py set 05:30              - Set 5h 30m time limit")
        print("  python update_time_config.py set 02:00 00:10        - Set 2h time limit, 10m grace")
        print("  python update_time_config.py set 08:45 00:15        - Set 8h 45m time limit, 15m grace")
        return
    
    command = sys.argv[1].lower()
    
    if command == "show":
        show_current_config()
    
    elif command == "set":
        if len(sys.argv) < 3:
            print("❌ Please provide time in HH:MM format")
            print("   Example: python update_time_config.py set 05:30")
            print("   Example: python update_time_config.py set 05:30 00:10")
            return
        
        new_time = sys.argv[2]
        new_grace = sys.argv[3] if len(sys.argv) > 3 else None
        update_time_config(new_time, new_grace)
    
    elif command == "help":
        print("\n📋 Time Configuration Help:")
        print("   The time.json file controls how long the GitHub Actions workflow runs.")
        print("   Format: HH:MM where HH is hours (00-23) and MM is minutes (00-59)")
        print("")
        print("   Configuration structure:")
        print("   {")
        print('     "time": "05:00",    # Total time limit')
        print('     "grace": "00:05"    # Grace period for graceful shutdown')
        print("   }")
        print("")
        print("   Examples:")
        print("   - time: 05:00, grace: 00:05 = 5h limit, shutdown starts at 4h 55m")
        print("   - time: 02:30, grace: 00:10 = 2h 30m limit, shutdown starts at 2h 20m")
        print("   - time: 08:45, grace: 00:15 = 8h 45m limit, shutdown starts at 8h 30m")
        print("")
        print("   The workflow will:")
        print("   1. Run for the specified time limit")
        print("   2. Save progress every product processed")
        print("   3. Start graceful shutdown when grace period time remains")
        print("   4. Commit and push all completed work")
        print("   5. Exit successfully")
    
    else:
        print(f"❌ Unknown command: {command}")
        print("   Use 'python update_time_config.py help' for usage information")


if __name__ == "__main__":
    main()
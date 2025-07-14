#!/usr/bin/env python3
"""
Time Management Utility for GitHub Actions Workflow
Handles time-based workflow control with graceful shutdown
"""

import json
import time
import datetime
import os
import sys
from typing import Dict, Tuple, Optional


class TimeManager:
    """Manages time-based workflow execution with graceful shutdown"""
    
    def __init__(self, time_config_file: str = "time.json"):
        self.time_config_file = time_config_file
        self.start_time = time.time()
        self.time_limit_seconds = 0
        self.grace_period_seconds = 0  # Will be loaded from time.json
        self.shutdown_requested = False
        
        # Load time configuration
        self.load_time_config()
        
        # Set up signal handlers for graceful shutdown
        self._setup_signal_handlers()
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        import signal
        
        def signal_handler(signum, frame):
            print(f"\nReceived signal {signum}. Requesting graceful shutdown...")
            self.shutdown_requested = True
        
        # Handle SIGTERM (sent by GitHub Actions timeout)
        signal.signal(signal.SIGTERM, signal_handler)
        # Handle SIGINT (Ctrl+C)
        signal.signal(signal.SIGINT, signal_handler)
    
    def load_time_config(self) -> bool:
        """Load time configuration from time.json"""
        try:
            if not os.path.exists(self.time_config_file):
                print(f"Warning: {self.time_config_file} not found. Using defaults.")
                self.time_limit_seconds = self._parse_time_string("05:00")  # 5 hours default
                self.grace_period_seconds = self._parse_time_string("00:05")  # 5 minutes default
                return False
            
            with open(self.time_config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            if not isinstance(config, list) or len(config) == 0:
                print(f"Warning: Invalid format in {self.time_config_file}. Using defaults.")
                self.time_limit_seconds = self._parse_time_string("05:00")
                self.grace_period_seconds = self._parse_time_string("00:05")
                return False
            
            # Load time limit
            time_str = config[0].get("time", "05:00")
            self.time_limit_seconds = self._parse_time_string(time_str)
            
            # Load grace period
            grace_str = config[0].get("grace", "00:05")
            self.grace_period_seconds = self._parse_time_string(grace_str)
            
            # Display loaded configuration
            time_hours, time_minutes = divmod(self.time_limit_seconds, 3600)
            time_minutes = time_minutes // 60
            grace_hours, grace_minutes = divmod(self.grace_period_seconds, 3600)
            grace_minutes = grace_minutes // 60
            
            print(f"✅ Time limit loaded: {time_hours}h {time_minutes}m ({self.time_limit_seconds} seconds)")
            print(f"✅ Grace period loaded: {grace_hours}h {grace_minutes}m ({self.grace_period_seconds} seconds)")
            return True
            
        except Exception as e:
            print(f"Error loading time config: {e}")
            print("Using defaults.")
            self.time_limit_seconds = self._parse_time_string("05:00")
            self.grace_period_seconds = self._parse_time_string("00:05")
            return False
    
    def _parse_time_string(self, time_str: str) -> int:
        """Parse time string in HH:MM format to seconds"""
        try:
            hours, minutes = map(int, time_str.split(':'))
            return (hours * 3600) + (minutes * 60)
        except Exception as e:
            print(f"Error parsing time string '{time_str}': {e}")
            return 0
    
    def get_elapsed_time(self) -> float:
        """Get elapsed time since workflow start in seconds"""
        return time.time() - self.start_time
    
    def get_remaining_time(self) -> float:
        """Get remaining time in seconds"""
        return max(0, self.time_limit_seconds - self.get_elapsed_time())
    
    def get_time_status(self) -> Dict:
        """Get comprehensive time status"""
        elapsed = self.get_elapsed_time()
        remaining = self.get_remaining_time()
        
        return {
            "elapsed_seconds": elapsed,
            "remaining_seconds": remaining,
            "elapsed_formatted": self.format_time(elapsed),
            "remaining_formatted": self.format_time(remaining),
            "time_limit_seconds": self.time_limit_seconds,
            "time_limit_formatted": self.format_time(self.time_limit_seconds),
            "progress_percentage": (elapsed / self.time_limit_seconds) * 100,
            "should_continue": remaining > self.grace_period_seconds and not self.shutdown_requested
        }
    
    def should_continue_processing(self) -> bool:
        """Check if processing should continue"""
        if self.shutdown_requested:
            return False
        
        remaining = self.get_remaining_time()
        return remaining > self.grace_period_seconds
    
    def should_start_graceful_shutdown(self) -> bool:
        """Check if graceful shutdown should start"""
        remaining = self.get_remaining_time()
        return remaining <= self.grace_period_seconds or self.shutdown_requested
    
    def format_time(self, seconds: float) -> str:
        """Format time in seconds to human-readable format"""
        hours, remainder = divmod(int(seconds), 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    
    def log_time_status(self, current_item: str = "", total_items: int = 0, processed_items: int = 0):
        """Log current time status"""
        status = self.get_time_status()
        
        print(f"\n⏱️  Time Status:")
        print(f"   Elapsed: {status['elapsed_formatted']}")
        print(f"   Remaining: {status['remaining_formatted']}")
        print(f"   Progress: {status['progress_percentage']:.1f}%")
        
        if current_item:
            print(f"   Current: {current_item}")
        
        if total_items > 0:
            print(f"   Items: {processed_items}/{total_items} ({(processed_items/total_items)*100:.1f}%)")
        
        if self.should_start_graceful_shutdown():
            print(f"   🚨 Graceful shutdown will start soon!")
    
    def wait_with_timeout_check(self, wait_seconds: float) -> bool:
        """Wait for specified seconds while checking timeout. Returns True if wait completed, False if timeout"""
        start_wait = time.time()
        while time.time() - start_wait < wait_seconds:
            if not self.should_continue_processing():
                return False
            time.sleep(0.1)  # Check every 100ms
        return True
    
    def create_progress_checkpoint(self, data: Dict, checkpoint_file: str = "progress_checkpoint.json"):
        """Create a progress checkpoint file"""
        try:
            checkpoint = {
                "timestamp": datetime.datetime.now().isoformat(),
                "time_status": self.get_time_status(),
                "data": data
            }
            
            with open(checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump(checkpoint, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Progress checkpoint created: {checkpoint_file}")
            return True
            
        except Exception as e:
            print(f"Error creating progress checkpoint: {e}")
            return False
    
    def log_final_summary(self, stats: Dict):
        """Log final execution summary"""
        status = self.get_time_status()
        
        print(f"\n{'='*60}")
        print(f"📊 WORKFLOW EXECUTION SUMMARY")
        print(f"{'='*60}")
        print(f"⏱️  Time Limit: {status['time_limit_formatted']}")
        print(f"⏱️  Time Elapsed: {status['elapsed_formatted']}")
        print(f"⏱️  Time Remaining: {status['remaining_formatted']}")
        print(f"📈 Progress: {status['progress_percentage']:.1f}%")
        
        if stats.get("total_items"):
            print(f"📦 Items Processed: {stats.get('processed_items', 0)}/{stats.get('total_items', 0)}")
        
        if stats.get("new_items"):
            print(f"✅ New Items Added: {stats.get('new_items', 0)}")
        
        if stats.get("updated_items"):
            print(f"🔄 Items Updated: {stats.get('updated_items', 0)}")
        
        if stats.get("skipped_items"):
            print(f"⚠️  Items Skipped: {stats.get('skipped_items', 0)}")
        
        print(f"🔄 Graceful Shutdown: {'Yes' if self.should_start_graceful_shutdown() else 'No'}")
        print(f"💾 Changes Saved: {'Yes' if stats.get('changes_saved', False) else 'No'}")
        print(f"{'='*60}")


def main():
    """Test the TimeManager functionality"""
    print("Testing TimeManager...")
    
    tm = TimeManager()
    
    # Test basic functionality
    print(f"Time limit: {tm.time_limit_seconds} seconds")
    print(f"Should continue: {tm.should_continue_processing()}")
    
    # Test time status
    status = tm.get_time_status()
    print(f"Time status: {status}")
    
    # Test logging
    tm.log_time_status("Test Product", 100, 1)
    
    # Test final summary
    stats = {
        "total_items": 100,
        "processed_items": 25,
        "new_items": 20,
        "updated_items": 5,
        "skipped_items": 75,
        "changes_saved": True
    }
    tm.log_final_summary(stats)


if __name__ == "__main__":
    main()
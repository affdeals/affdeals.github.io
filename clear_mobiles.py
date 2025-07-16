#!/usr/bin/env python3
"""
Clear Mobiles JSON File
Clears the content of mobiles.json file without deleting it
"""

import json
import os


def clear_mobiles_json(json_file_path="mobiles.json"):
    """
    Clear the content of mobiles.json file by resetting it to initial structure
    
    Args:
        json_file_path (str): Path to the mobiles.json file
    """
    try:
        # Check if file exists
        if not os.path.exists(json_file_path):
            print(f"File {json_file_path} does not exist. Creating new file...")
        
        # Initial empty structure
        initial_data = {
            "total_mobile_phones": 0,
            "products": []
        }
        
        # Write the cleared structure to file
        with open(json_file_path, "w", encoding="utf-8") as f:
            json.dump(initial_data, f, indent=2, ensure_ascii=False)
        
        print(f"Successfully cleared {json_file_path}")
        print("File now contains:")
        print(f"- total_mobile_phones: 0")
        print(f"- products: [] (empty array)")
        
        return True
        
    except Exception as e:
        print(f"Error clearing {json_file_path}: {e}")
        return False


def main():
    """Main function to clear mobiles.json"""
    print("Clearing mobiles.json file...")
    
    # Clear the mobiles.json file
    success = clear_mobiles_json("mobiles.json")
    
    if success:
        print("\n✅ mobiles.json has been successfully cleared!")
    else:
        print("\n❌ Failed to clear mobiles.json")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
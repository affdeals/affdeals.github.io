#!/usr/bin/env python3
"""
Product Count Matcher
Compares the number of products in mobiles.json and update_mobiles.json
"""

import json
import os
import sys

def load_json_file(filepath):
    """Load JSON file and return the data"""
    try:
        with open(filepath, 'r', encoding='utf-8') as file:
            return json.load(file)
    except FileNotFoundError:
        print(f"Error: File '{filepath}' not found.")
        return None
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON format in '{filepath}': {e}")
        return None
    except Exception as e:
        print(f"Error loading '{filepath}': {e}")
        return None

def count_products_in_mobiles(data):
    """Count products in mobiles.json"""
    if not data:
        return 0
    
    # Check if there's a 'products' key
    if 'products' in data:
        return len(data['products'])
    
    # Check if there's a 'total_mobile_phones' key for cross-reference
    if 'total_mobile_phones' in data:
        print(f"Note: mobiles.json also contains 'total_mobile_phones': {data['total_mobile_phones']}")
    
    return 0

def count_products_in_update_mobiles(data):
    """Count products in update_mobiles.json"""
    if not data:
        return 0
    
    # Check if there's a 'products' key
    if 'products' in data:
        return len(data['products'])
    
    return 0

def main():
    """Main function to compare product counts"""
    print("Product Count Matcher")
    print("=" * 50)
    
    # File paths
    mobiles_file = "mobiles.json"
    update_mobiles_file = "update_mobiles.json"
    
    # Load JSON files
    print(f"Loading {mobiles_file}...")
    mobiles_data = load_json_file(mobiles_file)
    
    print(f"Loading {update_mobiles_file}...")
    update_mobiles_data = load_json_file(update_mobiles_file)
    
    # Check if both files loaded successfully
    if mobiles_data is None or update_mobiles_data is None:
        print("Failed to load one or both JSON files. Exiting.")
        sys.exit(1)
    
    # Count products in both files
    mobiles_count = count_products_in_mobiles(mobiles_data)
    update_mobiles_count = count_products_in_update_mobiles(update_mobiles_data)
    
    # Display results
    print(f"\nProduct Count Results:")
    print(f"- {mobiles_file}: {mobiles_count} products")
    print(f"- {update_mobiles_file}: {update_mobiles_count} products")
    
    # Compare counts
    print(f"\nComparison Result:")
    if mobiles_count == update_mobiles_count:
        print(f"✅ MATCH: Both files contain the same number of products ({mobiles_count})")
        
        # Additional check for total_mobile_phones field if it exists
        if 'total_mobile_phones' in mobiles_data:
            total_mobile_phones = mobiles_data['total_mobile_phones']
            if total_mobile_phones == mobiles_count:
                print(f"✅ VERIFICATION: The 'total_mobile_phones' field ({total_mobile_phones}) matches the actual product count")
            else:
                print(f"⚠️  WARNING: The 'total_mobile_phones' field ({total_mobile_phones}) doesn't match the actual product count ({mobiles_count})")
        
        return True
    else:
        print(f"❌ MISMATCH: Product counts don't match!")
        print(f"   Difference: {abs(mobiles_count - update_mobiles_count)} products")
        
        if mobiles_count > update_mobiles_count:
            print(f"   {mobiles_file} has {mobiles_count - update_mobiles_count} more products")
        else:
            print(f"   {update_mobiles_file} has {update_mobiles_count - mobiles_count} more products")
        
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
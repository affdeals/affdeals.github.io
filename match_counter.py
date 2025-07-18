#!/usr/bin/env python3
"""
Product Counter
Counts the number of products in mobiles.json and update_mobiles.json
"""

import json
import os

def load_json_file(filepath):
    """Load JSON file and return the data"""
    try:
        with open(filepath, 'r', encoding='utf-8') as file:
            data = json.load(file)
            return data if data else {}
    except (FileNotFoundError, json.JSONDecodeError, Exception):
        return {}

def count_products(data):
    """Count products in JSON data"""
    if not data or 'products' not in data:
        return 0
    
    products = data['products']
    if not products:
        return 0
    
    return len(products)

def count_listed_products(data):
    """Count products with listed: 'yes' in JSON data"""
    if not data or 'products' not in data:
        return 0
    
    products = data['products']
    if not products:
        return 0
    
    listed_count = 0
    for product in products:
        if product.get('listed') == 'yes':
            listed_count += 1
    
    return listed_count

def main():
    """Main function to count products"""
    print("Product Counter")
    print("=" * 30)
    
    # File paths
    mobiles_file = "mobiles.json"
    update_mobiles_file = "update_mobiles.json"
    
    # Load JSON files
    mobiles_data = load_json_file(mobiles_file)
    update_mobiles_data = load_json_file(update_mobiles_file)
    
    # Count products in both files
    mobiles_count = count_products(mobiles_data)
    update_mobiles_count = count_products(update_mobiles_data)
    
    # Count listed products in update_mobiles.json
    update_mobiles_listed_count = count_listed_products(update_mobiles_data)
    
    # Display results
    print(f"\nProduct Count Results:")
    print(f"- {mobiles_file}: {mobiles_count}")
    print(f"- {update_mobiles_file}: {update_mobiles_count}")
    print(f"- {update_mobiles_file} (listed): {update_mobiles_listed_count}")
    print(f"- {update_mobiles_file} (unlisted): {update_mobiles_count - update_mobiles_listed_count}")

if __name__ == "__main__":
    main()
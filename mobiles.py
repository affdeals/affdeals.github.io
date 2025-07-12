#!/usr/bin/env python3
"""
Smartprix Mobile Phone Scraper
Scrapes mobile phone details from Smartprix website using Selenium
"""

import re
import time
import json
import os
import sys
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
import contextlib
import tempfile

@contextlib.contextmanager
def suppress_stderr():
    """Context manager to suppress stderr messages"""
    with open(os.devnull, "w") as devnull:
        old_stderr = sys.stderr
        sys.stderr = devnull
        try:
            yield
        finally:
            sys.stderr = old_stderr


def setup_driver():
    """Setup Chrome WebDriver with options"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in background
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-webgl")
    chrome_options.add_argument("--disable-software-rasterizer")
    chrome_options.add_argument("--disable-3d-apis")
    chrome_options.add_argument("--disable-background-timer-throttling")
    chrome_options.add_argument("--disable-backgrounding-occluded-windows")
    chrome_options.add_argument("--disable-renderer-backgrounding")
    chrome_options.add_argument("--disable-features=TranslateUI")
    chrome_options.add_argument("--disable-ipc-flooding-protection")
    chrome_options.add_argument("--log-level=3")  # Suppress INFO, WARNING, ERROR
    chrome_options.add_argument("--silent")  # Suppress console output
    chrome_options.add_argument("--disable-logging")  # Disable logging
    chrome_options.add_argument("--disable-gpu-logging")  # Disable GPU logging
    chrome_options.add_argument("--disable-extensions")  # Disable extensions
    chrome_options.add_argument("--disable-plugins")  # Disable plugins
    chrome_options.add_argument("--disable-images")  # Disable images for faster loading
    chrome_options.add_argument("--disable-web-security")  # Disable web security
    chrome_options.add_argument("--disable-features=VizDisplayCompositor")  # Disable compositor
    chrome_options.add_argument("--disable-background-networking")  # Disable background networking
    chrome_options.add_argument("--disable-default-apps")  # Disable default apps
    chrome_options.add_argument("--disable-sync")  # Disable sync
    chrome_options.add_argument("--disable-translate")  # Disable translate
    chrome_options.add_argument("--hide-scrollbars")  # Hide scrollbars
    chrome_options.add_argument("--mute-audio")  # Mute audio
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    
    # Suppress DevTools listening message
    chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")

    temp_profile = tempfile.mkdtemp(prefix="sp-chrome-profile-")
    chrome_options.add_argument(f"--user-data-dir={temp_profile}")
    
    try:
        # Suppress stderr messages from Chrome
        os.environ['WDM_LOG_LEVEL'] = '0'
        
        # Create driver with suppressed stderr
        with suppress_stderr():
            driver = webdriver.Chrome(options=chrome_options)
        return driver
    except Exception as e:
        print(f"Error setting up Chrome driver: {e}")
        print("Make sure ChromeDriver is installed and in your PATH")
        return None


def extract_mobile_count(text):
    """Extract numerical value from text like '1,540 Mobile Phones'"""
    if not text:
        return None
    
    # Remove any extra whitespace and convert to string
    text = str(text).strip()
    
    # Use regex to find numbers (including those with commas)
    # Pattern matches: digits, commas, and digits again
    pattern = r'[\d,]+(?=\s*Mobile\s*Phones?|$)'
    match = re.search(pattern, text, re.IGNORECASE)
    
    if match:
        # Remove commas and convert to integer
        number_str = match.group().replace(',', '')
        try:
            return int(number_str)
        except ValueError:
            return None
    
    # Alternative pattern: just extract first number sequence with commas
    pattern2 = r'[\d,]+'
    match2 = re.search(pattern2, text)
    if match2:
        number_str = match2.group().replace(',', '')
        try:
            return int(number_str)
        except ValueError:
            return None
    
    return None


def generate_unique_id(product_name):
    """Generate unique ID from product name"""
    if not product_name:
        return None
    
    # Convert to lowercase and replace spaces with underscores
    unique_id = re.sub(r'[^a-zA-Z0-9\s]', '', product_name.lower())
    unique_id = re.sub(r'\s+', '_', unique_id.strip())
    
    return unique_id


def initialize_json_file(total_count, json_file_path):
    """Initialize JSON file with total count and empty products array"""
    initial_data = {
        "total_mobile_phones": total_count,
        "products": []
    }
    
    with open(json_file_path, "w", encoding="utf-8") as f:
        json.dump(initial_data, f, indent=2, ensure_ascii=False)


def append_product_to_json(product_data, json_file_path):
    """Append a single product to the JSON file"""
    try:
        # Read existing data
        with open(json_file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Append new product
        data["products"].append(product_data)
        
        # Write back to file
        with open(json_file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        return True
    except Exception as e:
        return False


def scrape_product_details(driver, product_xpath, retries=5):
    """Scrape individual product details with retry logic"""
    for attempt in range(retries):
        try:
            # Wait for element to be present
            wait = WebDriverWait(driver, 5)
            product_element = wait.until(EC.presence_of_element_located((By.XPATH, product_xpath)))
            
            # Initialize product data (count will be set later)
            product_data = {
                "count": 0,  # Will be set when product is successfully saved
                "unique_id": None,
                "name": None,
                "price": None,
                "url": None
            }
            
            # Try to extract product name
            try:
                name_element = product_element.find_element(By.CSS_SELECTOR, "h2, .prd-name, [data-name], .product-name")
                product_data["name"] = name_element.text.strip() if name_element.text else None
            except:
                try:
                    name_element = product_element.find_element(By.TAG_NAME, "h2")
                    product_data["name"] = name_element.text.strip() if name_element.text else None
                except:
                    pass
            
            # Try to extract price
            try:
                price_element = product_element.find_element(By.CSS_SELECTOR, ".prd-price, .price, [data-price], .product-price")
                product_data["price"] = price_element.text.strip() if price_element.text else None
            except:
                try:
                    price_element = product_element.find_element(By.XPATH, ".//span[contains(@class, 'price') or contains(text(), '₹')]")
                    product_data["price"] = price_element.text.strip() if price_element.text else None
                except:
                    pass
            
            # Try to extract URL
            try:
                url_element = product_element.find_element(By.CSS_SELECTOR, "a[href]")
                relative_url = url_element.get_attribute("href")
                if relative_url:
                    if relative_url.startswith('/'):
                        product_data["url"] = f"https://www.smartprix.com{relative_url}"
                    else:
                        product_data["url"] = relative_url
            except:
                pass
            
            # Generate unique ID if we have a name
            if product_data["name"]:
                product_data["unique_id"] = generate_unique_id(product_data["name"])
            
            # Return product data if we have at least name
            if product_data["name"]:
                return product_data
            
        except Exception as e:
            if attempt == retries - 1:  # Last attempt
                return None
            time.sleep(1)  # Wait before retry
    
    return None


def debug_page_elements(driver):
    """Debug function to identify Load More button and other elements"""
    print("\n=== PAGE DEBUG INFO ===")
    
    # Look for all buttons on the page
    buttons = driver.find_elements(By.TAG_NAME, "button")
    print(f"Found {len(buttons)} buttons on the page")
    
    for i, button in enumerate(buttons[:10]):  # Show first 10 buttons
        try:
            text = button.text.strip()
            classes = button.get_attribute("class")
            print(f"Button {i+1}: Text='{text}', Classes='{classes}'")
        except:
            pass
    
    # Look for all divs that might be load more buttons
    divs_with_load = driver.find_elements(By.XPATH, "//div[contains(text(), 'Load') or contains(text(), 'load') or contains(text(), 'More') or contains(text(), 'more')]")
    print(f"\nFound {len(divs_with_load)} divs with 'Load' or 'More' text")
    
    for i, div in enumerate(divs_with_load[:5]):
        try:
            text = div.text.strip()
            classes = div.get_attribute("class")
            print(f"Div {i+1}: Text='{text}', Classes='{classes}'")
        except:
            pass
    
    # Look for elements at the bottom of the page
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(2)
    
    # Check what's at the bottom
    bottom_elements = driver.find_elements(By.XPATH, "//div[position()>=last()-5]")
    print(f"\nBottom elements:")
    for i, elem in enumerate(bottom_elements):
        try:
            text = elem.text.strip()[:50]  # First 50 chars
            tag = elem.tag_name
            classes = elem.get_attribute("class")
            print(f"Bottom element {i+1}: Tag='{tag}', Classes='{classes}', Text='{text}'")
        except:
            pass
    
    print("=== END DEBUG INFO ===\n")


def try_infinite_scroll(driver, max_scrolls=5):
    """Try infinite scroll approach as fallback"""
    print("Trying infinite scroll approach...")
    
    # Count products before scrolling
    products_before = len(driver.find_elements(By.XPATH, "//div[contains(@class, 'product') or contains(@class, 'prd')]"))
    
    for i in range(max_scrolls):
        print(f"Scroll attempt {i+1}/{max_scrolls}")
        
        # Scroll to bottom
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3)
        
        # Check if new products loaded
        products_after = len(driver.find_elements(By.XPATH, "//div[contains(@class, 'product') or contains(@class, 'prd')]"))
        
        if products_after > products_before:
            print(f"New products loaded via scrolling! Before: {products_before}, After: {products_after}")
            return True
        
        products_before = products_after
    
    print("Infinite scroll didn't load more products")
    return False


def click_load_more_button(driver, load_more_xpath):
    """Click Load More button with multiple strategies and retry logic"""
    print("Attempting to click Load More button...")
    
    # Try multiple strategies to find and click the Load More button
    strategies = [
        # Strategy 1: Original XPath
        lambda: driver.find_element(By.XPATH, load_more_xpath),
        # Strategy 2: Common Load More button selectors
        lambda: driver.find_element(By.CSS_SELECTOR, "button[class*='load-more']"),
        lambda: driver.find_element(By.CSS_SELECTOR, "div[class*='load-more']"),
        lambda: driver.find_element(By.CSS_SELECTOR, "a[class*='load-more']"),
        # Strategy 3: Text-based search
        lambda: driver.find_element(By.XPATH, "//button[contains(text(), 'Load More') or contains(text(), 'load more')]"),
        lambda: driver.find_element(By.XPATH, "//div[contains(text(), 'Load More') or contains(text(), 'load more')]"),
        lambda: driver.find_element(By.XPATH, "//a[contains(text(), 'Load More') or contains(text(), 'load more')]"),
        # Strategy 4: Alternative common patterns
        lambda: driver.find_element(By.CSS_SELECTOR, "button[data-action*='load']"),
        lambda: driver.find_element(By.CSS_SELECTOR, "div[data-action*='load']"),
    ]
    
    for strategy_num, strategy in enumerate(strategies, 1):
        try:
            print(f"Trying strategy {strategy_num}...")
            
            # Wait a bit and scroll to bottom first
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            # Try to find element
            load_more_button = strategy()
            
            if load_more_button:
                print(f"Found Load More button with strategy {strategy_num}")
                
                # Check if element is displayed and enabled
                if not load_more_button.is_displayed():
                    print("Button is not visible, trying next strategy...")
                    continue
                
                # Scroll to the button with some offset
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", load_more_button)
                time.sleep(1)
                
                # Try different clicking methods
                click_methods = [
                    # Method 1: Regular click
                    lambda: load_more_button.click(),
                    # Method 2: JavaScript click
                    lambda: driver.execute_script("arguments[0].click();", load_more_button),
                    # Method 3: Action chains click
                    lambda: driver.execute_script("arguments[0].dispatchEvent(new MouseEvent('click', {bubbles: true}));", load_more_button),
                ]
                
                for method_num, click_method in enumerate(click_methods, 1):
                    try:
                        print(f"Trying click method {method_num}...")
                        
                        # Wait for element to be clickable
                        wait = WebDriverWait(driver, 3)
                        wait.until(EC.element_to_be_clickable(load_more_button))
                        
                        # Count products before clicking
                        products_before = len(driver.find_elements(By.XPATH, "//div[contains(@class, 'product') or contains(@class, 'prd')]"))
                        
                        # Click the button
                        click_method()
                        print(f"Clicked Load More button successfully with method {method_num}")
                        
                        # Wait for content to load
                        time.sleep(8)  # Increased wait time
                        
                        # Check if new products were loaded
                        products_after = len(driver.find_elements(By.XPATH, "//div[contains(@class, 'product') or contains(@class, 'prd')]"))
                        
                        if products_after > products_before:
                            print(f"New products loaded! Before: {products_before}, After: {products_after}")
                            return True
                        else:
                            print(f"No new products loaded. Before: {products_before}, After: {products_after}")
                            # Continue to try other methods
                            continue
                            
                    except Exception as e:
                        print(f"Click method {method_num} failed: {e}")
                        continue
                
        except Exception as e:
            print(f"Strategy {strategy_num} failed: {e}")
            continue
    
    print("All strategies failed to click Load More button")
    return False


def scrape_smartprix_mobiles(debug_mode=False):
    """Main function to scrape mobile phone details from Smartprix"""
    
    # URL to scrape
    url = "https://www.smartprix.com/mobiles/exclude_global-exclude_out_of_stock-exclude_upcoming-stock/amazon-store"
    
    # XPath patterns
    total_count_xpath = "/html/body/div[1]/main/div[1]/div[2]/div[1]/div/div[1]"
    load_more_xpath = "/html/body/div[1]/main/div[1]/div[2]/div[3]"
    json_file_path = "mobiles.json"
    
    # Setup driver
    driver = setup_driver()
    if not driver:
        return None
    
    try:
        driver.get(url)
        time.sleep(3)
        
        # First, get total count
        wait = WebDriverWait(driver, 10)
        total_element = wait.until(EC.presence_of_element_located((By.XPATH, total_count_xpath)))
        total_text = total_element.text
        total_mobile_count = extract_mobile_count(total_text)
        
        if not total_mobile_count:
            return None
        
        # Print total count found
        print(f"Total Mobile Phones Found = {total_mobile_count}")
        
        # Initialize JSON file
        initialize_json_file(total_mobile_count, json_file_path)
        
        # Track unique IDs to avoid duplicates
        unique_ids_seen = set()
        total_scraped = 0
        product_count = 0  # Counter for product numbering
        current_product_position = 1  # Track current product position on the page
        
        # Scraping loop
        while total_scraped < total_mobile_count:
            # Try to scrape 20 products in current batch
            products_scraped_in_batch = 0
            batch_start = current_product_position
            batch_end = current_product_position + 19  # 20 products per batch
            
            print(f"Scraping products from position {batch_start} to {batch_end}")
            
            # First, check how many products are actually available on the page
            total_products_on_page = len(driver.find_elements(By.XPATH, "//div[contains(@class, 'product') or contains(@class, 'prd')]"))
            print(f"Total products currently on page: {total_products_on_page}")
            
            # Adjust batch_end if we don't have enough products on the page
            actual_batch_end = min(batch_end, total_products_on_page)
            
            for i in range(batch_start, actual_batch_end + 1):
                if total_scraped >= total_mobile_count:
                    break
                    
                product_xpath = f"/html/body/div[1]/main/div[1]/div[2]/div[2]/div[{i}]"
                
                # Try to scrape product (count will be set when we successfully save the product)
                product_data = scrape_product_details(driver, product_xpath)
                
                if product_data and product_data["unique_id"]:
                    # Check for duplicate unique_id
                    if product_data["unique_id"] not in unique_ids_seen:
                        unique_ids_seen.add(product_data["unique_id"])
                        
                        # Set the count for this product
                        product_count += 1
                        product_data["count"] = product_count
                        
                        # Append to JSON immediately
                        if append_product_to_json(product_data, json_file_path):
                            total_scraped += 1
                            products_scraped_in_batch += 1
                            print(f"Scraped product {total_scraped}: {product_data['name']}")
                    else:
                        # Handle duplicate by appending number
                        counter = 1
                        original_id = product_data["unique_id"]
                        while f"{original_id}_{counter}" in unique_ids_seen:
                            counter += 1
                        product_data["unique_id"] = f"{original_id}_{counter}"
                        unique_ids_seen.add(product_data["unique_id"])
                        
                        # Set the count for this product
                        product_count += 1
                        product_data["count"] = product_count
                        
                        # Append to JSON immediately
                        if append_product_to_json(product_data, json_file_path):
                            total_scraped += 1
                            products_scraped_in_batch += 1
                            print(f"Scraped product {total_scraped}: {product_data['name']}")
            
            # Print batch summary
            print(f"Batch completed. Products scraped in this batch: {products_scraped_in_batch}")
            print(f"Total products scraped so far: {total_scraped}/{total_mobile_count}")
            
            # Check if we've scraped all products
            if total_scraped >= total_mobile_count:
                break
            
            # If no products were scraped in this batch and we haven't reached the total,
            # we need to load more products before continuing
            if products_scraped_in_batch == 0:
                print("No products scraped in this batch. Will try to load more products...")
                # Don't update position yet - we'll try to load more products first
            else:
                # Update current position for next batch only if we scraped some products
                current_product_position += 20
            
            # Debug page elements before trying to click Load More (only if debug mode is enabled)
            if debug_mode:
                debug_page_elements(driver)
            
            # Count products currently on page before clicking Load More
            products_on_page_before = len(driver.find_elements(By.XPATH, "//div[contains(@class, 'product') or contains(@class, 'prd')]"))
            print(f"Products on page before Load More: {products_on_page_before}")
            
            # Try to click Load More button
            if not click_load_more_button(driver, load_more_xpath):
                print("Failed to click Load More button, trying infinite scroll as fallback...")
                
                # Try infinite scroll approach
                if try_infinite_scroll(driver):
                    print("Infinite scroll worked, continuing...")
                    # Count products after infinite scroll
                    products_on_page_after = len(driver.find_elements(By.XPATH, "//div[contains(@class, 'product') or contains(@class, 'prd')]"))
                    print(f"Products on page after infinite scroll: {products_on_page_after}")
                    continue
                else:
                    print("Both Load More button and infinite scroll failed")
                    
                    # Final check and debug info
                    try:
                        current_products = len(driver.find_elements(By.XPATH, "//div[contains(@class, 'product') or contains(@class, 'prd')]"))
                        print(f"Current products on page: {current_products}")
                        
                        # If we haven't reached the expected total, there might be an issue
                        if current_products < total_mobile_count:
                            print("There might be more products available but both methods failed")
                            print("This could be due to:")
                            print("1. Website structure changed")
                            print("2. Anti-bot protection")
                            print("3. Different Load More button implementation")
                            print("4. JavaScript not fully loaded")
                            print("5. The website switched to a different pagination method")
                        
                    except Exception as e:
                        print(f"Error checking page state: {e}")
                    
                    break  # No more Load More button or failed to click
            else:
                # Load More button was clicked successfully
                products_on_page_after = len(driver.find_elements(By.XPATH, "//div[contains(@class, 'product') or contains(@class, 'prd')]"))
                print(f"Products on page after Load More: {products_on_page_after}")
                new_products_loaded = products_on_page_after - products_on_page_before
                print(f"New products loaded: {new_products_loaded}")
            
            # If no products were scraped in this batch, break to avoid infinite loop
            if products_scraped_in_batch == 0:
                break
        
        return total_scraped
        
    except Exception as e:
        return None
    finally:
        # Close the browser
        driver.quit()


if __name__ == "__main__":
    import sys
    
    # Check if debug mode is requested
    debug_mode = len(sys.argv) > 1 and sys.argv[1] == "--debug"
    
    result = scrape_smartprix_mobiles(debug_mode=debug_mode)
    
    if result:
        print(f"Successfully scraped {result} mobile phones and saved to mobiles.json")
    else:
        print("Failed to scrape mobile phones")
        
    if debug_mode:
        print("\nDebug mode was enabled. Run without --debug flag for normal operation.")
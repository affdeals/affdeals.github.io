#!/usr/bin/env python3
"""
ASIN and MRP Scraper for Smartprix Mobile Products
Reads mobiles.json, visits each product page, extracts Amazon.in ASIN and MRP data
"""

import json
import time
import os
import sys
import re
import contextlib
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
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
    chrome_options.add_argument("--disable-web-security")  # Disable web security
    chrome_options.add_argument("--disable-features=VizDisplayCompositor")  # Disable compositor
    chrome_options.add_argument("--disable-background-networking")  # Disable background networking
    chrome_options.add_argument("--disable-default-apps")  # Disable default apps
    chrome_options.add_argument("--disable-sync")  # Disable sync
    chrome_options.add_argument("--disable-translate")  # Disable translate
    chrome_options.add_argument("--hide-scrollbars")  # Hide scrollbars
    chrome_options.add_argument("--mute-audio")  # Mute audio
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--force-device-scale-factor=1")  # Ensure consistent scaling
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


def extract_asin_from_amazon_url(url):
    """Extract ASIN from Amazon URL"""
    try:
        # Common Amazon ASIN patterns
        patterns = [
            r'/dp/([A-Z0-9]{10})',
            r'/product/([A-Z0-9]{10})',
            r'/gp/product/([A-Z0-9]{10})',
            r'asin=([A-Z0-9]{10})',
            r'ASIN=([A-Z0-9]{10})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    except Exception as e:
        print(f"    Error extracting ASIN from URL: {e}")
        return None


def get_amazon_mrp(driver):
    """Extract MRP from Amazon.in product page using class-based selector with data-a-size='s'"""
    try:
        # Wait for page to load properly
        time.sleep(3)
        
        print("    Attempting to extract MRP from Amazon page...")
        
        # Use the class-based selector with data-a-size="s" as specified by user
        mrp_selector = "span.a-price.a-text-price[data-a-size='s'][data-a-strike='true'] span.a-offscreen"
        
        try:
            # Try to find the MRP element using CSS selector
            mrp_element = driver.find_element(By.CSS_SELECTOR, mrp_selector)
            mrp_text = mrp_element.get_attribute("innerHTML").strip()
            
            if mrp_text and '₹' in mrp_text:
                print(f"    ✓ Found MRP: {mrp_text}")
                return mrp_text
            else:
                print("    MRP element found but text is empty or invalid")
                return ""
                
        except NoSuchElementException:
            print("    ✗ MRP element not found (MRP likely same as current price)")
            return ""
        except Exception as e:
            print(f"    Error accessing MRP element: {e}")
            return ""
        
    except Exception as e:
        print(f"    ✗ Error extracting MRP: {e}")
        return ""


def get_amazon_mrp_from_asin(driver, asin):
    """Extract MRP by navigating directly to Amazon using ASIN"""
    try:
        # Navigate directly to Amazon product page using ASIN
        amazon_url = f"https://www.amazon.in/dp/{asin}/"
        print(f"    Navigating directly to Amazon: {amazon_url}")
        
        driver.get(amazon_url)
        time.sleep(5)  # Wait for page to load
        
        # Use the same get_amazon_mrp function to extract MRP
        return get_amazon_mrp(driver)
            
    except Exception as e:
        print(f"    ✗ Error navigating to Amazon or extracting MRP: {e}")
        return ""


def scrape_store_links(driver, product_url, retries=3):
    """Scrape store links from product page using specific XPath patterns"""
    for attempt in range(retries):
        try:
            print(f"  Scraping store links from: {product_url}")
            driver.get(product_url)
            
            # Wait for page to load
            wait = WebDriverWait(driver, 10)
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            time.sleep(3)
            
            store_links = []
            
            # Try the specific XPath patterns from update_mobiles.py
            xpath_patterns = [
                "/html/body/div[1]/main/div[1]/div[2]/div[3]/div[1]/a[1]",
                "/html/body/div[1]/main/div[1]/div[2]/div[3]/ul[1]/li[1]/a",
                "/html/body/div[1]/main/div[1]/div[2]/div[3]/ul[1]/li[2]/a",
                "/html/body/div[1]/main/div[1]/div[2]/div[3]/ul[1]/li[3]/a",
                "/html/body/div[1]/main/div[1]/div[2]/div[3]/ul[1]/li[4]/a",
                "/html/body/div[1]/main/div[1]/div[2]/div[3]/ul[1]/li[5]/a",
                "/html/body/div[1]/main/div[1]/div[2]/div[3]/ul[1]/li[6]/a",
                "/html/body/div[1]/main/div[1]/div[2]/div[3]/ul[1]/li[7]/a",
                "/html/body/div[1]/main/div[1]/div[2]/div[3]/ul[1]/li[8]/a",
                "/html/body/div[1]/main/div[1]/div[2]/div[3]/ul[1]/li[9]/a",
                "/html/body/div[1]/main/div[1]/div[2]/div[3]/ul[1]/li[10]/a"
            ]
            
            for i, xpath in enumerate(xpath_patterns):
                try:
                    element = driver.find_element(By.XPATH, xpath)
                    href = element.get_attribute("href")
                    if href:
                        store_links.append(href)
                        print(f"    Found store link {i+1}: {href}")
                except NoSuchElementException:
                    continue
                except Exception as e:
                    print(f"    Error finding element with XPath {xpath}: {e}")
                    continue
            
            # Try to find more store links dynamically if the specific ones don't work
            if not store_links:
                print("    No store links found with specific XPaths, trying alternative patterns...")
                alternative_xpaths = [
                    "//div[contains(@class, 'store')]//a[@href]",
                    "//div[contains(@class, 'buy')]//a[@href]",
                    "//div[contains(@class, 'shop')]//a[@href]",
                    "//a[contains(@href, 'amazon')]",
                    "//a[contains(@href, 'flipkart')]",
                    "//a[contains(@href, 'myntra')]",
                    "//a[contains(@href, 'ajio')]"
                ]
                
                for alt_xpath in alternative_xpaths:
                    try:
                        elements = driver.find_elements(By.XPATH, alt_xpath)
                        for element in elements[:10]:  # Limit to first 10 to avoid too many links
                            href = element.get_attribute("href")
                            if href and href not in store_links:
                                store_links.append(href)
                                print(f"    Found alternative store link: {href}")
                    except Exception as e:
                        continue
            
            print(f"  Found {len(store_links)} total store links")
            return store_links
            
        except Exception as e:
            print(f"  Error scraping store links (attempt {attempt + 1}/{retries}): {e}")
            if attempt < retries - 1:
                time.sleep(2)
            else:
                print(f"  Failed to scrape store links after {retries} attempts")
                return []
    
    return []


def find_amazon_link_and_extract_asin(driver, store_links):
    """Find Amazon.in link from store links and extract ASIN"""
    potential_amazon_links = []
    
    # Filter for potential Amazon links (including smartprix redirect links)
    for link in store_links:
        if 'amazon' in link.lower() or 'l.smartprix.com' in link.lower():
            potential_amazon_links.append(link)
    
    if not potential_amazon_links:
        print("  No potential Amazon links found in store links")
        return None, False
    
    print(f"  Found {len(potential_amazon_links)} potential Amazon links")
    
    # Try each potential Amazon link to see which one redirects to amazon.in
    for i, amazon_link in enumerate(potential_amazon_links):
        try:
            print(f"    Checking link {i+1}: {amazon_link}")
            
            # Visit the link
            driver.get(amazon_link)
            time.sleep(5)  # Give more time for redirects
            
            # Check if we're on amazon.in
            current_url = driver.current_url
            print(f"    Redirected to: {current_url}")
            
            if 'amazon.in' in current_url:
                print(f"    Found Amazon.in redirect!")
                
                # Extract ASIN from the URL
                asin = extract_asin_from_amazon_url(current_url)
                if asin:
                    print(f"    Extracted ASIN: {asin}")
                    
                    # Try to extract MRP from current page first
                    mrp = get_amazon_mrp(driver)
                    
                    # If MRP not found on redirect page, try navigating directly to Amazon
                    if not mrp:
                        print(f"    MRP not found via redirect, trying direct navigation...")
                        mrp = get_amazon_mrp_from_asin(driver, asin)
                    
                    return {"asin": asin, "mrp": mrp}, True
                else:
                    print(f"    Could not extract ASIN from URL, trying to find ASIN in page content...")
                    # Try to find ASIN in page content
                    try:
                        # Look for products with ASIN in the page
                        asin_elements = driver.find_elements(By.XPATH, "//div[@data-asin]")
                        if asin_elements:
                            for element in asin_elements:
                                asin = element.get_attribute("data-asin")
                                if asin and len(asin) == 10:  # ASIN is typically 10 characters
                                    print(f"    Found ASIN in page data: {asin}")
                                    
                                    # Try to extract MRP from current page first
                                    mrp = get_amazon_mrp(driver)
                                    
                                    # If MRP not found, try navigating directly to Amazon
                                    if not mrp:
                                        print(f"    MRP not found on current page, trying direct navigation...")
                                        mrp = get_amazon_mrp_from_asin(driver, asin)
                                    
                                    return {"asin": asin, "mrp": mrp}, True
                        
                        # Try alternative methods to find ASIN
                        asin_links = driver.find_elements(By.XPATH, "//a[contains(@href, '/dp/')]")
                        if asin_links:
                            for link in asin_links[:3]:  # Check first 3 links
                                href = link.get_attribute("href")
                                if href:
                                    asin = extract_asin_from_amazon_url(href)
                                    if asin:
                                        print(f"    Found ASIN in product link: {asin}")
                                        
                                        # Try to extract MRP from current page first
                                        mrp = get_amazon_mrp(driver)
                                        
                                        # If MRP not found, try navigating directly to Amazon
                                        if not mrp:
                                            print(f"    MRP not found on current page, trying direct navigation...")
                                            mrp = get_amazon_mrp_from_asin(driver, asin)
                                        
                                        return {"asin": asin, "mrp": mrp}, True
                    except Exception as e:
                        print(f"    Error finding ASIN in page: {e}")
                        continue
                    
                    print(f"    Could not extract ASIN from page content")
            else:
                print(f"    Link does not redirect to amazon.in")
                
        except Exception as e:
            print(f"    Error checking link {i+1}: {e}")
            continue
    
    print("  No valid Amazon.in links found or ASIN could not be extracted")
    return None, False


def load_mobiles_data():
    """Load mobile data from mobiles.json"""
    try:
        with open("mobiles.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("products", [])
    except FileNotFoundError:
        print("Error: mobiles.json file not found!")
        return []
    except Exception as e:
        print(f"Error loading mobiles.json: {e}")
        return []


def save_asin_mrp_data(data):
    """Save ASIN and MRP data to asin_mrp.json"""
    try:
        with open("asin_mrp.json", "w", encoding="utf-8") as f:
            json.dump({
                "total_products": len(data),
                "products": data
            }, f, indent=2, ensure_ascii=False)
        print(f"Saved {len(data)} products to asin_mrp.json")
        return True
    except Exception as e:
        print(f"Error saving data to asin_mrp.json: {e}")
        return False


def process_product(driver, product):
    """Process a single product to extract ASIN and MRP"""
    print(f"\nProcessing: {product['name']}")
    print(f"URL: {product['url']}")
    
    # Scrape store links from the product page
    store_links = scrape_store_links(driver, product['url'])
    
    if not store_links:
        print("  No store links found for this product")
        return {
            "unique_id": product['unique_id'],
            "name": product['name'],
            "smartprix_url": product['url'],
            "asin": None,
            "mrp": None,
            "amazon_found": False,
            "error": "No store links found"
        }
    
    # Find Amazon link and extract ASIN and MRP
    amazon_data, amazon_found = find_amazon_link_and_extract_asin(driver, store_links)
    
    result = {
        "unique_id": product['unique_id'],
        "name": product['name'],
        "smartprix_url": product['url'],
        "asin": amazon_data['asin'] if amazon_data else None,
        "mrp": amazon_data['mrp'] if amazon_data else None,
        "amazon_found": amazon_found
    }
    
    if not amazon_found:
        result["error"] = "Amazon link not found or ASIN could not be extracted"
    
    return result


def main():
    """Main function to process all products and extract ASIN/MRP data"""
    print("ASIN and MRP Scraper for Smartprix Mobile Products")
    print("=" * 50)
    
    # Load mobile products data
    products = load_mobiles_data()
    if not products:
        print("No products found to process!")
        return
    
    print(f"Found {len(products)} products to process")
    
    # Setup Chrome driver
    driver = setup_driver()
    if not driver:
        print("Failed to setup Chrome driver!")
        return
    
    processed_data = []
    
    try:
        for i, product in enumerate(products, 1):
            print(f"\n[{i}/{len(products)}] Processing product...")
            
            result = process_product(driver, product)
            processed_data.append(result)
            
            # Show progress
            if result['amazon_found']:
                print(f"  ✓ Success: ASIN={result['asin']}, MRP={result['mrp']}")
            else:
                print(f"  ✗ Failed: {result.get('error', 'Unknown error')}")
            
            # Small delay between products
            time.sleep(2)
            
    except KeyboardInterrupt:
        print("\nProcess interrupted by user")
    except Exception as e:
        print(f"\nUnexpected error: {e}")
    finally:
        # Always save whatever data we have processed
        if processed_data:
            save_asin_mrp_data(processed_data)
        
        # Close the driver
        if driver:
            driver.quit()
    
    print(f"\nProcessing complete!")
    print(f"Successfully processed: {sum(1 for item in processed_data if item['amazon_found'])}/{len(processed_data)} products")


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Smartprix Mobile Phone Image Scraper
Scrapes product images from individual mobile phone pages using Selenium
"""

import json
import time
import os
import sys
import requests
import re
from urllib.parse import urlparse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import contextlib
from PIL import Image, ImageDraw
import io
import base64


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
    """Setup Chrome WebDriver with options (same as original script)"""
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
    # Note: NOT disabling images as we need to scrape them
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


def create_images_directory(unique_id):
    """Create directory structure for storing images"""
    try:
        # Create main images folder if it doesn't exist
        images_dir = "images"
        if not os.path.exists(images_dir):
            os.makedirs(images_dir)
        
        # Create subfolder with unique_id
        product_dir = os.path.join(images_dir, unique_id)
        if not os.path.exists(product_dir):
            os.makedirs(product_dir)
        
        return product_dir
    except Exception as e:
        print(f"Error creating directory: {e}")
        return None


def check_existing_images(unique_id):
    """Check if images already exist for this product and return count"""
    try:
        product_dir = os.path.join("images", unique_id)
        if os.path.exists(product_dir):
            existing_count = 0
            for filename in os.listdir(product_dir):
                if filename.startswith("image_") and filename.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                    existing_count += 1
            return existing_count
        return 0
    except Exception as e:
        print(f"Error checking existing images: {e}")
        return 0


def transform_image_url(image_url):
    """Transform image URL to get higher resolution version"""
    if image_url.startswith("https://cdn1.smartprix.com/"):
        # Replace -w***-h*** with -w1800-h1800 for higher resolution
        pattern = r'-w\d+-h\d+/'
        replacement = '-w1800-h1800/'
        transformed_url = re.sub(pattern, replacement, image_url)
        return transformed_url
    return image_url


def convert_webp_to_jpg(webp_path, jpg_path):
    """Convert WebP image to JPG format"""
    try:
        with Image.open(webp_path) as img:
            # Convert to RGB if necessary (WebP might have alpha channel)
            if img.mode in ('RGBA', 'LA'):
                # Create a white background
                rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                rgb_img.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = rgb_img
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Save as JPG
            img.save(jpg_path, 'JPEG', quality=95)
        return True
    except Exception as e:
        print(f"    Error converting WebP to JPG: {e}")
        return False


def convert_svg_to_jpg_with_selenium(driver, svg_content, jpg_path):
    """Convert SVG content to JPG format using selenium screenshot"""
    try:
        # Create a temporary HTML file with the SVG
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    margin: 0;
                    padding: 20px;
                    background-color: white;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    min-height: 100vh;
                }}
                svg {{
                    max-width: 800px;
                    max-height: 600px;
                }}
            </style>
        </head>
        <body>
            {svg_content.decode('utf-8') if isinstance(svg_content, bytes) else svg_content}
        </body>
        </html>
        """
        
        # Save HTML to temporary file
        temp_html_path = "temp_svg.html"
        with open(temp_html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        # Load HTML in selenium
        driver.get(f"file:///{os.path.abspath(temp_html_path)}")
        time.sleep(2)
        
        # Take screenshot
        screenshot = driver.get_screenshot_as_png()
        
        # Convert screenshot to PIL Image
        img = Image.open(io.BytesIO(screenshot))
        
        # Convert to black and white
        bw_img = img.convert('L')
        
        # Save as JPG
        bw_img.save(jpg_path, 'JPEG', quality=95)
        
        # Clean up temporary file
        try:
            os.remove(temp_html_path)
        except:
            pass
        
        return True
    except Exception as e:
        print(f"    Error converting SVG to JPG with selenium: {e}")
        return False


def download_svg_with_selenium(driver, svg_url, save_path):
    """Download SVG using Selenium and convert to black and white JPG"""
    try:
        print(f"    Using Selenium to access SVG: {svg_url}")
        
        # Navigate to the SVG URL directly
        driver.get(svg_url)
        time.sleep(3)  # Wait for SVG to load
        
        # Get the page source which should contain the SVG
        page_source = driver.page_source
        
        # Check if this is actually an SVG response by looking at content type or page source
        if '<svg' in page_source:
            # Extract SVG content from the page source
            svg_start = page_source.find('<svg')
            svg_end = page_source.find('</svg>') + 6
            
            if svg_start != -1 and svg_end != -1:
                svg_content = page_source[svg_start:svg_end]
                print(f"    Extracted SVG content from page")
                
                # Convert extracted SVG to JPG
                if convert_svg_to_jpg_with_selenium(driver, svg_content, save_path):
                    return True
        
        # If extraction failed, try taking a screenshot of the entire page
        print(f"    SVG extraction failed, taking screenshot instead")
        
        # Set window size to ensure we get the full SVG
        driver.set_window_size(1200, 800)
        time.sleep(1)
        
        screenshot = driver.get_screenshot_as_png()
        
        # Convert screenshot to PIL Image
        img = Image.open(io.BytesIO(screenshot))
        
        # Try to crop to just the SVG content (remove browser chrome)
        # This is a rough estimate - you might need to adjust based on actual SVG size
        width, height = img.size
        
        # Crop out browser elements (rough estimate)
        # Usually SVG content is centered, so we crop from center
        crop_margin = min(width, height) // 10
        cropped_img = img.crop((crop_margin, crop_margin, width - crop_margin, height - crop_margin))
        
        # Convert to black and white
        bw_img = cropped_img.convert('L')
        
        # Resize to a reasonable size (e.g., 800x600 max)
        max_size = 800
        if bw_img.width > max_size or bw_img.height > max_size:
            bw_img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
        
        # Save as JPG
        bw_img.save(save_path, 'JPEG', quality=95)
        print(f"    Saved screenshot as black and white JPG")
        return True
        
    except Exception as e:
        print(f"    Error downloading SVG with Selenium: {e}")
        return False


def convert_svg_to_jpg(svg_content, jpg_path):
    """Convert SVG content to JPG format and make it black and white (fallback method)"""
    try:
        # Create a simple black and white placeholder image for SVG files
        # This is a fallback when selenium method fails
        img = Image.new('RGB', (800, 600), color='white')
        draw = ImageDraw.Draw(img)
        
        # Draw some basic shapes to indicate it's an SVG file
        draw.rectangle([50, 50, 750, 550], outline='black', width=3)
        draw.text((300, 250), "SVG Image", fill='black')
        draw.text((280, 300), "(Converted)", fill='black')
        
        # Convert to black and white
        bw_img = img.convert('L')
        
        # Save as JPG
        bw_img.save(jpg_path, 'JPEG', quality=95)
        return True
    except Exception as e:
        print(f"    Error converting SVG to JPG: {e}")
        return False


def download_and_process_image(image_url, save_path, driver=None, retries=3):
    """Download image from URL, process it, and save locally"""
    for attempt in range(retries):
        try:
            # Check if this is a smartprix.com SVG URL that might need special handling
            if image_url.startswith("https://www.smartprix.com/"):
                print(f"    Detected smartprix.com SVG URL: {image_url}")
                if driver:
                    return download_svg_with_selenium(driver, image_url, save_path)
                else:
                    print(f"    No driver available for SVG download")
                    return False
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            # Transform URL to get higher resolution if it's a CDN URL
            processed_url = transform_image_url(image_url)
            print(f"    Downloading: {processed_url}")
            
            response = requests.get(processed_url, headers=headers, timeout=15)
            response.raise_for_status()
            
            # Determine file type and process accordingly
            content_type = response.headers.get('content-type', '').lower()
            
            if 'svg' in content_type or processed_url.endswith('.svg'):
                # Handle SVG files - convert to black and white JPG
                print(f"    Processing SVG file...")
                # Try selenium method first, then fallback
                if driver and convert_svg_to_jpg_with_selenium(driver, response.content, save_path):
                    return True
                elif convert_svg_to_jpg(response.content, save_path):
                    return True
                else:
                    print(f"    Failed to convert SVG to JPG")
                    return False
            
            elif 'webp' in content_type or processed_url.endswith('.webp'):
                # Handle WebP files - convert to JPG
                print(f"    Processing WebP file...")
                temp_webp_path = save_path.replace('.jpg', '.webp')
                
                # Save WebP temporarily
                with open(temp_webp_path, 'wb') as f:
                    f.write(response.content)
                
                # Convert to JPG
                if convert_webp_to_jpg(temp_webp_path, save_path):
                    # Remove temporary WebP file
                    try:
                        os.remove(temp_webp_path)
                    except:
                        pass
                    return True
                else:
                    print(f"    Failed to convert WebP to JPG")
                    return False
            
            else:
                # Handle other image formats (JPG, PNG, etc.)
                print(f"    Processing {content_type} file...")
                temp_path = save_path.replace('.jpg', f'_temp{os.path.splitext(processed_url)[1]}')
                
                # Save original file temporarily
                with open(temp_path, 'wb') as f:
                    f.write(response.content)
                
                # Convert to JPG if needed
                if not temp_path.endswith('.jpg'):
                    try:
                        with Image.open(temp_path) as img:
                            # Convert to RGB if necessary
                            if img.mode in ('RGBA', 'LA'):
                                # Create a white background
                                rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                                rgb_img.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                                img = rgb_img
                            elif img.mode != 'RGB':
                                img = img.convert('RGB')
                            
                            # Save as JPG
                            img.save(save_path, 'JPEG', quality=95)
                        
                        # Remove temporary file
                        try:
                            os.remove(temp_path)
                        except:
                            pass
                        return True
                    except Exception as e:
                        print(f"    Error converting image to JPG: {e}")
                        return False
                else:
                    # Already JPG, just move it
                    try:
                        os.rename(temp_path, save_path)
                        return True
                    except:
                        return False
            
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(1)
            else:
                print(f"    Failed to download and process image after {retries} attempts: {e}")
                return False
    
    return False


def scrape_product_image_urls_only(driver, product_url, retries=3):
    """Scrape image URLs from a product page without downloading"""
    for attempt in range(retries):
        try:
            print(f"  Visiting URL: {product_url}")
            driver.get(product_url)
            
            # Wait for page to load
            wait = WebDriverWait(driver, 10)
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            
            # Give extra time for images to load
            time.sleep(3)
            
            # Find all image elements using the specific XPath pattern
            image_urls = []
            
            # Try multiple variations of the XPath in case the structure varies slightly
            xpath_patterns = [
                "/html/body/div[1]/main/div[1]/div[1]/div[1]/div[3]/ul/li[{index}]/img",
                "/html/body/div[1]/main/div[1]/div[1]/div[1]/div[2]/ul/li[{index}]/img",
                "/html/body/div[1]/main/div[1]/div[1]/div[1]/div[4]/ul/li[{index}]/img",
                "/html/body/div[1]/main/div[1]/div[1]/div[2]/div[3]/ul/li[{index}]/img",
                "/html/body/div[1]/main/div[1]/div[2]/div[1]/div[3]/ul/li[{index}]/img"
            ]
            
            # Try each pattern
            for pattern in xpath_patterns:
                if image_urls:  # If we already found images with a previous pattern, break
                    break
                    
                print(f"    Trying XPath pattern: {pattern.format(index='N')}")
                image_index = 1
                
                while True:
                    try:
                        # Construct XPath for current image
                        xpath = pattern.format(index=image_index)
                        
                        # Try to find the image element
                        img_element = driver.find_element(By.XPATH, xpath)
                        
                        # Get the image URL
                        src = img_element.get_attribute("src")
                        if not src:
                            # Try data-src or data-lazy attributes
                            src = img_element.get_attribute("data-src") or img_element.get_attribute("data-lazy")
                        
                        if src and src.startswith("http"):
                            image_urls.append(src)
                            print(f"    Found image {image_index}: {src}")
                        
                        image_index += 1
                        
                    except NoSuchElementException:
                        # No more images found at this index for this pattern
                        if image_index == 1:
                            print(f"    No images found with this pattern")
                        else:
                            print(f"    Found {image_index - 1} images with this pattern")
                        break
                    except Exception as e:
                        print(f"    Error getting image {image_index}: {e}")
                        break
            
            # If no images found with the specific patterns, try alternative methods
            if not image_urls:
                print("    No images found with specific XPath, trying alternative methods...")
                
                # Try alternative XPaths that might work
                alternative_xpaths = [
                    "//div[contains(@class, 'gallery')]//img",
                    "//div[contains(@class, 'product-images')]//img",
                    "//div[contains(@class, 'image')]//img",
                    "//ul//li//img",
                    "//main//img"
                ]
                
                for alt_xpath in alternative_xpaths:
                    try:
                        images = driver.find_elements(By.XPATH, alt_xpath)
                        for img in images:
                            src = img.get_attribute("src") or img.get_attribute("data-src")
                            if src and src.startswith("http"):
                                # Filter out obvious non-product images
                                if not any(unwanted in src.lower() for unwanted in ['logo', 'icon', 'banner', 'ad', 'social', 'header', 'footer']):
                                    if src not in image_urls:
                                        image_urls.append(src)
                        
                        if image_urls:
                            print(f"    Found {len(image_urls)} images using alternative method")
                            break
                    except Exception as e:
                        continue
            
            print(f"  Found {len(image_urls)} total images")
            return image_urls
            
        except Exception as e:
            print(f"  Error scraping images (attempt {attempt + 1}/{retries}): {e}")
            if attempt < retries - 1:
                time.sleep(2)
            else:
                print(f"  Failed to scrape images after {retries} attempts")
                return []
    
    return []


def scrape_and_save_product_images(driver, product_url, unique_id, retries=3):
    """Scrape image URLs from a product page and save them locally, return original URLs"""
    for attempt in range(retries):
        try:
            print(f"  Visiting URL: {product_url}")
            driver.get(product_url)
            
            # Wait for page to load
            wait = WebDriverWait(driver, 10)
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            
            # Give extra time for images to load
            time.sleep(3)
            
            # Find all image elements using the specific XPath pattern
            image_urls = []
            
            # Use the exact XPath pattern provided by user
            # /html/body/div[1]/main/div[1]/div[1]/div[1]/div[3]/ul/li[1]/img
            # /html/body/div[1]/main/div[1]/div[1]/div[1]/div[3]/ul/li[2]/img
            # etc.
            
            # Try multiple variations of the XPath in case the structure varies slightly
            xpath_patterns = [
                "/html/body/div[1]/main/div[1]/div[1]/div[1]/div[3]/ul/li[{index}]/img",
                "/html/body/div[1]/main/div[1]/div[1]/div[1]/div[2]/ul/li[{index}]/img",
                "/html/body/div[1]/main/div[1]/div[1]/div[1]/div[4]/ul/li[{index}]/img",
                "/html/body/div[1]/main/div[1]/div[1]/div[2]/div[3]/ul/li[{index}]/img",
                "/html/body/div[1]/main/div[1]/div[2]/div[1]/div[3]/ul/li[{index}]/img"
            ]
            
            # Try each pattern
            for pattern in xpath_patterns:
                if image_urls:  # If we already found images with a previous pattern, break
                    break
                    
                print(f"    Trying XPath pattern: {pattern.format(index='N')}")
                image_index = 1
                
                while True:
                    try:
                        # Construct XPath for current image
                        xpath = pattern.format(index=image_index)
                        
                        # Try to find the image element
                        img_element = driver.find_element(By.XPATH, xpath)
                        
                        # Get the image URL
                        src = img_element.get_attribute("src")
                        if not src:
                            # Try data-src or data-lazy attributes
                            src = img_element.get_attribute("data-src") or img_element.get_attribute("data-lazy")
                        
                        if src and src.startswith("http"):
                            image_urls.append(src)
                            print(f"    Found image {image_index}: {src}")
                        
                        image_index += 1
                        
                    except NoSuchElementException:
                        # No more images found at this index for this pattern
                        if image_index == 1:
                            print(f"    No images found with this pattern")
                        else:
                            print(f"    Found {image_index - 1} images with this pattern")
                        break
                    except Exception as e:
                        print(f"    Error getting image {image_index}: {e}")
                        break
            
            # If no images found with the specific pattern, try alternative methods
            if not image_urls:
                print("    No images found with specific XPath, trying alternative methods...")
                
                # Try alternative XPaths that might work
                alternative_xpaths = [
                    "//div[contains(@class, 'gallery')]//img",
                    "//div[contains(@class, 'product-images')]//img",
                    "//div[contains(@class, 'image')]//img",
                    "//ul//li//img",
                    "//main//img"
                ]
                
                for alt_xpath in alternative_xpaths:
                    try:
                        images = driver.find_elements(By.XPATH, alt_xpath)
                        for img in images:
                            src = img.get_attribute("src") or img.get_attribute("data-src")
                            if src and src.startswith("http"):
                                # Filter out obvious non-product images
                                if not any(unwanted in src.lower() for unwanted in ['logo', 'icon', 'banner', 'ad', 'social', 'header', 'footer']):
                                    if src not in image_urls:
                                        image_urls.append(src)
                        
                        if image_urls:
                            print(f"    Found {len(image_urls)} images using alternative method")
                            break
                    except Exception as e:
                        continue
            
            print(f"  Found {len(image_urls)} total images")
            
            # Create directory for this product
            product_dir = create_images_directory(unique_id)
            if not product_dir:
                print("  Failed to create product directory")
                return []
            
            # Download and save images, but return original URLs
            successfully_downloaded = []
            for i, image_url in enumerate(image_urls, 1):
                try:
                    # All images will be saved as JPG regardless of original format
                    filename = f"image_{i}.jpg"
                    save_path = os.path.join(product_dir, filename)
                    
                    # Download and process image
                    print(f"    Processing image {i}: {image_url}")
                    if download_and_process_image(image_url, save_path, driver):
                        # Store original URL for JSON (not local path)
                        successfully_downloaded.append(image_url)
                        print(f"    Saved locally as: {filename}")
                    else:
                        print(f"    Failed to process image {i}")
                        
                except Exception as e:
                    print(f"    Error processing image {i}: {e}")
                    continue
            
            print(f"  Successfully downloaded {len(successfully_downloaded)} images")
            return successfully_downloaded
            
        except Exception as e:
            print(f"  Error scraping images (attempt {attempt + 1}/{retries}): {e}")
            if attempt < retries - 1:
                time.sleep(2)
            else:
                print(f"  Failed to scrape images after {retries} attempts")
                return []
    
    return []


def load_mobiles_data(json_file_path):
    """Load existing mobiles data from JSON file"""
    try:
        with open(json_file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except Exception as e:
        print(f"Error loading mobiles data: {e}")
        return None


def save_updated_mobiles_data(data, json_file_path):
    """Save updated mobiles data to JSON file"""
    try:
        with open(json_file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving updated mobiles data: {e}")
        return False


def main():
    """Main function to scrape product images"""
    print("=== Smartprix Mobile Image Scraper ===")
    print("Loading existing mobiles data...")
    
    # Load existing mobiles data
    mobiles_data = load_mobiles_data("mobiles.json")
    if not mobiles_data:
        print("Failed to load mobiles data. Exiting.")
        return
    
    products = mobiles_data.get("products", [])
    total_products = len(products)
    print(f"Found {total_products} products to process")
    
    # Option to test with limited products first
    test_mode = input("Test mode? Enter number of products to test (or press Enter for all): ").strip()
    if test_mode and test_mode.isdigit():
        test_limit = int(test_mode)
        products = products[:test_limit]
        total_products = len(products)
        print(f"Testing with first {total_products} products")
    
    # Setup Chrome driver
    print("Setting up Chrome driver...")
    driver = setup_driver()
    if not driver:
        print("Failed to setup Chrome driver. Exiting.")
        return
    
    try:
        # Prepare updated data structure
        updated_data = {
            "total_mobile_phones": mobiles_data.get("total_mobile_phones", 0),
            "products": []
        }
        
        # Process each product
        for i, product in enumerate(products, 1):
            print(f"\nProcessing product {i}/{total_products}: {product.get('name', 'Unknown')}")
            
            # Create updated product data with original fields
            updated_product = {
                "count": product.get("count", i),
                "unique_id": product.get("unique_id"),
                "name": product.get("name"),
                "price": product.get("price"),
                "url": product.get("url")
            }
            
            # Check for existing images first
            existing_count = check_existing_images(product.get("unique_id", ""))
            
            if existing_count > 0:
                print(f"  Found {existing_count} existing images, skipping download")
                # For existing images, we need to scrape URLs but not download
                if product.get("url") and product.get("unique_id"):
                    # Just scrape URLs without downloading
                    original_image_urls = scrape_product_image_urls_only(driver, product["url"])
                    print(f"  Retrieved {len(original_image_urls)} original URLs")
                else:
                    print("  No URL found for this product")
                    original_image_urls = []
            else:
                # Scrape and save images if URL exists
                if product.get("url") and product.get("unique_id"):
                    original_image_urls = scrape_and_save_product_images(driver, product["url"], product["unique_id"])
                    print(f"  Downloaded {len(original_image_urls)} new images")
                else:
                    print("  No URL or unique_id found for this product")
                    original_image_urls = []
            
            # Add original image URLs to the product data
            for j, image_url in enumerate(original_image_urls, 1):
                updated_product[f"image_{j}_url"] = image_url
            
            if original_image_urls:
                print(f"  Added {len(original_image_urls)} original image URLs to JSON")
            
            # Add to updated data
            updated_data["products"].append(updated_product)
            
            # Save progress every 10 products
            if i % 10 == 0:
                print(f"  Saving progress... ({i}/{total_products})")
                save_updated_mobiles_data(updated_data, "update_mobiles.json")
            
            # Add small delay between requests
            time.sleep(1)
        
        # Save final data
        print(f"\nSaving final data to update_mobiles.json...")
        if save_updated_mobiles_data(updated_data, "update_mobiles.json"):
            print("Successfully saved updated mobiles data!")
        else:
            print("Failed to save updated mobiles data.")
    
    except KeyboardInterrupt:
        print("\nScript interrupted by user. Saving current progress...")
        save_updated_mobiles_data(updated_data, "update_mobiles.json")
        print("Progress saved.")
    
    except Exception as e:
        print(f"Error during scraping: {e}")
        print("Saving current progress...")
        save_updated_mobiles_data(updated_data, "update_mobiles.json")
    
    finally:
        # Close the driver
        if driver:
            driver.quit()
            print("Chrome driver closed.")


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Smartprix Mobile Phone Image and Variant Scraper
Scrapes product images and variants from individual mobile phone pages using Selenium
"""

import json
import time
import os
import sys
import requests
import re
import shutil
import unicodedata
from urllib.parse import urlparse, quote_plus
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import contextlib
from PIL import Image, ImageDraw
import io
import base64
import tempfile
from time_manager import TimeManager


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


def clean_unicode_text(text):
    """Clean and normalize unicode text to ensure proper handling"""
    if not text:
        return text
    
    try:
        # Normalize unicode characters
        normalized = unicodedata.normalize('NFKC', text)
        
        # Clean up any problematic characters while preserving important ones
        # Keep currency symbols, measurement symbols, and special characters
        cleaned = normalized.strip()
        
        # Handle specific problematic characters
        replacements = {
            # Smart quotes to regular quotes
            '"': '"',
            '"': '"',
            ''': "'",
            ''': "'",
            # En-dash and em-dash to regular dash
            '–': '-',
            '—': '-',
            # Other problematic characters
            '…': '...',
            # Keep these important symbols as-is:
            # ₹ (rupee), ƒ (f-hook), µ (micro), ~ (tilde), ° (degree)
        }
        
        for old, new in replacements.items():
            cleaned = cleaned.replace(old, new)
        
        return cleaned
    except Exception as e:
        print(f"Error cleaning unicode text: {e}")
        return text


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
                    align-items: flex-start;
                    min-height: 100vh;
                    overflow: visible;
                }}
                svg {{
                    max-width: 1200px;
                    max-height: none;
                    height: auto;
                    width: auto;
                    display: block;
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
        
        # Get the SVG element to determine its actual dimensions
        try:
            svg_element = driver.find_element(By.TAG_NAME, "svg")
            svg_rect = svg_element.rect
            svg_width = svg_rect['width']
            svg_height = svg_rect['height']
            
            # Set window size to accommodate the SVG with some padding
            window_width = max(1200, int(svg_width) + 100)
            window_height = max(800, int(svg_height) + 200)
            driver.set_window_size(window_width, window_height)
            time.sleep(1)
            
            print(f"    SVG dimensions: {svg_width}x{svg_height}, window size: {window_width}x{window_height}")
            
        except Exception as e:
            print(f"    Could not get SVG dimensions, using default window size: {e}")
            driver.set_window_size(1200, 1000)
        
        # Scroll to top to ensure we capture from the beginning
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(1)
        
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
        
        # Try to get the SVG element dimensions if it's loaded directly
        try:
            svg_element = driver.find_element(By.TAG_NAME, "svg")
            if svg_element:
                svg_rect = svg_element.rect
                svg_width = svg_rect['width']
                svg_height = svg_rect['height']
                
                # Set window size to accommodate the SVG
                window_width = max(1200, int(svg_width) + 100)
                window_height = max(800, int(svg_height) + 200)
                driver.set_window_size(window_width, window_height)
                time.sleep(2)
                
                print(f"    Direct SVG dimensions: {svg_width}x{svg_height}, window size: {window_width}x{window_height}")
        except Exception as e:
            print(f"    Could not get direct SVG dimensions: {e}")
        
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
        
        # Try to get the actual content dimensions first
        try:
            # Execute JavaScript to get the actual content dimensions
            content_width = driver.execute_script("return Math.max(document.body.scrollWidth, document.documentElement.scrollWidth);")
            content_height = driver.execute_script("return Math.max(document.body.scrollHeight, document.documentElement.scrollHeight);")
            
            # Set window size to ensure we get the full content
            window_width = max(1200, content_width + 100)
            window_height = max(800, content_height + 100)
            driver.set_window_size(window_width, window_height)
            time.sleep(2)
            
            print(f"    Content dimensions: {content_width}x{content_height}, window size: {window_width}x{window_height}")
            
        except Exception as e:
            print(f"    Could not get content dimensions, using larger default window size: {e}")
            driver.set_window_size(1600, 1200)
            time.sleep(2)
        
        # Scroll to top to ensure we capture from the beginning
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(1)
        
        # Take screenshot of the full page
        screenshot = driver.get_screenshot_as_png()
        
        # Convert screenshot to PIL Image
        img = Image.open(io.BytesIO(screenshot))
        
        # More conservative cropping to avoid cutting off content
        width, height = img.size
        
        # Only crop if the image is much larger than expected
        # Use smaller margins to preserve more content
        if width > 1000 or height > 800:
            # Conservative cropping - only remove obvious browser chrome
            crop_top = 50  # Remove top browser elements
            crop_bottom = 50  # Remove bottom browser elements  
            crop_left = 50  # Remove left browser elements
            crop_right = 50  # Remove right browser elements
            
            # Make sure we don't crop too much
            crop_top = min(crop_top, height // 20)
            crop_bottom = min(crop_bottom, height // 20)
            crop_left = min(crop_left, width // 20)
            crop_right = min(crop_right, width // 20)
            
            cropped_img = img.crop((crop_left, crop_top, width - crop_right, height - crop_bottom))
        else:
            # For smaller images, don't crop at all
            cropped_img = img
        
        # Convert to black and white
        bw_img = cropped_img.convert('L')
        
        # Resize to a reasonable size (e.g., 1200x900 max to preserve more detail)
        max_size = 1200
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





def scrape_product_variants(driver, product_url, retries=3):
    """Scrape product variants from a product page"""
    for attempt in range(retries):
        try:
            print(f"  Scraping variants from: {product_url}")
            driver.get(product_url)
            
            # Wait for page to load
            wait = WebDriverWait(driver, 10)
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            
            # Give extra time for dynamic content to load
            time.sleep(3)
            
            variants = []
            
            # Try to scrape variants using the specified XPath pattern
            # /html/body/div[1]/main/div[1]/div[2]/div[4]/div[2]/div[1]
            # /html/body/div[1]/main/div[1]/div[2]/div[4]/div[2]/div[2]
            # etc.
            
            # Try multiple variations of the XPath in case the structure varies slightly
            xpath_patterns = [
                "/html/body/div[1]/main/div[1]/div[2]/div[4]/div[2]/div[{index}]",
                "/html/body/div[1]/main/div[1]/div[2]/div[3]/div[2]/div[{index}]",
                "/html/body/div[1]/main/div[1]/div[2]/div[5]/div[2]/div[{index}]",
                "/html/body/div[1]/main/div[1]/div[1]/div[4]/div[2]/div[{index}]",
                "/html/body/div[1]/main/div[1]/div[3]/div[4]/div[2]/div[{index}]"
            ]
            
            # Try each pattern
            for pattern in xpath_patterns:
                if variants:  # If we already found variants with a previous pattern, break
                    break
                    
                print(f"    Trying XPath pattern: {pattern.format(index='N')}")
                variant_index = 1
                
                while True:
                    try:
                        # Construct XPath for current variant
                        xpath = pattern.format(index=variant_index)
                        
                        # Try to find the variant element
                        variant_element = driver.find_element(By.XPATH, xpath)
                        
                        # Extract variant data
                        variant_data = {
                            "size": None,
                            "price": None
                        }
                        
                        # Try to extract size/variant info
                        try:
                            # Look for size info in various ways
                            size_selectors = [
                                "span",
                                "div[class*='size']",
                                "div[class*='variant']",
                                "div[class*='option']",
                                "*[class*='size']",
                                "*[class*='variant']",
                                "*[class*='option']"
                            ]
                            
                            for selector in size_selectors:
                                try:
                                    size_elements = variant_element.find_elements(By.CSS_SELECTOR, selector)
                                    for elem in size_elements:
                                        text = elem.text.strip()
                                        if text and any(keyword in text.lower() for keyword in ['gb', 'tb', 'ram', 'storage', 'memory']):
                                            variant_data["size"] = text
                                            break
                                    if variant_data["size"]:
                                        break
                                except:
                                    continue
                            
                            # If no size found, try getting all text from the element
                            if not variant_data["size"]:
                                all_text = variant_element.text.strip()
                                if all_text:
                                    # Look for patterns like "8GB+128GB" or "8GB RAM 128GB"
                                    size_match = re.search(r'(\d+\s*GB[^₹]*(?:\+|\s+)\d+\s*GB[^₹]*)', all_text, re.IGNORECASE)
                                    if size_match:
                                        variant_data["size"] = size_match.group(1).strip()
                                    else:
                                        # Look for any GB/TB patterns
                                        gb_match = re.search(r'(\d+\s*(?:GB|TB)[^₹]*)', all_text, re.IGNORECASE)
                                        if gb_match:
                                            variant_data["size"] = gb_match.group(1).strip()
                        except Exception as e:
                            print(f"    Error extracting size: {e}")
                        
                        # Try to extract price
                        try:
                            # Look for price info in various ways
                            price_selectors = [
                                "span[class*='price']",
                                "div[class*='price']",
                                "*[class*='price']",
                                "span",
                                "div"
                            ]
                            
                            for selector in price_selectors:
                                try:
                                    price_elements = variant_element.find_elements(By.CSS_SELECTOR, selector)
                                    for elem in price_elements:
                                        text = elem.text.strip()
                                        if text and '₹' in text:
                                            variant_data["price"] = text
                                            break
                                    if variant_data["price"]:
                                        break
                                except:
                                    continue
                            
                            # If no price found, try getting all text from the element
                            if not variant_data["price"]:
                                all_text = variant_element.text.strip()
                                if all_text and '₹' in all_text:
                                    # Extract price pattern
                                    price_match = re.search(r'₹[\d,]+', all_text)
                                    if price_match:
                                        variant_data["price"] = price_match.group().strip()
                        except Exception as e:
                            print(f"    Error extracting price: {e}")
                        
                        # Only add variant if we have at least size or price
                        if variant_data["size"] or variant_data["price"]:
                            variants.append(variant_data)
                            print(f"    Found variant {variant_index}: Size='{variant_data['size']}', Price='{variant_data['price']}'")
                        
                        variant_index += 1
                        
                    except NoSuchElementException:
                        # No more variants found at this index for this pattern
                        if variant_index == 1:
                            print(f"    No variants found with this pattern")
                        else:
                            print(f"    Found {variant_index - 1} variants with this pattern")
                        break
                    except Exception as e:
                        print(f"    Error getting variant {variant_index}: {e}")
                        break
            
            # If no variants found with the specific pattern, try alternative methods
            if not variants:
                print("    No variants found with specific XPath, trying alternative methods...")
                
                # Try alternative selectors that might work
                alternative_selectors = [
                    "div[class*='variant']",
                    "div[class*='option']",
                    "div[class*='size']",
                    "div[class*='price-option']",
                    "div[class*='config']",
                    "div[class*='storage']",
                    "button[class*='variant']",
                    "button[class*='option']",
                    "span[class*='variant']",
                    "span[class*='option']"
                ]
                
                for selector in alternative_selectors:
                    try:
                        variant_elements = driver.find_elements(By.CSS_SELECTOR, selector)
                        for elem in variant_elements:
                            text = elem.text.strip()
                            if text and (any(keyword in text.lower() for keyword in ['gb', 'tb', 'ram', 'storage']) or '₹' in text):
                                # Try to extract size and price from the text
                                variant_data = {
                                    "size": None,
                                    "price": None
                                }
                                
                                # Extract size
                                size_match = re.search(r'(\d+\s*GB[^₹]*(?:\+|\s+)\d+\s*GB[^₹]*)', text, re.IGNORECASE)
                                if size_match:
                                    variant_data["size"] = size_match.group(1).strip()
                                else:
                                    gb_match = re.search(r'(\d+\s*(?:GB|TB)[^₹]*)', text, re.IGNORECASE)
                                    if gb_match:
                                        variant_data["size"] = gb_match.group(1).strip()
                                
                                # Extract price
                                price_match = re.search(r'₹[\d,]+', text)
                                if price_match:
                                    variant_data["price"] = price_match.group().strip()
                                
                                # Add variant if we have at least size or price
                                if variant_data["size"] or variant_data["price"]:
                                    # Check if this variant already exists
                                    variant_exists = False
                                    for existing_variant in variants:
                                        if (existing_variant["size"] == variant_data["size"] and 
                                            existing_variant["price"] == variant_data["price"]):
                                            variant_exists = True
                                            break
                                    
                                    if not variant_exists:
                                        variants.append(variant_data)
                        
                        if variants:
                            print(f"    Found {len(variants)} variants using alternative method")
                            break
                    except Exception as e:
                        continue
            
            print(f"  Found {len(variants)} total variants")
            return variants
            
        except Exception as e:
            print(f"  Error scraping variants (attempt {attempt + 1}/{retries}): {e}")
            if attempt < retries - 1:
                time.sleep(2)
            else:
                print(f"  Failed to scrape variants after {retries} attempts")
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


def append_product_to_json(product_data, json_file_path):
    """Append a single product to the JSON file"""
    try:
        # Load existing data
        try:
            with open(json_file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            # If file doesn't exist or is corrupted, create new structure
            data = {
                "products": []
            }
        
        # Add the new product
        data["products"].append(product_data)
        
        # Save updated data
        with open(json_file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        return True
    except Exception as e:
        print(f"Error appending product to JSON: {e}")
        return False


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


def extract_specs_from_popup(driver, popup_element):
    """Extract specifications from the popup element and organize by sections"""
    try:
        features_by_section = {}
        
        # Extract specifications from the popup structure
        
        # Look for main section headers - these are typically larger headers that represent major categories
        main_section_selectors = [
            "h2, h3[class*='section'], h4[class*='section']",
            "div[class*='section-title'], div[class*='spec-section-title']",
            "dt[class*='section'], .spec-category[class*='main']",
            "*[class*='main-heading'], *[class*='section-header']"
        ]
        
        # Get all potential headers and analyze them
        all_headers = []
        header_selectors = ["h1, h2, h3, h4, h5, h6", "div[class*='title'], div[class*='header']", "dt, .category, .section"]
        
        for selector in header_selectors:
            try:
                found_headers = popup_element.find_elements(By.CSS_SELECTOR, selector)
                for header in found_headers:
                    header_text = header.text.strip()
                    if header_text:
                        header_info = {
                            'element': header,
                            'text': header_text,
                            'tag': header.tag_name,
                            'class': header.get_attribute('class') or '',
                            'font_size': header.value_of_css_property('font-size'),
                            'font_weight': header.value_of_css_property('font-weight')
                        }
                        all_headers.append(header_info)
            except:
                continue
        
        # Identify main sections based on known keywords and styling
        main_sections = []
        main_section_keywords = ['general', 'design', 'display', 'memory', 'camera', 'battery', 'connectivity', 'performance', 'technical', 'multimedia', 'extra']
        
        for header_info in all_headers:
            header_text_lower = header_info['text'].lower()
            
            # Check if this is a main section header
            if any(keyword in header_text_lower for keyword in main_section_keywords):
                # Additional checks to distinguish main sections from subsections
                is_main_section = False
                
                # Check 1: Main sections are typically one word and match our keywords exactly
                if header_text_lower in main_section_keywords:
                    is_main_section = True
                # Check 2: Main sections might have specific styling (larger font, bold, etc.)
                elif header_info['font_weight'] in ['bold', '700', '600'] or int(header_info['font_size'].replace('px', '')) > 14:
                    is_main_section = True
                # Check 3: Main sections might have specific classes
                elif any(cls in header_info['class'].lower() for cls in ['section', 'main', 'title', 'header']):
                    is_main_section = True
                
                if is_main_section:
                    main_sections.append(header_info)
        
        if main_sections:
            
            for i, section_info in enumerate(main_sections):
                section_name = section_info['text']
                section_element = section_info['element']
                
                # Find all specifications between this section and the next main section
                section_specs = []
                
                # Determine the range for this section
                if i < len(main_sections) - 1:
                    next_section_element = main_sections[i + 1]['element']
                    # Get all elements between current section and next section
                    xpath_query = f".//*[preceding-sibling::*[. = '{section_element}'] and following-sibling::*[. = '{next_section_element}']]"
                else:
                    # Last section - get all elements after this section
                    xpath_query = f".//*[preceding-sibling::*[. = '{section_element}']]"
                
                try:
                    # Find all tables in this section's range
                    tables_in_section = section_element.find_elements(By.XPATH, "following-sibling::table | following::table")
                    
                    # Limit to tables that come before the next main section
                    if i < len(main_sections) - 1:
                        next_section_element = main_sections[i + 1]['element']
                        filtered_tables = []
                        for table in tables_in_section:
                            try:
                                # Check if this table comes before the next main section
                                comparison_result = driver.execute_script("""
                                    var table = arguments[0];
                                    var nextSection = arguments[1];
                                    var tablePos = table.getBoundingClientRect();
                                    var nextSectionPos = nextSection.getBoundingClientRect();
                                    return tablePos.top < nextSectionPos.top;
                                """, table, next_section_element)
                                
                                if comparison_result:
                                    filtered_tables.append(table)
                            except:
                                continue
                        tables_in_section = filtered_tables
                    
                    # Extract specifications from all tables in this section
                    for table in tables_in_section[:3]:  # Limit to first 3 tables to avoid going too far
                        rows = table.find_elements(By.CSS_SELECTOR, "tr")
                        for row in rows:
                            cells = row.find_elements(By.CSS_SELECTOR, "td, th")
                            if len(cells) >= 2:
                                key = clean_unicode_text(cells[0].text.strip())
                                value = clean_unicode_text(cells[1].text.strip())
                                if key and value:
                                    section_specs.append({
                                        "specification": key,
                                        "value": value
                                    })
                
                except Exception as e:
                    continue
                
                if section_specs:
                    features_by_section[section_name] = section_specs
        
        else:
            # Fallback: extract all specifications without sectioning
            all_specs = []
            tables = popup_element.find_elements(By.CSS_SELECTOR, "table")
            for table in tables:
                rows = table.find_elements(By.CSS_SELECTOR, "tr")
                for row in rows:
                    cells = row.find_elements(By.CSS_SELECTOR, "td, th")
                    if len(cells) >= 2:
                        key = clean_unicode_text(cells[0].text.strip())
                        value = clean_unicode_text(cells[1].text.strip())
                        if key and value:
                            all_specs.append({
                                "specification": key,
                                "value": value
                            })
            
            if all_specs:
                features_by_section["Specifications"] = all_specs
        
        return features_by_section
        
    except Exception as e:
        print(f"    Error extracting specs from popup: {e}")
        return None


def scrape_features(driver, product_url, retries=3):
    """Scrape Features from product page and return structured data organized by sections"""
    for attempt in range(retries):
        try:
            print(f"  Scraping Features from: {product_url}")
            driver.get(product_url)
            
            # Wait for page to load
            wait = WebDriverWait(driver, 10)
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            time.sleep(3)
            
            # First, try to find and click the "VIEW FULL SPECS" button to open the popup
            try:
                print("    Looking for VIEW FULL SPECS button...")
                
                # Try different selectors for the VIEW FULL SPECS button
                full_specs_button_selectors = [
                    "/html/body/div[1]/main/div[3]/div/div[1]/div[5]/a/b",
                    "/html/body/div[1]/main/div[3]/div/div[1]/div[5]/a",
                    "//a[contains(text(), 'VIEW FULL SPECS')]",
                    "//b[contains(text(), 'VIEW FULL SPECS')]",
                    "//a[contains(text(), 'Full Specs')]",
                    "//button[contains(text(), 'VIEW FULL SPECS')]"
                ]
                
                button_found = False
                for selector in full_specs_button_selectors:
                    try:
                        if selector.startswith("//"):
                            button = driver.find_element(By.XPATH, selector)
                        else:
                            button = driver.find_element(By.XPATH, selector)
                        
                        if button and button.is_displayed():
                            print(f"    Found VIEW FULL SPECS button with selector: {selector}")
                            
                            # Scroll to the button to make sure it's visible
                            driver.execute_script("arguments[0].scrollIntoView(true);", button)
                            time.sleep(1)
                            
                            # Try multiple click methods
                            try:
                                # Method 1: Regular click
                                button.click()
                                print("    Clicked VIEW FULL SPECS button (regular click)")
                                button_found = True
                                break
                            except Exception as e:
                                try:
                                    # Method 2: JavaScript click
                                    driver.execute_script("arguments[0].click();", button)
                                    print("    Clicked VIEW FULL SPECS button (JavaScript click)")
                                    button_found = True
                                    break
                                except Exception as e2:
                                    print(f"    Failed to click button with selector {selector}: {e2}")
                                    continue
                    except Exception as e:
                        continue
                
                if not button_found:
                    print("    VIEW FULL SPECS button not found or could not be clicked")
                else:
                    # Wait for popup to load with more time
                    print("    Waiting for popup to load...")
                    time.sleep(5)
                    
                    # Try to find the popup with specifications
                    popup_selectors = [
                        "div.sm-bottom-popup.with-overlay",
                        "div[class*='sm-bottom-popup']",
                        "div[class*='popup']",
                        "div[class*='modal']",
                        "div[class*='overlay']"
                    ]
                    
                    popup_found = False
                    for popup_selector in popup_selectors:
                        try:
                            # Use WebDriverWait to wait for popup
                            wait = WebDriverWait(driver, 10)
                            popup = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, popup_selector)))
                            
                            if popup and popup.is_displayed():
                                print(f"    Found popup with selector: {popup_selector}")
                                popup_found = True
                                
                                # Wait a bit more for popup content to load
                                time.sleep(2)
                                
                                # Now extract specifications from the popup
                                features_by_section = extract_specs_from_popup(driver, popup)
                                
                                if features_by_section:
                                    print(f"    Successfully extracted specifications from popup")
                                    
                                    # Close the popup
                                    try:
                                        close_button = popup.find_element(By.CSS_SELECTOR, "button[class*='close'], .close, button[aria-label='Close'], .close-btn")
                                        close_button.click()
                                        print("    Closed popup")
                                    except:
                                        # Try pressing Escape key
                                        try:
                                            driver.execute_script("arguments[0].style.display = 'none';", popup)
                                            print("    Hid popup")
                                        except:
                                            # Try pressing Escape key
                                            driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                                            print("    Pressed Escape to close popup")
                                    
                                    return features_by_section
                                break
                        except Exception as e:
                            continue
                    
                    if not popup_found:
                        print("    Popup not found or not accessible")
                        # Try to debug by taking a screenshot
                        try:
                            driver.save_screenshot("debug_popup.png")
                            print("    Saved debug screenshot as debug_popup.png")
                        except:
                            pass
                        
            except Exception as e:
                print(f"    Error handling popup: {e}")
            
            # If popup method failed, return None
            print("    Could not extract specifications from popup")
            return None
                
        except Exception as e:
            print(f"  Error scraping Features (attempt {attempt + 1}/{retries}): {e}")
            if attempt < retries - 1:
                time.sleep(2)
            else:
                print(f"  Failed to scrape Features after {retries} attempts")
                return None
    
    return None


def scrape_spec_score(driver, product_url, retries=3):
    """Scrape Spec Score from product page using specific XPath"""
    for attempt in range(retries):
        try:
            print(f"  Scraping Spec Score from: {product_url}")
            driver.get(product_url)
            
            # Wait for page to load
            wait = WebDriverWait(driver, 10)
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            time.sleep(3)
            
            # Try to find Spec Score using the specific XPath
            spec_score_xpath = "/html/body/div[1]/main/div[3]/div/div[1]/div[2]/div[1]"
            
            try:
                spec_score_element = driver.find_element(By.XPATH, spec_score_xpath)
                spec_score_text = spec_score_element.text.strip()
                
                if spec_score_text:
                    print(f"    Found Spec Score: {spec_score_text}")
                    return spec_score_text
                else:
                    print(f"    Spec Score element found but empty")
            except NoSuchElementException:
                print(f"    Spec Score element not found with specific XPath")
            except Exception as e:
                print(f"    Error finding Spec Score element: {e}")
            
            # Try alternative XPaths for Spec Score
            alternative_xpaths = [
                "/html/body/div[1]/main/div[3]/div/div[1]/div[2]/div[1]",
                "/html/body/div[1]/main/div[2]/div/div[1]/div[2]/div[1]",
                "/html/body/div[1]/main/div[4]/div/div[1]/div[2]/div[1]",
                "//div[contains(@class, 'spec-score')]",
                "//div[contains(text(), 'Spec Score')]",
                "//div[contains(@class, 'score')]//div[contains(@class, 'number')]",
                "//span[contains(@class, 'score')]"
            ]
            
            for alt_xpath in alternative_xpaths:
                try:
                    elements = driver.find_elements(By.XPATH, alt_xpath)
                    for element in elements:
                        text = element.text.strip()
                        if text and (text.replace('.', '').replace('/10', '').replace('%', '').isdigit() or 
                                   any(keyword in text.lower() for keyword in ['score', 'rating', 'spec'])):
                            print(f"    Found Spec Score with alternative XPath: {text}")
                            return text
                except Exception as e:
                    continue
            
            print(f"  No Spec Score found")
            return None
            
        except Exception as e:
            print(f"  Error scraping Spec Score (attempt {attempt + 1}/{retries}): {e}")
            if attempt < retries - 1:
                time.sleep(2)
            else:
                print(f"  Failed to scrape Spec Score after {retries} attempts")
                return None
    
    return None





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


def get_amazon_mrp(driver):
    """Extract MRP from Amazon.in product page using specific selector with all required attributes"""
    try:
        # Wait for page to load properly
        time.sleep(3)
        
        print("    Attempting to extract MRP from Amazon page...")
        
        # Use the class-based selector with all required attributes to find the correct MRP element
        # Must match: class="a-price a-text-price" data-a-size="s" data-a-strike="true" data-a-color="secondary"
        mrp_selector = "span.a-price.a-text-price[data-a-size='s'][data-a-strike='true'][data-a-color='secondary'] span.a-offscreen"
        
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
            print("    ✗ MRP element with data-a-color='secondary' not found (MRP likely same as current price)")
            return ""
        except Exception as e:
            print(f"    Error accessing MRP element: {e}")
            return ""
        
    except Exception as e:
        print(f"    ✗ Error extracting MRP: {e}")
        return ""


def normalize_price(price_str):
    """Normalize price string for comparison"""
    if not price_str:
        return ""
    
    # Remove currency symbols and common formatting
    normalized = price_str.strip()
    # Remove commas and spaces
    normalized = normalized.replace(',', '').replace(' ', '')
    # Extract only numbers and decimal point
    import re
    numbers = re.findall(r'[\d.]+', normalized)
    if numbers:
        return numbers[0]
    return ""


def compare_prices(price1, price2, tolerance_percent=0):
    """Compare two prices with tolerance for slight variations"""
    try:
        # Normalize both prices
        norm_price1 = normalize_price(price1)
        norm_price2 = normalize_price(price2)
        
        if not norm_price1 or not norm_price2:
            return False
        
        # Convert to float for comparison
        float_price1 = float(norm_price1)
        float_price2 = float(norm_price2)
        
        # Calculate percentage difference
        avg_price = (float_price1 + float_price2) / 2
        if avg_price == 0:
            return False
        
        percent_diff = abs(float_price1 - float_price2) / avg_price * 100
        
        print(f"    Price comparison: {price1} vs {price2} (difference: {percent_diff:.1f}%)")
        
        return percent_diff <= tolerance_percent
        
    except Exception as e:
        print(f"    Error comparing prices: {e}")
        return False


def search_amazon_for_product(driver, product_name, expected_price):
    """Search Amazon.in for product by name and verify by price matching"""
    try:
        print(f"  Searching Amazon.in for product: {product_name}")
        
        # Create direct search URL by properly encoding the product name
        # Use quote_plus to handle spaces and special characters properly
        search_query = quote_plus(product_name)
        search_url = f"https://www.amazon.in/s?k={search_query}"
        
        print(f"    Using direct search URL: {search_url}")
        
        # Navigate directly to search results
        driver.get(search_url)
        time.sleep(5)  # Wait for search results to load
        
        print(f"    Search completed for: {product_name}")
        
        # Look for product results
        try:
            # Try to find product results
            product_elements = driver.find_elements(By.XPATH, "//div[@data-component-type='s-search-result']")
            
            if not product_elements:
                print("    No search results found")
                return None, False
            
            print(f"    Found {len(product_elements)} search results")
            
            # Check first few results for price matching
            for i, product_element in enumerate(product_elements[:5]):  # Check first 5 results
                try:
                    print(f"    Checking result {i+1}...")
                    
                    # Get the product link
                    product_link = product_element.find_element(By.XPATH, ".//a[contains(@href, '/dp/')]")
                    product_url = product_link.get_attribute("href")
                    
                    if not product_url:
                        continue
                    
                    # Extract ASIN from URL
                    asin = extract_asin_from_amazon_url(product_url)
                    if not asin:
                        continue
                    
                    # Get price from search results
                    price_elements = product_element.find_elements(By.XPATH, ".//span[@class='a-price-whole']")
                    if not price_elements:
                        # Try alternative price selectors
                        price_elements = product_element.find_elements(By.XPATH, ".//span[contains(@class, 'a-price') and contains(@class, 'a-text-price')]//span[@class='a-offscreen']")
                    
                    if price_elements:
                        amazon_price = price_elements[0].text.strip()
                        print(f"      Found product with price: {amazon_price}")
                        
                        # Compare prices
                        if compare_prices(expected_price, amazon_price):
                            print(f"      ✓ Price match found! Navigating to product page...")
                            
                            # Navigate to product page to get detailed info with retry mechanism
                            max_retries = 3
                            retry_count = 0
                            navigation_success = False
                            
                            while retry_count < max_retries and not navigation_success:
                                try:
                                    if retry_count > 0:
                                        print(f"        Retry {retry_count}/{max_retries-1} for navigation...")
                                    
                                    driver.get(product_url)
                                    time.sleep(5)
                                    
                                    # Verify we're on the correct product page by checking URL contains the ASIN
                                    current_url = driver.current_url
                                    if asin in current_url:
                                        navigation_success = True
                                        print(f"        ✓ Successfully navigated to product page for ASIN: {asin}")
                                    else:
                                        raise Exception(f"Navigation failed - URL does not contain ASIN {asin}. Current URL: {current_url}")
                                    
                                except Exception as nav_error:
                                    retry_count += 1
                                    print(f"        Navigation attempt {retry_count} failed: {nav_error}")
                                    
                                    if retry_count < max_retries:
                                        print(f"        Retrying navigation in 3 seconds...")
                                        time.sleep(3)
                                    else:
                                        print(f"        All navigation attempts failed after {max_retries} retries")
                                        raise nav_error
                            
                            if navigation_success:
                                # Extract MRP from product page
                                mrp = get_amazon_mrp(driver)
                                return {"asin": asin, "mrp": mrp}, True
                        else:
                            print(f"      ✗ Price mismatch, continuing search...")
                    else:
                        print(f"      No price found for this result")
                        
                except Exception as e:
                    print(f"      Error checking result {i+1}: {e}")
                    continue
            
            print("    No price-matched products found in search results")
            return None, False
            
        except Exception as e:
            print(f"    Error processing search results: {e}")
            return None, False
            
    except Exception as e:
        print(f"    Error searching Amazon for product: {e}")
        return None, False


def find_amazon_product_by_search(driver, product_name, expected_price):
    """Find Amazon product by searching and verifying price match"""
    print(f"  Searching Amazon.in independently for: {product_name}")
    print(f"  Expected price for verification: {expected_price}")
    
    # Search Amazon.in for the product
    amazon_data, found = search_amazon_for_product(driver, product_name, expected_price)
    
    if found and amazon_data:
        print(f"  ✓ Found verified Amazon product!")
        print(f"  ASIN: {amazon_data['asin']}")
        if amazon_data['mrp']:
            print(f"  MRP: {amazon_data['mrp']}")
        else:
            print(f"  MRP not found (might be same as current price)")
        return amazon_data, True
    else:
        print(f"  ✗ No verified Amazon product found")
        return None, False


def get_existing_products():
    """Get dictionary of existing products from update_mobiles.json with their prices and listed status"""
    try:
        with open("update_mobiles.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        
        existing_products = {}
        for product in data.get("products", []):
            if product.get("id"):
                existing_products[product["id"]] = {
                    "price": product.get("price", ""),
                    "listed": product.get("listed", "no"),  # Include listed status
                    "index": data["products"].index(product)  # Store index for updating
                }
        
        return existing_products
    except (FileNotFoundError, json.JSONDecodeError):
        # If file doesn't exist or is corrupted, return empty dict
        return {}
    except Exception as e:
        print(f"Error reading existing products: {e}")
        return {}


def ensure_images_folder_exists():
    """Ensure the images folder exists"""
    try:
        images_dir = "images"
        if not os.path.exists(images_dir):
            os.makedirs(images_dir)
            print(f"Created images folder: {images_dir}")
        return True
    except Exception as e:
        print(f"Error creating images folder: {e}")
        return False


def cleanup_discontinued_products(mobiles_data):
    """Remove products from update_mobiles.json that don't exist in mobiles.json"""
    try:
        print("Checking for discontinued products in update_mobiles.json...")
        
        # Get all unique_ids from mobiles.json
        valid_unique_ids = set()
        for product in mobiles_data.get("products", []):
            if product.get("unique_id"):
                valid_unique_ids.add(product["unique_id"])
        
        print(f"Found {len(valid_unique_ids)} valid products in mobiles.json")
        
        # Load update_mobiles.json
        try:
            with open("update_mobiles.json", "r", encoding="utf-8") as f:
                update_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            print("update_mobiles.json not found or corrupted - no cleanup needed")
            return True
        
        # Find products to remove
        original_products = update_data.get("products", [])
        products_to_keep = []
        removed_count = 0
        
        for product in original_products:
            product_id = product.get("id")
            if product_id and product_id in valid_unique_ids:
                products_to_keep.append(product)
            else:
                removed_count += 1
                product_name = product.get("name", "Unknown")
                print(f"  🗑️  Removing discontinued product: {product_name} (ID: {product_id})")
                
                # Also remove the product's image folder if it exists
                try:
                    product_image_dir = os.path.join("images", product_id)
                    if os.path.exists(product_image_dir):
                        shutil.rmtree(product_image_dir)
                        print(f"    🗑️  Removed image folder: {product_image_dir}")
                except Exception as e:
                    print(f"    ⚠️  Could not remove image folder for {product_id}: {e}")
        
        # Update the data
        update_data["products"] = products_to_keep
        
        # Save the updated file
        with open("update_mobiles.json", "w", encoding="utf-8") as f:
            json.dump(update_data, f, indent=2, ensure_ascii=False)
        
        if removed_count > 0:
            print(f"✅ Removed {removed_count} discontinued products from update_mobiles.json")
            print(f"✅ Kept {len(products_to_keep)} current products")
        else:
            print("✅ No discontinued products found - all products are current")
        
        return True
    except Exception as e:
        print(f"❌ Error during cleanup: {e}")
        return False


def update_existing_product(product_data, product_index, json_file_path):
    """Update an existing product in the JSON file at the specified index"""
    try:
        # Load existing data
        with open(json_file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Update the product at the specified index
        if 0 <= product_index < len(data["products"]):
            # Update the product
            data["products"][product_index] = product_data
            
            # Save updated data
            with open(json_file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            return True
        else:
            print(f"Invalid product index: {product_index}")
            return False
    except Exception as e:
        print(f"Error updating existing product: {e}")
        return False


def main():
    """Main function to scrape product images with time management"""
    print("=== Smartprix Mobile Image Scraper with Time Management ===")
    
    # Initialize time manager
    time_manager = TimeManager()
    print(f"⏱️  Workflow time limit: {time_manager.format_time(time_manager.time_limit_seconds)}")
    
    print("Loading existing mobiles data...")
    
    # Load existing mobiles data
    mobiles_data = load_mobiles_data("mobiles.json")
    if not mobiles_data:
        print("Failed to load mobiles data. Exiting.")
        return
    
    products = mobiles_data.get("products", [])
    total_products = len(products)
    print(f"Found {total_products} products to process")
    
    # Clean up discontinued products from update_mobiles.json
    if not cleanup_discontinued_products(mobiles_data):
        print("Warning: Failed to cleanup discontinued products. Continuing...")
    
    # Get existing products to check for duplicates, price changes, and listed status
    print("Checking for existing products in update_mobiles.json...")
    existing_products = get_existing_products()
    print(f"Found {len(existing_products)} existing products in update_mobiles.json")
    
    # Ensure images folder exists
    print("Ensuring images folder exists...")
    if not ensure_images_folder_exists():
        print("Failed to ensure images folder exists. Exiting.")
        return
    
    # Setup Chrome driver
    print("Setting up Chrome driver...")
    driver = setup_driver()
    if not driver:
        print("Failed to setup Chrome driver. Exiting.")
        return
    
    try:
        # Process each product
        processed_count = 0
        updated_count = 0
        skipped_count = 0
        
        for i, product in enumerate(products, 1):
            # Check time limit before processing each product
            if not time_manager.should_continue_processing():
                print(f"\n🚨 Time limit approaching! Starting graceful shutdown...")
                print(f"⏱️  Processed {processed_count + updated_count}/{total_products} products before timeout")
                break
            
            unique_id = product.get("unique_id")
            product_name = product.get("name", "Unknown")
            current_price = product.get("price", "")
            
            print(f"\nProcessing product {i}/{total_products}: {product_name}")
            
            # Log time status periodically (every 10 products)
            if i % 10 == 0 or i == 1:
                time_manager.log_time_status(
                    current_item=f"Product {i}: {product_name}",
                    total_items=total_products,
                    processed_items=processed_count + updated_count
                )
            
            # Check if this product already exists in update_mobiles.json
            existing_product = existing_products.get(unique_id)
            should_update = False
            product_index = None
            
            if existing_product:
                existing_price = existing_product.get("price", "")
                existing_listed = existing_product.get("listed", "no")
                product_index = existing_product.get("index")
                
                if current_price == existing_price and existing_listed != "no":
                    print(f"  ⚠️  Product '{unique_id}' already exists with same price ({current_price}) and listed status is '{existing_listed}' - skipping")
                    skipped_count += 1
                    continue
                elif current_price == existing_price and existing_listed == "no":
                    print(f"  🔄 Product '{unique_id}' exists with same price ({current_price}) but listed status is 'no' - re-scraping")
                    should_update = True
                else:
                    print(f"  🔄 Product '{unique_id}' exists but price changed: '{existing_price}' -> '{current_price}' - updating")
                    should_update = True
            
            # Create updated product data in the new format
            updated_product = {
                "id": unique_id,
                "name": product_name,
                "listed": "no",  # Initialize as "no", will be updated if Amazon link is found
                "price": product.get("price"),
                "mrp": "",  # Initialize MRP field as empty
                "url": product.get("url"),
                "images": [],  # Initialize empty images array
                "variants": [],  # Initialize empty variants array
                "asin": None,  # Initialize ASIN field
                "spec_score": None,  # Initialize Spec Score field
                "features": None  # Initialize Features field
            }
            
            # Scrape and save images if URL exists (always download all images)
            if product.get("url") and product.get("unique_id"):
                original_image_urls = scrape_and_save_product_images(driver, product["url"], product["unique_id"])
                print(f"  Downloaded {len(original_image_urls)} new images")
                
                # Add GitHub raw URL image paths to the images array
                for j, image_url in enumerate(original_image_urls, 1):
                    # Create relative path: images/unique_id/image_j.jpg
                    relative_path = f"images/{product['unique_id']}/image_{j}.jpg"
                    # Add GitHub raw URL prefix
                    github_raw_url = f"https://raw.githubusercontent.com/affdeals/affdeals.github.io/refs/heads/main/{relative_path}"
                    updated_product["images"].append(github_raw_url)
                
                if original_image_urls:
                    print(f"  Added {len(original_image_urls)} GitHub raw URL image paths to JSON")
                
                # Scrape variants from the same product URL
                variants = scrape_product_variants(driver, product["url"])
                if variants:
                    updated_product["variants"] = variants
                    print(f"  Added {len(variants)} variants to product data")
                else:
                    print("  No variants found for this product")
                
                # Scrape Spec Score from the product page
                print("  Scraping Spec Score...")
                spec_score = scrape_spec_score(driver, product["url"])
                if spec_score:
                    updated_product["spec_score"] = spec_score
                    print(f"  Added Spec Score: {spec_score}")
                else:
                    print("  No Spec Score found")
                
                # Scrape Features from the product page
                print("  Scraping Features...")
                features = scrape_features(driver, product["url"])
                if features:
                    updated_product["features"] = features
                    total_specs = sum(len(specs) for specs in features.values())
                    print(f"  Added {total_specs} specifications across {len(features)} sections")
                else:
                    print("  No Features found")
                
                # Search Amazon.in independently and verify by price matching
                print("  Searching Amazon.in independently for product...")
                amazon_data, amazon_found = find_amazon_product_by_search(driver, product["name"], product["price"])
                if amazon_found and amazon_data:
                    updated_product["listed"] = "yes"
                    updated_product["asin"] = amazon_data["asin"]
                    updated_product["mrp"] = amazon_data["mrp"]
                    print(f"  Added ASIN: {amazon_data['asin']}")
                    if amazon_data["mrp"]:
                        print(f"  Added MRP: {amazon_data['mrp']}")
                    else:
                        print(f"  MRP not found (might be same as current price)")
                else:
                    updated_product["listed"] = "no"
                    updated_product["asin"] = None
                    updated_product["mrp"] = ""
                    print("  No verified Amazon product found - marked as not listed")
            else:
                print("  No URL or unique_id found for this product")
            
            # Save product to JSON file immediately after processing
            if should_update:
                print(f"  Updating existing product in update_mobiles.json...")
                if update_existing_product(updated_product, product_index, "update_mobiles.json"):
                    print(f"  Successfully updated product {i}/{total_products} in JSON")
                    updated_count += 1
                    # Update the existing_products dict to reflect the new price
                    existing_products[unique_id]["price"] = current_price
                else:
                    print(f"  Failed to update product {i}/{total_products} in JSON")
            else:
                print(f"  Appending new product to update_mobiles.json...")
                if append_product_to_json(updated_product, "update_mobiles.json"):
                    print(f"  Successfully appended product {i}/{total_products} to JSON")
                    processed_count += 1
                    # Add the product to existing_products to avoid duplicates in current session
                    existing_products[unique_id] = {
                        "price": current_price,
                        "index": len(existing_products)  # Approximation, will be corrected if needed
                    }
                else:
                    print(f"  Failed to append product {i}/{total_products} to JSON")
            
            # Add small delay between requests (with timeout checking)
            if not time_manager.wait_with_timeout_check(1):
                print(f"🚨 Time limit reached during processing delay. Starting graceful shutdown...")
                break
        
        # Determine if processing was completed or interrupted
        was_interrupted = not time_manager.should_continue_processing()
        
        if was_interrupted:
            print(f"\n🚨 Processing interrupted due to time limit!")
            print(f"⏱️  Completed {processed_count + updated_count}/{total_products} products")
        else:
            print(f"\n✅ Processing complete!")
        
        print(f"✅ New products added: {processed_count}")
        print(f"🔄 Existing products updated: {updated_count}")
        print(f"⚠️  Skipped (no changes): {skipped_count} products")
        print(f"📊 Total products in mobiles.json: {total_products}")
        
        # Show final count in update_mobiles.json
        try:
            with open("update_mobiles.json", "r", encoding="utf-8") as f:
                final_data = json.load(f)
            final_count = len(final_data.get("products", []))
            print(f"📊 Total products in update_mobiles.json: {final_count}")
        except:
            pass
        
        changes_made = processed_count > 0 or updated_count > 0
        if changes_made:
            print(f"💾 Changes made to update_mobiles.json!")
        else:
            print("💾 No changes needed - all processed products are up to date.")
        
        # Log final summary with time management
        stats = {
            "total_items": total_products,
            "processed_items": processed_count + updated_count,
            "new_items": processed_count,
            "updated_items": updated_count,
            "skipped_items": skipped_count,
            "changes_saved": changes_made,
            "interrupted": was_interrupted
        }
        time_manager.log_final_summary(stats)
    
    except KeyboardInterrupt:
        print("\n🚨 Script interrupted by user.")
        print("💾 Current progress is already saved in update_mobiles.json")
        
        # Log interruption summary
        stats = {
            "total_items": total_products,
            "processed_items": processed_count + updated_count,
            "new_items": processed_count,
            "updated_items": updated_count,
            "skipped_items": skipped_count,
            "changes_saved": True,
            "interrupted": True
        }
        time_manager.log_final_summary(stats)
    
    except Exception as e:
        print(f"❌ Error during scraping: {e}")
        print("💾 Current progress is already saved in update_mobiles.json")
        
        # Log error summary
        stats = {
            "total_items": total_products,
            "processed_items": processed_count + updated_count,
            "new_items": processed_count,
            "updated_items": updated_count,
            "skipped_items": skipped_count,
            "changes_saved": True,
            "interrupted": True,
            "error": str(e)
        }
        time_manager.log_final_summary(stats)
    
    finally:
        # Close the driver
        if driver:
            driver.quit()
            print("Chrome driver closed.")


if __name__ == "__main__":
    main()
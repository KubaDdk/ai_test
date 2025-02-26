"""
Selenium-based website crawler for analyzing web pages and identifying interactive elements.
"""

import time
import logging
from typing import List, Dict, Any, Optional, Set
import urllib.parse

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager

from ..utils.config import Config
from .element_parser import ElementParser

logger = logging.getLogger(__name__)

class SeleniumCrawler:
    """
    A crawler that uses Selenium to navigate websites and extract interactive elements.
    """
    
    def __init__(self, config: Config):
        """
        Initialize the crawler with configuration settings.
        
        Args:
            config: Configuration object containing crawler settings
        """
        self.config = config
        self.driver = None
        self.element_parser = ElementParser(config)
        self.visited_urls = set()
        self.queue = []
        self.base_url = ""
        self.domain = ""
    
    def setup_driver(self):
        """
        Set up the Selenium WebDriver with appropriate options.
        """
        chrome_options = Options()
        
        if self.config.get('crawler.headless', True):
            chrome_options.add_argument("--headless")
        
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-notifications")
        chrome_options.add_argument("--disable-popup-blocking")
        chrome_options.add_argument("--disable-extensions")
        
        # Add user agent to mimic real browser
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Set page load timeout
        self.driver.set_page_load_timeout(self.config.get('crawler.page_load_timeout', 30))
    
    def extract_domain(self, url: str) -> str:
        """
        Extract the domain from a URL.
        
        Args:
            url: The URL to extract domain from
            
        Returns:
            The domain name
        """
        parsed_url = urllib.parse.urlparse(url)
        return parsed_url.netloc
    
    def should_crawl_url(self, url: str) -> bool:
        """
        Determine if a URL should be crawled based on domain and crawl rules.
        
        Args:
            url: The URL to evaluate
            
        Returns:
            True if the URL should be crawled, False otherwise
        """
        # Skip URLs that have already been visited
        if url in self.visited_urls:
            return False
        
        # Skip URLs that don't have the same domain (avoid external links)
        if self.domain not in self.extract_domain(url):
            return False
        
        # Skip non-HTTP URLs (like mailto:, tel:, etc.)
        if not url.startswith(('http://', 'https://')):
            return False
        
        # Skip URLs with file extensions that don't need to be crawled
        excluded_extensions = ['.pdf', '.jpg', '.jpeg', '.png', '.gif', '.css', '.js', '.ico']
        if any(url.lower().endswith(ext) for ext in excluded_extensions):
            return False
        
        return True
    
    def start_crawl(self, start_url: str) -> List[Dict[str, Any]]:
        """
        Start crawling from a given URL.
        
        Args:
            start_url: The starting URL for crawling
            
        Returns:
            A list of dictionaries containing information about interactive elements
        """
        self.base_url = start_url
        self.domain = self.extract_domain(start_url)
        self.visited_urls = set()
        self.queue = [start_url]
        
        try:
            self.setup_driver()
            
            max_pages = self.config.get('crawler.max_pages', 20)
            max_depth = self.config.get('crawler.max_depth', 2)
            wait_time = self.config.get('crawler.wait_time', 3)
            
            all_elements_data = []
            current_depth = 0
            pages_visited = 0
            
            # Dictionary to track URLs at each depth level
            depth_urls = {0: [start_url]}
            
            while self.queue and pages_visited < max_pages and current_depth <= max_depth:
                # Process all URLs at the current depth
                urls_at_current_depth = depth_urls.get(current_depth, [])
                depth_urls[current_depth + 1] = []
                
                for url in urls_at_current_depth:
                    if url in self.visited_urls or not self.should_crawl_url(url):
                        continue
                    
                    logger.info(f"Crawling: {url}")
                    
                    try:
                        self.driver.get(url)
                        self.visited_urls.add(url)
                        pages_visited += 1
                        
                        # Wait for page to load
                        time.sleep(wait_time)
                        
                        # Extract elements from the page
                        elements_data = self.element_parser.extract_elements(self.driver, url)
                        all_elements_data.extend(elements_data)
                        
                        # Find links to other pages
                        links = self.driver.find_elements(By.TAG_NAME, "a")
                        for link in links:
                            try:
                                href = link.get_attribute("href")
                                if href and self.should_crawl_url(href):
                                    depth_urls[current_depth + 1].append(href)
                            except Exception as e:
                                logger.warning(f"Error extracting href from link: {e}")
                    
                    except TimeoutException:
                        logger.warning(f"Timeout while loading {url}")
                    except WebDriverException as e:
                        logger.warning(f"WebDriver error while crawling {url}: {e}")
                    except Exception as e:
                        logger.error(f"Unexpected error while crawling {url}: {e}")
                
                # Move to next depth level
                current_depth += 1
            
            logger.info(f"Crawling complete. Visited {pages_visited} pages, found {len(all_elements_data)} interactive elements.")
            return all_elements_data
            
        finally:
            if self.driver:
                self.driver.quit()
    
    def get_single_page_elements(self, url: str) -> List[Dict[str, Any]]:
        """
        Extract interactive elements from a single page without crawling further.
        
        Args:
            url: The URL to analyze
            
        Returns:
            A list of dictionaries containing information about interactive elements
        """
        try:
            self.setup_driver()
            
            wait_time = self.config.get('crawler.wait_time', 3)
            
            logger.info(f"Analyzing single page: {url}")
            
            self.driver.get(url)
            time.sleep(wait_time)
            
            elements_data = self.element_parser.extract_elements(self.driver, url)
            
            logger.info(f"Analysis complete. Found {len(elements_data)} interactive elements.")
            return elements_data
            
        finally:
            if self.driver:
                self.driver.quit()
"""
Module for parsing and extracting information from web page elements.
"""

import logging
from typing import List, Dict, Any, Optional
import json
import base64
import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import StaleElementReferenceException

from ..utils.config import Config

logger = logging.getLogger(__name__)

class ElementParser:
    """
    Parser for extracting and categorizing interactive elements from web pages.
    """
    
    def __init__(self, config: Config):
        """
        Initialize the element parser with configuration settings.
        
        Args:
            config: Configuration object containing parser settings
        """
        self.config = config
        self.element_selectors = config.get('crawler.elements_to_find', [
            'a', 'button', 'input', 'select', 'textarea',
            "[role='button']", "[role='link']", "[role='checkbox']", "[role='radio']"
        ])
        
        # Get attributes to extract from the configuration
        self.attrs_to_extract = config.get('crawler.attributes_to_extract', [
            'id', 'class', 'name', 'type', 'href', 'value', 'placeholder', 
            'role', 'aria-label', 'title', 'data-testid'
        ])
        
        # Flag to determine if screenshots should be taken
        self.take_screenshots = config.get('crawler.take_screenshots', False)
    
    def extract_elements(self, driver: webdriver.Chrome, page_url: str) -> List[Dict[str, Any]]:
        """
        Extract interactive elements from the current page.
        
        Args:
            driver: Selenium WebDriver instance
            page_url: URL of the current page
            
        Returns:
            A list of dictionaries containing element information
        """
        elements_data = []
        page_title = driver.title
        
        # Extract elements using configured selectors
        for selector in self.element_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                logger.debug(f"Found {len(elements)} elements matching selector: {selector}")
                
                for element in elements:
                    element_data = self._extract_element_data(element, page_url, page_title)
                    if element_data:
                        elements_data.append(element_data)
            
            except Exception as e:
                logger.warning(f"Error finding elements with selector {selector}: {e}")
        
        return elements_data
    
    def _extract_element_data(self, element: WebElement, page_url: str, page_title: str) -> Optional[Dict[str, Any]]:
        """
        Extract data from a single web element.
        
        Args:
            element: Selenium WebElement to extract data from
            page_url: URL of the current page
            page_title: Title of the current page
            
        Returns:
            Dictionary containing element information or None if extraction failed
        """
        try:
            # Skip elements that are not displayed or enabled if configured to do so
            if (self.config.get('crawler.skip_hidden_elements', True) and 
                    not element.is_displayed()):
                return None
            
            # Basic element info
            element_data = {
                "page_url": page_url,
                "page_title": page_title,
                "tag_name": element.tag_name,
                "text": element.text.strip() if element.text else "",
                "is_displayed": element.is_displayed(),
                "is_enabled": element.is_enabled() if element.tag_name != 'a' else True,
                "location": {
                    "x": element.location['x'],
                    "y": element.location['y']
                },
                "size": {
                    "width": element.size['width'],
                    "height": element.size['height']
                },
                "attributes": {}
            }
            
            # Extract relevant attributes
            for attr in self.attrs_to_extract:
                value = element.get_attribute(attr)
                if value:
                    element_data["attributes"][attr] = value
            
            # Categorize element type
            element_data["element_type"] = self._categorize_element(element)
            
            # Take screenshot if configured
            if self.take_screenshots and element.is_displayed():
                try:
                    screenshot = element.screenshot_as_base64
                    element_data["screenshot"] = screenshot
                except Exception as ss_err:
                    logger.debug(f"Could not take screenshot of element: {ss_err}")
            
            return element_data
            
        except StaleElementReferenceException:
            logger.debug("Element became stale during extraction")
            return None
        except Exception as e:
            logger.warning(f"Error extracting data from element: {e}")
            return None
    
    def _categorize_element(self, element: WebElement) -> str:
        """
        Categorize an element based on its type and attributes.
        
        Args:
            element: Selenium WebElement to categorize
            
        Returns:
            String representing the element category
        """
        tag_name = element.tag_name.lower()
        
        # Check for role attribute first
        role = element.get_attribute("role")
        if role:
            if role in ["button", "link", "checkbox", "radio", "tab", "menu", "menuitem", 
                       "combobox", "listbox", "option", "slider", "switch"]:
                return role
        
        # Then check for specific element types
        if tag_name == "a":
            return "link"
        elif tag_name == "button":
            return "button"
        elif tag_name == "input":
            input_type = element.get_attribute("type")
            if input_type in ["checkbox", "radio", "submit", "button"]:
                return input_type
            elif input_type in ["text", "email", "password", "number", "tel", "url", "search"]:
                return "input_field"
            else:
                return "input_" + (input_type or "text")
        elif tag_name == "select":
            return "dropdown"
        elif tag_name == "textarea":
            return "text_area"
        elif tag_name == "form":
            return "form"
        
        # Classify divs and spans with click handlers or that look interactive
        if tag_name in ["div", "span"]:
            class_attr = element.get_attribute("class") or ""
            if any(keyword in class_attr.lower() for keyword in ["button", "btn", "link", "clickable"]):
                return "pseudo_button"
        
        # Handle icons that might be interactive
        if tag_name in ["i", "svg", "img"]:
            parent = element.find_element(By.XPATH, "..")
            if parent.tag_name == "a":
                return "icon_link"
            else:
                return "icon"
        
        # Default classification
        return "other"
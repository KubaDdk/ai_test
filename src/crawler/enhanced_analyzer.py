"""
Enhanced HTML analyzer that can handle JavaScript-rendered pages using Selenium.
"""

import logging
import json
import time
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin
import re

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchElementException
from selenium.webdriver.remote.webelement import WebElement
from webdriver_manager.chrome import ChromeDriverManager

logger = logging.getLogger(__name__)

class EnhancedAnalyzer:
    """
    Enhanced analyzer that uses Selenium to analyze JavaScript-rendered pages.
    """
    
    def __init__(self, config=None):
        """
        Initialize the enhanced analyzer.
        
        Args:
            config: Optional configuration object or dictionary
        """
        self.config = config or {}
        self.driver = None
        
        # Define interactive element selectors
        self.interactive_selectors = self.config.get('analyzer.interactive_selectors', [
            'a', 'button', 'input', 'select', 'textarea', '[role="button"]', 
            '[role="link"]', '[role="checkbox"]', '[role="radio"]', '[role="tab"]'
        ])
    
    def setup_driver(self, headless=True):
        """
        Set up the Selenium WebDriver.
        
        Args:
            headless: Whether to run in headless mode
        """
        chrome_options = Options()
        
        if headless:
            chrome_options.add_argument("--headless")
        
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-notifications")
        chrome_options.add_argument("--disable-popup-blocking")
        
        # Add user agent to mimic real browser
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        
        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.set_page_load_timeout(30)
        except Exception as e:
            logger.error(f"Error setting up Chrome driver: {e}")
            # Try Firefox as a fallback
            try:
                from selenium.webdriver.firefox.options import Options as FirefoxOptions
                from selenium.webdriver.firefox.service import Service as FirefoxService
                from webdriver_manager.firefox import GeckoDriverManager
                
                firefox_options = FirefoxOptions()
                if headless:
                    firefox_options.add_argument("--headless")
                
                service = FirefoxService(GeckoDriverManager().install())
                self.driver = webdriver.Firefox(service=service, options=firefox_options)
                self.driver.set_page_load_timeout(30)
                logger.info("Using Firefox as fallback browser")
            except Exception as firefox_error:
                logger.error(f"Error setting up Firefox driver: {firefox_error}")
                raise Exception("Could not initialize any web driver")
    
    def get_page(self, url: str, wait_time: int = 3) -> Dict[str, Any]:
        """
        Load a page and wait for it to render.
        
        Args:
            url: URL to load
            wait_time: Time to wait for page to render
            
        Returns:
            Page information
        """
        if not self.driver:
            self.setup_driver()
        
        try:
            logger.info(f"Loading page: {url}")
            self.driver.get(url)
            time.sleep(wait_time)  # Wait for JavaScript to render
            
            page_info = {
                "url": url,
                "title": self.driver.title,
                "html": self.driver.page_source
            }
            
            return page_info
        except Exception as e:
            logger.error(f"Error loading page {url}: {e}")
            return {
                "url": url,
                "error": str(e),
                "html": ""
            }
    
    def find_interactive_elements(self) -> List[Dict[str, Any]]:
        """
        Find all interactive elements on the current page.
        
        Returns:
            List of element data dictionaries
        """
        elements_data = []
        for selector in self.interactive_selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                logger.debug(f"Found {len(elements)} elements matching selector: {selector}")
                
                for element in elements:
                    try:
                        element_data = self._extract_element_data(element)
                        if element_data:
                            elements_data.append(element_data)
                    except Exception as element_error:
                        logger.debug(f"Error extracting element data: {element_error}")
            except Exception as e:
                logger.warning(f"Error finding elements with selector {selector}: {e}")
        
        return elements_data
    
    def _extract_element_data(self, element: WebElement) -> Optional[Dict[str, Any]]:
        """
        Extract data from a WebElement.
        
        Args:
            element: Selenium WebElement
            
        Returns:
            Dictionary with element data or None if extraction failed
        """
        try:
            # Skip hidden elements
            if not element.is_displayed():
                return None
            
            # Get element attributes
            attributes = {}
            for attr in ['id', 'class', 'name', 'type', 'href', 'value', 'placeholder', 
                        'role', 'aria-label', 'data-test', 'data-testid']:
                value = element.get_attribute(attr)
                if value:
                    attributes[attr] = value
            
            # Basic element info
            element_data = {
                "tag_name": element.tag_name,
                "text": element.text.strip() if element.text else "",
                "is_displayed": element.is_displayed(),
                "is_enabled": element.is_enabled() if element.tag_name != 'a' else True,
                "location": {
                    "x": element.location['x'],
                    "y": element.location['y']
                },
                "attributes": attributes,
                "element_type": self._categorize_element(element),
                "css_selector": self._generate_css_selector(element)
            }
            
            # Determine possible actions
            element_data["actions"] = self._determine_possible_actions(element)
            
            return element_data
        except Exception as e:
            logger.debug(f"Error extracting element data: {e}")
            return None
    
    def _categorize_element(self, element: WebElement) -> str:
        """
        Categorize an element based on its type and attributes.
        
        Args:
            element: Selenium WebElement
            
        Returns:
            Element category string
        """
        tag_name = element.tag_name.lower()
        
        # Check for role attribute first
        role = element.get_attribute("role")
        if role and role in ["button", "link", "checkbox", "radio", "tab", "menuitem"]:
            return role
        
        # Check tag name
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
        
        # Check class name for common patterns
        class_attr = element.get_attribute("class") or ""
        if any(keyword in class_attr.lower() for keyword in ["button", "btn"]):
            return "pseudo_button"
        elif any(keyword in class_attr.lower() for keyword in ["dropdown", "select"]):
            return "pseudo_dropdown"
        
        return "other"
    
    def _determine_possible_actions(self, element: WebElement) -> List[Dict[str, Any]]:
        """
        Determine possible user actions for an element.
        
        Args:
            element: Selenium WebElement
            
        Returns:
            List of possible actions
        """
        actions = []
        element_type = self._categorize_element(element)
        
        if element_type in ["link", "button", "submit", "pseudo_button", "pseudo_dropdown"]:
            actions.append({
                "type": "click",
                "cypress": f"cy.get('{self._generate_css_selector(element)}').click()"
            })
        
        elif element_type in ["input_field", "text_area"]:
            placeholder = element.get_attribute("placeholder") or ""
            input_type = element.get_attribute("type") or ""
            
            sample_text = "Test input"
            if "email" in input_type.lower() or "email" in placeholder.lower():
                sample_text = "test@example.com"
            elif "password" in input_type.lower() or "password" in placeholder.lower():
                sample_text = "Password123"
            
            actions.append({
                "type": "input",
                "value": sample_text,
                "cypress": f"cy.get('{self._generate_css_selector(element)}').type('{sample_text}')"
            })
        
        elif element_type == "dropdown":
            actions.append({
                "type": "select",
                "cypress": f"cy.get('{self._generate_css_selector(element)}').select('OPTION_VALUE')"
            })
        
        elif element_type in ["checkbox", "radio"]:
            actions.append({
                "type": "check",
                "cypress": f"cy.get('{self._generate_css_selector(element)}').check()"
            })
        
        return actions
    
    def _generate_css_selector(self, element: WebElement) -> str:
        """
        Generate a CSS selector for the element that can be used in Cypress tests.
        
        Args:
            element: Selenium WebElement
            
        Returns:
            CSS selector string
        """
        # Try ID first (most reliable)
        element_id = element.get_attribute("id")
        if element_id:
            return f"#{element_id}"
        
        # Try data-test or data-testid (common for testing)
        data_test = element.get_attribute("data-test")
        if data_test:
            return f"[data-test='{data_test}']"
        
        data_testid = element.get_attribute("data-testid")
        if data_testid:
            return f"[data-testid='{data_testid}']"
        
        # Try name attribute
        name = element.get_attribute("name")
        if name:
            return f"{element.tag_name}[name='{name}']"
        
        # Try placeholder for input fields
        if element.tag_name in ["input", "textarea"]:
            placeholder = element.get_attribute("placeholder")
            if placeholder:
                return f"{element.tag_name}[placeholder='{placeholder}']"
        
        # Try class, but this is less reliable for unique identification
        class_name = element.get_attribute("class")
        if class_name:
            # Take just the first class to avoid overly complex selectors
            first_class = class_name.split()[0] if class_name.split() else ""
            if first_class and not first_class.startswith(('ng-', 'ui-')):
                return f"{element.tag_name}.{first_class}"
        
        # Fallback: element type and its text content if it has any
        text = element.text.strip()
        if text and len(text) < 50:  # Avoid very long text
            # Escape single quotes
            text = text.replace("'", "\\'")
            return f"{element.tag_name}:contains('{text}')"
        
        # Last resort: relative position
        return f"{element.tag_name}"
    
    def generate_user_flows(self, elements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Generate potential user flows from the elements.
        
        Args:
            elements: List of element data dictionaries
            
        Returns:
            List of user flow dictionaries
        """
        if not elements:
            return []
        
        # Group elements by type
        input_fields = [e for e in elements if e["element_type"] in ["input_field", "text_area"]]
        buttons = [e for e in elements if e["element_type"] in ["button", "submit"]]
        links = [e for e in elements if e["element_type"] == "link"]
        checkboxes = [e for e in elements if e["element_type"] == "checkbox"]
        
        flows = []
        
        # Try to identify login flow
        login_flow = self._identify_login_flow(input_fields, buttons)
        if login_flow:
            flows.append(login_flow)
        
        # Try to identify form submission flow
        form_flow = self._identify_form_flow(input_fields, buttons)
        if form_flow:
            flows.append(form_flow)
        
        # Navigation flow
        if links:
            nav_flow = {
                "name": "Navigation",
                "description": "Navigate through site links",
                "steps": []
            }
            
            # Add up to 5 top links by vertical position (usually navigation menus)
            top_links = sorted(links, key=lambda x: x["location"]["y"])[:5]
            for link in top_links:
                text = link["text"] or "link"
                nav_flow["steps"].append({
                    "element": link["css_selector"],
                    "action": "click",
                    "description": f"Click {text}",
                    "cypress": f"cy.get('{link['css_selector']}').click()"
                })
            
            flows.append(nav_flow)
        
        return flows
    
    def _identify_login_flow(self, input_fields, buttons) -> Optional[Dict[str, Any]]:
        """
        Try to identify a login flow.
        
        Args:
            input_fields: List of input field elements
            buttons: List of button elements
            
        Returns:
            Login flow dictionary or None if not found
        """
        # Look for username/email and password fields
        username_field = None
        password_field = None
        
        for field in input_fields:
            attrs = field.get("attributes", {})
            field_type = attrs.get("type", "")
            placeholder = attrs.get("placeholder", "").lower()
            name = attrs.get("name", "").lower()
            
            # Check for password field
            if field_type == "password" or "password" in name or "password" in placeholder:
                password_field = field
            
            # Check for username/email field
            elif (field_type in ["text", "email"] or 
                  any(term in name for term in ["user", "email", "name", "login"]) or
                  any(term in placeholder for term in ["user", "email", "name", "login"])):
                username_field = field
        
        # Look for login button
        login_button = None
        for button in buttons:
            text = button.get("text", "").lower()
            if any(term in text for term in ["log in", "login", "sign in", "signin", "submit"]):
                login_button = button
                break
        
        # If we have both fields and a button, create a login flow
        if username_field and password_field and login_button:
            return {
                "name": "User Authentication",
                "description": "Log into the application",
                "steps": [
                    {
                        "element": username_field["css_selector"],
                        "action": "input",
                        "value": "standard_user",
                        "description": "Enter username",
                        "cypress": f"cy.get('{username_field['css_selector']}').type('standard_user')"
                    },
                    {
                        "element": password_field["css_selector"],
                        "action": "input",
                        "value": "secret_sauce",
                        "description": "Enter password",
                        "cypress": f"cy.get('{password_field['css_selector']}').type('secret_sauce')"
                    },
                    {
                        "element": login_button["css_selector"],
                        "action": "click",
                        "description": "Click login button",
                        "cypress": f"cy.get('{login_button['css_selector']}').click()"
                    }
                ]
            }
        
        return None
    
    def _identify_form_flow(self, input_fields, buttons) -> Optional[Dict[str, Any]]:
        """
        Try to identify a form submission flow.
        
        Args:
            input_fields: List of input field elements
            buttons: List of button elements
            
        Returns:
            Form flow dictionary or None if not found
        """
        if not input_fields or not buttons:
            return None
        
        # Skip if we have very few input fields (might be login form)
        if len(input_fields) <= 2:
            return None
        
        # Look for submit button
        submit_button = None
        for button in buttons:
            text = button.get("text", "").lower()
            attrs = button.get("attributes", {})
            if (text and any(term in text for term in ["submit", "save", "send", "create", "add"])) or \
                (attrs.get("type") == "submit"):
                submit_button = button
                break
        
        if not submit_button:
            # Take the button that's positioned below the input fields
            input_bottom = max([field["location"]["y"] for field in input_fields])
            candidates = [b for b in buttons if b["location"]["y"] > input_bottom]
            if candidates:
                submit_button = min(candidates, key=lambda x: x["location"]["y"])
        
        if not submit_button and buttons:
            # Just take the last button as a guess
            submit_button = buttons[-1]
        
        if submit_button:
            flow = {
                "name": "Form Submission",
                "description": "Fill out and submit a form",
                "steps": []
            }
            
            # Add steps for input fields
            for field in input_fields[:5]:  # Limit to first 5 fields
                attrs = field.get("attributes", {})
                placeholder = attrs.get("placeholder", "")
                name = attrs.get("name", "")
                field_type = attrs.get("type", "")
                
                # Determine appropriate test value
                test_value = "Test input"
                if field_type == "email" or "email" in name.lower():
                    test_value = "test@example.com"
                elif "name" in name.lower() or "name" in placeholder.lower():
                    test_value = "Test User"
                elif "phone" in name.lower() or "phone" in placeholder.lower():
                    test_value = "555-123-4567"
                elif "zip" in name.lower() or "postal" in name.lower():
                    test_value = "12345"
                
                flow["steps"].append({
                    "element": field["css_selector"],
                    "action": "input",
                    "value": test_value,
                    "description": f"Enter {test_value} in {placeholder or name or 'field'}",
                    "cypress": f"cy.get('{field['css_selector']}').type('{test_value}')"
                })
            
            # Add submit step
            flow["steps"].append({
                "element": submit_button["css_selector"],
                "action": "click",
                "description": f"Click {submit_button.get('text', 'submit button')}",
                "cypress": f"cy.get('{submit_button['css_selector']}').click()"
            })
            
            return flow
        
        return None
    
    def generate_cypress_test(self, page_info, elements, flows) -> str:
        """
        Generate a Cypress test script from the analysis.
        
        Args:
            page_info: Page information
            elements: List of elements
            flows: List of user flows
            
        Returns:
            Cypress test script
        """
        url = page_info.get("url", "")
        title = page_info.get("title", "page")
        
        cypress_code = [
            "/// <reference types='cypress' />",
            "",
            f"describe('{title} - Automated Test', () => {{",
        ]
        
        # Add a test for each identified flow
        if flows:
            for flow in flows:
                flow_name = flow.get("name", "User Flow")
                flow_desc = flow.get("description", "")
                
                cypress_code.append(f"  it('{flow_name}: {flow_desc}', () => {{")
                cypress_code.append(f"    cy.visit('{url}');")
                cypress_code.append("")
                
                for step in flow.get("steps", []):
                    cypress_code.append(f"    // {step.get('description', '')}")
                    if "cypress" in step:
                        cypress_code.append(f"    {step['cypress']}")
                    cypress_code.append("")
                
                # Add a basic assertion
                cypress_code.append("    // Verify page changed after flow completion")
                cypress_code.append("    cy.url().should('include', '/');")
                cypress_code.append("  }});")
                cypress_code.append("")
        else:
            # Create a basic test that just clicks all interactive elements
            cypress_code.append("  it('should interact with all elements', () => {{")
            cypress_code.append(f"    cy.visit('{url}');")
            cypress_code.append("")
            
            clickable_elements = [e for e in elements if e.get("element_type") in ["button", "link", "submit"]]
            for i, element in enumerate(clickable_elements[:10]):  # Limit to 10 elements
                element_text = element.get("text", "").replace("'", "\\'") or f"element {i+1}"
                cypress_code.append(f"    // Click {element_text}")
                cypress_code.append(f"    cy.get('{element.get('css_selector')}').click();")
                cypress_code.append("")
            
            cypress_code.append("  }});")
        
        cypress_code.append("}});")
        
        return "\n".join(cypress_code)
    
    def analyze_and_generate(self, url: str) -> Dict[str, Any]:
        """
        Complete analysis: analyze page, generate flows, and create Cypress tests.
        
        Args:
            url: URL to analyze
            
        Returns:
            Dictionary with analysis results
        """
        try:
            # Set up driver if not already set up
            if not self.driver:
                self.setup_driver()
            
            # Get page information
            page_info = self.get_page(url)
            
            # Find interactive elements
            elements = self.find_interactive_elements()
            
            # Generate user flows
            flows = self.generate_user_flows(elements)
            
            # Generate Cypress test
            cypress_test = self.generate_cypress_test(page_info, elements, flows)
            
            # Prepare analysis results
            results = {
                "page_info": {
                    "url": page_info.get("url"),
                    "title": page_info.get("title")
                },
                "elements_count": len(elements),
                "elements": elements,
                "user_flows": flows,
                "cypress_test": cypress_test,
                "html_content": page_info.get("html", "")
            }
            
            return results
            
        except Exception as e:
            logger.error(f"Error during analysis: {e}")
            return {
                "error": str(e),
                "page_info": {"url": url, "title": "Error"},
                "elements_count": 0,
                "elements": [],
                "user_flows": [],
                "cypress_test": f"// Error during analysis: {e}",
                "html_content": ""
            }
        finally:
            # Clean up
            if self.driver:
                self.driver.quit()
                self.driver = None
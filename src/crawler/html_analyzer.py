"""
HTML analyzer module for extracting interactive elements and generating Cypress actions.
"""

import requests
from bs4 import BeautifulSoup
import re
import json
import logging
from typing import List, Dict, Any
from urllib.parse import urljoin

logger = logging.getLogger(__name__)

class HtmlAnalyzer:
    """
    Analyzer for extracting interactive elements from HTML and generating action sequences.
    """
    
    def __init__(self, config=None):
        """
        Initialize the HTML analyzer with configuration settings.
        
        Args:
            config: Optional configuration object or dictionary 
        """
        self.config = config or {}
        
        # Define interactive element selectors
        self.interactive_selectors = self.config.get('analyzer.interactive_selectors', [
            'a', 'button', 'input[type="submit"]', 'input[type="button"]', 
            'input[type="text"]', 'input[type="email"]', 'input[type="password"]',
            'select', 'textarea', '[role="button"]', '[role="link"]'
        ])
        
        # Session for requests
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def get_page_html(self, url: str) -> str:
        """
        Fetch the HTML content of a page.
        
        Args:
            url: URL to fetch
            
        Returns:
            HTML content as string
        """
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return response.text
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return ""
    
    def analyze_page(self, url: str) -> Dict[str, Any]:
        """
        Analyze a web page and extract interactive elements.
        
        Args:
            url: URL to analyze
            
        Returns:
            Dictionary with page information and interactive elements
        """
        html = self.get_page_html(url)
        if not html:
            return {"url": url, "error": "Failed to fetch page", "elements": []}
        
        soup = BeautifulSoup(html, 'html.parser')
        
        page_info = {
            "url": url,
            "title": soup.title.string if soup.title else "No title",
            "elements": []
        }
        
        # Extract interactive elements
        for selector in self.interactive_selectors:
            elements = soup.select(selector)
            for element in elements:
                element_data = self._extract_element_data(element, url)
                if element_data:
                    page_info["elements"].append(element_data)
        
        logger.info(f"Found {len(page_info['elements'])} interactive elements on {url}")
        return page_info
    
    def _extract_element_data(self, element, base_url: str) -> Dict[str, Any]:
        """
        Extract data from a BeautifulSoup element.
        
        Args:
            element: BeautifulSoup element
            base_url: Base URL for resolving relative links
            
        Returns:
            Dictionary with element information
        """
        tag_name = element.name
        
        # Basic element data
        element_data = {
            "tag_name": tag_name,
            "text": element.get_text().strip(),
            "attributes": {attr: element.get(attr) for attr in element.attrs},
            "selector": self._get_unique_selector(element),
            "element_type": self._categorize_element(element),
            "actions": self._determine_possible_actions(element, base_url)
        }
        
        return element_data
    
    def _get_unique_selector(self, element) -> str:
        """
        Generate a unique CSS selector for an element.
        
        Args:
            element: BeautifulSoup element
            
        Returns:
            CSS selector string
        """
        # Try id first
        if element.get('id'):
            return f"#{element['id']}"
        
        # Try using a combination of tag and classes
        if element.get('class'):
            classes = '.'.join(element['class'])
            selector = f"{element.name}.{classes}"
            return selector
        
        # Try using name attribute
        if element.get('name'):
            return f"{element.name}[name='{element['name']}']"
        
        # Try text content for elements like buttons
        if element.name in ['button', 'a'] and element.get_text().strip():
            return f"{element.name}:contains('{element.get_text().strip()}')"
        
        # Fallback to position-based selector
        selector_parts = []
        for parent in element.parents:
            if parent.name == 'html':
                break
            if parent.get('id'):
                selector_parts.append(f"#{parent['id']}")
                break
            parent_siblings = [sibling for sibling in parent.find_previous_siblings(parent.name)]
            selector_parts.append(f"{parent.name}:nth-of-type({len(parent_siblings) + 1})")
        
        siblings = [sibling for sibling in element.find_previous_siblings(element.name)]
        selector_parts.append(f"{element.name}:nth-of-type({len(siblings) + 1})")
        
        return ' > '.join(reversed(selector_parts))
    
    def _categorize_element(self, element) -> str:
        """
        Categorize an element based on its type and attributes.
        
        Args:
            element: BeautifulSoup element
            
        Returns:
            String representing the element category
        """
        tag_name = element.name
        
        # Check for role attribute first
        role = element.get('role')
        if role and role in ["button", "link", "checkbox", "radio"]:
            return role
        
        # Check element type
        if tag_name == 'a':
            return "link"
        elif tag_name == 'button':
            return "button"
        elif tag_name == 'input':
            input_type = element.get('type', '')
            if input_type in ["checkbox", "radio", "submit", "button"]:
                return input_type
            elif input_type in ["text", "email", "password", "number", "tel", "url", "search"]:
                return "input_field"
            else:
                return f"input_{input_type}" if input_type else "input"
        elif tag_name == 'select':
            return "dropdown"
        elif tag_name == 'textarea':
            return "text_area"
        elif tag_name == 'form':
            return "form"
        
        # Default
        return "other"
    
    def _determine_possible_actions(self, element, base_url: str) -> List[Dict[str, Any]]:
        """
        Determine possible user actions for an element.
        
        Args:
            element: BeautifulSoup element
            base_url: Base URL for resolving relative links
            
        Returns:
            List of possible actions
        """
        actions = []
        element_type = self._categorize_element(element)
        
        if element_type in ["link", "button", "submit"]:
            actions.append({
                "type": "click",
                "description": f"Click on {element.get_text().strip() or element_type}"
            })
            
            # For links, add navigation action
            if element_type == "link" and element.get('href'):
                href = element.get('href')
                if not href.startswith(('http://', 'https://', 'javascript:', '#')):
                    full_url = urljoin(base_url, href)
                    actions.append({
                        "type": "navigate",
                        "url": full_url,
                        "description": f"Navigate to {full_url}"
                    })
        
        elif element_type in ["input_field", "text_area"]:
            placeholder = element.get('placeholder', '')
            label_text = self._find_label_for_element(element)
            input_name = element.get('name', '')
            
            description = label_text or placeholder or input_name or "text field"
            actions.append({
                "type": "input",
                "description": f"Enter text in {description}",
                "value": "{sample_text}"  # Placeholder to be replaced
            })
        
        elif element_type == "dropdown":
            options = []
            for option in element.find_all('option'):
                if option.get('value'):
                    options.append({
                        "value": option.get('value'),
                        "text": option.get_text().strip()
                    })
            
            actions.append({
                "type": "select",
                "description": f"Select option from dropdown",
                "options": options[:5]  # Limit to first 5 options
            })
        
        elif element_type in ["checkbox", "radio"]:
            actions.append({
                "type": "toggle",
                "description": f"Toggle {element_type}"
            })
        
        return actions
    
    def _find_label_for_element(self, element) -> str:
        """
        Find the label text for a form element.
        
        Args:
            element: BeautifulSoup element
            
        Returns:
            Label text if found, empty string otherwise
        """
        # Check for id attribute and find label with matching 'for' attribute
        if element.get('id'):
            label = element.find_previous('label', attrs={"for": element.get('id')})
            if label:
                return label.get_text().strip()
        
        # Check for wrapper label
        parent_label = element.find_parent('label')
        if parent_label:
            # Extract text excluding the element's own text
            element_text = element.get_text().strip()
            label_text = parent_label.get_text().strip()
            if element_text:
                label_text = label_text.replace(element_text, '').strip()
            return label_text
        
        return ""
    
    def generate_cypress_test(self, page_data: Dict[str, Any]) -> str:
        """
        Generate Cypress test code from page analysis data.
        
        Args:
            page_data: Page analysis data from analyze_page()
            
        Returns:
            Cypress test code as string
        """
        elements = page_data.get("elements", [])
        if not elements:
            return "// No interactive elements found on page"
        
        cypress_code = [
            "describe('Automated test for " + page_data.get("title", "page") + "', () => {",
            "  it('should interact with page elements', () => {",
            f"    cy.visit('{page_data.get('url')}');",
            ""
        ]
        
        # Add test steps for interactive elements
        for i, element in enumerate(elements):
            selector = element.get("selector", "")
            if not selector:
                continue
                
            element_text = element.get("text", "").replace("'", "\\'")
            element_type = element.get("element_type", "unknown")
            actions = element.get("actions", [])
            
            # Add comment for clarity
            description = f"{element_type}: {element_text}" if element_text else element_type
            cypress_code.append(f"    // {description}")
            
            # Add Cypress commands based on possible actions
            for action in actions:
                action_type = action.get("type")
                
                if action_type == "click":
                    cypress_code.append(f"    cy.get('{selector}').click();")
                
                elif action_type == "input":
                    sample_text = "Test input"
                    if "email" in selector.lower():
                        sample_text = "test@example.com"
                    elif "password" in selector.lower():
                        sample_text = "SecurePassword123"
                    
                    cypress_code.append(f"    cy.get('{selector}').type('{sample_text}');")
                
                elif action_type == "select" and action.get("options"):
                    if action.get("options"):
                        option_value = action["options"][0]["value"]
                        cypress_code.append(f"    cy.get('{selector}').select('{option_value}');")
                
                elif action_type == "toggle":
                    cypress_code.append(f"    cy.get('{selector}').check();")
            
            cypress_code.append("")
        
        cypress_code.extend([
            "    // Add assertions here",
            "    cy.url().should('include', '/');",
            "  });",
            "});"
        ])
        
        return "\n".join(cypress_code)
    
    def generate_user_flows(self, page_data: Dict[str, Any], max_flows: int = 3) -> List[Dict[str, Any]]:
        """
        Generate potential user flows from page analysis data.
        
        Args:
            page_data: Page analysis data from analyze_page()
            max_flows: Maximum number of flows to generate
            
        Returns:
            List of user flow descriptions
        """
        elements = page_data.get("elements", [])
        if not elements:
            return []
        
        # Group elements by type
        element_groups = {}
        for element in elements:
            element_type = element.get("element_type", "other")
            if element_type not in element_groups:
                element_groups[element_type] = []
            element_groups[element_type].append(element)
        
        # Define common flow patterns
        flows = []
        
        # 1. Form submission flow
        form_elements = page_data.get("elements", [])
        input_fields = [e for e in form_elements if e.get("element_type") in ["input_field", "text_area", "dropdown"]]
        submit_buttons = [e for e in form_elements if e.get("element_type") in ["button", "submit"]]
        
        if input_fields and submit_buttons:
            flow = {
                "name": "Form Submission",
                "description": "Fill in form fields and submit",
                "steps": []
            }
            
            # Add steps for input fields
            for field in input_fields[:5]:  # Limit to first 5 fields
                field_text = field.get("text", "") or self._find_label_for_element(field) or "field"
                step = {
                    "element": field.get("selector", ""),
                    "action": "input",
                    "description": f"Enter data in {field_text}"
                }
                flow["steps"].append(step)
            
            # Add submit step
            submit = submit_buttons[0]
            submit_text = submit.get("text", "") or "submit button"
            flow["steps"].append({
                "element": submit.get("selector", ""),
                "action": "click",
                "description": f"Click {submit_text}"
            })
            
            flows.append(flow)
        
        # 2. Navigation flow
        links = [e for e in elements if e.get("element_type") == "link"]
        if links:
            primary_links = [l for l in links if self._is_primary_navigation(l)]
            if primary_links:
                flow = {
                    "name": "Navigation",
                    "description": "Navigate through primary site sections",
                    "steps": []
                }
                
                for link in primary_links[:max_flows]:
                    link_text = link.get("text", "") or "link"
                    flow["steps"].append({
                        "element": link.get("selector", ""),
                        "action": "click",
                        "description": f"Click on {link_text}"
                    })
                
                flows.append(flow)
        
        # 3. User authentication flow
        username_fields = [e for e in elements if self._is_username_field(e)]
        password_fields = [e for e in elements if self._is_password_field(e)]
        login_buttons = [e for e in elements if self._is_login_button(e)]
        
        if username_fields and password_fields and login_buttons:
            flow = {
                "name": "User Authentication",
                "description": "Log in to the system",
                "steps": []
            }
            
            flow["steps"].append({
                "element": username_fields[0].get("selector", ""),
                "action": "input",
                "description": "Enter username"
            })
            
            flow["steps"].append({
                "element": password_fields[0].get("selector", ""),
                "action": "input",
                "description": "Enter password"
            })
            
            flow["steps"].append({
                "element": login_buttons[0].get("selector", ""),
                "action": "click",
                "description": "Click login button"
            })
            
            flows.append(flow)
        
        return flows[:max_flows]
    
    def _is_primary_navigation(self, element) -> bool:
        """Check if an element is likely part of primary navigation."""
        # Look for common navigation classes or patterns
        attrs = element.get("attributes", {})
        if not attrs:
            return False
            
        classes = attrs.get("class", [])
        if isinstance(classes, str):
            classes = classes.split()
            
        nav_indicators = ['nav', 'menu', 'main-menu', 'navbar', 'navigation', 'header']
        
        # Check element classes
        for cls in classes:
            if any(indicator in cls.lower() for indicator in nav_indicators):
                return True
        
        # Check if inside navigation element
        if "selector" in element:
            if "nav" in element["selector"].lower() or "header" in element["selector"].lower():
                return True
                
        return False
    
    def _is_username_field(self, element) -> bool:
        """Check if an element is likely a username field."""
        element_type = element.get("element_type", "")
        if element_type != "input_field":
            return False
            
        attrs = element.get("attributes", {})
        
        # Check for common username field indicators
        indicators = ['username', 'user', 'email', 'login', 'name', 'account']
        
        # Check element attributes
        for key, value in attrs.items():
            if value and any(indicator in str(value).lower() for indicator in indicators):
                return True
                
        return False
    
    def _is_password_field(self, element) -> bool:
        """Check if an element is likely a password field."""
        element_type = element.get("element_type", "")
        attrs = element.get("attributes", {})
        
        # Check if it's a password input
        if element_type == "input_field" and attrs.get("type") == "password":
            return True
            
        return False
    
    def _is_login_button(self, element) -> bool:
        """Check if an element is likely a login button."""
        element_type = element.get("element_type", "")
        if element_type not in ["button", "submit"]:
            return False
            
        # Check text content
        text = element.get("text", "").lower()
        login_terms = ['login', 'log in', 'sign in', 'signin', 'enter', 'submit']
        
        if any(term in text for term in login_terms):
            return True
            
        # Check attributes
        attrs = element.get("attributes", {})
        for key, value in attrs.items():
            if value and any(term in str(value).lower() for term in login_terms):
                return True
                
        return False
    
    def analyze_and_generate(self, url: str) -> Dict[str, Any]:
        """
        Complete analysis: analyze page, generate flows, and create Cypress tests.
        
        Args:
            url: URL to analyze
            
        Returns:
            Dictionary with analysis results
        """
        # Analyze the page
        page_data = self.analyze_page(url)
        
        # Generate user flows
        user_flows = self.generate_user_flows(page_data)
        
        # Generate Cypress test
        cypress_test = self.generate_cypress_test(page_data)
        
        # Compile all results
        results = {
            "page_info": {
                "url": page_data.get("url"),
                "title": page_data.get("title")
            },
            "elements_count": len(page_data.get("elements", [])),
            "elements": page_data.get("elements", []),
            "user_flows": user_flows,
            "cypress_test": cypress_test
        }
        
        return results
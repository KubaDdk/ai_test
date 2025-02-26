#!/usr/bin/env python3
"""
Script to run the website crawler and extract interactive elements.
"""

import os
import sys
import json
import argparse
from datetime import datetime

# Add the project root directory to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Import project modules
from src.utils.config import Config
from src.utils.logger import setup_colored_console_logger
from src.crawler.selenium_crawler import SeleniumCrawler

def main():
    """Main entry point for the crawler script."""
    
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Run the website crawler to extract interactive elements")
    parser.add_argument("--url", "-u", required=True, help="URL to start crawling from")
    parser.add_argument("--config", "-c", help="Path to configuration file")
    parser.add_argument("--output", "-o", help="Path to save output file")
    parser.add_argument("--single-page", "-s", action="store_true", help="Crawl only the specified page, not following links")
    parser.add_argument("--depth", "-d", type=int, help="Maximum crawl depth")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    # Set up logging
    log_level = "DEBUG" if args.verbose else "INFO"
    logger = setup_colored_console_logger(level=getattr(sys.modules["logging"], log_level))
    
    try:
        # Load configuration
        config_path = args.config or os.path.join(project_root, "config", "default.yaml")
        logger.info(f"Loading configuration from: {config_path}")
        config = Config(config_path)
        
        # Override configuration with command line arguments if provided
        if args.depth:
            config.set("crawler.max_depth", args.depth)
            logger.info(f"Setting maximum crawl depth to: {args.depth}")
        
        # Initialize the crawler
        logger.info("Initializing crawler...")
        crawler = SeleniumCrawler(config)
        
        # Start crawling
        start_time = datetime.now()
        logger.info(f"Starting to crawl: {args.url}")
        
        if args.single_page:
            elements = crawler.get_single_page_elements(args.url)
            logger.info(f"Analyzed single page, found {len(elements)} interactive elements")
        else:
            elements = crawler.start_crawl(args.url)
            logger.info(f"Crawl complete, found {len(elements)} interactive elements across multiple pages")
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        logger.info(f"Crawl completed in {duration:.2f} seconds")
        
        # Save the results
        if elements:
            output_path = args.output
            if not output_path:
                # Generate default output path if not specified
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"crawl_results_{timestamp}.json"
                output_dir = os.path.join(project_root, "data", "raw")
                os.makedirs(output_dir, exist_ok=True)
                output_path = os.path.join(output_dir, filename)
            
            # Create output directory if it doesn't exist
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            
            # Save the crawl results to a JSON file
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(elements, f, indent=2, ensure_ascii=False)
                
            logger.info(f"Results saved to: {output_path}")
        else:
            logger.warning("No elements were found during the crawl")
        
        return 0  # Success exit code
        
    except Exception as e:
        logger.error(f"Error during crawl: {e}", exc_info=args.verbose)
        return 1  # Error exit code

if __name__ == "__main__":
    sys.exit(main())
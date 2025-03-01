#!/usr/bin/env python3
"""
Script to run the enhanced analyzer with Selenium support for JavaScript-rendered pages.
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
from src.crawler.enhanced_analyzer import EnhancedAnalyzer

def main():
    """Main entry point for the enhanced analyzer script."""
    
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Run the enhanced analyzer for JavaScript-rendered pages")
    parser.add_argument("--url", "-u", required=True, help="URL to analyze")
    parser.add_argument("--config", "-c", help="Path to configuration file")
    parser.add_argument("--output-dir", "-o", help="Directory to save output files")
    parser.add_argument("--output-filename", "-f", help="Base filename for output files")
    parser.add_argument("--no-headless", action="store_true", help="Run browser in visible mode (not headless)")
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
        
        # Initialize the analyzer
        logger.info("Initializing enhanced analyzer...")
        analyzer = EnhancedAnalyzer(config.config_data)
        
        # Set headless mode
        headless = not args.no_headless
        if not headless:
            logger.info("Running browser in visible mode")
        
        # Start analysis
        start_time = datetime.now()
        logger.info(f"Starting to analyze: {args.url}")
        
        # Setup driver with headless mode setting
        analyzer.setup_driver(headless=headless)
        
        # Perform analysis
        analysis_results = analyzer.analyze_and_generate(args.url)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        logger.info(f"Analysis completed in {duration:.2f} seconds")
        
        elements_count = analysis_results.get("elements_count", 0)
        flows_count = len(analysis_results.get("user_flows", []))
        
        logger.info(f"Found {elements_count} interactive elements")
        logger.info(f"Generated {flows_count} potential user flows")
        
        # Determine output directory and filenames
        output_dir = args.output_dir or os.path.join(project_root, "data", "output")
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_filename = args.output_filename or f"enhanced_analysis_{timestamp}"
        
        # Save analysis results
        analysis_file = os.path.join(output_dir, f"{base_filename}.json")
        with open(analysis_file, "w", encoding="utf-8") as f:
            json.dump(analysis_results, f, indent=2, ensure_ascii=False)
        logger.info(f"Analysis results saved to: {analysis_file}")
        
        # Save user flows separately
        flows_dir = os.path.join(output_dir, "user_flows")
        os.makedirs(flows_dir, exist_ok=True)
        flows_file = os.path.join(flows_dir, f"{base_filename}_flows.json")
        with open(flows_file, "w", encoding="utf-8") as f:
            json.dump(analysis_results.get("user_flows", []), f, indent=2, ensure_ascii=False)
        logger.info(f"User flows saved to: {flows_file}")
        
        # Save the raw HTML content for debugging
        html_file = None
        if "html_content" in analysis_results and analysis_results["html_content"]:
            html_dir = os.path.join(output_dir, "html")
            os.makedirs(html_dir, exist_ok=True)
            html_file = os.path.join(html_dir, f"{base_filename}.html")
            with open(html_file, "w", encoding="utf-8") as f:
                f.write(analysis_results["html_content"])
            logger.info(f"Raw HTML saved to: {html_file}")
        
        # Save Cypress test
        if "cypress_test" in analysis_results:
            cypress_dir = os.path.join(output_dir, "cypress_tests")
            os.makedirs(cypress_dir, exist_ok=True)
            cypress_file = os.path.join(cypress_dir, f"{base_filename}_spec.js")
            with open(cypress_file, "w", encoding="utf-8") as f:
                f.write(analysis_results["cypress_test"])
            logger.info(f"Cypress test saved to: {cypress_file}")
        
        # Quick summary
        print("\n=== Analysis Summary ===")
        print(f"URL: {args.url}")
        print(f"Page Title: {analysis_results.get('page_info', {}).get('title', 'Unknown')}")
        print(f"Interactive Elements: {elements_count}")
        print(f"Potential User Flows: {flows_count}")
        print(f"Output Files:")
        print(f"  - Analysis: {analysis_file}")
        print(f"  - User Flows: {flows_file}")
        if html_file:
            print(f"  - Raw HTML: {html_file}")
        print(f"  - Cypress Test: {cypress_file}")
        
        return 0  # Success exit code
        
    except Exception as e:
        logger.error(f"Error during analysis: {e}", exc_info=args.verbose)
        return 1  # Error exit code

if __name__ == "__main__":
    sys.exit(main())
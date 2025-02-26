"""
Logging utility for the website analysis agent.
"""

import os
import logging
import sys
from datetime import datetime
from typing import Optional

def setup_logger(name: str = "website_analyzer", 
                 level: int = logging.INFO,
                 log_file: Optional[str] = None,
                 console: bool = True) -> logging.Logger:
    """
    Set up and configure a logger.
    
    Args:
        name: Logger name
        level: Logging level
        log_file: Path to log file (if None, no file logging)
        console: Whether to log to console
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Remove existing handlers to avoid duplicates
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Add file handler if log_file is specified
    if log_file:
        # Ensure log directory exists
        log_dir = os.path.dirname(log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
            
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    # Add console handler if requested
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    return logger

def get_default_logger(log_dir: Optional[str] = None) -> logging.Logger:
    """
    Get a default configured logger for the application.
    
    Args:
        log_dir: Directory to store log files (default: project's data/logs dir)
        
    Returns:
        Configured logger instance
    """
    if not log_dir:
        # Default to logs directory in project root
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        log_dir = os.path.join(project_root, 'data', 'logs')
    
    # Create log directory if it doesn't exist
    os.makedirs(log_dir, exist_ok=True)
    
    # Create log filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = os.path.join(log_dir, f'website_analyzer_{timestamp}.log')
    
    return setup_logger(log_file=log_file)

# Configuration for displaying log messages in a more user-friendly way
class ColoredFormatter(logging.Formatter):
    """
    Formatter that adds color to log levels for console output.
    """
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',  # Cyan
        'INFO': '\033[32m',   # Green
        'WARNING': '\033[33m', # Yellow
        'ERROR': '\033[31m',  # Red
        'CRITICAL': '\033[41m\033[37m',  # White on Red bg
        'RESET': '\033[0m'    # Reset color
    }
    
    def format(self, record):
        """Format log record with colors."""
        log_message = super().format(record)
        levelname = record.levelname
        
        if hasattr(sys.stdout, 'isatty') and sys.stdout.isatty():
            # Only apply colors when output is to a terminal
            color = self.COLORS.get(levelname, self.COLORS['RESET'])
            reset = self.COLORS['RESET']
            log_message = f"{color}{log_message}{reset}"
            
        return log_message

def setup_colored_console_logger(name: str = "website_analyzer",
                               level: int = logging.INFO) -> logging.Logger:
    """
    Set up a logger with colored console output.
    
    Args:
        name: Logger name
        level: Logging level
        
    Returns:
        Configured logger with colored output
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Remove existing handlers to avoid duplicates
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create console handler with colored formatter
    console_handler = logging.StreamHandler(sys.stdout)
    formatter = ColoredFormatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger
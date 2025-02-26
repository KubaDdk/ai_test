"""
Configuration management utility for the website analysis agent.
"""

import os
import yaml
import logging
from typing import Dict, Any, List, Optional, Union

logger = logging.getLogger(__name__)

class Config:
    """
    Configuration manager that loads and provides access to configuration settings.
    """
    
    def __init__(self, config_path: str = None, credentials_path: str = None):
        """
        Initialize the configuration manager.
        
        Args:
            config_path: Path to the main configuration file
            credentials_path: Path to the credentials file
        """
        self.config_data = {}
        
        # Set default paths if not provided
        if not config_path:
            config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                     'config', 'default.yaml')
        
        if not credentials_path:
            credentials_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                          'config', 'credentials.yaml')
        
        # Load configuration file
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as config_file:
                    self.config_data = yaml.safe_load(config_file) or {}
                logger.info(f"Loaded configuration from {config_path}")
            except Exception as e:
                logger.error(f"Error loading configuration from {config_path}: {e}")
                self.config_data = {}
        else:
            logger.warning(f"Configuration file not found at {config_path}")
        
        # Load credentials if available
        if os.path.exists(credentials_path):
            try:
                with open(credentials_path, 'r') as cred_file:
                    credentials = yaml.safe_load(cred_file) or {}
                # Merge credentials into config data
                self._merge_dicts(self.config_data, credentials)
                logger.info(f"Loaded credentials from {credentials_path}")
            except Exception as e:
                logger.error(f"Error loading credentials from {credentials_path}: {e}")
    
    def _merge_dicts(self, target: Dict, source: Dict) -> None:
        """
        Recursively merge source dictionary into target dictionary.
        
        Args:
            target: Target dictionary to merge into
            source: Source dictionary to merge from
        """
        for key, value in source.items():
            if isinstance(value, dict) and key in target and isinstance(target[key], dict):
                self._merge_dicts(target[key], value)
            else:
                target[key] = value
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get a configuration value using a dot-notation path.
        
        Args:
            key_path: Dot-notation path to the configuration value
            default: Default value to return if the key is not found
            
        Returns:
            The configuration value or the default value
        """
        keys = key_path.split('.')
        value = self.config_data
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value
    
    def set(self, key_path: str, value: Any) -> None:
        """
        Set a configuration value using a dot-notation path.
        
        Args:
            key_path: Dot-notation path to the configuration value
            value: Value to set
        """
        keys = key_path.split('.')
        config = self.config_data
        
        # Navigate to the last parent dictionary
        for key in keys[:-1]:
            if key not in config or not isinstance(config[key], dict):
                config[key] = {}
            config = config[key]
        
        # Set the value on the last key
        config[keys[-1]] = value
    
    def save(self, config_path: str = None) -> bool:
        """
        Save the current configuration to a file.
        
        Args:
            config_path: Path to save the configuration file
            
        Returns:
            True if successful, False otherwise
        """
        if not config_path:
            config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                      'config', 'default.yaml')
        
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            
            with open(config_path, 'w') as config_file:
                yaml.dump(self.config_data, config_file, default_flow_style=False)
            logger.info(f"Configuration saved to {config_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving configuration to {config_path}: {e}")
            return False
    
    def __str__(self) -> str:
        """String representation of the configuration."""
        return yaml.dump(self.config_data, default_flow_style=False)
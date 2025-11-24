import json
import os
from typing import Dict, Any
import logging


class ConfigManager:
    """
    Manages application configuration with file persistence.
    Demonstrates configuration management pattern.
    """

    def __init__(self, config_file: str = "config.json"):
        self.config_file = config_file
        self.config: Dict[str, Any] = {}
        self.default_config = {
            "default_connections": 4,
            "chunk_size": 1024 * 1024,  # 1MB
            "timeout": 30,
            "max_retries": 3,
            "user_agent": "ParallelDownloader/1.0",
            "buffer_size": 8192 * 8  # 64KB
        }
        self.logger = logging.getLogger(__name__)
        self._load_config()

    def _load_config(self):
        """Load configuration from file or create default"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    loaded_config = json.load(f)
                self.config = {**self.default_config, **loaded_config}
                self.logger.info(f"Loaded configuration from {self.config_file}")
            except (json.JSONDecodeError, IOError) as e:
                self.logger.warning(f"Failed to load config, using defaults: {e}")
                self.config = self.default_config.copy()
        else:
            self.config = self.default_config.copy()
            self._save_config()

    def _save_config(self):
        """Save current configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
        except IOError as e:
            self.logger.error(f"Failed to save config: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        return self.config.get(key, default)

    def set(self, key: str, value: Any):
        """Set configuration value and save"""
        self.config[key] = value
        self._save_config()

    def update(self, new_config: Dict[str, Any]):
        """Update multiple configuration values"""
        self.config.update(new_config)
        self._save_config()
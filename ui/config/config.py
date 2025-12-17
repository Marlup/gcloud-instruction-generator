import json
from pathlib import Path
from typing import Dict

# UI Settings
expand_actions = False
current_theme = "cyborg"

# Config file path
CONFIG_FILE = Path("ui/config/ui_settings.json")

# Default values for gcloud parameters
DEFAULT_PARAMS = {
    "project_id": "",
    "region": "",
    "location": ""
}


class UIConfigManager:
    """Manages UI configuration persistence."""
    
    def __init__(self, config_path: Path = CONFIG_FILE):
        self.config_path = config_path
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
    
    def load_default_params(self) -> Dict[str, str]:
        """
        Load default parameters from config file.
        
        Returns:
            dict: Default parameters with project_id, region, location
        """
        if not self.config_path.exists():
            return DEFAULT_PARAMS.copy()
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return config.get('default_params', DEFAULT_PARAMS.copy())
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Failed to load config from {self.config_path}: {e}")
            return DEFAULT_PARAMS.copy()
    
    def save_default_params(self, params: Dict[str, str]) -> bool:
        """
        Save default parameters to config file.
        
        Args:
            params: Dictionary with default parameter values
            
        Returns:
            bool: True if saved successfully, False otherwise
        """
        try:
            # Load existing config or create new
            config = {}
            if self.config_path.exists():
                try:
                    with open(self.config_path, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                except json.JSONDecodeError:
                    config = {}
            
            # Update default params
            config['default_params'] = params
            
            # Save config
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            return True
        except IOError as e:
            print(f"Error: Failed to save config to {self.config_path}: {e}")
            return False
    
    def get_theme(self) -> str:
        """Get the saved theme."""
        if not self.config_path.exists():
            return current_theme
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return config.get('theme', current_theme)
        except (json.JSONDecodeError, IOError):
            return current_theme
    
    def save_theme(self, theme: str) -> bool:
        """Save the current theme preference."""
        try:
            config = {}
            if self.config_path.exists():
                try:
                    with open(self.config_path, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                except json.JSONDecodeError:
                    config = {}
            
            config['theme'] = theme
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            return True
        except IOError as e:
            print(f"Error: Failed to save theme: {e}")
            return False


# Global config manager instance
config_manager = UIConfigManager()

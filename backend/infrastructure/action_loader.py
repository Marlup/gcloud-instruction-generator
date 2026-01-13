import os
import json
import logging
from typing import List, Dict, Any

logging.getLogger(__name__)

class ActionLoader:

    def __init__(self, service_path: str):
        self.service_path = service_path
        self.actions = self._load_actions()

    def _load_actions(self) -> Dict[str, Any]:
        """
        Loads actions from the single 'actions.json' file.
        Format: Resource -> Nested Dict -> ... -> { "action": ActionDefinition }
        """
        actions_file = os.path.join(self.service_path, "actions.json")
        if os.path.exists(actions_file):
            logging.info(f"Loading actions from: {actions_file}")
            try:
                with open(actions_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logging.error(f"Error loading {actions_file}: {e}")
                return {}
        
        logging.warning(f"actions.json not found in {self.service_path}")
        return {}

    def get_all_actions_flat(self) -> List[Dict[str, Any]]:
        """
        Traverses the tree and returns a list of all action definitions,
        enriched with their path/resource info for debugging or flat listing.
        """
        flat_list = []
        
        def traverse(node: Dict[str, Any], path: List[str]):
            # If current node has "action", it's a command
            if "action" in node:
                action_def = node["action"]
                # Enrich with path if needed, or just return the def
                # action_def['start_path'] = path 
                flat_list.append(action_def)
            
            # Recurse into children
            for key, val in node.items():
                if key == "action": 
                    continue
                if isinstance(val, dict):
                    traverse(val, path + [key])

        for resource, subtree in self.actions.items():
            if isinstance(subtree, dict):
                traverse(subtree, [resource])
                
        return flat_list

    def get_action_by_path(self, keys: List[str]) -> Dict[str, Any]:
        """
        Retrieves an action definition by following a list of keys.
        keys[0] should be the resource name.
        """
        if not keys:
            return None
        
        node = self.actions
        try:
            for k in keys:
                node = node[k]
            
            if "action" in node:
                return node["action"]
            return node
        except KeyError:
            return None

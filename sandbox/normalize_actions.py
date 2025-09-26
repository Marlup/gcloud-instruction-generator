import os
from typing import Dict
import json
import logging

def main():
    parent_path = "plugins"
    service_paths = os.listdir(parent_path)

    # Make 
    for service_path in service_paths:
        
        service_path = os.path.join(parent_path, service_path)
        action_path = os.path.join(service_path, "actions.json")

        actions_data = read_action_from_file(action_path)

        make_dirs(actions_data, service_path)

def read_action_from_file(path: str):
    logging.info("read_action_from_file", f"action-filename : {path}")
    with open(path, "r", errors="ignore", encoding="utf-8") as f:
        return json.load(f)
    
def make_dirs(actions_data: Dict[str, Dict], base_path: str):
    # actions-json-file -> [resource] -> [category] -> [action] -> cmd, params

    for resource, resource_data in actions_data.items():
        resource_path = os.path.join(base_path, resource)
        print("make_dirs", f"resource_path : {resource_path}")

        # Make a directory for resource
        os.makedirs(resource_path, exist_ok=True)
        
        # Make a directory for resource
        make_category_files(resource_data, resource_path)

def make_category_files(categories_data: Dict[str, Dict], base_path):
    # [category] -> [action] -> cmd, params

    for category, categories_data in categories_data.items():
        
        # Make a directory for resource
        category_path =  os.path.join(base_path, category)
        os.makedirs(category_path, exist_ok=True)

        category_actions_file_path =  os.path.join(category_path, "action.json")
        with open(category_actions_file_path, "w") as f:
            json.dump(categories_data, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    main()
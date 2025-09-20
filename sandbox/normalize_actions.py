import os
from typing import Dict
import json

def main():
    parent_path = "plugins"
    service_paths = os.listdir(parent_path)

    # Make 
    for service_path in service_paths:
        
        service_path = os.path.join(parent_path, service_path)
        action_path = os.path.join(service_path, "actions.json")

        actions = read_action_from_file(action_path)

        make_dirs(actions, action_path)


def read_action_from_file(path: str):
    print(f"action-filename : {path}")
    with open(path, "r", errors="ignore", encoding="utf-8") as f:
        return json.load(f)
    
def make_dirs(actions_data: Dict[str, Dict], base_path: str):
    # actions-json-file -> [resource] -> [category] -> [action] -> cmd, params

    for resource, resource_data in actions_data.items():
        resource_path = os.path.join(base_path, resource)

        # Make a directory for resource
        os.makedirs(resource_path, exist_ok=True)
        
        # Make a directory for resource
        make_category_files(resource_path, resource_data)

def make_category_files(categories_data: Dict[str, Dict], base_path):
    # [category] -> [action] -> cmd, params

    for category, categories_data in categories_data.items():

        category_path =  os.path.join(base_path, category, "action.json")
        with open(category_path, "r") as f:
            json.dump(categories_data, f)


if __name__ == "__main__":
    main()
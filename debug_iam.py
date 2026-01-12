
from backend.actions.build_actions import load_global_config, build_service_configs, iter_commands, map_group_to_resource, process_service, write_single_actions_file, ServiceConfig
from pathlib import Path
import json
import logging

# Setup basic logging to stdout
logging.basicConfig(level=logging.INFO)

def debug_iam():
    # Load raw data
    input_dir = Path("data/webscrap/landing")
    service = "iam"
    json_path = input_dir / service / "iam_commands.json"
    
    with open(json_path, "r", encoding="utf-8") as f:
        commands_list = json.load(f)
    
    print(f"Total items in json: {len(commands_list)}")
    
    # Check first few items
    for i, item in enumerate(commands_list[:10]):
        print(f"Item {i}: id={item.get('id')} type={item.get('type')} path={item.get('path')}")

    # Run iter_commands
    service_config = ServiceConfig(name="iam", input_dir=input_dir, output_dir=Path("tmp"))
    
    processed_ids = []
    print("\n--- Processed Commands ---")
    
    actions_index = {}
    
    for i, cmd_node in enumerate(iter_commands(service_config, commands_list)):
        processed_ids.append(cmd_node.node.get("id"))
        if "delete" in cmd_node.node.get("id", "") and "credentials" in cmd_node.node.get("id", ""):
            print(f"Found credential delete: {cmd_node.node.get('id')}")
            # print details
            # print(cmd_node.group_path, cmd_node.name)
        
        # Copied logic from process_service loop
        resource = map_group_to_resource(service_config, cmd_node.group_path)
        full_command_path = cmd_node.group_path + [cmd_node.name]
        
        if cmd_node.group_path:
             first_segment = cmd_node.group_path[0]
             mapped_resource = map_group_to_resource(service_config, cmd_node.group_path)
             if mapped_resource == first_segment:
                 tree_path = full_command_path[1:]
             else:
                 tree_path = full_command_path
        else:
            tree_path = full_command_path
            
        if not tree_path:
            tree_path = [cmd_node.name]
            
        actions_index.setdefault(resource, {})
        current_level = actions_index[resource]
        
        for idx, segment in enumerate(tree_path):
            is_last = (idx == len(tree_path) - 1)
            if is_last:
                current_level[segment] = {"cmd": "MOCK"}
            else:
                current_level = current_level.setdefault(segment, {})

    print(f"Processed count: {len(processed_ids)}")
    
    # Check specifically for skipped 3rd item?
    # Index 2 in 0-indexed list.
    id_2 = commands_list[2].get("id")
    if id_2 not in processed_ids:
        print(f"WARNING: Item 2 ({id_2}) was NOT processed.")
    else:
        print(f"Item 2 ({id_2}) was processed.")

    # Check structure of oauth-clients -> credentials
    print("\n--- Structure Verification ---")
    oauth = actions_index.get("oauth-clients", {})
    creds = oauth.get("credentials", {})
    print(json.dumps(creds, indent=2))

if __name__ == "__main__":
    debug_iam()

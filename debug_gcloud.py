
import json
import os
import sys

# Add current directory to sys.path to import backend
sys.path.append(os.getcwd())

try:
    from backend.actions.build_actions import simplify_command_synopsis, CommandNode
except ImportError:
    # Fallback if import fails, simplistic mock
    print("Could not import build_actions, will rely on inspection")
    simplify_command_synopsis = None

def find_command(node, path_suffix):
    # Recurse to find the command with path_suffix
    # path_suffix is list of strings, e.g. ["insights", "inventory-reports", "list"]
    
    # Check base commands
    base_commands = node.get("base_commands", {})
    if len(path_suffix) == 1 and path_suffix[0] in base_commands:
        return base_commands[path_suffix[0]]

    # Check groups
    base_groups = node.get("base_groups", {})
    if len(path_suffix) > 1 and path_suffix[0] in base_groups:
        return find_command(base_groups[path_suffix[0]], path_suffix[1:])
    
    return None

def main():
    json_path = "data/web-gcloud/storage/storage_command.json"
    if not os.path.exists(json_path):
        print(f"File not found: {json_path}")
        return

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Looking for: gcloud storage insights inventory-reports list
    # Path in JSON structure: storage -> insights -> inventory-reports -> list?
    # Actually the structure is recursive.
    # The file is storage_command.json, so root is 'storage'.
    # We want command: insights inventory-reports list
    
    cmd_node_dict = find_command(data, ["insights", "inventory-reports", "list"])
    
    if cmd_node_dict:
        print("FOUND NODE KEYS:", cmd_node_dict.keys())
        print("SYNOPSIS:", cmd_node_dict.get("command_synopsis"))
        print("DESCRIPTION:", cmd_node_dict.get("description")[:100])
        print("FLAGS:", cmd_node_dict.get("flags"))
        print("FLAGS (if any):", cmd_node_dict.get("flags")) # Checking for this
        
        if simplify_command_synopsis:
            cmd = CommandNode(
                service="storage",
                group_path=["insights", "inventory-reports"],
                name="list",
                node=cmd_node_dict
            )
            synopsis = simplify_command_synopsis("storage", cmd)
            print("GENERATED SYNOPSIS:", synopsis)
    else:
        print("Command not found.")

if __name__ == "__main__":
    main()

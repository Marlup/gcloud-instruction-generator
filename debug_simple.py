
import json
import os

def find_command(node, path_suffix):
    base_commands = node.get("base_commands", {})
    if len(path_suffix) == 1 and path_suffix[0] in base_commands:
        return base_commands[path_suffix[0]]

    base_groups = node.get("base_groups", {})
    if len(path_suffix) > 1 and path_suffix[0] in base_groups:
        return find_command(base_groups[path_suffix[0]], path_suffix[1:])
    
    return None

def main():
    json_path = "data/webscrap/landing/storage/storage_command.json"
    print(f"Reading {json_path}...")
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        print("Loaded.")
    except Exception as e:
        print(f"Error loading: {e}")
        return

    cmd_node_dict = find_command(data, ["insights", "inventory-reports", "list"])
    
    if cmd_node_dict:
        print("FOUND NODE KEYS:", list(cmd_node_dict.keys()))
        print("SYNOPSIS:", cmd_node_dict.get("command_synopsis"))
        
        # Check for flags
        keys = cmd_node_dict.keys()
        if "flags" in keys:
            print("HAS 'flags' ARRAY/DICT")
            flags = cmd_node_dict["flags"]
            print(f"Type of flags: {type(flags)}")
            if isinstance(flags, list) and len(flags) > 0:
                print("First flag:", flags[0])
            elif isinstance(flags, dict) and len(flags) > 0:
                print("First flag:", list(flags.items())[0])
        else:
            print("NO 'flags' KEY found. Keys are:", list(keys))

    else:
        print("Command not found.")

if __name__ == "__main__":
    main()

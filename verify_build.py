
import sys
import json
import os

# Ensure backend can be imported
sys.path.append(os.getcwd())

from backend.actions.build_actions import simplify_command_synopsis, CommandNode

# Mock node with brackets in synopsis
node_data = {
    "command_synopsis": "gcloud storage buckets list [--project=PROJECT_ID] [--location=LOCATION] [--filter=EXPRESSION]",
    "description": "List buckets.",
    "positional_args": {},
    "flags": {}
}

cmd = CommandNode(
    service="storage",
    group_path=["buckets"],
    name="list",
    node=node_data
)

try:
    match = simplify_command_synopsis("storage", cmd)
    # expected tuple (str, list)
    result = {
        "output_type": str(type(match)),
        "template": match[0],
        "flags": match[1]
    }
except Exception as e:
    result = {"error": str(e)}

with open("verification_result.txt", "w") as f:
    json.dump(result, f, indent=2)

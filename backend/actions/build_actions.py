#!/usr/bin/env python3
"""
build_actions.py

Purpose:
    Read normalized gcloud documentation JSON files for one or more services
    and generate curated "actions" JSON files grouped by:
      - service
      - resource (e.g. buckets, objects, iam_and_security)
      - category (reading, creation, modification, revoke, assignment)

    The curated JSON files are intended to be consumed by a UI that renders
    each action as a clickable command with editable parameters.

Usage:
    python build_actions.py --config=actions_config.json
    python build_actions.py --config=actions_config.json --services storage,bigquery
"""

from __future__ import annotations

import re
import logging
import argparse
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


#==============================================
# Loging setup
#==============================================

logging.getLogger(__name__)

# ==============================================
# Data models
# ==============================================

CATEGORY_READING = "reading"
CATEGORY_CREATION = "creation"
CATEGORY_MODIFICATION = "modification"
CATEGORY_REVOKE = "revoke"
CATEGORY_ASSIGNMENT = "assignment"

ALL_CATEGORIES = {
    CATEGORY_READING,
    CATEGORY_CREATION,
    CATEGORY_MODIFICATION,
    CATEGORY_REVOKE,
    CATEGORY_ASSIGNMENT,
}


@dataclass
class ServiceConfig:
    """
    Purpose:
        Store configuration for processing a single gcloud service.

    Args:
        name:
            Service name (e.g. "storage", "bigquery").
        input_dir:
            Directory where the gcloud documentation JSON files live.
        output_dir:
            Base directory where curated action JSONs will be written.
        resource_map:
            Optional mapping from group names (from service_name path) to
            resource directory names (e.g. {"buckets": "buckets",
            "managed-folders": "buckets"}).
    """
    name: str
    input_dir: Path
    output_dir: Path
    resource_map: Dict[str, str] = field(default_factory=dict)


@dataclass
class GlobalConfig:
    """
    Purpose:
        Store global configuration loaded from config file.

    Args:
        services:
            List of service names to process by default.
        input_dir:
            Base directory for input gcloud documentation JSONs.
        output_dir:
            Base directory for generated actions.
        resource_maps:
            Optional mapping of per-service resource mappings.
            Example:
                {
                  "storage": {
                    "resource_map": {
                      "buckets": "buckets",
                      "managed-folders": "buckets",
                      "objects": "objects",
                      "hmac": "iam_and_security"
                    }
                  }
                }
    """
    services: List[str]
    input_dir: Path
    output_dir: Path
    resource_maps: Dict[str, Dict[str, Any]] = field(default_factory=dict)


@dataclass
class CommandNode:
    """
    Purpose:
        Represent a single gcloud command discovered in the documentation tree.

    Args:
        service:
            Service name (e.g. "storage").
        group_path:
            List of CLI group components from root to parent of command
            (e.g. ["buckets", "anywhere-caches"]).
        name:
            Command name (e.g. "create", "list", "describe").
        node:
            Original JSON node for the command (contains description,
            command_synopsis, positional_args, required_flags, optional_flags, flags, etc.).
    """
    service: str
    group_path: List[str]
    name: str
    node: Dict[str, Any]


@dataclass
class ActionDefinition:
    """
    Purpose:
        Curated action that will be written to a JSON file.

    Args:
        label:
            Human-readable label (e.g. "Create bucket").
        cmd:
            Command template with placeholders in curly braces.
        params:
            List of placeholder names used in cmd.
        flags:
            List of optional flags dictionaries.
            Example: [{"flag": "--location", "placeholder": "LOCATION"}]
        explanation:
            Short English description of the action.
    """
    label: str
    cmd: str
    params: List[str]
    flags: List[Dict[str, str]]
    explanation: str


# ==============================================
# Config loading
# ==============================================

def load_global_config(path: Path=Path("backend/config/actions_config.json")) -> GlobalConfig:
    """
    Purpose:
        Load global configuration from a JSON file.
        If "services" is omitted, discover all valid services from the folder structure.

    Args:
        path:
            Path to config file.

    Returns:
        GlobalConfig:
            Parsed configuration object.

    Raises:
        FileNotFoundError:
            If the config file does not exist.
        ValueError:
            If required fields are missing or malformed.
    """
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    #data = json.loads(path.read_text(encoding="utf-8"))
    logging.info(f"reading from config : {path}")
    with open(path, "r") as f:
        data = json.load(f)

    try:
        gcloud_docs_dir = Path(data["gcloud_docs_dir"])
        output_dir = Path(data["output_dir"])
    except KeyError as exc:
        raise ValueError(f"Missing required key in config: {exc}") from exc

    # optional services in config
    services = data.get("services")
    if services is None:
        services = discover_available_services(gcloud_docs_dir)

    resource_maps = data.get("resource_maps", {})

    return GlobalConfig(
        services=services,
        input_dir=gcloud_docs_dir,
        output_dir=output_dir,
        resource_maps=resource_maps,
    )


def build_service_configs(
    global_config: GlobalConfig,
    override_services: Optional[List[str]] = None,
) -> List[ServiceConfig]:
    """
    Purpose:
        Combine CLI override + discovered services.

    Args:
        global_config:
            GlobalConfig loaded from the config file.
        override_services:
            Optional list of service names provided via CLI. When present,
            this list overrides the services field from global_config.

    Returns:
        List[ServiceConfig]:
            Config objects for each service to process.
    """
    services = override_services if override_services else global_config.services

    service_configs = []
    for service in services:
        service_cfg = global_config.resource_maps.get(service, {})
        resource_map = service_cfg.get("resource_map", {})

        service_configs.append(
            ServiceConfig(
                name=service,
                input_dir=global_config.input_dir,
                output_dir=global_config.output_dir,
                resource_map=resource_map,
            )
        )

    return service_configs


# ==============================================
# Documentation traversal
# ==============================================

def load_service_doc(service_config: ServiceConfig) -> Dict[str, Any]:
    """
    Purpose:
        Load the normalized gcloud documentation JSON for a given service:
        convention => <input_dir>/<service>/<service>_command.json

    Args:
        service_config:
            Configuration for the service to process.

    Returns:
        dict:
            Parsed JSON representing the gcloud doc tree.

    Raises:
        FileNotFoundError:
            If the documentation file for the service does not exist.
    """
    folder = service_config.input_dir / service_config.name
    json_path = folder / f"{service_config.name}_command.json"

    if not json_path.exists():
        raise FileNotFoundError(
            f"Gcloud command file not found: {json_path}"
        )

    #return json.loads(json_path.read_text(encoding="utf-8"))
    with open(json_path, "r") as f:
        return json.load(f)


def iter_commands(
    service_name: str,
    node: Dict[str, Any],
    group_path: Optional[List[str]] = None,
) -> Iterable[CommandNode]:
    """
    Purpose:
        Recursively traverse the gcloud doc tree and yield all leaf commands.

    Args:
        service_name:
            Name of the service (e.g. "storage").
        node:
            Current node in the doc tree.
        group_path:
            Accumulated list of group names from root to this node.

    Yields:
        CommandNode:
            One object per gcloud CLI command discovered.
    """
    if group_path is None:
        group_path = []
    
    if not node:
        raise AttributeError(
            f"node is {node}"
        )

    # Commands at this level
    base_commands = node.get("base_commands", {})
    for cmd_name, cmd_node in base_commands.items():
        if not cmd_name:
            print("\t", cmd_name, cmd_node)
            continue
        yield CommandNode(
            service=service_name,
            group_path=list(group_path),
            name=cmd_name,
            node=cmd_node,
        )

    # Nested groups
    base_groups = node.get("base_groups", {})
    for group_name, group_node in base_groups.items():
        if not group_node:
            print("\t", group_name, group_node)
            continue
        new_path = list(group_path) + [group_name]
        yield from iter_commands(service_name, group_node, new_path)


# ==============================================
# Mapping: group -> resource, command -> category
# ==============================================

def map_group_to_resource(
    service_config: ServiceConfig,
    group_path: List[str],
) -> str:
    """
    Purpose:
        Map a gcloud group path to a resource directory name.

    Args:
        service_config:
            Config containing the resource_map.
        group_path:
            List of group components (e.g. ["buckets", "anywhere-caches"]).

    Returns:
        str:
            Resource directory name (e.g. "buckets", "objects",
            "iam_and_security", "transfers").

    Notes:
        - Uses the last group component by default.
        - Applies the service's resource_map if available.
        - Fallback to the raw last group name if no mapping is found.
    """
    if not group_path:
        # Top-level commands ("cp", "ls", "rm") can be assigned to a generic resource
        # or a service-specific "misc" resource.
        return "misc"

    raw_resource = group_path[0]  # e.g. "buckets", "objects", "managed-folders"
    mapped = service_config.resource_map.get(raw_resource)
    return mapped if mapped else raw_resource


def map_command_to_category(command_name: str, group_path: List[str]) -> str:
    """
    Purpose:
        Infer the category of an action from command name and group path.

    Args:
        command_name:
            CLI command name (e.g. "list", "create", "update", "delete").
        group_path:
            List of group components.

    Returns:
        str:
            One of the known category constants (reading, creation,
            modification, revoke, assignment).

    Notes:
        - This is heuristic-based and should be refined as needed.
    """
    name = command_name.lower()

    # Reading
    if name in {"list", "describe", "get", "details"}:
        return CATEGORY_READING

    # Creation
    if name in {"create", "insert", "add"}:
        # "add-iam-policy-binding" is closer to assignment, but this is resolved
        # below by checking the full path.
        if "iam" in "-".join(group_path) or "policy" in "-".join(group_path):
            if "add" in name or "set" in name:
                return CATEGORY_ASSIGNMENT
        return CATEGORY_CREATION

    # Deletion / removal (treated as modification)
    if name in {"delete", "rm", "remove"}:
        if "iam-policy-binding" in name or "iam" in "-".join(group_path):
            return CATEGORY_REVOKE
        return CATEGORY_MODIFICATION

    # Updates / configuration
    if name in {"update", "rewrite", "relocate", "set"}:
        if "iam" in "-".join(group_path) or "policy" in "-".join(group_path):
            # set-iam-policy, etc.
            return CATEGORY_ASSIGNMENT
        return CATEGORY_MODIFICATION

    # Operations related to revoke / assignment that do not follow simple verbs
    full_path = "/".join(group_path + [command_name])
    if "remove-iam-policy-binding" in full_path:
        return CATEGORY_REVOKE
    if "add-iam-policy-binding" in full_path or "set-iam-policy" in full_path:
        return CATEGORY_ASSIGNMENT

    # Default fallback
    return CATEGORY_MODIFICATION


# ==============================================
# Action building
# ==============================================

PLACEHOLDER_PATTERN = re.compile(r"\{(\w+)\}")


def build_action_label(cmd: CommandNode) -> str:
    """
    Purpose:
        Generate a human-readable label for an action.

    Args:
        cmd:
            CommandNode for which to build a label.

    Returns:
        str:
            A concise label such as "Create bucket" or "List objects".
    """
    verb = cmd.name.replace("-", " ").capitalize()
    # Try to derive resource from group path: first component is often resource
    resource = cmd.group_path[0].replace("-", " ") if cmd.group_path else cmd.service
    return f"{verb} {resource}".strip()


def simplify_command_synopsis(service: str, cmd: CommandNode) -> Tuple[str, List[Dict[str, str]]]:
    """
    Purpose:
        Produce a simplified gcloud command template from the command node.

    Args:
        service:
            Service name (e.g. "storage").
        cmd:
            CommandNode with original doc node.

    Returns:
        (str, List[Dict[str, str]]):
            - Command with placeholders in curly braces.
            - List of optional flags parsed from synopsis.

    Notes:
        - Parses positional_args, required_flags, and optional_flags from the doc.
        - Creates placeholders for each argument and flag.
        - Parses optional flags from command_synopsis.
    """
    base = ["gcloud", service] + cmd.group_path + [cmd.name]
    parts = base.copy()

    # Extract positional arguments from the node
    positional_args = cmd.node.get("positional_args", {})
    for arg_name in positional_args.keys():
        # Clean up the argument name (remove dashes, make it usable as placeholder)
        clean_name = arg_name.replace("-", "_").upper()
        parts.append(f"{{{clean_name}}}")

    # Extract REQUIRED flags -> these go into the main command 'parts' (mandatory)
    required_flags_node = cmd.node.get("required_flags", {})
    for flag_name in required_flags_node.keys():
        clean_name = flag_name.replace("-", "_").upper()
        parts.append(f"--{flag_name}={{{clean_name}}}")

    # Extract OPTIONAL flags and FLAGS -> these go into the optional checkbox list
    optional_flags = []
    
    # helper to add flags
    def _add_flags_to_list(flags_source: dict):
        for flag_name, flag_info in flags_source.items():
            content = flag_info.get("content", "")
            clean_ph = ""
            full_flag = f"--{flag_name}"
            
            if "=" in content:
                value_part = content.split("=", 1)[1]
                clean_ph = value_part.replace("[", "").replace("]", "").split(",")[0].replace("…", "").strip()
            
            optional_flags.append({
                "name": full_flag,
                "placeholder": clean_ph
            })

    # Add from "OPTIONAL-FLAGS" ID
    _add_flags_to_list(cmd.node.get("optional_flags", {}))
    # Add from "FLAGS" ID
    _add_flags_to_list(cmd.node.get("flags", {}))

    # If no positional args and no required flags, add a generic resource placeholder
    # ONLY if we didn't add anything else? 
    # Actually, relying on positional_args is better. 
    # If positional_args is empty but command effectively requires one (legacy),
    if not positional_args and not required_flags_node:
        # Some commands might be purely flag based or list commands.
        # Check command type. 'list' usually doesn't need resource arg if args empty.
        # But 'create' might.
        if "list" not in cmd.name and "create" in cmd.name:
             # Heuristic fallback
             pass

    synopsis_str = " ".join(parts)
    return synopsis_str, optional_flags


def extract_placeholders(cmd_template: str) -> List[str]:
    """
    Purpose:
        Extract placeholder names from a command template.

    Args:
        cmd_template:
            Command string containing placeholders in curly braces.

    Returns:
        list[str]:
            Unique placeholder names in the order of appearance.
    """
    seen = set()
    params: List[str] = []
    for match in PLACEHOLDER_PATTERN.finditer(cmd_template):
        name = match.group(1)
        if name not in seen:
            seen.add(name)
            params.append(name)
    return params


def build_action_definition(cmd: CommandNode) -> ActionDefinition:
    """
    Purpose:
        Build an ActionDefinition from a CommandNode.

    Args:
        cmd:
            CommandNode describing the gcloud CLI command.

    Returns:
        ActionDefinition:
            Curated action with label, command template, params and explanation.

    Notes:
        - This uses a simplified command template and description. It should be
          refined to:
            * Use key positional arguments.
            * Use important required flags as placeholders.
    """
    label = build_action_label(cmd)
    cmd_template, optional_flags = simplify_command_synopsis(cmd.service, cmd)
    params = extract_placeholders(cmd_template)

    if not cmd.node:
        raise AttributeError(
            f"Absent attribute 'node' in 'cmd.node' {cmd}'"
        )
    description = cmd.node.get("description", "").strip().replace("\n", " ")
    if not description:
        description = f"Execute gcloud {cmd.service} {' '.join(cmd.group_path + [cmd.name])}."

    explanation = description.split(".")[0].strip() + "." if "." in description else description

    return ActionDefinition(
        label=label,
        cmd=cmd_template,
        params=params,
        flags=optional_flags,
        explanation=explanation,
    )


# ==============================================
# Aggregation and file writing
# ==============================================

def validate_action(action: ActionDefinition) -> None:
    """
    Purpose:
        Validate consistency of an action definition.

    Args:
        action:
            ActionDefinition to validate.

    Raises:
        ValueError:
            If the action is inconsistent (e.g. placeholders in cmd not
            present in params).
    """
    placeholders = set(extract_placeholders(action.cmd))
    params_set = set(action.params)

    if placeholders != params_set:
        raise ValueError(
            f"Inconsistent action '{action.label}': cmd placeholders {placeholders} "
            f"do not match params {params_set}"
        )


def add_action_to_index(
    index: Dict[str, Dict[str, Dict[str, ActionDefinition]]],
    resource: str,
    category: str,
    action: ActionDefinition,
) -> None:
    """
    Purpose:
        Insert an action into a nested index [resource][category][label].

    Args:
        index:
            Nested dictionary to populate.
        resource:
            Resource name (e.g. "buckets", "objects").
        category:
            Category (reading, creation, modification, revoke, assignment).
        action:
            ActionDefinition to insert.

    Returns:
        None
    """
    if category not in ALL_CATEGORIES:
        # Ignore unknown categories or raise, depending on strictness preference
        # For now, we treat unknown as modification.
        category = CATEGORY_MODIFICATION

    index.setdefault(resource, {}).setdefault(category, {})
    index[resource][category][action.label] = action


def write_actions_to_files(
    service_config: ServiceConfig,
    actions_index: Dict[str, Dict[str, Dict[str, ActionDefinition]]],
    dry_run: bool = False,
) -> None:
    """
    Purpose:
        Write curated action definitions to JSON files per resource and category.

    Args:
        service_config:
            Configuration for the service (contains output_dir).
        actions_index:
            Nested dict: {resource: {category: {label: ActionDefinition}}}.
        dry_run:
            If True, do not actually write files, only print planned paths.

    Returns:
        None
    """
    base_dir = service_config.output_dir / service_config.name
    for resource, categories in actions_index.items():
        for category, actions in categories.items():
            if not actions:
                continue

            resource_dir = base_dir / resource
            resource_dir.mkdir(parents=True, exist_ok=True)

            out_path = resource_dir / f"{category}.json"

            # Convert to plain JSON dict
            json_obj: Dict[str, Dict[str, Any]] = {}
            for label, action in actions.items():
                json_obj[label] = {
                    "cmd": action.cmd,
                    "params": action.params,
                    "flags": action.flags,
                    "explanation": action.explanation,
                }

            if dry_run:
                print(f"[DRY-RUN] Would write {out_path} with {len(json_obj)} actions")
                continue

            out_path.write_text(
                json.dumps(json_obj, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            print(f"Wrote {out_path} ({len(json_obj)} actions)")


# ==============================================
# Main orchestration
# ==============================================

def process_service(
    service_config: ServiceConfig,
    dry_run: bool = False,
) -> None:
    """
    Purpose:
        Process a single service: load doc, extract commands, map to actions,
        and write out curated JSON files.

    Args:
        service_config:
            Service configuration.
        dry_run:
            If True, do not write files, only show planned output.

    Returns:
        None
    """
    doc = load_service_doc(service_config)
    actions_index: Dict[str, Dict[str, Dict[str, ActionDefinition]]] = {}

    for cmd_node in iter_commands(service_config.name, doc):
        resource = map_group_to_resource(service_config, cmd_node.group_path)
        category = map_command_to_category(cmd_node.name, cmd_node.group_path)

        try:
            action = build_action_definition(cmd_node)
        except AttributeError as exc:
            print(f"Skipping invalid action definition. cmd_node '{cmd_node.node}': {exc}")
            continue
        try:
            validate_action(action)
        except ValueError as exc:
            # Depending on strictness you might want to log and continue instead.
            print(f"Skipping invalid action '{action.label}': {exc}")
            continue

        add_action_to_index(actions_index, resource, category, action)

    write_actions_to_files(service_config, actions_index, dry_run=dry_run)


def parse_args() -> argparse.Namespace:
    """
    Purpose:
        Parse command-line arguments.

    Returns:
        argparse.Namespace:
            Parsed arguments.
    """
    parser = argparse.ArgumentParser(
        description="Generate curated gcloud actions JSON files from documentation JSONs."
    )
    parser.add_argument(
        "--config",
        type=str,
        default="backend/config/actions_config.json",
        help="Path to global config JSON file.",
    )
    parser.add_argument(
        "--services",
        type=str,
        default="",
        help="Comma-separated list of service names. If omitted, auto-discover all services."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview output paths without writing files.",
    )

    return parser.parse_args()

def discover_available_services(base_path: Path) -> List[str]:
    """
    Scan the folder structure data/web-gcloud/ to discover
    which gcloud services exist.

    Expected format:
        data/web-gcloud/<service>/<service>_command.json

    Return:
        A list of service names, e.g. ["storage", "bq", "auth", ...]
    """
    services = []
    for entry in base_path.iterdir():
        if not entry.is_dir():
            continue
        # the JSON is expected as: <service>/<service>_command.json
        json_path = entry / f"{entry.name}_command.json"
        if json_path.exists():
            services.append(entry.name)

    if not services:
        raise services
    return sorted(services)

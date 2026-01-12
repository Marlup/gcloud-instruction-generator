#!/usr/bin/env python3
"""
build_actions.py

Purpose:
    Read scrapped gcloud documentation JSON files (flat structure) for one or more services
    and generate a single curated "actions.json" file per service grouped by:
      - resource (e.g. buckets, objects)
      - hierarchical command structure

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
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union

#==============================================
# Loging setup
#==============================================

logging.getLogger(__name__)

# ==============================================
# Data models
# ==============================================

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
    """
    services: List[str]
    input_dir: Path
    output_dir: Path
    resource_map: Dict[str, Dict[str, Any]] = field(default_factory=dict)


@dataclass
class CommandNode:
    """
    Purpose:
        Represent a single gcloud command extracted from the flat list.
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
    """
    label: str
    cmd: str
    params: List[str]
    flags: List[Dict[str, str]]
    explanation: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cmd": self.cmd,
            "params": self.params,
            "flags": self.flags,
            "explanation": self.explanation
        }


# Type definition for the nested action tree
# It can be a nested dictionary returning eventually an ActionDefinition (or its dict representation)
ActionTree = Dict[str, Union['ActionTree', Dict[str, Any]]]


# ==============================================
# Config loading
# ==============================================

def load_global_config(path: Path=Path("backend/config/actions_config.json")) -> GlobalConfig:
    """
    Load global configuration from a JSON file.
    """
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    logging.info(f"reading from config : {path}")
    with open(path, "r") as f:
        data = json.load(f)

    try:
        # If input_dir is not absolute, assume relative to project root.
        # However, we'll respect what's in the config or default to the new location.
        # For this refactor, we prefer the new default location if not specified clearly.
        input_str = data.get("gcloud_docs_dir", "data/webscrap/landing")
        gcloud_docs_dir = Path(input_str)
        output_dir = Path(data.get("output_dir", "data/plugins"))
    except KeyError as exc:
        raise ValueError(f"Missing required key in config: {exc}") from exc

    services = data.get("services")
    if services is None:
        services = discover_available_services(gcloud_docs_dir)

    resource_map = data.get("resource_map", {})

    return GlobalConfig(
        services=services,
        input_dir=gcloud_docs_dir,
        output_dir=output_dir,
        resource_map=resource_map,
    )


def build_service_configs(
    global_config: GlobalConfig,
    override_services: Optional[List[str]] = None,
) -> List[ServiceConfig]:
    services = override_services if override_services else global_config.services

    service_configs = []
    for service in services:
        service_cfg = global_config.resource_map.get(service, {})
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
# Documentation traversal (Flat)
# ==============================================

def load_service_commands(service_config: ServiceConfig) -> List[Dict[str, Any]]:
    """
    Load the normalized flat gcloud command list for a given service.
    Path: <input_dir>/<service>/<service>_commands.json
    """
    # Adjust path to match the discovered structure: data/webscrap/landing/storage/storage_commands.json
    # input_dir should be 'data/webscrap/landing'
    folder = service_config.input_dir / service_config.name
    json_path = folder / f"{service_config.name}_commands.json"

    if not json_path.exists():
        # Fallback check: maybe input_dir was just 'data/services' or similar?
        # Let's try to be robust or just fail.
        raise FileNotFoundError(
            f"Gcloud commands file not found: {json_path}"
        )

    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def iter_commands(
    service_config: ServiceConfig,
    commands_list: List[Dict[str, Any]]
) -> Iterable[CommandNode]:
    """
    Iterate over the flat list of items and yield those that are commands.
    """
    for item in commands_list:
        if item.get("type") != "command":
            continue

        full_path = item.get("path", [])
        if not full_path:
            continue

        # e.g. ["storage", "buckets", "create"]
        # service = "storage"
        # name = "create"
        # group_path = ["storage", "buckets"]
        
        # Le's clean up the path.
        path_segments = [p for p in full_path if p]
        
        # Remove service name from start if present (it usually is)
        if path_segments and path_segments[0] == service_config.name:
            path_segments.pop(0)
            
        if not path_segments:
            # Should not happen for a command inside a service, unless it's just 'gcloud service' command?
            continue

        command_name = path_segments[-1]
        group_path = path_segments[:-1]

        yield CommandNode(
            service=service_config.name,
            group_path=group_path,
            name=command_name,
            node=item,
        )


# ==============================================
# Mapping
# ==============================================


def map_group_to_resource(
    service_config: ServiceConfig,
    group_path: List[str],
) -> str:
    """
    Map a gcloud group path to a resource directory name.
    """
    if not group_path:
        # If no group path, it belongs to the service's main bucket/group
        return service_config.name

    raw_resource = group_path[0]  # e.g. "buckets", "objects"
    mapped = service_config.resource_map.get(raw_resource)
    return mapped if mapped else raw_resource


# ==============================================
# Action building
# ==============================================

PLACEHOLDER_PATTERN = re.compile(r"\{(\w+)\}")

def build_action_label(cmd: CommandNode) -> str:
    verb = cmd.name.replace("-", " ").capitalize()
    # If we have a group path, append the direct parent if meaningful? 
    # Or just Verb + Resource.
    # storage buckets create -> "Create buckets" (if resource is 'buckets')
    # storage buckets anywhere-caches create -> "Create anywhere caches"
    
    resource_suffix = ""
    if cmd.group_path:
        # Use the last group component as the specific subject
        resource_suffix = cmd.group_path[-1].replace("-", " ")
    else:
        resource_suffix = cmd.service

    # Avoid redundancy if verb includes resource name? (rare in gcloud utils)
    return f"{verb} {resource_suffix}".strip()


def simplify_command_synopsis(service: str, cmd: CommandNode) -> Tuple[str, List[Dict[str, str]]]:
    """
    Reconstruct command template and extract flags from the new flat JSON format.
    The new JSON has 'positional_args', 'required_flags', 'optional_flags', 'flags'.
    """
    
    # 1. Build the base command
    parts = ["gcloud", service] + cmd.group_path + [cmd.name]
    
    # 2. Add Positional Args
    # The JSON has them in a dict. Order helps if we can trust keys iteration or need sorting?
    # Usually positional args order matters. The JSON dict keys might not be ordered preserved in extremely old python,
    # but 3.9+ is fine. However, 'positional_args' key in JSON doesn't strictly guarantee order in the schema definition,
    # but the synopsis string does.
    # Let's check command_synopsis first.
    synopsis = cmd.node.get("command_synopsis", "")
    
    # If we use synopsis, we have to parse it. 
    # Or we can construct it from the dicts if we assume an order.
    # Let's try to trust the 'positional_args' dict keys as ordered.
    
    pos_args = cmd.node.get("positional_args", {})
    for arg_name in pos_args:
        # clean name
        # Remove brackets if they are optional indicators in key (usually not in key)
        clean = arg_name.replace("-", "_").replace("[", "").replace("]", "").replace("…", "").upper()
        parts.append(f"{{{clean}}}")

    # 3. Add Required Flags
    req_flags = cmd.node.get("required_flags", {})
    for flag_name in req_flags:
        # flag_name is usually "bucket" for "--bucket"
        clean = flag_name.replace("-", "_").upper()
        parts.append(f"--{flag_name}={{{clean}}}")

    # 4. Optional Flags for checkboxes
    optional_flags = []
    
    def _add_flags(source: Dict[str, Any]):
        for flag_key, flag_data in source.items():
            # flag_key is like "location" or "retention-period"
            # content is like "--location=LOCATION, -l LOCATION"
            
            # We want the main long flag
            full_flag = f"--{flag_key}"
            
            # Determine placeholder if any
            # We can look at 'content' or guess.
            placeholder = ""
            content = flag_data.get("content", "")
            if "=" in content:
                # content: "--flag=VALUE"
                val_part = content.split("=", 1)[1]
                # Cleanup: "VALUE, -f VALUE" -> "VALUE"
                clean_ph = val_part.split(",")[0].strip()
                # remove optional brackets if any
                clean_ph = clean_ph.replace("[", "").replace("]", "").replace("…", "")
                placeholder = clean_ph
            
            optional_flags.append({
                "name": full_flag,
                "placeholder": placeholder
            })

    _add_flags(cmd.node.get("optional_flags", {}))
    _add_flags(cmd.node.get("flags", {}))

    return " ".join(parts), optional_flags


def extract_placeholders(cmd_template: str) -> List[str]:
    seen = set()
    params: List[str] = []
    for match in PLACEHOLDER_PATTERN.finditer(cmd_template):
        name = match.group(1)
        if name not in seen:
            seen.add(name)
            params.append(name)
    return params


def build_action_definition(cmd: CommandNode) -> ActionDefinition:
    label = build_action_label(cmd)
    cmd_template, optional_flags = simplify_command_synopsis(cmd.service, cmd)
    params = extract_placeholders(cmd_template)

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
# Aggregation and writing
# ==============================================

def validate_action(action: ActionDefinition) -> None:
    placeholders = set(extract_placeholders(action.cmd))
    params_set = set(action.params)
    if placeholders != params_set:
        raise ValueError(f"Inconsistent action '{action.label}'")


def write_single_actions_file(
    service_config: ServiceConfig,
    actions_index: Dict[str, ActionTree],
    dry_run: bool = False,
) -> None:
    """
    Write all curated actions for a service to a single JSON file.
    Output structure:
    {
      "resource_name": {
         "subcommand": {
             "__action": { "cmd": ... }
             "subcommand": { ... }
         }
      }
    }
    """
    resource_dir = service_config.output_dir / service_config.name
    if not dry_run:
        resource_dir.mkdir(parents=True, exist_ok=True)
    
    out_path = resource_dir / "actions.json"

    if dry_run:
        print(f"[DRY-RUN] Will write layout to {out_path}")
        print(f"Resources found: {list(actions_index.keys())}")
        return

    out_path.write_text(
        json.dumps(actions_index, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
    print(f"Wrote actions to {out_path}")


# ==============================================
# Main
# ==============================================

def process_service(service_config: ServiceConfig, dry_run: bool = False) -> None:
    try:
        commands = load_service_commands(service_config)
    except FileNotFoundError as e:
        print(f"Skipping {service_config.name}: {e}")
        return

    # Structure: Dict[ResourceName, NestedTree]
    actions_index: Dict[str, ActionTree] = {}

    for cmd_node in iter_commands(service_config, commands):
        # 1. Determine Resource (Top Level Group)
        resource = map_group_to_resource(service_config, cmd_node.group_path)
        
        # 2. Build the tree path
        full_command_path = cmd_node.group_path + [cmd_node.name]
        
        if cmd_node.group_path:
            # We used group_path[0] for resource mapping.
            
            first_segment = cmd_node.group_path[0]
            mapped_resource = map_group_to_resource(service_config, cmd_node.group_path)
            
            # If the mapped resource is exactly the first segment, we can strip it.
            if mapped_resource == first_segment:
                tree_path = full_command_path[1:]
            else:
                # If it was remapped, we keep it.
                tree_path = full_command_path
        else:
            # top level command in service
            tree_path = full_command_path
            
        if not tree_path:
            tree_path = [cmd_node.name]

        try:
            action = build_action_definition(cmd_node)
            validate_action(action)
        except Exception as exc:
            # print(f"Skipping action for {cmd_node.name}: {exc}")
            continue

        # Insert into tree
        actions_index.setdefault(resource, {})
        current_level = actions_index[resource]
        
        for i, segment in enumerate(tree_path):
            is_last = (i == len(tree_path) - 1)
            
            if is_last:
                # Assign action definition encapsulated in __action
                current_level.setdefault(segment, {})["action"] = action.to_dict()
            else:
                current_level = current_level.setdefault(segment, {})
                # No issue if keys exist


    write_single_actions_file(service_config, actions_index, dry_run=dry_run)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, default="backend/config/actions_config.json")
    parser.add_argument("--services", type=str, default="")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def discover_available_services(base_path: Path) -> List[str]:
    """
    Discover services by listing directories in the base_path.
    """
    if not base_path.exists():
        return []
    return [d.name for d in base_path.iterdir() if d.is_dir()]


def main() -> None:
    args = parse_args()
    config_path = Path(args.config)
    global_cfg = load_global_config(config_path)

    override_services = None
    if args.services:
        override_services = [s.strip() for s in args.services.split(",") if s.strip()]

    service_configs = build_service_configs(global_cfg, override_services)

    for service_cfg in service_configs:
        print(f"Processing service: {service_cfg.name}")
        process_service(service_cfg, dry_run=args.dry_run)


if __name__ == "__main__":
    main()

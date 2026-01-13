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

import logging
from pathlib import Path
from typing import List, Optional

from backend.actions.build_actions import (
    parse_args,
    load_global_config, 
    build_service_configs, 
    process_service
)

#==============================================
# Loging setup
#==============================================

logging.basicConfig(
   level=logging.INFO,
   filename="data/curation-run.log",
   filemode="a",        # "a" = append, "w" = overwrite
   format="%(asctime)s [%(levelname)s] %(message)s"
)

def main() -> None:
    """
    Purpose:
        Entry point: load config, resolve services, and process each service.

    Returns:
        None
    """
    args = parse_args()
    config_path = Path(args.config)

    global_cfg = load_global_config(config_path)

    override_services: Optional[List[str]] = None
    if args.services:
        override_services = [s.strip() for s in args.services.split(",") if s.strip()]

    service_configs = build_service_configs(global_cfg, override_services)

    for service_cfg in service_configs:
        print(f"Processing service: {service_cfg.name}")
        process_service(service_cfg, dry_run=args.dry_run)


if __name__ == "__main__":
    main()

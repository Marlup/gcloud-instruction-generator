import logging
import argparse
from backend.services.knowledge_updater import GCPKnowledgeUpdater
from backend.core.types.enums import UpdateMode

logging.basicConfig(
    level=logging.INFO,
    filename="data/web-cloud-updater-run.log",
    filemode="a",
    format="%(asctime)s [%(levelname)s] %(message)s"
)

def parse_args():
    parser = argparse.ArgumentParser(
        description="Run GCP knowledge updater with mode + optional target services"
    )

    parser.add_argument(
        "--update-mode",
        type=str,
        required=True,
        choices=[m.name.lower() for m in UpdateMode],
        help="Update mode: single | partial | full | patch"
    )

    parser.add_argument(
        "--services",
        type=str,
        required=False,
        default="",
        help="Comma-separated list of services: e.g. storage,iam,bq"
    )
    
    parser.add_argument(
        "--patch-services",
        type=str,
        required=False,
        default="",
        help="(PATCH mode only) Comma-separated list of services to patch. If not provided, all services with unprocessed.json will be patched."
    )

    args = parser.parse_args()

    # Convert mode to enum
    mode = UpdateMode[args.update_mode.upper()]

    # Clean services list (comma-separated)
    if args.services.strip():
        target_services = [s.strip() for s in args.services.split(",") if s.strip()]
    else:
        target_services = []
    
    # For PATCH mode, use patch_services if provided, otherwise use services
    if mode == UpdateMode.PATCH:
        if args.patch_services.strip():
            target_services = [s.strip() for s in args.patch_services.split(",") if s.strip()]
        elif not target_services:
            # No services specified, will process all services with unprocessed.json
            target_services = None

    return mode, target_services


def main():
    mode, target_services = parse_args()

    updater = GCPKnowledgeUpdater()

    updater.run_update(
        mode=mode,
        target_services=target_services
    )


if __name__ == "__main__":
    main()

# ✔️ Example Executions

# Partial update for selected services
# python main_webscrap.py --update-mode partial --services storage,iam,billing,bq

# Single update for one service
# python main_webscrap.py --update-mode single --services storage bq

# Full update (services argument ignored)
# python main_webscrap.py --update-mode full

# Patch mode - process all unscraped entities from all services
# python main_webscrap.py --update-mode patch

# Patch mode - process unscraped entities from specific services only
# python main_webscrap.py --update-mode patch --patch-services billing,storage,iam


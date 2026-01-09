import logging
import argparse
from backend.services.knowledge_updater import GCPKnowledgeUpdater
from backend.services.parallel.threading_updater import ThreadingGCPKnowledgeUpdater
from backend.services.parallel.threading_config import ThreadingConfig
from backend.core.types.enums import UpdateMode

logging.basicConfig(
    level=logging.INFO,
    filename="data/web-cloud-updater-run.log",
    filemode="a",
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# Also log to console for parallel mode
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
logging.getLogger().addHandler(console_handler)

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
    
    # Parallel processing options
    parser.add_argument(
        "--parallel",
        action="store_true",
        help="Enable parallel processing (3-5x faster)"
    )
    
    parser.add_argument(
        "--n-fetchers",
        type=int,
        default=4,
        help="Number of fetcher workers (default: 4)"
    )
    
    parser.add_argument(
        "--n-scrapers",
        type=int,
        default=4,
        help="Number of scraper workers (default: 4)"
    )
    
    parser.add_argument(
        "--n-io",
        type=int,
        default=2,
        help="Number of I/O workers (default: 2)"
    )
    
    parser.add_argument(
        "--rate-limit",
        type=float,
        default=0.1,
        help="Delay between requests in seconds (default: 0.1)"
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

    return mode, target_services, args


def main():
    mode, target_services, args = parse_args()

    if args.parallel:
        # Use threading updater (Windows-compatible)
        logging.info("Using THREADING processing mode (Windows-compatible)")
        logging.info(f"Workers: {args.n_fetchers} fetchers, {args.n_scrapers} scrapers, {args.n_io} I/O")
        
        config = ThreadingConfig(
            n_fetchers=args.n_fetchers,
            n_scrapers=args.n_scrapers,
            n_io=args.n_io,
            rate_limit_delay=args.rate_limit
        )
        
        updater = ThreadingGCPKnowledgeUpdater(config=config)
        summary = updater.run_update(
            mode=mode,
            target_services=target_services
        )
        
        # Print summary
        print("\n" + "=" * 60)
        print("THREADING UPDATE SUMMARY")
        print("=" * 60)
        print(f"Total Services:    {summary.get('total_services', 0)}")
        print(f"Total Saved:       {summary.get('total_saved', 0)}")
        print(f"Total Errors:      {summary.get('total_errors', 0)}")
        print(f"Success Rate:      {summary.get('success_rate', 0):.2f}%")
        print(f"Duration:          {summary.get('duration_seconds', 0):.2f}s")
        print("=" * 60)
    else:
        # Use sequential updater
        logging.info("Using SEQUENTIAL processing mode")
        updater = GCPKnowledgeUpdater()
        updater.run_update(
            mode=mode,
            target_services=target_services
        )


if __name__ == "__main__":
    main()

# ✔️ Example Executions

# === SEQUENTIAL MODE (Original) ===

# Single update for one service
# python main_webscrap.py --update-mode single --services storage

# Partial update for selected services
# python main_webscrap.py --update-mode partial --services storage,iam,billing,bq

# Full update (all services)
# python main_webscrap.py --update-mode full

# Patch mode - process all unscraped entities
# python main_webscrap.py --update-mode patch

# Patch mode - specific services only
# python main_webscrap.py --update-mode patch --patch-services billing,storage,iam


# === PARALLEL MODE (3-5x Faster) ===

# Single service with parallel processing
# python main_webscrap.py --update-mode single --services storage --parallel

# Partial update with parallel (default: 4 fetchers, 4 scrapers, 2 I/O)
# python main_webscrap.py --update-mode partial --services compute,storage,ai --parallel

# Full update with parallel (high performance)
# python main_webscrap.py --update-mode full --parallel --n-fetchers 6 --n-scrapers 6 --n-io 3

# Conservative parallel (server-friendly)
# python main_webscrap.py --update-mode single --services storage --parallel --n-fetchers 2 --n-scrapers 2 --n-io 1 --rate-limit 0.5


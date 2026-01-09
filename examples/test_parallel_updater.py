"""
Example usage of the parallel GCP knowledge updater.

This script demonstrates how to use the parallel processing system
to scrape Google Cloud documentation.
"""

import logging
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.services.parallel import ParallelGCPKnowledgeUpdater, ParallelConfig
from backend.core.types.enums import UpdateMode


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)


def example_single_service():
    """Example: Update a single service."""
    logger.info("=" * 60)
    logger.info("Example 1: Single Service Update")
    logger.info("=" * 60)
    
    # Configure with reduced workers for testing
    config = ParallelConfig(
        n_fetchers=2,
        n_scrapers=2,
        n_io=1,
        rate_limit_delay=0.2,  # Be nice to the server
        enable_progress_logging=True
    )
    
    # Create updater
    updater = ParallelGCPKnowledgeUpdater(config=config)
    
    # Run update for single service
    logger.info("Updating service: 'storage'")
    summary = updater.run_update(UpdateMode.SINGLE, target_services="storage")
    
    # Print summary
    print_summary(summary)


def example_partial_services():
    """Example: Update multiple specific services."""
    logger.info("=" * 60)
    logger.info("Example 2: Partial Services Update")
    logger.info("=" * 60)
    
    # Configure
    config = ParallelConfig(
        n_fetchers=3,
        n_scrapers=3,
        n_io=2,
        rate_limit_delay=0.15
    )
    
    # Create updater
    updater = ParallelGCPKnowledgeUpdater(config=config)
    
    # Update specific services
    services = ["compute", "storage", "ai"]
    logger.info(f"Updating services: {services}")
    summary = updater.run_update(UpdateMode.PARTIAL, target_services=services)
    
    # Print summary
    print_summary(summary)


def example_full_update():
    """Example: Update all services (WARNING: This takes a long time!)."""
    logger.info("=" * 60)
    logger.info("Example 3: Full Update (All Services)")
    logger.info("=" * 60)
    
    # Configure with more workers for full update
    config = ParallelConfig(
        n_fetchers=6,
        n_scrapers=6,
        n_io=3,
        rate_limit_delay=0.1,
        enable_progress_logging=True
    )
    
    # Create updater
    updater = ParallelGCPKnowledgeUpdater(config=config)
    
    # Run full update
    logger.info("Starting full update of all services...")
    logger.warning("This may take 10-30 minutes depending on your connection!")
    summary = updater.run_update(UpdateMode.FULL)
    
    # Print summary
    print_summary(summary)


def print_summary(summary: dict):
    """Print formatted summary."""
    print("\n" + "=" * 60)
    print("UPDATE SUMMARY")
    print("=" * 60)
    print(f"Total Services:     {summary.get('total_services', 0)}")
    print(f"Total Fetched:      {summary.get('total_fetched', 0)}")
    print(f"Total Scraped:      {summary.get('total_scraped', 0)}")
    print(f"Total Saved:        {summary.get('total_saved', 0)}")
    print(f"Total Errors:       {summary.get('total_errors', 0)}")
    print(f"Total Unprocessed:  {summary.get('total_unprocessed', 0)}")
    print(f"Success Rate:       {summary.get('success_rate', 0):.2f}%")
    print(f"Duration:           {summary.get('duration_seconds', 0):.2f}s")
    
    worker_config = summary.get('worker_config', {})
    if worker_config:
        print(f"\nWorker Configuration:")
        print(f"  Fetchers:  {worker_config.get('n_fetchers', 0)}")
        print(f"  Scrapers:  {worker_config.get('n_scrapers', 0)}")
        print(f"  I/O:       {worker_config.get('n_io', 0)}")
        print(f"  Total:     {worker_config.get('total_workers', 0)}")
    
    print("=" * 60)
    print()


if __name__ == "__main__":
    # Choose which example to run
    import sys
    
    if len(sys.argv) > 1:
        example = sys.argv[1]
    else:
        print("Usage: python test_parallel_updater.py <example>")
        print("\nExamples:")
        print("  single  - Update single service (storage)")
        print("  partial - Update multiple services (compute, storage, ai)")
        print("  full    - Update all services (WARNING: Long running!)")
        print("\nDefaulting to 'single' example...")
        example = "single"
    
    try:
        if example == "single":
            example_single_service()
        elif example == "partial":
            example_partial_services()
        elif example == "full":
            example_full_update()
        else:
            logger.error(f"Unknown example: {example}")
            sys.exit(1)
    
    except KeyboardInterrupt:
        logger.warning("\nInterrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        sys.exit(1)

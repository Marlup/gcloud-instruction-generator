
import logging
import sys
import os

# Add backend to path
sys.path.append(os.getcwd())

from backend.services.parallel.threading_updater import ThreadingGCPKnowledgeUpdater
from backend.services.parallel.threading_config import ThreadingConfig
from backend.core.types.enums import UpdateMode

# Configure logging to stdout
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(r"c:\MyWork\main-demos\Google cloud\gcloud-instruction-generator\verification.log", mode='w'),
        logging.StreamHandler(sys.stdout)
    ]
)

def main():
    print("Starting verification of Flat List Architecture...")
    
    # Use conservative config
    config = ThreadingConfig(
        n_fetchers=1,
        n_scrapers=1,
        n_io=1,
        rate_limit_delay=0.1
    )
    
    updater = ThreadingGCPKnowledgeUpdater(config=config)
    
    # Run for 'config' service
    print("Running update for 'config' service...")
    summary = updater.run_update(
        mode=UpdateMode.SINGLE,
        target_services="config"
    )
    
    print("\nSummary:", summary)
    
    # Verify file
    expected_file = "data/webscrap/landing/config/config_commands.json"
    if os.path.exists(expected_file):
        print(f"SUCCESS: {expected_file} created.")
        size = os.path.getsize(expected_file)
        print(f"File size: {size} bytes")
    else:
        print(f"FAILURE: {expected_file} NOT found.")

if __name__ == "__main__":
    main()

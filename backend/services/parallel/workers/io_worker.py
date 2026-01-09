"""
I/O worker for file operations and unprocessed tracking.

Responsible for saving data to disk and managing unprocessed items.
"""

from multiprocessing import Queue
from typing import Optional, Tuple, Dict, List, Any
import os
import json
import logging
import tempfile

from backend.services.parallel.workers.base_worker import BaseWorker
from backend.services.parallel.shared_pools import SharedPools
from backend.services.parallel.config import ParallelConfig


logger = logging.getLogger(__name__)


class IOWorker(BaseWorker):
    """Worker for file I/O operations."""
    
    def __init__(self, worker_id: int, io_queue: Queue,
                 shared_pools: SharedPools, config: ParallelConfig):
        """
        Initialize I/O worker.
        
        Args:
            worker_id: Unique worker identifier
            io_queue: Queue with I/O tasks
            shared_pools: Shared data structures
            config: Configuration object
        """
        super().__init__(worker_id, shared_pools, config)
        self.io_queue = io_queue
        self.data_dir = config.data_dir
    
    def get_primary_queue(self) -> Queue:
        """Get primary queue (io_queue)."""
        return self.io_queue
    
    def run(self):
        """Main worker loop."""
        self.main_loop()
    
    def process_task(self, task: Dict):
        """
        Process an I/O task.
        
        Args:
            task: Dict with 'service_name'
        """
        service_name = task.get('service_name')
        
        self.logger.debug(f"Saving: {service_name}")
        
        # Get data from scrape pool
        service_data = self.shared_pools.get_from_scrape_pool(service_name)
        
        if not service_data:
            self.logger.warning(f"No data found in scrape pool for {service_name}")
            return
        
        try:
            # Save service data
            self.save_service_data(service_name, service_data)
            
            # Save unprocessed items
            unprocessed_items = self.shared_pools.get_unprocessed(service_name)
            if unprocessed_items:
                self.save_unprocessed(service_name, unprocessed_items)
            
            # Increment counter
            self.shared_pools.increment_counter('saved')
        
        except Exception as e:
            self.logger.error(f"Error saving {service_name}: {e}", exc_info=True)
            self.shared_pools.increment_counter('errors')
    
    def save_service_data(self, service_name: str, service_data: Dict):
        """
        Save ServiceCommand data to JSON file.
        
        Args:
            service_name: Service name
            service_data: ServiceCommand dict
        """
        # Create directory
        service_dir = os.path.join(self.data_dir, service_name)
        os.makedirs(service_dir, exist_ok=True)
        
        # File path
        filename = f"{service_name}_command.json"
        filepath = os.path.join(service_dir, filename)
        
        # Atomic write
        self.atomic_write(filepath, service_data)
        
        self.logger.info(f"Saved: {filepath}")
    
    def save_unprocessed(self, service_name: str, unprocessed_items: List[Dict]):
        """
        Save unprocessed items to unprocessed.json.
        
        Args:
            service_name: Service name
            unprocessed_items: List of unprocessed item dicts
        """
        # Create directory
        service_dir = os.path.join(self.data_dir, service_name)
        os.makedirs(service_dir, exist_ok=True)
        
        # File path
        filepath = os.path.join(service_dir, "unprocessed.json")
        
        # Merge with existing if file exists
        merged_items = self.merge_unprocessed(filepath, unprocessed_items)
        
        # Atomic write
        self.atomic_write(filepath, merged_items)
        
        self.logger.info(f"Saved {len(merged_items)} unprocessed items to {filepath}")
    
    def atomic_write(self, filepath: str, data: Any):
        """
        Write data to file atomically.
        
        Uses temp file + rename to prevent corruption.
        
        Args:
            filepath: Target file path
            data: Data to write (will be JSON serialized)
        """
        # Get directory
        dirpath = os.path.dirname(filepath)
        
        # Create temp file in same directory
        fd, temp_path = tempfile.mkstemp(dir=dirpath, suffix='.tmp.json')
        
        try:
            # Write to temp file
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # Rename to final path (atomic on most systems)
            if os.path.exists(filepath):
                os.remove(filepath)
            os.rename(temp_path, filepath)
        
        except Exception as e:
            # Clean up temp file on error
            try:
                os.remove(temp_path)
            except:
                pass
            raise e
    
    def merge_unprocessed(self, filepath: str, new_items: List[Dict]) -> List[Dict]:
        """
        Merge new unprocessed items with existing ones.
        
        Args:
            filepath: Path to existing unprocessed.json
            new_items: New unprocessed items
            
        Returns:
            Merged list (deduplicated by URL)
        """
        existing_items = []
        
        # Read existing if file exists
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    existing_items = json.load(f)
                    if not isinstance(existing_items, list):
                        existing_items = [existing_items]
            except (json.JSONDecodeError, ValueError) as e:
                self.logger.warning(f"Could not read existing unprocessed.json: {e}")
                existing_items = []
        
        # Merge and deduplicate by URL
        url_to_item = {}
        
        # Add existing items
        for item in existing_items:
            url = item.get('url', '')
            if url:
                url_to_item[url] = item
        
        # Add/update with new items (newer items override)
        for item in new_items:
            url = item.get('url', '')
            if url:
                url_to_item[url] = item
        
        # Convert back to list, sorted by timestamp
        merged = list(url_to_item.values())
        merged.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        return merged
    
    def try_work_stealing(self) -> Tuple[bool, Optional[Dict]]:
        """
        Try to steal work from other queues.
        
        I/O workers can't help with fetch/scrape tasks.
        
        Returns:
            Tuple of (found_work: bool, task: Dict)
        """
        return False, None

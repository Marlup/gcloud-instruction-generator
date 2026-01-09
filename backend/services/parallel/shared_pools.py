"""
Shared data structures for inter-process communication.

Provides thread-safe pools for storing parsed HTML and extracted data.
"""

import multiprocessing as mp
from multiprocessing import Manager
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class SharedPools:
    """Thread-safe shared data structures for worker coordination."""
    
    def __init__(self, manager: Manager):
        """
        Initialize shared pools.
        
        Args:
            manager: Multiprocessing Manager for shared objects
        """
        self.manager = manager
        
        # Shared dictionaries
        self.fetch_pool: Dict = manager.dict()
        self.scrape_pool: Dict = manager.dict()
        self.unprocessed: Dict = manager.dict()
        
        # Progress counters
        self.counters = manager.dict({
            'fetched': 0,
            'scraped': 0,
            'saved': 0,
            'errors': 0
        })
        
        # Control flags
        self.shutdown_flag = manager.Value('i', 0)  # 0 = running, 1 = shutdown
        
        # Locks for thread-safety
        self.fetch_lock = manager.Lock()
        self.scrape_lock = manager.Lock()
        self.unprocessed_lock = manager.Lock()
        self.counter_lock = manager.Lock()
    
    # === Fetch Pool Operations ===
    
    def add_to_fetch_pool(self, service_name: str, category: str, data: Dict):
        """
        Add parsed HTML to fetch pool.
        
        Args:
            service_name: Service name (e.g., 'storage')
            category: 'GROUPS' or 'COMMANDS'
            data: Dict with keys: name, url, html, soup
        """
        with self.fetch_lock:
            if service_name not in self.fetch_pool:
                self.fetch_pool[service_name] = self.manager.dict({
                    'GROUPS': self.manager.list(),
                    'COMMANDS': self.manager.list(),
                    'metadata': self.manager.dict({
                        'status': 'parsing',
                        'timestamp': datetime.now().isoformat()
                    })
                })
            
            # Get the category list and append
            service_dict = self.fetch_pool[service_name]
            category_list = service_dict[category]
            category_list.append(data)
            
            logger.debug(f"Added to fetch pool: {service_name}/{category}/{data.get('name')}")
    
    def get_from_fetch_pool(self, service_name: str, category: str, index: int = 0) -> Optional[Dict]:
        """
        Get and remove item from fetch pool.
        
        Args:
            service_name: Service name
            category: 'GROUPS' or 'COMMANDS'
            index: Index to pop (default 0 for FIFO)
            
        Returns:
            Data dict or None if not available
        """
        with self.fetch_lock:
            if service_name not in self.fetch_pool:
                return None
            
            service_dict = self.fetch_pool[service_name]
            category_list = service_dict[category]
            
            if len(category_list) > index:
                return category_list.pop(index)
            
            return None
    
    def has_fetch_data(self, service_name: str, category: str) -> bool:
        """Check if fetch pool has data for service/category."""
        with self.fetch_lock:
            if service_name not in self.fetch_pool:
                return False
            return len(self.fetch_pool[service_name][category]) > 0
    
    # === Scrape Pool Operations ===
    
    def add_to_scrape_pool(self, service_name: str, data: Dict):
        """
        Add extracted data to scrape pool.
        
        Args:
            service_name: Service name
            data: ServiceCommand dict
        """
        with self.scrape_lock:
            if service_name not in self.scrape_pool:
                self.scrape_pool[service_name] = self.manager.dict({
                    'data': None,
                    'metadata': self.manager.dict({
                        'status': 'extracting',
                        'timestamp': datetime.now().isoformat()
                    })
                })
            
            scrape_dict = self.scrape_pool[service_name]
            scrape_dict['data'] = data
            scrape_dict['metadata']['status'] = 'ready_to_save'
            scrape_dict['metadata']['timestamp'] = datetime.now().isoformat()
            
            logger.debug(f"Added to scrape pool: {service_name}")
    
    def get_from_scrape_pool(self, service_name: str) -> Optional[Dict]:
        """
        Get and remove data from scrape pool.
        
        Args:
            service_name: Service name
            
        Returns:
            ServiceCommand dict or None
        """
        with self.scrape_lock:
            if service_name not in self.scrape_pool:
                return None
            
            scrape_dict = self.scrape_pool[service_name]
            data = scrape_dict.get('data')
            
            if data:
                # Mark as saved and remove
                scrape_dict['metadata']['status'] = 'saved'
                del self.scrape_pool[service_name]
                return data
            
            return None
    
    def has_scrape_data(self, service_name: str) -> bool:
        """Check if scrape pool has data for service."""
        with self.scrape_lock:
            if service_name not in self.scrape_pool:
                return False
            return self.scrape_pool[service_name].get('data') is not None
    
    # === Unprocessed Tracking ===
    
    def mark_as_unprocessed(self, service_name: str, group_name: str, 
                           url: str, error_info: Dict):
        """
        Mark an item as unprocessed due to error.
        
        Args:
            service_name: Service name
            group_name: Group/command name
            url: Full URL
            error_info: Dict with 'type', 'message', 'retry_count'
        """
        with self.unprocessed_lock:
            if service_name not in self.unprocessed:
                self.unprocessed[service_name] = self.manager.list()
            
            item = {
                'service_name': service_name,
                'group_name': group_name,
                'url': url,
                'error_type': error_info.get('type', 'Unknown'),
                'error_message': error_info.get('message', ''),
                'timestamp': datetime.now().isoformat(),
                'retry_count': error_info.get('retry_count', 0)
            }
            
            unprocessed_list = self.unprocessed[service_name]
            unprocessed_list.append(item)
            
            logger.warning(f"Marked as unprocessed: {service_name}/{group_name} - {error_info.get('type')}")
    
    def get_unprocessed(self, service_name: str) -> List[Dict]:
        """Get all unprocessed items for a service."""
        with self.unprocessed_lock:
            if service_name in self.unprocessed:
                return list(self.unprocessed[service_name])
            return []
    
    def get_all_unprocessed(self) -> Dict[str, List[Dict]]:
        """Get all unprocessed items grouped by service."""
        with self.unprocessed_lock:
            return {svc: list(items) for svc, items in self.unprocessed.items()}
    
    # === Counter Operations ===
    
    def increment_counter(self, counter_name: str, amount: int = 1):
        """
        Atomically increment a counter.
        
        Args:
            counter_name: 'fetched', 'scraped', 'saved', or 'errors'
            amount: Amount to increment
        """
        with self.counter_lock:
            self.counters[counter_name] = self.counters[counter_name] + amount
    
    def get_counter(self, counter_name: str) -> int:
        """Get current counter value."""
        with self.counter_lock:
            return self.counters.get(counter_name, 0)
    
    def get_all_counters(self) -> Dict[str, int]:
        """Get all counter values."""
        with self.counter_lock:
            return dict(self.counters)
    
    # === Shutdown Control ===
    
    def set_shutdown_flag(self):
        """Signal all workers to shutdown."""
        self.shutdown_flag.value = 1
        logger.info("Shutdown flag set")
    
    def is_shutdown_requested(self) -> bool:
        """Check if shutdown has been requested."""
        return self.shutdown_flag.value == 1
    
    # === Statistics ===
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get current statistics.
        
        Returns:
            Dict with counters, pool sizes, and status
        """
        with self.fetch_lock, self.scrape_lock, self.counter_lock:
            fetch_pool_size = sum(
                len(svc.get('GROUPS', [])) + len(svc.get('COMMANDS', []))
                for svc in self.fetch_pool.values()
            )
            
            scrape_pool_size = len(self.scrape_pool)
            unprocessed_count = sum(len(items) for items in self.unprocessed.values())
            
            return {
                'counters': dict(self.counters),
                'fetch_pool_size': fetch_pool_size,
                'scrape_pool_size': scrape_pool_size,
                'unprocessed_count': unprocessed_count,
                'services_in_fetch': len(self.fetch_pool),
                'services_in_scrape': len(self.scrape_pool),
                'shutdown_requested': self.is_shutdown_requested()
            }

"""
Fetcher worker for HTTP requests and HTML parsing.

Responsible for fetching URLs and parsing HTML content.
"""

from multiprocessing import Queue
from typing import Optional, Tuple, Dict
import requests
import time
from bs4 import BeautifulSoup
import logging

from backend.services.parallel.workers.base_worker import BaseWorker
from backend.services.parallel.shared_pools import SharedPools
from backend.services.parallel.config import ParallelConfig


logger = logging.getLogger(__name__)


class FetcherWorker(BaseWorker):
    """Worker for fetching and parsing HTML."""
    
    @property
    def WORKER_TYPE(self) -> str:
        return 'fetchers'
    
    def __init__(self, worker_id: int, fetch_queue: Queue, scrape_queue: Queue,
                 shared_pools: SharedPools, config: ParallelConfig):
        """
        Initialize fetcher worker.
        
        Args:
            worker_id: Unique worker identifier
            fetch_queue: Queue with URLs to fetch
            scrape_queue: Queue to put scraping tasks
            shared_pools: Shared data structures
            config: Configuration object
        """
        super().__init__(worker_id, shared_pools, config)
        self.fetch_queue = fetch_queue
        self.scrape_queue = scrape_queue
    
    def get_primary_queue(self) -> Queue:
        """Get primary queue (fetch_queue)."""
        return self.fetch_queue
    
    def run(self):
        """Main worker loop."""
        self.main_loop()
    
    def process_task(self, task: Dict):
        """
        Process a fetch task.
        
        Args:
            task: Dict with 'url', 'service_name', 'category', 'name'
        """
        url = task.get('url')
        service_name = task.get('service_name')
        category = task.get('category', 'COMMANDS')  # GROUPS or COMMANDS
        name = task.get('name', '')
        
        self.logger.debug(f"Fetching: {url}")
        
        # Fetch URL with retry logic
        success, html, error = self.fetch_url(url)
        
        if success:
            # Parse HTML
            parsed_data = self.parse_html(html, url, name)
            
            if parsed_data:
                # Store in fetch pool
                self.store_parsed_data(service_name, category, parsed_data)
                
                # Enqueue scraping task
                self.enqueue_scraping_task(service_name, category, name)
                
                # Increment counter
                self.shared_pools.increment_counter('fetched')
                
                # Apply rate limiting
                self.apply_rate_limit()
            else:
                self.logger.warning(f"Failed to parse HTML from {url}")
                self.handle_error(service_name, name, url, {
                    'type': 'ParseError',
                    'message': 'Failed to parse HTML',
                    'retry_count': 0
                })
        else:
            self.logger.error(f"Failed to fetch {url}: {error}")
            self.handle_error(service_name, name, url, error)
    
    def fetch_url(self, url: str) -> Tuple[bool, str, Dict]:
        """
        Fetch URL with retry logic.
        
        Args:
            url: URL to fetch
            
        Returns:
            Tuple of (success: bool, html: str, error_info: Dict)
        """
        last_error = None
        
        for attempt in range(self.config.max_retries):
            try:
                response = requests.get(
                    url,
                    timeout=self.config.request_timeout
                )
                
                # Check status code
                if response.status_code == 200:
                    return True, response.text, {}
                elif 400 <= response.status_code < 500:
                    # Client error, don't retry
                    return False, "", {
                        'type': 'HTTPError',
                        'message': f'HTTP {response.status_code}',
                        'retry_count': attempt
                    }
                else:
                    # Server error, retry with backoff
                    last_error = {
                        'type': 'HTTPError',
                        'message': f'HTTP {response.status_code}',
                        'retry_count': attempt
                    }
                    
                    if attempt < self.config.max_retries - 1:
                        backoff = self.config.retry_backoff_base * (2 ** attempt)
                        self.logger.warning(
                            f"HTTP {response.status_code} for {url}, "
                            f"retrying in {backoff}s (attempt {attempt + 1}/{self.config.max_retries})"
                        )
                        time.sleep(backoff)
            
            except requests.Timeout:
                last_error = {
                    'type': 'TimeoutError',
                    'message': f'Request timeout after {self.config.request_timeout}s',
                    'retry_count': attempt
                }
                
                if attempt < self.config.max_retries - 1:
                    backoff = self.config.retry_backoff_base * (2 ** attempt)
                    self.logger.warning(
                        f"Timeout for {url}, retrying in {backoff}s "
                        f"(attempt {attempt + 1}/{self.config.max_retries})"
                    )
                    time.sleep(backoff)
            
            except requests.RequestException as e:
                last_error = {
                    'type': 'ConnectionError',
                    'message': str(e),
                    'retry_count': attempt
                }
                
                if attempt < self.config.max_retries - 1:
                    backoff = self.config.retry_backoff_base * (2 ** attempt)
                    self.logger.warning(
                        f"Connection error for {url}, retrying in {backoff}s "
                        f"(attempt {attempt + 1}/{self.config.max_retries})"
                    )
                    time.sleep(backoff)
        
        # All retries failed
        return False, "", last_error or {
            'type': 'UnknownError',
            'message': 'All retries failed',
            'retry_count': self.config.max_retries
        }
    
    def parse_html(self, html: str, url: str, name: str) -> Optional[Dict]:
        """
        Parse HTML - just validate and return HTML string.
        
        Note: We don't create BeautifulSoup here because soup objects
        contain weakrefs that cannot be pickled on Windows.
        The ScraperWorker will re-parse from HTML string.
        
        Args:
            html: HTML content
            url: Source URL
            name: Item name
            
        Returns:
            Dict with parsed data or None on error
        """
        try:
            # Just validate that it's parseable
            soup = BeautifulSoup(html, 'html.parser')
            
            # Return only picklable data (no soup object)
            return {
                'name': name,
                'url': url,
                'html': html  # Store HTML string, not soup object
            }
        except Exception as e:
            self.logger.error(f"Error parsing HTML from {url}: {e}")
            return None
    
    def store_parsed_data(self, service_name: str, category: str, parsed_data: Dict):
        """
        Store parsed data in fetch pool.
        
        Args:
            service_name: Service name
            category: 'GROUPS' or 'COMMANDS'
            parsed_data: Parsed data dict
        """
        self.shared_pools.add_to_fetch_pool(service_name, category, parsed_data)
    
    def enqueue_scraping_task(self, service_name: str, category: str, name: str):
        """
        Add scraping task to queue.
        
        Args:
            service_name: Service name
            category: 'GROUPS' or 'COMMANDS'
            name: Item name
        """
        task = {
            'service_name': service_name,
            'category': category,
            'name': name
        }
        self.scrape_queue.put(task)
    
    def apply_rate_limit(self):
        """Sleep to respect rate limiting."""
        if self.config.rate_limit_delay > 0:
            time.sleep(self.config.rate_limit_delay)
    
    def handle_error(self, service_name: str, group_name: str, url: str, error_info: Dict):
        """
        Handle fetch error by marking as unprocessed.
        
        Args:
            service_name: Service name
            group_name: Group/command name
            url: URL that failed
            error_info: Error information dict
        """
        self.shared_pools.mark_as_unprocessed(service_name, group_name, url, error_info)
        self.shared_pools.increment_counter('errors')
    
    def try_work_stealing(self) -> Tuple[bool, Optional[Dict]]:
        """
        Try to steal work from scrape_queue.
        
        Returns:
            Tuple of (found_work: bool, task: Dict)
        """
        # Fetchers can't really help with scraping effectively
        # So we don't implement work stealing for now
        return False, None

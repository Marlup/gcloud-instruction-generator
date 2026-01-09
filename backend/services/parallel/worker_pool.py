"""
Worker pool management for coordinating parallel workers.

Manages worker lifecycle, queues, and graceful shutdown.
"""

import multiprocessing as mp
from multiprocessing import Queue, Process, Manager
from typing import List, Dict, Any
import signal
import time
import logging

from backend.services.parallel.workers import FetcherWorker, ScraperWorker, IOWorker
from backend.services.parallel.shared_pools import SharedPools
from backend.services.parallel.config import ParallelConfig


logger = logging.getLogger(__name__)


# Standalone worker runner functions (picklable on Windows)
def _run_fetcher_worker(worker_id, fetch_queue, scrape_queue, shared_pools, config):
    """Standalone function to run a fetcher worker."""
    worker = FetcherWorker(worker_id, fetch_queue, scrape_queue, shared_pools, config)
    worker.run()


def _run_scraper_worker(worker_id, scrape_queue, io_queue, shared_pools, config):
    """Standalone function to run a scraper worker."""
    worker = ScraperWorker(worker_id, scrape_queue, io_queue, shared_pools, config)
    worker.run()


def _run_io_worker(worker_id, io_queue, shared_pools, config):
    """Standalone function to run an I/O worker."""
    worker = IOWorker(worker_id, io_queue, shared_pools, config)
    worker.run()


class WorkerPool:
    """Manages worker processes and task queues."""
    
    def __init__(self, shared_pools: SharedPools, config: ParallelConfig):
        """
        Initialize worker pool.
        
        Args:
            shared_pools: Shared data structures
            config: Configuration object
        """
        self.shared_pools = shared_pools
        self.config = config
        
        # Create manager for queues
        self.manager = Manager()
        
        # Create task queues
        self.fetch_queue: Queue = self.manager.Queue()
        self.scrape_queue: Queue = self.manager.Queue()
        self.io_queue: Queue = self.manager.Queue()
        
        # Worker processes
        self.fetcher_processes: List[Process] = []
        self.scraper_processes: List[Process] = []
        self.io_processes: List[Process] = []
        
        # Statistics
        self.start_time = None
        self.end_time = None
    
    def start(self):
        """Start all worker processes."""
        self.start_time = time.time()
        
        logger.info(f"Starting {self.config.total_workers} worker processes...")
        
        # Start fetchers - use standalone function
        for i in range(self.config.n_fetchers):
            process = Process(
                target=_run_fetcher_worker,
                args=(i, self.fetch_queue, self.scrape_queue, self.shared_pools, self.config),
                name=f"Fetcher-{i}"
            )
            process.start()
            self.fetcher_processes.append(process)
            logger.info(f"Started FetcherWorker-{i} (PID: {process.pid})")
        
        # Start scrapers - use standalone function
        for i in range(self.config.n_scrapers):
            process = Process(
                target=_run_scraper_worker,
                args=(i, self.scrape_queue, self.io_queue, self.shared_pools, self.config),
                name=f"Scraper-{i}"
            )
            process.start()
            self.scraper_processes.append(process)
            logger.info(f"Started ScraperWorker-{i} (PID: {process.pid})")
        
        # Start I/O workers - use standalone function
        for i in range(self.config.n_io):
            process = Process(
                target=_run_io_worker,
                args=(i, self.io_queue, self.shared_pools, self.config),
                name=f"IOWorker-{i}"
            )
            process.start()
            self.io_processes.append(process)
            logger.info(f"Started IOWorker-{i} (PID: {process.pid})")
        
        logger.info(f"All {self.config.total_workers} workers started")
    
    def populate_fetch_queue(self, service_urls: List[Dict]):
        """
        Add initial service URLs to fetch queue.
        
        Args:
            service_urls: List of dicts with 'url', 'service_name', 'category', 'name'
        """
        for item in service_urls:
            self.fetch_queue.put(item)
        
        logger.info(f"Populated fetch queue with {len(service_urls)} tasks")
    
    def monitor_progress(self):
        """
        Monitor and log progress.
        
        Logs statistics at configured interval.
        """
        last_log_time = time.time()
        
        while not self.all_workers_done():
            current_time = time.time()
            
            if current_time - last_log_time >= self.config.progress_log_interval:
                stats = self.shared_pools.get_statistics()
                counters = stats['counters']
                
                logger.info(
                    f"Progress: "
                    f"Fetched: {counters['fetched']} | "
                    f"Scraped: {counters['scraped']} | "
                    f"Saved: {counters['saved']} | "
                    f"Errors: {counters['errors']} | "
                    f"Fetch pool: {stats['fetch_pool_size']} | "
                    f"Scrape pool: {stats['scrape_pool_size']}"
                )
                
                last_log_time = current_time
            
            time.sleep(1)
    
    def all_workers_done(self) -> bool:
        """Check if all workers have finished."""
        all_processes = (
            self.fetcher_processes + 
            self.scraper_processes + 
            self.io_processes
        )
        
        return all(not p.is_alive() for p in all_processes)
    
    def send_poison_pills(self):
        """Send poison pills (None) to all queues to signal shutdown."""
        logger.info("Sending poison pills to all workers...")
        
        # Send one poison pill per worker to each queue
        for _ in range(self.config.n_fetchers):
            self.fetch_queue.put(None)
        
        for _ in range(self.config.n_scrapers):
            self.scrape_queue.put(None)
        
        for _ in range(self.config.n_io):
            self.io_queue.put(None)
        
        logger.info("Poison pills sent")
    
    def wait_for_completion(self, timeout: int = None):
        """
        Wait for all workers to complete.
        
        Args:
            timeout: Timeout in seconds (None for config default)
        """
        if timeout is None:
            timeout = self.config.shutdown_timeout
        
        logger.info(f"Waiting for workers to complete (timeout: {timeout}s)...")
        
        all_processes = (
            self.fetcher_processes + 
            self.scraper_processes + 
            self.io_processes
        )
        
        start_time = time.time()
        
        for process in all_processes:
            remaining_time = timeout - (time.time() - start_time)
            
            if remaining_time <= 0:
                logger.warning(f"Timeout waiting for {process.name}")
                break
            
            process.join(timeout=remaining_time)
            
            if process.is_alive():
                logger.warning(f"{process.name} did not exit within timeout, terminating...")
                process.terminate()
                process.join(timeout=5)
                
                if process.is_alive():
                    logger.error(f"{process.name} did not respond to terminate, killing...")
                    process.kill()
        
        self.end_time = time.time()
        logger.info("All workers completed")
    
    def handle_signal(self, signum, frame):
        """
        Handle interrupt signals for graceful shutdown.
        
        Args:
            signum: Signal number
            frame: Stack frame
        """
        logger.warning(f"Received signal {signum}, initiating graceful shutdown...")
        
        # Set shutdown flag
        self.shared_pools.set_shutdown_flag()
        
        # Send poison pills
        self.send_poison_pills()
        
        # Wait for completion
        self.wait_for_completion(timeout=10)
    
    def setup_signal_handlers(self):
        """Set up signal handlers for graceful shutdown."""
        signal.signal(signal.SIGINT, self.handle_signal)
        signal.signal(signal.SIGTERM, self.handle_signal)
    
    def get_queue_sizes(self) -> Dict[str, int]:
        """
        Get current queue sizes.
        
        Returns:
            Dict with queue names and sizes
        """
        return {
            'fetch_queue': self.fetch_queue.qsize(),
            'scrape_queue': self.scrape_queue.qsize(),
            'io_queue': self.io_queue.qsize()
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get worker pool statistics.
        
        Returns:
            Dict with timing and worker statistics
        """
        duration = None
        if self.start_time:
            end = self.end_time or time.time()
            duration = end - self.start_time
        
        return {
            'duration_seconds': duration,
            'total_workers': self.config.total_workers,
            'n_fetchers': self.config.n_fetchers,
            'n_scrapers': self.config.n_scrapers,
            'n_io': self.config.n_io,
            'queue_sizes': self.get_queue_sizes(),
            **self.shared_pools.get_statistics()
        }
    
    def shutdown(self):
        """Graceful shutdown of worker pool."""
        logger.info("Shutting down worker pool...")
        
        # Set shutdown flag
        self.shared_pools.set_shutdown_flag()
        
        # Send poison pills
        self.send_poison_pills()
        
        # Wait for completion
        self.wait_for_completion()
        
        logger.info("Worker pool shutdown complete")

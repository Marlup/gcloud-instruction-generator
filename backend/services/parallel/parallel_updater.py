"""
Parallel GCP Knowledge Updater.

Main orchestrator for parallel web scraping of Google Cloud documentation.
"""

import os
import logging
import requests
from bs4 import BeautifulSoup
from typing import Dict, List, Union, Optional, Any
from multiprocessing import Manager
import time

from backend.services.parallel.config import ParallelConfig
from backend.services.parallel.shared_pools import SharedPools
from backend.services.parallel.worker_pool import WorkerPool
from backend.services.knowledge_updater import GCPKnowledgeUpdater
from backend.core.types.enums import UpdateMode


logger = logging.getLogger(__name__)


class ParallelGCPKnowledgeUpdater:
    """
    Parallel implementation of GCP Knowledge Updater.
    
    Uses multiprocessing to fetch, scrape, and save Google Cloud
    documentation in parallel.
    """
    
    BASE_URL = "https://cloud.google.com/sdk/gcloud/reference"
    SDK_RELATIVE_URL = "/sdk/gcloud/reference/"
    
    def __init__(self, config: Optional[ParallelConfig] = None, **kwargs):
        """
        Initialize parallel updater.
        
        Args:
            config: ParallelConfig object (or use kwargs)
            **kwargs: Config parameters to override defaults
        """
        # Create config
        if config is None:
            config = ParallelConfig(**kwargs)
        self.config = config
        
        # Create data directory
        os.makedirs(self.config.data_dir, exist_ok=True)
        
        # Initialize manager
        self.manager = Manager()
        
        # Initialize shared pools
        self.shared_pools = SharedPools(self.manager)
        
        # Initialize worker pool
        self.worker_pool = WorkerPool(self.shared_pools, self.config)
        
        # Fallback to sequential updater
        self.sequential_updater = GCPKnowledgeUpdater(
            recursion_level_limit=self.config.recursion_level_limit
        )
    
    def run_update(
        self,
        mode: UpdateMode,
        target_services: Optional[Union[str, List[str]]] = None
    ) -> Dict[str, Any]:
        """
        Public interface for running updates.
        
        Args:
            mode: Update mode (FULL, PARTIAL, SINGLE)
            target_services: Target services (required for PARTIAL/SINGLE)
            
        Returns:
            Summary dict with statistics
        """
        logger.info(f"Starting parallel update. Mode: {mode.value}, Target: {target_services}")
        
        start_time = time.time()
        
        try:
            if mode == UpdateMode.FULL:
                summary = self._update_all_services_parallel()
            elif mode == UpdateMode.PARTIAL:
                if not target_services:
                    raise ValueError("PARTIAL update requires target_services")
                summary = self._update_services_parallel(target_services)
            elif mode == UpdateMode.SINGLE:
                if not target_services:
                    raise ValueError("SINGLE update requires target_services")
                if isinstance(target_services, (list, tuple)):
                    if len(target_services) != 1:
                        raise ValueError("SINGLE update requires exactly one service")
                    target_services = target_services[0]
                summary = self._update_single_parallel(target_services)
            elif mode == UpdateMode.PATCH:
                # Use sequential for PATCH mode (operates on existing unprocessed.json files)
                logger.info("Using sequential updater for PATCH mode")
                self.sequential_updater.run_update(mode, target_services)
                summary = {'mode': 'PATCH', 'used_sequential': True}
            else:
                raise ValueError(f"Unsupported mode: {mode}")
            
            # Calculate total duration
            duration = time.time() - start_time
            summary['duration_seconds'] = duration
            
            logger.info(f"Parallel update complete. Duration: {duration:.2f}s")
            
            return summary
        
        except Exception as e:
            logger.error(f"Error in parallel update: {e}", exc_info=True)
            raise
    
    def _update_all_services_parallel(self) -> Dict[str, Any]:
        """
        Fetch and process all services in parallel.
        
        Returns:
            Summary dict
        """
        logger.info("Fetching index page to discover services...")
        
        # Fetch index page
        index_html = requests.get(self.BASE_URL).text
        soup = BeautifulSoup(index_html, "html.parser")
        
        # Extract service links
        service_urls = []
        section_tags = soup.select("ul.devsite-nav-section")
        
        for section_tag in section_tags:
            links = section_tag.select("li a[href]")
            for link in links:
                href = link.get("href", "")
                if not href.startswith("/sdk/gcloud/reference/"):
                    continue
                
                service = href.split("/")[-1]
                if not service or service == "reference":
                    continue
                
                full_url = f"{self.BASE_URL}/{service}"
                
                service_urls.append({
                    'url': full_url,
                    'service_name': service,
                    'category': 'COMMANDS',
                    'name': service
                })
        
        logger.info(f"Found {len(service_urls)} services to process")
        
        # Start workers
        self.worker_pool.start()
        
        # Populate fetch queue
        self.worker_pool.populate_fetch_queue(service_urls)
        
        # Monitor progress (in background)
        if self.config.enable_progress_logging:
            # We'll just wait for completion and log final stats
            pass
        
        # Wait for all queues to be empty and workers to finish
        self._wait_for_completion()
        
        # Send poison pills and wait
        self.worker_pool.send_poison_pills()
        self.worker_pool.wait_for_completion()
        
        # Save unprocessed items
        self._save_all_unprocessed()
        
        # Generate summary
        summary = self._generate_summary_report()
        
        return summary
    
    def _update_services_parallel(self, services: List[str]) -> Dict[str, Any]:
        """
        Fetch and process specific services in parallel.
        
        Args:
            services: List of service names
            
        Returns:
            Summary dict
        """
        logger.info(f"Processing {len(services)} services in parallel...")
        
        # Build service URLs
        service_urls = []
        for service in services:
            full_url = f"{self.BASE_URL}/{service}"
            service_urls.append({
                'url': full_url,
                'service_name': service,
                'category': 'COMMANDS',
                'name': service
            })
        
        # Start workers
        self.worker_pool.start()
        
        # Populate fetch queue
        self.worker_pool.populate_fetch_queue(service_urls)
        
        # Wait for completion
        self._wait_for_completion()
        
        # Shutdown
        self.worker_pool.send_poison_pills()
        self.worker_pool.wait_for_completion()
        
        # Save unprocessed
        self._save_all_unprocessed()
        
        # Generate summary
        summary = self._generate_summary_report()
        
        return summary
    
    def _update_single_parallel(self, service: str) -> Dict[str, Any]:
        """
        Fetch and process a single service.
        
        For single services, parallel may not provide much benefit.
        Consider using sequential for very small workloads.
        
        Args:
            service: Service name
            
        Returns:
            Summary dict
        """
        logger.info(f"Processing single service: {service}")
        
        # For single service, use simplified approach
        return self._update_services_parallel([service])
    
    def _wait_for_completion(self):
        """
        Wait for all work to be processed.
        
        Monitors queues and pools until all work is done.
        """
        logger.info("Waiting for all work to complete...")
        
        last_log_time = time.time()
        consecutive_empty_checks = 0
        
        while True:
            # Check if all queues are empty and pools are empty
            queue_sizes = self.worker_pool.get_queue_sizes()
            stats = self.shared_pools.get_statistics()
            
            all_empty = (
                queue_sizes['io_queue'] == 0 and
                stats['fetch_pool_size'] == 0 and
                stats['scrape_pool_size'] == 0 and
                all(count == 0 for count in stats['active_workers'].values())
            )
            
            if all_empty:
                consecutive_empty_checks += 1
                if consecutive_empty_checks >= 3:
                    logger.info("All queues and pools empty, work complete")
                    break
            else:
                consecutive_empty_checks = 0
            
            # Log progress
            current_time = time.time()
            if current_time - last_log_time >= self.config.progress_log_interval:
                counters = stats['counters']
                logger.info(
                    f"Progress: "
                    f"Fetched: {counters['fetched']} | "
                    f"Scraped: {counters['scraped']} | "
                    f"Saved: {counters['saved']} | "
                    f"Errors: {counters['errors']} | "
                    f"Queues: F:{queue_sizes['fetch_queue']} "
                    f"S:{queue_sizes['scrape_queue']} "
                    f"I:{queue_sizes['io_queue']} | "
                    f"Active: {stats['active_workers']}"
                )
                last_log_time = current_time
            
            time.sleep(1)
    
    def _save_all_unprocessed(self):
        """Save all unprocessed items to respective unprocessed.json files."""
        all_unprocessed = self.shared_pools.get_all_unprocessed()
        
        if not all_unprocessed:
            logger.info("No unprocessed items to save")
            return
        
        logger.info(f"Saving unprocessed items for {len(all_unprocessed)} services")
        
        for service_name, items in all_unprocessed.items():
            if not items:
                continue
            
            # Create directory
            service_dir = os.path.join(self.config.data_dir, service_name)
            os.makedirs(service_dir, exist_ok=True)
            
            # Save unprocessed.json
            filepath = os.path.join(service_dir, "unprocessed.json")
            
            # Use IOWorker logic for merging
            from .workers.io_worker import IOWorker
            dummy_worker = IOWorker(
                worker_id=999,
                io_queue=self.manager.Queue(),
                shared_pools=self.shared_pools,
                config=self.config
            )
            
            merged_items = dummy_worker.merge_unprocessed(filepath, items)
            dummy_worker.atomic_write(filepath, merged_items)
            
            logger.info(f"Saved {len(merged_items)} unprocessed items for {service_name}")
    
    def _generate_summary_report(self) -> Dict[str, Any]:
        """
        Generate summary report of the update.
        
        Returns:
            Summary dict with statistics
        """
        stats = self.worker_pool.get_statistics()
        counters = stats['counters']
        
        total_processed = counters['saved']
        total_errors = counters['errors']
        unprocessed_count = stats['unprocessed_count']
        
        success_rate = 0
        if total_processed + total_errors > 0:
            success_rate = (total_processed / (total_processed + total_errors)) * 100
        
        summary = {
            'total_services': total_processed,
            'total_fetched': counters['fetched'],
            'total_scraped': counters['scraped'],
            'total_saved': counters['saved'],
            'total_errors': total_errors,
            'total_unprocessed': unprocessed_count,
            'success_rate': success_rate,
            'duration_seconds': stats['duration_seconds'],
            'worker_config': {
                'n_fetchers': self.config.n_fetchers,
                'n_scrapers': self.config.n_scrapers,
                'n_io': self.config.n_io,
                'total_workers': self.config.total_workers
            }
        }
        
        logger.info(f"Summary: {summary}")
        
        return summary

"""
Threading-based parallel updater for Windows compatibility.

Uses threading instead of multiprocessing to avoid pickle issues.
All workers share the same memory space.
"""

import os
import logging
import requests
from bs4 import BeautifulSoup
from typing import Dict, List, Union, Optional, Any
import time
import threading
from queue import Queue, Empty
from datetime import datetime
from collections import defaultdict

from backend.services.parallel.threading_config import ThreadingConfig
from backend.services.knowledge_updater import GCPKnowledgeUpdater
from backend.core.types.enums import UpdateMode


logger = logging.getLogger(__name__)


class ThreadingGCPKnowledgeUpdater:
    """
    Threading-based parallel implementation of GCP Knowledge Updater.
    
    Uses Python threading for parallel processing (Windows-compatible).
    """
    
    BASE_URL = "https://cloud.google.com/sdk/gcloud/reference"
    SDK_RELATIVE_URL = "/sdk/gcloud.reference/"
    
    def __init__(self, config: Optional[ThreadingConfig] = None, **kwargs):
        """
        Initialize threading updater.
        
        Args:
            config: ThreadingConfig object (or use kwargs)
            **kwargs: Config parameters to override defaults
        """
        # Create config
        if config is None:
            config = ThreadingConfig(**kwargs)
        self.config = config
        
        # Create data directory
        os.makedirs(self.config.data_dir, exist_ok=True)
        
        # Task queues (thread-safe)
        self.fetch_queue: Queue = Queue(maxsize=self.config.max_queue_size)
        self.scrape_queue: Queue = Queue(maxsize=self.config.max_queue_size)
        self.io_queue: Queue = Queue(maxsize=self.config.max_queue_size)
        
        # Worker threads
        self.fetcher_threads: List[threading.Thread] = []
        self.scraper_threads: List[threading.Thread] = []
        self.io_threads: List[threading.Thread] = []
        
        # Shared state (thread-safe with locks)
        self.state_lock = threading.Lock()
        self.counters = {
            'fetched': 0,
            'scraped': 0,
            'saved': 0,
            'errors': 0
        }
        # Flat list storage: service_name -> list of command dicts
        self.service_data = defaultdict(list)
        self.unprocessed_items = defaultdict(list)
        
        # Shutdown flag
        self.shutdown_event = threading.Event()
        
        # Timing
        self.start_time = None
        self.end_time = None
    
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
        logger.info(f"Starting threading update. Mode: {mode.value}, Target: {target_services}")
        
        self.start_time = time.time()
        
        try:
            if mode == UpdateMode.FULL:
                summary = self._update_all_services_threaded()
            elif mode == UpdateMode.PARTIAL:
                if not target_services:
                    raise ValueError("PARTIAL update requires target_services")
                summary = self._update_services_threaded(target_services)
            elif mode == UpdateMode.SINGLE:
                if not target_services:
                    raise ValueError("SINGLE update requires target_services")
                if isinstance(target_services, (list, tuple)):
                    if len(target_services) != 1:
                        raise ValueError("SINGLE update requires exactly one service")
                    target_services = target_services[0]
                summary = self._update_single_threaded(target_services)
            elif mode == UpdateMode.PATCH:
                # Use sequential for PATCH mode
                logger.info("Using sequential updater for PATCH mode")
                self.sequential_updater.run_update(mode, target_services)
                summary = {'mode': 'PATCH', 'used_sequential': True}
            else:
                raise ValueError(f"Unsupported mode: {mode}")
            
            # Calculate total duration
            duration = time.time() - self.start_time
            summary['duration_seconds'] = duration
            
            logger.info(f"Threading update complete. Duration: {duration:.2f}s")
            
            return summary
        
        except Exception as e:
            logger.error(f"Error in threading update: {e}", exc_info=True)
            raise
    
    def _update_all_services_threaded(self) -> Dict[str, Any]:
        """Fetch and process all services using threading with full discovery."""
        logger.info("Fetching index page to discover ALL services and commands...")
        
        # Fetch index page
        try:
            index_html = requests.get(self.BASE_URL).text
        except Exception as e:
            logger.error(f"Failed to fetch index page: {e}")
            raise

        soup = BeautifulSoup(index_html, "html.parser")
        
        # Extract ALL links from sidebar
        # This gives us the full hierarchy upfront
        sidebar_items = []
        section_tags = soup.select("ul.devsite-nav-section li a[href]")
        
        logger.info(f"Found {len(section_tags)} links in sidebar. Analyzing hierarchy...")
        
        for link in section_tags:
            href = link.get("href", "")
            if not href.startswith("/sdk/gcloud/reference/"):
                continue
            
            # Remove prefix to get path parts
            # e.g. /sdk/gcloud/reference/storage/buckets/create -> storage/buckets/create
            rel_path = href.replace("/sdk/gcloud/reference/", "")
            if not rel_path or rel_path == "reference":
                continue
                
            parts = rel_path.split("/")
            service_name = parts[0]
            
            full_url = f"https://cloud.google.com{href}"
            
            # Determine type heuristic:
            # If it has a 'next' sibling that is a list, it's a GROUP (has children)
            # Otherwise it's likely a COMMAND (leaf)
            # NOTE: Ideally we check the HTML content, but sidebar structure is a good hint.
            # For now, we fetch EVERYTHING and let the scraper finalize the type based on content.
            
            # We'll treat everything as a potential command/group to be scraped
            # The scraper will extract the real type (Command vs Group) from the page content
            
            sidebar_items.append({
                'url': full_url,
                'service_name': service_name,
                'path_parts': parts,
                'name': parts[-1] 
            })
            
        logger.info(f"Identified {len(sidebar_items)} items to process across {len(set(i['service_name'] for i in sidebar_items))} services")
        
        # Process with threading
        return self._process_with_threads(sidebar_items)
    
    def _update_services_threaded(self, services: List[str]) -> Dict[str, Any]:
        """Fetch and process specific services using threading."""
        logger.info(f"Processing services: {services}")
        
        # We still need to discover ALL links for these services to get the full list
        # We can't just guess the URLs.
        
        index_html = requests.get(self.BASE_URL).text
        soup = BeautifulSoup(index_html, "html.parser")
        
        sidebar_items = []
        section_tags = soup.select("ul.devsite-nav-section li a[href]")
        
        target_services = set(services)
        
        for link in section_tags:
            href = link.get("href", "")
            if not href.startswith("/sdk/gcloud/reference/"):
                continue
                
            rel_path = href.replace("/sdk/gcloud/reference/", "")
            if not rel_path:
                continue
                
            parts = rel_path.split("/")
            service_name = parts[0]
            
            if service_name in target_services:
                 full_url = f"https://cloud.google.com{href}"
                 sidebar_items.append({
                    'url': full_url,
                    'service_name': service_name,
                    'path_parts': parts,
                    'name': parts[-1]
                })

        logger.info(f"Found {len(sidebar_items)} items for services {services}")
        return self._process_with_threads(sidebar_items)
    
    def _update_single_threaded(self, service: str) -> Dict[str, Any]:
        """Fetch and process a single service using threading."""
        logger.info(f"Processing single service with threading: {service}")
        return self._update_services_threaded([service])
    
    def _process_with_threads(self, service_urls: List[Dict]) -> Dict[str, Any]:
        """Main threading processing loop."""
        # Dynamic Queue Sizing
        if self.config.dynamic_queue_sizes:
            total_items = len(service_urls)
            logger.info(f"Dynamic queue sizing enabled. Total items: {total_items}")
            
            # Re-initialize queues with optimized sizes
            # Fetch Queue: Big enough to hold EVERYTHING so main thread never blocks
            self.fetch_queue = Queue(maxsize=total_items + 100)
            
            # Scrape Queue: Bounded to control memory usage (backpressure)
            # 2000 items is a good balance between throughput and memory
            self.scrape_queue = Queue(maxsize=2000)
            
            # IO Queue: Big enough to hold EVERYTHING so scrapers never block on IO
            self.io_queue = Queue(maxsize=total_items + 100)
            
            logger.info(f"Resized Queues -> Fetch: {self.fetch_queue.maxsize}, Scrape: {self.scrape_queue.maxsize}, IO: {self.io_queue.maxsize}")

        # Start worker threads FIRST to drain queue while filling
        self._start_workers()
        
        # Populate fetch queue
        for item in service_urls:
            self.fetch_queue.put(item)
        
        # Wait for work to complete
        self._wait_for_completion()
        
        # Signal shutdown
        self._signal_shutdown()
        
        # Wait for threads to exit
        self._join_all_threads()
        
        # Save all accumulated data
        self._save_all_service_data()
        
        # Save unprocessed items
        self._save_unprocessed()
        
        # Generate summary
        return self._generate_summary()
    
    def _start_workers(self):
        """Start all worker threads."""
        logger.info(f"Starting {self.config.total_workers} worker threads...")
        
        # Start fetchers
        for i in range(self.config.n_fetchers):
            thread = threading.Thread(
                target=self._fetcher_worker,
                args=(i,),
                name=f"Fetcher-{i}",
                daemon=True
            )
            thread.start()
            self.fetcher_threads.append(thread)
            logger.info(f"Started Fetcher-{i}")
        
        # Start scrapers
        for i in range(self.config.n_scrapers):
            thread = threading.Thread(
                target=self._scraper_worker,
                args=(i,),
                name=f"Scraper-{i}",
                daemon=True
            )
            thread.start()
            self.scraper_threads.append(thread)
            logger.info(f"Started Scraper-{i}")
        
        # Start I/O workers
        for i in range(self.config.n_io):
            thread = threading.Thread(
                target=self._io_worker,
                args=(i,),
                name=f"IOWorker-{i}",
                daemon=True
            )
            thread.start()
            self.io_threads.append(thread)
            logger.info(f"Started IOWorker-{i}")
        
        logger.info(f"All {self.config.total_workers} workers started")
    
    def _fetcher_worker(self, worker_id: int):
        """Fetcher worker thread function."""
        logger.info(f"Fetcher-{worker_id} starting")
        idle_count = 0
        
        while not self.shutdown_event.is_set():
            try:
                # Get task from queue
                task = self.fetch_queue.get(timeout=self.config.queue_get_timeout)
                
                if task is None:  # Poison pill
                    break
                
                idle_count = 0
                
                # Process task
                url = task['url']
                service_name = task['service_name']
                path_parts = task.get('path_parts', [])
                name = task.get('name', '')
                
                logger.debug(f"Fetcher-{worker_id} fetching: {url}")
                
                # Fetch and parse
                html = self._fetch_url(url)
                
                if html:
                    # Put to scrape queue with HTML string AND metadata
                    self.scrape_queue.put({
                        'service_name': service_name,
                        'url': url,
                        'html': html,
                        'path_parts': path_parts,
                        'name': name
                    })
                    
                    with self.state_lock:
                        self.counters['fetched'] += 1
                    
                    # Rate limit
                    time.sleep(self.config.rate_limit_delay)
                
                self.fetch_queue.task_done()
                
            except Empty:
                # Just wait... do not exit on idle
                continue
            except Exception as e:
                logger.error(f"Error in Fetcher-{worker_id}: {e}", exc_info=True)
        
        logger.info(f"Fetcher-{worker_id} exiting")
    
    def _scraper_worker(self, worker_id: int):
        """Scraper worker thread function."""
        logger.info(f"Scraper-{worker_id} starting")
        try:
            idle_count = 0
            
            while not self.shutdown_event.is_set():
                try:
                    # Get task from queue
                    task = self.scrape_queue.get(timeout=self.config.queue_get_timeout)
                    
                    if task is None:  # Poison pill
                        break
                    
                    idle_count = 0
                    
                    # Process task
                    service_name = task['service_name']
                    html = task['html']
                    url = task['url']
                    path_parts = task.get('path_parts', [])
                    
                    logger.info(f"Scraper-{worker_id} picked up task: {service_name} ({len(html)} bytes)")
                    
                    # Extract data (can use BeautifulSoup directly - no pickle!)
                    extracted_data = self._extract_data(html, service_name, url)
                    
                    if extracted_data:
                        # Enrich with flat list metadata
                        # Type heuristic: Check if extracting flags failed or succeeded?
                        # Actually, Groups usually have 'base_groups' or 'base_commands' but no 'flags'
                        # Commands have 'flags'.
                        
                        item_type = 'command'
                        if not extracted_data.get('flags') and not extracted_data.get('positional_args'):
                             # Likely a group
                             item_type = 'group'
                         
                        # Construct ID
                        # e.g. path_parts=['storage', 'buckets', 'create'] -> storage.buckets.create
                        item_id = ".".join(path_parts)
                        command_path = "gcloud " + " ".join(path_parts)
                        
                        flat_item = {
                            'id': item_id,
                            'service': service_name,
                            'type': item_type,
                            'path': path_parts,
                            'command_path': command_path,
                            **extracted_data
                        }
                        
                        # Remove legacy recursive keys if present to save space
                        flat_item.pop('base_groups', None)
                        flat_item.pop('base_commands', None)
    
                        # Log extracted data sample
                        # keys_found = list(extracted_data.keys())
                        # logger.info(f"Scraper-{worker_id} extracted data for {service_name}. Keys: {keys_found}")
                        
                        # Put to I/O queue
                        self.io_queue.put({
                            'service_name': service_name,
                            'data': flat_item
                        })
                        
                        with self.state_lock:
                            self.counters['scraped'] += 1
                    
                    self.scrape_queue.task_done()
                    
                except Empty:
                    # Just wait... do not exit on idle
                    continue
                except Exception as e:
                    with self.state_lock:
                         self.counters['errors'] += 1
                    logger.error(f"Error in Scraper-{worker_id} loop: {e}", exc_info=True)
            
            logger.info(f"Scraper-{worker_id} exiting")
            
        except Exception as e:
            with self.state_lock:
                 self.counters['errors'] += 1
            logger.critical(f"Scraper-{worker_id} CRASHED: {e}", exc_info=True)

    
    def _io_worker(self, worker_id: int):
        """I/O worker thread function."""
        logger.info(f"IOWorker-{worker_id} starting")
        idle_count = 0
        
        while not self.shutdown_event.is_set():
            try:
                # Get task from queue
                task = self.io_queue.get(timeout=self.config.queue_get_timeout)
                
                if task is None:  # Poison pill
                    break
                
                idle_count = 0
                
                # Process task
                service_name = task['service_name']
                data = task['data']
                
                # Accumulate in memory (Thread-safe dict, list append is atomic in CPython but let's be safe)
                # Actually, we process one item at a time here.
                # We need to save eventually.
                
                # Store in thread-safe container
                with self.state_lock:
                    self.service_data[service_name].append(data)
                    self.counters['saved'] += 1
                
                # We do NOT save to file on every single item anymore to avoid partial overwrites of the list
                # We will save at the end in _process_with_threads
                
                self.io_queue.task_done()
                
            except Empty:
                 # Just wait... do not exit on idle
                continue
            except Exception as e:
                logger.error(f"Error in IOWorker-{worker_id}: {e}", exc_info=True)
        
        logger.info(f"IOWorker-{worker_id} exiting")
    
    def _fetch_url(self, url: str) -> Optional[str]:
        """Fetch URL with retry logic."""
        for attempt in range(self.config.max_retries):
            try:
                response = requests.get(url, timeout=self.config.request_timeout)
                if response.status_code == 200:
                    return response.text
                elif 400 <= response.status_code < 500:
                    logger.warning(f"HTTP {response.status_code} for {url} (no retry)")
                    return None
                else:
                    if attempt < self.config.max_retries - 1:
                        backoff = self.config.retry_backoff_base * (2 ** attempt)
                        time.sleep(backoff)
            except Exception as e:
                if attempt < self.config.max_retries - 1:
                    backoff = self.config.retry_backoff_base * (2 ** attempt)
                    time.sleep(backoff)
                else:
                    logger.error(f"Failed to fetch {url}: {e}")
        
        return None
    
    def _extract_data(self, html: str, service_name: str, url: str) -> Optional[Dict]:
        """Extract data from HTML."""
        try:
            import hashlib
            soup = BeautifulSoup(html, 'html.parser')
            article = soup.find("article")
            
            if not article:
                return None
            
            # Extract synopsis
            synopsis = self._get_section_text(article, "section[id='SYNOPSIS']")
            
            # Extract description
            description = self._get_section_text(article, "section[id='DESCRIPTION']")
            
            # Extract flags
            positional_args = self._extract_flags(article, "section[id='POSITIONAL-ARGUMENTS'] dl[class]")
            required_flags = self._extract_flags(article, "section[id='REQUIRED-FLAGS'] dl[class]")
            optional_flags = self._extract_flags(article, "section[id='OPTIONAL-FLAGS'] dl[class]")
            
            flags = self._extract_flags(article, "section[id='FLAGS'] dl[class]")
            if not flags:
                flags = self._extract_flags(article, "section[id='LIST-COMMAND-FLAGS'] dl[class]")
            
            # Extract groups and commands
            base_groups = self._extract_links(article, "section[id='GROUP']")
            base_commands = self._extract_links(article, "section[id='COMMAND']")
            
            # Calculate signature
            raw_string = (
                f"{service_name}."
                f"{'.'.join(sorted(base_groups.keys()))}."
                f"{'.'.join(sorted(base_commands.keys()))}"
            )
            sha256_sign = hashlib.sha256(raw_string.encode("utf-8")).hexdigest()
            
            return {
                'service_name': service_name,
                'service_url': url,
                'description': description,
                'command_synopsis': synopsis,
                'sha256_sign': sha256_sign,
                'positional_args': positional_args,
                'required_flags': required_flags,
                'optional_flags': optional_flags,
                'flags': flags,
                'base_groups': base_groups,
                'base_commands': base_commands
            }
            
        except Exception as e:
            logger.error(f"Error extracting data for {service_name}: {e}")
            return None
    
    def _get_section_text(self, article, css_selector: str) -> str:
        """Extract text from a section."""
        if not article:
            return ""
        
        selector = article.select_one(css_selector)
        if not selector:
            return ""
        
        parts = selector.get_text().split("\n")
        parts = [part for part in parts if part]
        return "\n".join(parts[1:])  # Skip first element (heading)
    
    def _extract_flags(self, article, css_selector: str) -> Dict:
        """Extract flags from article."""
        if not article:
            return {}
        
        section_dl = article.select_one(css_selector)
        if not section_dl:
            return {}
        
        flags_dict = {}
        
        for dt in section_dl.find_all("dt", id=True):
            dd = dt.find_next_sibling('dd')
            if not dd:
                continue
            
            flag_raw_name = dt.get("id", "")
            if not flag_raw_name:
                continue
            
            flag_name = flag_raw_name.replace("--", "")
            flag_content = dt.get_text(strip=True)
            flag_desc = dd.get_text(strip=True)
            
            flags_dict[flag_name] = {
                "content": flag_content,
                "description": flag_desc
            }
        
        return flags_dict
    
    def _extract_links(self, article, css_selector: str) -> Dict:
        """Extract groups or commands."""
        if not article:
            return {}
        
        section = article.select_one(css_selector)
        if not section:
            return {}
        
        result = {}
        for tag in section.select("a[href]"):
            name = tag.get_text(strip=True)
            url = tag.get("href", "")
            result[name] = url
        
        return result
    
    def _save_all_service_data(self):
        """Save all accumulated service data to files."""
        logger.info("Saving all service data...")
        
        with self.state_lock:
            all_data = dict(self.service_data)
        
        import json
        
        for service_name, commands_list in all_data.items():
            if not commands_list:
                continue
                
            service_dir = os.path.join(self.config.data_dir, service_name)
            os.makedirs(service_dir, exist_ok=True)
            
            # Save as {service}_commands.json (plural to indicate list)
            filename = f"{service_name}_commands.json"
            filepath = os.path.join(service_dir, filename)
            
            logger.info(f"Saving {len(commands_list)} commands for {service_name} to {filepath}...")
            
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(commands_list, f, indent=2, ensure_ascii=False)
                
                file_size = os.path.getsize(filepath)
                logger.info(f"Successfully saved: {filepath} (Size: {file_size} bytes)")
            except Exception as e:
                logger.error(f"Failed to save data for {service_name}: {e}")
    
    def _wait_for_completion(self):
        """Wait for all queues to be empty."""
        logger.info("Waiting for work to complete...")
        
        last_log_time = time.time()
        
        while True:
            fetch_size = self.fetch_queue.qsize()
            scrape_size = self.scrape_queue.qsize()
            io_size = self.io_queue.qsize()
            
            all_empty = (fetch_size == 0 and scrape_size == 0 and io_size == 0)
            
            if all_empty:
                # Double-check after a brief wait
                time.sleep(2)
                if (self.fetch_queue.qsize() == 0 and 
                    self.scrape_queue.qsize() == 0 and 
                    self.io_queue.qsize() == 0):
                    logger.info("All queues empty, work complete")
                    break
            
            # Log progress
            current_time = time.time()
            if current_time - last_log_time >= self.config.progress_log_interval:
                with self.state_lock:
                    counters = dict(self.counters)
                
                logger.info(
                    f"Progress: Fetched: {counters['fetched']} | "
                    f"Scraped: {counters['scraped']} | "
                    f"Saved: {counters['saved']} | "
                    f"Errors: {counters['errors']} | "
                    f"Queues: F:{fetch_size} S:{scrape_size} I:{io_size}"
                )
                last_log_time = current_time
            
            time.sleep(1)
    
    def _signal_shutdown(self):
        """Signal all workers to shutdown."""
        logger.info("Signaling shutdown to all workers...")
        
        self.shutdown_event.set()
        
        # Send poison pills
        for _ in range(self.config.n_fetchers):
            self.fetch_queue.put(None)
        for _ in range(self.config.n_scrapers):
            self.scrape_queue.put(None)
        for _ in range(self.config.n_io):
            self.io_queue.put(None)
    
    def _join_all_threads(self):
        """Wait for all threads to complete."""
        logger.info("Waiting for all threads to exit...")
        
        all_threads = self.fetcher_threads + self.scraper_threads + self.io_threads
        
        for thread in all_threads:
            thread.join(timeout=5)
            if thread.is_alive():
                logger.warning(f"{thread.name} did not exit cleanly")
        
        self.end_time = time.time()
        logger.info("All threads exited")
    
    def _save_unprocessed(self):
        """Save unprocessed items to files."""
        with self.state_lock:
            unprocessed = dict(self.unprocessed_items)
        
        if not unprocessed:
            return
        
        import json
        for service_name, items in unprocessed.items():
            if not items:
                continue
            
            service_dir = os.path.join(self.config.data_dir, service_name)
            os.makedirs(service_dir, exist_ok=True)
            
            filepath = os.path.join(service_dir, "unprocessed.json")
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(items, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved {len(items)} unprocessed items for {service_name}")
    
    def _generate_summary(self) -> Dict[str, Any]:
        """Generate summary report."""
        with self.state_lock:
            counters = dict(self.counters)
            unprocessed_count = sum(len(items) for items in self.unprocessed_items.values())
        
        total_processed = counters['saved']
        total_errors = counters['errors']
        
        success_rate = 0
        if total_processed + total_errors > 0:
            success_rate = (total_processed / (total_processed + total_errors)) * 100
        
        duration = (self.end_time or time.time()) - self.start_time
        
        summary = {
            'total_services': total_processed,
            'total_fetched': counters['fetched'],
            'total_scraped': counters['scraped'],
            'total_saved': counters['saved'],
            'total_errors': total_errors,
            'total_unprocessed': unprocessed_count,
            'success_rate': success_rate,
            'duration_seconds': duration,
            'worker_config': {
                'n_fetchers': self.config.n_fetchers,
                'n_scrapers': self.config.n_scrapers,
                'n_io': self.config.n_io,
                'total_workers': self.config.total_workers
            }
        }
        
        logger.info(f"Summary: {summary}")
        
        return summary

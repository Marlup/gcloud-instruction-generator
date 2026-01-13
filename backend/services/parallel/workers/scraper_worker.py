"""
Scraper worker for data extraction from parsed HTML.

Responsible for extracting structured data from BeautifulSoup objects.
"""

from multiprocessing import Queue
from typing import Optional, Tuple, Dict, Any
import hashlib
import logging
from bs4 import BeautifulSoup, Tag

from backend.services.parallel.workers.base_worker import BaseWorker
from backend.services.parallel.shared_pools import SharedPools
from backend.services.parallel.config import ParallelConfig


logger = logging.getLogger(__name__)


class ScraperWorker(BaseWorker):
    """Worker for digging data from parsed HTML."""
    
    @property
    def WORKER_TYPE(self) -> str:
        return 'scrapers'
    
    def __init__(self, worker_id: int, scrape_queue: Queue, io_queue: Queue,
                 shared_pools: SharedPools, config: ParallelConfig):
        """
        Initialize scraper worker.
        
        Args:
            worker_id: Unique worker identifier
            scrape_queue: Queue with scraping tasks
            io_queue: Queue to put I/O tasks
            shared_pools: Shared data structures
            config: Configuration object
        """
        super().__init__(worker_id, shared_pools, config)
        self.scrape_queue = scrape_queue
        self.io_queue = io_queue
    
    def get_primary_queue(self) -> Queue:
        """Get primary queue (scrape_queue)."""
        return self.scrape_queue
    
    def run(self):
        """Main worker loop."""
        self.main_loop()
    
    def process_task(self, task: Dict):
        """
        Process a scraping task.
        
        Args:
            task: Dict with 'service_name', 'category', 'name'
        """
        service_name = task.get('service_name')
        category = task.get('category')
        name = task.get('name', '')
        
        self.logger.debug(f"Scraping: {service_name}/{category}/{name}")
        
        # Get parsed HTML from fetch pool
        parsed_data = self.shared_pools.get_from_fetch_pool(service_name, category, 0)
        
        if not parsed_data:
            self.logger.warning(f"No parsed data found for {service_name}/{category}/{name}")
            return
        
        try:
            # Get HTML string and re-parse it
            # (We can't pass soup objects on Windows due to pickle issues)
            html = parsed_data.get('html')
            url = parsed_data.get('url')
            
            if not html:
                raise ValueError("No HTML content in parsed data")
            
            # Re-parse HTML to create soup object
            soup = BeautifulSoup(html, 'html.parser')
            
            extracted_data = self.extract_data(soup, service_name, url)
            
            if extracted_data:
                # Store in scrape pool
                self.store_extracted_data(service_name, extracted_data)
                
                # Enqueue I/O task
                self.enqueue_io_task(service_name)
                
                # Increment counter
                self.shared_pools.increment_counter('scraped')
            else:
                self.logger.warning(f"Failed to extract data from {service_name}")
                self.handle_error(service_name, name, url, {
                    'type': 'ExtractionError',
                    'message': 'Failed to extract data',
                    'retry_count': 0
                })
        
        except Exception as e:
            self.logger.error(f"Error scraping {service_name}/{category}/{name}: {e}", exc_info=True)
            self.handle_error(service_name, name, parsed_data.get('url', ''), {
                'type': 'ExtractionError',
                'message': str(e),
                'retry_count': 0
            })
    
    def extract_data(self, soup: BeautifulSoup, service_name: str, url: str) -> Optional[Dict]:
        """
        Extract all data from soup.
        
        Args:
            soup: BeautifulSoup object
            service_name: Service name
            url: Source URL
            
        Returns:
            ServiceCommand dict or None
        """
        try:
            article = soup.find("article")
            
            if not article:
                self.logger.warning(f"No article tag found for {service_name}")
                return None
            
            # Extract synopsis
            synopsis = self.extract_synopsis(article)
            
            # Extract description
            description = self.extract_description(article)
            
            # Extract positional arguments
            positional_args = self.extract_flags(
                article, "section[id='POSITIONAL-ARGUMENTS'] dl[class]"
            )
            
            # Extract required flags
            required_flags = self.extract_flags(
                article, "section[id='REQUIRED-FLAGS'] dl[class]"
            )
            
            # Extract optional flags
            optional_flags = self.extract_flags(
                article, "section[id='OPTIONAL-FLAGS'] dl[class]"
            )
            
            # Extract general flags
            flags = self.extract_flags(article, "section[id='FLAGS'] dl[class]")
            if not flags:
                flags = self.extract_flags(
                    article, "section[id='LIST-COMMAND-FLAGS'] dl[class]"
                )
            
            # Extract groups and commands (simplified - no recursion in parallel version yet)
            base_groups = self.extract_groups_and_commands(
                article, "section[id='GROUP']", service_name
            )
            base_commands = self.extract_groups_and_commands(
                article, "section[id='COMMAND']", service_name
            )
            
            # Build ServiceCommand
            service_command = self.build_service_command(
                service_name=service_name,
                service_url=url,
                description=description,
                synopsis=synopsis,
                positional_args=positional_args,
                required_flags=required_flags,
                optional_flags=optional_flags,
                flags=flags,
                base_groups=base_groups,
                base_commands=base_commands
            )
            
            return service_command
        
        except Exception as e:
            self.logger.error(f"Error extracting data for {service_name}: {e}", exc_info=True)
            return None
    
    def extract_synopsis(self, article: Tag) -> str:
        """Extract synopsis section."""
        return self._get_key_text(article, "section[id='SYNOPSIS']")
    
    def extract_description(self, article: Tag) -> str:
        """Extract description section."""
        return self._get_key_text(article, "section[id='DESCRIPTION']")
    
    def _get_key_text(self, tag: Tag, css_selector: str) -> str:
        """
        Extract text from a section.
        
        Args:
            tag: Parent tag
            css_selector: CSS selector
            
        Returns:
            Extracted text
        """
        if not tag:
            return ""
        
        selector = tag.select_one(css_selector)
        if not selector:
            return ""
        
        parts = selector.get_text().split("\n")
        parts = [part for part in parts if part]
        return "\n".join(parts[1:])  # Skip first element (usually the heading)
    
    def extract_flags(self, article: Tag, css_selector: str) -> Dict:
        """
        Extract flags section.
        
        Args:
            article: Article tag
            css_selector: CSS selector for flags section
            
        Returns:
            Dict of flags
        """
        if not article:
            return {}
        
        section_dl = article.select_one(css_selector)
        if not section_dl:
            return {}
        
        flags_dict = {}
        
        # Find all dt tags with ids
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
    
    def extract_groups_and_commands(self, article: Tag, css_selector: str, 
                                   service_name: str) -> Dict:
        """
        Extract groups or commands (non-recursive version).
        
        Args:
            article: Article tag
            css_selector: CSS selector
            service_name: Service name
            
        Returns:
            Dict of group/command names to URLs
        """
        if not article:
            return {}
        
        section = article.select_one(css_selector)
        if not section:
            return {}
        
        result = {}
        
        for tag in section.select("a[href]"):
            name = tag.get_text(strip=True)
            url = tag.get("href", "")
            
            # Store just the URL for now (no recursive fetching in parallel version)
            result[name] = url
        
        return result
    
    def build_service_command(self, **kwargs) -> Dict:
        """
        Build ServiceCommand dict.
        
        Args:
            **kwargs: ServiceCommand fields
            
        Returns:
            ServiceCommand as dict
        """
        service_name = kwargs.get('service_name', '')
        base_groups = kwargs.get('base_groups', {})
        base_commands = kwargs.get('base_commands', {})
        
        # Calculate signature
        raw_string = (
            f"{service_name}."
            f"{'.'.join(sorted(base_groups.keys()))}."
            f"{'.'.join(sorted(base_commands.keys()))}"
        )
        sha256_sign = hashlib.sha256(raw_string.encode("utf-8")).hexdigest()
        
        return {
            'service_name': service_name,
            'service_url': kwargs.get('service_url', ''),
            'description': kwargs.get('description', ''),
            'command_synopsis': kwargs.get('synopsis', ''),
            'sha256_sign': sha256_sign,
            'positional_args': kwargs.get('positional_args', {}),
            'required_flags': kwargs.get('required_flags', {}),
            'optional_flags': kwargs.get('optional_flags', {}),
            'flags': kwargs.get('flags', {}),
            'base_groups': base_groups,
            'base_commands': base_commands
        }
    
    def store_extracted_data(self, service_name: str, service_command: Dict):
        """
        Store extracted data in scrape pool.
        
        Args:
            service_name: Service name
            service_command: ServiceCommand dict
        """
        self.shared_pools.add_to_scrape_pool(service_name, service_command)
    
    def enqueue_io_task(self, service_name: str):
        """
        Add I/O task to queue.
        
        Args:
            service_name: Service name
        """
        task = {'service_name': service_name}
        self.io_queue.put(task)
    
    def handle_error(self, service_name: str, group_name: str, url: str, error_info: Dict):
        """
        Handle extraction error.
        
        Args:
            service_name: Service name
            group_name: Group/command name
            url: URL that failed
            error_info: Error information
        """
        self.shared_pools.mark_as_unprocessed(service_name, group_name, url, error_info)
        self.shared_pools.increment_counter('errors')
    
    def try_work_stealing(self) -> Tuple[bool, Optional[Dict]]:
        """
        Try to steal work from fetch_queue.
        
        Returns:
            Tuple of (found_work: bool, task: Dict)
        """
        # Scrapers can't help with fetching
        return False, None

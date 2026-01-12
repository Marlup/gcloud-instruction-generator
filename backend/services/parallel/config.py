"""
Configuration module for parallel knowledge updater.

Provides centralized configuration management using dataclasses.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ParallelConfig:
    """Configuration for parallel GCP knowledge updater."""
    
    # Worker counts
    n_fetchers: int = 1
    n_scrapers: int = 2
    n_io: int = 1
    
    # Recursion settings
    recursion_level_limit: int = 1
    
    # Network settings
    rate_limit_delay: float = 0.1  # seconds between requests
    request_timeout: int = 30  # seconds
    max_retries: int = 3
    retry_backoff_base: float = 1.0  # seconds
    
    # Pool size limits
    max_fetch_pool_size: int = 1000
    max_scrape_pool_size: int = 500
    
    # Shutdown settings
    shutdown_timeout: int = 30  # seconds
    queue_get_timeout: int = 2  # seconds for primary queue
    work_steal_timeout: float = 0.5  # seconds for secondary queue
    max_idle_checks: int = 3  # consecutive empty checks before exit
    
    # Progress monitoring
    progress_log_interval: int = 10  # seconds
    
    # Paths
    data_dir: str = "data/webscrap/landing"
    
    # Feature flags
    enable_work_stealing: bool = True
    enable_progress_logging: bool = True
    
    def __post_init__(self):
        """Validate configuration."""
        if self.n_fetchers < 1:
            raise ValueError("n_fetchers must be at least 1")
        if self.n_scrapers < 1:
            raise ValueError("n_scrapers must be at least 1")
        if self.n_io < 1:
            raise ValueError("n_io must be at least 1")
        if self.rate_limit_delay < 0:
            raise ValueError("rate_limit_delay must be non-negative")
        if self.request_timeout < 1:
            raise ValueError("request_timeout must be at least 1")
        if self.max_retries < 0:
            raise ValueError("max_retries must be non-negative")
    
    @property
    def total_workers(self) -> int:
        """Total number of worker processes."""
        return self.n_fetchers + self.n_scrapers + self.n_io

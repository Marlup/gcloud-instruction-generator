"""
Threading-based configuration for Windows compatibility.

Uses threading instead of multiprocessing to avoid pickle issues.
"""

from dataclasses import dataclass


@dataclass
class ThreadingConfig:
    """Configuration for threading-based GCP knowledge updater."""
    
    # Worker counts (threads instead of processes)
    n_fetchers: int = 3
    n_scrapers: int = 4
    n_io: int = 1
    
    # Recursion settings
    recursion_level_limit: int = 1
    
    # Network settings
    rate_limit_delay: float = 0.1  # seconds between requests
    request_timeout: int = 30  # seconds
    max_retries: int = 3
    retry_backoff_base: float = 1.0  # seconds
    
    # Queue settings
    max_queue_size: int = 1000
    queue_get_timeout: int = 2  # seconds for primary queue
    max_idle_checks: int = 3  # consecutive empty checks before exit
    
    # Progress monitoring
    progress_log_interval: int = 10  # seconds
    
    # Paths
    data_dir: str = "data/webscrap/landing"
    
    # Feature flags
    enable_progress_logging: bool = True
    dynamic_queue_sizes: bool = True
    
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
        """Total number of worker threads."""
        return self.n_fetchers + self.n_scrapers + self.n_io

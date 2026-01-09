"""
Base worker class for all worker types.

Provides common functionality for worker processes.
"""

from abc import ABC, abstractmethod
from multiprocessing import Queue
from typing import Optional, Tuple
import logging
import queue

from backend.services.parallel.shared_pools import SharedPools
from backend.services.parallel.config import ParallelConfig


class BaseWorker(ABC):
    """Abstract base class for all worker types."""
    
    def __init__(self, worker_id: int, shared_pools: SharedPools, 
                 config: ParallelConfig):
        """
        Initialize base worker.
        
        Args:
            worker_id: Unique worker identifier
            shared_pools: Shared data structures
            config: Configuration object
        """
        self.worker_id = worker_id
        self.shared_pools = shared_pools
        self.config = config
        self.logger = self._setup_logger()
        self.idle_check_count = 0
    
    def _setup_logger(self) -> logging.Logger:
        """Set up worker-specific logger."""
        logger = logging.getLogger(f"{self.__class__.__name__}-{self.worker_id}")
        return logger
    
    @abstractmethod
    def run(self):
        """
        Main worker loop.
        
        Must be implemented by subclasses.
        """
        pass
    
    @abstractmethod
    def process_task(self, task: any):
        """
        Process a single task.
        
        Args:
            task: Task data from queue
            
        Must be implemented by subclasses.
        """
        pass
    
    @abstractmethod
    def get_primary_queue(self) -> Queue:
        """
        Get the primary queue for this worker type.
        
        Returns:
            Primary task queue
            
        Must be implemented by subclasses.
        """
        pass
    
    def get_from_queue(self, q: Queue, timeout: float) -> Optional[any]:
        """
        Get item from queue with timeout.
        
        Args:
            q: Queue to get from
            timeout: Timeout in seconds
            
        Returns:
            Task data or None if timeout/empty
        """
        try:
            task = q.get(timeout=timeout)
            return task
        except queue.Empty:
            return None
    
    def is_poison_pill(self, task: any) -> bool:
        """
        Check if task is a poison pill (shutdown signal).
        
        Args:
            task: Task to check
            
        Returns:
            True if poison pill (None), False otherwise
        """
        return task is None
    
    def should_shutdown(self) -> bool:
        """
        Check if worker should shutdown.
        
        Returns:
            True if shutdown requested or max idle checks reached
        """
        if self.shared_pools.is_shutdown_requested():
            return True
        
        if self.idle_check_count >= self.config.max_idle_checks:
            self.logger.info(f"Worker {self.worker_id} idle for {self.idle_check_count} checks, exiting")
            return True
        
        return False
    
    def reset_idle_count(self):
        """Reset idle check counter when work is found."""
        self.idle_check_count = 0
    
    def increment_idle_count(self):
        """Increment idle check counter when no work is found."""
        self.idle_check_count += 1
    
    def try_work_stealing(self) -> Tuple[bool, Optional[any]]:
        """
        Try to steal work from other queues.
        
        Returns:
            Tuple of (found_work: bool, task: any)
            
        Default implementation returns (False, None).
        Subclasses can override to implement work stealing.
        """
        return False, None
    
    def main_loop(self):
        """
        Main worker loop implementation.
        
        This is a template method that can be used by subclasses.
        """
        self.logger.info(f"Worker {self.worker_id} started")
        
        while not self.should_shutdown():
            # Try to get task from primary queue
            primary_queue = self.get_primary_queue()
            task = self.get_from_queue(primary_queue, self.config.queue_get_timeout)
            
            if task is not None:
                # Check for poison pill
                if self.is_poison_pill(task):
                    self.logger.info(f"Worker {self.worker_id} received poison pill, exiting")
                    break
                
                # Process task
                self.reset_idle_count()
                try:
                    self.process_task(task)
                except Exception as e:
                    self.logger.error(f"Error processing task: {e}", exc_info=True)
                    self.shared_pools.increment_counter('errors')
            else:
                # No task in primary queue, try work stealing
                if self.config.enable_work_stealing:
                    found_work, stolen_task = self.try_work_stealing()
                    
                    if found_work and stolen_task is not None:
                        self.reset_idle_count()
                        try:
                            self.process_task(stolen_task)
                        except Exception as e:
                            self.logger.error(f"Error processing stolen task: {e}", exc_info=True)
                            self.shared_pools.increment_counter('errors')
                    else:
                        self.increment_idle_count()
                else:
                    self.increment_idle_count()
        
        self.logger.info(f"Worker {self.worker_id} exiting")

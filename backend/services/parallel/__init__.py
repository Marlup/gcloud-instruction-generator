"""
Parallel processing module for GCP Knowledge Updater.

This module provides a multiprocessing implementation for efficient
web scraping of Google Cloud documentation.
"""

from .config import ParallelConfig
from .parallel_updater import ParallelGCPKnowledgeUpdater

__version__ = "1.0.0"
__all__ = ["ParallelConfig", "ParallelGCPKnowledgeUpdater"]

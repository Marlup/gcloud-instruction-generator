# Parallel Processing Module

A multiprocessing implementation for efficient web scraping of Google Cloud documentation.

## Features

- **3-5x faster** than sequential processing
- **Thread-safe** shared data structures
- **Robust error handling** with retry logic
- **Graceful shutdown** with signal handling
- **Comprehensive logging** and progress monitoring
- **Atomic file operations** to prevent corruption
- **Unprocessed tracking** for failed items

## Quick Start

```python
from backend.services.parallel import ParallelGCPKnowledgeUpdater, ParallelConfig
from backend.core.types.enums import UpdateMode

# Configure
config = ParallelConfig(
    n_fetchers=4,
    n_scrapers=4,
    n_io=2,
    rate_limit_delay=0.1
)

# Create updater
updater = ParallelGCPKnowledgeUpdater(config=config)

# Update single service
summary = updater.run_update(UpdateMode.SINGLE, target_services="storage")

# View results
print(f"Saved: {summary['total_saved']}")
print(f"Errors: {summary['total_errors']}")
print(f"Duration: {summary['duration_seconds']:.2f}s")
```

## Architecture

### Components

1. **config.py** - Configuration management with validation
2. **shared_pools.py** - Thread-safe shared data structures
3. **workers/** - Worker implementations
   - `base_worker.py` - Abstract base class
   - `fetcher_worker.py` - HTTP fetching & HTML parsing
   - `scraper_worker.py` - Data extraction
   - `io_worker.py` - File I/O operations
4. **worker_pool.py** - Process lifecycle management
5. **parallel_updater.py** - Main orchestrator

### Data Flow

```
Index Page → Fetch Queue → Fetcher Workers → Fetch Pool
                                                ↓
                                           Scrape Queue → Scraper Workers → Scrape Pool
                                                                                  ↓
                                                                              I/O Queue → I/O Workers → JSON Files
```

## Configuration

### ParallelConfig Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `n_fetchers` | 4 | Number of fetcher workers |
| `n_scrapers` | 4 | Number of scraper workers |
| `n_io` | 2 | Number of I/O workers |
| `rate_limit_delay` | 0.1 | Delay between requests (seconds) |
| `max_retries` | 3 | Maximum retry attempts |
| `request_timeout` | 30 | HTTP request timeout (seconds) |
| `max_fetch_pool_size` | 1000 | Maximum fetch pool size |
| `max_scrape_pool_size` | 500 | Maximum scrape pool size |
| `shutdown_timeout` | 30 | Graceful shutdown timeout (seconds) |

See [config.py](./config.py) for full parameter list.

## Update Modes

### FULL Mode
Updates all services from the index page.

```python
updater.run_update(UpdateMode.FULL)
```

### PARTIAL Mode
Updates specific services.

```python
updater.run_update(
    UpdateMode.PARTIAL, 
    target_services=["compute", "storage", "ai"]
)
```

### SINGLE Mode
Updates a single service.

```python
updater.run_update(
    UpdateMode.SINGLE, 
    target_services="storage"
)
```

### PATCH Mode
Processes unprocessed items (uses sequential updater).

```python
updater.run_update(UpdateMode.PATCH)
```

## Error Handling

### Unprocessed Items

Failed items are saved to `unprocessed.json` with this structure:

```json
[
  {
    "service_name": "storage",
    "group_name": "buckets/update",
    "url": "https://...",
    "error_type": "HTTPError",
    "error_message": "Connection timeout",
    "timestamp": "2026-01-08T16:00:00",
    "retry_count": 3
  }
]
```

### Retry Logic

- **HTTPError 4xx**: No retry (client error)
- **HTTPError 5xx**: Retry with exponential backoff
- **Timeout**: Retry with increased timeout
- **Connection Error**: Retry up to 3 times

Backoff schedule: 1s → 2s → 4s

## Examples

See [examples/test_parallel_updater.py](../../examples/test_parallel_updater.py) for complete examples.

### Basic Usage

```python
config = ParallelConfig(n_fetchers=2, n_scrapers=2, n_io=1)
updater = ParallelGCPKnowledgeUpdater(config=config)
summary = updater.run_update(UpdateMode.SINGLE, "storage")
```

### High Performance

```python
config = ParallelConfig(
    n_fetchers=8,
    n_scrapers=8,
    n_io=4,
    rate_limit_delay=0.05
)
updater = ParallelGCPKnowledgeUpdater(config=config)
summary = updater.run_update(UpdateMode.FULL)
```

### Conservative (Server-Friendly)

```python
config = ParallelConfig(
    n_fetchers=2,
    n_scrapers=2,
    n_io=1,
    rate_limit_delay=0.5,
    max_retries=5
)
updater = ParallelGCPKnowledgeUpdater(config=config)
summary = updater.run_update(UpdateMode.PARTIAL, ["compute", "storage"])
```

## Monitoring

### Progress Logging

Enabled by default every 10 seconds:

```
[2026-01-08 16:15:30] Progress: Fetched: 45/100 | Scraped: 38/45 | Saved: 35/38 | Errors: 3
```

### Summary Report

Returned after completion:

```python
{
  "total_services": 150,
  "total_fetched": 450,
  "total_scraped": 450,
  "total_saved": 148,
  "total_errors": 2,
  "total_unprocessed": 2,
  "success_rate": 98.67,
  "duration_seconds": 180.5,
  "worker_config": {
    "n_fetchers": 4,
    "n_scrapers": 4,
    "n_io": 2,
    "total_workers": 10
  }
}
```

## Testing

Run test examples:

```bash
cd "c:\MyWork\main-demos\Google cloud\gcloud-instruction-generator"

# Test single service
python examples/test_parallel_updater.py single

# Test multiple services
python examples/test_parallel_updater.py partial

# Test full update (WARNING: Long running!)
python examples/test_parallel_updater.py full
```

## Troubleshooting

### Workers Not Starting

Check if port/permissions are blocking multiprocessing:
```python
import multiprocessing
print(multiprocessing.cpu_count())  # Should show CPU count
```

### High Memory Usage

Reduce pool sizes:
```python
config = ParallelConfig(
    max_fetch_pool_size=100,
    max_scrape_pool_size=50
)
```

### Rate Limiting Errors

Increase delay:
```python
config = ParallelConfig(rate_limit_delay=0.5)
```

### Graceful Shutdown Not Working

Increase timeout:
```python
config = ParallelConfig(shutdown_timeout=60)
```

## Performance Tips

1. **Adjust workers** based on CPU cores: `n_fetchers = n_scrapers = cpu_count()`
2. **Reduce rate limit** if server allows: `rate_limit_delay=0.05`
3. **Increase I/O workers** for slow disks: `n_io=4`
4. **Monitor queue sizes** to identify bottlenecks

## License

Same as parent project.

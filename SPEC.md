# Technical Requirements

## Overview
This tool bulk deletes customers from a BigCommerce store while respecting API rate limits and handling large datasets efficiently.

## API Constraints
- Maximum 5 concurrent connections to BigCommerce API
- Rate limit: 20,000 requests per hour (~150 requests/30sec)
- Delete endpoint accepts maximum 10 customer IDs per request
- Pagination supported with 250 items per page maximum

## Implementation Details

### Core Components

#### State Manager
Manages persistent state using a single JSON file:
- Tracks all processed customer IDs
- Handles state file I/O operations
- Provides simple interface for checking and updating progress

State File:
- `processed_customers.json`: Set of all processed customer IDs

#### CustomerDeleter
Handles the main deletion logic:
- Processes customers page by page (250 per request)
- Groups deletions into configurable batch sizes (default 10)
- Manages concurrent operations (default 5)
- Implements rate limiting (default 150 requests/30sec)
- Provides dry-run capability for testing

### Configuration Parameters
- `store_hash`: BigCommerce store identifier
- `access_token`: API authentication token
- `rate_limit`: Requests per 30 seconds (default: 150)
- `batch_size`: Customers per deletion request (default: 10)
- `max_concurrent`: Maximum parallel operations (default: 5)
- `dry_run`: Test mode without actual deletions
- `state_dir`: Location for state files (default: "./state")

### Error Handling
- Failed operations are logged with API response details
- Exceptions during deletion are caught and logged
- Script can be safely interrupted and resumed
- Clear error messages for troubleshooting

### Recovery Capabilities
The script is designed to be interrupt-safe:
1. State is saved after each successful batch
2. Already processed customers are automatically skipped
3. Can resume from any point
4. Maintains accurate progress counting

### Memory Management
- Processes customers in pages of 250
- Only keeps processed IDs in memory
- Writes progress to disk after each batch
- Maintains constant memory usage regardless of total customer count

### Progress Reporting
- Shows total customer count at start
- Displays already processed count on resume
- Reports progress percentage after each batch
- Indicates dry-run operations clearly
- Provides final summary statistics

### Rate Limiting Strategy
- Uses asyncio.sleep() between API calls
- Sleep duration calculated as: 30 seconds / rate_limit
- Concurrent operations managed via asyncio.Semaphore
- Default rate of 150 requests per 30-second period
- Configurable via command-line parameter
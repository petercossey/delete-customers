# Technical Requirements

## Overview
This tool bulk deletes customers from a BigCommerce store while respecting API rate limits and handling large datasets efficiently using a two-phase approach.

## API Constraints
- Maximum 5 concurrent connections to BigCommerce API
- Rate limit: 20,000 requests per hour (~150 requests/30sec)
- Delete endpoint accepts maximum 10 customer IDs per request
- Pagination supported with 250 items per page maximum

## Implementation Details

### Core Components

#### CustomerDeleter
Main class that handles:
- Fetching all customer IDs (phase 1)
- Processing deletions in batches (phase 2)
- Rate limit management
- Concurrent operations
- Error handling and retries

### Configuration Parameters
- `store_hash`: BigCommerce store identifier
- `access_token`: API authentication token
- `rate_limit`: Requests per 30 seconds (default: 150)
- `batch_size`: Customers per deletion request (default: 10)
- `max_concurrent`: Maximum parallel operations (default: 5)
- `dry_run`: Test mode without actual deletions

### Error Handling
- Failed operations are logged with API response details
- Automatic retry on server errors (5xx)
- Rate limit handling with backoff based on Retry-After header
- Clear error messages for troubleshooting
- Graceful handling of network timeouts

### Two-Phase Operation
1. Customer ID Collection Phase:
   - Fetches all customer IDs using pagination
   - 250 customers per page (API maximum)
   - Maintains list of all customer IDs in memory

2. Deletion Phase:
   - Processes customers in configurable batch sizes
   - Default batch size of 10 customers
   - Tracks progress with percentage complete
   - Provides detailed logging of operations

### Rate Limiting Strategy
- Uses asyncio.sleep() between API calls
- Sleep duration calculated as: 30 seconds / rate_limit
- Concurrent operations managed via asyncio.Semaphore
- Default rate of 150 requests per 30-second period
- Respects API's 429 responses and Retry-After headers
- Adds small delays between requests to prevent rate limit hits

### Progress Reporting
- Shows total customer count at start
- Reports each page of customers fetched
- Displays progress percentage during deletion
- Indicates dry-run operations clearly
- Provides final summary statistics
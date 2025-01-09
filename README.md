# BigCommerce Customer Cleanup

A script to bulk delete customers from a BigCommerce store. Handles large customer sets efficiently with rate limiting and concurrent operations.

⚠️ **WARNING: This script deletes customer data. Use with extreme caution.**

## Disclaimer

This script is provided as-is, without any warranties or guarantees of any kind, express or implied. It is intended as a proof of concept only. The authors accept no liability for any data loss or other damages resulting from its use. Always test thoroughly in a non-production environment first and ensure you have proper backups before running any data deletion scripts.

## AI Attribution

Significant portions of this codebase were generated with the assistance of AI coding tools including GitHub Copilot and Claude. While efforts have been made to verify the code's functionality, users should review and test thoroughly before use in any critical environments.

## Quick Start

1. Clone this repository:
```bash
git clone https://github.com/yourusername/bigcommerce-customer-cleanup.git
cd bigcommerce-customer-cleanup
```

2. Create and activate a virtual environment:
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Unix/MacOS
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run the script:
```bash
python delete_customers.py \
    --store-hash="your_store_hash" \
    --access-token="your_api_token" \
    --dry-run  # Remove this flag to actually delete customers
```

## How It Works

The script operates in two phases:
1. Fetches all customer IDs from the BigCommerce API using pagination
2. Processes deletions in batches with automatic rate limiting and retries

Features:
- Automatic rate limit handling with backoff
- Concurrent operations for improved performance
- Clear progress reporting
- Dry-run mode for testing
- Automatic retry on server errors

## Options

- `--store-hash`: Your BigCommerce store hash (required)
- `--access-token`: Your BigCommerce API token (required)
- `--rate-limit`: Number of requests per 30 seconds (default: 150)
- `--batch-size`: Number of customers to delete in each batch (default: 10)
- `--max-concurrent`: Maximum number of concurrent connections (default: 5)
- `--dry-run`: Run in test mode without actually deleting customers (default: False)

## Progress Reporting

The script provides detailed progress information:
```
2024-01-09 17:30:00,000 - INFO - Fetching all customer IDs...
2024-01-09 17:30:00,100 - INFO - Fetched page 1 - Found 250 customers
2024-01-09 17:30:00,200 - INFO - Fetched page 2 - Found 250 customers
2024-01-09 17:30:00,300 - INFO - Found 500 customers to process
2024-01-09 17:30:00,400 - INFO - Progress: 10/500 customers (2.0%)
2024-01-09 17:30:00,500 - INFO - Progress: 20/500 customers (4.0%)
...
2024-01-09 17:30:10,000 - INFO - Operation complete. Processed 500/500 customers (100.0%)
```

## Rate Limiting

The script automatically handles BigCommerce API rate limits:
- Respects the 429 status code and Retry-After header
- Implements automatic backoff when rate limited
- Adds small delays between requests to prevent rate limit hits

## Error Handling

- Automatically retries on server errors (5xx)
- Handles rate limits with proper backoff
- Clear error messages for troubleshooting
- Graceful handling of network issues
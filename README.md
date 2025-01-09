# BigCommerce Customer Cleanup

A script to bulk delete customers from a BigCommerce store. Handles large customer sets with resume capability and progress tracking.

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

## State Management

The script maintains state in a `state` directory to track progress and enable resume capability:

- `state/processed_customers.json`: Tracks all processed customer IDs

To start fresh, remove the state directory:
```bash
rm -rf state/
```

The script will create a new state directory when it runs.

## Options

- `--store-hash`: Your BigCommerce store hash (required)
- `--access-token`: Your BigCommerce API token (required)
- `--rate-limit`: Number of requests per 30 seconds (default: 150)
- `--batch-size`: Number of customers to delete in each batch (default: 10)
- `--max-concurrent`: Maximum number of concurrent connections (default: 5)
- `--dry-run`: Run in test mode without actually deleting customers (default: False)
- `--state-dir`: Directory to store state files (default: "./state")

## Progress Reporting

The script provides detailed progress information:
```
2025-01-09 17:30:00,000 - INFO - Found 1500 total customers
2025-01-09 17:30:00,100 - INFO - Already processed: 500 customers
2025-01-09 17:30:00,200 - INFO - Processed 510/1500 customers (34.0%)
...
2025-01-09 17:30:10,000 - INFO - Operation complete. Processed 1500/1500 customers (100.0%)
```

## Memory Usage

The script processes customers page by page instead of loading all customer IDs into memory at once:
- ~2MB of disk space per million customer IDs
- Small constant memory footprint regardless of total customer count

## Recovery

If the script is interrupted, it can be restarted with the same parameters. It will:
1. Load the list of already processed customers
2. Skip any previously processed customers
3. Continue processing remaining customers
4. Show progress as a percentage of total customers
#!/usr/bin/env python3
import asyncio
import aiohttp
import typer
import json
import logging
import sys
import os
from pathlib import Path
from typing import Set, List, Dict

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = typer.Typer()

class CustomerDeletionManager:
    def __init__(self):
        self.state_file = "state/processed_customers.json"
        self.state = self._load_state()
        self.processed_ids = self.state.get('processed_ids', set())
        self.total_customers = self.state.get('total_customers', None)
        
    def _load_state(self):
        """Load state including processed IDs and total customers"""
        if os.path.exists(self.state_file):
            with open(self.state_file, 'r') as f:
                state = json.load(f)
                # Convert processed_ids list to set
                if 'processed_ids' in state:
                    state['processed_ids'] = set(state['processed_ids'])
                return state
        return {}
    
    def _save_state(self):
        """Save state including processed IDs and total customers"""
        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
        state = {
            'processed_ids': list(self.processed_ids),
            'total_customers': self.total_customers
        }
        with open(self.state_file, 'w') as f:
            json.dump(state, f)
    
    def set_total_customers(self, total):
        """Set total customers only if not already set"""
        if self.total_customers is None:
            self.total_customers = total
            self._save_state()
    
    def process_customers(self, customer_ids):
        """Process customer IDs with proper progress tracking"""
        batch_size = len(customer_ids)
        remaining_customers = [c for c in customer_ids if c not in self.processed_ids]
        
        logging.debug(f"Processing batch of {batch_size} customers")
        
        for customer_id in remaining_customers:
            self.processed_ids.add(customer_id)
            
        # Save progress
        self._save_state()

class CustomerDeleter:
    def __init__(
        self,
        store_hash: str,
        access_token: str,
        rate_limit: int = 150,
        batch_size: int = 10,
        max_concurrent: int = 5,
        dry_run: bool = False,
        state_dir: Path = Path("./state")
    ):
        self.base_url = f"https://api.bigcommerce.com/stores/{store_hash}/v3"
        self.headers = {
            "X-Auth-Token": access_token,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        self.rate_limit = rate_limit
        self.batch_size = batch_size
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.dry_run = dry_run
        self.state = CustomerDeletionManager()
        self.sleep_time = 30 / rate_limit

    async def get_total_customers(self, session: aiohttp.ClientSession) -> int:
        """Get total customer count from API."""
        url = f"{self.base_url}/customers"
        params = {"limit": 1}
        
        async with session.get(url, headers=self.headers, params=params) as response:
            if response.status != 200:
                raise Exception(f"Failed to get customer count: {await response.text()}")
            data = await response.json()
            return data["meta"]["pagination"]["total"]

    async def get_customer_ids(self, session: aiohttp.ClientSession, page: int) -> List[int]:
        """Get customer IDs for a single page."""
        url = f"{self.base_url}/customers"
        params = {"page": page, "limit": 250}
        
        async with self.semaphore:
            async with session.get(url, headers=self.headers, params=params) as response:
                if response.status != 200:
                    raise Exception(f"Failed to fetch customers: {await response.text()}")
                data = await response.json()
                await asyncio.sleep(self.sleep_time)
                return [customer["id"] for customer in data["data"]]

    async def delete_customers(self, session: aiohttp.ClientSession, customer_ids: List[int]) -> bool:
        """Delete a batch of customers. Returns True if successful."""
        if not customer_ids:
            return True

        url = f"{self.base_url}/customers"
        params = {"id:in": ",".join(map(str, customer_ids))}

        if self.dry_run:
            logger.info(f"[DRY RUN] Would delete customers: {customer_ids}")
            return True

        async with self.semaphore:
            async with session.delete(url, headers=self.headers, params=params) as response:
                response_text = await response.text()
                if response.status == 204:
                    await asyncio.sleep(self.sleep_time)
                    return True
                logger.error(f"Failed to delete customers (Status {response.status}): {response_text}")
                return False

    async def run(self):
        """Main execution logic."""
        async with aiohttp.ClientSession() as session:
            # Get total count only if not already stored
            if self.state.total_customers is None:
                total_customers = await self.get_total_customers(session)
                self.state.set_total_customers(total_customers)
            else:
                total_customers = self.state.total_customers
                
            logger.info(f"Total customers to process: {total_customers}")
            logger.info(f"Already processed: {len(self.state.processed_ids)} customers")

            if self.dry_run:
                logger.info("DRY RUN MODE - No actual deletions will occur")

            page = 1
            while True:
                # Get customer IDs for current page
                customer_ids = await self.get_customer_ids(session, page)
                if not customer_ids:
                    break

                # Filter out already processed customers
                remaining_ids = [cid for cid in customer_ids 
                               if cid not in self.state.processed_ids]

                # Process in batches
                for i in range(0, len(remaining_ids), self.batch_size):
                    batch = remaining_ids[i:i + self.batch_size]
                    if await self.delete_customers(session, batch):
                        self.state.process_customers(batch)
                        logger.info(
                            f"Processed {len(self.state.processed_ids)}/{total_customers} "
                            f"customers ({(len(self.state.processed_ids)/total_customers)*100:.1f}%)"
                        )
                    await asyncio.sleep(0.2)  # Small delay between batches

                page += 1

            logger.info(
                f"Operation complete. Processed {len(self.state.processed_ids)}/{total_customers} "
                f"customers ({(len(self.state.processed_ids)/total_customers)*100:.1f}%)"
            )

@app.command()
def main(
    store_hash: str = typer.Option(..., help="BigCommerce store hash"),
    access_token: str = typer.Option(..., help="BigCommerce API access token"),
    rate_limit: int = typer.Option(150, help="Number of requests per 30 seconds"),
    batch_size: int = typer.Option(10, help="Number of customers to delete in each batch"),
    max_concurrent: int = typer.Option(5, help="Maximum number of concurrent connections"),
    dry_run: bool = typer.Option(False, help="Run in dry-run mode (no actual deletions)"),
    state_dir: str = typer.Option("./state", help="Directory to store state files")
):
    """Bulk delete customers from a BigCommerce store."""
    try:
        deleter = CustomerDeleter(
            store_hash=store_hash,
            access_token=access_token,
            rate_limit=rate_limit,
            batch_size=batch_size,
            max_concurrent=max_concurrent,
            dry_run=dry_run,
            state_dir=Path(state_dir)
        )
        
        asyncio.run(deleter.run())
        
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    app()
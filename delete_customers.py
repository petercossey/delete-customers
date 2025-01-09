#!/usr/bin/env python3
import asyncio
import aiohttp
import typer
import logging
import sys
from pathlib import Path
from typing import List, Set

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = typer.Typer()

class CustomerDeleter:
    def __init__(
        self,
        store_hash: str,
        access_token: str,
        rate_limit: int = 150,
        batch_size: int = 10,
        max_concurrent: int = 5,
        dry_run: bool = False,
    ):
        self.base_url = f"https://api.bigcommerce.com/stores/{store_hash}/v3"
        self.headers = {
            "X-Auth-Token": access_token,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        self.batch_size = batch_size
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.dry_run = dry_run
        self.processed_ids: Set[int] = set()
        self.sleep_time = 30 / rate_limit
        
    async def get_all_customer_ids(self, session: aiohttp.ClientSession) -> List[int]:
        """Get all customer IDs using pagination"""
        all_ids = []
        page = 1
        
        while True:
            url = f"{self.base_url}/customers"
            params = {"page": page, "limit": 250}
            
            async with self.semaphore, session.get(url, headers=self.headers, params=params) as response:
                if response.status == 429:  # Rate limit hit
                    retry_after = int(response.headers.get('Retry-After', 30))
                    logger.warning(f"Rate limited. Waiting {retry_after} seconds...")
                    await asyncio.sleep(retry_after)
                    continue
                    
                if response.status != 200:
                    raise Exception(f"Failed to fetch customers: {await response.text()}")
                
                data = await response.json()
                if not data["data"]:
                    break
                    
                page_ids = [customer["id"] for customer in data["data"]]
                all_ids.extend(page_ids)
                
                logger.info(f"Fetched page {page} - Found {len(page_ids)} customers")
                page += 1
                
                # Respect rate limits
                await asyncio.sleep(0.2)
        
        return all_ids

    async def delete_batch(self, session: aiohttp.ClientSession, customer_ids: List[int]) -> bool:
        """Delete a batch of customers"""
        if not customer_ids:
            return True

        url = f"{self.base_url}/customers"
        params = {"id:in": ",".join(map(str, customer_ids))}

        if self.dry_run:
            logger.info(f"[DRY RUN] Would delete customers: {customer_ids}")
            return True

        while True:  # Retry loop
            try:
                async with self.semaphore, session.delete(url, headers=self.headers, params=params) as response:
                    if response.status == 429:  # Rate limit hit
                        retry_after = int(response.headers.get('Retry-After', 30))
                        logger.warning(f"Rate limited. Waiting {retry_after} seconds...")
                        await asyncio.sleep(retry_after)
                        continue
                        
                    if response.status == 204:
                        self.processed_ids.update(customer_ids)
                        await asyncio.sleep(0.2)  # Respect rate limits
                        return True
                        
                    if response.status >= 500:
                        logger.error(f"Server error: {await response.text()}")
                        await asyncio.sleep(5)  # Back off on server errors
                        continue
                        
                    logger.error(f"Failed to delete customers: {await response.text()}")
                    return False
                    
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                logger.error(f"Request failed: {str(e)}")
                await asyncio.sleep(5)
                continue

    async def run(self):
        """Main execution logic"""
        timeout = aiohttp.ClientTimeout(total=300)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            # First, get all customer IDs
            logger.info("Fetching all customer IDs...")
            all_customer_ids = await self.get_all_customer_ids(session)
            total_customers = len(all_customer_ids)
            
            if total_customers == 0:
                logger.info("No customers found to process")
                return
                
            logger.info(f"Found {total_customers} customers to process")
            
            # Process in batches
            for i in range(0, total_customers, self.batch_size):
                batch = all_customer_ids[i:i + self.batch_size]
                if await self.delete_batch(session, batch):
                    logger.info(
                        f"Progress: {len(self.processed_ids)}/{total_customers} "
                        f"({len(self.processed_ids)/total_customers*100:.1f}%)"
                    )
                await asyncio.sleep(0.2)  # Respect rate limits
            
            logger.info(
                f"Operation complete. Processed {len(self.processed_ids)}/{total_customers} "
                f"customers ({len(self.processed_ids)/total_customers*100:.1f}%)"
            )

@app.command()
def main(
    store_hash: str = typer.Option(..., help="BigCommerce store hash"),
    access_token: str = typer.Option(..., help="BigCommerce API access token"),
    rate_limit: int = typer.Option(150, help="Number of requests per 30 seconds"),
    batch_size: int = typer.Option(10, help="Number of customers to delete in each batch"),
    max_concurrent: int = typer.Option(5, help="Maximum number of concurrent connections"),
    dry_run: bool = typer.Option(False, help="Run in dry-run mode (no actual deletions)"),
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
        )
        
        asyncio.run(deleter.run())
        
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    app()
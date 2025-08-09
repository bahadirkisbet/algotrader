#!/usr/bin/env python3
"""
Binance Data Ingestor

This script fetches monthly candle data from Binance Vision API,
unzips the data, merges it, and saves it using the archive manager.
"""

import asyncio
import aiohttp
import aiofiles
import gzip
import json
import os
import re
from datetime import datetime
from typing import List, Dict, Any
from pathlib import Path

# Add parent directory to path to import modules
import sys
sys.path.append(str(Path(__file__).parent.parent))

from modules.archive.archive_manager import ArchiveManager
from models.data_models.candle import Candle
from models.time_models import Interval


class BinanceDataIngestor:
    """Fetches and processes Binance historical data from Binance Vision API."""
    
    def __init__(self, config_file: str = "config.ini"):
        self.base_url = "https://data.binance.vision"
        self.archive_manager = ArchiveManager(config_file)
        self.temp_dir = "temp_downloads"
        
        # Create temp directory if it doesn't exist
        if not os.path.exists(self.temp_dir):
            os.makedirs(self.temp_dir)
    
    async def fetch_monthly_data_links(self, symbol: str = "BTCUSDT", interval: str = "5m") -> List[str]:
        """Fetch all available monthly data download links for a symbol and interval."""
        # The page uses JavaScript to load data from S3, so we'll directly access the S3 bucket
        # or use the list.js endpoint that contains the actual file listing
        
        # First try to get the list.js file which contains the actual data
        list_url = f"{self.base_url}/list.js?prefix=data/spot/monthly/klines/{symbol}/{interval}/"
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(list_url) as response:
                    if response.status == 200:
                        js_content = await response.text()
                        # Parse the JavaScript content to extract file URLs
                        zip_links = self.parse_list_js(js_content, symbol, interval)
                        if zip_links:
                            return zip_links
            except Exception as e:
                print(f"Warning: Could not fetch list.js: {e}")
            
            # Fallback: try to construct URLs based on common patterns
            # Binance typically has data from 2017 onwards
            print("Using fallback method to construct download URLs...")
            return self.construct_fallback_urls(symbol, interval)
    
    def parse_list_js(self, js_content: str, symbol: str, interval: str) -> List[str]:
        """Parse the list.js content to extract file URLs."""
        # The list.js file contains JavaScript code that defines the file listing
        # We need to extract the actual file paths from it
        
        # Look for patterns like "data/spot/monthly/klines/BTCUSDT/5m/BTCUSDT-5m-2023-01.zip"
        import re
        
        # Pattern to match the file paths in the JavaScript
        pattern = rf'"{symbol}-{interval}-(\d{{4}})-(\d{{2}})\.zip"'
        matches = re.findall(pattern, js_content)
        
        if matches:
            zip_links = []
            for year, month in matches:
                file_path = f"data/spot/monthly/klines/{symbol}/{interval}/{symbol}-{interval}-{year}-{month}.zip"
                full_url = f"{self.base_url}/{file_path}"
                zip_links.append(full_url)
            
            print(f"Found {len(zip_links)} files from list.js")
            return zip_links
        
        return []
    
    def construct_fallback_urls(self, symbol: str, interval: str) -> List[str]:
        """Construct download URLs based on common patterns when list.js is not available."""
        # Binance typically has data from 2017 onwards
        # We'll try to construct URLs for recent years and months
        
        current_year = datetime.now().year
        current_month = datetime.now().month
        
        zip_links = []
        
        # Try to get data for the last few years
        for year in range(2020, current_year + 1):
            for month in range(1, 13):
                # Skip future months
                if year == current_year and month > current_month:
                    break
                
                # Format month with leading zero
                month_str = f"{month:02d}"
                
                file_path = f"data/spot/monthly/klines/{symbol}/{interval}/{symbol}-{interval}-{year}-{month_str}.zip"
                full_url = f"{self.base_url}/{file_path}"
                zip_links.append(full_url)
        
        print(f"Constructed {len(zip_links)} fallback URLs for {symbol} {interval}")
        return zip_links
    
    async def download_file(self, session: aiohttp.ClientSession, url: str, filename: str) -> str:
        """Download a file from URL and save it to temp directory."""
        filepath = os.path.join(self.temp_dir, filename)
        
        async with session.get(url) as response:
            if response.status != 200:
                raise Exception(f"Failed to download {url}: {response.status}")
            
            async with aiofiles.open(filepath, 'wb') as f:
                async for chunk in response.content.iter_chunked(8192):
                    await f.write(chunk)
        
        return filepath
    
    async def download_all_monthly_data(self, symbol: str = "BTCUSDT", interval: str = "5m") -> List[str]:
        """Download all monthly data files for a symbol and interval."""
        print(f"Fetching monthly data links for {symbol} {interval}...")
        zip_links = await self.fetch_monthly_data_links(symbol, interval)
        
        if not zip_links:
            print("No monthly data files found.")
            return []
        
        print(f"Found {len(zip_links)} monthly data files to download.")
        
        # Validate URLs before downloading
        print("Validating URLs...")
        valid_urls = await self.validate_urls(zip_links)
        
        if not valid_urls:
            print("No valid URLs found after validation.")
            return []
        
        print(f"Proceeding with {len(valid_urls)} valid URLs.")
        
        downloaded_files = []
        async with aiohttp.ClientSession() as session:
            for i, url in enumerate(valid_urls, 1):
                filename = url.split('/')[-1]
                print(f"Downloading {i}/{len(valid_urls)}: {filename}")
                
                try:
                    filepath = await self.download_file(session, url, filename)
                    downloaded_files.append(filepath)
                    print(f"✓ Downloaded: {filename}")
                except Exception as e:
                    print(f"✗ Failed to download {filename}: {e}")
        
        return downloaded_files
    
    async def validate_urls(self, urls: List[str]) -> List[str]:
        """Validate URLs by checking if they return 200 status."""
        valid_urls = []
        
        async with aiohttp.ClientSession() as session:
            for url in urls:
                try:
                    async with session.head(url) as response:
                        if response.status == 200:
                            valid_urls.append(url)
                            print(f"✓ Valid: {url.split('/')[-1]}")
                        else:
                            print(f"✗ Invalid ({response.status}): {url.split('/')[-1]}")
                except Exception as e:
                    print(f"✗ Error checking {url.split('/')[-1]}: {e}")
        
        return valid_urls
    
    def parse_csv_line(self, line: str, symbol: str) -> Candle:
        """Parse a CSV line from Binance data into a Candle object."""
        # Binance CSV format: Open time, Open, High, Low, Close, Volume, Close time, Quote asset volume, Number of trades, Taker buy base asset volume, Taker buy quote asset volume, Ignore
        parts = line.strip().split(',')
        
        if len(parts) < 6:
            raise ValueError(f"Invalid CSV line format: {line}")
        
        # Validate and clean timestamp
        try:
            open_time = int(parts[0])  # Open time in milliseconds
            
            # Validate timestamp range (should be between 2010 and 2030)
            # Convert to seconds and check if it's reasonable
            timestamp_seconds = open_time / 1000
            if timestamp_seconds < 1262304000 or timestamp_seconds > 1893456000:  # 2010-01-01 to 2030-01-01
                raise ValueError(f"Timestamp {open_time} is out of reasonable range")
                
        except (ValueError, OverflowError) as e:
            raise ValueError(f"Invalid timestamp {parts[0]}: {e}")
        
        try:
            open_price = float(parts[1])
            high_price = float(parts[2])
            low_price = float(parts[3])
            close_price = float(parts[4])
            volume = float(parts[5])
            trade_count = int(parts[8]) if len(parts) > 8 else 0
        except (ValueError, IndexError) as e:
            raise ValueError(f"Invalid numeric values in line: {e}")
        
        return Candle(
            symbol=symbol,
            timestamp=open_time,
            open=open_price,
            high=high_price,
            low=low_price,
            close=close_price,
            volume=volume,
            trade_count=trade_count
        )
    
    async def process_zip_file(self, zip_filepath: str, symbol: str) -> List[Candle]:
        """Extract and process a zip file containing CSV data."""
        import zipfile
        
        candles = []
        
        try:
            with zipfile.ZipFile(zip_filepath, 'r') as zip_ref:
                # Get the CSV file from the zip
                csv_files = [f for f in zip_ref.namelist() if f.endswith('.csv')]
                
                if not csv_files:
                    print(f"No CSV files found in {zip_filepath}")
                    return candles
                
                csv_filename = csv_files[0]
                
                # Read and parse the CSV content
                with zip_ref.open(csv_filename) as csv_file:
                    # Skip header if present
                    lines = csv_file.read().decode('utf-8').split('\n')
                    
                    valid_candles = 0
                    invalid_lines = 0
                    
                    for line_num, line in enumerate(lines, 1):
                        line = line.strip()
                        if not line or line.startswith('Open time'):  # Skip empty lines and headers
                            continue
                        
                        try:
                            candle = self.parse_csv_line(line, symbol)
                            candles.append(candle)
                            valid_candles += 1
                        except Exception as e:
                            invalid_lines += 1
                            if invalid_lines <= 5:  # Only show first 5 errors to avoid spam
                                print(f"Warning: Failed to parse line {line_num} in {os.path.basename(zip_filepath)}: {e}")
                                if invalid_lines == 1:  # Show the problematic line for first error
                                    print(f"  Problematic line: {line[:100]}...")
                            elif invalid_lines == 6:
                                print(f"... and {invalid_lines - 5} more invalid lines in {os.path.basename(zip_filepath)}")
                            continue
                    
                    if invalid_lines > 0:
                        print(f"⚠️  {invalid_lines} invalid lines were skipped in {os.path.basename(zip_filepath)}")
                    
                    print(f"✓ Processed {zip_filepath}: {valid_candles} valid candles, {invalid_lines} invalid lines skipped")
                
        except Exception as e:
            print(f"Error processing {zip_filepath}: {e}")
        
        return candles
    
    async def merge_and_save_data(self, all_candles: List[Candle], symbol: str, interval: str):
        """Merge all candles and save them using the archive manager."""
        if not all_candles:
            print("No candles to save.")
            return
        
        # Additional validation: filter out any candles with invalid timestamps
        valid_candles = []
        invalid_candles = 0
        
        for candle in all_candles:
            try:
                # Test if timestamp can be converted to datetime
                timestamp_seconds = candle.timestamp / 1000
                if timestamp_seconds < 1262304000 or timestamp_seconds > 1893456000:  # 2010-01-01 to 2030-01-01
                    invalid_candles += 1
                    continue
                valid_candles.append(candle)
            except Exception:
                invalid_candles += 1
                continue
        
        if invalid_candles > 0:
            print(f"⚠️  Filtered out {invalid_candles} candles with invalid timestamps")
        
        if not valid_candles:
            print("No valid candles to save after filtering.")
            return
        
        # Sort candles by timestamp
        valid_candles.sort(key=lambda x: x.timestamp)
        
        print(f"Total valid candles to save: {len(valid_candles)}")
        
        try:
            start_date = datetime.fromtimestamp(valid_candles[0].timestamp/1000)
            end_date = datetime.fromtimestamp(valid_candles[-1].timestamp/1000)
            print(f"Date range: {start_date} to {end_date}")
        except Exception as e:
            print(f"Warning: Could not display date range: {e}")
        
        # Convert interval string to Interval enum
        interval_enum = self.string_to_interval(interval)
        
        # Save using archive manager
        await self.archive_manager.archive_candles(symbol, valid_candles, interval)
        
        print(f"✓ Successfully saved {len(valid_candles)} candles for {symbol} {interval}")
    
    def string_to_interval(self, interval_str: str) -> Interval:
        """Convert interval string to Interval enum."""
        interval_map = {
            "1m": Interval.ONE_MINUTE,
            "5m": Interval.FIVE_MINUTES,
            "15m": Interval.FIFTEEN_MINUTES,
            "30m": Interval.THIRTY_MINUTES,
            "1h": Interval.ONE_HOUR,
            "1d": Interval.ONE_DAY
        }
        return interval_map.get(interval_str, Interval.FIVE_MINUTES)
    
    async def cleanup_temp_files(self, file_paths: List[str]):
        """Clean up temporary downloaded files."""
        for filepath in file_paths:
            try:
                if os.path.exists(filepath):
                    os.remove(filepath)
                    print(f"✓ Cleaned up: {os.path.basename(filepath)}")
            except Exception as e:
                print(f"Warning: Failed to clean up {filepath}: {e}")
        
        # Remove temp directory if empty
        try:
            if os.path.exists(self.temp_dir) and not os.listdir(self.temp_dir):
                os.rmdir(self.temp_dir)
                print("✓ Cleaned up temp directory")
        except Exception as e:
            print(f"Warning: Failed to clean up temp directory: {e}")
    
    async def ingest_monthly_data(self, symbol: str = "BTCUSDT", interval: str = "5m"):
        """Main method to ingest monthly data for a symbol and interval."""
        print(f"Starting data ingestion for {symbol} {interval}...")
        print("=" * 50)
        
        try:
            # Step 1: Download all monthly data files
            downloaded_files = await self.download_all_monthly_data(symbol, interval)
            
            if not downloaded_files:
                print("No files downloaded. Exiting.")
                return
            
            # Step 2: Process each zip file and extract candles
            all_candles = []
            for zip_file in downloaded_files:
                candles = await self.process_zip_file(zip_file, symbol)
                all_candles.extend(candles)
            
            # Step 3: Merge and save data
            await self.merge_and_save_data(all_candles, symbol, interval)
            
            # Step 4: Cleanup
            await self.cleanup_temp_files(downloaded_files)
            
            print("=" * 50)
            print(f"✓ Data ingestion completed successfully for {symbol} {interval}")
            print(f"Total candles processed: {len(all_candles)}")
            
        except Exception as e:
            print(f"✗ Data ingestion failed: {e}")
            raise
    
    async def shutdown(self):
        """Cleanup resources."""
        await self.archive_manager.shutdown()


async def main():
    """Main function to run the data ingestion."""
    ingestor = BinanceDataIngestor()
    
    try:
        # Ingest BTCUSDT 5m data
        await ingestor.ingest_monthly_data("BTCUSDT", "5m")
        
        # You can add more symbols/intervals here if needed
        # await ingestor.ingest_monthly_data("ETHUSDT", "5m")
        # await ingestor.ingest_monthly_data("BTCUSDT", "1h")
        
    except Exception as e:
        print(f"Error in main: {e}")
    finally:
        await ingestor.shutdown()


if __name__ == "__main__":
    asyncio.run(main())

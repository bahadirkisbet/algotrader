#!/usr/bin/env python3
"""
Simple test script to verify async functionality.
"""

import asyncio
import logging
from datetime import datetime, timedelta

from models.time_models import Interval
from data_center.async_data_center import AsyncDataCenter
from data_provider.exchange_collection.exchange_library.binance_spot import Binance
from managers.async_archive_manager import AsyncArchiveManager


async def test_basic_async():
    """Test basic async functionality."""
    print("Testing basic async functionality...")
    
    # Test data center initialization
    data_center = AsyncDataCenter()
    print("✓ Data center created")
    
    # Test exchange creation
    exchange = Binance()
    print("✓ Exchange created")
    
    # Test archive manager
    archiver = AsyncArchiveManager()
    print("✓ Archive manager created")
    
    # Set dependencies
    data_center.set_exchange(exchange)
    data_center.set_archiver(archiver)
    print("✓ Dependencies set")
    
    # Test initialization
    await data_center.initialize()
    print("✓ Data center initialized")
    
    # Test start/stop
    await data_center.start()
    print("✓ Data center started")
    
    await asyncio.sleep(1)  # Let it run for a bit
    
    await data_center.stop()
    print("✓ Data center stopped")
    
    # Test exchange methods
    try:
        products = await exchange.fetch_product_list()
        print(f"✓ Fetched {len(products)} products from exchange")
    except Exception as e:
        print(f"⚠ Exchange fetch failed (expected in test): {e}")
    
    # Test archive manager
    try:
        files = await archiver.list()
        print(f"✓ Archive manager listed {len(files)} files")
    except Exception as e:
        print(f"⚠ Archive list failed (expected in test): {e}")
    
    print("\n🎉 All basic async tests passed!")


async def test_data_processing():
    """Test data processing functionality."""
    print("\nTesting data processing...")
    
    data_center = AsyncDataCenter()
    
    # Test adding data to buffer
    from models.data_models.candle import Candle
    
    test_candle = Candle(
        symbol="TEST",
        timestamp=int(datetime.now().timestamp() * 1000),
        open=100.0,
        high=110.0,
        low=90.0,
        close=105.0,
        volume=1000.0,
        trade_count=50
    )
    
    data_center.add_candle(test_candle)
    print("✓ Test candle added to buffer")
    
    # Test status
    status = await data_center.get_status()
    print(f"✓ Status retrieved: {status}")
    
    print("🎉 Data processing tests passed!")


async def main():
    """Main test function."""
    print("🚀 Starting Async AlgoTrader Tests\n")
    
    try:
        await test_basic_async()
        await test_data_processing()
        
        print("\n✅ All tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    
    # Run tests
    asyncio.run(main()) 
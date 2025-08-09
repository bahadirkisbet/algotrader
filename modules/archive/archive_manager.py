import asyncio
import configparser
import gzip
import json
import os
from typing import List

from models.data_models.candle import Candle
from models.time_models import Interval


class ArchiveManager:
    """Manages data archiving and retrieval operations."""
    
    def __init__(self, config_file: str = "config.ini"):
        self.config = configparser.ConfigParser()
        self.config.read(config_file)
        
        self.__archive_folder__ = self.config.get("ARCHIVE", "archive_folder", fallback="archive")
        self.__default_encoding__ = self.config.get("ARCHIVE", "default_encoding", fallback="utf-8")
        
        # Create archive folder if it doesn't exist
        if not os.path.exists(self.__archive_folder__):
            os.mkdir(self.__archive_folder__)
    
    async def save(self,
                   exchange_code: str,
                   symbol: str,
                   data_type: str,
                   data_frame: str,
                   data: List[Candle]) -> None:
        """Save data to archive asynchronously."""
        file_name = f"{self.__archive_folder__}/{exchange_code}_{data_type}_{symbol}_{data_frame}.json.gz"
        json_dict = {
            "exchange_code": exchange_code,
            "symbol": symbol,
            "data_type": data_type,
            "data_frame": data_frame,
            "data": [candle.to_dict() for candle in data]
        }
        json_str = json.dumps(json_dict).encode(self.__default_encoding__)
        
        # Use asyncio to run the file operation in a thread pool
        await asyncio.get_event_loop().run_in_executor(
            None, self.__write_gzip_file__, file_name, json_str
        )
    
    def __write_gzip_file__(self, file_name: str, data: bytes) -> None:
        """Write gzipped data to file (synchronous, runs in thread pool)."""
        with gzip.open(file_name, "w") as out:
            out.write(data)
    
    async def read(self, exchange_code: str,
                   symbol: str,
                   data_type: str,
                   data_frame: str) -> List[Candle]:
        """Read data from archive asynchronously."""
        file_name = f"{self.__archive_folder__}/{exchange_code}_{data_type}_{symbol}_{data_frame}.json.gz"
        
        if not os.path.exists(file_name):
            return []
        
        # Use asyncio to run the file operation in a thread pool
        return await asyncio.get_event_loop().run_in_executor(
            None, self.__read_gzip_file__, file_name
        )
    
    def __read_gzip_file__(self, file_name: str) -> List[Candle]:
        """Read gzipped data from file (synchronous, runs in thread pool)."""
        with gzip.open(file_name, "r") as f_in:
            json_str = f_in.read().decode(self.__default_encoding__)
        return [Candle(*json_candle) for json_candle in json.loads(json_str)["data"]]
    
    async def list(self) -> List[str]:
        """List archive files asynchronously."""
        return await asyncio.get_event_loop().run_in_executor(
            None, os.listdir, self.__archive_folder__
        )
    
    async def get_file_names_filtered(self,
                                     exchange_code: str = None,
                                     symbol: str = None,
                                     data_type: str = None,
                                     data_frame: str = None) -> List[str]:
        """Get filtered file names asynchronously."""
        file_names = await self.list()
        
        if exchange_code is not None:
            file_names = [file for file in file_names if file.startswith(f"{exchange_code}_")]
        
        if symbol is not None:
            file_names = [file for file in file_names if f"_{symbol}_" in file]
        
        if data_type is not None:
            file_names = [file for file in file_names if f"_{data_type}_" in file]
        
        if data_frame is not None:
            file_names = [file for file in file_names if file.endswith(f"_{data_frame}.json.gz")]
        
        return file_names
    
    async def read_file(self, file_name: str) -> List[Candle]:
        """Read a specific file asynchronously."""
        return await asyncio.get_event_loop().run_in_executor(
            None, self.__read_gzip_file__, file_name
        )
    
    async def archive_candle(self, candle: Candle) -> None:
        """Archive a single candle asynchronously."""
        try:
            # Get exchange code from config or use default
            exchange_code = self.config.get("EXCHANGE", "exchange_code", fallback="UNKNOWN")
            
            # Archive the candle
            await self.save(
                exchange_code=exchange_code,
                symbol=candle.symbol,
                data_type="CANDLE",
                data_frame="1m",  # Default frame, could be configurable
                data=[candle]
            )
            
            self.logger.debug(f"Archived candle for {candle.symbol}")
            
        except Exception as e:
            self.logger.error(f"Failed to archive candle: {e}")
    
    async def get_candles(self, symbol: str, interval: Interval) -> List[Candle]:
        """Get candles for a symbol and interval asynchronously."""
        try:
            # Get exchange code from config
            exchange_code = self.config.get("EXCHANGE", "exchange_code", fallback="UNKNOWN")
            
            # Try to read archived data
            candles = await self.read(
                exchange_code=exchange_code,
                symbol=symbol,
                data_type="CANDLE",
                data_frame=self.__interval_to_frame__(interval)
            )
            
            return candles
            
        except Exception as e:
            self.logger.error(f"Failed to get candles for {symbol}: {e}")
            return []
    
    def __interval_to_frame__(self, interval: Interval) -> str:
        """Convert interval to frame string."""
        interval_map = {
            Interval.ONE_MINUTE: "1m",
            Interval.FIVE_MINUTES: "5m",
            Interval.FIFTEEN_MINUTES: "15m",
            Interval.ONE_HOUR: "1h",
            Interval.FOUR_HOURS: "4h",
            Interval.ONE_DAY: "1d"
        }
        return interval_map.get(interval, "1m")
    
    async def shutdown(self) -> None:
        """Shutdown the archive manager."""
        # No specific cleanup needed for file operations
        pass

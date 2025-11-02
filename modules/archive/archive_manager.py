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

        self.archive_folder = self.config.get("ARCHIVE", "archive_folder", fallback=".cache")
        self.default_encoding = self.config.get("ARCHIVE", "default_encoding", fallback="utf-8")

        # Create archive folder if it doesn't exist
        if not os.path.exists(self.archive_folder):
            os.mkdir(self.archive_folder)

    async def save(
        self, exchange_code: str, symbol: str, data_type: str, data_frame: str, data: List[Candle]
    ) -> None:
        """Save data to archive asynchronously."""
        file_name = (
            f"{self.archive_folder}/{exchange_code}_{data_type}_{symbol}_{data_frame}.json.gz"
        )
        json_dict = {
            "exchange_code": exchange_code,
            "symbol": symbol,
            "data_type": data_type,
            "data_frame": data_frame,
            "data": [candle.to_dict() for candle in data],
        }
        json_str = json.dumps(json_dict).encode(self.default_encoding)

        # Use asyncio to run the file operation in a thread pool
        await asyncio.get_event_loop().run_in_executor(
            None, self.write_gzip_file, file_name, json_str
        )

    def write_gzip_file(self, file_name: str, data: bytes) -> None:
        """Write gzipped data to file (synchronous, runs in thread pool)."""
        with gzip.open(file_name, "w") as out:
            out.write(data)

    async def read(
        self, exchange_code: str, symbol: str, data_type: str, data_frame: str
    ) -> List[Candle]:
        """Read data from archive asynchronously."""
        file_name = (
            f"{self.archive_folder}/{exchange_code}_{data_type}_{symbol}_{data_frame}.json.gz"
        )

        if not os.path.exists(file_name):
            return []

        # Use asyncio to run the file operation in a thread pool
        return await asyncio.get_event_loop().run_in_executor(None, self.read_gzip_file, file_name)

    def read_gzip_file(self, file_name: str) -> List[Candle]:
        """Read gzipped data from file (synchronous, runs in thread pool)."""
        with gzip.open(file_name, "r") as f_in:
            json_str = f_in.read().decode(self.default_encoding)
        return [Candle.from_json(json_candle) for json_candle in json.loads(json_str)["data"]]

    async def list(self) -> List[str]:
        """List archive files asynchronously."""
        return await asyncio.get_event_loop().run_in_executor(None, os.listdir, self.archive_folder)

    async def get_file_names_filtered(
        self,
        exchange_code: str = None,
        symbol: str = None,
        data_type: str = None,
        data_frame: str = None,
    ) -> List[str]:
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
        """Read data from a specific archive file."""
        file_path = f"{self.archive_folder}/{file_name}"
        if not os.path.exists(file_path):
            return []

        return await asyncio.get_event_loop().run_in_executor(None, self.read_gzip_file, file_path)

    async def archive_candle(self, candle: Candle) -> None:
        """Archive a single candle."""
        # Group candles by symbol and interval for efficient archiving
        # This is a simplified version - in practice, you might want to batch candles
        await self.save(
            exchange_code="BINANCE",  # Default, should be configurable
            symbol=candle.symbol,
            data_type="CANDLE",
            data_frame="1m",  # Default interval, should be configurable
            data=[candle],
        )

    async def archive_candles(
        self, symbol: str, candles: List[Candle], interval: str = "5m"
    ) -> None:
        """Archive multiple candles for a symbol."""
        if not candles:
            return

        # Group by interval (assuming all candles have same interval)
        # In practice, you might want to group by actual interval
        await self.save(
            exchange_code="BINANCE",  # Default, should be configurable
            symbol=symbol,
            data_type="CANDLE",
            data_frame=interval,  # Use the actual interval
            data=candles,
        )

    async def get_candles(self, symbol: str, interval: Interval) -> List[Candle]:
        """Get archived candles for a symbol and interval."""
        data_frame = self.interval_to_frame(interval)

        return await self.read(
            exchange_code="BINANCE",  # Default, should be configurable
            symbol=symbol,
            data_type="CANDLE",
            data_frame=data_frame,
        )

    def interval_to_frame(self, interval: Interval) -> str:
        """Convert interval to frame string for file naming."""
        match interval:
            case Interval.ONE_MINUTE:
                return "1m"
            case Interval.FIVE_MINUTES:
                return "5m"
            case Interval.FIFTEEN_MINUTES:
                return "15m"
            case Interval.ONE_HOUR:
                return "1h"
            case Interval.ONE_DAY:
                return "1d"
            case _:
                return "1m"  # Default

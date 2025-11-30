"""
Binance Exchange REST API Implementation.

This module implements the REST API operations for Binance exchange,
following SOLID principles and async best practices.
"""

import asyncio
import csv
import io
import zipfile
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

import aiohttp

from modules.exchange.exchange import Exchange
from modules.model.candle import Candle
from modules.model.exchange_info import ExchangeInfo
from modules.model.exchange_type import ExchangeType
from modules.model.interval import Interval
from modules.model.sorting_option import SortBy, SortingOption


class BinanceExchange(Exchange):
    """
    Binance exchange REST API implementation.

    Handles all REST API operations for Binance including:
    - Fetching product lists
    - Historical OHLCV data
    - Exchange information
    """

    def __init__(self, exchange_type: ExchangeType = ExchangeType.SPOT):
        """
        Initialize Binance exchange.

        Args:
            exchange_type: Type of exchange (SPOT by default)
        """
        super().__init__(exchange_type)

        # Binance-specific configuration
        self.api_url = "https://api.binance.com/api/v3"
        self.api_endpoints = {
            "exchange_info": "/exchangeInfo",
            "klines": "/klines",
            "ticker_price": "/ticker/price",
            "ticker_24hr": "/ticker/24hr",
        }

        # Binance Vision configuration for bulk historical data
        self.vision_base_url = "https://data.binance.vision"
        self._setup_vision_urls()

        # HTTP session for connection pooling
        self.session: Optional[aiohttp.ClientSession] = None

        # Exchange metadata
        self.first_data_date = datetime(2017, 7, 14)  # Binance launch date
        self.exchange_name = "Binance"

        # Feature flags
        self.use_vision_for_historical = True  # Use Binance Vision for historical data

    def _setup_vision_urls(self) -> None:
        """Setup Binance Vision URLs based on exchange type."""
        if self.exchange_type == ExchangeType.SPOT:
            self.vision_data_path = "data/spot"
        elif self.exchange_type == ExchangeType.FUTURES:
            self.vision_data_path = "data/futures/um"
        else:
            self.vision_data_path = "data/spot"

    async def initialize(self, on_candle_received: Callable[[Candle], None]) -> None:
        """Initialize the Binance exchange connection."""
        try:
            self.session = aiohttp.ClientSession()
            self.on_candle_received = on_candle_received
            if await self.test_connection():
                await self.set_initialized(True)
                if self.logger:
                    self.logger.info("Binance exchange initialized successfully")
            else:
                raise ConnectionError("Failed to connect to Binance API")

        except Exception as e:
            if self.logger:
                self.logger.error("Failed to initialize Binance exchange: %s", e)
            raise

        """Get the name of the exchange."""
        return self.exchange_name

    async def fetch_product_list(
        self, sorting_option: Optional[SortingOption] = None, limit: int = -1
    ) -> List[str]:
        """
        Fetch list of available trading products from Binance.

        Args:
            sorting_option: Optional sorting configuration
            limit: Maximum number of products to return

        Returns:
            List of trading pair symbols
        """
        if not self.session:
            raise RuntimeError("Exchange not initialized. Call initialize() first.")

        try:
            url = f"{self.api_url}{self.api_endpoints['exchange_info']}"

            async with self.session.get(url) as response:
                if response.status != 200:
                    raise aiohttp.ClientResponseError(
                        response.request_info,
                        response.history,
                        status=response.status,
                        message=f"HTTP {response.status}",
                    )

                data = await response.json()
                symbols_data = data.get("symbols", [])

                # Filter for trading pairs only
                symbols_data = [s for s in symbols_data if s.get("status") == "TRADING"]

                # Apply sorting if specified
                if sorting_option:
                    symbols_data = self._apply_sorting(symbols_data, sorting_option)

                # Apply limit
                if limit > 0:
                    symbols_data = symbols_data[:limit]

                symbols = [s["symbol"] for s in symbols_data]

                if self.logger:
                    self.logger.info(
                        "Fetched %s trading symbols from Binance", len(symbols)
                    )

                return symbols

        except Exception as e:
            if self.logger:
                self.logger.error("Failed to fetch product list: %s", e)
            raise

    @staticmethod
    def _apply_sorting(
        data: List[Dict[str, Any]], sorting_option: SortingOption
    ) -> List[Dict[str, Any]]:
        """
        Apply sorting to product list.

        Args:
            data: List of symbol dictionaries
            sorting_option: Sorting configuration

        Returns:
            Sorted list of symbols
        """
        is_reverse = sorting_option.sort_order.value

        if sorting_option.sort_by == SortBy.SYMBOL:
            data.sort(key=lambda x: x.get("symbol", ""), reverse=is_reverse)
        elif sorting_option.sort_by == SortBy.VOLUME:
            data.sort(key=lambda x: float(x.get("volume", 0)), reverse=is_reverse)
        elif sorting_option.sort_by == SortBy.PRICE:
            data.sort(key=lambda x: float(x.get("price", 0)), reverse=is_reverse)

        return data

    async def fetch_ohlcv(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        interval: Interval,
    ) -> List[Candle]:
        """Fetch OHLCV data from Binance."""
        return await self.fetch_historical_data(symbol, start_date, end_date, interval)

    async def fetch_historical_data(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        interval: Interval,
    ) -> List[Candle]:
        """
        Fetch historical candle data from Binance.

        Uses Binance Vision for bulk historical data (recommended for large datasets)
        and falls back to REST API for recent data or when Vision fails.

        Args:
            symbol: Trading pair symbol (e.g., "BTCUSDT")
            start_date: Start date for data
            end_date: End date for data
            interval: Candle interval

        Returns:
            List of Candle objects
        """
        if not self.session:
            raise RuntimeError("Exchange not initialized. Call initialize() first.")

        try:
            # Determine if we should use Binance Vision or REST API
            time_range_days = (end_date - start_date).days

            # Use Vision for historical data older than 7 days or large ranges
            if self.use_vision_for_historical and (
                time_range_days > 7 or (datetime.utcnow() - end_date).days > 7
            ):
                if self.logger:
                    self.logger.info(
                        "Using Binance Vision for %s (range: %s days)",
                        symbol,
                        time_range_days,
                    )
                try:
                    candles = await self._fetch_from_vision(
                        symbol, start_date, end_date, interval
                    )
                    if candles:
                        return candles
                except Exception as e:
                    if self.logger:
                        self.logger.warning(
                            "Binance Vision fetch failed, falling back to REST API: %s",
                            e,
                        )

            # Fall back to REST API
            if self.logger:
                self.logger.info("Using REST API for %s", symbol)
            return await self._fetch_from_api(symbol, start_date, end_date, interval)

        except Exception as e:
            if self.logger:
                self.logger.error(
                    "Failed to fetch historical data for %s: %s", symbol, e
                )
            raise

    async def _fetch_from_api(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        interval: Interval,
    ) -> List[Candle]:
        """
        Fetch historical data using Binance REST API.

        Args:
            symbol: Trading pair symbol
            start_date: Start date
            end_date: End date
            interval: Candle interval

        Returns:
            List of Candle objects
        """
        # Create URL list for pagination
        url_list = self._create_url_list(symbol, start_date, end_date, interval)

        # Fetch all pages concurrently
        tasks = [self._fetch_page(url, symbol) for url in url_list]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Combine results
        candles = []
        for result in results:
            if isinstance(result, Exception):
                if self.logger:
                    self.logger.warning("Failed to fetch page: %s", result)
                continue
            if result:
                candles.extend(result)

        if self.logger:
            self.logger.info(
                "Fetched %s historical candles for %s", len(candles), symbol
            )

        return candles

    async def _fetch_from_vision(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        interval: Interval,
    ) -> List[Candle]:
        """
        Fetch historical data from Binance Vision.

        Binance Vision provides bulk historical data in CSV format organized by:
        - Daily files: data/spot/daily/klines/BTCUSDT/1m/BTCUSDT-1m-2024-01-01.zip
        - Monthly files: data/spot/monthly/klines/BTCUSDT/1m/BTCUSDT-1m-2024-01.zip

        Args:
            symbol: Trading pair symbol
            start_date: Start date
            end_date: End date
            interval: Candle interval

        Returns:
            List of Candle objects
        """
        interval_str = self.interval_to_granularity(interval)
        candles = []

        # Generate list of files to download
        file_urls = self._generate_vision_urls(
            symbol, start_date, end_date, interval_str
        )

        # Download and process files concurrently
        tasks = [self._download_and_parse_vision_file(url, symbol) for url in file_urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Combine results
        for result in results:
            if isinstance(result, Exception):
                if self.logger:
                    self.logger.debug("Failed to fetch Vision file: %s", result)
                continue
            if result:
                candles.extend(result)

        # Filter candles to exact date range
        candles = [
            c
            for c in candles
            if start_date.timestamp() * 1000
            <= c.timestamp
            <= end_date.timestamp() * 1000
        ]

        # Sort by timestamp
        candles.sort(key=lambda x: x.timestamp)

        if self.logger:
            self.logger.info(
                "Fetched %s candles from Binance Vision for %s", len(candles), symbol
            )

        return candles

    def _generate_vision_urls(
        self, symbol: str, start_date: datetime, end_date: datetime, interval_str: str
    ) -> List[str]:
        """
        Generate list of Binance Vision URLs to download.

        Args:
            symbol: Trading pair symbol
            start_date: Start date
            end_date: End date
            interval_str: Interval string (e.g., "1m", "1h")

        Returns:
            List of URLs to download
        """
        urls = []
        current_date = start_date.replace(day=1)  # Start from beginning of month

        # Determine if we should use daily or monthly files
        time_range_days = (end_date - start_date).days
        use_daily = time_range_days <= 31

        if use_daily:
            # Use daily files
            current_date = start_date
            while current_date <= end_date:
                date_str = current_date.strftime("%Y-%m-%d")
                url = (
                    f"{self.vision_base_url}/{self.vision_data_path}/daily/klines/"
                    f"{symbol}/{interval_str}/{symbol}-{interval_str}-{date_str}.zip"
                )
                urls.append(url)
                current_date += timedelta(days=1)
        else:
            # Use monthly files
            while current_date <= end_date:
                date_str = current_date.strftime("%Y-%m")
                url = (
                    f"{self.vision_base_url}/{self.vision_data_path}/monthly/klines/"
                    f"{symbol}/{interval_str}/{symbol}-{interval_str}-{date_str}.zip"
                )
                urls.append(url)
                # Move to next month
                if current_date.month == 12:
                    current_date = current_date.replace(
                        year=current_date.year + 1, month=1
                    )
                else:
                    current_date = current_date.replace(month=current_date.month + 1)

        return urls

    async def _download_and_parse_vision_file(
        self, url: str, symbol: str
    ) -> List[Candle]:
        """
        Download and parse a Binance Vision ZIP file.

        Args:
            url: URL to download
            symbol: Trading pair symbol

        Returns:
            List of Candle objects
        """
        try:
            async with self.session.get(url) as response:
                if response.status != 200:
                    return []

                # Download ZIP file
                zip_data = await response.read()

                # Extract and parse CSV
                with zipfile.ZipFile(io.BytesIO(zip_data)) as zip_file:
                    # Get the CSV filename (should be only one file in the ZIP)
                    csv_filename = zip_file.namelist()[0]
                    csv_data = zip_file.read(csv_filename).decode("utf-8")

                    # Parse CSV
                    return self._parse_vision_csv(csv_data, symbol)

        except Exception as e:
            if self.logger:
                self.logger.debug("Error downloading Vision file %s: %s", url, e)
            return []

    def _parse_vision_csv(self, csv_data: str, symbol: str) -> List[Candle]:
        """
        Parse Binance Vision CSV data into Candle objects.

        CSV format:
        [0] Open time
        [1] Open
        [2] High
        [3] Low
        [4] Close
        [5] Volume
        [6] Close time
        [7] Quote asset volume
        [8] Number of trades
        [9] Taker buy base asset volume
        [10] Taker buy quote asset volume
        [11] Ignore

        Args:
            csv_data: CSV data as string
            symbol: Trading pair symbol

        Returns:
            List of Candle objects
        """
        candles = []
        csv_reader = csv.reader(io.StringIO(csv_data))

        for row in csv_reader:
            try:
                candle = Candle(
                    s=symbol,
                    ts=int(row[0]),
                    o=float(row[1]),
                    h=float(row[2]),
                    l=float(row[3]),
                    c=float(row[4]),
                    v=float(row[5]),
                    tc=int(row[8]) if len(row) > 8 else 0,
                )
                candles.append(candle)
            except (ValueError, IndexError) as e:
                if self.logger:
                    self.logger.debug("Error parsing CSV row: %s", e)
                continue

        return candles

    def _create_url_list(
        self, symbol: str, start_date: datetime, end_date: datetime, interval: Interval
    ) -> List[str]:
        """
        Create list of URLs for paginated requests.

        Args:
            symbol: Trading pair symbol
            start_date: Start date
            end_date: End date
            interval: Candle interval

        Returns:
            List of URLs
        """
        url_list = []
        interval_str = self.interval_to_granularity(interval)
        max_limit = self.get_max_candle_limit()

        start_ts = int(start_date.timestamp() * 1000)
        end_ts = int(end_date.timestamp() * 1000)

        url = (
            f"{self.api_url}{self.api_endpoints['klines']}"
            f"?symbol={symbol}&interval={interval_str}"
            f"&startTime={start_ts}&endTime={end_ts}&limit={max_limit}"
        )
        url_list.append(url)

        return url_list

    async def _fetch_page(self, url: str, symbol: str) -> List[Candle]:
        """
        Fetch a single page of candle data.

        Args:
            url: API endpoint URL
            symbol: Trading pair symbol

        Returns:
            List of Candle objects
        """
        try:
            async with self.session.get(url) as response:
                if response.status != 200:
                    return []

                data = await response.json()
                candles = []

                for item in data:
                    candle = Candle(
                        s=symbol,
                        ts=int(item[0]),
                        o=float(item[1]),
                        h=float(item[2]),
                        l=float(item[3]),
                        c=float(item[4]),
                        v=float(item[5]),
                        tc=int(item[8]) if len(item) > 8 else 0,
                    )
                    candles.append(candle)

                return candles

        except Exception:
            return []

    async def get_exchange_info(self) -> ExchangeInfo:
        """
        Get general exchange information.

        Returns:
            ExchangeInfo object
        """
        return ExchangeInfo(
            name=self.exchange_name,
            first_data_datetime=self.first_data_date,
            exchange_type=self.exchange_type,
        )

    async def get_symbol_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific symbol.

        Args:
            symbol: Trading pair symbol

        Returns:
            Symbol information dictionary or None
        """
        if not self.session:
            raise RuntimeError("Exchange not initialized. Call initialize() first.")

        try:
            url = f"{self.api_url}{self.api_endpoints['exchange_info']}"

            async with self.session.get(url) as response:
                if response.status != 200:
                    return None

                data = await response.json()
                symbols = data.get("symbols", [])

                for symbol_info in symbols:
                    if symbol_info.get("symbol") == symbol:
                        return symbol_info

                return None

        except Exception as e:
            if self.logger:
                self.logger.error("Failed to get symbol info for %s: %s", symbol, e)
            return None

    async def close(self) -> None:
        """Close the exchange connection and cleanup."""
        try:
            if self.session:
                await self.session.close()
                self.session = None

            await super().close()

        except Exception as e:
            if self.logger:
                self.logger.error("Error closing Binance exchange: %s", e)

    def interval_to_granularity(self, interval: Interval) -> str:
        """
        Convert interval to Binance format.

        Args:
            interval: Internal interval enum

        Returns:
            Binance interval string
        """
        interval_map = {
            Interval.ONE_MINUTE: "1m",
            Interval.FIVE_MINUTES: "5m",
            Interval.FIFTEEN_MINUTES: "15m",
            Interval.ONE_HOUR: "1h",
            Interval.FOUR_HOURS: "4h",
            Interval.ONE_DAY: "1d",
        }
        return interval_map.get(interval, "1m")

    def get_max_candle_limit(self) -> int:
        """Get maximum candle limit per request."""
        return 1000

    def convert_datetime_to_exchange_timestamp(self, dt: datetime) -> str:
        """Convert datetime to Binance timestamp format."""
        return str(int(dt.timestamp() * 1000))

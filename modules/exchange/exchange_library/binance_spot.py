import asyncio
import datetime
from typing import Callable, List, Optional

import aiohttp
from data_provider.exchange_collection.exchange import Exchange

from models.data_models.candle import Candle
from models.exchange_info import ExchangeInfo
from models.exchange_type import ExchangeType
from models.sorting_option import SortBy, SortingOption
from models.time_models import Interval


class Binance(Exchange):
    """
    Binance is a cryptocurrency exchange.
    """
    
    def __init__(self):
        self.name: str = "Binance"
        self.exchange_type: ExchangeType = ExchangeType.SPOT
        self.websocket_url: str = "wss://stream.binance.com:9443/ws"
        self.api_url: str = "https://api.binance.com/api/v3"
        self.api_endpoints: dict = {
            "fetch_product_list": "/exchangeInfo",
            "fetch_candle": "/klines?symbol={}&interval={}&startTime={}&endTime={}&limit={}"
        }
        self.first_data_date = datetime.datetime(2022, 8, 14, 0, 0, 0, 0)
        self.__development_mode__ = False
        self.__candle_callback__: Optional[Callable] = None
        self.__session__: Optional[aiohttp.ClientSession] = None
        self.__websocket__: Optional[object] = None
    
    async def fetch_product_list(self, sorting_option: SortingOption = None, limit: int = -1) -> List[str]:
        """Fetch product list asynchronously."""
        assert "fetch_product_list" in self.api_endpoints, "`fetch_product_list` endpoint not defined"
        
        if self.__development_mode__:
            return ["BTCUSDT"]
        
        if not self.__session__:
            self.__session__ = aiohttp.ClientSession()
        
        url = self.api_url + self.api_endpoints["fetch_product_list"]
        
        try:
            async with self.__session__.get(url) as response:
                if response.status != 200:
                    raise Exception("Error while fetching product list")
                
                data = await response.json()
                
                if sorting_option is not None:
                    data = self.__apply_sorting_options__(data, sorting_option)
                
                if limit > 0:
                    data = data[:limit]
                
                return [product["symbol"] for product in data]
                
        except Exception as e:
            raise Exception(f"Failed to fetch product list: {e}")
    
    @staticmethod
    def __apply_sorting_options__(data: list, sorting_option: SortingOption):
        """Apply sorting options to the data."""
        is_reverse = sorting_option.sort_order.value
        match sorting_option.sort_by:
            case SortBy.VOLUME:
                data.sort(key=lambda x: float(x["quoteVolume"]), reverse=is_reverse)
            case SortBy.PRICE:
                data.sort(key=lambda x: float(x["price"]), reverse=is_reverse)
            case SortBy.SYMBOL:
                data.sort(key=lambda x: x["symbol"], reverse=is_reverse)
            case _:
                pass
        return data
    
    async def fetch_ohlcv(self, symbol: str, start_date: datetime.datetime, end_date: datetime.datetime, interval: Interval) -> List[Candle]:
        """Fetch OHLCV data asynchronously."""
        assert "fetch_candle" in self.api_endpoints, "fetch_candle endpoint not defined"
        assert self.api_url is not None, "api_url not defined"
        
        if not self.__session__:
            self.__session__ = aiohttp.ClientSession()
        
        url_list = self.__create_url_list__(start_date, end_date, interval, symbol)
        
        # Create tasks for concurrent requests
        tasks = [self.__make_request_async__(url, symbol) for url in url_list]
        
        # Execute all requests concurrently
        response_list = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        result = []
        for response in response_list:
            if isinstance(response, Exception):
                continue
            if response is not None:
                result.extend(response)
        
        return result
    
    async def __make_request_async__(self, url: str, symbol: str):
        """Make an async HTTP request."""
        try:
            async with self.__session__.get(url) as response:
                if response.status != 200:
                    return None
                
                json_data = await response.json()
                
                candles = []
                for item in json_data:
                    candle = Candle(
                        symbol=symbol,
                        timestamp=int(item[0]),  # Already in milliseconds
                        open=float(item[1]),
                        high=float(item[2]),
                        low=float(item[3]),
                        close=float(item[4]),
                        volume=float(item[5]),
                        trade_count=int(item[8]) if len(item) > 8 else 0
                    )
                    candles.append(candle)
                
                return candles
                
        except Exception:
            return None
    
    def __create_url_list__(self,
                           startDate: datetime.datetime,
                           endDate: datetime.datetime,
                           interval: Interval,
                           symbol: str):
        """Create a list of URLs for fetching candle data."""
        url_list = []
        current_date = startDate
        granularity = self.interval_to_granularity(interval)
        max_limit = self.get_max_candle_limit()
        
        while current_date < endDate:
            end_time = min(current_date + datetime.timedelta(hours=1), endDate)
            start_timestamp = self.convert_datetime_to_exchange_timestamp(current_date)
            end_timestamp = self.convert_datetime_to_exchange_timestamp(end_time)
            
            url = self.api_url + self.api_endpoints["fetch_candle"].format(
                symbol, granularity, start_timestamp, end_timestamp, max_limit
            )
            url_list.append(url)
            current_date = end_time
        
        return url_list
    
    async def subscribe_to_websocket(self, symbols: List[str], interval: Interval) -> None:
        """Subscribe to websocket for real-time data."""
        try:
            # Create websocket connection
            self.__websocket__ = await self.__create_websocket_connection__(symbols, interval)
        except Exception as e:
            raise Exception(f"Failed to subscribe to websocket: {e}")
    
    async def __create_websocket_connection__(self, symbols: List[str], interval: Interval):
        """Create websocket connection."""
        # This is a placeholder - implement actual websocket connection
        # using aiohttp or websockets library
        pass
    
    async def unsubscribe_from_websocket(self, symbol: str, interval: Interval) -> None:
        """Unsubscribe from websocket."""
        if self.__websocket__:
            # Close websocket connection
            pass
    
    def register_candle_callback(self, callback: Callable) -> None:
        """Register callback for candle data updates."""
        self.__candle_callback__ = callback
    
    def get_exchange_name(self) -> str:
        """Get exchange name."""
        return self.name
    
    def get_exchange_info(self) -> ExchangeInfo:
        """Get exchange information."""
        return ExchangeInfo(
            name=self.name,
            exchange_type=self.exchange_type,
            websocket_url=self.websocket_url,
            api_url=self.api_url
        )
    
    async def close(self) -> None:
        """Close the exchange connection gracefully."""
        if self.__session__:
            await self.__session__.close()
        
        if self.__websocket__:
            # Close websocket connection
            pass
    
    def interval_to_granularity(self, interval: Interval) -> str:
        """Convert interval to Binance granularity format."""
        interval_map = {
            Interval.ONE_MINUTE: "1m",
            Interval.FIVE_MINUTES: "5m",
            Interval.FIFTEEN_MINUTES: "15m",
            Interval.ONE_HOUR: "1h",
            Interval.FOUR_HOURS: "4h",
            Interval.ONE_DAY: "1d"
        }
        return interval_map.get(interval, "1m")
    
    def get_max_candle_limit(self) -> int:
        """Get maximum candle limit per request."""
        return 1000
    
    def convert_datetime_to_exchange_timestamp(self, dt: datetime.datetime) -> str:
        """Convert datetime to exchange timestamp format."""
        return str(int(dt.timestamp() * 1000))

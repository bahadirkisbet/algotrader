import json
from datetime import datetime
from typing import Any, Dict, Optional


class Candle:
    """
    A class to represent a candlestick with validation and error handling.
    """

    def __init__(
        self,
        symbol: str,
        timestamp: int,
        open: float,
        high: float,
        low: float,
        close: float,
        volume: float,
        trade_count: Optional[int] = None,
    ):
        """
        Initialize a new Candle instance with validation.

        Args:
            symbol: Trading symbol (e.g., "BTCUSDT")
            timestamp: Unix timestamp in milliseconds
            open: Opening price
            high: Highest price during the period
            low: Lowest price during the period
            close: Closing price
            volume: Trading volume
            trade_count: Number of trades during the period
        """
        self._validate_inputs(symbol, timestamp, open, high, low, close, volume, trade_count)

        self.symbol = symbol
        self.timestamp = timestamp
        self.open = float(open)
        self.high = float(high)
        self.low = float(low)
        self.close = float(close)
        self.volume = float(volume)
        self.trade_count = int(trade_count) if trade_count is not None else None

    def _validate_inputs(
        self,
        symbol: str,
        timestamp: int,
        open: float,
        high: float,
        low: float,
        close: float,
        volume: float,
        trade_count: int,
    ) -> None:
        """Validate input parameters for data integrity."""
        if not symbol or not isinstance(symbol, str):
            raise ValueError("Symbol must be a non-empty string")

        if not isinstance(timestamp, (int, float)) or timestamp <= 0:
            raise ValueError("Timestamp must be a positive number")

        if not isinstance(open, (int, float)) or open < 0:
            raise ValueError("Open price must be a non-negative number")

        if not isinstance(high, (int, float)) or high < 0:
            raise ValueError("High price must be a non-negative number")

        if not isinstance(low, (int, float)) or low < 0:
            raise ValueError("Low price must be a non-negative number")

        if not isinstance(close, (int, float)) or close < 0:
            raise ValueError("Close price must be a non-negative number")

        if not isinstance(volume, (int, float)) or volume < 0:
            raise ValueError("Volume must be a non-negative number")

        if not isinstance(trade_count, (int, float)) or trade_count < 0:
            raise ValueError("Trade count must be a non-negative number")

        # Validate price relationships
        if high < max(open, close):
            raise ValueError("High price must be greater than or equal to open and close prices")

        if low > min(open, close):
            raise ValueError("Low price must be less than or equal to open and close prices")

    @classmethod
    def from_json(cls, json_data: Dict[str, Any]) -> "Candle":
        """
        Create a Candle instance from JSON data with validation.

        Args:
            json_data: Dictionary containing candle data

        Returns:
            New Candle instance

        Raises:
            ValueError: If required fields are missing or invalid
        """
        required_fields = [
            "symbol",
            "timestamp",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "trade_count",
        ]

        # Check for required fields
        missing_fields = [field for field in required_fields if field not in json_data]
        if missing_fields:
            raise ValueError(f"Missing required fields: {missing_fields}")

        try:
            return cls(
                symbol=str(json_data["symbol"]),
                timestamp=int(json_data["timestamp"]),
                open=float(json_data["open"]),
                high=float(json_data["high"]),
                low=float(json_data["low"]),
                close=float(json_data["close"]),
                volume=float(json_data["volume"]),
                trade_count=int(json_data["trade_count"]),
            )
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid data type in JSON: {e}")

    @classmethod
    def read_json(cls, json_data: Dict[str, Any]) -> "Candle":
        """Alias for from_json for backward compatibility."""
        return cls.from_json(json_data)

    def to_dict(self) -> Dict[str, Any]:
        """Convert candle to dictionary representation."""
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "trade_count": self.trade_count,
        }

    def get_json(self) -> Dict[str, Any]:
        """Alias for to_dict for backward compatibility."""
        return self.to_dict()

    def to_json_string(self) -> str:
        """Convert candle to JSON string representation."""
        return json.dumps(self.to_dict())

    @property
    def open_price(self) -> float:
        """Get the opening price."""
        return self.open

    @property
    def high_price(self) -> float:
        """Get the highest price during the period."""
        return self.high

    @property
    def low_price(self) -> float:
        """Get the lowest price during the period."""
        return self.low

    @property
    def close_price(self) -> float:
        """Get the closing price."""
        return self.close

    @property
    def datetime(self) -> datetime:
        """Get the datetime representation of the timestamp."""
        return datetime.fromtimestamp(self.timestamp / 1000)

    @property
    def price_change(self) -> float:
        """Get the absolute price change from open to close."""
        return self.close - self.open

    @property
    def price_change_percent(self) -> float:
        """Get the percentage price change from open to close."""
        if self.open == 0:
            return 0.0
        return ((self.close - self.open) / self.open) * 100

    @property
    def body_size(self) -> float:
        """Get the size of the candle body (open to close)."""
        return abs(self.close - self.open)

    @property
    def upper_shadow(self) -> float:
        """Get the size of the upper shadow (high to max of open/close)."""
        return self.high - max(self.open, self.close)

    @property
    def lower_shadow(self) -> float:
        """Get the size of the lower shadow (min of open/close to low)."""
        return min(self.open, self.close) - self.low

    @property
    def total_range(self) -> float:
        """Get the total price range (high to low)."""
        return self.high - self.low

    def is_bullish(self) -> bool:
        """Check if the candle is bullish (close > open)."""
        return self.close > self.open

    def is_bearish(self) -> bool:
        """Check if the candle is bearish (close < open)."""
        return self.close < self.open

    def is_doji(self, threshold: float = 0.001) -> bool:
        """Check if the candle is a doji (very small body)."""
        return self.body_size <= threshold

    def __str__(self) -> str:
        """String representation of the candle."""
        return (
            f"{self.symbol} - {self.datetime.strftime('%Y-%m-%d %H:%M:%S')} - "
            f"O:{self.open:.4f} H:{self.high:.4f} L:{self.low:.4f} "
            f"C:{self.close:.4f} V:{self.volume:.2f} T:{self.trade_count}"
        )

    def __repr__(self) -> str:
        """Detailed string representation for debugging."""
        return (
            f"Candle(symbol='{self.symbol}', timestamp={self.timestamp}, "
            f"open={self.open}, high={self.high}, low={self.low}, "
            f"close={self.close}, volume={self.volume}, trade_count={self.trade_count})"
        )

    def __eq__(self, other: Any) -> bool:
        """Check equality with another candle."""
        if not isinstance(other, Candle):
            return False
        return (
            self.symbol == other.symbol
            and self.timestamp == other.timestamp
            and self.open == other.open
            and self.high == other.high
            and self.low == other.low
            and self.close == other.close
            and self.volume == other.volume
            and self.trade_count == other.trade_count
        )

    def __hash__(self) -> int:
        """Hash based on symbol and timestamp."""
        return hash((self.symbol, self.timestamp))

    @staticmethod
    def get_fields() -> list:
        """Get list of field names."""
        return ["symbol", "timestamp", "open", "high", "low", "close", "volume", "trade_count"]

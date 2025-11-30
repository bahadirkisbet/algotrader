import json
from datetime import datetime
from typing import Any, Dict, Optional


class Candle:
    """
    A class to represent a candlestick with validation and error handling.
    """

    def __init__(
        self,
        s: str,
        ts: int,
        o: float,
        h: float,
        l: float,
        c: float,
        v: float,
        tc: Optional[int] = None,
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
        self._validate_inputs(s, ts, o, h, l, c, v, tc)

        self.s = s
        self.ts = ts
        self.o = o
        self.h = h
        self.l = l
        self.c = c
        self.v = v
        self.tc = tc
        self.iv = {}

    def _validate_inputs(
        self,
        s: str,
        ts: int,
        o: float,
        h: float,
        l: float,
        c: float,
        v: float,
        tc: int,
    ) -> None:
        """Validate input parameters for data integrity."""
        if not s or not isinstance(s, str):
            raise ValueError("Symbol must be a non-empty string")

        if not isinstance(ts, (int, float)) or ts <= 0:
            raise ValueError("Timestamp must be a positive number")

        if not isinstance(open, (int, float)) or open < 0:
            raise ValueError("Open price must be a non-negative number")

        if not isinstance(h, (int, float)) or h < 0:
            raise ValueError("High price must be a non-negative number")

        if not isinstance(l, (int, float)) or l < 0:
            raise ValueError("Low price must be a non-negative number")

        if not isinstance(c, (int, float)) or c < 0:
            raise ValueError("Close price must be a non-negative number")

        if not isinstance(v, (int, float)) or v < 0:
            raise ValueError("Volume must be a non-negative number")

        if not isinstance(tc, (int, float)) or tc < 0:
            raise ValueError("Trade count must be a non-negative number")

        # Validate price relationships
        if h < max(o, c):
            raise ValueError(
                "High price must be greater than or equal to open and close prices"
            )

        if l > min(o, c):
            raise ValueError(
                "Low price must be less than or equal to open and close prices"
            )

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
                s=str(json_data["s"]),
                ts=int(json_data["ts"]),
                o=float(json_data["o"]),
                h=float(json_data["h"]),
                l=float(json_data["l"]),
                c=float(json_data["c"]),
                v=float(json_data["v"]),
                tc=int(json_data["tc"]),
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
            "s": self.s,
            "ts": self.ts,
            "o": self.o,
            "h": self.h,
            "l": self.l,
            "c": self.c,
            "v": self.v,
            "tc": self.tc,
            "iv": self.iv,
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
        return self.o

    @property
    def high_price(self) -> float:
        """Get the highest price during the period."""
        return self.h

    @property
    def low_price(self) -> float:
        """Get the lowest price during the period."""
        return self.l

    @property
    def close_price(self) -> float:
        """Get the closing price."""
        return self.c

    @property
    def datetime(self) -> datetime:
        """Get the datetime representation of the timestamp."""
        return datetime.fromtimestamp(self.ts / 1000)

    @property
    def price_change(self) -> float:
        """Get the absolute price change from open to close."""
        return self.c - self.o

    @property
    def price_change_percent(self) -> float:
        """Get the percentage price change from open to close."""
        if self.o == 0:
            return 0.0
        return ((self.c - self.o) / self.o) * 100

    @property
    def body_size(self) -> float:
        """Get the size of the candle body (open to close)."""
        return abs(self.c - self.o)

    @property
    def upper_shadow(self) -> float:
        """Get the size of the upper shadow (high to max of open/close)."""
        return self.h - max(self.o, self.c)

    @property
    def lower_shadow(self) -> float:
        """Get the size of the lower shadow (min of open/close to low)."""
        return min(self.o, self.c) - self.l

    @property
    def total_range(self) -> float:
        """Get the total price range (high to low)."""
        return self.h - self.l

    def is_bullish(self) -> bool:
        """Check if the candle is bullish (close > open)."""
        return self.c > self.o

    def is_bearish(self) -> bool:
        """Check if the candle is bearish (close < open)."""
        return self.c < self.o

    def is_doji(self, threshold: float = 0.001) -> bool:
        """Check if the candle is a doji (very small body)."""
        return self.body_size <= threshold

    def __str__(self) -> str:
        """String representation of the candle."""
        return (
            f"{self.s} - {self.datetime.strftime('%Y-%m-%d %H:%M:%S')} - "
            f"O:{self.o:.4f} H:{self.h:.4f} L:{self.l:.4f} "
            f"C:{self.c:.4f} V:{self.v:.2f} T:{self.tc}"
        )

    def __repr__(self) -> str:
        """Detailed string representation for debugging."""
        return (
            f"Candle(symbol='{self.s}', timestamp={self.ts}, "
            f"o={self.o}, h={self.h}, l={self.l}, "
            f"c={self.c}, v={self.v}, tc={self.tc})"
        )

    def __eq__(self, other: Any) -> bool:
        """Check equality with another candle."""
        if not isinstance(other, Candle):
            return False
        return (
            self.s == other.s
            and self.ts == other.ts
            and self.o == other.o
            and self.h == other.h
            and self.l == other.l
            and self.c == other.c
            and self.v == other.v
            and self.tc == other.tc
        )

    def __hash__(self) -> int:
        """Hash based on symbol and timestamp."""
        return hash((self.s, self.ts))

    @staticmethod
    def get_fields() -> list:
        """Get list of field names."""
        return ["s", "ts", "o", "h", "l", "c", "v", "tc", "iv"]

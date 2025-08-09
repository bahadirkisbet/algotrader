import pytest
from datetime import datetime
from models.data_models.candle import Candle


class TestCandle:
    """Test cases for the Candle model."""

    def test_candle_creation_valid_data(self):
        """Test creating a candle with valid data."""
        candle = Candle("BTCUSDT", 1610000000000, 50000.0, 51000.0, 49000.0, 50500.0, 100.5, 150)
        
        assert candle.symbol == "BTCUSDT"
        assert candle.timestamp == 1610000000000
        assert candle.open == 50000.0
        assert candle.high == 51000.0
        assert candle.low == 49000.0
        assert candle.close == 50500.0
        assert candle.volume == 100.5
        assert candle.trade_count == 150

    def test_candle_creation_invalid_symbol(self):
        """Test creating a candle with invalid symbol."""
        with pytest.raises(ValueError, match="Symbol must be a non-empty string"):
            Candle("", 1610000000000, 50000.0, 51000.0, 49000.0, 50500.0, 100.5, 150)

    def test_candle_creation_invalid_timestamp(self):
        """Test creating a candle with invalid timestamp."""
        with pytest.raises(ValueError, match="Timestamp must be a positive number"):
            Candle("BTCUSDT", -1000, 50000.0, 51000.0, 49000.0, 50500.0, 100.5, 150)

    def test_candle_creation_invalid_prices(self):
        """Test creating a candle with invalid prices."""
        with pytest.raises(ValueError, match="High price must be greater than or equal to open and close prices"):
            Candle("BTCUSDT", 1610000000000, 50000.0, 49000.0, 49000.0, 50500.0, 100.5, 150)

    def test_candle_from_json_valid(self):
        """Test creating a candle from valid JSON data."""
        json_data = {
            "symbol": "ETHUSDT",
            "timestamp": 1610000000000,
            "open": 3000.0,
            "high": 3100.0,
            "low": 2900.0,
            "close": 3050.0,
            "volume": 50.0,
            "trade_count": 100
        }
        
        candle = Candle.from_json(json_data)
        assert candle.symbol == "ETHUSDT"
        assert candle.close == 3050.0

    def test_candle_from_json_missing_fields(self):
        """Test creating a candle from JSON with missing fields."""
        json_data = {
            "symbol": "ETHUSDT",
            "timestamp": 1610000000000,
            "open": 3000.0,
            "high": 3100.0,
            "low": 2900.0,
            # Missing close, volume, trade_count
        }
        
        with pytest.raises(ValueError, match="Missing required fields"):
            Candle.from_json(json_data)

    def test_candle_properties(self):
        """Test candle calculated properties."""
        candle = Candle("BTCUSDT", 1610000000000, 50000.0, 51000.0, 49000.0, 50500.0, 100.5, 150)
        
        assert candle.price_change == 500.0
        assert candle.price_change_percent == 1.0
        assert candle.body_size == 500.0
        assert candle.upper_shadow == 500.0
        assert candle.lower_shadow == 1000.0
        assert candle.total_range == 2000.0

    def test_candle_patterns(self):
        """Test candle pattern detection."""
        bullish_candle = Candle("BTCUSDT", 1610000000000, 50000.0, 51000.0, 49000.0, 50500.0, 100.5, 150)
        bearish_candle = Candle("BTCUSDT", 1610000000000, 50500.0, 51000.0, 49000.0, 50000.0, 100.5, 150)
        
        assert bullish_candle.is_bullish() is True
        assert bullish_candle.is_bearish() is False
        assert bearish_candle.is_bullish() is False
        assert bearish_candle.is_bearish() is True

    def test_candle_doji_detection(self):
        """Test doji pattern detection."""
        doji_candle = Candle("BTCUSDT", 1610000000000, 50000.0, 50010.0, 49990.0, 50000.0, 100.5, 150)
        normal_candle = Candle("BTCUSDT", 1610000000000, 50000.0, 51000.0, 49000.0, 50500.0, 100.5, 150)
        
        assert doji_candle.is_doji() is True
        assert normal_candle.is_doji() is False

    def test_candle_datetime_property(self):
        """Test datetime property conversion."""
        candle = Candle("BTCUSDT", 1610000000000, 50000.0, 51000.0, 49000.0, 50500.0, 100.5, 150)
        
        expected_datetime = datetime.fromtimestamp(1610000000000 / 1000)
        assert candle.datetime == expected_datetime

    def test_candle_equality(self):
        """Test candle equality comparison."""
        candle1 = Candle("BTCUSDT", 1610000000000, 50000.0, 51000.0, 49000.0, 50500.0, 100.5, 150)
        candle2 = Candle("BTCUSDT", 1610000000000, 50000.0, 51000.0, 49000.0, 50500.0, 100.5, 150)
        candle3 = Candle("ETHUSDT", 1610000000000, 50000.0, 51000.0, 49000.0, 50500.0, 100.5, 150)
        
        assert candle1 == candle2
        assert candle1 != candle3
        assert hash(candle1) == hash(candle2)

    def test_candle_string_representation(self):
        """Test candle string representation."""
        candle = Candle("BTCUSDT", 1610000000000, 50000.0, 51000.0, 49000.0, 50500.0, 100.5, 150)
        
        str_repr = str(candle)
        assert "BTCUSDT" in str_repr
        assert "50000.0000" in str_repr
        assert "51000.0000" in str_repr

    def test_candle_to_dict(self):
        """Test candle to dictionary conversion."""
        candle = Candle("BTCUSDT", 1610000000000, 50000.0, 51000.0, 49000.0, 50500.0, 100.5, 150)
        
        candle_dict = candle.to_dict()
        assert isinstance(candle_dict, dict)
        assert candle_dict["symbol"] == "BTCUSDT"
        assert candle_dict["open"] == 50000.0

    def test_candle_get_fields(self):
        """Test getting field names."""
        fields = Candle.get_fields()
        expected_fields = ["symbol", "timestamp", "open", "high", "low", "close", "volume", "trade_count"]
        
        assert fields == expected_fields
        assert len(fields) == 8 
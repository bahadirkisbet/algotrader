config = {
    "default": {
        "development_mode": True,
        "archive_folder": ".cache",
    },
    "exchange": {
        "exchange_code": "BNB",
        "subscription_type": "CANDLE",
        "max_connection_limit": 100,
        "time_frame": "1h",
        "default_interval": "1h",
        "symbols": ["BTCUSDT", "ETHUSDT"],
    },
    "logging": {
        "enable_console_logging": True,
        "enable_file_logging": True,
        "log_format": "detailed",
        "log_file": "log/app.log",
        "log_level": "info",
        "max_log_size": 10485760,
        "log_backup_count": 5,
    },
    "trading": {
        "engine_type": "BACKTEST",
        "strategy_type": "PARABOLIC_SAR",
        "start_date": "2020-01-01",
        "end_date": "2025-11-16",
        "initial_capital": 10000.0,
        "commission_rate": 0.001,
        "slippage_pct": 0.0,
        "maker_fee": 0.001,
        "taker_fee": 0.001,
        "stop_loss_pct": 0.01,
        "take_profit_pct": 0.02,
    },
    "archive": {
        "archive_folder": ".cache",
        "default_encoding": "utf-8",
    },
    "symbols": [
        {
            "pair": "BTCUSDT",
            "interval": "1h",
            "indicators": [
                {
                    "code": "EMA",
                    "parameters": {"period": 20},
                },
                {
                    "code": "RSI",
                    "parameters": {"period": 14},
                },
            ],
        },
        {
            "pair": "ETHUSDT",
            "interval": "1m",
            "indicators": [
                {
                    "code": "PARABOLIC_SAR",
                    "parameters": {"af": 0.02, "max_af": 0.2},
                },
                {
                    "code": "RSI",
                    "parameters": {"period": 14},
                },
                {
                    "code": "SMA",
                    "parameters": {"period": 50},
                },
            ],
        },
    ],
}

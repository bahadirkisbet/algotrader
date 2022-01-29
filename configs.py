CONFIG = {  # new exchange configs will be added here
    "BNB_spot": {
        "endpoints": {
            "api": "https://api.binance.com",
            "candles": "/api/v3/klines",
            "coins": "/api/v3/exchangeInfo",
            "websocket": "wss://stream.binance.com:9443/ws/",
            "websocket_extra": "%s@kline_%s"
        },
        "fields": ["open_time",  # 0
                   "open",  # 1
                   "high",  # 2
                   "low",  # 3
                   "close",  # 4
                   "volume",  # 5
                   "close_time",  # 6
                   "quote_asset_volume",  # 7
                   "number_of_trades",  # 8
                   "taker_buy_asset_volume",  # 9
                   "taker_buy_quote_volume",  # 10
                   "nothing"],  # 11
        "map": {  # mapping for data fields of the request coming from the exchange
            "o": 1,
            "h": 2,
            "l": 3,
            "c": 4,
            "v": 5,
            "o_ts": 0,
            "c_ts": 6
        },
        "exchange_code": "BNB",
        "intervals": {
            5: "5m",
            15: "15m",
            30: "30m",
            60: "1h",
            240: "4h",
            1440: "1d"
        },
        "first_ts": 1500238800000,
        "request_body": {
            "candle": """ { 'symbol': '%s',
                'interval': '%s',
                'startTime': %d,
                'endTime': %d,
                'limit': 1000
                 }""",
            "subscribe": "{ 'method': 'SUBSCRIBE','params': [ '%s@%s_%s' ],'id': 1}"

        },
        "throttle_ms": 50
    }
}

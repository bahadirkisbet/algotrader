# AlgoTrader

A comprehensive algorithmic trading application built in Python with support for multiple cryptocurrency exchanges, technical indicators, and machine learning models.

## Features

- **Multi-Exchange Support**: Currently supports Binance with extensible architecture for other exchanges
- **Historical Data Management**: Automated data ingestion from Binance Vision API with archiving capabilities
- **Technical Indicators**: SMA, EMA, and extensible framework for additional indicators
- **Backtesting Engine**: Simulation engine for strategy testing
- **Risk Management**: Built-in risk management framework
- **Asynchronous Architecture**: High-performance async/await implementation
- **Data Archiving**: Efficient gzipped JSON storage with ArchiveManager
- **WebSocket Support**: Real-time market data streaming

## Installation

### Prerequisites

- Python 3.10 or higher
- pip package manager

### Quick Start

1. **Clone the repository**

   ```bash
   git clone <repository-url>
   cd algotrader
   ```

2. **Install dependencies**

   ```bash
   # Install core dependencies
   pip install -e .

   # Install development dependencies (optional)
   pip install -e .[dev]
   ```

3. **Configure the application**
   ```bash
   # Copy and edit the configuration file
   cp config.ini.example config.ini
   # Edit config.ini with your settings
   ```

## Usage

### Available Commands

The project uses Taskipy for easy command execution:

```bash
# Development
task dev                    # Run in development mode
task prod                   # Run in production mode

# Data Ingestion
task ingest_binance        # Download and archive Binance historical data

# Testing
task test                  # Run all tests
task test_all             # Run tests with verbose output
task test_candle          # Run candle model tests
task test_ema             # Run EMA indicator tests
task test_sma             # Run SMA indicator tests
task test_simulation      # Run simulation engine tests
task cov                  # Run tests with coverage report

# Code Quality
task lint                 # Run Ruff linter
task fmt                  # Format code with Black and isort
task fmt_check            # Check code formatting
task typecheck            # Run MyPy type checker

# Maintenance
task clean                # Clean Python cache files
task clean_all            # Clean all temporary and cache files
task deps_dev             # Install development dependencies
```

### Data Ingestion Example

Download and archive historical BTCUSDT 5-minute candle data:

```bash
task ingest_binance
```

This will:

1. Download monthly data files from Binance Vision API
2. Process and validate the data
3. Archive the data using the ArchiveManager
4. Clean up temporary files

### Programmatic Usage

```python
from modules.archive.archive_manager import ArchiveManager
from models.data_models.candle import Candle

# Initialize archive manager
archive = ArchiveManager()

# Save candles
await archive.archive_candles("BTCUSDT", candles_list, "5m")

# Retrieve archived data
candles = await archive.get_candles("BTCUSDT", Interval.FIVE_MINUTES)
```

## Project Structure

```
algotrader/
├── algorithmic_trader.py      # Main application entry point
├── startup.py                 # Application startup and service injection
├── config.ini                 # Configuration file
├── pyproject.toml            # Project configuration and dependencies
├── modules/                   # Core application modules
│   ├── archive/              # Data archiving and retrieval
│   ├── config/               # Configuration management
│   ├── exchange/             # Exchange integrations (REST & WebSocket)
│   ├── strategy/             # Simple stateless indicators
│   └── websocket/            # WebSocket management
├── domains/                   # Domain models and business logic
│   ├── market_data/          # Market data models
│   ├── risk_management/      # Risk management framework
│   ├── strategy_engine/      # Advanced strategy implementations
│   └── trading/              # Trading operations and exchanges
├── simulations/               # Backtesting framework (TradingView-style)
│   ├── engine.py             # Main simulation engine
│   ├── portfolio.py          # Portfolio management
│   ├── performance.py        # Performance metrics
│   └── config.py             # Simulation configuration
├── data_center/               # Data management and indicators
│   ├── data_center.py        # Core data center
│   └── jobs/                 # Background jobs
│       └── technical_indicators/  # Stateful real-time indicators
├── models/                    # Data models
│   ├── data_models/          # Core data structures (Candle, etc.)
│   └── time_models.py        # Time and interval models
├── scripts/                   # Utility scripts
│   └── binance_data_ingestor.py  # Bulk historical data download
├── tests/                     # Test suite
└── utils/                     # Utility functions and helpers
```

## Configuration

The application uses `config.ini` for configuration. Key sections include:

- **ARCHIVE**: Archive folder and encoding settings
- **EXCHANGE**: Exchange-specific configurations
- **LOGGING**: Log level and output settings
- **WEBSOCKET**: WebSocket connection settings

## Development

### Code Quality

The project enforces high code quality standards:

- **Black**: Code formatting
- **Ruff**: Fast Python linter
- **MyPy**: Static type checking
- **isort**: Import sorting

### Running Tests

```bash
# Run all tests
task test

# Run specific test categories
task test_candle
task test_ema
task test_simulation

# Run with coverage
task cov
```

### Code Formatting

```bash
# Format code
task fmt

# Check formatting
task fmt_check
```

## System Overview

### Core Components

1. **Exchange Module** (`modules/exchange/`)

   - SOLID-compliant exchange integrations
   - Automatic Binance Vision support for bulk historical data
   - Separate REST and WebSocket implementations
   - Extensible for additional exchanges

2. **Simulation Framework** (`simulations/`)

   - Complete TradingView-style backtesting engine
   - Portfolio management with position tracking
   - 20+ performance metrics (Sharpe, Sortino, Calmar, etc.)
   - Automated report generation with charts
   - Strategy functions for flexible testing

3. **Technical Indicators**

   - **Stateless** (`modules/strategy/technical_indicators.py`): Batch calculation on candle lists
   - **Stateful** (`data_center/jobs/technical_indicators/`): Real-time streaming with state management
   - Implementations: SMA, EMA, Parabolic SAR, RSI, Bollinger Bands

4. **Data Management**
   - Archive manager for compressed historical data storage
   - Data ingestion scripts for bulk downloads
   - Gap detection and backfilling

### TODO

#### Completed ✅

- [x] Exchange module refactoring (SOLID principles)
- [x] Binance Vision integration
- [x] Complete backtesting framework
- [x] Technical indicators (SMA, EMA, Parabolic SAR)
- [x] Performance metrics and reporting
- [x] Code cleanup and consolidation

#### Planned 📋

- [ ] Add more exchange support (Coinbase, Kraken, etc.)
- [ ] Implement ML-based strategies (LSTM, XGBoost, etc.)
- [ ] Real-time trading execution
- [ ] Risk management enhancements
- [ ] Web UI for strategy monitoring
- [ ] REST API for remote access

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and quality checks: `task test && task lint && task fmt_check`
5. Submit a pull request

## License

This project is licensed under the MIT License.

## Disclaimer

This software is for educational and research purposes only. Trading cryptocurrencies involves substantial risk and may result in the loss of your invested capital. You should carefully consider whether trading is suitable for you in light of your financial condition, investment objectives, and risk tolerance.

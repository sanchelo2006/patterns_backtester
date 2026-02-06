MOEX & Crypto Backtest System
This project is fully developed by DeepSeek AI Assistant

📋 Project Overview
The MOEX & Crypto Backtest System is a comprehensive trading strategy backtesting platform specifically designed for testing Japanese candlestick patterns on MOEX (Moscow Exchange) and cryptocurrency markets. The application provides a complete workflow from strategy creation to performance analysis with detailed visualization capabilities.

🎯 Key Features
Multi-Market Support
MOEX (Moscow Exchange): Full support for Russian stock market data

Cryptocurrency Markets: Integration with Bybit exchange via API

Support for both testnet and mainnet environments

Pattern Detection & Analysis
61 Japanese Candlestick Patterns: Full TA-Lib integration

Adjustable Detection Threshold: Fine-tune pattern sensitivity (0-100%)

Pattern Visualization: Interactive diagrams with detailed explanations

Pattern Statistics: Performance analysis per pattern type

Strategy Management
Custom Strategy Creation: Build strategies with multiple patterns

Entry & Exit Rules: Various rule configurations

Risk Management: Position sizing, stop loss, take profit

Database Storage: Save and load strategies from SQLite database

Backtesting Engine
Realistic Simulation: Includes commission and slippage

Performance Metrics: Comprehensive statistics (Sharpe ratio, win rate, max drawdown, etc.)

Capital Tracking: Detailed trade-by-trade capital allocation

Multi-timeframe Support: From 1 minute to monthly charts

Visualization & Reporting
Interactive Plotly Charts: Professional TradingView-style interface

Technical Indicators: MACD, RSI, Volume with toggle options

Trade Markers: Visual entry/exit points on charts

Excel Export: Complete results with multiple sheets

Database Integration: Store and compare historical results

📁 Project Structure
text
patterns_backtester/
├── 📂 database/
│   └── strategies.db          # SQLite database for strategies and results
├── 📂 logs/                   # Application logs (rotated weekly)
├── 📂 results/                # Excel export files
├── 📂 src/
│   ├── 📂 backtest/          # Backtesting engine and metrics
│   ├── 📂 config/            # Configuration and settings
│   ├── 📂 data/              # Data clients (MOEX, Crypto)
│   ├── 📂 gui/               # PyQt5 GUI components
│   ├── 📂 patterns/          # Pattern detection logic
│   ├── 📂 strategies/        # Strategy definitions and rules
│   ├── 📂 utils/             # Logging and utilities
│   └── 📂 visualization/     # Charting and visualization
├── main.py                   # Application entry point
├── requirements.txt          # Python dependencies
└── README.md                # This file
🔧 Installation & Setup
Prerequisites
Python 3.8+

Git

Internet connection (for data fetching)

Step-by-Step Installation
Clone the Repository

bash
git clone <repository-url>
cd patterns_backtester
Create Virtual Environment

bash
python -m venv .venv

# On Windows
.venv\Scripts\activate

# On macOS/Linux
source .venv/bin/activate
Install Dependencies

bash
pip install -r requirements.txt
Environment Configuration
Create a .env file in the root directory:

env
# For Bybit Crypto Trading (optional)
BYBIT_TESTNET=False
BYBIT_API_KEY=your_api_key
BYBIT_API_SECRET=your_api_secret
Run the Application

bash
python main.py
📊 Supported Candlestick Patterns
Note: Pattern descriptions are currently under development. Basic information is available, but detailed descriptions and reliability ratings are being refined.

The system supports all 61 TA-Lib candlestick patterns:

Single Candle Patterns
CDLDOJI - Indecision pattern

CDLHAMMER - Bullish reversal

CDLHANGINGMAN - Bearish reversal

CDLSHOOTINGSTAR - Bearish reversal

CDLINVERTEDHAMMER - Bullish reversal

CDLMARUBOZU - Strong momentum

CDLSPINNINGTOP - Indecision

Two Candle Patterns
CDLENGULFING - Strong reversal

CDLHARAMI - Potential reversal

CDLHARAMICROSS - Stronger harami

CDLPIERCING - Bullish reversal

CDLDARKCLOUDCOVER - Bearish reversal

Three Candle Patterns
CDLMORNINGSTAR - Bullish reversal

CDLEVENINGSTAR - Bearish reversal

CDL3WHITESOLDIERS - Strong bullish

CDL3BLACKCROWS - Strong bearish

CDLIDENTICAL3CROWS - Very bearish

Complex Patterns
CDLABANDONEDBABY - Rare but reliable reversal

CDLKICKING - Gap-based reversal

CDLMATCHINGLOW - Bullish support

CDLRISEFALL3METHODS - Continuation pattern

CDLTRISTAR - Extreme indecision

Full pattern list available in the Help section of the application.

🎮 User Guide
1. Creating a Strategy
Click "New" in Strategy Management

Enter a unique strategy name

Select patterns to include (Ctrl+Click for multiple)

Choose entry rule:

OPEN_NEXT_CANDLE - Enter at next candle open

MIDDLE_OF_PATTERN - Enter at pattern midpoint

CLOSE_PATTERN - Enter at pattern close

Select exit rule:

STOP_LOSS_TAKE_PROFIT - Fixed SL/TP levels

TAKE_PROFIT_ONLY - Profit target only

OPPOSITE_PATTERN - Exit on opposite signal

TIMEBASED_EXIT - Exit after N bars

TRAILING_STOP - Dynamic trailing stop

Set risk parameters:

Position Size (% of capital)

Stop Loss (%)

Take Profit (%)

Max Bars to Hold

Click "Save"

2. Fetching Market Data
Select market type (MOEX or Cryptocurrency)

Enter ticker/symbol:

MOEX: SBER, GAZP, LKOH, etc.

Crypto: BTCUSDT, ETHUSDT, XRPUSDT, etc.

Choose timeframe (1m to Monthly)

Set date range

Adjust pattern threshold (default 0.5)

Click "Fetch Data"

3. Running Backtest
Select your strategy from dropdown

Review parameters:

Initial Capital (default: 1,000,000 RUB)

Commission % (default: 0.1%)

Slippage % (default: 0.1%)

Click "Run Backtest"

View results in the right panel

4. Analyzing Results
Performance Metrics
Capital: Initial/Final, Total Return %

Trade Statistics: Total trades, Win Rate, Profit Factor

Risk Metrics: Sharpe Ratio, Max Drawdown, Avg Trade Duration

Pattern Performance: Win rate by pattern type

Visualization Options
Click "Show Chart" for interactive visualization

Select indicators to display (Volume, MACD, RSI)

Use Plotly controls to:

Zoom in/out

Pan across time

Hover for detailed values

Compare price levels

Export Options
Excel Export: Complete results with multiple sheets

Database Save: Store results for historical comparison

CSV Export: From database viewer

5. Database Management
Access via "View Database" button:

Strategies Tab
View all saved strategies

Edit or delete individual strategies

Export to CSV

Results Tab
View historical backtest results

Compare performance across tests

Delete individual or all results

⚙️ Technical Details
Backtesting Engine
The engine simulates realistic trading conditions:

python
# Core components
engine = BacktestEngine(
    initial_capital=1000000,
    position_size_pct=10,      # % of capital per trade
    commission=0.001,          # 0.1% commission
    slippage=0.001            # 0.1% slippage
)
Key Features:

Position sizing based on available capital

Commission applied on entry and exit

Slippage simulation for realistic fills

Equity curve tracking with drawdown calculation

Comprehensive trade logging

Pattern Detection
python
# Pattern detection with threshold
detector = PatternDetector(threshold=0.5)
df_with_patterns = detector.detect_all_patterns(df)

# Signal generation
signal, pattern_name = detector.get_signal(row, patterns_to_use)
Threshold Explanation:

0.0: Maximum sensitivity (more false signals)

0.5: Default (TA-Lib standard)

1.0: Minimum sensitivity (fewer, stronger signals)

Data Sources
MOEX Client
Uses MOEX ISS API

Supports OHLC data with realistic wick generation

Fallback to close-only data with synthesized OHLC

Board: TQBR, Engine: stock, Market: shares

Crypto Client (Bybit)
PyBit unified trading API

Testnet and mainnet support

Spot market data

Automatic pagination for large date ranges

📈 Performance Metrics Calculated
Return Metrics
Total Return (%)

Average ROI per Trade (%)

Sharpe Ratio (annualized)

Profit Factor (Gross Profit / Gross Loss)

Risk Metrics
Maximum Drawdown (%)

Standard Deviation of P&L

Consecutive Wins/Losses

Average Trade Duration

Trade Statistics
Total Trades

Win Rate (%)

Average Win/Loss

Long/Short Distribution

Pattern-specific Statistics

🔍 Advanced Features
Debug Mode
Enable via "Debug Mode" button

Detailed logging of trade decisions

Capital tracking verification

Pattern detection details

Database Operations
python
# Bulk operations available
db.delete_all_strategies()      # Delete all strategies
db.delete_all_backtest_results() # Delete all results
db.clean_database()             # Complete database reset
Custom Indicators
The visualization system supports:

MACD (12, 26, 9)

RSI (14 period)

Volume with color coding

Custom trade markers for entry/exit points

🐛 Troubleshooting
Common Issues
No Data Fetched

Check internet connection

Verify ticker/symbol is correct

Ensure date range is valid

Check API keys for crypto (if using)

Chart Not Displaying

Verify Plotly installation

Check browser pop-up settings

Ensure sufficient data points

Database Errors

Check file permissions

Verify SQLite installation

Check disk space

Pattern Detection Issues

Adjust threshold slider

Ensure sufficient historical data

Verify TA-Lib installation

Log Files
Application logs are stored in logs/ directory:

app.log - General application logs

error.log - Error details

user.log - User actions

Logs rotate weekly (Monday)

📚 API Reference
MOEX API
Base URL: https://iss.moex.com/iss/

Endpoint: engines/stock/markets/shares/boards/TQBR/securities/{ticker}/candles.json

Parameters: from, till, interval, candles.columns

Bybit API
Category: spot

Endpoint: /v5/market/kline

Parameters: symbol, interval, start, end, limit

🔮 Future Enhancements
Planned Features
Machine Learning Integration

Pattern prediction models

Optimal parameter detection

Risk-adjusted strategy optimization

Additional Markets

Forex pairs

US stocks

Futures contracts

Advanced Analytics

Monte Carlo simulation

Walk-forward analysis

Parameter optimization grid

Real-time Features

Live pattern detection

Paper trading mode

Alert system

Enhanced Visualization

3D pattern visualization

Correlation matrices

Heat maps of pattern performance

Pattern Description Completion
Currently in progress:

Detailed reliability ratings

Historical performance statistics

Market condition effectiveness

Timeframe-specific recommendations

👥 Contributing
While this project is fully developed by DeepSeek, suggestions and feedback are welcome:

Report bugs via issue tracker

Suggest new features

Share pattern performance insights

Provide market-specific optimizations

📄 License
This project is developed by DeepSeek AI Assistant for educational and research purposes. Users are responsible for complying with applicable regulations when using this software for actual trading.

⚠️ Disclaimer
Trading involves substantial risk of loss. This software is for educational and research purposes only. Past performance does not guarantee future results. Always test strategies thoroughly before using real capital. The developers are not responsible for any financial losses incurred through the use of this software.

Last Updated: February 2026
Developed by: DeepSeek AI Assistant
Project Status: Active Development

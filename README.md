# Mid-Cap Portfolio Dashboard - 30-Day Trading Experiment

**Live Dashboard**: [https://deuxfoistrois.github.io/Midcap-Research-30-day-experiment/](https://deuxfoistrois.github.io/Midcap-Research-30-day-experiment/)

A fully automated mid-cap stock trading system with $100,000 baseline investment, focusing on catalyst-driven opportunities with comprehensive risk management.

## Portfolio Strategy

**Investment Approach**: Catalyst-driven mid-cap stock selection with 30-day holding periods
**Baseline Investment**: $100,000
**Maximum Risk**: 8% portfolio loss ($8,000)
**Trailing Stops**: Activate at 5% gains, trail 8% below highs
**Target Return**: 15-20% over 30-day experiment

## Current Holdings

| Symbol | Allocation | Sector | Entry Target | Stop Loss | Catalyst |
|--------|------------|--------|--------------|-----------|----------|
| SNDX | $25,000 | Healthcare | $42.50 | $39.10 | Q3 earnings Oct 30, HIV pipeline updates |
| EPAM | $25,000 | Technology | $195.00 | $179.40 | Q3 earnings Oct 31, digital transformation recovery |
| STRL | $25,000 | Healthcare | $320.00 | $294.40 | FDA liver cancer drug decision Oct 2025 |
| IDCC | $25,000 | Technology | $135.00 | $124.20 | 5G patent renewals, AI chip IP monetization |

## Repository Structure

```
├── config.json                    # Portfolio configuration and stock settings
├── main.py                        # Daily portfolio data management
├── alpaca_sync.py                 # Bidirectional Alpaca synchronization
├── trailing_stops.py              # Trailing stop loss management
├── order_management.py            # Order execution and position management
├── index.html                     # Live portfolio dashboard
├── docs/
│   └── latest.json                # Current portfolio state (updated daily)
├── data/
│   ├── portfolio_history.csv      # Historical performance data
│   └── trailing_stops.json        # Active trailing stop data
├── logs/
│   ├── executions_YYYY_MM.json    # Trade execution logs
│   ├── orders_YYYY_MM.json        # Order placement logs
│   ├── sync_YYYY_MM.json          # Sync operation logs
│   └── trailing_stops_YYYY_MM_DD.txt # Daily stop loss reports
└── .github/workflows/
    └── daily_portfolio.yml        # Automated daily workflow
```

## Core Scripts

### config.json
Portfolio configuration with stock allocations, entry targets, stop losses, catalysts, and risk parameters. All scripts read from this file dynamically.

### main.py
**Purpose**: Daily portfolio data management
- Fetches current market prices from Alpaca API
- Calculates positions based on entry targets and current prices
- Updates portfolio metrics and performance tracking
- Saves data to JSON/CSV for dashboard consumption
- Runs daily via GitHub Actions

### alpaca_sync.py
**Purpose**: Bidirectional synchronization with Alpaca paper account
- Detects intraday stop loss executions
- Projects repo positions to Alpaca paper trading account
- Updates repo when stop losses trigger during trading hours
- Maintains alignment between tracking system and actual trades
- Critical for real-time stop loss detection

### trailing_stops.py
**Purpose**: Advanced stop loss management
- Activates trailing stops when positions gain 5%
- Trails stops 8% below highest prices reached
- Updates stop prices as positions move higher
- Generates daily stop loss status reports
- Coordinates with order_management.py for Alpaca updates

### order_management.py
**Purpose**: Trade execution and order management
- Places initial buy orders for all positions
- Sets and updates stop loss orders on Alpaca
- Handles emergency liquidations if needed
- Manages trailing stop order updates
- Provides order status monitoring

### index.html
**Purpose**: Live portfolio dashboard
- Real-time portfolio performance visualization
- Individual stock performance charts
- Portfolio allocation pie charts
- Risk monitoring and alerts
- Catalyst tracking and technical analysis display

## Automation Workflow

The system runs automatically via GitHub Actions every weekday at 4:30 PM ET:

1. **Alpaca Sync**: Check for intraday stop loss executions
2. **Portfolio Update**: Refresh prices and calculate current performance
3. **Trailing Stops**: Update trailing stop prices based on new highs
4. **Order Management**: Update stop loss orders on Alpaca
5. **Data Persistence**: Commit updated data files to repository

## Risk Management Features

- **Maximum Loss Limit**: 8% of $100,000 baseline ($8,000 maximum loss)
- **Position-Level Stops**: Individual stop losses for each stock
- **Trailing Stop Protection**: Locks in profits after 5% gains
- **Risk Alerts**: Dashboard warnings at 6% portfolio loss
- **Diversification**: Equal allocation across healthcare and technology sectors
- **Catalyst Timing**: 30-day holding periods aligned with earnings/FDA decisions

## Dashboard Features

- **Performance Tracking**: Portfolio vs mid-cap benchmark comparison
- **Individual Analysis**: Per-stock performance and technical setups
- **Risk Monitoring**: Real-time alerts for approaching risk thresholds
- **Catalyst Calendar**: Upcoming earnings dates and FDA decisions
- **Trade History**: Complete log of all executions and stops
- **Mobile Responsive**: Optimized for desktop and mobile viewing

## Setup Instructions

1. **Repository Secrets**: Add Alpaca API credentials to GitHub secrets
2. **GitHub Pages**: Enable Pages deployment from main branch
3. **Workflow Permissions**: Enable "Read and write permissions" in Actions settings
4. **Initial Orders**: Manually trigger workflow to place first trades
5. **Monitoring**: Dashboard updates automatically after each workflow run

## Performance Metrics

- **Total Return**: Current portfolio performance vs $100,000 baseline
- **Individual P&L**: Per-stock profit/loss tracking
- **Risk Utilization**: Current portfolio risk vs 8% maximum
- **Stop Loss Activity**: Active trailing stops and trigger levels
- **Benchmark Comparison**: Performance vs MDY, IJH, VO mid-cap ETFs

## Data Sources

- **Market Data**: Alpaca Markets API (real-time quotes and bars)
- **Trade Execution**: Alpaca Paper Trading Account
- **Dashboard Updates**: Real-time data from GitHub-hosted JSON files
- **Historical Tracking**: CSV-based portfolio history with daily snapshots

## Disclaimer

This is a paper trading experiment for educational and research purposes. All trades are executed in Alpaca's paper trading environment with virtual money. Past performance does not guarantee future results. The 30-day experiment focuses on mid-cap catalyst opportunities with defined risk parameters.

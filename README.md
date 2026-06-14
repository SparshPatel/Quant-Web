# Kappa-Quant
Access the Webpage at https://quant-web-1ur9.onrender.com/


A full-stack quantitative finance analytics platform built with Django. Provides 25+ interactive tools for portfolio optimization, risk management, derivatives pricing, and market analysis — powered by real-time data from Yahoo Finance.

---

## Features

### Portfolio & Optimization
- **CVaR Optimization** — Conditional Value-at-Risk portfolio construction
- **Efficient Frontier** — Mean-variance optimization with interactive Plotly charts
- **Portfolio Rebalancing** — Target allocation drift monitoring and rebalance signals
- **Portfolio Attribution** — Brinson-style performance attribution
- **Factor Exposure** — Multi-factor risk decomposition (Fama-French)
- **Monte Carlo Simulation** — Forward-looking portfolio return distributions

### Risk & Volatility
- **Risk Dashboard** — VaR, CVaR, drawdown, Sharpe, Sortino at a glance
- **Stress Testing** — Historical and hypothetical scenario analysis
- **Volatility Surface** — 3D implied volatility surface construction
- **Correlation Matrix** — Dynamic correlation heatmaps

### Trading & Strategies
- **Pairs Trading** — Cointegration-based statistical arbitrage
- **Market Regime Detection** — HMM-based regime clustering (bull/bear/sideways)
- **Backtesting Engine** — Strategy backtesting with performance metrics
- **Options Strategy Builder** — Payoff diagrams for multi-leg option strategies
- **Sector Rotation** — Momentum-based sector allocation signals
- **Technical Indicators** — RSI, MACD, Bollinger Bands, and more

### Fundamentals & Macro
- **DCF Valuation** — Discounted cash flow intrinsic value calculator
- **Earnings Calendar** — Upcoming earnings with surprise history
- **Dividend Tracker** — Yield, payout ratio, and ex-date monitoring
- **Global Macro Dashboard** — GDP, inflation, rates across economies
- **Yield Curve Analysis** — Term structure visualization and inversion signals
- **Currency Exposure** — FX risk analysis for international portfolios
- **Cross-Border Analytics** — ADR/GDR premium and geographic diversification

### Other Tools
- **Sentiment Analysis** — News-based market sentiment scoring
- **Stock Screener** — Multi-factor screening with custom filters
- **Watchlist** — Personalized asset tracking
- **PDF Report Generation** — Export analysis to downloadable reports
- **Save & Rerun** — Persist analysis parameters and re-execute later

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Django 5.x, Gunicorn |
| Data | yfinance, pandas, NumPy |
| Optimization | CVXPY, SciPy |
| ML/Stats | scikit-learn, hmmlearn, statsmodels |
| Visualization | Plotly, Matplotlib |
| Frontend | Bootstrap 5, Plotly.js |
| Database | SQLite (dev) / PostgreSQL (prod) |
| Static Files | WhiteNoise |
| Deployment | Render (Docker-ready) |

---

## Local Setup

```bash
# Clone
git clone https://github.com/SparshPatel/Quant-Web.git
cd Quant-Web/quant-web

# Virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run migrations & start server
python manage.py migrate
python manage.py runserver

# Statistical Mean-Reversion — Pairs Trading

## Overview

A pairs trading strategy that finds two cointegrated stocks, monitors the spread between them, and trades when it deviates significantly from its historical mean. I use Coca-Cola (KO) and PepsiCo (PEP) as the pair.

## The Idea

KO and PEP are in the same industry and tend to move together over time. When their price spread gets stretched — one moves too far relative to the other — there's a statistical tendency for it to snap back. This strategy tries to capture that mean-reversion.

## Approach

1. Fetched daily prices for KO and PEP (2015–2024) using `yfinance`
2. Ran the Engle-Granger cointegration test using `statsmodels`
3. Estimated the hedge ratio via OLS regression
4. Computed a 60-day rolling z-score of the spread
5. Entry signal: z-score crosses ±2.0 — exit when it crosses back to 0
6. Backtested the strategy and computed Sharpe ratio, max drawdown, etc.

## Strategy Rules

| Signal | Condition | Action |
|--------|-----------|--------|
| Long spread | z-score < -2.0 | Buy PEP, short KO |
| Short spread | z-score > +2.0 | Short PEP, buy KO |
| Exit | z-score crosses 0 | Close position |

## Key Concepts

- **Cointegration**: Two time series are cointegrated if a linear combination of them is stationary. This is stronger than correlation — it means they share a long-run equilibrium.
- **Hedge Ratio**: The number of shares of stock A to short for every share of stock B, estimated via OLS regression.
- **Z-Score**: How many standard deviations the spread is from its rolling mean. Used to generate entry and exit signals.

## Dependencies

- yfinance
- statsmodels
- numpy
- pandas
- matplotlib

## How to Run

```bash
pip install yfinance statsmodels numpy pandas matplotlib
jupyter notebook pairs_trading.ipynb
```

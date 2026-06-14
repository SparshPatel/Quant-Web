# Market Regime Clustering

## Overview

This project uses a Hidden Markov Model (HMM) to detect different market regimes from S&P 500 (SPY) historical data. The model learns to identify bull, bear, and sideways environments on its own by analyzing patterns in rolling returns and volatility.

## Why This Matters

Financial markets don't behave the same way all the time. A strategy that works in a calm uptrend might blow up during a volatile crash. Being able to detect what regime the market is in helps with risk management and strategy selection.

## Approach

1. Pulled ~17 years of daily SPY data (2007–2024) using `yfinance`
2. Engineered two features: 21-day rolling return and 21-day rolling volatility
3. Fit a 3-state Gaussian HMM using `hmmlearn`
4. Each trading day gets labeled as one of three regimes
5. Plotted the price chart color-coded by regime

## What the Model Finds

The three regimes generally correspond to:
- **Low-vol bull markets** — steady uptrends with low volatility
- **High-vol bear markets** — sharp selloffs like 2008, 2020
- **Transitional/sideways periods** — choppy, uncertain markets

The model isn't perfect — there's some noise in the transitions — but it does a solid job at flagging the major regime shifts.

## Dependencies

- yfinance
- hmmlearn
- numpy
- pandas
- matplotlib

## How to Run

```bash
pip install yfinance hmmlearn numpy pandas matplotlib
jupyter notebook market_regime_clustering.ipynb
```

# Implied Volatility Surface Builder

## Overview

This project builds an implied volatility surface from live AAPL options data. For every available option contract, I back out the implied volatility using Black-Scholes inversion and plot the result as a 3D surface across strike prices and expiry dates.

## Why This Matters

The volatility surface is one of the most important tools in options trading. It tells you how the market prices risk across different moneyness levels and time horizons. The shape of the surface — skew, smile, term structure — carries a lot of information about market sentiment and tail risk expectations.

## Approach

1. Fetched AAPL options chains across multiple expiry dates using `yfinance`
2. Defined Black-Scholes pricing and used `scipy.optimize.brentq` (Brent's method) to solve for implied vol
3. Filtered out illiquid contracts with zero bids and extreme strikes
4. Built an interactive 3D volatility surface using `plotly`
5. Also plotted a 2D volatility smile for a single expiry using `matplotlib`

## Key Observations

- OTM puts typically have higher implied vol than OTM calls — this is the "skew" and reflects the market's crash risk premium
- Near-term options tend to have steeper skew than longer-dated ones
- The surface shape changes over time as market conditions shift

## Dependencies

- yfinance
- scipy
- numpy
- pandas
- plotly
- matplotlib

## How to Run

```bash
pip install yfinance scipy numpy pandas plotly matplotlib
jupyter notebook volatility_surface.ipynb
```

**Note:** This pulls live options data, so the surface will look different each time you run it depending on current market conditions.

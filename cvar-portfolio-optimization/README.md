# CVaR Portfolio Optimization

## Overview

This project optimizes a portfolio by minimizing Conditional Value-at-Risk (CVaR) instead of variance. CVaR — also called Expected Shortfall — measures the expected loss in the worst x% of scenarios. It's what risk managers actually care about, and it's a step beyond the standard Markowitz mean-variance framework.

## Why Not Just Use Markowitz?

Mean-variance optimization treats a +5% day and a -5% day as equally risky (both increase variance). In reality, investors care a lot more about the downside. CVaR focuses specifically on tail losses, producing portfolios that are more robust during drawdowns.

## Approach

1. Downloaded daily returns for 8 stocks (AAPL, MSFT, GOOGL, AMZN, JPM, JNJ, XOM, PG) from 2018–2024
2. Formulated the CVaR minimization problem using the Rockafellar-Uryasev linear programming method
3. Solved for optimal weights using `cvxpy`
4. Compared performance against an equal-weight benchmark
5. Computed risk metrics: annualized return, volatility, Sharpe ratio, VaR, and CVaR for both portfolios

## The Math

CVaR at confidence level α is:

```
CVaR_α = min over γ { γ + (1/αN) × Σ max(0, -rᵢᵀw - γ) }
```

where `rᵢ` are historical return vectors, `w` are portfolio weights, and `γ` is the VaR threshold. The `max(0, ...)` terms are linearized with auxiliary variables, making this a standard LP that solvers handle easily.

## What to Expect

The CVaR-optimized portfolio tends to concentrate weight in lower-volatility, defensive stocks. This makes sense — CVaR penalizes tail risk heavily, so it avoids assets with fat left tails. The tradeoff is that it may lag in strong bull markets where high-beta names rally hard.

## Dependencies

- yfinance
- cvxpy
- numpy
- pandas
- matplotlib

## How to Run

```bash
pip install yfinance cvxpy numpy pandas matplotlib
jupyter notebook cvar_optimization.ipynb
```

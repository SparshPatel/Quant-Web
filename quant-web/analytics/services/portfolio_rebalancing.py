import re
import numpy as np
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def validate_ticker(ticker):
    return bool(re.match(r'^[\^]?[A-Z0-9.\-=]{1,20}$', ticker.upper()))


def rebalance_portfolio(tickers, current_weights, target_weights,
                        portfolio_value=100000, tx_cost_bps=10):
    """
    Compare current vs target weights, compute required trades, and
    estimate transaction costs.

    Parameters
    ----------
    tickers : list[str]
    current_weights : list[float]  – must sum to ~1
    target_weights : list[float]   – must sum to ~1
    portfolio_value : float
    tx_cost_bps : float – one-way transaction cost in basis points

    Returns dict with charts + trade list.
    """
    for t in tickers:
        if not validate_ticker(t):
            raise ValueError(f"Invalid ticker: {t}")
    n = len(tickers)
    if len(current_weights) != n or len(target_weights) != n:
        raise ValueError("Number of weights must match number of tickers.")

    cw = np.array(current_weights, dtype=float)
    tw = np.array(target_weights, dtype=float)

    # Normalise
    if abs(cw.sum() - 1.0) > 0.05:
        raise ValueError("Current weights must sum to approximately 1.")
    if abs(tw.sum() - 1.0) > 0.05:
        raise ValueError("Target weights must sum to approximately 1.")
    cw = cw / cw.sum()
    tw = tw / tw.sum()

    diff = tw - cw
    trade_values = diff * portfolio_value
    total_turnover = np.abs(trade_values).sum()
    tx_cost = total_turnover * (tx_cost_bps / 10_000)

    # Fetch latest prices to compute share counts
    data = yf.download(tickers, period='5d')['Close']
    if isinstance(data, pd.Series):
        data = data.to_frame(tickers[0])
    latest_prices = data.iloc[-1]

    trades = []
    for i, t in enumerate(tickers):
        price = float(latest_prices[t]) if t in latest_prices.index else float(latest_prices.iloc[i])
        shares = trade_values[i] / price if price > 0 else 0
        trades.append({
            'ticker': t,
            'current_pct': f"{cw[i]*100:.1f}%",
            'target_pct': f"{tw[i]*100:.1f}%",
            'diff_pct': f"{diff[i]*100:+.1f}%",
            'trade_value': f"${trade_values[i]:+,.0f}",
            'shares': f"{shares:+.1f}",
            'action': 'BUY' if trade_values[i] > 0 else ('SELL' if trade_values[i] < 0 else 'HOLD'),
        })

    # ---------- Charts ----------
    fig = make_subplots(rows=1, cols=2,
                        subplot_titles=['Current Allocation', 'Target Allocation'],
                        specs=[[{'type': 'pie'}, {'type': 'pie'}]])
    fig.add_trace(go.Pie(labels=tickers, values=cw, hole=0.4,
                         textinfo='label+percent'), row=1, col=1)
    fig.add_trace(go.Pie(labels=tickers, values=tw, hole=0.4,
                         textinfo='label+percent'), row=1, col=2)
    fig.update_layout(template='plotly_white', height=400,
                      margin=dict(l=20, r=20, t=50, b=20))
    alloc_chart = fig.to_html(full_html=False, include_plotlyjs=False)

    # Drift bar chart
    fig2 = go.Figure()
    colors = ['#28a745' if d > 0 else '#dc3545' for d in diff]
    fig2.add_trace(go.Bar(x=tickers, y=diff * 100, marker_color=colors,
                          text=[f"{d*100:+.1f}%" for d in diff],
                          textposition='outside'))
    fig2.update_layout(title='Weight Drift (Target − Current)',
                       yaxis_title='Percentage Points',
                       template='plotly_white', height=350,
                       margin=dict(l=40, r=20, t=50, b=40))
    drift_chart = fig2.to_html(full_html=False, include_plotlyjs=False)

    return {
        'trades': trades,
        'total_turnover': f"${total_turnover:,.0f}",
        'tx_cost': f"${tx_cost:,.2f}",
        'tx_cost_bps': tx_cost_bps,
        'portfolio_value': f"${portfolio_value:,.0f}",
        'alloc_chart': alloc_chart,
        'drift_chart': drift_chart,
    }

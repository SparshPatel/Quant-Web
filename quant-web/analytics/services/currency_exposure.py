"""
Currency Exposure Analyzer.

Analyses FX risk for a portfolio of international holdings,
shows hedged vs unhedged returns, and calculates FX contribution.
"""

import numpy as np
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .global_indices import (
    GLOBAL_INDICES, FX_PAIRS, FX_CONVERSION_COSTS,
    fetch_fx_rate, fetch_multiple_fx_rates,
)


def analyze_currency_exposure(tickers, weights=None, base_currency='USD',
                               start_date='2020-01-01', end_date=None):
    """
    Analyse how FX movements affect portfolio returns.

    Args:
        tickers: list of index tickers or stock tickers
        weights: list of floats (must sum to 1). None = equal weight.
        base_currency: investor's home currency
        start_date / end_date: date strings
    """
    if not tickers:
        raise ValueError("Provide at least one ticker.")

    n = len(tickers)
    if weights is None:
        weights = [1.0 / n] * n
    elif abs(sum(weights) - 1.0) > 0.01:
        raise ValueError("Weights must sum to 1.0")

    # Determine currency for each ticker
    ticker_currencies = []
    for t in tickers:
        meta = GLOBAL_INDICES.get(t)
        if meta:
            ticker_currencies.append(meta['currency'])
        else:
            # Try to guess from yfinance
            try:
                info = yf.Ticker(t).info or {}
                ticker_currencies.append(info.get('currency', 'USD'))
            except Exception:
                ticker_currencies.append('USD')

    # Unique currencies needed
    unique_currencies = set(ticker_currencies) - {base_currency}

    # Download price data for all tickers
    all_prices = {}
    for t in tickers:
        try:
            data = yf.download(t, start=start_date, end=end_date, progress=False)
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.droplevel(level=1)
            if 'Close' in data.columns and len(data) > 1:
                all_prices[t] = data['Close']
        except Exception:
            continue

    if not all_prices:
        raise ValueError("Could not retrieve price data for any ticker.")

    prices_df = pd.DataFrame(all_prices).dropna(how='all').ffill().dropna()

    # Download FX data for non-base currencies
    fx_series = {}
    for curr in unique_currencies:
        pair = f"{curr}{base_currency}=X"
        try:
            fx_data = yf.download(pair, start=start_date, end=end_date, progress=False)
            if isinstance(fx_data.columns, pd.MultiIndex):
                fx_data.columns = fx_data.columns.droplevel(level=1)
            if 'Close' in fx_data.columns:
                fx_series[curr] = fx_data['Close']
        except Exception:
            pass

    # Calculate local-currency returns (unhedged) and FX-adjusted returns
    local_returns = prices_df.pct_change().dropna()

    # FX returns for each ticker
    fx_returns_df = pd.DataFrame(index=local_returns.index)
    for i, t in enumerate(tickers):
        if t not in local_returns.columns:
            continue
        curr = ticker_currencies[i]
        if curr == base_currency or curr not in fx_series:
            fx_returns_df[t] = 0.0
        else:
            fx_ret = fx_series[curr].reindex(local_returns.index).ffill().pct_change()
            fx_returns_df[t] = fx_ret.reindex(local_returns.index).fillna(0)

    # Total return in base currency = (1 + local_return) * (1 + fx_return) - 1
    total_returns = pd.DataFrame(index=local_returns.index)
    available_tickers = [t for t in tickers if t in local_returns.columns]
    available_weights = []
    available_currencies = []

    for i, t in enumerate(tickers):
        if t in local_returns.columns:
            total_returns[t] = (1 + local_returns[t]) * (1 + fx_returns_df[t]) - 1
            available_weights.append(weights[i])
            available_currencies.append(ticker_currencies[i])

    if not available_tickers:
        raise ValueError("No overlapping data available.")

    # Normalise weights
    w = np.array(available_weights)
    w = w / w.sum()

    # Portfolio returns
    port_local = (local_returns[available_tickers].values @ w)
    port_total = (total_returns[available_tickers].values @ w)
    port_fx_only = port_total - port_local  # FX contribution

    idx = local_returns.index

    # Cumulative
    cum_local = (1 + pd.Series(port_local, index=idx)).cumprod()
    cum_total = (1 + pd.Series(port_total, index=idx)).cumprod()

    # -- Chart 1: Hedged (local) vs Unhedged (total) cumulative --
    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(
        x=idx, y=cum_local, name=f'Hedged (Local Currency Returns)',
        line=dict(width=1.8, color='#2563eb'),
    ))
    fig1.add_trace(go.Scatter(
        x=idx, y=cum_total, name=f'Unhedged (in {base_currency})',
        line=dict(width=1.8, color='#dc2626'),
    ))
    fig1.update_layout(
        title=f'Hedged vs Unhedged Portfolio Returns (in {base_currency})',
        xaxis_title='Date', yaxis_title='Growth of $1',
        template='plotly_white', height=450,
        margin=dict(l=40, r=20, t=50, b=40),
    )

    # -- Chart 2: Rolling FX contribution --
    rolling_fx = pd.Series(port_fx_only, index=idx).rolling(63).sum()  # quarterly
    fig2 = go.Figure()
    fig2.add_trace(go.Bar(
        x=idx, y=rolling_fx,
        marker_color=np.where(rolling_fx >= 0, '#16a34a', '#dc2626'),
        name='FX Contribution (63-day rolling)',
    ))
    fig2.update_layout(
        title='Rolling 63-Day FX Contribution to Portfolio Returns',
        xaxis_title='Date', yaxis_title='FX Return Contribution',
        template='plotly_white', height=350,
        margin=dict(l=40, r=20, t=50, b=40),
    )

    # -- Chart 3: Currency allocation pie --
    currency_weights = {}
    for i, t in enumerate(available_tickers):
        curr = available_currencies[i]
        currency_weights[curr] = currency_weights.get(curr, 0) + w[i]

    fig3 = go.Figure(data=[go.Pie(
        labels=list(currency_weights.keys()),
        values=list(currency_weights.values()),
        textinfo='label+percent',
        hole=0.4,
    )])
    fig3.update_layout(
        title='Portfolio Currency Allocation',
        template='plotly_white', height=350,
        margin=dict(l=20, r=20, t=50, b=20),
    )

    # -- Summary stats --
    ann_local = float(np.mean(port_local) * 252)
    ann_total = float(np.mean(port_total) * 252)
    ann_fx = ann_total - ann_local
    vol_local = float(np.std(port_local) * np.sqrt(252))
    vol_total = float(np.std(port_total) * np.sqrt(252))

    # Conversion cost estimate
    total_conv_cost = sum(
        w[i] * FX_CONVERSION_COSTS.get(available_currencies[i], 0.10)
        for i in range(len(available_tickers))
    )

    # Current FX rates
    current_rates = []
    for curr in sorted(set(available_currencies)):
        if curr == base_currency:
            continue
        rate = fetch_fx_rate(curr, base_currency)
        cost = FX_CONVERSION_COSTS.get(curr, 0.10)
        current_rates.append({
            'currency': curr,
            'rate': f"{rate:.4f}" if rate else 'N/A',
            'spread_pct': f"{cost:.2f}%",
        })

    holdings_detail = []
    for i, t in enumerate(available_tickers):
        meta = GLOBAL_INDICES.get(t, {'name': t, 'flag': ''})
        holdings_detail.append({
            'ticker': t,
            'name': meta.get('name', t),
            'flag': meta.get('flag', ''),
            'currency': available_currencies[i],
            'weight': f"{w[i]:.2%}",
            'fx_cost_pct': f"{FX_CONVERSION_COSTS.get(available_currencies[i], 0.10):.2f}%",
        })

    return {
        'hedged_chart': fig1.to_html(full_html=False, include_plotlyjs=False),
        'fx_contribution_chart': fig2.to_html(full_html=False, include_plotlyjs=False),
        'currency_pie_chart': fig3.to_html(full_html=False, include_plotlyjs=False),
        'ann_return_hedged': f"{ann_local:.2%}",
        'ann_return_unhedged': f"{ann_total:.2%}",
        'fx_impact': f"{ann_fx:+.2%}",
        'vol_hedged': f"{vol_local:.2%}",
        'vol_unhedged': f"{vol_total:.2%}",
        'est_conversion_cost': f"{total_conv_cost:.3%}",
        'base_currency': base_currency,
        'current_rates': current_rates,
        'holdings': holdings_detail,
        'n_currencies': len(set(available_currencies)),
    }

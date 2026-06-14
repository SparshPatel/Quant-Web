"""
Global Macro Dashboard — compare indices across regions.

Side-by-side performance, correlation heatmap, and relative strength
for selected world indices.
"""

import numpy as np
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .global_indices import GLOBAL_INDICES, fetch_index_data


def compare_global_indices(index_tickers, start_date, end_date):
    """
    Compare performance of multiple global indices.
    Returns normalised charts, correlation, and summary statistics.
    """
    if len(index_tickers) < 2:
        raise ValueError("Select at least 2 indices to compare.")
    if len(index_tickers) > 15:
        raise ValueError("Maximum 15 indices at a time for readability.")

    # Fetch all price series
    all_close = {}
    meta_list = []
    for ticker in index_tickers:
        meta = GLOBAL_INDICES.get(ticker, {'name': ticker, 'flag': '', 'currency': '?', 'country': '?', 'region': '?'})
        try:
            df = fetch_index_data(ticker, start_date, end_date)
            if 'Close' in df.columns and len(df) > 1:
                all_close[ticker] = df['Close']
                meta_list.append(meta | {'ticker': ticker})
        except Exception:
            continue

    if len(all_close) < 2:
        raise ValueError("Could not retrieve enough data. Try different indices or a wider date range.")

    prices = pd.DataFrame(all_close).dropna(how='all').ffill().dropna()
    if len(prices) < 2:
        raise ValueError("Not enough overlapping data between selected indices.")

    returns = prices.pct_change().dropna()

    # -- Normalised price chart (base 100) --
    normalised = (prices / prices.iloc[0]) * 100

    colors = [
        '#2563eb', '#dc2626', '#16a34a', '#f59e0b', '#8b5cf6',
        '#ec4899', '#06b6d4', '#84cc16', '#f97316', '#6366f1',
        '#14b8a6', '#e11d48', '#a855f7', '#22d3ee', '#eab308',
    ]

    fig_perf = go.Figure()
    for i, ticker in enumerate(normalised.columns):
        meta = GLOBAL_INDICES.get(ticker, {'name': ticker, 'flag': ''})
        label = f"{meta.get('flag', '')} {meta.get('name', ticker)}"
        fig_perf.add_trace(go.Scatter(
            x=normalised.index, y=normalised[ticker],
            name=label, line=dict(width=1.8, color=colors[i % len(colors)]),
        ))
    fig_perf.update_layout(
        title='Normalised Performance (Base 100)',
        xaxis_title='Date', yaxis_title='Index (Base 100)',
        template='plotly_white', height=500,
        margin=dict(l=40, r=20, t=50, b=40),
        legend=dict(font=dict(size=10)),
    )

    # -- Correlation heatmap --
    corr = returns.corr()
    labels = [f"{GLOBAL_INDICES.get(t, {}).get('flag', '')} {GLOBAL_INDICES.get(t, {}).get('name', t)}"
              for t in corr.columns]

    fig_corr = go.Figure(data=go.Heatmap(
        z=corr.values, x=labels, y=labels,
        colorscale='RdBu_r', zmin=-1, zmax=1,
        text=np.round(corr.values, 2), texttemplate='%{text}',
        textfont=dict(size=10),
    ))
    fig_corr.update_layout(
        title='Cross-Index Correlation',
        template='plotly_white', height=500,
        margin=dict(l=120, r=20, t=50, b=120),
    )

    # -- Summary statistics table --
    summary = []
    for ticker in returns.columns:
        meta = GLOBAL_INDICES.get(ticker, {'name': ticker, 'flag': '', 'currency': '?', 'region': '?'})
        r = returns[ticker]
        ann_ret = r.mean() * 252
        ann_vol = r.std() * np.sqrt(252)
        sharpe = ann_ret / ann_vol if ann_vol > 0 else 0
        cum_ret = (1 + r).prod() - 1
        max_dd = ((prices[ticker] / prices[ticker].cummax()) - 1).min()

        summary.append({
            'ticker': ticker,
            'name': f"{meta.get('flag', '')} {meta.get('name', ticker)}",
            'currency': meta.get('currency', '?'),
            'region': meta.get('region', '?'),
            'ann_return': f"{ann_ret:.2%}",
            'ann_vol': f"{ann_vol:.2%}",
            'sharpe': f"{sharpe:.2f}",
            'cum_return': f"{cum_ret:.2%}",
            'max_drawdown': f"{max_dd:.2%}",
        })

    # Sort by annualised return descending
    summary.sort(key=lambda x: float(x['ann_return'].strip('%')), reverse=True)

    # -- Rolling 60-day correlation with first index --
    reference = index_tickers[0]
    ref_meta = GLOBAL_INDICES.get(reference, {'name': reference, 'flag': ''})
    fig_rolling = go.Figure()
    for i, ticker in enumerate(index_tickers[1:], start=1):
        meta = GLOBAL_INDICES.get(ticker, {'name': ticker, 'flag': ''})
        if ticker in returns.columns and reference in returns.columns:
            rc = returns[reference].rolling(60).corr(returns[ticker])
            fig_rolling.add_trace(go.Scatter(
                x=rc.index, y=rc.values,
                name=f"{meta.get('flag', '')} {meta.get('name', ticker)}",
                line=dict(width=1.3, color=colors[i % len(colors)]),
            ))
    fig_rolling.update_layout(
        title=f'Rolling 60-Day Correlation vs {ref_meta.get("flag", "")} {ref_meta.get("name", reference)}',
        xaxis_title='Date', yaxis_title='Correlation',
        template='plotly_white', height=400,
        margin=dict(l=40, r=20, t=50, b=40),
    )

    return {
        'performance_chart': fig_perf.to_html(full_html=False, include_plotlyjs=False),
        'correlation_chart': fig_corr.to_html(full_html=False, include_plotlyjs=False),
        'rolling_corr_chart': fig_rolling.to_html(full_html=False, include_plotlyjs=False),
        'summary': summary,
        'n_indices': len(summary),
        'date_range': f"{prices.index[0].date()} to {prices.index[-1].date()}",
        'n_days': len(prices),
    }

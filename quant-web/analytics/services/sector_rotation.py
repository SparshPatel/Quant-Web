import re
import numpy as np
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots


# Sector ETFs (SPDR sector ETFs)
SECTOR_ETFS = {
    'XLK': 'Technology',
    'XLV': 'Healthcare',
    'XLF': 'Financials',
    'XLY': 'Consumer Discretionary',
    'XLP': 'Consumer Staples',
    'XLI': 'Industrials',
    'XLE': 'Energy',
    'XLB': 'Materials',
    'XLC': 'Communication Services',
    'XLRE': 'Real Estate',
    'XLU': 'Utilities',
}


def analyze_sectors(start_date, end_date, lookback=63):
    """
    Sector momentum analysis using SPDR sector ETFs.

    Parameters
    ----------
    start_date, end_date : str
    lookback : int – days for momentum calculation

    Returns dict with sector heatmap, relative strength, and rotation signals.
    """
    tickers = list(SECTOR_ETFS.keys())

    prices = yf.download(tickers, start=start_date, end=end_date)['Close']
    if isinstance(prices, pd.Series):
        raise ValueError("Could not download sector ETF data.")

    returns = prices.pct_change().dropna()
    if len(returns) < lookback:
        raise ValueError(f"Need at least {lookback} trading days of data.")

    # ---------- Momentum scores ----------
    momentum = {}
    for t in tickers:
        if t in returns.columns:
            mom = (prices[t].iloc[-1] / prices[t].iloc[-lookback] - 1) * 100
            momentum[t] = mom

    # Sort by momentum
    sorted_sectors = sorted(momentum.items(), key=lambda x: x[1], reverse=True)

    sector_data = []
    for t, mom in sorted_sectors:
        name = SECTOR_ETFS[t]
        ret_1m = (prices[t].iloc[-1] / prices[t].iloc[-min(21, len(prices))] - 1) * 100
        ret_3m = (prices[t].iloc[-1] / prices[t].iloc[-min(63, len(prices))] - 1) * 100
        vol = returns[t].std() * np.sqrt(252) * 100

        # Relative strength vs SPY
        spy_mom = 0
        if '^GSPC' not in tickers:
            try:
                spy_data = yf.download('SPY', start=start_date, end=end_date)['Close']
                if isinstance(spy_data, pd.DataFrame):
                    spy_data = spy_data.iloc[:, 0]
                if len(spy_data) >= lookback:
                    spy_mom = (float(spy_data.iloc[-1]) / float(spy_data.iloc[-lookback]) - 1) * 100
            except Exception:
                pass
        rs = mom - spy_mom

        signal = 'OVERWEIGHT' if rs > 2 else ('UNDERWEIGHT' if rs < -2 else 'NEUTRAL')

        sector_data.append({
            'ticker': t,
            'sector': name,
            'momentum': f"{mom:+.1f}%",
            'ret_1m': f"{ret_1m:+.1f}%",
            'ret_3m': f"{ret_3m:+.1f}%",
            'volatility': f"{vol:.1f}%",
            'rel_strength': f"{rs:+.1f}%",
            'signal': signal,
            'mom_raw': mom,
        })

    # ---------- Heatmap chart ----------
    names = [d['sector'] for d in sector_data]
    moms = [d['mom_raw'] for d in sector_data]

    fig_heat = go.Figure()
    colors = ['#28a745' if m > 0 else '#dc3545' for m in moms]
    fig_heat.add_trace(go.Bar(
        x=names, y=moms, marker_color=colors,
        text=[f"{m:+.1f}%" for m in moms], textposition='outside'))
    fig_heat.update_layout(
        title=f'Sector Momentum ({lookback}-Day Return)',
        yaxis_title='Return (%)',
        template='plotly_white', height=400,
        margin=dict(l=40, r=20, t=50, b=80))
    heatmap_chart = fig_heat.to_html(full_html=False, include_plotlyjs=False)

    # ---------- Relative strength chart ----------
    rs_vals = [float(d['rel_strength'].replace('%', '').replace('+', '')) for d in sector_data]
    rs_colors = ['#28a745' if v > 0 else '#dc3545' for v in rs_vals]
    fig_rs = go.Figure()
    fig_rs.add_trace(go.Bar(
        x=names, y=rs_vals, marker_color=rs_colors,
        text=[f"{v:+.1f}%" for v in rs_vals], textposition='outside'))
    fig_rs.update_layout(
        title='Relative Strength vs Market (SPY)',
        yaxis_title='Relative Return (%)',
        template='plotly_white', height=400,
        margin=dict(l=40, r=20, t=50, b=80))
    rs_chart = fig_rs.to_html(full_html=False, include_plotlyjs=False)

    # ---------- Performance over time ----------
    fig_perf = go.Figure()
    norm = prices / prices.iloc[0] * 100
    for t in tickers:
        if t in norm.columns:
            fig_perf.add_trace(go.Scatter(
                x=norm.index, y=norm[t],
                mode='lines', name=SECTOR_ETFS[t],
                line=dict(width=1.5)))
    fig_perf.update_layout(
        title='Sector Performance (Indexed to 100)',
        xaxis_title='Date', yaxis_title='Indexed Price',
        template='plotly_white', height=450,
        margin=dict(l=40, r=20, t=50, b=40),
        legend=dict(font=dict(size=10)))
    perf_chart = fig_perf.to_html(full_html=False, include_plotlyjs=False)

    return {
        'sector_data': sector_data,
        'heatmap_chart': heatmap_chart,
        'rs_chart': rs_chart,
        'perf_chart': perf_chart,
        'lookback': lookback,
    }

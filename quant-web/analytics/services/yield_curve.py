import numpy as np
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go


# US Treasury tickers on Yahoo Finance
TREASURY_TICKERS = {
    '^IRX': {'label': '3-Month', 'maturity': 0.25},
    '^FVX': {'label': '5-Year', 'maturity': 5},
    '^TNX': {'label': '10-Year', 'maturity': 10},
    '^TYX': {'label': '30-Year', 'maturity': 30},
}

# Additional maturities via ETF proxies
ETF_PROXIES = {
    'SHY': {'label': '1-3 Year (SHY)', 'maturity': 2},
    'IEF': {'label': '7-10 Year (IEF)', 'maturity': 8.5},
    'TLT': {'label': '20+ Year (TLT)', 'maturity': 25},
}


def analyze_yield_curve():
    """
    Fetch current US Treasury yields, build yield curve, detect inversion.

    Returns dict with curve data, spread analysis, and charts.
    """
    # Fetch treasury yields
    tickers = list(TREASURY_TICKERS.keys())
    data = yf.download(tickers, period='2y')['Close']
    if isinstance(data, pd.Series):
        data = data.to_frame(tickers[0])

    if data.empty:
        raise ValueError("Could not download Treasury yield data.")

    # Current yields (latest row)
    latest = data.iloc[-1]
    prev_month = data.iloc[-22] if len(data) > 22 else data.iloc[0]
    prev_year = data.iloc[-252] if len(data) > 252 else data.iloc[0]

    curve_points = []
    for t, meta in TREASURY_TICKERS.items():
        if t in latest.index:
            current = float(latest[t])
            month_ago = float(prev_month[t]) if t in prev_month.index else None
            year_ago = float(prev_year[t]) if t in prev_year.index else None
            curve_points.append({
                'label': meta['label'],
                'maturity': meta['maturity'],
                'yield_pct': f"{current:.2f}%",
                'yield_raw': current,
                'change_1m': f"{(current - month_ago):+.2f}%" if month_ago else 'N/A',
                'change_1y': f"{(current - year_ago):+.2f}%" if year_ago else 'N/A',
            })

    # Sort by maturity
    curve_points.sort(key=lambda x: x['maturity'])

    # Spread analysis
    spreads = {}
    yields_dict = {cp['label']: cp['yield_raw'] for cp in curve_points}
    if '10-Year' in yields_dict and '3-Month' in yields_dict:
        spread_10y_3m = yields_dict['10-Year'] - yields_dict['3-Month']
        spreads['10Y-3M'] = f"{spread_10y_3m:+.2f}%"
        spreads['10Y-3M_inverted'] = spread_10y_3m < 0
    if '10-Year' in yields_dict and '30-Year' in yields_dict:
        spread_30y_10y = yields_dict['30-Year'] - yields_dict['10-Year']
        spreads['30Y-10Y'] = f"{spread_30y_10y:+.2f}%"
    if '5-Year' in yields_dict and '3-Month' in yields_dict:
        spread_5y_3m = yields_dict['5-Year'] - yields_dict['3-Month']
        spreads['5Y-3M'] = f"{spread_5y_3m:+.2f}%"

    inversion_detected = any(
        curve_points[i]['yield_raw'] > curve_points[i+1]['yield_raw']
        for i in range(len(curve_points) - 1)
    )

    # ---------- Yield curve chart ----------
    maturities = [cp['maturity'] for cp in curve_points]
    yields = [cp['yield_raw'] for cp in curve_points]
    labels = [cp['label'] for cp in curve_points]

    fig_curve = go.Figure()
    fig_curve.add_trace(go.Scatter(
        x=maturities, y=yields, mode='lines+markers',
        line=dict(width=3, color='#0d6efd'),
        marker=dict(size=10),
        text=labels, hovertemplate='%{text}<br>Maturity: %{x}Y<br>Yield: %{y:.2f}%'))
    fig_curve.update_layout(
        title='US Treasury Yield Curve',
        xaxis_title='Maturity (Years)', yaxis_title='Yield (%)',
        template='plotly_white', height=400,
        margin=dict(l=40, r=20, t=50, b=40))

    # Shade inversion areas
    if inversion_detected:
        fig_curve.add_annotation(
            text="⚠ Yield Curve Inversion Detected",
            xref="paper", yref="paper", x=0.5, y=1.05,
            showarrow=False, font=dict(color='red', size=14))
    curve_chart = fig_curve.to_html(full_html=False, include_plotlyjs=False)

    # ---------- Historical spread chart ----------
    if '^TNX' in data.columns and '^IRX' in data.columns:
        hist_spread = data['^TNX'] - data['^IRX']
        fig_spread = go.Figure()
        fig_spread.add_trace(go.Scatter(
            x=hist_spread.index, y=hist_spread.values,
            mode='lines', line=dict(width=1.5),
            name='10Y - 3M Spread'))
        fig_spread.add_hline(y=0, line_dash='dash', line_color='red',
                             annotation_text='Inversion Threshold')
        fig_spread.update_layout(
            title='10Y - 3M Treasury Spread (Historical)',
            xaxis_title='Date', yaxis_title='Spread (%)',
            template='plotly_white', height=350,
            margin=dict(l=40, r=20, t=50, b=40))
        spread_chart = fig_spread.to_html(full_html=False, include_plotlyjs=False)
    else:
        spread_chart = None

    return {
        'curve_points': curve_points,
        'spreads': spreads,
        'inversion_detected': inversion_detected,
        'curve_chart': curve_chart,
        'spread_chart': spread_chart,
    }

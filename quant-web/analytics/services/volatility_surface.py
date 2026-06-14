import re
import numpy as np
import pandas as pd
import yfinance as yf
from scipy.optimize import brentq
from scipy.stats import norm
import plotly.graph_objects as go


def validate_ticker(ticker):
    return bool(re.match(r'^[\^]?[A-Z0-9.\-=]{1,20}$', ticker.upper()))


def _bs_call(S, K, T, r, sigma):
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    return S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)


def _implied_vol(price, S, K, T, r):
    try:
        return brentq(lambda sigma: _bs_call(S, K, T, r, sigma) - price, 0.01, 5.0)
    except Exception:
        return np.nan


def build_surface(ticker_symbol):
    if not validate_ticker(ticker_symbol):
        raise ValueError(f"Invalid ticker symbol: {ticker_symbol}")

    ticker = yf.Ticker(ticker_symbol)
    spot = ticker.history(period='1d')['Close'].iloc[-1]
    expiries = ticker.options

    if not expiries:
        raise ValueError(f"No options data available for {ticker_symbol}.")

    r = 0.05
    results = []
    n_expiries = min(12, len(expiries))

    for exp in expiries[:n_expiries]:
        chain = ticker.option_chain(exp)
        calls = chain.calls

        T = (pd.Timestamp(exp) - pd.Timestamp.now()).days / 365
        if T <= 0.003:
            continue

        for _, row in calls.iterrows():
            K = row['strike']

            if row['bid'] > 0 and row['ask'] > 0:
                price = (row['bid'] + row['ask']) / 2
            elif row['lastPrice'] > 0:
                price = row['lastPrice']
            else:
                continue

            if K < spot * 0.7 or K > spot * 1.3:
                continue

            iv = _implied_vol(price, spot, K, T, r)

            if not np.isnan(iv) and 0.05 < iv < 2.0:
                results.append({
                    'expiry': exp,
                    'strike': K,
                    'T': round(T, 4),
                    'iv': round(iv, 4),
                    'mid_price': round(price, 2),
                })

    if not results:
        raise ValueError("Could not compute any implied volatilities. Try a different ticker.")

    df = pd.DataFrame(results)

    # 3D surface
    fig1 = go.Figure(data=[go.Mesh3d(
        x=df['strike'], y=df['T'], z=df['iv'],
        intensity=df['iv'], colorscale='Viridis', opacity=0.75,
        colorbar_title='IV')])
    fig1.update_layout(
        title=f'Implied Volatility Surface — {ticker_symbol}',
        scene=dict(
            xaxis_title='Strike Price ($)',
            yaxis_title='Time to Expiry (years)',
            zaxis_title='Implied Volatility'),
        height=600, margin=dict(l=0, r=0, t=50, b=0))

    # 2D smile for one expiry
    available = df['expiry'].unique()
    target_exp = available[min(2, len(available) - 1)]
    smile = df[df['expiry'] == target_exp].sort_values('strike')

    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(
        x=smile['strike'], y=smile['iv'], mode='lines+markers',
        marker=dict(size=4), name='IV'))
    fig2.add_vline(x=spot, line_dash='dash', line_color='red',
                   annotation_text=f'Spot = ${spot:.0f}')
    fig2.update_layout(
        title=f'Volatility Smile — Expiry: {target_exp}',
        xaxis_title='Strike Price ($)', yaxis_title='Implied Volatility',
        template='plotly_white', height=400, margin=dict(l=40, r=20, t=50, b=40))

    return {
        'spot': f"{spot:.2f}",
        'n_expiries': len(available),
        'n_points': len(df),
        'surface_chart': fig1.to_html(full_html=False, include_plotlyjs=False),
        'smile_chart': fig2.to_html(full_html=False, include_plotlyjs=False),
        'smile_expiry': target_exp,
    }

import re
import numpy as np
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go


def validate_ticker(ticker):
    return bool(re.match(r'^[\^]?[A-Z0-9.\-=]{1,20}$', ticker.upper()))


def get_watchlist_data(tickers, sma_short=20, sma_long=50, rsi_period=14):
    """
    Fetch live data for a watchlist: price, change, SMA crossover signal,
    RSI signal, and key stats.

    Parameters
    ----------
    tickers : list[str]
    sma_short, sma_long : int – SMA periods for crossover
    rsi_period : int

    Returns dict with watchlist data and mini-charts.
    """
    for t in tickers:
        if not validate_ticker(t):
            raise ValueError(f"Invalid ticker: {t}")

    watchlist = []

    for t in tickers:
        try:
            stock = yf.Ticker(t)
            info = stock.info or {}
            hist = stock.history(period='6mo')

            if hist.empty:
                watchlist.append({
                    'ticker': t, 'name': t, 'price': 'N/A',
                    'change_1d': 'N/A', 'change_1w': 'N/A',
                    'sma_signal': 'N/A', 'rsi': 'N/A', 'rsi_signal': 'N/A',
                    'volume': 'N/A', 'mkt_cap': 'N/A',
                })
                continue

            close = hist['Close']
            price = float(close.iloc[-1])

            # Daily change
            if len(close) >= 2:
                change_1d = (close.iloc[-1] / close.iloc[-2] - 1) * 100
            else:
                change_1d = 0

            # Weekly change
            if len(close) >= 6:
                change_1w = (close.iloc[-1] / close.iloc[-6] - 1) * 100
            else:
                change_1w = 0

            # SMA crossover signal
            sma_signal = 'N/A'
            if len(close) >= sma_long:
                sma_s = close.rolling(sma_short).mean()
                sma_l = close.rolling(sma_long).mean()
                if sma_s.iloc[-1] > sma_l.iloc[-1]:
                    sma_signal = 'BULLISH'
                else:
                    sma_signal = 'BEARISH'

            # RSI
            rsi_val = None
            rsi_signal = 'N/A'
            if len(close) >= rsi_period + 1:
                delta = close.diff()
                gain = delta.clip(lower=0).rolling(rsi_period).mean()
                loss = (-delta.clip(upper=0)).rolling(rsi_period).mean()
                rs = gain / loss
                rsi = 100 - (100 / (1 + rs))
                rsi_val = float(rsi.iloc[-1])
                if rsi_val < 30:
                    rsi_signal = 'OVERSOLD'
                elif rsi_val > 70:
                    rsi_signal = 'OVERBOUGHT'
                else:
                    rsi_signal = 'NEUTRAL'

            # Volume
            vol = hist['Volume'].iloc[-1] if 'Volume' in hist.columns else 0
            mkt_cap = info.get('marketCap', 0)

            watchlist.append({
                'ticker': t,
                'name': info.get('shortName', t),
                'price': f"${price:,.2f}",
                'change_1d': f"{change_1d:+.2f}%",
                'change_1w': f"{change_1w:+.2f}%",
                'sma_signal': sma_signal,
                'rsi': f"{rsi_val:.0f}" if rsi_val is not None else 'N/A',
                'rsi_signal': rsi_signal,
                'volume': f"{vol:,.0f}" if vol else 'N/A',
                'mkt_cap': f"${mkt_cap/1e9:.1f}B" if mkt_cap else 'N/A',
                'change_1d_raw': change_1d,
            })
        except Exception:
            watchlist.append({
                'ticker': t, 'name': t, 'price': 'N/A',
                'change_1d': 'N/A', 'change_1w': 'N/A',
                'sma_signal': 'N/A', 'rsi': 'N/A', 'rsi_signal': 'N/A',
                'volume': 'N/A', 'mkt_cap': 'N/A', 'change_1d_raw': 0,
            })

    # ---------- Daily change chart ----------
    valid = [w for w in watchlist if w.get('change_1d_raw', 0) != 0 or w['price'] != 'N/A']
    if valid:
        labels = [w['ticker'] for w in valid]
        changes = [w.get('change_1d_raw', 0) for w in valid]
        colors = ['#28a745' if c > 0 else '#dc3545' for c in changes]
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=labels, y=changes, marker_color=colors,
            text=[f"{c:+.2f}%" for c in changes], textposition='outside'))
        fig.update_layout(
            title='Today\'s Performance',
            yaxis_title='Change (%)',
            template='plotly_white', height=350,
            margin=dict(l=40, r=20, t=50, b=40))
        change_chart = fig.to_html(full_html=False, include_plotlyjs=False)
    else:
        change_chart = None

    return {
        'watchlist': watchlist,
        'change_chart': change_chart,
    }

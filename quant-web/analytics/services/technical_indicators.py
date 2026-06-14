import re
import numpy as np
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def _sma(s, w):
    return s.rolling(w).mean()


def _ema(s, w):
    return s.ewm(span=w, adjust=False).mean()


def _rsi(s, period=14):
    delta = s.diff()
    gain = delta.where(delta > 0, 0.0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


def _macd(s, fast=12, slow=26, signal=9):
    ema_fast = _ema(s, fast)
    ema_slow = _ema(s, slow)
    macd_line = ema_fast - ema_slow
    signal_line = _ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def _bollinger(s, window=20, n_std=2):
    sma = _sma(s, window)
    std = s.rolling(window).std()
    return sma, sma + n_std * std, sma - n_std * std


def chart_indicators(ticker, start_date, end_date,
                     show_sma=True, sma_windows='20,50',
                     show_rsi=True, rsi_period=14,
                     show_macd=True,
                     show_bb=True, bb_window=20, bb_std=2.0):
    ticker = ticker.strip().upper()
    if not re.match(r'^[\^]?[A-Z0-9.\-=]{1,20}$', ticker):
        raise ValueError(f"Invalid ticker: {ticker}")

    df = yf.download(ticker, start=start_date, end=end_date)
    if df.empty or len(df) < 50:
        raise ValueError("Not enough data. Try a wider date range.")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    close = df['Close']
    dates = df.index

    # count subplots needed
    rows = 1
    if show_rsi:
        rows += 1
    if show_macd:
        rows += 1

    row_heights = [0.6] + [0.2] * (rows - 1)
    fig = make_subplots(rows=rows, cols=1, shared_xaxes=True,
                        vertical_spacing=0.03,
                        row_heights=row_heights)

    # --- Price + overlays ---
    fig.add_trace(go.Scatter(x=dates, y=close.values, mode='lines',
                             name=ticker, line=dict(width=1.5, color='black')), row=1, col=1)

    if show_sma:
        windows = [int(w.strip()) for w in sma_windows.split(',') if w.strip().isdigit()]
        colors = ['royalblue', 'orange', 'forestgreen', 'crimson']
        for i, w in enumerate(windows[:4]):
            s = _sma(close, w)
            fig.add_trace(go.Scatter(x=dates, y=s.values, mode='lines',
                                     name=f'SMA {w}',
                                     line=dict(width=1, color=colors[i % len(colors)])),
                          row=1, col=1)

    if show_bb:
        mid, upper, lower = _bollinger(close, bb_window, bb_std)
        fig.add_trace(go.Scatter(x=dates, y=upper.values, mode='lines',
                                 line=dict(width=0.5, color='gray', dash='dash'),
                                 name='BB Upper', showlegend=False), row=1, col=1)
        fig.add_trace(go.Scatter(x=dates, y=lower.values, mode='lines',
                                 fill='tonexty',
                                 fillcolor='rgba(128,128,128,0.1)',
                                 line=dict(width=0.5, color='gray', dash='dash'),
                                 name='Bollinger Bands'), row=1, col=1)

    current_row = 2

    # --- RSI ---
    if show_rsi:
        rsi = _rsi(close, rsi_period)
        fig.add_trace(go.Scatter(x=dates, y=rsi.values, mode='lines',
                                 name=f'RSI({rsi_period})',
                                 line=dict(width=1.5, color='purple')),
                      row=current_row, col=1)
        fig.add_hline(y=70, line_dash='dash', line_color='red', row=current_row, col=1)
        fig.add_hline(y=30, line_dash='dash', line_color='green', row=current_row, col=1)
        fig.update_yaxes(title_text='RSI', row=current_row, col=1)
        current_row += 1

    # --- MACD ---
    if show_macd:
        macd_line, signal_line, histogram = _macd(close)
        colors_hist = ['forestgreen' if v >= 0 else 'crimson' for v in histogram.values]
        fig.add_trace(go.Bar(x=dates, y=histogram.values, name='MACD Hist',
                             marker_color=colors_hist, opacity=0.6),
                      row=current_row, col=1)
        fig.add_trace(go.Scatter(x=dates, y=macd_line.values, mode='lines',
                                 name='MACD', line=dict(width=1.5, color='royalblue')),
                      row=current_row, col=1)
        fig.add_trace(go.Scatter(x=dates, y=signal_line.values, mode='lines',
                                 name='Signal', line=dict(width=1.5, color='orange')),
                      row=current_row, col=1)
        fig.update_yaxes(title_text='MACD', row=current_row, col=1)

    fig.update_layout(
        title=f'{ticker} — Technical Analysis',
        template='plotly_white',
        height=200 + rows * 250,
        margin=dict(l=40, r=20, t=50, b=40),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='left', x=0),
        xaxis_rangeslider_visible=False)
    fig.update_yaxes(title_text='Price ($)', row=1, col=1)

    # latest values
    last_close = float(close.iloc[-1])
    last_rsi = float(_rsi(close, rsi_period).iloc[-1]) if show_rsi else None
    macd_l, sig_l, _ = _macd(close)
    last_macd = float(macd_l.iloc[-1]) if show_macd else None
    last_signal = float(sig_l.iloc[-1]) if show_macd else None

    return {
        'ticker': ticker,
        'date_range': f"{dates[0].date()} to {dates[-1].date()}",
        'last_close': f"${last_close:,.2f}",
        'last_rsi': f"{last_rsi:.1f}" if last_rsi is not None else 'N/A',
        'rsi_signal': 'Overbought' if last_rsi and last_rsi > 70 else ('Oversold' if last_rsi and last_rsi < 30 else 'Neutral'),
        'last_macd': f"{last_macd:.4f}" if last_macd is not None else 'N/A',
        'macd_signal': 'Bullish' if last_macd and last_signal and last_macd > last_signal else 'Bearish',
        'chart': fig.to_html(full_html=False, include_plotlyjs=False),
    }

import re
import numpy as np
import pandas as pd
import yfinance as yf
import statsmodels.api as sm
from statsmodels.tsa.stattools import coint
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def validate_ticker(ticker):
    return bool(re.match(r'^[\^]?[A-Z0-9.\-=]{1,20}$', ticker.upper()))


def analyze_pair(ticker1, ticker2, start_date, end_date, entry_z=2.0, lookback=60):
    for t in [ticker1, ticker2]:
        if not validate_ticker(t):
            raise ValueError(f"Invalid ticker symbol: {t}")

    if ticker1.upper() == ticker2.upper():
        raise ValueError("The two tickers must be different.")

    raw = yf.download([ticker1, ticker2], start=start_date, end=end_date)
    data = raw['Close'].copy()
    data.dropna(inplace=True)

    if len(data) < lookback + 30:
        raise ValueError("Not enough data. Try a wider date range.")

    # Cointegration test
    score, pvalue, _ = coint(data[ticker1], data[ticker2])
    is_cointegrated = pvalue < 0.05

    # Hedge ratio via OLS
    X = sm.add_constant(data[ticker1])
    ols_result = sm.OLS(data[ticker2], X).fit()
    hedge_ratio = ols_result.params.iloc[1]
    intercept = ols_result.params.iloc[0]

    # Spread and z-score
    data['spread'] = data[ticker2] - hedge_ratio * data[ticker1] - intercept
    data['spread_mean'] = data['spread'].rolling(lookback).mean()
    data['spread_std'] = data['spread'].rolling(lookback).std()
    data['zscore'] = (data['spread'] - data['spread_mean']) / data['spread_std']
    data.dropna(inplace=True)

    # Backtest
    positions = []
    pos = 0
    for z in data['zscore']:
        if pos == 0:
            if z < -entry_z:
                pos = 1
            elif z > entry_z:
                pos = -1
        elif pos == 1 and z > 0:
            pos = 0
        elif pos == -1 and z < 0:
            pos = 0
        positions.append(pos)

    data['position'] = positions
    data['spread_return'] = data[ticker2].pct_change() - hedge_ratio * data[ticker1].pct_change()
    data['strategy_return'] = data['position'].shift(1) * data['spread_return']
    data['cumulative'] = (1 + data['strategy_return'].fillna(0)).cumprod()

    strat = data['strategy_return'].dropna()
    total_return = data['cumulative'].iloc[-1] - 1
    sharpe = strat.mean() / strat.std() * np.sqrt(252) if strat.std() > 0 else 0
    max_dd = (data['cumulative'] / data['cumulative'].cummax() - 1).min()
    num_trades = int((data['position'].diff().abs() > 0).sum())

    # Spread & z-score chart
    fig1 = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.5, 0.5],
                         vertical_spacing=0.06)

    fig1.add_trace(go.Scatter(
        x=data.index, y=data['spread'], mode='lines',
        line=dict(width=0.8), name='Spread'), row=1, col=1)
    fig1.add_hline(y=data['spread'].mean(), line_dash='dash', line_color='red',
                   annotation_text='Mean', row=1, col=1)

    fig1.add_trace(go.Scatter(
        x=data.index, y=data['zscore'], mode='lines',
        line=dict(width=0.8), name='Z-Score'), row=2, col=1)
    fig1.add_hline(y=entry_z, line_dash='dash', line_color='red', row=2, col=1)
    fig1.add_hline(y=-entry_z, line_dash='dash', line_color='green', row=2, col=1)
    fig1.add_hline(y=0, line_color='black', opacity=0.3, row=2, col=1)

    fig1.update_layout(
        title=f'Spread: {ticker2} − {hedge_ratio:.2f} × {ticker1}',
        template='plotly_white', height=500, margin=dict(l=40, r=20, t=50, b=40))
    fig1.update_yaxes(title_text='Spread', row=1, col=1)
    fig1.update_yaxes(title_text='Z-Score', row=2, col=1)

    # Cumulative return chart
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(
        x=data.index, y=data['cumulative'], mode='lines',
        line=dict(width=1.5), name='Strategy'))
    fig2.update_layout(
        title='Pairs Trading — Cumulative Returns',
        xaxis_title='Date', yaxis_title='Cumulative Return',
        template='plotly_white', height=400, margin=dict(l=40, r=20, t=50, b=40))

    return {
        'coint_stat': f"{score:.4f}",
        'coint_pvalue': f"{pvalue:.4f}",
        'is_cointegrated': is_cointegrated,
        'hedge_ratio': f"{hedge_ratio:.4f}",
        'total_return': f"{total_return:.2%}",
        'sharpe': f"{sharpe:.2f}",
        'max_drawdown': f"{max_dd:.2%}",
        'num_trades': num_trades,
        'spread_chart': fig1.to_html(full_html=False, include_plotlyjs=False),
        'cumulative_chart': fig2.to_html(full_html=False, include_plotlyjs=False),
        'date_range': f"{data.index[0].date()} to {data.index[-1].date()}",
    }

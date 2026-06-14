import re
import numpy as np
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots


STRATEGY_CHOICES = {
    'sma_crossover': 'SMA Crossover',
    'rsi_mean_reversion': 'RSI Mean Reversion',
    'momentum': 'Momentum (N-Day Return)',
    'bollinger_bands': 'Bollinger Bands',
    'buy_and_hold': 'Buy & Hold (Benchmark)',
}


def _sma(series, window):
    return series.rolling(window).mean()


def _rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


def run_backtest(ticker, start_date, end_date, strategy, initial_capital=10000,
                 fast_window=20, slow_window=50, rsi_period=14,
                 rsi_oversold=30, rsi_overbought=70, momentum_window=20,
                 bb_window=20, bb_std=2.0):
    ticker = ticker.strip().upper()
    if not re.match(r'^[\^]?[A-Z0-9.\-=]{1,20}$', ticker):
        raise ValueError(f"Invalid ticker: {ticker}")

    df = yf.download(ticker, start=start_date, end=end_date)
    if df.empty or len(df) < max(slow_window, 50):
        raise ValueError("Not enough data. Try a wider date range.")

    # Flatten multi-index columns if present
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    close = df['Close'].copy()
    dates = df.index

    signal = pd.Series(0.0, index=dates)  # +1 = long, 0 = flat

    # --- Generate signals ---
    if strategy == 'sma_crossover':
        sma_fast = _sma(close, fast_window)
        sma_slow = _sma(close, slow_window)
        signal[sma_fast > sma_slow] = 1.0

    elif strategy == 'rsi_mean_reversion':
        rsi = _rsi(close, rsi_period)
        position = 0.0
        for i in range(len(rsi)):
            if pd.notna(rsi.iloc[i]):
                if rsi.iloc[i] < rsi_oversold:
                    position = 1.0
                elif rsi.iloc[i] > rsi_overbought:
                    position = 0.0
            signal.iloc[i] = position

    elif strategy == 'momentum':
        mom = close.pct_change(momentum_window)
        signal[mom > 0] = 1.0

    elif strategy == 'bollinger_bands':
        sma = _sma(close, bb_window)
        std = close.rolling(bb_window).std()
        upper = sma + bb_std * std
        lower = sma - bb_std * std
        position = 0.0
        for i in range(len(close)):
            if pd.notna(lower.iloc[i]):
                if close.iloc[i] < lower.iloc[i]:
                    position = 1.0
                elif close.iloc[i] > upper.iloc[i]:
                    position = 0.0
            signal.iloc[i] = position

    elif strategy == 'buy_and_hold':
        signal[:] = 1.0
    else:
        raise ValueError(f"Unknown strategy: {strategy}")

    # Shift signal by 1 day (trade next day)
    signal = signal.shift(1).fillna(0.0)

    # --- Compute returns ---
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = signal * daily_ret
    bh_ret = daily_ret

    cum_strat = (1 + strat_ret).cumprod() * initial_capital
    cum_bh = (1 + bh_ret).cumprod() * initial_capital

    # --- Stats ---
    total_days = len(daily_ret)
    years = total_days / 252

    strat_total = cum_strat.iloc[-1] / initial_capital - 1
    bh_total = cum_bh.iloc[-1] / initial_capital - 1
    strat_ann = (1 + strat_total) ** (1 / years) - 1 if years > 0 else 0
    bh_ann = (1 + bh_total) ** (1 / years) - 1 if years > 0 else 0
    strat_vol = strat_ret.std() * np.sqrt(252)
    bh_vol = bh_ret.std() * np.sqrt(252)
    strat_sharpe = strat_ann / strat_vol if strat_vol > 0 else 0
    bh_sharpe = bh_ann / bh_vol if bh_vol > 0 else 0

    dd_strat = cum_strat / cum_strat.cummax() - 1
    dd_bh = cum_bh / cum_bh.cummax() - 1

    n_trades = int((signal.diff().abs() > 0).sum())

    # --- Equity chart ---
    fig_eq = go.Figure()
    fig_eq.add_trace(go.Scatter(x=dates, y=cum_strat.values, mode='lines',
                                name=STRATEGY_CHOICES.get(strategy, strategy),
                                line=dict(width=2, color='royalblue')))
    fig_eq.add_trace(go.Scatter(x=dates, y=cum_bh.values, mode='lines',
                                name='Buy & Hold', line=dict(width=1.5, dash='dash', color='gray')))
    fig_eq.update_layout(
        title='Equity Curve', xaxis_title='Date', yaxis_title='Portfolio Value ($)',
        template='plotly_white', height=400,
        margin=dict(l=40, r=20, t=50, b=40),
        legend=dict(yanchor='top', y=0.99, xanchor='left', x=0.01))

    # --- Drawdown chart ---
    fig_dd = go.Figure()
    fig_dd.add_trace(go.Scatter(x=dates, y=dd_strat.values, mode='lines',
                                fill='tozeroy', name='Strategy',
                                line=dict(width=1, color='crimson'),
                                fillcolor='rgba(220,20,60,0.15)'))
    fig_dd.add_trace(go.Scatter(x=dates, y=dd_bh.values, mode='lines',
                                name='Buy & Hold',
                                line=dict(width=1, dash='dash', color='gray')))
    fig_dd.update_layout(
        title='Drawdown', xaxis_title='Date', yaxis_title='Drawdown',
        template='plotly_white', height=300,
        margin=dict(l=40, r=20, t=50, b=40))

    return {
        'ticker': ticker,
        'strategy_name': STRATEGY_CHOICES.get(strategy, strategy),
        'date_range': f"{dates[0].date()} to {dates[-1].date()}",
        'initial_capital': f"${initial_capital:,.0f}",
        'final_value': f"${cum_strat.iloc[-1]:,.2f}",
        'total_return': f"{strat_total:.2%}",
        'ann_return': f"{strat_ann:.2%}",
        'ann_vol': f"{strat_vol:.2%}",
        'sharpe': f"{strat_sharpe:.2f}",
        'max_drawdown': f"{dd_strat.min():.2%}",
        'n_trades': n_trades,
        'bh_total_return': f"{bh_total:.2%}",
        'bh_ann_return': f"{bh_ann:.2%}",
        'bh_sharpe': f"{bh_sharpe:.2f}",
        'bh_max_drawdown': f"{dd_bh.min():.2%}",
        'bh_final_value': f"${cum_bh.iloc[-1]:,.2f}",
        'equity_chart': fig_eq.to_html(full_html=False, include_plotlyjs=False),
        'dd_chart': fig_dd.to_html(full_html=False, include_plotlyjs=False),
    }

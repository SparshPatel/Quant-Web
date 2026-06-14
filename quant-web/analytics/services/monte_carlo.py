import re
import numpy as np
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go


def simulate_paths(ticker, n_simulations=500, n_days=252, lookback_years=3):
    ticker = ticker.strip().upper()
    if not re.match(r'^[\^]?[A-Z0-9.\-=]{1,20}$', ticker):
        raise ValueError(f"Invalid ticker: {ticker}")

    end = pd.Timestamp.today()
    start = end - pd.DateOffset(years=lookback_years)
    prices = yf.download(ticker, start=str(start.date()), end=str(end.date()))['Close']
    if isinstance(prices, pd.DataFrame):
        prices = prices.iloc[:, 0]
    if prices.empty or len(prices) < 30:
        raise ValueError("Not enough historical data.")

    returns = prices.pct_change().dropna()
    mu_daily = returns.mean()
    sigma_daily = returns.std()
    last_price = float(prices.iloc[-1])

    # GBM simulation
    dt = 1.0
    drift = (mu_daily - 0.5 * sigma_daily ** 2) * dt
    diffusion = sigma_daily * np.sqrt(dt)

    np.random.seed(42)
    Z = np.random.standard_normal((n_simulations, n_days))
    log_returns = drift + diffusion * Z
    log_paths = np.cumsum(log_returns, axis=1)
    price_paths = last_price * np.exp(log_paths)

    # prepend starting price
    start_col = np.full((n_simulations, 1), last_price)
    price_paths = np.hstack([start_col, price_paths])

    days = list(range(n_days + 1))

    # percentiles
    p5 = np.percentile(price_paths, 5, axis=0)
    p25 = np.percentile(price_paths, 25, axis=0)
    p50 = np.percentile(price_paths, 50, axis=0)
    p75 = np.percentile(price_paths, 75, axis=0)
    p95 = np.percentile(price_paths, 95, axis=0)
    mean_path = np.mean(price_paths, axis=0)

    # --- fan chart ---
    fig = go.Figure()
    # 90% band
    fig.add_trace(go.Scatter(x=days, y=p95.tolist(), mode='lines',
                             line=dict(width=0), showlegend=False))
    fig.add_trace(go.Scatter(x=days, y=p5.tolist(), mode='lines',
                             fill='tonexty', fillcolor='rgba(70,130,180,0.15)',
                             line=dict(width=0), name='90% CI'))
    # 50% band
    fig.add_trace(go.Scatter(x=days, y=p75.tolist(), mode='lines',
                             line=dict(width=0), showlegend=False))
    fig.add_trace(go.Scatter(x=days, y=p25.tolist(), mode='lines',
                             fill='tonexty', fillcolor='rgba(70,130,180,0.30)',
                             line=dict(width=0), name='50% CI'))
    # median
    fig.add_trace(go.Scatter(x=days, y=p50.tolist(), mode='lines',
                             line=dict(width=2, color='royalblue'), name='Median'))
    fig.add_trace(go.Scatter(x=days, y=mean_path.tolist(), mode='lines',
                             line=dict(width=2, dash='dash', color='orange'), name='Mean'))

    fig.update_layout(
        title=f'Monte Carlo Simulation — {ticker} ({n_simulations} paths, {n_days} days)',
        xaxis_title='Trading Days', yaxis_title='Price ($)',
        template='plotly_white', height=500,
        margin=dict(l=40, r=20, t=50, b=40))

    # --- terminal distribution ---
    terminal = price_paths[:, -1]
    fig_hist = go.Figure()
    fig_hist.add_trace(go.Histogram(x=terminal, nbinsx=80,
                                    marker_color='steelblue', opacity=0.75))
    fig_hist.add_vline(x=last_price, line_dash='dash', line_color='red',
                       annotation_text=f'Current: ${last_price:,.2f}')
    fig_hist.update_layout(
        title='Terminal Price Distribution',
        xaxis_title='Price ($)', yaxis_title='Frequency',
        template='plotly_white', height=350,
        margin=dict(l=40, r=20, t=50, b=40))

    prob_profit = float(np.mean(terminal > last_price))
    expected_ret = float(np.mean(terminal / last_price - 1))

    return {
        'ticker': ticker,
        'current_price': f"${last_price:,.2f}",
        'n_simulations': n_simulations,
        'n_days': n_days,
        'mu_ann': f"{mu_daily * 252:.2%}",
        'sigma_ann': f"{sigma_daily * np.sqrt(252):.2%}",
        'median_terminal': f"${float(np.median(terminal)):,.2f}",
        'mean_terminal': f"${float(np.mean(terminal)):,.2f}",
        'p5_terminal': f"${float(np.percentile(terminal, 5)):,.2f}",
        'p95_terminal': f"${float(np.percentile(terminal, 95)):,.2f}",
        'prob_profit': f"{prob_profit:.1%}",
        'expected_return': f"{expected_ret:.2%}",
        'fan_chart': fig.to_html(full_html=False, include_plotlyjs=False),
        'hist_chart': fig_hist.to_html(full_html=False, include_plotlyjs=False),
    }

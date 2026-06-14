import re
import numpy as np
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from scipy.optimize import minimize


def plot_frontier(tickers, start_date, end_date, n_points=80):
    for t in tickers:
        if not re.match(r'^[\^]?[A-Z0-9.\-=]{1,20}$', t):
            raise ValueError(f"Invalid ticker: {t}")
    if len(tickers) < 2:
        raise ValueError("Need at least 2 tickers.")

    prices = yf.download(tickers, start=start_date, end=end_date)['Close']
    if isinstance(prices, pd.Series):
        raise ValueError("Only got data for one ticker.")
    returns = prices.pct_change().dropna()
    if len(returns) < 30:
        raise ValueError("Not enough data. Try a wider date range.")

    tickers_sorted = list(returns.columns)
    n = len(tickers_sorted)
    mu = returns.mean().values * 252
    cov = returns.cov().values * 252

    # --- individual assets ---
    asset_vols = np.sqrt(np.diag(cov))

    # --- efficient frontier via optimisation ---
    def port_vol(w):
        return np.sqrt(w @ cov @ w)

    def port_ret(w):
        return w @ mu

    constraints = [{'type': 'eq', 'fun': lambda w: np.sum(w) - 1}]
    bounds = tuple((0, 1) for _ in range(n))

    # find min-vol and max-return anchor points
    res_min = minimize(port_vol, np.ones(n) / n, method='SLSQP',
                       bounds=bounds, constraints=constraints)
    w_min = res_min.x
    ret_min = port_ret(w_min)

    ret_max = mu.max()
    target_rets = np.linspace(ret_min, ret_max, n_points)

    front_vols, front_rets, front_sharpes = [], [], []

    for tr in target_rets:
        c = constraints + [{'type': 'eq', 'fun': lambda w, r=tr: port_ret(w) - r}]
        res = minimize(port_vol, np.ones(n) / n, method='SLSQP',
                       bounds=bounds, constraints=c)
        if res.success:
            v = port_vol(res.x)
            front_vols.append(v)
            front_rets.append(tr)
            front_sharpes.append(tr / v if v > 0 else 0)

    # max Sharpe portfolio
    best_idx = int(np.argmax(front_sharpes))
    msr_vol, msr_ret = front_vols[best_idx], front_rets[best_idx]

    # re-solve for max-Sharpe weights
    c_msr = constraints + [{'type': 'eq', 'fun': lambda w: port_ret(w) - msr_ret}]
    res_msr = minimize(port_vol, np.ones(n) / n, method='SLSQP',
                       bounds=bounds, constraints=c_msr)
    msr_weights = res_msr.x

    # equal-weight portfolio
    eq_w = np.ones(n) / n
    eq_vol = port_vol(eq_w)
    eq_ret = port_ret(eq_w)

    # --- chart ---
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=front_vols, y=front_rets, mode='lines',
        name='Efficient Frontier',
        line=dict(width=3, color='royalblue')))

    fig.add_trace(go.Scatter(
        x=asset_vols.tolist(), y=mu.tolist(), mode='markers+text',
        text=tickers_sorted, textposition='top center',
        name='Individual Assets',
        marker=dict(size=10, color='gray')))

    fig.add_trace(go.Scatter(
        x=[msr_vol], y=[msr_ret], mode='markers',
        name=f'Max Sharpe ({msr_ret:.1%} ret, {msr_vol:.1%} vol)',
        marker=dict(size=14, symbol='star', color='gold',
                    line=dict(width=1, color='black'))))

    fig.add_trace(go.Scatter(
        x=[eq_vol], y=[eq_ret], mode='markers',
        name=f'Equal Weight ({eq_ret:.1%} ret, {eq_vol:.1%} vol)',
        marker=dict(size=12, symbol='diamond', color='crimson',
                    line=dict(width=1, color='black'))))

    fig.add_trace(go.Scatter(
        x=[port_vol(w_min)], y=[ret_min], mode='markers',
        name=f'Min Variance ({ret_min:.1%} ret)',
        marker=dict(size=12, symbol='square', color='forestgreen',
                    line=dict(width=1, color='black'))))

    fig.update_layout(
        title='Efficient Frontier (Mean-Variance)',
        xaxis_title='Annualized Volatility',
        yaxis_title='Annualized Return',
        template='plotly_white', height=550,
        margin=dict(l=40, r=20, t=50, b=40),
        xaxis_tickformat='.1%', yaxis_tickformat='.1%',
        legend=dict(yanchor='top', y=0.99, xanchor='left', x=0.01))

    # --- weights table ---
    weights = [{'ticker': t, 'weight': f"{w:.2%}"} for t, w in zip(tickers_sorted, msr_weights)]

    return {
        'frontier_chart': fig.to_html(full_html=False, include_plotlyjs=False),
        'msr_return': f"{msr_ret:.2%}",
        'msr_vol': f"{msr_vol:.2%}",
        'msr_sharpe': f"{msr_ret / msr_vol:.2f}" if msr_vol > 0 else "N/A",
        'eq_return': f"{eq_ret:.2%}",
        'eq_vol': f"{eq_vol:.2%}",
        'minvar_return': f"{ret_min:.2%}",
        'minvar_vol': f"{port_vol(w_min):.2%}",
        'weights': weights,
        'n_assets': n,
        'n_days': len(returns),
    }

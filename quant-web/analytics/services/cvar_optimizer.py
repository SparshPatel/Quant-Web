import re
import numpy as np
import pandas as pd
import yfinance as yf
import cvxpy as cp
import plotly.graph_objects as go


def validate_ticker(ticker):
    return bool(re.match(r'^[\^]?[A-Z0-9.\-=]{1,20}$', ticker.upper()))


def optimize_cvar(tickers, start_date, end_date, alpha=0.05):
    for t in tickers:
        if not validate_ticker(t):
            raise ValueError(f"Invalid ticker symbol: {t}")

    if len(tickers) < 2:
        raise ValueError("Need at least 2 tickers for portfolio optimization.")

    prices = yf.download(tickers, start=start_date, end=end_date)['Close']
    if isinstance(prices, pd.Series):
        raise ValueError("Only got data for one ticker. Check symbols and date range.")

    returns = prices.pct_change().dropna()
    if len(returns) < 30:
        raise ValueError("Not enough data points. Try a wider date range.")

    tickers_sorted = list(returns.columns)
    n_assets = len(tickers_sorted)
    n_days = len(returns)
    R = returns.values

    # Decision variables
    w = cp.Variable(n_assets)
    gamma = cp.Variable()
    z = cp.Variable(n_days)

    portfolio_loss = -R @ w

    constraints = [
        z >= portfolio_loss - gamma,
        z >= 0,
        cp.sum(w) == 1,
        w >= 0,
    ]

    cvar = gamma + (1.0 / (alpha * n_days)) * cp.sum(z)
    problem = cp.Problem(cp.Minimize(cvar), constraints)
    problem.solve()

    if problem.status != 'optimal':
        raise ValueError(f"Optimization failed with status: {problem.status}")

    optimal_w = w.value

    # Equal-weight benchmark
    eq_w = np.ones(n_assets) / n_assets
    cvar_rets = R @ optimal_w
    eq_rets = R @ eq_w

    cvar_cum = (1 + pd.Series(cvar_rets, index=returns.index)).cumprod()
    eq_cum = (1 + pd.Series(eq_rets, index=returns.index)).cumprod()

    # Risk metrics
    def _risk(rets):
        var = np.percentile(rets, alpha * 100)
        cvar_val = rets[rets <= var].mean()
        return var, cvar_val

    var_opt, cvar_opt = _risk(cvar_rets)
    var_eq, cvar_eq = _risk(eq_rets)

    metrics = {
        'ann_return_opt': f"{cvar_rets.mean() * 252:.2%}",
        'ann_return_eq': f"{eq_rets.mean() * 252:.2%}",
        'ann_vol_opt': f"{cvar_rets.std() * np.sqrt(252):.2%}",
        'ann_vol_eq': f"{eq_rets.std() * np.sqrt(252):.2%}",
        'sharpe_opt': f"{cvar_rets.mean() / cvar_rets.std() * np.sqrt(252):.2f}",
        'sharpe_eq': f"{eq_rets.mean() / eq_rets.std() * np.sqrt(252):.2f}",
        'var_opt': f"{var_opt:.4f}",
        'var_eq': f"{var_eq:.4f}",
        'cvar_opt': f"{cvar_opt:.4f}",
        'cvar_eq': f"{cvar_eq:.4f}",
    }

    weights = [(t, f"{wt:.4f}") for t, wt in zip(tickers_sorted, optimal_w)]

    # Cumulative returns chart
    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(
        x=cvar_cum.index, y=cvar_cum.values,
        name='CVaR Optimized', line=dict(width=1.5)))
    fig1.add_trace(go.Scatter(
        x=eq_cum.index, y=eq_cum.values,
        name='Equal Weight', line=dict(width=1.5, dash='dash')))
    fig1.update_layout(
        title='CVaR Optimized vs Equal Weight Portfolio',
        xaxis_title='Date', yaxis_title='Growth of $1',
        template='plotly_white', height=450, margin=dict(l=40, r=20, t=50, b=40))

    # Weight comparison chart
    fig2 = go.Figure()
    fig2.add_trace(go.Bar(x=tickers_sorted, y=optimal_w, name='CVaR Optimized'))
    fig2.add_trace(go.Bar(x=tickers_sorted, y=[1 / n_assets] * n_assets, name='Equal Weight'))
    fig2.update_layout(
        title='Portfolio Weight Comparison', barmode='group',
        xaxis_title='Asset', yaxis_title='Weight',
        template='plotly_white', height=400, margin=dict(l=40, r=20, t=50, b=40))

    return {
        'weights': weights,
        'metrics': metrics,
        'cumulative_chart': fig1.to_html(full_html=False, include_plotlyjs=False),
        'weights_chart': fig2.to_html(full_html=False, include_plotlyjs=False),
        'optimal_cvar': f"{problem.value:.6f}",
        'n_days': n_days,
        'date_range': f"{returns.index[0].date()} to {returns.index[-1].date()}",
    }

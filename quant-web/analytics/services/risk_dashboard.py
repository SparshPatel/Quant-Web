import re
import numpy as np
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def validate_ticker(ticker):
    return bool(re.match(r'^[\^]?[A-Z0-9.\-=]{1,20}$', ticker.upper()))


def analyze_risk(tickers, start_date, end_date, confidence=0.95):
    for t in tickers:
        if not validate_ticker(t):
            raise ValueError(f"Invalid ticker symbol: {t}")

    if len(tickers) < 2:
        raise ValueError("Need at least 2 tickers for risk analysis.")

    prices = yf.download(tickers, start=start_date, end=end_date)['Close']
    if isinstance(prices, pd.Series):
        raise ValueError("Only got data for one ticker. Check symbols and date range.")

    returns = prices.pct_change().dropna()
    if len(returns) < 30:
        raise ValueError("Not enough data points. Try a wider date range.")

    tickers_sorted = list(returns.columns)
    n = len(tickers_sorted)
    alpha = 1 - confidence

    # Equal-weight portfolio
    eq_w = np.ones(n) / n
    port_returns = returns.values @ eq_w

    # --- VaR & CVaR ---
    var_hist = np.percentile(port_returns, alpha * 100)
    cvar_hist = port_returns[port_returns <= var_hist].mean()

    # Parametric VaR (Gaussian)
    mu = port_returns.mean()
    sigma = port_returns.std()
    from scipy.stats import norm
    var_param = mu + sigma * norm.ppf(alpha)

    # --- Correlation matrix ---
    corr = returns.corr()

    fig_corr = go.Figure(data=go.Heatmap(
        z=corr.values, x=tickers_sorted, y=tickers_sorted,
        colorscale='RdBu_r', zmin=-1, zmax=1, text=np.round(corr.values, 2),
        texttemplate='%{text:.2f}', textfont=dict(size=11)))
    fig_corr.update_layout(
        title='Correlation Matrix',
        template='plotly_white', height=450,
        margin=dict(l=40, r=20, t=50, b=40))

    # --- Rolling volatility ---
    rolling_vol = pd.Series(port_returns, index=returns.index).rolling(21).std() * np.sqrt(252)

    fig_vol = go.Figure()
    fig_vol.add_trace(go.Scatter(
        x=rolling_vol.index, y=rolling_vol.values,
        mode='lines', line=dict(width=1), name='21-Day Rolling Vol'))
    fig_vol.update_layout(
        title='Portfolio Rolling Volatility (Annualized)',
        xaxis_title='Date', yaxis_title='Volatility',
        template='plotly_white', height=350,
        margin=dict(l=40, r=20, t=50, b=40))

    # --- Drawdown ---
    cum = (1 + pd.Series(port_returns, index=returns.index)).cumprod()
    drawdown = cum / cum.cummax() - 1

    fig_dd = go.Figure()
    fig_dd.add_trace(go.Scatter(
        x=drawdown.index, y=drawdown.values,
        mode='lines', fill='tozeroy',
        line=dict(width=1, color='crimson'),
        fillcolor='rgba(220,20,60,0.15)', name='Drawdown'))
    fig_dd.update_layout(
        title='Portfolio Drawdown',
        xaxis_title='Date', yaxis_title='Drawdown',
        template='plotly_white', height=350,
        margin=dict(l=40, r=20, t=50, b=40))

    # --- Return distribution ---
    fig_dist = go.Figure()
    fig_dist.add_trace(go.Histogram(
        x=port_returns, nbinsx=80, name='Daily Returns',
        marker_color='steelblue', opacity=0.75))
    fig_dist.add_vline(x=var_hist, line_dash='dash', line_color='red',
                       annotation_text=f'VaR {confidence:.0%}: {var_hist:.4f}')
    fig_dist.update_layout(
        title='Return Distribution',
        xaxis_title='Daily Return', yaxis_title='Frequency',
        template='plotly_white', height=350,
        margin=dict(l=40, r=20, t=50, b=40))

    # --- Per-asset stats ---
    asset_stats = []
    for t in tickers_sorted:
        r = returns[t]
        asset_stats.append({
            'ticker': t,
            'ann_return': f"{r.mean() * 252:.2%}",
            'ann_vol': f"{r.std() * np.sqrt(252):.2%}",
            'sharpe': f"{r.mean() / r.std() * np.sqrt(252):.2f}" if r.std() > 0 else "N/A",
            'max_dd': f"{(((1 + r).cumprod() / (1 + r).cumprod().cummax()) - 1).min():.2%}",
            'skew': f"{r.skew():.2f}",
            'kurtosis': f"{r.kurtosis():.2f}",
        })

    max_dd_val = drawdown.min()

    return {
        'n_assets': n,
        'n_days': len(returns),
        'date_range': f"{returns.index[0].date()} to {returns.index[-1].date()}",
        'ann_return': f"{mu * 252:.2%}",
        'ann_vol': f"{sigma * np.sqrt(252):.2%}",
        'sharpe': f"{mu / sigma * np.sqrt(252):.2f}" if sigma > 0 else "N/A",
        'var_hist': f"{var_hist:.4f}",
        'var_param': f"{var_param:.4f}",
        'cvar': f"{cvar_hist:.4f}",
        'max_drawdown': f"{max_dd_val:.2%}",
        'confidence': f"{confidence:.0%}",
        'asset_stats': asset_stats,
        'corr_chart': fig_corr.to_html(full_html=False, include_plotlyjs=False),
        'vol_chart': fig_vol.to_html(full_html=False, include_plotlyjs=False),
        'dd_chart': fig_dd.to_html(full_html=False, include_plotlyjs=False),
        'dist_chart': fig_dist.to_html(full_html=False, include_plotlyjs=False),
    }

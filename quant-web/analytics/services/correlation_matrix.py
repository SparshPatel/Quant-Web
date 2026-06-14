import re
import numpy as np
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go


def build_correlation(tickers, start_date, end_date):
    for t in tickers:
        if not re.match(r'^[\^]?[A-Z0-9.\-=]{1,20}$', t):
            raise ValueError(f"Invalid ticker: {t}")
    if len(tickers) < 2:
        raise ValueError("Need at least 2 tickers.")

    prices = yf.download(tickers, start=start_date, end=end_date)['Close']
    if isinstance(prices, pd.Series):
        raise ValueError("Only got data for one ticker.")
    returns = prices.pct_change().dropna()
    if len(returns) < 20:
        raise ValueError("Not enough data.")

    tickers_sorted = list(returns.columns)
    corr = returns.corr()

    # --- heatmap ---
    fig_heat = go.Figure(data=go.Heatmap(
        z=corr.values, x=tickers_sorted, y=tickers_sorted,
        colorscale='RdBu_r', zmin=-1, zmax=1,
        text=np.round(corr.values, 2),
        texttemplate='%{text:.2f}', textfont=dict(size=10)))
    fig_heat.update_layout(
        title='Correlation Matrix',
        template='plotly_white', height=max(400, 50 * len(tickers_sorted)),
        margin=dict(l=40, r=20, t=50, b=40))

    # --- top & bottom pairs ---
    pairs = []
    for i in range(len(tickers_sorted)):
        for j in range(i + 1, len(tickers_sorted)):
            pairs.append({
                'pair': f"{tickers_sorted[i]} / {tickers_sorted[j]}",
                'corr': corr.iloc[i, j],
                'corr_fmt': f"{corr.iloc[i, j]:.4f}",
            })
    pairs.sort(key=lambda x: x['corr'], reverse=True)

    # --- dendrogram-style clustered order ---
    # simple bar chart of avg correlations
    avg_corr = corr.mean()
    fig_bar = go.Figure(data=[
        go.Bar(x=avg_corr.index.tolist(), y=avg_corr.values,
               marker_color=['royalblue' if v > 0 else 'crimson' for v in avg_corr.values],
               text=[f"{v:.2f}" for v in avg_corr.values], textposition='outside')])
    fig_bar.update_layout(
        title='Average Correlation per Asset',
        yaxis_title='Avg Correlation',
        template='plotly_white', height=350,
        margin=dict(l=40, r=20, t=50, b=40))

    return {
        'n_assets': len(tickers_sorted),
        'n_days': len(returns),
        'date_range': f"{returns.index[0].date()} to {returns.index[-1].date()}",
        'top_pairs': pairs[:5],
        'bottom_pairs': pairs[-5:][::-1],
        'heatmap_chart': fig_heat.to_html(full_html=False, include_plotlyjs=False),
        'bar_chart': fig_bar.to_html(full_html=False, include_plotlyjs=False),
    }

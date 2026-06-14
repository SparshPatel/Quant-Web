import re
import numpy as np
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go


def validate_ticker(ticker):
    return bool(re.match(r'^[\^]?[A-Z0-9.\-=]{1,20}$', ticker.upper()))


def attribute_returns(tickers, benchmark_ticker, weights, start_date, end_date):
    """
    Brinson-Fachler style return attribution.

    Parameters
    ----------
    tickers : list[str]        – portfolio stocks
    benchmark_ticker : str      – e.g. 'SPY'
    weights : list[float]       – portfolio weights (sum ≈ 1)
    start_date, end_date : str

    Returns dict with attribution breakdown and charts.
    """
    for t in tickers + [benchmark_ticker]:
        if not validate_ticker(t):
            raise ValueError(f"Invalid ticker: {t}")

    n = len(tickers)
    w = np.array(weights, dtype=float)
    if abs(w.sum() - 1.0) > 0.05:
        raise ValueError("Weights must sum to approximately 1.")
    w = w / w.sum()

    # Download all data
    all_tickers = tickers + [benchmark_ticker]
    prices = yf.download(all_tickers, start=start_date, end=end_date)['Close']
    if isinstance(prices, pd.Series):
        prices = prices.to_frame(all_tickers[0])

    # Total period returns
    total_returns = {}
    for t in all_tickers:
        if t in prices.columns:
            col = prices[t].dropna()
            if len(col) >= 2:
                total_returns[t] = col.iloc[-1] / col.iloc[0] - 1

    if benchmark_ticker not in total_returns:
        raise ValueError(f"No data for benchmark {benchmark_ticker}.")

    bench_return = total_returns[benchmark_ticker]

    # Fetch sector info for each holding
    sectors = {}
    for t in tickers:
        try:
            info = yf.Ticker(t).info or {}
            sectors[t] = info.get('sector', 'Unknown')
        except Exception:
            sectors[t] = 'Unknown'

    # Per-stock attribution
    attr_data = []
    portfolio_return = 0
    for i, t in enumerate(tickers):
        stock_ret = total_returns.get(t, 0)
        weighted_ret = w[i] * stock_ret
        portfolio_return += weighted_ret

        # Selection effect: how much this stock over/under-performed benchmark
        selection = w[i] * (stock_ret - bench_return)

        attr_data.append({
            'ticker': t,
            'sector': sectors.get(t, 'Unknown'),
            'weight': f"{w[i]*100:.1f}%",
            'return': f"{stock_ret*100:+.1f}%",
            'weighted_return': f"{weighted_ret*100:+.2f}%",
            'selection': f"{selection*100:+.2f}%",
            'return_raw': stock_ret,
            'selection_raw': selection,
        })

    active_return = portfolio_return - bench_return

    # ---------- Charts ----------
    # Waterfall-style attribution
    fig_attr = go.Figure()
    tickers_sorted = [d['ticker'] for d in attr_data]
    selections = [d['selection_raw'] * 100 for d in attr_data]
    colors = ['#28a745' if s > 0 else '#dc3545' for s in selections]
    fig_attr.add_trace(go.Bar(
        x=tickers_sorted, y=selections, marker_color=colors,
        text=[f"{s:+.2f}%" for s in selections], textposition='outside'))
    fig_attr.update_layout(
        title='Selection Effect by Holding',
        yaxis_title='Contribution (%)',
        template='plotly_white', height=400,
        margin=dict(l=40, r=20, t=50, b=40))
    attr_chart = fig_attr.to_html(full_html=False, include_plotlyjs=False)

    # Portfolio vs benchmark cumulative
    returns_df = prices.pct_change().dropna()
    port_daily = np.zeros(len(returns_df))
    for i, t in enumerate(tickers):
        if t in returns_df.columns:
            port_daily += w[i] * returns_df[t].values

    cum_port = (1 + pd.Series(port_daily, index=returns_df.index)).cumprod()
    cum_bench = (1 + returns_df[benchmark_ticker]).cumprod()

    fig_cum = go.Figure()
    fig_cum.add_trace(go.Scatter(
        x=cum_port.index, y=(cum_port - 1) * 100,
        mode='lines', name='Portfolio', line=dict(width=2)))
    fig_cum.add_trace(go.Scatter(
        x=cum_bench.index, y=(cum_bench - 1) * 100,
        mode='lines', name=benchmark_ticker, line=dict(width=2, dash='dash')))
    fig_cum.update_layout(
        title='Portfolio vs Benchmark Cumulative Return',
        xaxis_title='Date', yaxis_title='Cumulative Return (%)',
        template='plotly_white', height=400,
        margin=dict(l=40, r=20, t=50, b=40))
    cum_chart = fig_cum.to_html(full_html=False, include_plotlyjs=False)

    return {
        'attr_data': attr_data,
        'portfolio_return': f"{portfolio_return*100:+.2f}%",
        'benchmark_return': f"{bench_return*100:+.2f}%",
        'active_return': f"{active_return*100:+.2f}%",
        'benchmark_ticker': benchmark_ticker,
        'attr_chart': attr_chart,
        'cum_chart': cum_chart,
    }

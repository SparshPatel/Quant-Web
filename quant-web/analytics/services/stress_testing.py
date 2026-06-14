import re
import numpy as np
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def validate_ticker(ticker):
    return bool(re.match(r'^[\^]?[A-Z0-9.\-=]{1,20}$', ticker.upper()))


# Pre-defined historical crisis windows
CRISIS_SCENARIOS = {
    'gfc_2008': {
        'label': '2008 Global Financial Crisis',
        'start': '2007-10-01',
        'end': '2009-03-31',
    },
    'euro_debt_2011': {
        'label': '2011 Euro Debt Crisis',
        'start': '2011-07-01',
        'end': '2012-01-31',
    },
    'covid_2020': {
        'label': 'COVID-19 Crash (2020)',
        'start': '2020-02-01',
        'end': '2020-04-30',
    },
    'rate_hike_2022': {
        'label': '2022 Rate Hike Sell-off',
        'start': '2022-01-01',
        'end': '2022-10-31',
    },
    'dot_com_2000': {
        'label': 'Dot-Com Crash (2000-02)',
        'start': '2000-03-01',
        'end': '2002-10-31',
    },
}


def stress_test(tickers, scenarios=None, custom_shocks=None):
    """
    Replay historical crises on a portfolio and/or apply custom shocks.

    Parameters
    ----------
    tickers : list[str]
    scenarios : list[str] – keys from CRISIS_SCENARIOS
    custom_shocks : dict   – {'equity': -0.30, 'rate_change': 0.02, ...}

    Returns dict with scenario results and charts.
    """
    for t in tickers:
        if not validate_ticker(t):
            raise ValueError(f"Invalid ticker: {t}")
    if not scenarios and not custom_shocks:
        raise ValueError("Select at least one crisis scenario or define custom shocks.")

    n = len(tickers)
    results_table = []
    scenario_charts = []

    # Historical scenario replays
    selected = scenarios or []
    for key in selected:
        if key not in CRISIS_SCENARIOS:
            continue
        info = CRISIS_SCENARIOS[key]
        try:
            prices = yf.download(tickers, start=info['start'], end=info['end'])['Close']
            if isinstance(prices, pd.Series):
                prices = prices.to_frame(tickers[0])
            if prices.empty or len(prices) < 5:
                results_table.append({
                    'scenario': info['label'],
                    'portfolio_return': 'N/A (no data)',
                    'max_drawdown': 'N/A',
                    'worst_day': 'N/A',
                    'recovery_note': 'Insufficient data for this period',
                })
                continue

            returns = prices.pct_change().dropna()
            # Equal-weight portfolio
            eq_w = np.ones(n) / n
            port_ret = returns.values @ eq_w
            cum = (1 + pd.Series(port_ret, index=returns.index)).cumprod()
            total_ret = cum.iloc[-1] / cum.iloc[0] - 1
            drawdown = cum / cum.cummax() - 1
            max_dd = drawdown.min()
            worst_day = pd.Series(port_ret, index=returns.index).min()

            results_table.append({
                'scenario': info['label'],
                'portfolio_return': f"{total_ret*100:+.1f}%",
                'max_drawdown': f"{max_dd*100:.1f}%",
                'worst_day': f"{worst_day*100:.2f}%",
                'recovery_note': f"{info['start']} → {info['end']}",
            })

            # Cumulative return chart for this scenario
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=cum.index, y=(cum / cum.iloc[0] - 1) * 100,
                mode='lines', line=dict(width=2),
                name='Portfolio'))
            fig.update_layout(
                title=info['label'],
                xaxis_title='Date', yaxis_title='Cumulative Return (%)',
                template='plotly_white', height=300,
                margin=dict(l=40, r=20, t=50, b=40))
            scenario_charts.append(fig.to_html(full_html=False, include_plotlyjs=False))
        except Exception:
            results_table.append({
                'scenario': info['label'],
                'portfolio_return': 'Error',
                'max_drawdown': 'N/A',
                'worst_day': 'N/A',
                'recovery_note': 'Could not fetch data',
            })

    # Custom shock analysis
    custom_result = None
    if custom_shocks:
        equity_shock = custom_shocks.get('equity_shock', 0)
        # Fetch recent data for vol scaling
        try:
            prices = yf.download(tickers, period='1y')['Close']
            if isinstance(prices, pd.Series):
                prices = prices.to_frame(tickers[0])
            returns = prices.pct_change().dropna()
            eq_w = np.ones(n) / n
            port_ret = returns.values @ eq_w
            ann_vol = np.std(port_ret) * np.sqrt(252)
            portfolio_value = custom_shocks.get('portfolio_value', 100000)
            dollar_loss = portfolio_value * equity_shock
            vol_scaled_loss = portfolio_value * equity_shock * (ann_vol / 0.16)

            custom_result = {
                'equity_shock': f"{equity_shock*100:+.0f}%",
                'dollar_loss': f"${dollar_loss:+,.0f}",
                'ann_vol': f"{ann_vol*100:.1f}%",
                'vol_scaled_loss': f"${vol_scaled_loss:+,.0f}",
                'portfolio_value': f"${portfolio_value:,.0f}",
            }
        except Exception as e:
            custom_result = {'error': str(e)}

    # Summary comparison chart
    if results_table:
        labels = [r['scenario'] for r in results_table if r['portfolio_return'] not in ('N/A (no data)', 'Error')]
        vals = []
        for r in results_table:
            try:
                vals.append(float(r['portfolio_return'].replace('%', '').replace('+', '')))
            except (ValueError, AttributeError):
                pass
        if labels and vals:
            colors = ['#28a745' if v > 0 else '#dc3545' for v in vals]
            fig_summary = go.Figure()
            fig_summary.add_trace(go.Bar(
                x=labels, y=vals, marker_color=colors,
                text=[f"{v:+.1f}%" for v in vals], textposition='outside'))
            fig_summary.update_layout(
                title='Portfolio Return Across Crisis Scenarios',
                yaxis_title='Total Return (%)',
                template='plotly_white', height=400,
                margin=dict(l=40, r=20, t=50, b=80))
            summary_chart = fig_summary.to_html(full_html=False, include_plotlyjs=False)
        else:
            summary_chart = None
    else:
        summary_chart = None

    return {
        'results_table': results_table,
        'scenario_charts': scenario_charts,
        'summary_chart': summary_chart,
        'custom_result': custom_result,
    }

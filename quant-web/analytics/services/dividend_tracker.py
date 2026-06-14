import re
import numpy as np
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def validate_ticker(ticker):
    return bool(re.match(r'^[\^]?[A-Z0-9.\-=]{1,20}$', ticker.upper()))


def analyze_dividends(tickers):
    """
    Fetch dividend history, yield, growth rate, and upcoming ex-dates.

    Returns dict with per-stock dividend data, income projection, and charts.
    """
    for t in tickers:
        if not validate_ticker(t):
            raise ValueError(f"Invalid ticker: {t}")

    holdings = []
    all_div_histories = {}

    for t in tickers:
        try:
            stock = yf.Ticker(t)
            info = stock.info or {}
            divs = stock.dividends
            if divs is not None and len(divs) > 0:
                divs = divs[divs > 0]

            price = info.get('currentPrice') or info.get('regularMarketPrice') or 0
            div_yield = info.get('dividendYield') or 0
            annual_div = info.get('dividendRate') or 0
            ex_date = info.get('exDividendDate')
            payout_ratio = info.get('payoutRatio') or 0

            # Calculate 5-year dividend growth rate
            growth_rate = None
            if divs is not None and len(divs) >= 8:
                # Annualise: sum each year
                annual = divs.resample('YE').sum()
                annual = annual[annual > 0]
                if len(annual) >= 2:
                    cagr = (annual.iloc[-1] / annual.iloc[0]) ** (1 / (len(annual) - 1)) - 1
                    growth_rate = cagr

            # Convert ex_date from epoch if needed
            ex_date_str = 'N/A'
            if ex_date:
                try:
                    ex_date_str = pd.Timestamp(ex_date, unit='s').strftime('%Y-%m-%d')
                except Exception:
                    ex_date_str = str(ex_date)

            holdings.append({
                'ticker': t,
                'name': info.get('shortName', t),
                'price': f"${price:,.2f}" if price else 'N/A',
                'div_yield': f"{div_yield*100:.2f}%" if div_yield else 'N/A',
                'annual_div': f"${annual_div:.2f}" if annual_div else 'N/A',
                'payout_ratio': f"{payout_ratio*100:.0f}%" if payout_ratio else 'N/A',
                'growth_rate': f"{growth_rate*100:.1f}%" if growth_rate is not None else 'N/A',
                'ex_date': ex_date_str,
            })

            if divs is not None and len(divs) > 0:
                all_div_histories[t] = divs

        except Exception:
            holdings.append({
                'ticker': t, 'name': t, 'price': 'N/A',
                'div_yield': 'N/A', 'annual_div': 'N/A',
                'payout_ratio': 'N/A', 'growth_rate': 'N/A',
                'ex_date': 'N/A',
            })

    # ---------- Yield comparison chart ----------
    valid = [h for h in holdings if h['div_yield'] != 'N/A']
    if valid:
        labels = [h['ticker'] for h in valid]
        yields = [float(h['div_yield'].replace('%', '')) for h in valid]
        fig_yield = go.Figure()
        fig_yield.add_trace(go.Bar(
            x=labels, y=yields,
            marker_color='#28a745',
            text=[f"{y:.2f}%" for y in yields],
            textposition='outside'))
        fig_yield.update_layout(
            title='Dividend Yield Comparison',
            yaxis_title='Yield (%)',
            template='plotly_white', height=350,
            margin=dict(l=40, r=20, t=50, b=40))
        yield_chart = fig_yield.to_html(full_html=False, include_plotlyjs=False)
    else:
        yield_chart = None

    # ---------- Dividend history chart ----------
    if all_div_histories:
        fig_hist = go.Figure()
        for t, divs in all_div_histories.items():
            annual = divs.resample('YE').sum()
            fig_hist.add_trace(go.Bar(
                x=annual.index.year, y=annual.values,
                name=t))
        fig_hist.update_layout(
            title='Annual Dividends per Share',
            xaxis_title='Year', yaxis_title='Dividend ($)',
            barmode='group',
            template='plotly_white', height=400,
            margin=dict(l=40, r=20, t=50, b=40))
        history_chart = fig_hist.to_html(full_html=False, include_plotlyjs=False)
    else:
        history_chart = None

    # ---------- Income projection (5-year) ----------
    projection_rows = []
    for h in holdings:
        if h['annual_div'] != 'N/A' and h['growth_rate'] != 'N/A':
            annual = float(h['annual_div'].replace('$', ''))
            gr = float(h['growth_rate'].replace('%', '')) / 100
            row = {'ticker': h['ticker'], 'years': []}
            for yr in range(1, 6):
                projected = annual * (1 + gr) ** yr
                row['years'].append(f"${projected:.2f}")
            projection_rows.append(row)

    return {
        'holdings': holdings,
        'yield_chart': yield_chart,
        'history_chart': history_chart,
        'projection_rows': projection_rows,
    }

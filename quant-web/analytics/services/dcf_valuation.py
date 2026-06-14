import re
import numpy as np
import yfinance as yf
import plotly.graph_objects as go


def validate_ticker(ticker):
    return bool(re.match(r'^[\^]?[A-Z0-9.\-=]{1,20}$', ticker.upper()))


def run_dcf(ticker_symbol, growth_rate=0.10, discount_rate=0.10,
            terminal_growth=0.03, projection_years=5):
    if not validate_ticker(ticker_symbol):
        raise ValueError(f"Invalid ticker symbol: {ticker_symbol}")

    if discount_rate <= terminal_growth:
        raise ValueError("Discount rate must be greater than terminal growth rate.")

    ticker = yf.Ticker(ticker_symbol)

    # Check that this is actually a stock with financials
    info = ticker.info
    quote_type = info.get('quoteType', 'UNKNOWN')
    if quote_type not in ('EQUITY', 'MUTUALFUND'):
        raise ValueError(
            f"'{ticker_symbol}' is a {quote_type.lower()}, not a stock. "
            f"DCF valuation only works for equities with financial statements."
        )

    # Get cash flow data
    cf = ticker.cashflow
    if cf is None or cf.empty:
        raise ValueError(
            f"No cash flow data available for '{ticker_symbol}'. "
            f"This may happen with recently listed companies or certain share classes (e.g. try BRK-B instead of BRK.B)."
        )

    # Try to get FCF directly first, then fall back to OCF - CapEx
    fcf = None

    # Method 1: Free Cash Flow directly from yfinance
    fcf_keys = ['Free Cash Flow']
    for key in fcf_keys:
        if key in cf.index:
            fcf = cf.loc[key].iloc[0]
            break

    # Method 2: Operating Cash Flow - Capital Expenditure
    if fcf is None:
        ocf_keys = ['Operating Cash Flow', 'Total Cash From Operating Activities',
                    'Cash Flow From Continuing Operating Activities']
        capex_keys = ['Capital Expenditure', 'Capital Expenditures', 'Purchase Of PPE']

        ocf = None
        for key in ocf_keys:
            if key in cf.index:
                ocf = cf.loc[key].iloc[0]
                break

        capex = 0
        for key in capex_keys:
            if key in cf.index:
                capex = abs(cf.loc[key].iloc[0])
                break

        if ocf is not None:
            fcf = ocf - capex

    if fcf is None:
        raise ValueError(
            f"Could not determine Free Cash Flow for '{ticker_symbol}'. "
            f"Available cashflow items: {', '.join(cf.index[:5])}..."
        )

    if fcf <= 0:
        raise ValueError(f"Negative FCF (${fcf:,.0f}). DCF may not be meaningful for this company.")

    # Project FCF
    projected_fcf = []
    for year in range(1, projection_years + 1):
        projected = fcf * (1 + growth_rate) ** year
        projected_fcf.append(projected)

    # Terminal value
    terminal_value = projected_fcf[-1] * (1 + terminal_growth) / (discount_rate - terminal_growth)

    # Discount back
    pv_fcf = sum(f / (1 + discount_rate) ** t for t, f in enumerate(projected_fcf, 1))
    pv_terminal = terminal_value / (1 + discount_rate) ** projection_years
    enterprise_value = pv_fcf + pv_terminal

    # Get shares outstanding and net debt
    shares = info.get('sharesOutstanding', None)
    if not shares:
        raise ValueError(f"Could not retrieve shares outstanding for {ticker_symbol}.")

    total_debt = info.get('totalDebt', 0) or 0
    cash = info.get('totalCash', 0) or 0
    net_debt = total_debt - cash

    equity_value = enterprise_value - net_debt
    intrinsic_value = equity_value / shares
    current_price = info.get('currentPrice', info.get('previousClose', 0))
    upside = (intrinsic_value - current_price) / current_price if current_price else 0

    # Waterfall chart
    fig1 = go.Figure(go.Waterfall(
        x=['PV of FCFs', 'PV of Terminal Value', 'Enterprise Value',
           'Less: Net Debt', 'Equity Value'],
        y=[pv_fcf, pv_terminal, 0, -net_debt, 0],
        measure=['relative', 'relative', 'total', 'relative', 'total'],
        textposition='outside',
        text=[f'${pv_fcf / 1e9:.1f}B', f'${pv_terminal / 1e9:.1f}B',
              f'${enterprise_value / 1e9:.1f}B', f'${-net_debt / 1e9:.1f}B',
              f'${equity_value / 1e9:.1f}B'],
        connector=dict(line=dict(color='rgb(63, 63, 63)')),
    ))
    fig1.update_layout(
        title=f'DCF Valuation Breakdown — {ticker_symbol}',
        yaxis_title='Value ($)',
        template='plotly_white', height=450, margin=dict(l=40, r=20, t=50, b=40))

    # Projected FCF bar chart
    years = list(range(1, projection_years + 1))
    fig2 = go.Figure()
    fig2.add_trace(go.Bar(
        x=[f'Year {y}' for y in years],
        y=projected_fcf,
        text=[f'${f / 1e9:.2f}B' for f in projected_fcf],
        textposition='outside',
        marker_color='steelblue'))
    fig2.update_layout(
        title='Projected Free Cash Flow',
        yaxis_title='FCF ($)',
        template='plotly_white', height=350, margin=dict(l=40, r=20, t=50, b=40))

    return {
        'company': info.get('shortName', ticker_symbol),
        'current_price': f"${current_price:,.2f}",
        'intrinsic_value': f"${intrinsic_value:,.2f}",
        'upside': f"{upside:.1%}",
        'verdict': 'Undervalued' if upside > 0.10 else ('Overvalued' if upside < -0.10 else 'Fairly Valued'),
        'fcf': f"${fcf / 1e9:,.2f}B",
        'enterprise_value': f"${enterprise_value / 1e9:,.2f}B",
        'equity_value': f"${equity_value / 1e9:,.2f}B",
        'net_debt': f"${net_debt / 1e9:,.2f}B",
        'shares': f"{shares / 1e9:,.2f}B",
        'waterfall_chart': fig1.to_html(full_html=False, include_plotlyjs=False),
        'fcf_chart': fig2.to_html(full_html=False, include_plotlyjs=False),
    }

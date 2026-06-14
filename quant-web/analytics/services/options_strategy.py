import re
import numpy as np
import pandas as pd
import yfinance as yf
from scipy.stats import norm
import plotly.graph_objects as go


def validate_ticker(ticker):
    return bool(re.match(r'^[\^]?[A-Z0-9.\-=]{1,20}$', ticker.upper()))


STRATEGY_PRESETS = {
    'long_call': [{'type': 'call', 'side': 'buy', 'strike_offset': 0, 'qty': 1}],
    'long_put': [{'type': 'put', 'side': 'buy', 'strike_offset': 0, 'qty': 1}],
    'covered_call': [
        {'type': 'stock', 'side': 'buy', 'strike_offset': 0, 'qty': 100},
        {'type': 'call', 'side': 'sell', 'strike_offset': 5, 'qty': 1},
    ],
    'bull_call_spread': [
        {'type': 'call', 'side': 'buy', 'strike_offset': 0, 'qty': 1},
        {'type': 'call', 'side': 'sell', 'strike_offset': 10, 'qty': 1},
    ],
    'bear_put_spread': [
        {'type': 'put', 'side': 'buy', 'strike_offset': 0, 'qty': 1},
        {'type': 'put', 'side': 'sell', 'strike_offset': -10, 'qty': 1},
    ],
    'straddle': [
        {'type': 'call', 'side': 'buy', 'strike_offset': 0, 'qty': 1},
        {'type': 'put', 'side': 'buy', 'strike_offset': 0, 'qty': 1},
    ],
    'strangle': [
        {'type': 'call', 'side': 'buy', 'strike_offset': 5, 'qty': 1},
        {'type': 'put', 'side': 'buy', 'strike_offset': -5, 'qty': 1},
    ],
    'iron_condor': [
        {'type': 'put', 'side': 'buy', 'strike_offset': -15, 'qty': 1},
        {'type': 'put', 'side': 'sell', 'strike_offset': -5, 'qty': 1},
        {'type': 'call', 'side': 'sell', 'strike_offset': 5, 'qty': 1},
        {'type': 'call', 'side': 'buy', 'strike_offset': 15, 'qty': 1},
    ],
    'butterfly': [
        {'type': 'call', 'side': 'buy', 'strike_offset': -10, 'qty': 1},
        {'type': 'call', 'side': 'sell', 'strike_offset': 0, 'qty': 2},
        {'type': 'call', 'side': 'buy', 'strike_offset': 10, 'qty': 1},
    ],
}

STRATEGY_LABELS = {
    'long_call': 'Long Call',
    'long_put': 'Long Put',
    'covered_call': 'Covered Call',
    'bull_call_spread': 'Bull Call Spread',
    'bear_put_spread': 'Bear Put Spread',
    'straddle': 'Long Straddle',
    'strangle': 'Long Strangle',
    'iron_condor': 'Iron Condor',
    'butterfly': 'Butterfly Spread',
}


def _bs_price(S, K, T, r, sigma, opt_type):
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    if opt_type == 'call':
        return S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    else:
        return K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)


def build_strategy(ticker_symbol, strategy_name, custom_strike=None):
    if not validate_ticker(ticker_symbol):
        raise ValueError(f"Invalid ticker symbol: {ticker_symbol}")

    if strategy_name not in STRATEGY_PRESETS:
        raise ValueError(f"Unknown strategy: {strategy_name}")

    ticker = yf.Ticker(ticker_symbol)
    spot = ticker.history(period='1d')['Close'].iloc[-1]
    base_strike = custom_strike if custom_strike else round(spot / 5) * 5

    r = 0.05
    T = 30 / 365  # 30-day options
    sigma = 0.30   # assume 30% vol (reasonable default)

    # Try to get actual IV from options chain
    expiries = ticker.options
    if expiries:
        try:
            chain = ticker.option_chain(expiries[0])
            atm_calls = chain.calls
            atm_calls = atm_calls[atm_calls['impliedVolatility'] > 0]
            if not atm_calls.empty:
                closest = atm_calls.iloc[(atm_calls['strike'] - spot).abs().argsort()[:1]]
                sigma = float(closest['impliedVolatility'].iloc[0])
        except Exception:
            pass

    legs = STRATEGY_PRESETS[strategy_name]
    leg_details = []
    total_cost = 0

    for leg in legs:
        strike = base_strike + leg['strike_offset']
        qty = leg['qty']
        side = leg['side']

        if leg['type'] == 'stock':
            premium = spot
            cost = premium * qty * (1 if side == 'buy' else -1)
            leg_details.append({
                'type': 'Stock',
                'side': side.capitalize(),
                'strike': '-',
                'qty': qty,
                'premium': f"${premium:.2f}",
                'cost': f"${cost:,.2f}",
            })
        else:
            premium = _bs_price(spot, strike, T, r, sigma, leg['type'])
            cost = premium * 100 * qty * (1 if side == 'buy' else -1)
            leg_details.append({
                'type': f"{leg['type'].capitalize()}",
                'side': side.capitalize(),
                'strike': f"${strike:.0f}",
                'qty': qty,
                'premium': f"${premium:.2f}",
                'cost': f"${cost:,.2f}",
            })

        total_cost += cost

    # Payoff diagram
    price_range = np.linspace(spot * 0.7, spot * 1.3, 300)
    payoff = np.zeros_like(price_range)

    for leg in legs:
        strike = base_strike + leg['strike_offset']
        qty = leg['qty']
        sign = 1 if leg['side'] == 'buy' else -1

        if leg['type'] == 'stock':
            payoff += sign * qty * (price_range - spot)
        elif leg['type'] == 'call':
            premium = _bs_price(spot, strike, T, r, sigma, 'call')
            intrinsic = np.maximum(price_range - strike, 0)
            payoff += sign * qty * 100 * (intrinsic - premium)
        elif leg['type'] == 'put':
            premium = _bs_price(spot, strike, T, r, sigma, 'put')
            intrinsic = np.maximum(strike - price_range, 0)
            payoff += sign * qty * 100 * (intrinsic - premium)

    max_profit = payoff.max()
    max_loss = payoff.min()
    breakevens = []
    for i in range(len(payoff) - 1):
        if payoff[i] * payoff[i + 1] < 0:
            x = price_range[i] - payoff[i] * (price_range[i + 1] - price_range[i]) / (payoff[i + 1] - payoff[i])
            breakevens.append(x)

    # Payoff chart
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=price_range, y=payoff, mode='lines',
        line=dict(width=2, color='steelblue'), name='P&L at Expiry'))

    fig.add_hline(y=0, line_color='black', line_width=0.5)
    fig.add_vline(x=spot, line_dash='dash', line_color='red',
                  annotation_text=f'Spot ${spot:.0f}')

    for be in breakevens:
        fig.add_vline(x=be, line_dash='dot', line_color='gray',
                      annotation_text=f'BE ${be:.1f}')

    # Color fill
    fig.add_trace(go.Scatter(
        x=price_range[payoff >= 0], y=payoff[payoff >= 0],
        fill='tozeroy', mode='none', fillcolor='rgba(0,200,0,0.15)',
        name='Profit', showlegend=False))
    fig.add_trace(go.Scatter(
        x=price_range[payoff < 0], y=payoff[payoff < 0],
        fill='tozeroy', mode='none', fillcolor='rgba(200,0,0,0.15)',
        name='Loss', showlegend=False))

    fig.update_layout(
        title=f'{STRATEGY_LABELS[strategy_name]} — {ticker_symbol} (Spot: ${spot:.2f})',
        xaxis_title='Stock Price at Expiry ($)',
        yaxis_title='Profit / Loss ($)',
        template='plotly_white', height=500,
        margin=dict(l=40, r=20, t=50, b=40))

    return {
        'strategy_label': STRATEGY_LABELS[strategy_name],
        'spot': f"${spot:.2f}",
        'iv_used': f"{sigma:.1%}",
        'days_to_expiry': 30,
        'legs': leg_details,
        'total_cost': f"${total_cost:,.2f}",
        'max_profit': f"${max_profit:,.2f}" if max_profit < 1e8 else 'Unlimited',
        'max_loss': f"${max_loss:,.2f}",
        'breakevens': [f"${be:.2f}" for be in breakevens],
        'payoff_chart': fig.to_html(full_html=False, include_plotlyjs=False),
    }

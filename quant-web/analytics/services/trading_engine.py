"""
Simulation Trading Engine
Executes paper trades, manages positions, calculates P&L, provides live data.
"""
import yfinance as yf
import pandas as pd
import numpy as np
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timedelta
from django.utils import timezone


def get_live_quote(ticker):
    """Get real-time quote for a ticker."""
    try:
        t = yf.Ticker(ticker)
        info = t.fast_info
        hist = t.history(period='2d', interval='1m')
        if hist.empty:
            hist = t.history(period='5d')

        current = float(info.get('lastPrice', 0) or 0)
        prev_close = float(info.get('previousClose', 0) or 0)
        if current == 0 and not hist.empty:
            current = float(hist['Close'].iloc[-1])

        change = current - prev_close if prev_close else 0
        change_pct = (change / prev_close * 100) if prev_close else 0

        return {
            'ticker': ticker,
            'price': current,
            'prev_close': prev_close,
            'change': round(change, 2),
            'change_pct': round(change_pct, 2),
            'volume': int(info.get('lastVolume', 0) or 0),
            'day_high': float(info.get('dayHigh', 0) or 0),
            'day_low': float(info.get('dayLow', 0) or 0),
            'market_cap': float(info.get('marketCap', 0) or 0),
            'bid': current,   # Simplified — yfinance doesn't always give bid/ask
            'ask': current,
            'open': float(info.get('open', 0) or 0),
        }
    except Exception as e:
        return {
            'ticker': ticker,
            'price': 0,
            'error': str(e)
        }


def get_batch_quotes(tickers):
    """Fetch current prices for multiple tickers efficiently."""
    if not tickers:
        return {}
    try:
        data = yf.download(tickers, period='1d', progress=False)
        if data.empty:
            return {}
        prices = {}
        close = data['Close']
        if isinstance(close, pd.DataFrame):
            if len(tickers) == 1:
                prices[tickers[0]] = float(close.iloc[-1, 0])
            else:
                for t in tickers:
                    if t in close.columns:
                        val = close[t].iloc[-1]
                        if pd.notna(val):
                            prices[t] = float(val)
        else:
            prices[tickers[0]] = float(close.iloc[-1])
        return prices
    except Exception:
        return {}


def get_chart_data(ticker, period='1d', interval='5m'):
    """Get OHLCV data for candlestick charts."""
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period=period, interval=interval)
        if hist.empty:
            return None

        return {
            'dates': hist.index.strftime('%Y-%m-%d %H:%M').tolist(),
            'open': hist['Open'].round(2).tolist(),
            'high': hist['High'].round(2).tolist(),
            'low': hist['Low'].round(2).tolist(),
            'close': hist['Close'].round(2).tolist(),
            'volume': hist['Volume'].tolist(),
        }
    except Exception:
        return None


def execute_market_order(account, ticker, side, quantity, asset_type='stock',
                         option_type='', strike_price=None, expiry_date=None,
                         contract_size=1):
    """Execute a market order immediately at current price."""
    from portfolio.models import Order, Trade, Position

    quote = get_live_quote(ticker)
    if not quote.get('price') or quote['price'] <= 0:
        return {'success': False, 'error': f'Could not get price for {ticker}'}

    price = Decimal(str(quote['price']))
    qty = Decimal(str(quantity))

    # Determine multiplier
    multiplier = Decimal(str(contract_size)) if asset_type in ('option', 'future') else Decimal('1')

    # Cost check for buys
    total_cost = qty * price * multiplier
    if side == 'buy' and total_cost > account.cash_balance:
        return {'success': False, 'error': f'Insufficient funds. Need ${total_cost:,.2f}, have ${account.cash_balance:,.2f}'}

    # Create and fill order
    order = Order.objects.create(
        account=account,
        ticker=ticker.upper(),
        asset_type=asset_type,
        order_type='market',
        side=side,
        quantity=qty,
        filled_price=price,
        status='filled',
        option_type=option_type,
        strike_price=strike_price,
        expiry_date=expiry_date,
        filled_at=timezone.now(),
    )

    # Create trade record
    Trade.objects.create(
        account=account,
        order=order,
        ticker=ticker.upper(),
        side=side,
        quantity=qty,
        price=price,
    )

    # Update cash balance
    if side == 'buy':
        account.cash_balance -= total_cost
        position_side = 'long'
    else:
        account.cash_balance += total_cost
        position_side = 'short'
    account.save()

    # Create or update position
    _update_position(account, ticker.upper(), position_side, qty, price,
                     asset_type, option_type, strike_price, expiry_date, contract_size)

    return {
        'success': True,
        'order_id': order.id,
        'filled_price': float(price),
        'total_cost': float(total_cost),
        'message': f'{side.upper()} {qty} {ticker.upper()} @ ${price:.2f}'
    }


def execute_limit_order(account, ticker, side, quantity, limit_price,
                        asset_type='stock', option_type='', strike_price=None,
                        expiry_date=None, contract_size=1):
    """Place a limit order (filled if price condition met, otherwise pending)."""
    from portfolio.models import Order

    qty = Decimal(str(quantity))
    lp = Decimal(str(limit_price))
    multiplier = Decimal(str(contract_size)) if asset_type in ('option', 'future') else Decimal('1')

    # Check funds for buy limit
    if side == 'buy':
        total_cost = qty * lp * multiplier
        if total_cost > account.cash_balance:
            return {'success': False, 'error': 'Insufficient funds for limit order'}

    # Check if limit can be filled immediately
    quote = get_live_quote(ticker)
    current_price = Decimal(str(quote.get('price', 0)))

    can_fill = False
    if current_price > 0:
        if side == 'buy' and current_price <= lp:
            can_fill = True
        elif side == 'sell' and current_price >= lp:
            can_fill = True

    if can_fill:
        return execute_market_order(account, ticker, side, quantity, asset_type,
                                   option_type, strike_price, expiry_date, contract_size)

    # Create pending order
    order = Order.objects.create(
        account=account,
        ticker=ticker.upper(),
        asset_type=asset_type,
        order_type='limit',
        side=side,
        quantity=qty,
        limit_price=lp,
        status='pending',
        option_type=option_type,
        strike_price=strike_price,
        expiry_date=expiry_date,
    )

    return {
        'success': True,
        'order_id': order.id,
        'status': 'pending',
        'message': f'Limit {side.upper()} {qty} {ticker.upper()} @ ${lp:.2f} — pending'
    }


def execute_stop_order(account, ticker, side, quantity, stop_price,
                       asset_type='stock', option_type='', strike_price=None,
                       expiry_date=None, contract_size=1):
    """Place a stop order."""
    from portfolio.models import Order

    qty = Decimal(str(quantity))
    sp = Decimal(str(stop_price))

    order = Order.objects.create(
        account=account,
        ticker=ticker.upper(),
        asset_type=asset_type,
        order_type='stop',
        side=side,
        quantity=qty,
        stop_price=sp,
        status='pending',
        option_type=option_type,
        strike_price=strike_price,
        expiry_date=expiry_date,
    )

    return {
        'success': True,
        'order_id': order.id,
        'status': 'pending',
        'message': f'Stop {side.upper()} {qty} {ticker.upper()} @ ${sp:.2f} — pending'
    }


def check_pending_orders(account):
    """Check and fill any pending limit/stop orders."""
    from portfolio.models import Order

    pending = Order.objects.filter(account=account, status='pending')
    if not pending.exists():
        return []

    tickers = list(set(pending.values_list('ticker', flat=True)))
    prices = get_batch_quotes(tickers)

    filled = []
    for order in pending:
        cp = prices.get(order.ticker, 0)
        if cp <= 0:
            continue
        current_price = Decimal(str(cp))

        should_fill = False
        if order.order_type == 'limit':
            if order.side == 'buy' and current_price <= order.limit_price:
                should_fill = True
            elif order.side == 'sell' and current_price >= order.limit_price:
                should_fill = True
        elif order.order_type == 'stop':
            if order.side == 'buy' and current_price >= order.stop_price:
                should_fill = True
            elif order.side == 'sell' and current_price <= order.stop_price:
                should_fill = True

        if should_fill:
            result = _fill_order(order, current_price)
            if result:
                filled.append(result)

    return filled


def close_position(position, partial_qty=None):
    """Close an open position at market price."""
    from portfolio.models import Order, Trade

    if not position.is_open:
        return {'success': False, 'error': 'Position already closed'}

    quote = get_live_quote(position.ticker)
    if not quote.get('price') or quote['price'] <= 0:
        return {'success': False, 'error': f'Could not get price for {position.ticker}'}

    price = Decimal(str(quote['price']))
    close_qty = Decimal(str(partial_qty)) if partial_qty else position.quantity
    if close_qty > position.quantity:
        close_qty = position.quantity

    multiplier = Decimal(str(position.contract_size)) if position.asset_type in ('option', 'future') else Decimal('1')

    # Calculate P&L
    if position.side == 'long':
        pnl = (price - position.entry_price) * close_qty * multiplier
        order_side = 'sell'
    else:
        pnl = (position.entry_price - price) * close_qty * multiplier
        order_side = 'buy'

    # Create closing order
    order = Order.objects.create(
        account=position.account,
        ticker=position.ticker,
        asset_type=position.asset_type,
        order_type='market',
        side=order_side,
        quantity=close_qty,
        filled_price=price,
        status='filled',
        filled_at=timezone.now(),
    )

    Trade.objects.create(
        account=position.account,
        order=order,
        ticker=position.ticker,
        side=order_side,
        quantity=close_qty,
        price=price,
    )

    # Return cash
    account = position.account
    account.cash_balance += close_qty * price * multiplier + (pnl if position.side == 'short' else Decimal('0'))
    if position.side == 'long':
        account.cash_balance = account.cash_balance  # Already got proceeds
        # Correction: for long close (sell), receive proceeds
        account.cash_balance = account.cash_balance  # cash was reduced on buy, now add back sale proceeds
    # Simpler: just add/subtract the P&L and return original capital
    # Reset: on buy we subtract cost, on sell we add proceeds
    # For closing long: we sell → add proceeds (qty * price * mult)
    # For closing short: we buy to cover → subtract cost (qty * price * mult)
    # We already computed pnl, let's just handle cash properly
    account.cash_balance = account.cash_balance  # undo above
    if position.side == 'long':
        # Closing long = selling. Get proceeds
        account.cash_balance += close_qty * price * multiplier
    else:
        # Closing short = buying to cover. Pay the cost
        # But we received cash when we shorted, now we pay current price
        account.cash_balance -= close_qty * price * multiplier

    account.save()

    # Update position
    if close_qty >= position.quantity:
        position.is_open = False
        position.closed_at = timezone.now()
        position.realized_pnl = pnl
        position.save()
    else:
        position.quantity -= close_qty
        position.save()
        # Record partial P&L in trade
        order.filled_price = price
        order.save()

    return {
        'success': True,
        'closed_qty': float(close_qty),
        'close_price': float(price),
        'realized_pnl': float(pnl),
        'message': f'Closed {close_qty} {position.ticker} @ ${price:.2f} | P&L: ${pnl:,.2f}'
    }


def get_account_summary(account):
    """Calculate full account summary with live prices."""
    positions = account.positions.filter(is_open=True)
    tickers = list(set(positions.values_list('ticker', flat=True)))
    prices = get_batch_quotes(tickers)

    total_market_value = Decimal('0')
    total_unrealized_pnl = Decimal('0')
    enriched_positions = []

    for pos in positions:
        cp = prices.get(pos.ticker, float(pos.entry_price))
        current_price = Decimal(str(cp))
        multiplier = Decimal(str(pos.contract_size)) if pos.asset_type in ('option', 'future') else Decimal('1')

        market_value = pos.quantity * current_price * multiplier
        cost_basis = pos.quantity * pos.entry_price * multiplier

        if pos.side == 'long':
            unrealized_pnl = market_value - cost_basis
        else:
            unrealized_pnl = cost_basis - market_value

        pnl_pct = (float(unrealized_pnl) / float(cost_basis) * 100) if cost_basis else 0

        total_market_value += market_value
        total_unrealized_pnl += unrealized_pnl

        enriched_positions.append({
            'position': pos,
            'current_price': float(current_price),
            'market_value': float(market_value),
            'cost_basis': float(cost_basis),
            'unrealized_pnl': float(unrealized_pnl),
            'pnl_pct': round(pnl_pct, 2),
            'pnl_positive': unrealized_pnl >= 0,
        })

    # Realized P&L from closed positions
    closed = account.positions.filter(is_open=False, realized_pnl__isnull=False)
    total_realized_pnl = sum(float(p.realized_pnl) for p in closed)

    total_equity = float(account.cash_balance) + float(total_market_value)
    total_pnl = float(total_unrealized_pnl) + total_realized_pnl
    total_return = (total_pnl / float(account.initial_capital) * 100) if account.initial_capital else 0

    return {
        'cash_balance': float(account.cash_balance),
        'total_market_value': float(total_market_value),
        'total_equity': total_equity,
        'total_unrealized_pnl': float(total_unrealized_pnl),
        'total_realized_pnl': total_realized_pnl,
        'total_pnl': total_pnl,
        'total_return': round(total_return, 2),
        'initial_capital': float(account.initial_capital),
        'positions': enriched_positions,
        'position_count': len(enriched_positions),
    }


def get_equity_history(account):
    """Build approximate equity curve from trade history."""
    trades = account.trades.order_by('executed_at')
    if not trades.exists():
        return {
            'dates': [timezone.now().strftime('%Y-%m-%d %H:%M')],
            'equity': [float(account.initial_capital)],
        }

    dates = [account.created_at.strftime('%Y-%m-%d %H:%M')]
    equity = [float(account.initial_capital)]

    running = float(account.initial_capital)
    for trade in trades:
        if trade.side == 'sell':
            running += float(trade.quantity) * float(trade.price)
        else:
            running -= float(trade.quantity) * float(trade.price)
        dates.append(trade.executed_at.strftime('%Y-%m-%d %H:%M'))
        equity.append(round(running, 2))

    # Add current state
    summary = get_account_summary(account)
    dates.append(timezone.now().strftime('%Y-%m-%d %H:%M'))
    equity.append(round(summary['total_equity'], 2))

    return {'dates': dates, 'equity': equity}


def get_market_movers():
    """Get top market movers for the trading dashboard."""
    indices = {
        '^GSPC': 'S&P 500',
        '^DJI': 'Dow Jones',
        '^IXIC': 'NASDAQ',
        '^RUT': 'Russell 2000',
        '^VIX': 'VIX',
        '^FTSE': 'FTSE 100',
        '^N225': 'Nikkei 225',
    }
    movers = []
    for ticker, name in indices.items():
        try:
            q = get_live_quote(ticker)
            movers.append({
                'ticker': ticker,
                'name': name,
                'price': q.get('price', 0),
                'change': q.get('change', 0),
                'change_pct': q.get('change_pct', 0),
            })
        except Exception:
            pass
    return movers


# ─── Internal helpers ────────────────────────────────────────────────

def _update_position(account, ticker, side, quantity, price,
                     asset_type, option_type, strike_price, expiry_date, contract_size):
    """Create new position or average into existing one."""
    from portfolio.models import Position

    # Try to find existing open position with same ticker/side/type
    existing = Position.objects.filter(
        account=account, ticker=ticker, side=side,
        asset_type=asset_type, is_open=True
    ).first()

    if existing and asset_type == 'stock':
        # Average in
        total_qty = existing.quantity + quantity
        total_cost = (existing.quantity * existing.entry_price) + (quantity * price)
        existing.entry_price = (total_cost / total_qty).quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)
        existing.quantity = total_qty
        existing.save()
    else:
        Position.objects.create(
            account=account,
            ticker=ticker,
            asset_type=asset_type,
            side=side,
            quantity=quantity,
            entry_price=price,
            option_type=option_type,
            strike_price=strike_price,
            expiry_date=expiry_date,
            contract_size=contract_size,
        )


def _fill_order(order, fill_price):
    """Fill a pending order."""
    from portfolio.models import Trade

    multiplier = Decimal(str(100 if order.asset_type in ('option', 'future') else 1))
    total_cost = order.quantity * fill_price * multiplier

    if order.side == 'buy' and total_cost > order.account.cash_balance:
        order.status = 'cancelled'
        order.save()
        return None

    order.filled_price = fill_price
    order.status = 'filled'
    order.filled_at = timezone.now()
    order.save()

    Trade.objects.create(
        account=order.account,
        order=order,
        ticker=order.ticker,
        side=order.side,
        quantity=order.quantity,
        price=fill_price,
    )

    account = order.account
    if order.side == 'buy':
        account.cash_balance -= total_cost
        position_side = 'long'
    else:
        account.cash_balance += total_cost
        position_side = 'short'
    account.save()

    _update_position(
        account, order.ticker, position_side, order.quantity, fill_price,
        order.asset_type, order.option_type, order.strike_price,
        order.expiry_date, 100 if order.asset_type in ('option', 'future') else 1
    )

    return {
        'order_id': order.id,
        'ticker': order.ticker,
        'side': order.side,
        'quantity': float(order.quantity),
        'price': float(fill_price),
    }

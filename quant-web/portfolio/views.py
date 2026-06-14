from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
import yfinance as yf
import pandas as pd
import json

from .models import Portfolio, Holding, TradingAccount, Position, Order, Trade
from .forms import PortfolioForm, HoldingForm, TradingAccountForm, OrderForm


@login_required
def portfolio_list(request):
    portfolios = Portfolio.objects.filter(user=request.user)
    return render(request, 'portfolio/list.html', {'portfolios': portfolios})


@login_required
def portfolio_create(request):
    if request.method == 'POST':
        form = PortfolioForm(request.POST)
        if form.is_valid():
            portfolio = form.save(commit=False)
            portfolio.user = request.user
            portfolio.save()
            messages.success(request, f'Portfolio "{portfolio.name}" created.')
            return redirect('portfolio:detail', pk=portfolio.pk)
    else:
        form = PortfolioForm()
    return render(request, 'portfolio/form.html', {'form': form, 'title': 'Create Portfolio'})


@login_required
def portfolio_edit(request, pk):
    portfolio = get_object_or_404(Portfolio, pk=pk, user=request.user)
    if request.method == 'POST':
        form = PortfolioForm(request.POST, instance=portfolio)
        if form.is_valid():
            form.save()
            messages.success(request, 'Portfolio updated.')
            return redirect('portfolio:detail', pk=portfolio.pk)
    else:
        form = PortfolioForm(instance=portfolio)
    return render(request, 'portfolio/form.html', {'form': form, 'title': 'Edit Portfolio'})


@login_required
def portfolio_delete(request, pk):
    portfolio = get_object_or_404(Portfolio, pk=pk, user=request.user)
    if request.method == 'POST':
        name = portfolio.name
        portfolio.delete()
        messages.success(request, f'Portfolio "{name}" deleted.')
        return redirect('portfolio:list')
    return render(request, 'portfolio/confirm_delete.html', {'portfolio': portfolio})


@login_required
def portfolio_detail(request, pk):
    portfolio = get_object_or_404(Portfolio, pk=pk, user=request.user)
    holdings = portfolio.holdings.all()

    # Fetch live prices for holdings
    enriched = []
    total_value = 0
    total_cost = 0

    if holdings.exists():
        tickers = [h.ticker for h in holdings]
        try:
            price_data = yf.download(tickers, period='1d')['Close']
            if isinstance(price_data, pd.DataFrame):
                if len(tickers) == 1:
                    prices = {tickers[0]: float(price_data.iloc[-1, 0])}
                else:
                    prices = {t: float(price_data[t].iloc[-1]) for t in tickers if t in price_data.columns}
            else:
                prices = {tickers[0]: float(price_data.iloc[-1])}
        except Exception:
            prices = {}

        for h in holdings:
            current_price = prices.get(h.ticker, 0)
            market_value = float(h.shares) * current_price
            cost_basis = float(h.shares) * float(h.avg_cost)
            pnl = market_value - cost_basis
            pnl_pct = (pnl / cost_basis * 100) if cost_basis else 0
            total_value += market_value
            total_cost += cost_basis
            enriched.append({
                'holding': h,
                'current_price': f"{current_price:.2f}",
                'market_value': f"{market_value:,.2f}",
                'cost_basis': f"{cost_basis:,.2f}",
                'pnl': f"{pnl:,.2f}",
                'pnl_pct': f"{pnl_pct:.1f}",
                'pnl_positive': pnl >= 0,
            })

    total_pnl = total_value - total_cost

    # Add holding form
    holding_form = HoldingForm()

    return render(request, 'portfolio/detail.html', {
        'portfolio': portfolio,
        'holdings': enriched,
        'holding_form': holding_form,
        'total_value': f"{total_value:,.2f}",
        'total_cost': f"{total_cost:,.2f}",
        'total_pnl': f"{total_pnl:,.2f}",
        'total_pnl_pct': f"{(total_pnl / total_cost * 100):.1f}" if total_cost else "0.0",
        'total_pnl_positive': total_pnl >= 0,
    })


@login_required
def holding_add(request, portfolio_pk):
    portfolio = get_object_or_404(Portfolio, pk=portfolio_pk, user=request.user)
    if request.method == 'POST':
        form = HoldingForm(request.POST)
        if form.is_valid():
            holding = form.save(commit=False)
            holding.portfolio = portfolio
            holding.save()
            messages.success(request, f'{holding.ticker} added to portfolio.')
    return redirect('portfolio:detail', pk=portfolio.pk)


@login_required
def holding_delete(request, portfolio_pk, holding_pk):
    portfolio = get_object_or_404(Portfolio, pk=portfolio_pk, user=request.user)
    holding = get_object_or_404(Holding, pk=holding_pk, portfolio=portfolio)
    if request.method == 'POST':
        ticker = holding.ticker
        holding.delete()
        messages.success(request, f'{ticker} removed from portfolio.')
    return redirect('portfolio:detail', pk=portfolio.pk)


# ─── Simulation Trading Views ───────────────────────────────────────

@login_required
def trading_account_list(request):
    accounts = TradingAccount.objects.filter(user=request.user)
    return render(request, 'portfolio/trading_accounts.html', {'accounts': accounts})


@login_required
def trading_account_create(request):
    if request.method == 'POST':
        form = TradingAccountForm(request.POST)
        if form.is_valid():
            acct = form.save(commit=False)
            acct.user = request.user
            acct.cash_balance = acct.initial_capital
            acct.save()
            messages.success(request, f'Trading account "{acct.name}" created with ${acct.initial_capital:,.2f}')
            return redirect('portfolio:trading_dashboard', pk=acct.pk)
    else:
        form = TradingAccountForm()
    return render(request, 'portfolio/trading_account_form.html', {'form': form})


@login_required
def trading_dashboard(request, pk):
    """Main trading terminal — the heart of the sim trading platform."""
    from analytics.services.trading_engine import get_account_summary, check_pending_orders, get_chart_data

    account = get_object_or_404(TradingAccount, pk=pk, user=request.user)

    # Check pending orders on each dashboard load
    check_pending_orders(account)
    account.refresh_from_db()

    summary = get_account_summary(account)
    order_form = OrderForm()

    # Recent orders
    recent_orders = account.orders.all()[:20]

    # Default chart ticker
    default_ticker = 'AAPL'
    positions = summary['positions']
    if positions:
        default_ticker = positions[0]['position'].ticker

    chart_data = get_chart_data(default_ticker, period='5d', interval='5m')

    return render(request, 'portfolio/trading_dashboard.html', {
        'account': account,
        'summary': summary,
        'order_form': order_form,
        'recent_orders': recent_orders,
        'chart_data_json': json.dumps(chart_data) if chart_data else 'null',
        'default_ticker': default_ticker,
    })


@login_required
def place_order(request, pk):
    """Handle order placement from trading dashboard."""
    from analytics.services.trading_engine import (
        execute_market_order, execute_limit_order, execute_stop_order
    )

    account = get_object_or_404(TradingAccount, pk=pk, user=request.user)

    if request.method == 'POST':
        form = OrderForm(request.POST)
        if form.is_valid():
            d = form.cleaned_data
            kwargs = {
                'account': account,
                'ticker': d['ticker'],
                'side': d['side'],
                'quantity': d['quantity'],
                'asset_type': d['asset_type'],
                'option_type': d.get('option_type', ''),
                'strike_price': d.get('strike_price'),
                'expiry_date': d.get('expiry_date'),
                'contract_size': 100 if d['asset_type'] in ('option', 'future') else 1,
            }

            if d['order_type'] == 'market':
                result = execute_market_order(**kwargs)
            elif d['order_type'] == 'limit':
                kwargs['limit_price'] = d['limit_price']
                result = execute_limit_order(**kwargs)
            elif d['order_type'] == 'stop':
                kwargs['stop_price'] = d['stop_price']
                result = execute_stop_order(**kwargs)
            else:
                result = {'success': False, 'error': 'Unknown order type'}

            if result['success']:
                messages.success(request, result.get('message', 'Order placed.'))
            else:
                messages.error(request, result.get('error', 'Order failed.'))
        else:
            for field, errors in form.errors.items():
                for e in errors:
                    messages.error(request, f'{field}: {e}')

    return redirect('portfolio:trading_dashboard', pk=pk)


@login_required
def close_position_view(request, pk, position_pk):
    """Close an open position."""
    from analytics.services.trading_engine import close_position as engine_close

    account = get_object_or_404(TradingAccount, pk=pk, user=request.user)
    position = get_object_or_404(Position, pk=position_pk, account=account, is_open=True)

    if request.method == 'POST':
        result = engine_close(position)
        if result['success']:
            messages.success(request, result.get('message', 'Position closed.'))
        else:
            messages.error(request, result.get('error', 'Failed to close position.'))

    return redirect('portfolio:trading_dashboard', pk=pk)


@login_required
def cancel_order_view(request, pk, order_pk):
    """Cancel a pending order."""
    account = get_object_or_404(TradingAccount, pk=pk, user=request.user)
    order = get_object_or_404(Order, pk=order_pk, account=account, status='pending')

    if request.method == 'POST':
        order.status = 'cancelled'
        order.save()
        messages.success(request, f'Order #{order.id} cancelled.')

    return redirect('portfolio:trading_dashboard', pk=pk)


@login_required
def trade_history(request, pk):
    """Full trade history for an account."""
    account = get_object_or_404(TradingAccount, pk=pk, user=request.user)
    trades = account.trades.all()
    closed_positions = account.positions.filter(is_open=False)
    return render(request, 'portfolio/trade_history.html', {
        'account': account,
        'trades': trades,
        'closed_positions': closed_positions,
    })


@login_required
def trading_account_delete(request, pk):
    """Delete a trading account."""
    account = get_object_or_404(TradingAccount, pk=pk, user=request.user)
    if request.method == 'POST':
        name = account.name
        account.delete()
        messages.success(request, f'Account "{name}" deleted.')
        return redirect('portfolio:trading_accounts')
    return render(request, 'portfolio/confirm_delete_account.html', {'account': account})


# ─── API Endpoints for Live Updates ─────────────────────────────────

@login_required
def api_live_price(request, ticker):
    """JSON endpoint for live price data."""
    from analytics.services.trading_engine import get_live_quote
    quote = get_live_quote(ticker.upper())
    return JsonResponse(quote)


@login_required
def api_chart_data(request, ticker):
    """JSON endpoint for chart OHLCV data."""
    from analytics.services.trading_engine import get_chart_data
    period = request.GET.get('period', '1d')
    interval = request.GET.get('interval', '5m')
    # Validate inputs
    valid_periods = {'1d', '5d', '1mo', '3mo', '6mo', '1y', 'ytd'}
    valid_intervals = {'1m', '2m', '5m', '15m', '30m', '60m', '90m', '1h', '1d', '5d', '1wk', '1mo'}
    if period not in valid_periods:
        period = '1d'
    if interval not in valid_intervals:
        interval = '5m'
    data = get_chart_data(ticker.upper(), period=period, interval=interval)
    return JsonResponse(data if data else {'error': 'No data'})


@login_required
def api_positions(request, pk):
    """JSON endpoint for live position data."""
    from analytics.services.trading_engine import get_account_summary
    account = get_object_or_404(TradingAccount, pk=pk, user=request.user)
    summary = get_account_summary(account)

    positions_data = []
    for p in summary['positions']:
        pos = p['position']
        positions_data.append({
            'id': pos.id,
            'ticker': pos.ticker,
            'asset_type': pos.get_asset_type_display(),
            'side': pos.side,
            'quantity': float(pos.quantity),
            'entry_price': float(pos.entry_price),
            'current_price': p['current_price'],
            'market_value': p['market_value'],
            'unrealized_pnl': p['unrealized_pnl'],
            'pnl_pct': p['pnl_pct'],
            'pnl_positive': p['pnl_positive'],
        })

    return JsonResponse({
        'cash_balance': summary['cash_balance'],
        'total_equity': summary['total_equity'],
        'total_unrealized_pnl': summary['total_unrealized_pnl'],
        'total_realized_pnl': summary['total_realized_pnl'],
        'total_return': summary['total_return'],
        'positions': positions_data,
    })


@login_required
def api_equity_history(request, pk):
    """JSON endpoint for equity curve."""
    from analytics.services.trading_engine import get_equity_history
    account = get_object_or_404(TradingAccount, pk=pk, user=request.user)
    data = get_equity_history(account)
    return JsonResponse(data)

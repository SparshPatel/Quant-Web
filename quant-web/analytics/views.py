from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
import csv
import json

from .forms import (CVaRForm, MarketRegimeForm, PairsTradingForm,
                     VolSurfaceForm, DCFForm, OptionsStrategyForm,
                     RiskDashboardForm, BacktestForm, SentimentForm,
                     EfficientFrontierForm, FactorExposureForm,
                     EarningsCalendarForm, StockScreenerForm,
                     CorrelationMatrixForm, MonteCarloForm,
                     TechnicalIndicatorsForm,
                     GlobalMacroForm, CurrencyExposureForm, CrossBorderForm,
                     RebalancingForm, StressTestForm, DividendTrackerForm,
                     SectorRotationForm, PortfolioAttributionForm,
                     YieldCurveForm, WatchlistForm)
from .models import SavedAnalysis
from .services.cvar_optimizer import optimize_cvar
from .services.market_regime import cluster_regimes
from .services.pairs_trading import analyze_pair
from .services.volatility_surface import build_surface
from .services.dcf_valuation import run_dcf
from .services.options_strategy import build_strategy
from .services.risk_dashboard import analyze_risk
from .services.backtesting import run_backtest
from .services.sentiment_analysis import analyze_sentiment
from .services.efficient_frontier import plot_frontier
from .services.factor_exposure import analyze_factors
from .services.earnings_calendar import get_earnings
from .services.stock_screener import screen_stocks
from .services.correlation_matrix import build_correlation
from .services.monte_carlo import simulate_paths
from .services.technical_indicators import chart_indicators
from .services.global_macro import compare_global_indices
from .services.currency_exposure import analyze_currency_exposure
from .services.cross_border import build_cross_border_report
from .services.global_indices import resolve_ticker, resolve_tickers
from .services.portfolio_rebalancing import rebalance_portfolio
from .services.stress_testing import stress_test
from .services.dividend_tracker import analyze_dividends
from .services.sector_rotation import analyze_sectors
from .services.portfolio_attribution import attribute_returns
from .services.yield_curve import analyze_yield_curve
from .services.watchlist import get_watchlist_data
from .services.pdf_report import generate_pdf_report


@login_required
def cvar_view(request):
    form = CVaRForm(request.POST or None)
    results = None

    if request.method == 'POST' and form.is_valid():
        try:
            tickers = resolve_tickers(form.cleaned_data['tickers'])
            results = optimize_cvar(
                tickers=tickers,
                start_date=str(form.cleaned_data['start_date']),
                end_date=str(form.cleaned_data['end_date']),
                alpha=form.cleaned_data['alpha'],
            )
        except Exception as e:
            messages.error(request, str(e))

    return render(request, 'analytics/cvar.html', {'form': form, 'results': results})


@login_required
def market_regime_view(request):
    form = MarketRegimeForm(request.POST or None)
    results = None

    if request.method == 'POST' and form.is_valid():
        try:
            results = cluster_regimes(
                ticker=resolve_ticker(form.cleaned_data['ticker']),
                start_date=str(form.cleaned_data['start_date']),
                end_date=str(form.cleaned_data['end_date']),
                n_regimes=form.cleaned_data['n_regimes'],
            )
        except Exception as e:
            messages.error(request, str(e))

    return render(request, 'analytics/market_regime.html', {'form': form, 'results': results})


@login_required
def pairs_trading_view(request):
    form = PairsTradingForm(request.POST or None)
    results = None

    if request.method == 'POST' and form.is_valid():
        try:
            results = analyze_pair(
                ticker1=resolve_ticker(form.cleaned_data['ticker1']),
                ticker2=resolve_ticker(form.cleaned_data['ticker2']),
                start_date=str(form.cleaned_data['start_date']),
                end_date=str(form.cleaned_data['end_date']),
                entry_z=form.cleaned_data['entry_z'],
                lookback=form.cleaned_data['lookback'],
            )
        except Exception as e:
            messages.error(request, str(e))

    return render(request, 'analytics/pairs_trading.html', {'form': form, 'results': results})


@login_required
def volatility_surface_view(request):
    form = VolSurfaceForm(request.POST or None)
    results = None

    if request.method == 'POST' and form.is_valid():
        try:
            results = build_surface(
                ticker_symbol=resolve_ticker(form.cleaned_data['ticker']),
            )
        except Exception as e:
            messages.error(request, str(e))

    return render(request, 'analytics/volatility_surface.html', {'form': form, 'results': results})


@login_required
def dcf_view(request):
    form = DCFForm(request.POST or None)
    results = None

    if request.method == 'POST' and form.is_valid():
        try:
            results = run_dcf(
                ticker_symbol=resolve_ticker(form.cleaned_data['ticker']),
                growth_rate=form.cleaned_data['growth_rate'],
                discount_rate=form.cleaned_data['discount_rate'],
                terminal_growth=form.cleaned_data['terminal_growth'],
                projection_years=form.cleaned_data['projection_years'],
            )
        except Exception as e:
            messages.error(request, str(e))

    return render(request, 'analytics/dcf.html', {'form': form, 'results': results})


@login_required
def options_strategy_view(request):
    form = OptionsStrategyForm(request.POST or None)
    results = None

    if request.method == 'POST' and form.is_valid():
        try:
            results = build_strategy(
                ticker_symbol=resolve_ticker(form.cleaned_data['ticker']),
                strategy_name=form.cleaned_data['strategy'],
                custom_strike=form.cleaned_data.get('custom_strike'),
            )
        except Exception as e:
            messages.error(request, str(e))

    return render(request, 'analytics/options_strategy.html', {'form': form, 'results': results})


@login_required
def risk_dashboard_view(request):
    form = RiskDashboardForm(request.POST or None)
    results = None

    if request.method == 'POST' and form.is_valid():
        try:
            tickers = resolve_tickers(form.cleaned_data['tickers'])
            results = analyze_risk(
                tickers=tickers,
                start_date=str(form.cleaned_data['start_date']),
                end_date=str(form.cleaned_data['end_date']),
                confidence=form.cleaned_data['confidence'],
            )
        except Exception as e:
            messages.error(request, str(e))

    return render(request, 'analytics/risk_dashboard.html', {'form': form, 'results': results})


@login_required
def backtest_view(request):
    form = BacktestForm(request.POST or None)
    results = None

    if request.method == 'POST' and form.is_valid():
        try:
            cd = form.cleaned_data
            results = run_backtest(
                ticker=resolve_ticker(cd['ticker']),
                start_date=str(cd['start_date']),
                end_date=str(cd['end_date']),
                strategy=cd['strategy'],
                initial_capital=cd['initial_capital'],
                fast_window=cd['fast_window'],
                slow_window=cd['slow_window'],
                rsi_period=cd['rsi_period'],
                rsi_oversold=cd['rsi_oversold'],
                rsi_overbought=cd['rsi_overbought'],
            )
        except Exception as e:
            messages.error(request, str(e))

    return render(request, 'analytics/backtesting.html', {'form': form, 'results': results})


@login_required
def sentiment_view(request):
    form = SentimentForm(request.POST or None)
    results = None

    if request.method == 'POST' and form.is_valid():
        try:
            results = analyze_sentiment(
                ticker=resolve_ticker(form.cleaned_data['ticker']),
            )
        except Exception as e:
            messages.error(request, str(e))

    return render(request, 'analytics/sentiment.html', {'form': form, 'results': results})


@login_required
def efficient_frontier_view(request):
    form = EfficientFrontierForm(request.POST or None)
    results = None
    if request.method == 'POST' and form.is_valid():
        try:
            tickers = resolve_tickers(form.cleaned_data['tickers'])
            results = plot_frontier(
                tickers=tickers,
                start_date=str(form.cleaned_data['start_date']),
                end_date=str(form.cleaned_data['end_date']),
            )
        except Exception as e:
            messages.error(request, str(e))
    return render(request, 'analytics/efficient_frontier.html', {'form': form, 'results': results})


@login_required
def factor_exposure_view(request):
    form = FactorExposureForm(request.POST or None)
    results = None
    if request.method == 'POST' and form.is_valid():
        try:
            tickers = resolve_tickers(form.cleaned_data['tickers'])
            results = analyze_factors(
                tickers=tickers,
                start_date=str(form.cleaned_data['start_date']),
                end_date=str(form.cleaned_data['end_date']),
            )
        except Exception as e:
            messages.error(request, str(e))
    return render(request, 'analytics/factor_exposure.html', {'form': form, 'results': results})


@login_required
def earnings_calendar_view(request):
    form = EarningsCalendarForm(request.POST or None)
    results = None
    if request.method == 'POST' and form.is_valid():
        try:
            tickers = resolve_tickers(form.cleaned_data['tickers'])
            results = get_earnings(tickers=tickers)
        except Exception as e:
            messages.error(request, str(e))
    return render(request, 'analytics/earnings_calendar.html', {'form': form, 'results': results})


@login_required
def stock_screener_view(request):
    form = StockScreenerForm(request.POST or None)
    results = None
    if request.method == 'POST' and form.is_valid():
        try:
            cd = form.cleaned_data
            custom = None
            if cd.get('custom_tickers'):
                custom = resolve_tickers(cd['custom_tickers'])
            cap_min = cd.get('mkt_cap_min')
            if cap_min is not None:
                cap_min = cap_min * 1e9  # convert billions to raw
            results = screen_stocks(
                pe_max=cd.get('pe_max'),
                pe_min=cd.get('pe_min'),
                mkt_cap_min=cap_min,
                div_yield_min=cd.get('div_yield_min'),
                sector=cd.get('sector') or None,
                custom_tickers=custom,
                region=cd.get('region', 'us'),
            )
        except Exception as e:
            messages.error(request, str(e))
    return render(request, 'analytics/stock_screener.html', {'form': form, 'results': results})


@login_required
def correlation_matrix_view(request):
    form = CorrelationMatrixForm(request.POST or None)
    results = None
    if request.method == 'POST' and form.is_valid():
        try:
            tickers = resolve_tickers(form.cleaned_data['tickers'])
            results = build_correlation(
                tickers=tickers,
                start_date=str(form.cleaned_data['start_date']),
                end_date=str(form.cleaned_data['end_date']),
            )
        except Exception as e:
            messages.error(request, str(e))
    return render(request, 'analytics/correlation_matrix.html', {'form': form, 'results': results})


@login_required
def monte_carlo_view(request):
    form = MonteCarloForm(request.POST or None)
    results = None
    if request.method == 'POST' and form.is_valid():
        try:
            results = simulate_paths(
                ticker=resolve_ticker(form.cleaned_data['ticker']),
                n_simulations=form.cleaned_data['n_simulations'],
                n_days=form.cleaned_data['n_days'],
            )
        except Exception as e:
            messages.error(request, str(e))
    return render(request, 'analytics/monte_carlo.html', {'form': form, 'results': results})


@login_required
def technical_indicators_view(request):
    form = TechnicalIndicatorsForm(request.POST or None)
    results = None
    if request.method == 'POST' and form.is_valid():
        try:
            cd = form.cleaned_data
            results = chart_indicators(
                ticker=resolve_ticker(cd['ticker']),
                start_date=str(cd['start_date']),
                end_date=str(cd['end_date']),
                sma_windows=cd['sma_windows'],
                show_rsi=cd.get('show_rsi', True),
                show_macd=cd.get('show_macd', True),
                show_bb=cd.get('show_bb', True),
            )
        except Exception as e:
            messages.error(request, str(e))
    return render(request, 'analytics/technical_indicators.html', {'form': form, 'results': results})


# ---------- International / Global ----------

@login_required
def global_macro_view(request):
    form = GlobalMacroForm(request.POST or None)
    results = None
    if request.method == 'POST' and form.is_valid():
        try:
            results = compare_global_indices(
                index_tickers=form.cleaned_data['indices'],
                start_date=str(form.cleaned_data['start_date']),
                end_date=str(form.cleaned_data['end_date']),
            )
        except Exception as e:
            messages.error(request, str(e))
    return render(request, 'analytics/global_macro.html', {'form': form, 'results': results})


@login_required
def currency_exposure_view(request):
    form = CurrencyExposureForm(request.POST or None)
    results = None
    if request.method == 'POST' and form.is_valid():
        try:
            results = analyze_currency_exposure(
                tickers=form.cleaned_data['indices'],
                base_currency=form.cleaned_data['base_currency'],
                start_date=str(form.cleaned_data['start_date']),
                end_date=str(form.cleaned_data['end_date']),
            )
        except Exception as e:
            messages.error(request, str(e))
    return render(request, 'analytics/currency_exposure.html', {'form': form, 'results': results})


@login_required
def cross_border_view(request):
    form = CrossBorderForm(request.POST or None)
    results = None
    if request.method == 'POST' and form.is_valid():
        try:
            results = build_cross_border_report(
                selected_indices=form.cleaned_data['indices'],
                home_country=form.cleaned_data['home_country'],
                annual_dividend_yield=form.cleaned_data['dividend_yield'],
                portfolio_value=form.cleaned_data['portfolio_value'],
            )
        except Exception as e:
            messages.error(request, str(e))
    return render(request, 'analytics/cross_border.html', {'form': form, 'results': results})


# ---------- New Tools ----------

@login_required
def rebalancing_view(request):
    form = RebalancingForm(request.POST or None)
    results = None
    if request.method == 'POST' and form.is_valid():
        try:
            cd = form.cleaned_data
            tickers = resolve_tickers(cd['tickers'])
            current_w = [float(x.strip()) for x in cd['current_weights'].split(',')]
            target_w = [float(x.strip()) for x in cd['target_weights'].split(',')]
            results = rebalance_portfolio(
                tickers=tickers,
                current_weights=current_w,
                target_weights=target_w,
                portfolio_value=cd['portfolio_value'],
                tx_cost_bps=cd['tx_cost_bps'],
            )
        except Exception as e:
            messages.error(request, str(e))
    return render(request, 'analytics/rebalancing.html', {'form': form, 'results': results})


@login_required
def stress_test_view(request):
    form = StressTestForm(request.POST or None)
    results = None
    if request.method == 'POST' and form.is_valid():
        try:
            cd = form.cleaned_data
            tickers = resolve_tickers(cd['tickers'])
            custom_shocks = None
            if cd.get('equity_shock'):
                custom_shocks = {
                    'equity_shock': cd['equity_shock'] / 100,
                    'portfolio_value': cd.get('portfolio_value') or 100000,
                }
            results = stress_test(
                tickers=tickers,
                scenarios=cd.get('scenarios'),
                custom_shocks=custom_shocks,
            )
        except Exception as e:
            messages.error(request, str(e))
    return render(request, 'analytics/stress_test.html', {'form': form, 'results': results})


@login_required
def dividend_tracker_view(request):
    form = DividendTrackerForm(request.POST or None)
    results = None
    if request.method == 'POST' and form.is_valid():
        try:
            tickers = resolve_tickers(form.cleaned_data['tickers'])
            results = analyze_dividends(tickers=tickers)
        except Exception as e:
            messages.error(request, str(e))
    return render(request, 'analytics/dividend_tracker.html', {'form': form, 'results': results})


@login_required
def sector_rotation_view(request):
    form = SectorRotationForm(request.POST or None)
    results = None
    if request.method == 'POST' and form.is_valid():
        try:
            cd = form.cleaned_data
            results = analyze_sectors(
                start_date=str(cd['start_date']),
                end_date=str(cd['end_date']),
                lookback=cd['lookback'],
            )
        except Exception as e:
            messages.error(request, str(e))
    return render(request, 'analytics/sector_rotation.html', {'form': form, 'results': results})


@login_required
def portfolio_attribution_view(request):
    form = PortfolioAttributionForm(request.POST or None)
    results = None
    if request.method == 'POST' and form.is_valid():
        try:
            cd = form.cleaned_data
            tickers = resolve_tickers(cd['tickers'])
            weights = [float(x.strip()) for x in cd['weights'].split(',')]
            results = attribute_returns(
                tickers=tickers,
                benchmark_ticker=resolve_ticker(cd['benchmark']),
                weights=weights,
                start_date=str(cd['start_date']),
                end_date=str(cd['end_date']),
            )
        except Exception as e:
            messages.error(request, str(e))
    return render(request, 'analytics/portfolio_attribution.html', {'form': form, 'results': results})


@login_required
def yield_curve_view(request):
    form = YieldCurveForm(request.POST or None)
    results = None
    if request.method == 'POST':
        try:
            results = analyze_yield_curve()
        except Exception as e:
            messages.error(request, str(e))
    return render(request, 'analytics/yield_curve.html', {'form': form, 'results': results})


@login_required
def watchlist_view(request):
    form = WatchlistForm(request.POST or None)
    results = None
    if request.method == 'POST' and form.is_valid():
        try:
            tickers = resolve_tickers(form.cleaned_data['tickers'])
            results = get_watchlist_data(tickers=tickers)
        except Exception as e:
            messages.error(request, str(e))
    return render(request, 'analytics/watchlist.html', {'form': form, 'results': results})


@login_required
def pdf_report_view(request):
    """Render a print-friendly report for any analysis tool."""
    tool = request.GET.get('tool_name', '')
    if tool not in TOOL_MAP:
        messages.error(request, 'Unknown tool for report.')
        return redirect('dashboard')
    label = TOOL_MAP[tool][0]
    params = {k: v for k, v in request.GET.items() if k != 'tool_name'}
    report_html = generate_pdf_report(tool_name=label, results=params, params=params)
    return render(request, 'analytics/pdf_report.html', {
        'report_html': report_html,
        'tool_label': label,
    })


# ---------- Saved Analyses ----------

TOOL_MAP = {
    'cvar': ('CVaR Optimization', CVaRForm),
    'market_regime': ('Market Regimes', MarketRegimeForm),
    'pairs_trading': ('Pairs Trading', PairsTradingForm),
    'volatility_surface': ('Vol Surface', VolSurfaceForm),
    'dcf': ('DCF Valuation', DCFForm),
    'options_strategy': ('Options Strategy', OptionsStrategyForm),
    'risk_dashboard': ('Risk Dashboard', RiskDashboardForm),
    'backtesting': ('Backtesting', BacktestForm),
    'sentiment': ('Sentiment', SentimentForm),
    'efficient_frontier': ('Efficient Frontier', EfficientFrontierForm),
    'factor_exposure': ('Factor Exposure', FactorExposureForm),
    'earnings_calendar': ('Earnings Calendar', EarningsCalendarForm),
    'stock_screener': ('Stock Screener', StockScreenerForm),
    'correlation_matrix': ('Correlation Matrix', CorrelationMatrixForm),
    'monte_carlo': ('Monte Carlo', MonteCarloForm),
    'technical_indicators': ('Technical Indicators', TechnicalIndicatorsForm),
    'global_macro': ('Global Macro', GlobalMacroForm),
    'currency_exposure': ('Currency Exposure', CurrencyExposureForm),
    'cross_border': ('Cross-Border Portfolio', CrossBorderForm),
    'rebalancing': ('Portfolio Rebalancing', RebalancingForm),
    'stress_test': ('Stress Testing', StressTestForm),
    'dividend_tracker': ('Dividend Tracker', DividendTrackerForm),
    'sector_rotation': ('Sector Rotation', SectorRotationForm),
    'portfolio_attribution': ('Portfolio Attribution', PortfolioAttributionForm),
    'yield_curve': ('Yield Curve', YieldCurveForm),
    'watchlist': ('Watchlist', WatchlistForm),
}


@login_required
def save_analysis(request):
    if request.method == 'POST':
        tool = request.POST.get('tool_name', '')
        if tool not in TOOL_MAP:
            messages.error(request, 'Unknown tool.')
            return redirect('dashboard')
        label, form_class = TOOL_MAP[tool]
        params = {}
        for key in request.POST:
            if key not in ('csrfmiddlewaretoken', 'tool_name', 'save_analysis'):
                params[key] = request.POST[key]
        SavedAnalysis.objects.create(
            user=request.user, tool_name=tool, tool_label=label, parameters=params,
        )
        messages.success(request, f'Analysis saved: {label}')
    return redirect(request.META.get('HTTP_REFERER', 'dashboard'))


@login_required
def saved_analyses_list(request):
    analyses = SavedAnalysis.objects.filter(user=request.user)
    return render(request, 'analytics/saved_analyses.html', {'analyses': analyses})


@login_required
def delete_saved_analysis(request, pk):
    obj = get_object_or_404(SavedAnalysis, pk=pk, user=request.user)
    if request.method == 'POST':
        obj.delete()
        messages.success(request, 'Deleted.')
    return redirect('analytics:saved_analyses')


@login_required
def rerun_saved_analysis(request, pk):
    obj = get_object_or_404(SavedAnalysis, pk=pk, user=request.user)
    if obj.tool_name in TOOL_MAP:
        from django.urls import reverse
        url = reverse(f'analytics:{obj.tool_name}')
        # build POST-like redirect with params in query string
        qs = '&'.join(f"{k}={v}" for k, v in obj.parameters.items())
        return redirect(f"{url}?{qs}")
    return redirect('analytics:saved_analyses')


# ---------- CSV Export ----------

@login_required
def export_csv(request):
    """Generic CSV export — expects tool_name + same POST params in GET/POST."""
    tool = request.GET.get('tool_name') or request.POST.get('tool_name', '')
    if tool not in TOOL_MAP:
        messages.error(request, 'Unknown tool for export.')
        return redirect('dashboard')

    # Re-run the analysis with same params from GET
    params = {k: v for k, v in request.GET.items() if k != 'tool_name'}

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{tool}_export.csv"'
    writer = csv.writer(response)

    try:
        if tool == 'stock_screener':
            cd_custom = params.get('custom_tickers')
            custom = [t.strip().upper() for t in cd_custom.split(',') if t.strip()] if cd_custom else None
            cap_min = float(params['mkt_cap_min']) * 1e9 if params.get('mkt_cap_min') else None
            result = screen_stocks(
                pe_max=float(params['pe_max']) if params.get('pe_max') else None,
                pe_min=float(params['pe_min']) if params.get('pe_min') else None,
                mkt_cap_min=cap_min,
                div_yield_min=float(params['div_yield_min']) if params.get('div_yield_min') else None,
                sector=params.get('sector') or None,
                custom_tickers=custom,
                region=params.get('region', 'us'),
            )
            writer.writerow(['Ticker', 'Name', 'Price', 'P/E', 'Fwd P/E', 'Mkt Cap', 'Div Yield', 'Sector', 'Beta'])
            for s in result['stocks']:
                writer.writerow([s['ticker'], s['name'], s['price'], s['pe'], s['fwd_pe'],
                                 s['mkt_cap'], s['div_yield'], s['sector'], s['beta']])

        elif tool == 'correlation_matrix':
            tickers = [t.strip().upper() for t in params.get('tickers', '').split(',') if t.strip()]
            result = build_correlation(tickers, params.get('start_date', ''), params.get('end_date', ''))
            writer.writerow(['Most Correlated Pairs'])
            writer.writerow(['Pair', 'Correlation'])
            for p in result['top_pairs']:
                writer.writerow([p['pair'], p['corr_fmt']])
            writer.writerow([])
            writer.writerow(['Least Correlated Pairs'])
            for p in result['bottom_pairs']:
                writer.writerow([p['pair'], p['corr_fmt']])

        elif tool == 'earnings_calendar':
            tickers = [t.strip().upper() for t in params.get('tickers', '').split(',') if t.strip()]
            result = get_earnings(tickers)
            writer.writerow(['Ticker', 'Name', 'Price', 'P/E', 'EPS', 'Fwd EPS', 'Earnings Date'])
            for h in result['holdings']:
                writer.writerow([h['ticker'], h['name'], h['price'], h['pe'],
                                 h['eps'], h['fwd_eps'], h['earnings_date']])

        else:
            writer.writerow(['Export not yet supported for this tool.'])
            writer.writerow(['Use the Save Analysis feature to store and revisit results.'])

    except Exception as e:
        writer.writerow(['Error', str(e)])

    return response

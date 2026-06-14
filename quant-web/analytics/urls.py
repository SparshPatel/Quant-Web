from django.urls import path
from . import views

app_name = 'analytics'

urlpatterns = [
    path('cvar/', views.cvar_view, name='cvar'),
    path('market-regime/', views.market_regime_view, name='market_regime'),
    path('pairs-trading/', views.pairs_trading_view, name='pairs_trading'),
    path('volatility-surface/', views.volatility_surface_view, name='volatility_surface'),
    path('dcf/', views.dcf_view, name='dcf'),
    path('options-strategy/', views.options_strategy_view, name='options_strategy'),
    path('risk-dashboard/', views.risk_dashboard_view, name='risk_dashboard'),
    path('backtesting/', views.backtest_view, name='backtesting'),
    path('sentiment/', views.sentiment_view, name='sentiment'),
    path('efficient-frontier/', views.efficient_frontier_view, name='efficient_frontier'),
    path('factor-exposure/', views.factor_exposure_view, name='factor_exposure'),
    path('earnings-calendar/', views.earnings_calendar_view, name='earnings_calendar'),
    path('stock-screener/', views.stock_screener_view, name='stock_screener'),
    path('correlation-matrix/', views.correlation_matrix_view, name='correlation_matrix'),
    path('monte-carlo/', views.monte_carlo_view, name='monte_carlo'),
    path('technical-indicators/', views.technical_indicators_view, name='technical_indicators'),
    # International / Global
    path('global-macro/', views.global_macro_view, name='global_macro'),
    path('currency-exposure/', views.currency_exposure_view, name='currency_exposure'),
    path('cross-border/', views.cross_border_view, name='cross_border'),
    # New Tools
    path('rebalancing/', views.rebalancing_view, name='rebalancing'),
    path('stress-test/', views.stress_test_view, name='stress_test'),
    path('dividend-tracker/', views.dividend_tracker_view, name='dividend_tracker'),
    path('sector-rotation/', views.sector_rotation_view, name='sector_rotation'),
    path('portfolio-attribution/', views.portfolio_attribution_view, name='portfolio_attribution'),
    path('yield-curve/', views.yield_curve_view, name='yield_curve'),
    path('watchlist/', views.watchlist_view, name='watchlist'),
    path('pdf-report/', views.pdf_report_view, name='pdf_report'),
    # Save / Export
    path('save/', views.save_analysis, name='save_analysis'),
    path('saved/', views.saved_analyses_list, name='saved_analyses'),
    path('saved/<int:pk>/delete/', views.delete_saved_analysis, name='delete_saved'),
    path('saved/<int:pk>/rerun/', views.rerun_saved_analysis, name='rerun_saved'),
    path('export-csv/', views.export_csv, name='export_csv'),
]

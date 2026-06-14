from django import forms
from datetime import date, timedelta

from .services.global_indices import get_index_choices, GLOBAL_INDICES

# ---------------------------------------------------------------------------
# Reusable index-selector widget
# ---------------------------------------------------------------------------
INDEX_CHOICES = get_index_choices()

BASE_CURRENCY_CHOICES = [
    ('USD', '🇺🇸 USD — US Dollar'),
    ('EUR', '🇪🇺 EUR — Euro'),
    ('GBP', '🇬🇧 GBP — British Pound'),
    ('JPY', '🇯🇵 JPY — Japanese Yen'),
    ('CHF', '🇨🇭 CHF — Swiss Franc'),
    ('CAD', '🇨🇦 CAD — Canadian Dollar'),
    ('AUD', '🇦🇺 AUD — Australian Dollar'),
    ('SEK', '🇸🇪 SEK — Swedish Krona'),
    ('INR', '🇮🇳 INR — Indian Rupee'),
    ('CNY', '🇨🇳 CNY — Chinese Yuan'),
    ('BRL', '🇧🇷 BRL — Brazilian Real'),
    ('SGD', '🇸🇬 SGD — Singapore Dollar'),
    ('HKD', '🇭🇰 HKD — Hong Kong Dollar'),
    ('KRW', '🇰🇷 KRW — Korean Won'),
    ('MXN', '🇲🇽 MXN — Mexican Peso'),
    ('ZAR', '🇿🇦 ZAR — South African Rand'),
]

HOME_COUNTRY_CHOICES = [
    ('US', '🇺🇸 United States'),
    ('GB', '🇬🇧 United Kingdom'),
    ('DE', '🇩🇪 Germany'),
    ('FR', '🇫🇷 France'),
    ('SE', '🇸🇪 Sweden'),
    ('CH', '🇨🇭 Switzerland'),
    ('JP', '🇯🇵 Japan'),
    ('AU', '🇦🇺 Australia'),
    ('CA', '🇨🇦 Canada'),
    ('IN', '🇮🇳 India'),
    ('SG', '🇸🇬 Singapore'),
    ('HK', '🇭🇰 Hong Kong'),
    ('BR', '🇧🇷 Brazil'),
    ('KR', '🇰🇷 South Korea'),
    ('NL', '🇳🇱 Netherlands'),
]


class CVaRForm(forms.Form):
    tickers = forms.CharField(
        label='Ticker Symbols',
        initial='AAPL, MSFT, GOOGL, AMZN, JPM, JNJ, XOM, PG',
        help_text='Comma-separated — stocks (AAPL), ETFs (SPY), or indices (FTSE, NIKKEI, DAX, ^GSPC)',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    start_date = forms.DateField(
        initial=date.today() - timedelta(days=365 * 5),
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
    )
    end_date = forms.DateField(
        initial=date.today(),
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
    )
    alpha = forms.FloatField(
        label='Tail Probability (α)',
        initial=0.05, min_value=0.01, max_value=0.50,
        help_text='Default 5% — the worst-case percentile',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
    )


class MarketRegimeForm(forms.Form):
    ticker = forms.CharField(
        label='Ticker Symbol',
        initial='SPY', max_length=20,
        help_text='Stock (AAPL), ETF (SPY), or index (FTSE, NIKKEI, DAX, ^GSPC)',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    start_date = forms.DateField(
        initial=date(2007, 1, 1),
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
    )
    end_date = forms.DateField(
        initial=date.today(),
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
    )
    n_regimes = forms.IntegerField(
        label='Number of Regimes',
        initial=3, min_value=2, max_value=5,
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
    )


class PairsTradingForm(forms.Form):
    ticker1 = forms.CharField(
        label='Ticker 1', initial='KO', max_length=20,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    ticker2 = forms.CharField(
        label='Ticker 2', initial='PEP', max_length=20,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    start_date = forms.DateField(
        initial=date(2015, 1, 1),
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
    )
    end_date = forms.DateField(
        initial=date.today(),
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
    )
    entry_z = forms.FloatField(
        label='Entry Z-Score', initial=2.0,
        min_value=0.5, max_value=5.0,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
    )
    lookback = forms.IntegerField(
        label='Lookback Window (days)', initial=60,
        min_value=10, max_value=252,
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
    )


class VolSurfaceForm(forms.Form):
    ticker = forms.CharField(
        label='Ticker Symbol',
        initial='AAPL', max_length=20,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )


class DCFForm(forms.Form):
    ticker = forms.CharField(
        label='Ticker Symbol',
        initial='AAPL', max_length=20,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    growth_rate = forms.FloatField(
        label='FCF Growth Rate', initial=0.10,
        min_value=-0.50, max_value=1.0,
        help_text='Expected annual FCF growth (e.g. 0.10 = 10%)',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
    )
    discount_rate = forms.FloatField(
        label='Discount Rate (WACC)', initial=0.10,
        min_value=0.01, max_value=0.30,
        help_text='Weighted average cost of capital',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
    )
    terminal_growth = forms.FloatField(
        label='Terminal Growth Rate', initial=0.03,
        min_value=0.0, max_value=0.05,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.005'}),
    )
    projection_years = forms.IntegerField(
        label='Projection Years', initial=5,
        min_value=1, max_value=10,
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
    )


class OptionsStrategyForm(forms.Form):
    STRATEGY_CHOICES = [
        ('long_call', 'Long Call'),
        ('long_put', 'Long Put'),
        ('covered_call', 'Covered Call'),
        ('bull_call_spread', 'Bull Call Spread'),
        ('bear_put_spread', 'Bear Put Spread'),
        ('straddle', 'Straddle'),
        ('strangle', 'Strangle'),
        ('iron_condor', 'Iron Condor'),
        ('butterfly', 'Butterfly Spread'),
    ]

    ticker = forms.CharField(
        label='Ticker Symbol',
        initial='AAPL', max_length=20,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    strategy = forms.ChoiceField(
        label='Strategy',
        choices=STRATEGY_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    custom_strike = forms.FloatField(
        label='Custom Strike (optional)',
        required=False,
        help_text='Leave blank to use current price as reference',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5'}),
    )


class RiskDashboardForm(forms.Form):
    tickers = forms.CharField(
        label='Ticker Symbols',
        initial='AAPL, MSFT, GOOGL, AMZN, JPM',
        help_text='Comma-separated — stocks, ETFs, or indices (FTSE, NIKKEI, DAX)',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    start_date = forms.DateField(
        initial=date.today() - timedelta(days=365 * 3),
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
    )
    end_date = forms.DateField(
        initial=date.today(),
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
    )
    confidence = forms.FloatField(
        label='VaR Confidence Level',
        initial=0.95, min_value=0.90, max_value=0.99,
        help_text='e.g. 0.95 = 95% VaR',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
    )


class BacktestForm(forms.Form):
    STRATEGY_CHOICES = [
        ('sma_crossover', 'SMA Crossover'),
        ('rsi_mean_reversion', 'RSI Mean Reversion'),
        ('momentum', 'Momentum (N-Day Return)'),
        ('bollinger_bands', 'Bollinger Bands'),
        ('buy_and_hold', 'Buy & Hold (Benchmark)'),
    ]

    ticker = forms.CharField(
        label='Ticker Symbol',
        initial='SPY', max_length=20,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    strategy = forms.ChoiceField(
        label='Strategy',
        choices=STRATEGY_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    start_date = forms.DateField(
        initial=date(2015, 1, 1),
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
    )
    end_date = forms.DateField(
        initial=date.today(),
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
    )
    initial_capital = forms.IntegerField(
        label='Initial Capital ($)',
        initial=10000, min_value=100,
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
    )
    fast_window = forms.IntegerField(
        label='Fast SMA Window', initial=20, min_value=2, max_value=200,
        help_text='For SMA Crossover',
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
    )
    slow_window = forms.IntegerField(
        label='Slow SMA Window', initial=50, min_value=5, max_value=500,
        help_text='For SMA Crossover',
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
    )
    rsi_period = forms.IntegerField(
        label='RSI Period', initial=14, min_value=2, max_value=50,
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
    )
    rsi_oversold = forms.IntegerField(
        label='RSI Oversold', initial=30, min_value=5, max_value=50,
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
    )
    rsi_overbought = forms.IntegerField(
        label='RSI Overbought', initial=70, min_value=50, max_value=95,
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
    )


class SentimentForm(forms.Form):
    ticker = forms.CharField(
        label='Ticker Symbol',
        initial='AAPL', max_length=20,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )


class EfficientFrontierForm(forms.Form):
    tickers = forms.CharField(
        label='Ticker Symbols',
        initial='AAPL, MSFT, GOOGL, AMZN, JPM, JNJ, XOM, PG',
        help_text='Comma-separated — stocks, ETFs, or indices (FTSE, NIKKEI, ^GSPC)',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    start_date = forms.DateField(
        initial=date.today() - timedelta(days=365 * 5),
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
    )
    end_date = forms.DateField(
        initial=date.today(),
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
    )


class FactorExposureForm(forms.Form):
    tickers = forms.CharField(
        label='Ticker Symbols',
        initial='AAPL, MSFT, GOOGL, AMZN',
        help_text='Comma-separated — stocks, ETFs, or indices',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    start_date = forms.DateField(
        initial=date.today() - timedelta(days=365 * 5),
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
    )
    end_date = forms.DateField(
        initial=date.today(),
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
    )


class EarningsCalendarForm(forms.Form):
    tickers = forms.CharField(
        label='Ticker Symbols',
        initial='AAPL, MSFT, GOOGL, AMZN, TSLA',
        help_text='Comma-separated — stocks or ETFs',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )


class StockScreenerForm(forms.Form):
    SECTOR_CHOICES = [
        ('', 'Any Sector'),
        ('Technology', 'Technology'),
        ('Healthcare', 'Healthcare'),
        ('Financial Services', 'Financial Services'),
        ('Consumer Cyclical', 'Consumer Cyclical'),
        ('Consumer Defensive', 'Consumer Defensive'),
        ('Industrials', 'Industrials'),
        ('Energy', 'Energy'),
        ('Basic Materials', 'Basic Materials'),
        ('Communication Services', 'Communication Services'),
        ('Real Estate', 'Real Estate'),
        ('Utilities', 'Utilities'),
    ]

    REGION_CHOICES = [
        ('us', '🇺🇸 US Large-Caps (~100)'),
        ('europe', '🇪🇺 European Large-Caps (~35)'),
        ('asia', '🇯🇵 Asia-Pacific Large-Caps (~30)'),
        ('latam', '🇧🇷 Latin America (~10)'),
        ('global', '🌍 Global All (~175)'),
    ]

    region = forms.ChoiceField(
        label='Stock Universe',
        choices=REGION_CHOICES,
        initial='us',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    sector = forms.ChoiceField(
        label='Sector', choices=SECTOR_CHOICES, required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    pe_max = forms.FloatField(
        label='Max P/E', required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 30'}),
    )
    pe_min = forms.FloatField(
        label='Min P/E', required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 5'}),
    )
    mkt_cap_min = forms.FloatField(
        label='Min Market Cap ($B)', required=False,
        help_text='In billions, e.g. 10 = $10B',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '1'}),
    )
    div_yield_min = forms.FloatField(
        label='Min Dividend Yield', required=False,
        help_text='e.g. 0.02 = 2%',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.005'}),
    )
    custom_tickers = forms.CharField(
        label='Custom Universe (optional)',
        required=False,
        help_text='Comma-separated tickers; leave blank to use default ~100 large-caps',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )


class CorrelationMatrixForm(forms.Form):
    tickers = forms.CharField(
        label='Ticker Symbols',
        initial='AAPL, MSFT, GOOGL, AMZN, JPM, XOM, GLD, TLT',
        help_text='Comma-separated — stocks, ETFs, or indices (FTSE, NIKKEI, DAX)',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    start_date = forms.DateField(
        initial=date.today() - timedelta(days=365 * 3),
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
    )
    end_date = forms.DateField(
        initial=date.today(),
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
    )


class MonteCarloForm(forms.Form):
    ticker = forms.CharField(
        label='Ticker Symbol',
        initial='AAPL', max_length=20,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    n_simulations = forms.IntegerField(
        label='Number of Simulations',
        initial=500, min_value=50, max_value=5000,
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
    )
    n_days = forms.IntegerField(
        label='Forecast Days',
        initial=252, min_value=5, max_value=756,
        help_text='Trading days (252 ≈ 1 year)',
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
    )


class TechnicalIndicatorsForm(forms.Form):
    ticker = forms.CharField(
        label='Ticker Symbol',
        initial='AAPL', max_length=20,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    start_date = forms.DateField(
        initial=date.today() - timedelta(days=365),
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
    )
    end_date = forms.DateField(
        initial=date.today(),
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
    )
    sma_windows = forms.CharField(
        label='SMA Windows', initial='20, 50',
        help_text='Comma-separated periods',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    show_rsi = forms.BooleanField(label='Show RSI', initial=True, required=False,
                                   widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    show_macd = forms.BooleanField(label='Show MACD', initial=True, required=False,
                                    widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    show_bb = forms.BooleanField(label='Show Bollinger Bands', initial=True, required=False,
                                  widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))


# ---------------------------------------------------------------------------
# International / Global services
# ---------------------------------------------------------------------------

class GlobalMacroForm(forms.Form):
    indices = forms.MultipleChoiceField(
        label='Select Indices',
        choices=[],  # populated in __init__
        widget=forms.SelectMultiple(attrs={
            'class': 'form-select', 'size': '12',
        }),
        help_text='Hold Ctrl/Cmd to select multiple indices (2–15)',
    )
    start_date = forms.DateField(
        initial=date.today() - timedelta(days=365 * 3),
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
    )
    end_date = forms.DateField(
        initial=date.today(),
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Build flat choices with region labels
        flat = []
        for ticker, meta in sorted(GLOBAL_INDICES.items(), key=lambda x: (x[1]['region'], x[1]['name'])):
            flat.append((ticker, f"{meta['flag']} {meta['name']} ({ticker})"))
        self.fields['indices'].choices = flat


class CurrencyExposureForm(forms.Form):
    indices = forms.MultipleChoiceField(
        label='Select Indices / Tickers',
        choices=[],
        widget=forms.SelectMultiple(attrs={
            'class': 'form-select', 'size': '10',
        }),
        help_text='Select the indices in your international portfolio',
    )
    base_currency = forms.ChoiceField(
        label='Your Home Currency',
        choices=BASE_CURRENCY_CHOICES,
        initial='USD',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    start_date = forms.DateField(
        initial=date.today() - timedelta(days=365 * 3),
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
    )
    end_date = forms.DateField(
        initial=date.today(),
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        flat = []
        for ticker, meta in sorted(GLOBAL_INDICES.items(), key=lambda x: (x[1]['region'], x[1]['name'])):
            flat.append((ticker, f"{meta['flag']} {meta['name']} ({ticker})"))
        self.fields['indices'].choices = flat


# ---------------------------------------------------------------------------
# Portfolio Rebalancing
# ---------------------------------------------------------------------------

class RebalancingForm(forms.Form):
    tickers = forms.CharField(
        label='Ticker Symbols',
        initial='AAPL, MSFT, GOOGL, AMZN',
        help_text='Comma-separated tickers',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    current_weights = forms.CharField(
        label='Current Weights',
        initial='0.30, 0.25, 0.25, 0.20',
        help_text='Comma-separated, must sum to 1.0',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    target_weights = forms.CharField(
        label='Target Weights',
        initial='0.25, 0.25, 0.25, 0.25',
        help_text='Comma-separated, must sum to 1.0',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    portfolio_value = forms.IntegerField(
        label='Portfolio Value ($)',
        initial=100000, min_value=100,
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
    )
    tx_cost_bps = forms.IntegerField(
        label='Transaction Cost (bps)',
        initial=10, min_value=0, max_value=100,
        help_text='One-way cost in basis points (10 bps = 0.1%)',
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
    )


# ---------------------------------------------------------------------------
# Stress Testing
# ---------------------------------------------------------------------------

SCENARIO_CHOICES = [
    ('gfc_2008', '2008 Global Financial Crisis'),
    ('euro_debt_2011', '2011 Euro Debt Crisis'),
    ('covid_2020', 'COVID-19 Crash (2020)'),
    ('rate_hike_2022', '2022 Rate Hike Sell-off'),
    ('dot_com_2000', 'Dot-Com Crash (2000-02)'),
]


class StressTestForm(forms.Form):
    tickers = forms.CharField(
        label='Ticker Symbols',
        initial='AAPL, MSFT, GOOGL, AMZN, JPM',
        help_text='Comma-separated — equal-weight portfolio',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    scenarios = forms.MultipleChoiceField(
        label='Crisis Scenarios',
        choices=SCENARIO_CHOICES,
        initial=['gfc_2008', 'covid_2020', 'rate_hike_2022'],
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
    )
    equity_shock = forms.FloatField(
        label='Custom Equity Shock (%)',
        required=False,
        initial=-20,
        help_text='e.g. -20 = simulate a 20% market drop',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '1'}),
    )
    portfolio_value = forms.IntegerField(
        label='Portfolio Value ($)',
        initial=100000, min_value=100,
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
    )


# ---------------------------------------------------------------------------
# Dividend Tracker
# ---------------------------------------------------------------------------

class DividendTrackerForm(forms.Form):
    tickers = forms.CharField(
        label='Ticker Symbols',
        initial='JNJ, PG, KO, PEP, T, XOM, ABBV, MO',
        help_text='Comma-separated — best with dividend-paying stocks',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )


# ---------------------------------------------------------------------------
# Sector Rotation
# ---------------------------------------------------------------------------

class SectorRotationForm(forms.Form):
    start_date = forms.DateField(
        initial=date.today() - timedelta(days=365),
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
    )
    end_date = forms.DateField(
        initial=date.today(),
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
    )
    lookback = forms.IntegerField(
        label='Momentum Lookback (days)',
        initial=63, min_value=10, max_value=252,
        help_text='63 ≈ 3 months, 21 ≈ 1 month',
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
    )


# ---------------------------------------------------------------------------
# Portfolio Attribution
# ---------------------------------------------------------------------------

class PortfolioAttributionForm(forms.Form):
    tickers = forms.CharField(
        label='Portfolio Tickers',
        initial='AAPL, MSFT, GOOGL, AMZN',
        help_text='Comma-separated holdings',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    weights = forms.CharField(
        label='Portfolio Weights',
        initial='0.30, 0.25, 0.25, 0.20',
        help_text='Comma-separated, must sum to 1.0',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    benchmark = forms.CharField(
        label='Benchmark Ticker',
        initial='SPY', max_length=20,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    start_date = forms.DateField(
        initial=date.today() - timedelta(days=365),
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
    )
    end_date = forms.DateField(
        initial=date.today(),
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
    )


# ---------------------------------------------------------------------------
# Yield Curve
# ---------------------------------------------------------------------------

class YieldCurveForm(forms.Form):
    """No user inputs needed — always fetches current US Treasury curve."""
    pass


# ---------------------------------------------------------------------------
# Watchlist
# ---------------------------------------------------------------------------

class WatchlistForm(forms.Form):
    tickers = forms.CharField(
        label='Watchlist Tickers',
        initial='AAPL, MSFT, GOOGL, AMZN, TSLA, NVDA, META, JPM',
        help_text='Comma-separated — your personal watchlist',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )


class CrossBorderForm(forms.Form):
    indices = forms.MultipleChoiceField(
        label='Select Indices for Your Portfolio',
        choices=[],
        widget=forms.SelectMultiple(attrs={
            'class': 'form-select', 'size': '10',
        }),
        help_text='Pick indices to build an international allocation',
    )
    home_country = forms.ChoiceField(
        label='Investor Home Country',
        choices=HOME_COUNTRY_CHOICES,
        initial='US',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    portfolio_value = forms.IntegerField(
        label='Portfolio Value ($)',
        initial=1_000_000, min_value=1000,
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
    )
    dividend_yield = forms.FloatField(
        label='Assumed Dividend Yield',
        initial=0.02, min_value=0.0, max_value=0.15,
        help_text='Used to estimate withholding tax cost (e.g. 0.02 = 2%)',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.005'}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        flat = []
        for ticker, meta in sorted(GLOBAL_INDICES.items(), key=lambda x: (x[1]['region'], x[1]['name'])):
            flat.append((ticker, f"{meta['flag']} {meta['name']} ({ticker})"))
        self.fields['indices'].choices = flat

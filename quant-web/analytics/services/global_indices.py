"""
Global indices registry and on-the-fly data fetcher.

Provides metadata for ~50 major indices worldwide, grouped by region,
with currency, exchange info, and international portfolio considerations.
"""

import re
import pandas as pd
import yfinance as yf
from datetime import date, timedelta
from functools import lru_cache

# ---------------------------------------------------------------------------
# Global index registry: {yahoo_ticker: metadata}
# ---------------------------------------------------------------------------

GLOBAL_INDICES = {
    # ── North America ─────────────────────────────────────────────────────
    '^GSPC':   {'name': 'S&P 500',           'country': 'US',  'currency': 'USD', 'region': 'North America', 'flag': '🇺🇸', 'exchange': 'NYSE/NASDAQ',  'timezone': 'America/New_York'},
    '^DJI':    {'name': 'Dow Jones Industrial', 'country': 'US', 'currency': 'USD', 'region': 'North America', 'flag': '🇺🇸', 'exchange': 'NYSE',         'timezone': 'America/New_York'},
    '^IXIC':   {'name': 'NASDAQ Composite',  'country': 'US',  'currency': 'USD', 'region': 'North America', 'flag': '🇺🇸', 'exchange': 'NASDAQ',       'timezone': 'America/New_York'},
    '^RUT':    {'name': 'Russell 2000',      'country': 'US',  'currency': 'USD', 'region': 'North America', 'flag': '🇺🇸', 'exchange': 'NYSE',         'timezone': 'America/New_York'},
    '^GSPTSE': {'name': 'S&P/TSX Composite', 'country': 'CA',  'currency': 'CAD', 'region': 'North America', 'flag': '🇨🇦', 'exchange': 'TSX',          'timezone': 'America/Toronto'},
    '^MXX':    {'name': 'IPC Mexico',        'country': 'MX',  'currency': 'MXN', 'region': 'North America', 'flag': '🇲🇽', 'exchange': 'BMV',          'timezone': 'America/Mexico_City'},

    # ── Europe ────────────────────────────────────────────────────────────
    '^FTSE':     {'name': 'FTSE 100',          'country': 'GB', 'currency': 'GBP', 'region': 'Europe', 'flag': '🇬🇧', 'exchange': 'LSE',       'timezone': 'Europe/London'},
    '^GDAXI':    {'name': 'DAX 40',            'country': 'DE', 'currency': 'EUR', 'region': 'Europe', 'flag': '🇩🇪', 'exchange': 'XETRA',     'timezone': 'Europe/Berlin'},
    '^FCHI':     {'name': 'CAC 40',            'country': 'FR', 'currency': 'EUR', 'region': 'Europe', 'flag': '🇫🇷', 'exchange': 'Euronext',  'timezone': 'Europe/Paris'},
    '^STOXX50E': {'name': 'Euro Stoxx 50',     'country': 'EU', 'currency': 'EUR', 'region': 'Europe', 'flag': '🇪🇺', 'exchange': 'STOXX',     'timezone': 'Europe/Berlin'},
    '^AEX':      {'name': 'AEX 25',           'country': 'NL', 'currency': 'EUR', 'region': 'Europe', 'flag': '🇳🇱', 'exchange': 'Euronext',  'timezone': 'Europe/Amsterdam'},
    '^IBEX':     {'name': 'IBEX 35',          'country': 'ES', 'currency': 'EUR', 'region': 'Europe', 'flag': '🇪🇸', 'exchange': 'BME',       'timezone': 'Europe/Madrid'},
    '^SSMI':     {'name': 'SMI',              'country': 'CH', 'currency': 'CHF', 'region': 'Europe', 'flag': '🇨🇭', 'exchange': 'SIX',       'timezone': 'Europe/Zurich'},
    '^OMXS30':   {'name': 'OMX Stockholm 30', 'country': 'SE', 'currency': 'SEK', 'region': 'Europe', 'flag': '🇸🇪', 'exchange': 'Nasdaq Nordic', 'timezone': 'Europe/Stockholm'},
    '^BFX':      {'name': 'BEL 20',           'country': 'BE', 'currency': 'EUR', 'region': 'Europe', 'flag': '🇧🇪', 'exchange': 'Euronext',  'timezone': 'Europe/Brussels'},
    'FTSEMIB.MI':{'name': 'FTSE MIB',         'country': 'IT', 'currency': 'EUR', 'region': 'Europe', 'flag': '🇮🇹', 'exchange': 'Borsa Italiana', 'timezone': 'Europe/Rome'},
    '^OMXC25':   {'name': 'OMX Copenhagen 25','country': 'DK', 'currency': 'DKK', 'region': 'Europe', 'flag': '🇩🇰', 'exchange': 'Nasdaq Nordic', 'timezone': 'Europe/Copenhagen'},
    '^OMXHPI':   {'name': 'OMX Helsinki',     'country': 'FI', 'currency': 'EUR', 'region': 'Europe', 'flag': '🇫🇮', 'exchange': 'Nasdaq Nordic', 'timezone': 'Europe/Helsinki'},
    'PSI20.LS':  {'name': 'PSI 20',           'country': 'PT', 'currency': 'EUR', 'region': 'Europe', 'flag': '🇵🇹', 'exchange': 'Euronext',  'timezone': 'Europe/Lisbon'},
    '^ATX':      {'name': 'ATX',              'country': 'AT', 'currency': 'EUR', 'region': 'Europe', 'flag': '🇦🇹', 'exchange': 'Wiener Borse', 'timezone': 'Europe/Vienna'},

    # ── Asia-Pacific ──────────────────────────────────────────────────────
    '^N225':   {'name': 'Nikkei 225',         'country': 'JP', 'currency': 'JPY', 'region': 'Asia-Pacific', 'flag': '🇯🇵', 'exchange': 'TSE',     'timezone': 'Asia/Tokyo'},
    '^HSI':    {'name': 'Hang Seng',          'country': 'HK', 'currency': 'HKD', 'region': 'Asia-Pacific', 'flag': '🇭🇰', 'exchange': 'HKEX',    'timezone': 'Asia/Hong_Kong'},
    '000001.SS':{'name': 'Shanghai Composite','country': 'CN', 'currency': 'CNY', 'region': 'Asia-Pacific', 'flag': '🇨🇳', 'exchange': 'SSE',     'timezone': 'Asia/Shanghai'},
    '399001.SZ':{'name': 'Shenzhen Component','country': 'CN', 'currency': 'CNY', 'region': 'Asia-Pacific', 'flag': '🇨🇳', 'exchange': 'SZSE',    'timezone': 'Asia/Shanghai'},
    '^KS11':   {'name': 'KOSPI',              'country': 'KR', 'currency': 'KRW', 'region': 'Asia-Pacific', 'flag': '🇰🇷', 'exchange': 'KRX',     'timezone': 'Asia/Seoul'},
    '^TWII':   {'name': 'TAIEX',              'country': 'TW', 'currency': 'TWD', 'region': 'Asia-Pacific', 'flag': '🇹🇼', 'exchange': 'TWSE',    'timezone': 'Asia/Taipei'},
    '^STI':    {'name': 'Straits Times',      'country': 'SG', 'currency': 'SGD', 'region': 'Asia-Pacific', 'flag': '🇸🇬', 'exchange': 'SGX',     'timezone': 'Asia/Singapore'},
    '^BSESN':  {'name': 'BSE Sensex',         'country': 'IN', 'currency': 'INR', 'region': 'Asia-Pacific', 'flag': '🇮🇳', 'exchange': 'BSE',     'timezone': 'Asia/Kolkata'},
    '^NSEI':   {'name': 'Nifty 50',           'country': 'IN', 'currency': 'INR', 'region': 'Asia-Pacific', 'flag': '🇮🇳', 'exchange': 'NSE',     'timezone': 'Asia/Kolkata'},
    '^AXJO':   {'name': 'ASX 200',            'country': 'AU', 'currency': 'AUD', 'region': 'Asia-Pacific', 'flag': '🇦🇺', 'exchange': 'ASX',     'timezone': 'Australia/Sydney'},
    '^NZ50':   {'name': 'S&P/NZX 50',         'country': 'NZ', 'currency': 'NZD', 'region': 'Asia-Pacific', 'flag': '🇳🇿', 'exchange': 'NZX',     'timezone': 'Pacific/Auckland'},
    '^JKSE':   {'name': 'Jakarta Composite',  'country': 'ID', 'currency': 'IDR', 'region': 'Asia-Pacific', 'flag': '🇮🇩', 'exchange': 'IDX',     'timezone': 'Asia/Jakarta'},
    '^KLSE':   {'name': 'FTSE Bursa KLCI',    'country': 'MY', 'currency': 'MYR', 'region': 'Asia-Pacific', 'flag': '🇲🇾', 'exchange': 'Bursa Malaysia', 'timezone': 'Asia/Kuala_Lumpur'},
    '^SET.BK': {'name': 'SET Index',          'country': 'TH', 'currency': 'THB', 'region': 'Asia-Pacific', 'flag': '🇹🇭', 'exchange': 'SET',     'timezone': 'Asia/Bangkok'},

    # ── Latin America ─────────────────────────────────────────────────────
    '^BVSP':  {'name': 'Bovespa',             'country': 'BR', 'currency': 'BRL', 'region': 'Latin America', 'flag': '🇧🇷', 'exchange': 'B3',      'timezone': 'America/Sao_Paulo'},
    '^MERV':  {'name': 'MERVAL',              'country': 'AR', 'currency': 'ARS', 'region': 'Latin America', 'flag': '🇦🇷', 'exchange': 'BCBA',    'timezone': 'America/Argentina/Buenos_Aires'},
    '^IPSA':  {'name': 'S&P CLX IPSA',        'country': 'CL', 'currency': 'CLP', 'region': 'Latin America', 'flag': '🇨🇱', 'exchange': 'BCS',     'timezone': 'America/Santiago'},

    # ── Middle East & Africa ──────────────────────────────────────────────
    '^TA125.TA': {'name': 'TA-125',           'country': 'IL', 'currency': 'ILS', 'region': 'Middle East & Africa', 'flag': '🇮🇱', 'exchange': 'TASE',  'timezone': 'Asia/Jerusalem'},
    '^TASI':     {'name': 'Tadawul All Share','country': 'SA', 'currency': 'SAR', 'region': 'Middle East & Africa', 'flag': '🇸🇦', 'exchange': 'Tadawul', 'timezone': 'Asia/Riyadh'},
    '^J203.JO':  {'name': 'JSE All Share',    'country': 'ZA', 'currency': 'ZAR', 'region': 'Middle East & Africa', 'flag': '🇿🇦', 'exchange': 'JSE',   'timezone': 'Africa/Johannesburg'},
}


# ---------------------------------------------------------------------------
# FX pairs for currency conversion (base → USD)
# ---------------------------------------------------------------------------

FX_PAIRS = {
    'EUR': 'EURUSD=X',  'GBP': 'GBPUSD=X',  'JPY': 'JPYUSD=X',
    'CHF': 'CHFUSD=X',  'CAD': 'CADUSD=X',  'AUD': 'AUDUSD=X',
    'NZD': 'NZDUSD=X',  'SEK': 'SEKUSD=X',  'DKK': 'DKKUSD=X',
    'HKD': 'HKDUSD=X',  'SGD': 'SGDUSD=X',  'KRW': 'KRWUSD=X',
    'TWD': 'TWDUSD=X',  'INR': 'INRUSD=X',  'CNY': 'CNYUSD=X',
    'BRL': 'BRLUSD=X',  'MXN': 'MXNUSD=X',  'ZAR': 'ZARUSD=X',
    'ILS': 'ILSUSD=X',  'SAR': 'SARUSD=X',  'THB': 'THBUSD=X',
    'MYR': 'MYRUSD=X',  'IDR': 'IDRUSD=X',  'ARS': 'ARSUSD=X',
    'CLP': 'CLPUSD=X',
}


# ---------------------------------------------------------------------------
# International portfolio considerations by country
# ---------------------------------------------------------------------------

COUNTRY_INFO = {
    'US': {
        'withholding_tax_pct': 30,  # default for non-resident aliens, reduced by treaties
        'treaty_rate_pct': 15,      # typical treaty-reduced rate
        'settlement': 'T+1',
        'capital_gains_tax_note': 'Generally no US capital gains tax for non-residents on portfolio investments.',
        'regulatory_body': 'SEC',
        'fx_notes': 'USD is the global reserve currency — no conversion needed for USD-denominated portfolios.',
        'custody_notes': 'Well-established custody infrastructure. SIPC protection up to $500K.',
        'key_risks': ['Political risk around fiscal policy', 'Fed monetary policy impact'],
    },
    'GB': {
        'withholding_tax_pct': 0,
        'treaty_rate_pct': 0,
        'settlement': 'T+1',
        'capital_gains_tax_note': 'No UK capital gains tax for non-residents on shares (generally).',
        'regulatory_body': 'FCA',
        'fx_notes': 'GBP can be volatile post-Brexit. Typical FX spread 0.03-0.10%.',
        'custody_notes': 'FSCS protection up to £85K per firm.',
        'key_risks': ['Brexit-related trade friction', 'GBP currency risk'],
    },
    'DE': {
        'withholding_tax_pct': 26.375,
        'treaty_rate_pct': 15,
        'settlement': 'T+2',
        'capital_gains_tax_note': '26.375% flat tax on capital gains (incl. solidarity surcharge). Treaty may reduce.',
        'regulatory_body': 'BaFin',
        'fx_notes': 'EUR — deep liquidity, tight spreads (0.01-0.05%).',
        'custody_notes': 'Strong regulatory framework under EU MiFID II.',
        'key_risks': ['Eurozone monetary policy', 'Energy dependency'],
    },
    'FR': {
        'withholding_tax_pct': 30,
        'treaty_rate_pct': 15,
        'settlement': 'T+2',
        'capital_gains_tax_note': '30% flat tax (prélèvement forfaitaire unique). Treaty may reduce dividends.',
        'regulatory_body': 'AMF',
        'fx_notes': 'EUR — deep liquidity.',
        'custody_notes': 'EU investor protection under MiFID II.',
        'key_risks': ['Political risk', 'EU regulatory changes'],
    },
    'JP': {
        'withholding_tax_pct': 20.315,
        'treaty_rate_pct': 10,
        'settlement': 'T+2',
        'capital_gains_tax_note': '20.315% on capital gains for non-residents (may be exempt by treaty).',
        'regulatory_body': 'FSA / JSDA',
        'fx_notes': 'JPY carries significant volatility. Hedging recommended for large allocations.',
        'custody_notes': 'Robust infrastructure. Japan Securities Depository Center (JASDEC).',
        'key_risks': ['Yen volatility', 'BOJ policy shifts', 'Aging demographics'],
    },
    'HK': {
        'withholding_tax_pct': 0,
        'treaty_rate_pct': 0,
        'settlement': 'T+2',
        'capital_gains_tax_note': 'No capital gains tax in Hong Kong.',
        'regulatory_body': 'SFC',
        'fx_notes': 'HKD pegged to USD (7.75-7.85). Minimal FX risk vs USD.',
        'custody_notes': 'Gateway to China A-shares via Stock Connect.',
        'key_risks': ['China political risk', 'Peg sustainability in extreme scenarios'],
    },
    'CN': {
        'withholding_tax_pct': 10,
        'treaty_rate_pct': 10,
        'settlement': 'T+1',
        'capital_gains_tax_note': 'Capital gains tax temporarily exempt for QFII/Stock Connect investors.',
        'regulatory_body': 'CSRC',
        'fx_notes': 'CNY managed float — capital controls exist. QFII or Stock Connect required for access.',
        'custody_notes': 'Access via QFII, RQFII, or Hong Kong Stock Connect.',
        'key_risks': ['Capital controls', 'Regulatory unpredictability', 'Geopolitical tensions'],
    },
    'IN': {
        'withholding_tax_pct': 20,
        'treaty_rate_pct': 15,
        'settlement': 'T+1',
        'capital_gains_tax_note': 'Short-term gains (< 1 yr) taxed at 15%. Long-term gains > ₹1L at 10%.',
        'regulatory_body': 'SEBI',
        'fx_notes': 'INR partially convertible. FPI registration required.',
        'custody_notes': 'Foreign Portfolio Investor (FPI) registration required via SEBI.',
        'key_risks': ['INR volatility', 'FPI regulatory changes', 'Liquidity in mid-caps'],
    },
    'KR': {
        'withholding_tax_pct': 22,
        'treaty_rate_pct': 15,
        'settlement': 'T+2',
        'capital_gains_tax_note': 'Capital gains tax for foreign investors on Korean securities.',
        'regulatory_body': 'FSC / FSS',
        'fx_notes': 'KRW can be volatile. Limited offshore market.',
        'custody_notes': 'Korea Securities Depository (KSD). Foreign investor ID required.',
        'key_risks': ['Geopolitical (North Korea)', 'KRW volatility', 'Chaebol governance'],
    },
    'AU': {
        'withholding_tax_pct': 30,
        'treaty_rate_pct': 15,
        'settlement': 'T+2',
        'capital_gains_tax_note': 'Non-residents generally not taxed on portfolio capital gains.',
        'regulatory_body': 'ASIC',
        'fx_notes': 'AUD commodity-linked currency. Can be volatile.',
        'custody_notes': 'Well-regulated market. CHESS settlement system.',
        'key_risks': ['Commodity price dependency', 'AUD/USD volatility', 'China trade exposure'],
    },
    'BR': {
        'withholding_tax_pct': 15,
        'treaty_rate_pct': 15,
        'settlement': 'T+2',
        'capital_gains_tax_note': '15% on capital gains for non-residents. IOF tax on FX transactions.',
        'regulatory_body': 'CVM',
        'fx_notes': 'BRL highly volatile. IOF (financial operations tax) on FX flows.',
        'custody_notes': 'B3 exchange. CPF/CNPJ registration required for foreign investors.',
        'key_risks': ['BRL volatility', 'Political instability', 'High interest rates'],
    },
    'CH': {
        'withholding_tax_pct': 35,
        'treaty_rate_pct': 15,
        'settlement': 'T+2',
        'capital_gains_tax_note': 'No capital gains tax for private investors.',
        'regulatory_body': 'FINMA',
        'fx_notes': 'CHF safe-haven currency. Tight spreads.',
        'custody_notes': 'SIX Swiss Exchange. Strong investor protection.',
        'key_risks': ['CHF appreciation risk', 'SNB policy surprises'],
    },
    'SE': {
        'withholding_tax_pct': 30,
        'treaty_rate_pct': 15,
        'settlement': 'T+2',
        'capital_gains_tax_note': '30% on dividends. Capital gains may be treaty-exempt.',
        'regulatory_body': 'Finansinspektionen',
        'fx_notes': 'SEK can be volatile vs EUR and USD.',
        'custody_notes': 'Euroclear Sweden (formerly VPC).',
        'key_risks': ['SEK volatility', 'Small open economy sensitivity'],
    },
    'SG': {
        'withholding_tax_pct': 0,
        'treaty_rate_pct': 0,
        'settlement': 'T+2',
        'capital_gains_tax_note': 'No capital gains tax in Singapore.',
        'regulatory_body': 'MAS',
        'fx_notes': 'SGD managed float. Relatively stable.',
        'custody_notes': 'CDP (Central Depository). Well-regulated.',
        'key_risks': ['Small market', 'Regional contagion risk'],
    },
    'NL': {
        'withholding_tax_pct': 15,
        'treaty_rate_pct': 15,
        'settlement': 'T+2',
        'capital_gains_tax_note': 'NL introduced dividend WHT in 2024. Capital gains generally exempt for non-residents.',
        'regulatory_body': 'AFM',
        'fx_notes': 'EUR. See Germany/EU notes.',
        'custody_notes': 'Euronext Amsterdam. EU MiFID II framework.',
        'key_risks': ['Eurozone systemic risk'],
    },
    'TW': {
        'withholding_tax_pct': 21,
        'treaty_rate_pct': 21,
        'settlement': 'T+2',
        'capital_gains_tax_note': 'Securities transaction tax 0.3% on sales. Capital gains tax suspended.',
        'regulatory_body': 'FSC',
        'fx_notes': 'TWD partially managed. FINI/FIDI registration required.',
        'custody_notes': 'TDCC depository. Foreign investor approval needed.',
        'key_risks': ['Geopolitical (cross-strait)', 'TSMC concentration'],
    },
    # Fallback for countries not individually listed
    'EU': {
        'withholding_tax_pct': 15,
        'treaty_rate_pct': 15,
        'settlement': 'T+2',
        'capital_gains_tax_note': 'Varies by member state. Generally covered by MiFID II.',
        'regulatory_body': 'ESMA (EU-wide)',
        'fx_notes': 'EUR — deep liquidity.',
        'custody_notes': 'EU passporting regime.',
        'key_risks': ['Eurozone fragmentation risk'],
    },
    'MX': {
        'withholding_tax_pct': 10,
        'treaty_rate_pct': 10,
        'settlement': 'T+2',
        'capital_gains_tax_note': '10% on capital gains for non-residents.',
        'regulatory_body': 'CNBV',
        'fx_notes': 'MXN highly liquid EM currency but volatile.',
        'custody_notes': 'Indeval depository.',
        'key_risks': ['MXN volatility', 'Nearshoring dynamics', 'Political risk'],
    },
    'NZ': {
        'withholding_tax_pct': 30,
        'treaty_rate_pct': 15,
        'settlement': 'T+2',
        'capital_gains_tax_note': 'No general capital gains tax (FIF rules may apply for NZ residents).',
        'regulatory_body': 'FMA',
        'fx_notes': 'NZD commodity-linked. Can be volatile.',
        'custody_notes': 'NZX. Smaller market — liquidity may be limited.',
        'key_risks': ['Small market', 'NZD volatility'],
    },
    'ZA': {
        'withholding_tax_pct': 20,
        'treaty_rate_pct': 15,
        'settlement': 'T+3',
        'capital_gains_tax_note': 'Non-residents generally exempt from SA capital gains tax on shares.',
        'regulatory_body': 'FSCA',
        'fx_notes': 'ZAR very volatile. Dual listing on LSE common for large caps.',
        'custody_notes': 'Strate depository. Exchange controls exist.',
        'key_risks': ['ZAR volatility', 'Load shedding / infrastructure', 'Political risk'],
    },
    'SA': {
        'withholding_tax_pct': 5,
        'treaty_rate_pct': 5,
        'settlement': 'T+2',
        'capital_gains_tax_note': 'No capital gains tax. No personal income tax.',
        'regulatory_body': 'CMA',
        'fx_notes': 'SAR pegged to USD. Minimal FX risk.',
        'custody_notes': 'Edaa depository. QFI registration required.',
        'key_risks': ['Oil price dependency', 'Governance/transparency'],
    },
    'IL': {
        'withholding_tax_pct': 25,
        'treaty_rate_pct': 15,
        'settlement': 'T+2',
        'capital_gains_tax_note': '25% on capital gains for non-residents (may be treaty-reduced).',
        'regulatory_body': 'ISA',
        'fx_notes': 'ILS floating. Moderately volatile.',
        'custody_notes': 'TASE Clearing House.',
        'key_risks': ['Geopolitical risk', 'ILS volatility'],
    },
    'AR': {
        'withholding_tax_pct': 7,
        'treaty_rate_pct': 7,
        'settlement': 'T+2',
        'capital_gains_tax_note': 'Complex tax regime. Multiple FX rates complicate repatriation.',
        'regulatory_body': 'CNV',
        'fx_notes': 'ARS extreme volatility. Capital controls / cepo cambiario. Multiple exchange rates.',
        'custody_notes': 'Caja de Valores. Capital repatriation restrictions.',
        'key_risks': ['Hyperinflation risk', 'Capital controls', 'Default history'],
    },
    'CL': {
        'withholding_tax_pct': 35,
        'treaty_rate_pct': 15,
        'settlement': 'T+2',
        'capital_gains_tax_note': '35% on dividends, credits available. Capital gains may be exempt by treaty.',
        'regulatory_body': 'CMF',
        'fx_notes': 'CLP moderately volatile EM currency.',
        'custody_notes': 'DCV depository.',
        'key_risks': ['Copper price dependency', 'Political reform risk'],
    },
    'ID': {
        'withholding_tax_pct': 20,
        'treaty_rate_pct': 15,
        'settlement': 'T+2',
        'capital_gains_tax_note': '0.1% transaction tax on sales. Dividends WHT 20% (treaty may reduce).',
        'regulatory_body': 'OJK',
        'fx_notes': 'IDR volatile. Foreign ownership caps on some sectors.',
        'custody_notes': 'KSEI depository. Foreign ownership limits in certain sectors.',
        'key_risks': ['IDR volatility', 'Foreign ownership caps', 'Liquidity in small caps'],
    },
    'MY': {
        'withholding_tax_pct': 0,
        'treaty_rate_pct': 0,
        'settlement': 'T+2',
        'capital_gains_tax_note': 'No capital gains tax on shares. No dividend WHT.',
        'regulatory_body': 'SC Malaysia',
        'fx_notes': 'MYR partially managed. Moderate volatility.',
        'custody_notes': 'Bursa Malaysia Depository.',
        'key_risks': ['Commodity exposure', 'Political risk'],
    },
    'TH': {
        'withholding_tax_pct': 10,
        'treaty_rate_pct': 10,
        'settlement': 'T+2',
        'capital_gains_tax_note': 'No capital gains tax for non-residents on listed securities.',
        'regulatory_body': 'SEC Thailand',
        'fx_notes': 'THB managed float.',
        'custody_notes': 'TSD depository. Foreign ownership limits on some stocks.',
        'key_risks': ['Political instability', 'Foreign ownership limits', 'Tourism dependency'],
    },
    'ES': {
        'withholding_tax_pct': 19,
        'treaty_rate_pct': 15,
        'settlement': 'T+2',
        'capital_gains_tax_note': '19% WHT on dividends (treaty may reduce). Capital gains may be exempt.',
        'regulatory_body': 'CNMV',
        'fx_notes': 'EUR.',
        'custody_notes': 'Iberclear. EU MiFID II.',
        'key_risks': ['Eurozone periphery risk'],
    },
    'BE': {
        'withholding_tax_pct': 30,
        'treaty_rate_pct': 15,
        'settlement': 'T+2',
        'capital_gains_tax_note': '30% WHT on dividends. No capital gains tax for non-residents.',
        'regulatory_body': 'FSMA',
        'fx_notes': 'EUR.',
        'custody_notes': 'Euroclear (HQ in Brussels). EU MiFID II.',
        'key_risks': ['Eurozone risk'],
    },
    'IT': {
        'withholding_tax_pct': 26,
        'treaty_rate_pct': 15,
        'settlement': 'T+2',
        'capital_gains_tax_note': '26% on capital gains and dividends. Treaty may reduce.',
        'regulatory_body': 'CONSOB',
        'fx_notes': 'EUR.',
        'custody_notes': 'Monte Titoli (Euronext Securities Milan).',
        'key_risks': ['Sovereign debt levels', 'Eurozone periphery risk'],
    },
    'DK': {
        'withholding_tax_pct': 27,
        'treaty_rate_pct': 15,
        'settlement': 'T+2',
        'capital_gains_tax_note': '27% WHT on dividends (reclaimable to treaty rate). Generally no CG tax for non-residents.',
        'regulatory_body': 'Finanstilsynet',
        'fx_notes': 'DKK pegged to EUR (ERM II). Very stable.',
        'custody_notes': 'VP Securities.',
        'key_risks': ['DKK-EUR peg (very low risk)', 'Small market'],
    },
    'FI': {
        'withholding_tax_pct': 30,
        'treaty_rate_pct': 15,
        'settlement': 'T+2',
        'capital_gains_tax_note': '30% WHT on dividends. Capital gains generally exempt for non-residents.',
        'regulatory_body': 'Finanssivalvonta',
        'fx_notes': 'EUR.',
        'custody_notes': 'Euroclear Finland.',
        'key_risks': ['Small market', 'Nokia/commodity concentration'],
    },
    'PT': {
        'withholding_tax_pct': 28,
        'treaty_rate_pct': 15,
        'settlement': 'T+2',
        'capital_gains_tax_note': '28% on dividends and CG. Treaty may reduce.',
        'regulatory_body': 'CMVM',
        'fx_notes': 'EUR.',
        'custody_notes': 'Euronext Securities Porto. EU MiFID II.',
        'key_risks': ['Small market', 'Eurozone periphery'],
    },
    'AT': {
        'withholding_tax_pct': 27.5,
        'treaty_rate_pct': 15,
        'settlement': 'T+2',
        'capital_gains_tax_note': '27.5% on dividends and CG. Treaty may reduce.',
        'regulatory_body': 'FMA Austria',
        'fx_notes': 'EUR.',
        'custody_notes': 'OeKB CSD.',
        'key_risks': ['Small market', 'Eastern Europe exposure'],
    },
}


# ---------------------------------------------------------------------------
# Typical FX conversion costs (bid-ask spread %)
# ---------------------------------------------------------------------------

FX_CONVERSION_COSTS = {
    'USD': 0.00, 'EUR': 0.02, 'GBP': 0.03, 'JPY': 0.03, 'CHF': 0.04,
    'CAD': 0.04, 'AUD': 0.05, 'NZD': 0.08, 'SEK': 0.06, 'DKK': 0.04,
    'HKD': 0.03, 'SGD': 0.05, 'KRW': 0.10, 'TWD': 0.10, 'INR': 0.15,
    'CNY': 0.15, 'BRL': 0.20, 'MXN': 0.10, 'ZAR': 0.15, 'ILS': 0.10,
    'SAR': 0.05, 'THB': 0.10, 'MYR': 0.10, 'IDR': 0.15, 'ARS': 0.50,
    'CLP': 0.15,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_index_choices():
    """Return choices grouped by region for use in Django form ChoiceField."""
    choices = [('', '— Select an Index —')]
    regions = {}
    for ticker, meta in GLOBAL_INDICES.items():
        region = meta['region']
        regions.setdefault(region, [])
        regions[region].append((ticker, f"{meta['flag']} {meta['name']} ({ticker})"))

    for region in ['North America', 'Europe', 'Asia-Pacific', 'Latin America', 'Middle East & Africa']:
        if region in regions:
            choices.append((region, sorted(regions[region], key=lambda x: x[1])))
    return choices


def get_index_meta(ticker):
    """Return metadata dict for a given index ticker, or None."""
    return GLOBAL_INDICES.get(ticker)


def get_country_info(country_code):
    """Return country investment info dict."""
    return COUNTRY_INFO.get(country_code, COUNTRY_INFO.get('EU', {}))


# ---------------------------------------------------------------------------
# Smart ticker resolver — tries to match user input to known indices
# ---------------------------------------------------------------------------

# Build a lookup: uppercase short name → yahoo ticker
_INDEX_ALIASES = {}
for _ticker, _meta in GLOBAL_INDICES.items():
    # Map both with and without ^ prefix
    _INDEX_ALIASES[_ticker.upper()] = _ticker
    _INDEX_ALIASES[_ticker.lstrip('^').upper()] = _ticker
    # Map short names like "S&P 500", "FTSE 100", "Nikkei 225"
    _short = _meta['name'].upper().replace(' ', '')
    _INDEX_ALIASES[_short] = _ticker

# Common user aliases → correct yahoo ticker
_INDEX_ALIASES.update({
    'SPX': '^GSPC', 'SP500': '^GSPC', 'S&P500': '^GSPC', 'S&P': '^GSPC',
    'DOW': '^DJI', 'DJIA': '^DJI', 'DOWJONES': '^DJI',
    'NASDAQ': '^IXIC', 'COMP': '^IXIC', 'NDX': '^IXIC',
    'RUSSELL': '^RUT', 'RUSSELL2000': '^RUT', 'RUT': '^RUT',
    'FTSE': '^FTSE', 'FTSE100': '^FTSE', 'UKX': '^FTSE',
    'DAX': '^GDAXI', 'DAX40': '^GDAXI',
    'CAC': '^FCHI', 'CAC40': '^FCHI',
    'STOXX50': '^STOXX50E', 'EUROSTOXX': '^STOXX50E', 'EUROSTOXX50': '^STOXX50E',
    'SMI': '^SSMI',
    'AEX': '^AEX', 'AEX25': '^AEX',
    'IBEX': '^IBEX', 'IBEX35': '^IBEX',
    'OMX': '^OMXS30', 'OMXS30': '^OMXS30',
    'NIKKEI': '^N225', 'NIKKEI225': '^N225', 'N225': '^N225', 'NKY': '^N225',
    'HANGSENG': '^HSI', 'HSI': '^HSI',
    'SHANGHAI': '000001.SS', 'SHCOMP': '000001.SS',
    'KOSPI': '^KS11', 'KS11': '^KS11',
    'TAIEX': '^TWII', 'TWII': '^TWII',
    'SENSEX': '^BSESN', 'BSESN': '^BSESN',
    'NIFTY': '^NSEI', 'NIFTY50': '^NSEI', 'NSEI': '^NSEI',
    'ASX200': '^AXJO', 'ASX': '^AXJO', 'AXJO': '^AXJO',
    'BOVESPA': '^BVSP', 'BVSP': '^BVSP',
    'STI': '^STI',
    'STRAITS': '^STI',
    'MERVAL': '^MERV', 'MERV': '^MERV',
    'TSX': '^GSPTSE', 'GSPTSE': '^GSPTSE',
    'IPC': '^MXX', 'MXX': '^MXX',
    'OEX': '^OEX', 'SP100': '^OEX',
    'VIX': '^VIX',
    'TNX': '^TNX',
    'BEL20': '^BFX', 'BFX': '^BFX',
    'MIB': 'FTSEMIB.MI', 'FTSEMIB': 'FTSEMIB.MI',
    'ATX': '^ATX',
    'JKSE': '^JKSE', 'JAKARTA': '^JKSE',
    'KLCI': '^KLSE', 'KLSE': '^KLSE',
    'SET': '^SET.BK',
    'TADAWUL': '^TASI', 'TASI': '^TASI',
    'JSE': '^J203.JO',
})


def resolve_ticker(user_input):
    """
    Resolve a user-entered ticker to the correct Yahoo Finance symbol.

    - If it's already a valid ticker (starts with ^, has ., etc.), return as-is.
    - If it matches a known index alias (FTSE → ^FTSE, NIKKEI → ^N225), resolve it.
    - Otherwise, return the input uppercased as-is (it's probably a stock ticker).
    """
    cleaned = user_input.strip().upper()
    if not cleaned:
        return cleaned

    # Already looks like an index ticker or international stock
    if cleaned.startswith('^') or '.' in cleaned or '=' in cleaned:
        # Still check if it's a known alias
        return _INDEX_ALIASES.get(cleaned, cleaned)

    # Check alias map
    if cleaned in _INDEX_ALIASES:
        return _INDEX_ALIASES[cleaned]

    return cleaned


def resolve_tickers(ticker_string):
    """
    Parse a comma-separated string of tickers and resolve each one.
    Returns a list of resolved ticker symbols.
    """
    raw = [t.strip() for t in ticker_string.split(',') if t.strip()]
    return [resolve_ticker(t) for t in raw]


def validate_index_ticker(ticker):
    """Validate that a ticker looks legitimate."""
    return bool(re.match(r'^[\^]?[A-Z0-9.\-=]{1,20}$', ticker.upper()))


@lru_cache(maxsize=64)
def fetch_index_data(ticker, start_date, end_date):
    """
    Fetch index price data on-the-fly. Uses LRU cache to avoid
    redundant downloads within the same process.
    Returns a pandas DataFrame with columns: Date, Close, Volume.
    """
    if not validate_index_ticker(ticker):
        raise ValueError(f"Invalid ticker: {ticker}")

    data = yf.download(ticker, start=str(start_date), end=str(end_date), progress=False)

    if data is None or data.empty:
        raise ValueError(
            f"No data found for '{ticker}' between {start_date} and {end_date}. "
            f"The ticker may be invalid or data unavailable."
        )

    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.droplevel(level=1)

    return data


def fetch_fx_rate(currency, base='USD'):
    """Fetch latest FX rate for currency vs base. Returns rate as float."""
    if currency == base:
        return 1.0
    pair = f"{currency}{base}=X"
    try:
        ticker = yf.Ticker(pair)
        rate = ticker.info.get('regularMarketPrice') or ticker.info.get('previousClose')
        if rate:
            return float(rate)
    except Exception:
        pass
    # Try inverse
    pair_inv = f"{base}{currency}=X"
    try:
        ticker = yf.Ticker(pair_inv)
        rate = ticker.info.get('regularMarketPrice') or ticker.info.get('previousClose')
        if rate:
            return 1.0 / float(rate)
    except Exception:
        pass
    return None


def fetch_multiple_fx_rates(currencies, base='USD'):
    """Fetch FX rates for multiple currencies. Returns dict {currency: rate}."""
    rates = {}
    for curr in set(currencies):
        if curr == base:
            rates[curr] = 1.0
        else:
            rate = fetch_fx_rate(curr, base)
            rates[curr] = rate
    return rates

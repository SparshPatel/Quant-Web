import re
import yfinance as yf


SECTOR_CHOICES = [
    ('', 'Any'),
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

# Pre-built universe of liquid US equities
DEFAULT_UNIVERSE = [
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'BRK-B', 'TSLA',
    'UNH', 'JNJ', 'JPM', 'V', 'XOM', 'PG', 'MA', 'HD', 'CVX', 'MRK',
    'LLY', 'ABBV', 'PEP', 'KO', 'COST', 'AVGO', 'WMT', 'MCD', 'CSCO',
    'ACN', 'CRM', 'TMO', 'ABT', 'DHR', 'LIN', 'NEE', 'ADBE', 'NFLX',
    'TXN', 'AMD', 'PM', 'RTX', 'HON', 'UNP', 'LOW', 'INTC', 'AMGN',
    'IBM', 'CAT', 'BA', 'GE', 'SBUX', 'INTU', 'ISRG', 'SPGI', 'PLD',
    'MDLZ', 'GILD', 'BLK', 'ADP', 'SYK', 'BKNG', 'VRTX', 'MMC',
    'PYPL', 'CB', 'CI', 'SO', 'DUK', 'MO', 'ZTS', 'CME', 'CL', 'REGN',
    'PNC', 'USB', 'GS', 'MS', 'SCHW', 'WFC', 'C', 'AIG', 'MMM',
    'GD', 'LMT', 'NOC', 'FDX', 'UPS', 'DE', 'DAL', 'UAL', 'F', 'GM',
    'NKE', 'LULU', 'TGT', 'DG', 'DLTR', 'ORCL', 'NOW', 'SNOW', 'PANW',
]

# International stock universes by region
EUROPE_UNIVERSE = [
    'ASML', 'MC.PA', 'NESN.SW', 'NOVO-B.CO', 'AZN.L', 'SAP.DE',
    'SHEL.L', 'LVMH.PA', 'ROG.SW', 'NOVN.SW', 'OR.PA', 'ULVR.L',
    'SIE.DE', 'DTE.DE', 'AIR.PA', 'BN.PA', 'RMS.PA', 'TTE.PA',
    'ALV.DE', 'SAN.PA', 'BAS.DE', 'RIO.L', 'HSBA.L', 'BP.L',
    'GSK.L', 'DGE.L', 'BARC.L', 'VOD.L', 'LLOY.L', 'ABI.BR',
    'INGA.AS', 'PHIA.AS', 'ERIC-B.ST', 'VOLV-B.ST', 'SEB-A.ST',
]

ASIA_UNIVERSE = [
    '7203.T', '6758.T', '8306.T', '6861.T', '9984.T',  # Japan (Toyota, Sony, MUFG, Keyence, SoftBank)
    '0700.HK', '9988.HK', '0005.HK', '1299.HK', '2318.HK',  # HK (Tencent, Alibaba, HSBC, AIA, Ping An)
    '005930.KS', '000660.KS', '035420.KS',  # Korea (Samsung, SK Hynix, Naver)
    '2330.TW', '2317.TW',  # Taiwan (TSMC, Foxconn)
    'RELIANCE.NS', 'TCS.NS', 'INFY.NS', 'HDFCBANK.NS',  # India
    'BHP.AX', 'CBA.AX', 'CSL.AX', 'WES.AX',  # Australia
    'D05.SI', 'O39.SI',  # Singapore (DBS, OCBC)
]

LATAM_UNIVERSE = [
    'VALE3.SA', 'PETR4.SA', 'ITUB4.SA', 'BBDC4.SA', 'WEGE3.SA',  # Brazil
    'AMX.MX', 'BIMBOA.MX', 'FEMSAUBD.MX',  # Mexico
]

REGION_UNIVERSES = {
    'us': ('US Large-Caps (~100)', DEFAULT_UNIVERSE),
    'europe': ('European Large-Caps (~35)', EUROPE_UNIVERSE),
    'asia': ('Asia-Pacific Large-Caps (~30)', ASIA_UNIVERSE),
    'latam': ('Latin America (~10)', LATAM_UNIVERSE),
    'global': ('Global All (~175)', DEFAULT_UNIVERSE + EUROPE_UNIVERSE + ASIA_UNIVERSE + LATAM_UNIVERSE),
}


def screen_stocks(pe_max=None, pe_min=None, mkt_cap_min=None,
                  div_yield_min=None, sector=None, custom_tickers=None,
                  region='us'):
    if custom_tickers:
        universe = custom_tickers
    elif region in REGION_UNIVERSES:
        universe = REGION_UNIVERSES[region][1]
    else:
        universe = DEFAULT_UNIVERSE
    results = []
    errors = []

    for t in universe:
        t = t.strip().upper()
        if not re.match(r'^[\^]?[A-Z0-9.\-=]{1,20}$', t):
            continue
        try:
            info = yf.Ticker(t).info or {}
            if info.get('quoteType') not in ('EQUITY', 'ETF', None):
                continue

            pe = info.get('trailingPE')
            fwd_pe = info.get('forwardPE')
            cap = info.get('marketCap')
            dy = info.get('dividendYield')
            sec = info.get('sector', '')
            price = info.get('currentPrice') or info.get('regularMarketPrice')
            name = info.get('shortName', t)
            beta = info.get('beta')

            # apply filters
            if pe_max is not None and pe is not None and pe > pe_max:
                continue
            if pe_min is not None and pe is not None and pe < pe_min:
                continue
            if mkt_cap_min is not None and cap is not None and cap < mkt_cap_min:
                continue
            if div_yield_min is not None:
                if dy is None or dy < div_yield_min:
                    continue
            if sector and sec != sector:
                continue

            results.append({
                'ticker': t,
                'name': name,
                'price': f"${price:,.2f}" if price else 'N/A',
                'pe': f"{pe:.1f}" if pe else 'N/A',
                'fwd_pe': f"{fwd_pe:.1f}" if fwd_pe else 'N/A',
                'mkt_cap': _fmt_cap(cap) if cap else 'N/A',
                'mkt_cap_raw': cap or 0,
                'div_yield': f"{dy:.2%}" if dy else 'N/A',
                'sector': sec or 'N/A',
                'beta': f"{beta:.2f}" if beta else 'N/A',
            })
        except Exception:
            errors.append(t)

    # sort by market cap descending
    results.sort(key=lambda x: x['mkt_cap_raw'], reverse=True)

    return {
        'stocks': results,
        'n_results': len(results),
        'n_screened': len(universe),
        'errors': errors,
    }


def _fmt_cap(val):
    if val >= 1e12:
        return f"${val / 1e12:.1f}T"
    if val >= 1e9:
        return f"${val / 1e9:.1f}B"
    if val >= 1e6:
        return f"${val / 1e6:.0f}M"
    return f"${val:,.0f}"

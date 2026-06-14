import re
import yfinance as yf
from datetime import datetime, timedelta


def get_earnings(tickers):
    results = []
    errors = []

    for t in tickers:
        t = t.strip().upper()
        if not re.match(r'^[A-Z0-9.\-]{1,15}$', t):
            errors.append(f"Invalid ticker: {t}")
            continue

        try:
            stock = yf.Ticker(t)
            info = stock.info or {}

            name = info.get('shortName', t)
            price = info.get('currentPrice') or info.get('regularMarketPrice')
            mkt_cap = info.get('marketCap')
            eps = info.get('trailingEps')
            fwd_eps = info.get('forwardEps')
            pe = info.get('trailingPE')

            # earnings dates
            try:
                cal = stock.calendar
                if cal is not None:
                    if isinstance(cal, dict):
                        earn_date = cal.get('Earnings Date')
                        if isinstance(earn_date, list) and earn_date:
                            earn_date = earn_date[0]
                        if hasattr(earn_date, 'strftime'):
                            earn_date = earn_date.strftime('%Y-%m-%d')
                        else:
                            earn_date = str(earn_date) if earn_date else 'N/A'
                    else:
                        earn_date = 'N/A'
                else:
                    earn_date = 'N/A'
            except Exception:
                earn_date = 'N/A'

            # earnings history (recent quarters)
            quarters = []
            try:
                eh = stock.earnings_history
                if eh is not None and not eh.empty:
                    for _, row in eh.tail(4).iterrows():
                        quarters.append({
                            'quarter': str(row.get('quarter', '')),
                            'eps_est': f"{row.get('epsEstimate', 0):.2f}" if row.get('epsEstimate') is not None else 'N/A',
                            'eps_actual': f"{row.get('epsActual', 0):.2f}" if row.get('epsActual') is not None else 'N/A',
                            'surprise': f"{row.get('surprisePercent', 0):.1f}%" if row.get('surprisePercent') is not None else 'N/A',
                        })
            except Exception:
                pass

            results.append({
                'ticker': t,
                'name': name,
                'price': f"${price:,.2f}" if price else 'N/A',
                'mkt_cap': _fmt_cap(mkt_cap) if mkt_cap else 'N/A',
                'eps': f"{eps:.2f}" if eps else 'N/A',
                'fwd_eps': f"{fwd_eps:.2f}" if fwd_eps else 'N/A',
                'pe': f"{pe:.1f}" if pe else 'N/A',
                'earnings_date': earn_date,
                'quarters': quarters,
            })
        except Exception as e:
            errors.append(f"{t}: {e}")

    return {
        'holdings': results,
        'errors': errors,
        'n_holdings': len(results),
    }


def _fmt_cap(val):
    if val >= 1e12:
        return f"${val / 1e12:.1f}T"
    if val >= 1e9:
        return f"${val / 1e9:.1f}B"
    if val >= 1e6:
        return f"${val / 1e6:.0f}M"
    return f"${val:,.0f}"

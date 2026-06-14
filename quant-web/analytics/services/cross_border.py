"""
Cross-Border Portfolio Builder.

Aggregates international portfolio considerations: withholding taxes,
FX conversion costs, settlement differences, regulatory requirements,
and generates a comprehensive cost/risk report.
"""

import numpy as np
from .global_indices import (
    GLOBAL_INDICES, COUNTRY_INFO, FX_CONVERSION_COSTS,
    get_country_info, fetch_fx_rate,
)


def build_cross_border_report(selected_indices, weights=None, home_country='US',
                                annual_dividend_yield=0.02, portfolio_value=1_000_000):
    """
    Build a comprehensive international portfolio cost/risk report.

    Args:
        selected_indices: list of index tickers from GLOBAL_INDICES
        weights: allocation weights (sum to 1). None = equal weight.
        home_country: investor's home country code (e.g. 'US', 'GB', 'SE')
        annual_dividend_yield: assumed portfolio-level dividend yield
        portfolio_value: notional portfolio value in home currency
    """
    if not selected_indices:
        raise ValueError("Select at least one index.")

    n = len(selected_indices)
    if weights is None:
        weights = [1.0 / n] * n
    elif abs(sum(weights) - 1.0) > 0.01:
        raise ValueError("Weights must sum to 1.0")

    home_info = get_country_info(home_country)

    allocations = []
    total_fx_cost = 0.0
    total_wht_cost = 0.0
    total_custody_complexity = 0
    settlement_types = set()
    regulatory_notes = []
    key_risks_all = []

    for i, ticker in enumerate(selected_indices):
        meta = GLOBAL_INDICES.get(ticker)
        if not meta:
            continue

        country = meta['country']
        currency = meta['currency']
        info = get_country_info(country)
        w = weights[i]

        # FX conversion cost
        fx_spread = FX_CONVERSION_COSTS.get(currency, 0.10) / 100.0
        fx_cost_annual = w * fx_spread * 2  # round-trip (buy + sell or rebalance)

        # Withholding tax cost on dividends
        wht_rate = info.get('treaty_rate_pct', info.get('withholding_tax_pct', 15)) / 100.0
        wht_cost = w * annual_dividend_yield * wht_rate

        # Settlement
        settlement = info.get('settlement', 'T+2')
        settlement_types.add(settlement)

        # FX rate
        home_currency = home_info.get('fx_notes', 'USD')
        fx_rate = fetch_fx_rate(currency, 'USD')

        # Custody complexity (rough score 1-5)
        complexity_map = {
            'US': 1, 'GB': 1, 'CA': 1, 'AU': 1, 'DE': 1, 'FR': 1, 'NL': 1,
            'CH': 1, 'JP': 2, 'HK': 2, 'SG': 2, 'SE': 1, 'EU': 1,
            'KR': 3, 'TW': 3, 'IN': 4, 'CN': 5, 'BR': 4, 'MX': 3,
            'ZA': 3, 'SA': 4, 'IL': 2, 'AR': 5, 'CL': 3,
            'ID': 3, 'MY': 2, 'TH': 3,
        }
        complexity = complexity_map.get(country, 3)
        total_custody_complexity += complexity * w

        total_fx_cost += fx_cost_annual
        total_wht_cost += wht_cost

        # Key risks
        for risk in info.get('key_risks', []):
            key_risks_all.append(f"{meta['flag']} {risk}")

        # Regulatory notes
        reg = info.get('regulatory_body', 'Unknown')
        custody_note = info.get('custody_notes', '')
        if custody_note:
            regulatory_notes.append({
                'country': f"{meta['flag']} {meta['name']} ({country})",
                'regulator': reg,
                'note': custody_note,
            })

        allocations.append({
            'ticker': ticker,
            'name': f"{meta['flag']} {meta['name']}",
            'country': country,
            'currency': currency,
            'weight': f"{w:.1%}",
            'weight_raw': w,
            'exchange': meta.get('exchange', ''),
            'settlement': settlement,
            'wht_statutory': f"{info.get('withholding_tax_pct', '?')}%",
            'wht_treaty': f"{info.get('treaty_rate_pct', '?')}%",
            'fx_spread': f"{FX_CONVERSION_COSTS.get(currency, 0.10):.2f}%",
            'fx_rate_vs_usd': f"{fx_rate:.4f}" if fx_rate else 'N/A',
            'capital_gains_note': info.get('capital_gains_tax_note', ''),
            'custody_complexity': complexity,
            'complexity_label': ['', 'Simple', 'Easy', 'Moderate', 'Complex', 'Very Complex'][min(complexity, 5)],
        })

    # -- Cost summary --
    total_cost_pct = total_fx_cost + total_wht_cost
    total_cost_abs = total_cost_pct * portfolio_value

    # Estimated custody fee (based on complexity)
    custody_fee_pct = 0.02 + (total_custody_complexity * 0.005)  # base + complexity premium
    custody_fee_abs = custody_fee_pct / 100 * portfolio_value

    cost_summary = {
        'fx_conversion_cost': f"{total_fx_cost:.3%}",
        'fx_conversion_abs': f"${total_fx_cost * portfolio_value:,.0f}",
        'withholding_tax_cost': f"{total_wht_cost:.3%}",
        'withholding_tax_abs': f"${total_wht_cost * portfolio_value:,.0f}",
        'est_custody_fee': f"{custody_fee_pct:.3f}%",
        'est_custody_abs': f"${custody_fee_abs:,.0f}",
        'total_annual_cost': f"{total_cost_pct + custody_fee_pct / 100:.3%}",
        'total_annual_abs': f"${total_cost_abs + custody_fee_abs:,.0f}",
        'portfolio_value': f"${portfolio_value:,.0f}",
    }

    # -- Settlement risk --
    settlement_summary = []
    for s in sorted(settlement_types):
        countries = [a['name'] for a in allocations if a['settlement'] == s]
        settlement_summary.append({
            'settlement': s,
            'countries': ', '.join(countries),
            'note': 'Standard' if s == 'T+2' else ('Faster settlement' if s == 'T+1' else 'Slower — cash planning needed'),
        })

    # -- Region breakdown --
    region_weights = {}
    for a in allocations:
        meta = GLOBAL_INDICES.get(a['ticker'], {})
        region = meta.get('region', 'Other')
        region_weights[region] = region_weights.get(region, 0) + a['weight_raw']

    region_breakdown = [
        {'region': r, 'weight': f"{w:.1%}"}
        for r, w in sorted(region_weights.items(), key=lambda x: x[1], reverse=True)
    ]

    # -- Currency breakdown --
    currency_weights = {}
    for a in allocations:
        currency_weights[a['currency']] = currency_weights.get(a['currency'], 0) + a['weight_raw']

    currency_breakdown = [
        {'currency': c, 'weight': f"{w:.1%}", 'fx_spread': f"{FX_CONVERSION_COSTS.get(c, 0.10):.2f}%"}
        for c, w in sorted(currency_weights.items(), key=lambda x: x[1], reverse=True)
    ]

    # -- Diversification score (simple HHI-based) --
    region_vals = list(region_weights.values())
    hhi = sum(v ** 2 for v in region_vals)
    div_score = max(0, min(100, int((1 - hhi) * 100 * 1.5)))

    # -- Trading hours overlap advisory --
    hours_note = _trading_hours_advisory(allocations)

    return {
        'allocations': allocations,
        'cost_summary': cost_summary,
        'settlement_summary': settlement_summary,
        'region_breakdown': region_breakdown,
        'currency_breakdown': currency_breakdown,
        'regulatory_notes': regulatory_notes,
        'key_risks': key_risks_all[:15],  # top 15
        'diversification_score': div_score,
        'hours_advisory': hours_note,
        'n_countries': len(set(a['country'] for a in allocations)),
        'n_currencies': len(currency_weights),
        'home_country': home_country,
    }


def _trading_hours_advisory(allocations):
    """Generate a note about trading hour overlaps."""
    has_us = any(a['country'] == 'US' for a in allocations)
    has_eu = any(a['country'] in ('GB', 'DE', 'FR', 'NL', 'CH', 'SE', 'ES', 'IT', 'BE', 'DK', 'FI', 'PT', 'AT') for a in allocations)
    has_asia = any(a['country'] in ('JP', 'HK', 'CN', 'KR', 'TW', 'SG', 'IN', 'AU', 'NZ', 'ID', 'MY', 'TH') for a in allocations)

    notes = []
    if has_us and has_asia:
        notes.append("US and Asian markets have no overlapping trading hours. "
                     "Consider pre/post-market orders or next-day execution for rebalancing.")
    if has_eu and has_asia:
        notes.append("European and Asian markets overlap briefly in the early European morning. "
                     "Liquidity may be thin during overlap.")
    if has_us and has_eu:
        notes.append("US and European markets overlap ~14:30-17:30 CET (9:30-11:30 ET). "
                     "Best window for cross-Atlantic rebalancing.")
    if not notes:
        notes.append("All selected markets operate in similar time zones.")

    return notes

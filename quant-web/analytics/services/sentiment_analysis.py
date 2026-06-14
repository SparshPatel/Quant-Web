import re
import numpy as np
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta


def analyze_sentiment(ticker):
    ticker = ticker.strip().upper()
    if not re.match(r'^[\^]?[A-Z0-9.\-=]{1,20}$', ticker):
        raise ValueError(f"Invalid ticker: {ticker}")

    stock = yf.Ticker(ticker)
    info = stock.info
    if not info or info.get('quoteType') not in ('EQUITY', 'ETF'):
        raise ValueError(f"'{ticker}' is not a valid equity / ETF.")

    company_name = info.get('shortName', ticker)

    # --- News items ---
    news_items = stock.news or []
    parsed_news = []
    for item in news_items[:20]:
        content = item.get('content', {})
        title = content.get('title', 'No title')
        provider = content.get('provider', {}).get('displayName', 'Unknown')
        pub_date = content.get('pubDate', '')
        link = content.get('canonicalUrl', {}).get('url', '')
        # Simple keyword-based sentiment scoring
        score = _keyword_score(title)
        parsed_news.append({
            'title': title,
            'provider': provider,
            'date': pub_date[:10] if pub_date else '',
            'link': link,
            'score': score,
            'label': _label(score),
        })

    # --- Aggregate sentiment ---
    scores = [n['score'] for n in parsed_news]
    avg_score = np.mean(scores) if scores else 0.0
    pos_count = sum(1 for s in scores if s > 0.1)
    neg_count = sum(1 for s in scores if s < -0.1)
    neu_count = len(scores) - pos_count - neg_count

    # --- Analyst recommendations (upgrades / downgrades) ---
    recs = []
    try:
        ud_df = stock.upgrades_downgrades
        if ud_df is not None and not ud_df.empty:
            recent = ud_df.head(15)  # most recent first
            for idx, row in recent.iterrows():
                date_str = str(idx)[:10] if idx is not None else ''
                recs.append({
                    'date': date_str,
                    'firm': row.get('Firm', 'Unknown'),
                    'grade': row.get('ToGrade', ''),
                    'from_grade': row.get('FromGrade', ''),
                    'action': row.get('Action', ''),
                })
    except Exception:
        pass

    # --- Aggregate recommendation summary ---
    rec_summary = {}
    try:
        rec_df = stock.recommendations
        if rec_df is not None and not rec_df.empty:
            latest = rec_df.iloc[0]
            rec_summary = {
                'strong_buy': int(latest.get('strongBuy', 0)),
                'buy': int(latest.get('buy', 0)),
                'hold': int(latest.get('hold', 0)),
                'sell': int(latest.get('sell', 0)),
                'strong_sell': int(latest.get('strongSell', 0)),
            }
    except Exception:
        pass

    # --- Key fundamentals context ---
    pe = info.get('trailingPE')
    fwd_pe = info.get('forwardPE')
    pb = info.get('priceToBook')
    div_yield = info.get('dividendYield')
    mkt_cap = info.get('marketCap')
    beta = info.get('beta')
    target_mean = info.get('targetMeanPrice')
    current_price = info.get('currentPrice') or info.get('regularMarketPrice')

    upside = None
    if target_mean and current_price and current_price > 0:
        upside = (target_mean - current_price) / current_price

    # --- Sentiment gauge chart ---
    fig_gauge = go.Figure(go.Indicator(
        mode='gauge+number',
        value=avg_score,
        number={'suffix': '', 'valueformat': '.2f'},
        gauge=dict(
            axis=dict(range=[-1, 1], tickwidth=1),
            bar=dict(color='royalblue'),
            steps=[
                dict(range=[-1, -0.3], color='rgba(220,20,60,0.25)'),
                dict(range=[-0.3, 0.3], color='rgba(200,200,200,0.25)'),
                dict(range=[0.3, 1], color='rgba(34,139,34,0.25)'),
            ],
            threshold=dict(line=dict(color='black', width=2), thickness=0.75, value=avg_score)),
        title=dict(text='News Sentiment Score')))
    fig_gauge.update_layout(height=300, margin=dict(l=30, r=30, t=60, b=20))

    # --- Sentiment distribution bar ---
    fig_bar = go.Figure(data=[
        go.Bar(x=['Positive', 'Neutral', 'Negative'],
               y=[pos_count, neu_count, neg_count],
               marker_color=['forestgreen', 'gray', 'crimson'])])
    fig_bar.update_layout(
        title='Sentiment Distribution', yaxis_title='Count',
        template='plotly_white', height=300,
        margin=dict(l=40, r=20, t=50, b=40))

    return {
        'ticker': ticker,
        'company_name': company_name,
        'news': parsed_news,
        'n_articles': len(parsed_news),
        'avg_score': f"{avg_score:.2f}",
        'overall_label': _label(avg_score),
        'pos_count': pos_count,
        'neg_count': neg_count,
        'neu_count': neu_count,
        'recommendations': recs,
        'rec_summary': rec_summary,
        'pe': f"{pe:.1f}" if pe else 'N/A',
        'fwd_pe': f"{fwd_pe:.1f}" if fwd_pe else 'N/A',
        'pb': f"{pb:.2f}" if pb else 'N/A',
        'div_yield': f"{div_yield:.2%}" if div_yield else 'N/A',
        'mkt_cap': _fmt_cap(mkt_cap) if mkt_cap else 'N/A',
        'beta': f"{beta:.2f}" if beta else 'N/A',
        'current_price': f"${current_price:,.2f}" if current_price else 'N/A',
        'target_price': f"${target_mean:,.2f}" if target_mean else 'N/A',
        'upside': f"{upside:.1%}" if upside is not None else 'N/A',
        'gauge_chart': fig_gauge.to_html(full_html=False, include_plotlyjs=False),
        'bar_chart': fig_bar.to_html(full_html=False, include_plotlyjs=False),
    }


# ---------- helpers ----------

_POSITIVE = [
    'beat', 'surge', 'rally', 'gain', 'profit', 'upgrade', 'outperform',
    'record', 'boost', 'strong', 'growth', 'bullish', 'buy', 'positive',
    'up', 'high', 'rise', 'soar', 'jump', 'recover', 'optimis',
]
_NEGATIVE = [
    'miss', 'drop', 'fall', 'loss', 'decline', 'downgrade', 'underperform',
    'weak', 'cut', 'bearish', 'sell', 'negative', 'down', 'low', 'crash',
    'plunge', 'slump', 'risk', 'warn', 'fear', 'pessimis',
]


def _keyword_score(text):
    text_lower = text.lower()
    pos = sum(1 for w in _POSITIVE if w in text_lower)
    neg = sum(1 for w in _NEGATIVE if w in text_lower)
    total = pos + neg
    if total == 0:
        return 0.0
    return (pos - neg) / total


def _label(score):
    if score > 0.1:
        return 'Positive'
    elif score < -0.1:
        return 'Negative'
    return 'Neutral'


def _fmt_cap(val):
    if val >= 1e12:
        return f"${val / 1e12:.1f}T"
    if val >= 1e9:
        return f"${val / 1e9:.1f}B"
    if val >= 1e6:
        return f"${val / 1e6:.0f}M"
    return f"${val:,.0f}"

import re
import io
import ssl
import zipfile
import urllib.request
import numpy as np
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import statsmodels.api as sm


# Fama-French daily factors URL (Kenneth French's data library)
FF_URL = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/F-F_Research_Data_5_Factors_2x3_daily_CSV.zip"
MOM_URL = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/F-F_Momentum_Factor_daily_CSV.zip"

# SSL context that skips certificate verification (needed behind corporate proxies)
_ssl_ctx = ssl.create_default_context()
_ssl_ctx.check_hostname = False
_ssl_ctx.verify_mode = ssl.CERT_NONE


def _read_csv_from_zip_url(url, skiprows):
    """Download a zipped CSV from *url*, bypassing SSL verification."""
    req = urllib.request.urlopen(url, context=_ssl_ctx)
    with zipfile.ZipFile(io.BytesIO(req.read())) as zf:
        csv_name = [n for n in zf.namelist() if n.endswith('.CSV') or n.endswith('.csv')][0]
        with zf.open(csv_name) as f:
            return pd.read_csv(f, skiprows=skiprows, index_col=0)


def _load_ff_factors():
    """Load Fama-French 5 factors + Momentum from Kenneth French's website."""
    # 5 factors
    ff5 = _read_csv_from_zip_url(FF_URL, skiprows=3)
    # find where the annual section starts (blank row or non-numeric index)
    valid = ff5.index.astype(str).str.match(r'^\d{8}$')
    ff5 = ff5.loc[valid].copy()
    ff5.index = pd.to_datetime(ff5.index, format='%Y%m%d')
    for c in ff5.columns:
        ff5[c] = pd.to_numeric(ff5[c], errors='coerce') / 100  # percent → decimal

    # momentum
    try:
        mom = _read_csv_from_zip_url(MOM_URL, skiprows=13)
        valid_m = mom.index.astype(str).str.match(r'^\d{8}$')
        mom = mom.loc[valid_m].copy()
        mom.index = pd.to_datetime(mom.index, format='%Y%m%d')
        mom.columns = [c.strip() for c in mom.columns]
        if 'Mom   ' in mom.columns:
            mom.rename(columns={'Mom   ': 'Mom'}, inplace=True)
        for c in mom.columns:
            mom[c] = pd.to_numeric(mom[c], errors='coerce') / 100
        ff5 = ff5.join(mom[['Mom']], how='left')
    except Exception:
        ff5['Mom'] = np.nan

    ff5.columns = [c.strip() for c in ff5.columns]
    return ff5


def analyze_factors(tickers, start_date, end_date):
    for t in tickers:
        if not re.match(r'^[\^]?[A-Z0-9.\-=]{1,20}$', t):
            raise ValueError(f"Invalid ticker: {t}")
    if len(tickers) < 1:
        raise ValueError("Need at least 1 ticker.")

    prices = yf.download(tickers if len(tickers) > 1 else tickers[0],
                         start=start_date, end=end_date)['Close']
    if isinstance(prices, pd.Series):
        prices = prices.to_frame(tickers[0])
    returns = prices.pct_change().dropna()
    if len(returns) < 60:
        raise ValueError("Need at least 60 trading days.")

    tickers_sorted = list(returns.columns)
    n = len(tickers_sorted)

    # equal-weight portfolio
    port_ret = returns.mean(axis=1)

    # load factors
    try:
        ff = _load_ff_factors()
    except Exception as e:
        raise ValueError(f"Could not download Fama-French factors: {e}")

    # align dates
    merged = pd.DataFrame({'port': port_ret}).join(ff, how='inner')
    merged.dropna(subset=['Mkt-RF', 'SMB', 'HML', 'RF'], inplace=True)
    if len(merged) < 30:
        raise ValueError("Not enough overlapping data with factor series.")

    excess_ret = merged['port'] - merged['RF']

    # determine which factors are available
    factor_cols = ['Mkt-RF', 'SMB', 'HML']
    if 'RMW' in merged.columns and merged['RMW'].notna().sum() > 30:
        factor_cols.append('RMW')
    if 'CMA' in merged.columns and merged['CMA'].notna().sum() > 30:
        factor_cols.append('CMA')
    if 'Mom' in merged.columns and merged['Mom'].notna().sum() > 30:
        factor_cols.append('Mom')

    X = sm.add_constant(merged[factor_cols].fillna(0))
    model = sm.OLS(excess_ret, X).fit()

    # --- results ---
    factor_results = []
    for f in factor_cols:
        coef = model.params.get(f, 0)
        pval = model.pvalues.get(f, 1)
        factor_results.append({
            'factor': f,
            'beta': f"{coef:.4f}",
            't_stat': f"{model.tvalues.get(f, 0):.2f}",
            'p_value': f"{pval:.4f}",
            'significant': pval < 0.05,
        })

    alpha_ann = model.params.get('const', 0) * 252
    r_squared = model.rsquared
    adj_r_squared = model.rsquared_adj

    # --- bar chart of betas ---
    betas = [model.params.get(f, 0) for f in factor_cols]
    colors = ['forestgreen' if b > 0 else 'crimson' for b in betas]

    fig_beta = go.Figure(data=[
        go.Bar(x=factor_cols, y=betas, marker_color=colors,
               text=[f"{b:.3f}" for b in betas], textposition='outside')])
    fig_beta.update_layout(
        title='Factor Exposures (Betas)',
        yaxis_title='Beta', template='plotly_white', height=400,
        margin=dict(l=40, r=20, t=50, b=40))

    # --- cumulative factor contribution ---
    contributions = {}
    for f in factor_cols:
        contributions[f] = (merged[f] * model.params.get(f, 0)).cumsum()

    fig_contrib = go.Figure()
    fig_contrib.add_trace(go.Scatter(
        x=merged.index, y=excess_ret.cumsum().values,
        mode='lines', name='Portfolio (excess)',
        line=dict(width=2, color='black')))
    palette = ['royalblue', 'forestgreen', 'crimson', 'orange', 'purple', 'teal']
    for i, f in enumerate(factor_cols):
        fig_contrib.add_trace(go.Scatter(
            x=merged.index, y=contributions[f].values,
            mode='lines', name=f,
            line=dict(width=1.5, color=palette[i % len(palette)])))
    fig_contrib.update_layout(
        title='Cumulative Factor Contributions',
        xaxis_title='Date', yaxis_title='Cumulative Return',
        template='plotly_white', height=400,
        margin=dict(l=40, r=20, t=50, b=40))

    return {
        'tickers': ', '.join(tickers_sorted),
        'n_days': len(merged),
        'date_range': f"{merged.index[0].date()} to {merged.index[-1].date()}",
        'alpha_daily': f"{model.params.get('const', 0):.6f}",
        'alpha_ann': f"{alpha_ann:.2%}",
        'alpha_pval': f"{model.pvalues.get('const', 1):.4f}",
        'r_squared': f"{r_squared:.4f}",
        'adj_r_squared': f"{adj_r_squared:.4f}",
        'factors': factor_results,
        'beta_chart': fig_beta.to_html(full_html=False, include_plotlyjs=False),
        'contrib_chart': fig_contrib.to_html(full_html=False, include_plotlyjs=False),
    }

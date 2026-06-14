import re
import numpy as np
import pandas as pd
import yfinance as yf
from hmmlearn.hmm import GaussianHMM
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def validate_ticker(ticker):
    return bool(re.match(r'^[\^]?[A-Z0-9.\-=]{1,20}$', ticker.upper()))


def cluster_regimes(ticker, start_date, end_date, n_regimes=3):
    if not validate_ticker(ticker):
        raise ValueError(f"Invalid ticker symbol: {ticker}")

    data = yf.download(ticker, start=start_date, end=end_date)

    if data is None or data.empty:
        raise ValueError(f"No price data found for '{ticker}'. Check the symbol and try again.")

    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.droplevel(level=1)

    if 'Close' not in data.columns:
        raise ValueError(f"No 'Close' price column found for '{ticker}'.")

    if len(data) < 60:
        raise ValueError(f"Only {len(data)} trading days found for '{ticker}'. Need at least 60. Try a wider date range.")

    data['returns'] = data['Close'].pct_change()
    data['rolling_return'] = data['returns'].rolling(window=21).mean()
    data['rolling_vol'] = data['returns'].rolling(window=21).std()
    data.dropna(inplace=True)

    features = data[['rolling_return', 'rolling_vol']].values

    model = GaussianHMM(
        n_components=n_regimes, covariance_type='full',
        n_iter=1000, random_state=42)
    model.fit(features)

    hidden_states = model.predict(features)
    data['regime'] = hidden_states

    # Regime stats
    regime_stats = []
    for i in range(n_regimes):
        mask = data['regime'] == i
        n_days = int(mask.sum())
        if n_days > 0:
            ann_ret = data.loc[mask, 'returns'].mean() * 252
            ann_vol = data.loc[mask, 'rolling_vol'].mean() * np.sqrt(252)
        else:
            ann_ret = 0.0
            ann_vol = 0.0
        regime_stats.append({
            'regime': i,
            'ann_return_raw': ann_ret,
            'ann_vol_raw': ann_vol,
            'ann_return': f"{ann_ret:.2%}",
            'ann_vol': f"{ann_vol:.2%}",
            'days': n_days,
        })

    # Sort regimes by return for labeling
    regime_stats.sort(key=lambda x: x['ann_return_raw'], reverse=True)

    # Assign descriptive labels based on return/vol characteristics
    _LABEL_SETS = {
        2: [('Bull / Risk-On',  '#2ecc71'), ('Bear / Risk-Off', '#e74c3c')],
        3: [('Bull / Rally',    '#2ecc71'), ('Sideways / Normal', '#f39c12'), ('Bear / Crisis', '#e74c3c')],
        4: [('Strong Bull',     '#27ae60'), ('Mild Bull',  '#2ecc71'), ('Mild Bear', '#f39c12'), ('Bear / Crisis', '#e74c3c')],
        5: [('Strong Bull',     '#27ae60'), ('Bull',       '#2ecc71'), ('Sideways',  '#f39c12'),
            ('Bear',            '#e67e22'), ('Crash / Crisis', '#e74c3c')],
    }
    labels = _LABEL_SETS.get(n_regimes,
        [(f'Regime {i}', ['#2ecc71','#e74c3c','#f39c12','#3498db','#9b59b6'][i % 5]) for i in range(n_regimes)])
    for idx, rs in enumerate(regime_stats):
        rs['label'] = labels[idx][0]
        rs['color'] = labels[idx][1]

    # Build a map from regime number → label for the chart
    regime_label_map = {rs['regime']: rs['label'] for rs in regime_stats}
    regime_color_map = {rs['regime']: rs['color'] for rs in regime_stats}

    # Price chart colored by regime
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.65, 0.35],
                        vertical_spacing=0.06)

    for i in range(n_regimes):
        mask = data['regime'] == i
        fig.add_trace(go.Scatter(
            x=data.index[mask], y=data['Close'][mask],
            mode='markers', marker=dict(color=regime_color_map[i], size=3),
            name=f'{regime_label_map[i]}', legendgroup=f'r{i}'), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=data.index, y=data['rolling_vol'] * np.sqrt(252),
        mode='lines', line=dict(color='black', width=0.8),
        name='Rolling Vol', showlegend=False), row=2, col=1)

    fig.update_layout(
        title=f'{ticker} — Market Regime Clustering ({n_regimes} States)',
        template='plotly_white', height=600,
        margin=dict(l=40, r=20, t=50, b=40))
    fig.update_yaxes(title_text='Price ($)', row=1, col=1)
    fig.update_yaxes(title_text='Ann. Volatility', row=2, col=1)

    return {
        'regime_stats': regime_stats,
        'chart': fig.to_html(full_html=False, include_plotlyjs=False),
        'n_days': len(data),
        'date_range': f"{data.index[0].date()} to {data.index[-1].date()}",
    }

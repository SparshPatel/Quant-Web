import io
import base64
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime


def _fig_to_png_base64(fig_html):
    """Convert plotly HTML to a placeholder — actual rendering handled in template."""
    return fig_html


def generate_pdf_report(tool_name, results, params=None):
    """
    Build an HTML report suitable for browser print-to-PDF.

    Parameters
    ----------
    tool_name : str   – display name of the tool
    results : dict     – the results dict from the service
    params : dict      – the form parameters used

    Returns an HTML string ready for rendering.
    """
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')

    # Collect all charts from results
    charts = []
    for key, val in results.items():
        if isinstance(val, str) and ('plotly' in val.lower() or '<div' in val):
            charts.append(val)

    # Collect KPI-like values (non-chart, non-list strings)
    kpis = {}
    for key, val in results.items():
        if isinstance(val, (str, int, float)) and not isinstance(val, str):
            kpis[key.replace('_', ' ').title()] = val
        elif isinstance(val, str) and '<div' not in val and len(val) < 50:
            kpis[key.replace('_', ' ').title()] = val

    # Build HTML
    html_parts = [
        f'<div class="report-header text-center mb-4">',
        f'<h2>{tool_name} Report</h2>',
        f'<p class="text-muted">Generated {timestamp} — KappaQuant</p>',
    ]

    if params:
        html_parts.append('<div class="card border-0 shadow-sm mb-3"><div class="card-body">')
        html_parts.append('<h6>Parameters</h6><ul class="list-unstyled mb-0">')
        for k, v in params.items():
            html_parts.append(f'<li><strong>{k.replace("_", " ").title()}:</strong> {v}</li>')
        html_parts.append('</ul></div></div>')

    if kpis:
        html_parts.append('<div class="row g-3 mb-4">')
        for label, val in list(kpis.items())[:8]:
            html_parts.append(
                f'<div class="col-md-3">'
                f'<div class="card border-0 shadow-sm text-center p-3">'
                f'<small class="text-muted">{label}</small>'
                f'<h5 class="mb-0">{val}</h5>'
                f'</div></div>'
            )
        html_parts.append('</div>')

    html_parts.append('</div>')

    for chart in charts:
        html_parts.append(f'<div class="card border-0 shadow-sm mb-4"><div class="card-body">{chart}</div></div>')

    return '\n'.join(html_parts)

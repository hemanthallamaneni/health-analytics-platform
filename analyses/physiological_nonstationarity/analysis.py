# analyses/physiological_nonstationarity/analysis.py
# Physiological Nonstationarity Investigation
# Signals: Average HRV, Lowest Heart Rate, Sleep Efficiency, Readiness Score
# Methods: ADF, KPSS, PELT (ruptures), Detection Latency vs 30-day Rolling Mean
#
# NOTE ON BOCPD: A custom Adams & MacKay (2007) implementation was attempted.
# The implementation collapsed to the prior hazard rate (1/λ = 0.033) at every
# timestep — output was constant and uninformative. Root cause: underflow in the
# Student-T predictive likelihood as Normal-Gamma sufficient statistics tighten
# with run length. A stable implementation requires log-space message passing
# and is deferred to future work.

import os
import sys

# TODO(audit H3): sys.path workaround removable once pyproject.toml declares
# [build-system] and `uv sync` installs the ingestion package into the venv.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from ingestion.common.snowflake_auth import load_private_key

import numpy as np
import pandas as pd
from dotenv import load_dotenv
import snowflake.connector
from statsmodels.tsa.stattools import adfuller, kpss
import ruptures as rpt
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec
import warnings
warnings.filterwarnings('ignore')

load_dotenv()

# ── 1. DATA PULL ──────────────────────────────────────────────────────────────

conn = snowflake.connector.connect(
    user=os.environ["SNOWFLAKE_USER"],
    private_key=load_private_key(os.environ["SNOWFLAKE_PRIVATE_KEY_PATH"]),
    account=os.environ["SNOWFLAKE_ACCOUNT"],
    warehouse=os.environ["SNOWFLAKE_WAREHOUSE"],
    database=os.environ["SNOWFLAKE_DATABASE"],
    schema="MART_HEALTH"
)

df = pd.read_sql("""
    SELECT ACTIVITY_DATE, AVERAGE_HRV, LOWEST_HEART_RATE,
           SLEEP_EFFICIENCY, READINESS_SCORE
    FROM MART_HEALTH.DAILY_HEALTH_SUMMARY
    ORDER BY ACTIVITY_DATE
""", conn)
conn.close()

df['ACTIVITY_DATE'] = pd.to_datetime(df['ACTIVITY_DATE'])
df = df.set_index('ACTIVITY_DATE')

print(f"\n=== DATA LOADED ===")
print(f"Rows: {len(df)} | Range: {df.index.min().date()} → {df.index.max().date()}")
print("\nMissing values per signal:")
print(df.isnull().sum())

# Signal display label → (column name, hex color)
SIGNALS = {
    'HRV (ms)':             ('AVERAGE_HRV',      '#3B6FD4'),
    'Resting HR (bpm)':     ('LOWEST_HEART_RATE', '#C0392B'),
    'Sleep Efficiency (%)': ('SLEEP_EFFICIENCY',  '#27AE60'),
    'Readiness Score':      ('READINESS_SCORE',   '#E67E22'),
}

series_map = {
    label: df[col].dropna()
    for label, (col, _) in SIGNALS.items()
}

# ── 2. STATIONARITY TESTS ─────────────────────────────────────────────────────

print("\n" + "="*90)
print("STATIONARITY TESTS (ADF + KPSS)")
print("ADF H0: unit root (non-stationary) — Reject → stationary")
print("KPSS H0: stationary               — Reject → non-stationary")
print("Both reject simultaneously        → trend-stationary (stationary around drift)")
print("="*90)
print(f"{'Signal':<24} {'ADF Stat':>10} {'ADF p':>8} {'ADF':>10} | "
      f"{'KPSS Stat':>10} {'KPSS p':>8} {'KPSS':>10} | {'Verdict':>18}")
print("-"*108)

stationarity_rows = []

for label, series in series_map.items():
    adf_stat, adf_p, _, _, _, _ = adfuller(series, autolag='AIC')
    adf_result = "Reject H0" if adf_p < 0.05 else "Fail"

    kpss_stat, kpss_p, _, _ = kpss(series, regression='c', nlags='auto')
    kpss_result = "Reject H0" if kpss_p < 0.05 else "Fail"

    if adf_result == "Fail" and kpss_result == "Reject H0":
        verdict = "Non-stationary"
    elif adf_result == "Reject H0" and kpss_result == "Fail":
        verdict = "Stationary"
    elif adf_result == "Reject H0" and kpss_result == "Reject H0":
        verdict = "Trend-stationary"
    else:
        verdict = "Ambiguous"

    print(f"{label:<24} {adf_stat:>10.3f} {adf_p:>8.4f} {adf_result:>10} | "
          f"{kpss_stat:>10.3f} {kpss_p:>8.4f} {kpss_result:>10} | {verdict:>18}")

    stationarity_rows.append({
        'Signal': label,
        'ADF Stat': round(adf_stat, 4), 'ADF p': round(adf_p, 4), 'ADF Result': adf_result,
        'KPSS Stat': round(kpss_stat, 4), 'KPSS p': round(kpss_p, 4), 'KPSS Result': kpss_result,
        'Verdict': verdict,
    })

os.makedirs('analyses/physiological_nonstationarity/results', exist_ok=True)
pd.DataFrame(stationarity_rows).to_csv(
    'analyses/physiological_nonstationarity/results/stationarity_tests.csv', index=False)
print("\nSaved → results/stationarity_tests.csv")

# ── 3. PELT CHANGE-POINT DETECTION ───────────────────────────────────────────

print("\n" + "="*90)
print("PELT CHANGE-POINT DETECTION (RBF kernel, min_size=14 days, pen=10)")
print("="*90)

pelt_changepoints = {}  # label → [Timestamp, ...]
MIN_SIZE = 14

for label, series in series_map.items():
    arr  = series.values.reshape(-1, 1)
    algo = rpt.KernelCPD(kernel="rbf", min_size=MIN_SIZE).fit(arr)
    cps  = algo.predict(pen=10)
    dates = [series.index[i - 1] for i in cps[:-1]]
    pelt_changepoints[label] = dates
    print(f"{label:<24}: {len(dates)} CP(s) → {[str(d.date()) for d in dates]}")

# ── 4. REGIME MEANS ───────────────────────────────────────────────────────────

print("\n" + "="*90)
print("REGIME MEANS BEFORE / AFTER EACH CHANGE-POINT")
print("="*90)

regime_rows = []
for label, series in series_map.items():
    for cp in pelt_changepoints[label]:
        before    = series[series.index <= cp].mean()
        after     = series[series.index >  cp].mean()
        direction = "↓ DOWN" if after < before else "↑ UP"
        delta     = abs(after - before)
        pct       = delta / before * 100
        print(f"{label:<24}: before={before:.2f}  after={after:.2f}  "
              f"{direction}  Δ={delta:.2f} ({pct:.1f}%)")
        regime_rows.append({
            'Signal': label, 'CP Date': cp.date(),
            'Before Mean': round(before, 2), 'After Mean': round(after, 2),
            'Delta': round(delta, 2), 'Pct Change': round(pct, 1),
            'Direction': direction,
        })

pd.DataFrame(regime_rows).to_csv(
    'analyses/physiological_nonstationarity/results/regime_means.csv', index=False)
print("\nSaved → results/regime_means.csv")

# ── 5. DETECTION LATENCY ──────────────────────────────────────────────────────

print("\n" + "="*90)
print("DETECTION LATENCY: PELT vs 30-day Rolling Mean (>1 SD from prior regime mean)")
print("="*90)

latency_rows = []
for label, series in series_map.items():
    rolling_mean = series.rolling(30, min_periods=10).mean()
    pm = series.mean()
    ps = series.std()

    for cp in pelt_changepoints[label]:
        post         = series[series.index > cp]
        flagged_date = None
        for d in post.index:
            if abs(rolling_mean[d] - pm) > ps:
                flagged_date = d
                break

        latency = (flagged_date - cp).days if flagged_date else None
        latency_rows.append({
            'Signal':            label,
            'PELT CP Date':      cp.date(),
            'Rolling Flag Date': flagged_date.date() if flagged_date else 'Not flagged',
            'Latency (days)':    latency,
        })

latency_df = pd.DataFrame(latency_rows)
print(latency_df.to_string(index=False))
latency_df.to_csv(
    'analyses/physiological_nonstationarity/results/detection_latency.csv', index=False)
print("\nSaved → results/detection_latency.csv")

# ── 6. ANNOTATION MAP (edit here when events are confirmed) ───────────────────

# Maps change-point Timestamps → event label for chart annotation.
# Update this dict as new change-points are detected in future runs.
EVENT_ANNOTATIONS = {
    pd.Timestamp('2025-12-27'): 'Travel disruption',
    pd.Timestamp('2026-02-27'): 'Marathon block begins',
}

# ── 7. CHART ──────────────────────────────────────────────────────────────────

plt.rcParams.update({
    'font.family':        'DejaVu Sans',
    'font.size':          10,
    'axes.spines.top':    False,
    'axes.spines.right':  False,
    'axes.spines.left':   True,
    'axes.spines.bottom': True,
    'axes.linewidth':     0.8,
    'xtick.labelsize':    9,
    'ytick.labelsize':    9,
    'grid.color':         '#E5E5E5',
    'grid.linewidth':     0.6,
    'figure.facecolor':   'white',
    'axes.facecolor':     'white',
})

fig = plt.figure(figsize=(14, 13))
fig.patch.set_facecolor('white')

fig.text(0.055, 0.977,
         'Physiological Regime Analysis  ·  Nov 2025 – Apr 2026',
         fontsize=14, fontweight='bold', color='#1A1A1A', va='top')
fig.text(0.055, 0.959,
         'PELT change-point detection (RBF kernel) vs 30-day rolling mean  '
         '·  n = 130 days  ·  Oura Ring Gen3',
         fontsize=9, color='#666666', va='top')

gs   = GridSpec(4, 1, figure=fig,
                top=0.93, bottom=0.08, hspace=0.12, left=0.08, right=0.97)
axes = [fig.add_subplot(gs[i]) for i in range(4)]

for ax, (label, (col, color)) in zip(axes, SIGNALS.items()):
    series = series_map[label]
    roll   = series.rolling(30, min_periods=10).mean()
    cps    = pelt_changepoints[label]          # live — always matches analysis

    # Alternating regime shading
    boundaries = [series.index.min()] + cps + [series.index.max()]
    for i in range(len(boundaries) - 1):
        ax.axvspan(boundaries[i], boundaries[i + 1],
                   color='#2C3E50', alpha=0.05 if i % 2 == 0 else 0.0, zorder=0)

    # Raw signal — faint background
    ax.plot(series.index, series.values,
            color=color, alpha=0.25, linewidth=0.8, zorder=2)

    # Rolling mean — primary readable line
    ax.plot(roll.index, roll.values,
            color=color, linewidth=2.2, alpha=0.95, zorder=3)

    # Change-point lines + annotations
    for cp in cps:
        ax.axvline(cp, color='#2C3E50', linewidth=1.4,
                   linestyle='--', alpha=0.80, zorder=4)

        event = EVENT_ANNOTATIONS.get(cp)
        if event:
            yrange  = series.max() - series.min()
            y_label = series.max() - yrange * 0.04
            ax.text(cp + pd.Timedelta(days=2), y_label, event,
                    fontsize=8, color='#2C3E50', va='top', ha='left',
                    fontweight='semibold',
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='white',
                              edgecolor='#CCCCCC', linewidth=0.6, alpha=0.92))

    ax.set_ylabel(label, fontsize=9, color='#333333', labelpad=8)
    pad = (series.max() - series.min()) * 0.15
    ax.set_ylim(series.min() - pad, series.max() + pad)
    ax.grid(axis='y', zorder=1)
    ax.grid(axis='x', alpha=0.0)

    if ax != axes[-1]:
        ax.set_xticklabels([])
        ax.tick_params(axis='x', length=0)

axes[-1].xaxis.set_major_locator(mdates.MonthLocator())
axes[-1].xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
axes[-1].tick_params(axis='x', rotation=0, labelsize=9)

# Shared legend
fig.legend(
    handles=[
        plt.Line2D([0], [0], color='#888888', linewidth=0.8, alpha=0.5,
                   label='Daily value'),
        plt.Line2D([0], [0], color='#555555', linewidth=2.2,
                   label='30-day rolling mean'),
        plt.Line2D([0], [0], color='#2C3E50', linewidth=1.4, linestyle='--',
                   label='PELT change-point'),
        mpatches.Patch(color='#2C3E50', alpha=0.08,
                       label='Detected regime'),
    ],
    loc='lower center', ncol=4, fontsize=9,
    frameon=True, framealpha=0.95, edgecolor='#DDDDDD',
    bbox_to_anchor=(0.5, 0.005),
)

chart_path = 'analyses/physiological_nonstationarity/results/nonstationarity_analysis.png'
plt.savefig(chart_path, dpi=180, bbox_inches='tight', facecolor='white')
print(f"\nChart saved → {chart_path}")
print("\nAll outputs written. Ready to commit.")
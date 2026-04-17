"""
Project 3: Training load as predictor of regime transitions.

Question: do the 14-day training-load windows preceding the two PELT-detected
regime transitions (HRV: 2025-12-28, RHR: 2026-02-28) differ meaningfully from
the distribution of training load across all other 14-day windows in the dataset?

Methods:
  - Descriptive: percentile rank of pre-transition values vs. all 14-day rolling
    windows in the dataset.
  - Inference: permutation test (10,000 iterations) on the null that
    pre-transition labels are exchangeable with non-pre-transition labels.

Why not logistic regression: with n=2 positive cases, regression coefficients
are not identifiable in any meaningful sense. Permutation testing makes no
distributional assumptions and its small-n limitations are transparent in
the method itself.

Limitations:
  - n=2 transitions is the dominant constraint. Findings are descriptive only.
  - Rolling 14-day windows are not statistically independent (adjacent windows
    share 13 days of data). Permutation p-values should be interpreted with
    this dependency in mind; percentile rank is the more defensible quantitative
    claim.
"""

import os
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import snowflake.connector
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from ingestion.common.snowflake_auth import load_private_key

load_dotenv()

SNOWFLAKE_ACCOUNT = os.getenv("SNOWFLAKE_ACCOUNT")
SNOWFLAKE_USER = os.getenv("SNOWFLAKE_USER")
SNOWFLAKE_PRIVATE_KEY_PATH = os.environ["SNOWFLAKE_PRIVATE_KEY_PATH"]
SNOWFLAKE_WAREHOUSE = os.getenv("SNOWFLAKE_WAREHOUSE")
SNOWFLAKE_DATABASE = os.getenv("SNOWFLAKE_DATABASE")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

OUTPUT_DIR = Path(__file__).resolve().parent / "results"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Transition dates confirmed from mart_regime_labels (Q2b in input verification).
# These are the FIRST day of regime 2; the pre-transition window ends the day
# BEFORE these dates.
HRV_TRANSITION = pd.Timestamp("2025-12-28")
RHR_TRANSITION = pd.Timestamp("2026-02-28")
PRE_HRV_WINDOW_END = HRV_TRANSITION - pd.Timedelta(days=1)  # 2025-12-27
PRE_RHR_WINDOW_END = RHR_TRANSITION - pd.Timedelta(days=1)  # 2026-02-27

FEATURES = [
    "distance_14d",
    "elapsed_14d",
    "kj_14d",
    "workout_days_14d",
    "acwr_distance",
    "acwr_elapsed",
]

FEATURE_LABELS = {
    "distance_14d": "Cumulative distance (m)",
    "elapsed_14d": "Cumulative elapsed time (s)",
    "kj_14d": "Cumulative kilojoules",
    "workout_days_14d": "Workout days in window",
    "acwr_distance": "ACWR (distance)",
    "acwr_elapsed": "ACWR (elapsed time)",
}

N_PERMUTATIONS = 10_000
RNG_SEED = 42

# ---------------------------------------------------------------------------
# Data load
# ---------------------------------------------------------------------------

def get_connection():
    """Construct a Snowflake connection using key pair auth."""
    return snowflake.connector.connect(
        account=SNOWFLAKE_ACCOUNT,
        user=SNOWFLAKE_USER,
        private_key=load_private_key(SNOWFLAKE_PRIVATE_KEY_PATH),
        warehouse=SNOWFLAKE_WAREHOUSE,
        database=SNOWFLAKE_DATABASE,
        schema="MART_HEALTH",
    )


def load_features() -> pd.DataFrame:
    """Pull the materialized training-load feature mart from Snowflake."""
    query = """
        SELECT
            activity_date,
            regime_hrv,
            regime_resting_hr,
            distance_14d,
            elapsed_14d,
            kj_14d,
            workout_days_14d,
            acwr_distance,
            acwr_elapsed,
            rows_in_28d_window
        FROM mart_health.mart_training_load_features
        ORDER BY activity_date
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()
        cols = [c[0].lower() for c in cursor.description]
        df = pd.DataFrame(rows, columns=cols)
    finally:
        conn.close()

    df["activity_date"] = pd.to_datetime(df["activity_date"])
    # Snowflake NUMBER columns can come back as Decimal; coerce to float
    for col in FEATURES + ["rows_in_28d_window"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


# ---------------------------------------------------------------------------
# Window construction
# ---------------------------------------------------------------------------

def label_windows(df: pd.DataFrame) -> pd.DataFrame:
    """
    Label each row according to whether its trailing 14-day window IS the
    pre-transition window for HRV, RHR, or neither. The 14-day window is
    complete starting from the 14th row of data.
    """
    df = df.copy()
    has_complete_14d = df["activity_date"] >= df["activity_date"].iloc[0] + pd.Timedelta(days=13)

    df["window_label"] = "comparison"
    df.loc[~has_complete_14d, "window_label"] = "incomplete"
    df.loc[df["activity_date"] == PRE_HRV_WINDOW_END, "window_label"] = "pre_hrv_transition"
    df.loc[df["activity_date"] == PRE_RHR_WINDOW_END, "window_label"] = "pre_rhr_transition"
    return df


# ---------------------------------------------------------------------------
# Descriptive analysis
# ---------------------------------------------------------------------------

def percentile_rank(value: float, distribution: np.ndarray) -> float:
    """Empirical percentile rank: fraction of distribution at or below value."""
    distribution = distribution[~np.isnan(distribution)]
    if len(distribution) == 0 or pd.isna(value):
        return np.nan
    return float(np.mean(distribution <= value)) * 100


def build_descriptive_table(df: pd.DataFrame) -> pd.DataFrame:
    """Per-feature: pre-transition values, comparison distribution stats, percentile ranks."""
    comparison = df[df["window_label"] == "comparison"]
    pre_hrv = df[df["window_label"] == "pre_hrv_transition"]
    pre_rhr = df[df["window_label"] == "pre_rhr_transition"]

    rows = []
    for feature in FEATURES:
        comp_vals = comparison[feature].dropna().values
        hrv_val = pre_hrv[feature].iloc[0] if len(pre_hrv) else np.nan
        rhr_val = pre_rhr[feature].iloc[0] if len(pre_rhr) else np.nan

        rows.append({
            "feature": feature,
            "comparison_n": len(comp_vals),
            "comparison_mean": float(np.mean(comp_vals)) if len(comp_vals) else np.nan,
            "comparison_median": float(np.median(comp_vals)) if len(comp_vals) else np.nan,
            "comparison_std": float(np.std(comp_vals, ddof=1)) if len(comp_vals) > 1 else np.nan,
            "comparison_min": float(np.min(comp_vals)) if len(comp_vals) else np.nan,
            "comparison_max": float(np.max(comp_vals)) if len(comp_vals) else np.nan,
            "pre_hrv_value": float(hrv_val) if not pd.isna(hrv_val) else np.nan,
            "pre_hrv_percentile": percentile_rank(hrv_val, comp_vals),
            "pre_rhr_value": float(rhr_val) if not pd.isna(rhr_val) else np.nan,
            "pre_rhr_percentile": percentile_rank(rhr_val, comp_vals),
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Permutation test
# ---------------------------------------------------------------------------

def permutation_test(
    pre_values: np.ndarray,
    comparison_values: np.ndarray,
    n_permutations: int,
    rng: np.random.Generator,
) -> dict:
    """
    Two-sided permutation test on the difference in means between
    pre-transition and comparison windows.

    Null: the labels (pre-transition vs comparison) are exchangeable.
    Test statistic: |mean(pre) - mean(comparison)|
    """
    pre_values = pre_values[~np.isnan(pre_values)]
    comparison_values = comparison_values[~np.isnan(comparison_values)]

    n_pre = len(pre_values)
    if n_pre == 0 or len(comparison_values) == 0:
        return {"observed_diff": np.nan, "p_value": np.nan, "n_pre": n_pre, "n_comparison": len(comparison_values)}

    pooled = np.concatenate([pre_values, comparison_values])
    observed = np.mean(pre_values) - np.mean(comparison_values)
    observed_abs = abs(observed)

    extreme_count = 0
    for _ in range(n_permutations):
        perm = rng.permutation(pooled)
        perm_pre = perm[:n_pre]
        perm_comp = perm[n_pre:]
        diff = abs(np.mean(perm_pre) - np.mean(perm_comp))
        if diff >= observed_abs:
            extreme_count += 1

    # +1 in numerator and denominator: standard correction so p > 0
    p_value = (extreme_count + 1) / (n_permutations + 1)

    return {
        "observed_diff": float(observed),
        "p_value": float(p_value),
        "n_pre": n_pre,
        "n_comparison": len(comparison_values),
    }


def build_permutation_table(df: pd.DataFrame) -> pd.DataFrame:
    """Run permutation tests for HRV pre-window, RHR pre-window, and combined."""
    rng = np.random.default_rng(RNG_SEED)
    comparison = df[df["window_label"] == "comparison"]
    pre_hrv = df[df["window_label"] == "pre_hrv_transition"]
    pre_rhr = df[df["window_label"] == "pre_rhr_transition"]
    pre_combined = df[df["window_label"].isin(["pre_hrv_transition", "pre_rhr_transition"])]

    rows = []
    for feature in FEATURES:
        comp_vals = comparison[feature].values
        for label, subset in [
            ("pre_hrv_transition", pre_hrv),
            ("pre_rhr_transition", pre_rhr),
            ("pre_combined", pre_combined),
        ]:
            result = permutation_test(
                pre_values=subset[feature].values,
                comparison_values=comp_vals,
                n_permutations=N_PERMUTATIONS,
                rng=rng,
            )
            rows.append({
                "feature": feature,
                "comparison_to": label,
                **result,
            })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Visualization
# ---------------------------------------------------------------------------

def plot_feature_distributions(df: pd.DataFrame, output_path: Path) -> None:
    """2x3 grid: per feature, comparison distribution histogram + pre-transition markers."""
    comparison = df[df["window_label"] == "comparison"]
    pre_hrv = df[df["window_label"] == "pre_hrv_transition"]
    pre_rhr = df[df["window_label"] == "pre_rhr_transition"]

    fig, axes = plt.subplots(2, 3, figsize=(15, 8))
    axes = axes.flatten()

    for idx, feature in enumerate(FEATURES):
        ax = axes[idx]
        comp_vals = comparison[feature].dropna().values

        if len(comp_vals) > 0:
            ax.hist(comp_vals, bins=20, alpha=0.6, color="#4a7ba6", edgecolor="white",
                    label=f"Comparison windows (n={len(comp_vals)})")

        if len(pre_hrv) and not pd.isna(pre_hrv[feature].iloc[0]):
            ax.axvline(pre_hrv[feature].iloc[0], color="#c44e52", linestyle="--", linewidth=2,
                       label="Pre-HRV transition")

        if len(pre_rhr) and not pd.isna(pre_rhr[feature].iloc[0]):
            ax.axvline(pre_rhr[feature].iloc[0], color="#dd8452", linestyle="--", linewidth=2,
                       label="Pre-RHR transition")

        ax.set_title(FEATURE_LABELS[feature], fontsize=11)
        ax.set_xlabel(feature, fontsize=9)
        ax.set_ylabel("Window count", fontsize=9)
        ax.legend(fontsize=8, loc="upper right")
        ax.grid(alpha=0.3)

    fig.suptitle(
        "14-day training load: pre-transition windows vs. all other windows",
        fontsize=13, y=1.00
    )
    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("Loading mart_training_load_features from Snowflake...")
    df = load_features()
    print(f"Loaded {len(df)} rows, date range {df['activity_date'].min().date()} to {df['activity_date'].max().date()}")

    df = label_windows(df)
    label_counts = df["window_label"].value_counts()
    print(f"\nWindow label counts:\n{label_counts}\n")

    for label in ["pre_hrv_transition", "pre_rhr_transition"]:
        n = (df["window_label"] == label).sum()
        if n != 1:
            raise ValueError(f"Expected exactly 1 row labeled {label}, got {n}")

    print("Building descriptive table...")
    desc = build_descriptive_table(df)
    desc.to_csv(OUTPUT_DIR / "descriptive_summary.csv", index=False)
    print(desc.to_string(index=False))

    print(f"\nRunning permutation tests ({N_PERMUTATIONS} iterations per feature x condition)...")
    perm = build_permutation_table(df)
    perm.to_csv(OUTPUT_DIR / "permutation_results.csv", index=False)
    print(perm.to_string(index=False))

    pre_features = df[df["window_label"].isin(["pre_hrv_transition", "pre_rhr_transition"])][
        ["activity_date", "window_label"] + FEATURES
    ]
    pre_features.to_csv(OUTPUT_DIR / "pre_transition_features.csv", index=False)

    print("\nGenerating visualization...")
    plot_path = OUTPUT_DIR / "feature_distributions.png"
    plot_feature_distributions(df, plot_path)
    print(f"Saved chart: {plot_path}")

    print("\nDone.")


if __name__ == "__main__":
    main()

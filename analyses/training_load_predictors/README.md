# Training Load as a Predictor of Regime Transitions

**Status:** Complete — analysis executed April 2026; results in `results/`

## Executive Summary

This analysis investigates whether the two PELT-detected regime transitions identified in Project 1 (HRV: 2025-12-28; resting HR: 2026-02-28) share a common training-load signature. They do not. The two transitions occurred under markedly different training-load conditions: the HRV transition followed a 28-day period of zero training (a travel-related interruption), while the resting-HR transition followed an acute training-load spike with an acute-to-chronic workload ratio (ACWR) at the 100th percentile of all 14-day windows in the dataset. The interpretation is that the two regime shifts reflect distinct underlying mechanisms — one consistent with detraining/recovery, one consistent with overload — rather than a single training-load process.

## Motivation

This project is the third artifact in a portfolio investigating physiological nonstationarity in personal wearable data. Project 1 demonstrated empirically that HRV and resting heart rate fail formal stationarity tests and that change-point detection (PELT) identifies regime boundaries earlier than the rolling-window approaches commercial wearables use. Project 2 operationalized the regime structure into a reporting layer (Metabase dashboard on regime-aware baselines).

This project asks the natural follow-on: what is the training-load context of the detected transitions? If a single mechanism (e.g., training overload) drove both transitions, we would expect both to show elevated load in the preceding window. If the transitions reflect distinct mechanisms, the training-load signatures should differ.

This is framed as a methodological case study, not a predictive claim. With n=2 transitions, no statistical model can support generalization. The contribution is the methodological pattern (regime-aware feature engineering, percentile characterization, permutation testing under explicit small-n constraints) and the descriptive finding of heterogeneity.

## Method

**Feature engineering (dbt model `mart_training_load_features`):**

Built on `mart_regime_labels` from Project 2, which contains daily Strava aggregates joined to regime annotations. Six per-day rolling features computed via window functions:

- Cumulative distance, elapsed time, kilojoules, and workout-day count over a trailing 14-day window
- Acute-to-chronic workload ratio (ACWR) for distance and elapsed time: 7-day mean / 28-day mean

ACWR is a standard sports-science load metric (Gabbett, 2016); values above ~1.5 are widely cited as elevated injury and fatigue risk. ACWR is null where the 28-day chronic window is incomplete (first 27 rows of the dataset) or where the chronic baseline is zero.

**Comparison framework:**

Two analytical units of interest: the 14-day window ending the day before each PELT-detected transition (Dec 27, 2025 for HRV; Feb 27, 2026 for resting HR). All other rolling 14-day windows in the dataset (n=116) form the comparison distribution.

Two analyses per feature:

1. **Descriptive percentile rank.** Where does each pre-transition value fall in the comparison distribution?
2. **Permutation test (10,000 iterations).** Null: pre-transition labels are exchangeable with comparison labels. Test statistic: |mean(pre) − mean(comparison)|.

**Why not logistic regression.** With n=2 positive cases, regression coefficients are not identifiable in any meaningful sense. Permutation testing makes no distributional assumptions and its small-n constraints are transparent in the method itself: with n=1 in a test group, the minimum achievable p-value is bounded by the number of distinguishable label assignments, and the resulting p-values should be read as descriptive of the test geometry rather than as inferential evidence.

## Data

- 130 daily observations from 2025-11-25 to 2026-04-11
- Source: `mart_health.mart_training_load_features` (Snowflake), built from Project 2's regime-annotated daily mart
- 39 of 130 days had logged Strava activity (30%). Cumulative kilojoules populated on 23 days (59% of activity days), reflecting that Strava computes kJ from power data, which is rarely available for running activities — kJ is treated as a secondary feature only.
- Regime boundaries verified directly from `mart_regime_labels` rather than carried forward from prior session notes.

## Results

### Pre-transition feature values

| Feature | Pre-HRV (Dec 14–27, 2025) | Percentile | Pre-RHR (Feb 14–27, 2026) | Percentile |
|---|---:|---:|---:|---:|
| Cumulative distance (m) | 0 | 61% | 22,390 | 64% |
| Cumulative elapsed (s) | 0 | 58% | 20,240 | 65% |
| Cumulative kilojoules | 0 | 66% | 0 | 66% |
| Workout days | 0 | 58% | 6 | 64% |
| ACWR (distance) | undefined | — | **4.00** | **100%** |
| ACWR (elapsed time) | undefined | — | 3.29 | 86% |

The percentile ranks for the cumulative measures are deceptively middle-of-distribution — the comparison distribution is heavily right-skewed (median = 0 for all four cumulative measures), reflecting that the dataset spans periods of high and low training density and that more than half of all 14-day windows contain no logged activity.

The discriminating signal is the ACWR. The pre-RHR transition window had an acute distance ratio of 4.0 — the highest in the entire dataset, and well above the 1.5 sports-science threshold. The pre-HRV transition window had no defined ACWR because the 28-day chronic baseline was zero.

### Permutation test results

P-values for ACWR features (the only features with discriminating signal):

| Feature | Comparison | p-value | n_pre | n_comparison |
|---|---|---:|---:|---:|
| ACWR (distance) | pre-RHR vs comparison | 0.142 | 1 | 45 |
| ACWR (elapsed time) | pre-RHR vs comparison | 0.154 | 1 | 49 |

Neither reaches conventional significance thresholds, and they cannot — with n=1 in the test group, the test geometry caps achievable evidence regardless of effect size. P-values are reported for transparency but the descriptive percentile rank is the more defensible quantitative claim.

### Interpretation

The two regime transitions occurred under qualitatively different training-load conditions:

- **HRV transition (2025-12-28).** Preceded by 28 days of zero training. This period coincides with a documented travel event (interstate stay in San Ramon, CA). The HRV regime shift is consistent with a detraining or post-travel autonomic response.
- **RHR transition (2026-02-28).** Preceded by an acute training-load spike (ACWR distance = 4.0, the dataset maximum). This is consistent with an overload-driven cardiovascular adaptation or accumulated-fatigue response.

A single mechanism (e.g., "training load drives transitions") does not fit. The two transitions appear to reflect distinct physiological processes that share only the property of being detectable as nonstationarities. This is consistent with the Project 1 framing of regime structure as a methodological observation about the data, not a claim about a unified causal mechanism.

![Feature Distributions](results/feature_distributions.png)

*Per-feature comparison of 14-day pre-transition training-load values (dashed vertical lines) against the full distribution of all rolling 14-day windows in the dataset. The pre-RHR transition window (orange) shows ACWR distance at the 100th percentile; the pre-HRV transition window (red) shows zero load across all cumulative measures.*

## Limitations

- **n = 2 transitions.** This is the dominant constraint. No claim in this analysis generalizes beyond these two transitions in this dataset. The methodological pattern is what carries forward; the substantive finding is illustrative.
- **Single-subject data.** All observations are from one individual. Between-individual heterogeneity in training-load response is well-documented and is not addressed here.
- **Rolling-window dependence.** Adjacent 14-day windows share 13 days of underlying data. The 116 comparison windows are not statistically independent. This violates the exchangeability assumption underlying the permutation test and biases p-values toward zero. The percentile rank reporting is unaffected.
- **Activity coding.** Days without a logged Strava activity are coded as zero training load. This conflates "no workout occurred" with "no workout was logged." For this dataset the two are believed to be equivalent (primary endurance training is logged on Strava), but this assumption is documented rather than verified.
- **ACWR availability.** ACWR requires a complete 28-day chronic window with non-zero baseline. The pre-HRV transition window failed both conditions (the data window starts only 33 days before the transition, and the chronic baseline was zero), so the most discriminating feature could not be computed for that transition. This is an honest data limitation, not a methodological choice.

## Research Directions

- **Extend the data window.** Five months is too short to characterize regime structure robustly. Three years of historical Strava and Oura data would likely surface 6–10 transitions, enough to begin distinguishing transition typologies (overload-driven vs. detraining-driven vs. unexplained).
- **Couple with sleep and recovery features.** The current analysis uses Strava load only. Adding sleep duration, sleep efficiency, and Oura readiness as pre-transition features would test whether transitions are predicted better by the combination than by training load alone.
- **Test a state-space formulation.** A hidden Markov model with training load as an observed covariate could formalize the relationship between training input and regime hidden state, sidestepping the n=2 problem by treating regime occupancy as continuous rather than transitions as discrete events.
- **Validate the heterogeneity finding cross-individually.** The descriptive heterogeneity (detraining-type vs. overload-type transitions) is the most portable result from this analysis. Replicating the pattern across multiple users in a research dataset would convert it from a single-subject observation to a generalizable phenomenon.

## Reproducing

```bash
# 1. Build the feature mart
cd dbt/
dbt run --select mart_training_load_features

# 2. Run the analysis
cd ..
uv run python analyses/training_load_predictors/analysis.py
```

Outputs land in `analyses/training_load_predictors/results/`:
- `descriptive_summary.csv` — per-feature percentile ranks
- `permutation_results.csv` — permutation p-values
- `pre_transition_features.csv` — raw feature values for the two pre-transition windows
- `feature_distributions.png` — per-feature visualization

## References

- Gabbett, T.J. (2016). The training–injury prevention paradox: should athletes be training smarter and harder? *British Journal of Sports Medicine*, 50(5), 273–280.
- Killick, R., Fearnhead, P., & Eckley, I.A. (2012). Optimal detection of changepoints with a linear computational cost. *Journal of the American Statistical Association*, 107(500), 1590–1598.
- Plews, D.J. et al. (2013). Training adaptation and heart rate variability in elite endurance athletes: opening the door to effective monitoring. *Sports Medicine*, 43(9), 773–781.

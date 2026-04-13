# Physiological Nonstationarity Investigation

## Executive Summary

This analysis tests whether four physiological signals — average HRV, resting heart rate, sleep efficiency, and readiness score — satisfy the stationarity assumption implicitly embedded in commercial wearable baseline algorithms. Using ADF and KPSS tests on 130 days of personal Oura Ring data, HRV and resting HR are found to be trend-stationary rather than stationary, exhibiting directional drift inconsistent with a fixed population baseline. PELT change-point detection identifies two discrete regime transitions: a downward HRV shift on 2025-12-27 coinciding with interstate travel and environmental disruption, and a downward resting HR shift on 2026-02-27 coinciding with the start of a structured marathon training block. A naive 30-day rolling mean lagged PELT by 7 days on the HRV transition and failed entirely to flag the resting HR transition. These results motivate the regime-aware baseline framework implemented in Project 2 and the predictive regime transition model in Project 3.

---

## Motivation

Commercial wearable platforms — including Oura — compute readiness and recovery scores relative to a rolling personal baseline that assumes the underlying signal is stationary within a window. Plews et al. (2013) demonstrated that HRV in trained athletes is not well-described by a stationary process: systematic drift occurs across training blocks, competition phases, and recovery periods, and regime-level shifts are substantively different from day-to-day noise. If the baseline algorithm does not account for these transitions, it risks misclassifying a genuine physiological adaptation — such as cardiac remodeling under sustained aerobic load — as either a positive or negative deviation from a stale reference mean. This analysis operationalizes that critique on a single-subject longitudinal dataset, asking not whether nonstationarity exists theoretically, but whether it is detectable in 130 days of real data using standard time-series methods.

---

## Method

**Stationarity testing:** ADF (Augmented Dickey-Fuller) and KPSS (Kwiatkowski-Phillips-Schmidt-Shin) tests are applied jointly to each signal. Their null hypotheses are complementary — ADF tests for a unit root (H0: non-stationary), KPSS tests for level stationarity (H0: stationary) — so agreement between them narrows the inference. When both tests reject simultaneously, the series is trend-stationary: stationary around a deterministic trend rather than a fixed mean. This distinction matters because rolling-window baselines that assume a fixed mean will systematically misrepresent trend-stationary signals.

**Batch change-point detection (PELT):** Pruned Exact Linear Time (PELT) with an RBF kernel cost function is applied independently to each signal. Minimum segment size is set to 14 days (two weeks as the minimum meaningful physiological regime). Penalty parameter pen=10 was retained because the resulting segmentation is sparse and physiologically interpretable. PELT is a batch offline method — it has access to the full time series and identifies regime boundaries retrospectively.

**Detection latency:** For each PELT-detected change-point, the number of days until a 30-day rolling mean exceeds 1 SD from the prior regime mean is computed. This operationalizes the practical cost of naive smoothing relative to principled change-point detection.

**On BOCPD:** Bayesian Online Change-Point Detection (Adams & MacKay 2007) was implemented to compare online versus batch detection. The custom Normal-Gamma implementation produced constant output equal to the prior hazard rate (1/λ = 0.033) across all signals and all timesteps — indicating the predictive likelihood updates were not accumulating. The root cause is numerical underflow in the Student-T predictive distribution as sufficient statistics tighten with run length; a stable implementation requires log-space message passing. This is documented rather than patched. The conceptual contribution of BOCPD — motivating adaptive online methods — is carried forward into the research directions below.

---

## Data

| Property | Value |
|---|---|
| Source | Oura Ring Gen3 (personal device) |
| Date range | 2025-11-25 → 2026-04-11 |
| N | 130 daily observations |
| Missing values | 0 across all four signals |
| Signals | Average HRV (ms), Lowest Heart Rate (bpm), Sleep Efficiency (%), Readiness Score (0–100) |
| Pipeline | Oura REST API → Snowflake raw layer → dbt staging → `MART_HEALTH.DAILY_HEALTH_SUMMARY` |

---

## Results

### Stationarity Tests

| Signal | ADF Stat | ADF p | ADF Result | KPSS Stat | KPSS p | KPSS Result | Verdict |
|---|---|---|---|---|---|---|---|
| Average HRV | -3.065 | 0.0292 | Reject H0 | 0.998 | 0.0100 | Reject H0 | Trend-stationary |
| Lowest Heart Rate | -3.239 | 0.0179 | Reject H0 | 1.272 | 0.0100 | Reject H0 | Trend-stationary |
| Sleep Efficiency | -3.060 | 0.0296 | Reject H0 | 0.246 | 0.1000 | Fail | Stationary |
| Readiness Score | -4.232 | 0.0006 | Reject H0 | 0.271 | 0.1000 | Fail | Stationary |

HRV and resting HR fail the joint stationarity assumption — both ADF and KPSS reject simultaneously, indicating trend-stationarity. Sleep efficiency and readiness score are stationary in this window. The stationarity of the Oura composite (Readiness Score) relative to its non-stationary raw inputs (HRV, resting HR) is consistent with the hypothesis that Oura's algorithm applies smoothing that absorbs regime-level transitions detectable in the underlying signals. This asymmetry between raw signal behavior and composite score behavior is itself a testable and publishable observation.

### Change-Point Detection and Annotation

| Date | Signal | Before Mean | After Mean | Δ | Direction | Annotated Event |
|---|---|---|---|---|---|---|
| 2025-12-27 | Average HRV | 81.16 ms | 67.63 ms | 13.53 ms (16.7%) | ↓ | Travel to San Ramon, CA — 3-week family stay; schedule and sleep environment disruption |
| 2026-02-27 | Lowest Heart Rate | 48.68 bpm | 44.14 bpm | 4.54 bpm (9.3%) | ↓ | Marathon training block initiated (~20 mi/wk sustained aerobic load) |

Both directions are physiologically coherent. HRV suppression under travel and social-environmental disruption is consistent with elevated allostatic load reducing parasympathetic tone. Resting HR reduction under sustained aerobic training reflects cardiac adaptation — increased stroke volume reducing resting chronotropic demand. PELT recovered these transitions without prior annotation.

### Detection Latency

| Signal | PELT CP Date | Rolling Mean Flag Date | Latency (days) |
|---|---|---|---|
| Average HRV | 2025-12-27 | 2026-01-03 | 7 |
| Lowest Heart Rate | 2026-02-27 | Not flagged | — |

The rolling mean lagged PELT by 7 days on the HRV transition and failed entirely on resting HR. The resting HR regime shift was real and sustained — 4.54 bpm reduction held across the remainder of the observation window — but gradual enough that the global prior SD envelope contained the new regime mean. PELT caught it; naive smoothing did not. This asymmetry is the quantitative argument for regime-aware baselines in Project 2.

### Chart

![Nonstationarity Analysis](results/nonstationarity_analysis.png)

*Four signals on a shared time axis. Faint traces: daily values. Bold lines: 30-day rolling mean. Dashed vertical lines: PELT-detected change-points. Shaded regions: detected physiological regimes. Event annotations mark the life and training context of each transition.*

---

## Honest Limitations

**n=1, single device.** All results are specific to one individual measured on one device. No population-level inference is possible. Results are a methods demonstration and hypothesis-generating exercise, not generalizable findings.

**Self-annotation bias.** The mapping of change-point dates to life events is retrospective and self-reported. Confirmation bias cannot be ruled out — a detected date tends to attract a plausible explanation in memory. Signal directions are empirically verified; causal attribution is not.

**4.3-month observation window.** 130 days is short relative to annual training periodization. Regime transitions operating at seasonal or competitive-cycle timescales are not detectable in this window.

**PELT penalty selection.** pen=10 was set a priori and produced interpretable results. BIC-based automatic selection was not implemented. Robustness across the penalty range was not formally assessed.

**BOCPD numerical instability.** The custom Adams & MacKay implementation collapsed to the prior hazard rate at every timestep, producing uninformative constant output. Root cause is underflow in the Student-T predictive likelihood as Normal-Gamma sufficient statistics tighten over long run lengths. A numerically stable implementation requires log-space message passing. The zero-flag result should not be interpreted as evidence that BOCPD is ineffective for these signals.

**Missing signals.** Oura captures nightly skin temperature deviation and respiratory rate — both physiologically meaningful nonstationarity indicators not present in the current data mart. Including them would strengthen the signal set and improve detection sensitivity for illness-driven regime transitions, which are distinct from training or environmental disruptions.

**Independent per-signal detection.** PELT is applied independently to each signal. Synchronized regime transitions — where a single event (travel, illness, training load spike) shifts multiple signals simultaneously — are not detected as such. A joint transition detected across HRV and resting HR on the same date carries stronger evidential weight than two independent single-signal detections, but the current architecture cannot make that inference.

---

## Research Directions

This section documents the analytical extensions this work motivates — both immediate technical fixes and longer-horizon research questions. These are written as research directions rather than a to-do list because the goal is not just implementation but contribution.

### Immediate Technical Extensions

**Numerically stable BOCPD.** The correct fix is to rewrite the message-passing loop in log-space: compute `log P(x_t | r_t, data)` using `scipy.stats.t.logpdf`, accumulate log-probabilities across run lengths, and normalize via `logsumexp` before exponentiating. This is a known engineering solution to a known numerical problem — it is not a research contribution on its own, but it is a prerequisite for the batch-versus-online comparison this project originally intended. Once stable, the comparison between PELT (batch, retrospective) and BOCPD (online, sequential) produces the latency characterization that is directly relevant to real-time monitoring system design.

**Multivariate change-point detection.** Running PELT independently per signal cannot detect synchronized regime transitions. If travel disruption on Dec 27 shifted HRV, resting HR, and sleep efficiency simultaneously, three independent single-signal detections on three different dates misrepresent the structure of the event. The `ruptures` library supports multivariate PELT via the same API — applying it to the four signals jointly would produce a single set of regime boundaries shared across all signals, with detection sensitivity proportional to the number of signals that shift together. This is methodologically stronger and would be the appropriate approach in a publication.

### Connections to This Portfolio

**Project 2 — Regime-Aware Baselines in Power BI.** The PELT-detected regime boundaries from this analysis are used directly as partition keys in the Project 2 dashboard. Rather than computing a rolling global mean, each signal's baseline is computed within its detected regime. The detection latency result — PELT flagging 7 days earlier than a rolling mean, and catching a transition the rolling mean missed entirely — is the quantitative justification for that design decision. Project 2 operationalizes the finding; Project 1 establishes it.

**Project 3 — Does Training Load Predict Regime Transitions?** The annotated change-points here become the outcome variable in Project 3. If resting HR entered a new regime 7 days after a marathon training block began, the question is whether training load metrics in the days preceding that transition — cumulative distance, acute:chronic workload ratio, elevation gain — were already signaling the coming shift. That is a predictive question, not a descriptive one, and it is the analytical direction that connects this work to sports science literature on training load and readiness.

### Longer-Horizon Research Angles

**Regime transition classification.** The two annotated change-points here represent two qualitatively different types of events: environmental disruption (travel) and adaptive response (training). A larger dataset — either longitudinal extension of this subject or a multi-subject cohort — could ask whether the *shape* of a regime transition differs by type. A disruption-driven HRV shift might show a sharp drop followed by partial recovery; a training-driven resting HR shift might show a gradual monotonic decline. If these signatures are distinguishable, unsupervised classification of regime transition type becomes feasible, which is a publishable methodological contribution.

**The composite score problem.** Readiness Score is stationary while its inputs (HRV, resting HR) are trend-stationary. This is an empirically observable phenomenon that deserves formal characterization. The question is: at what point in a regime transition does Oura's composite score register a meaningful response, and how does that lag compare to raw signal detection? A formal transfer function analysis — treating Readiness Score as the output and raw signals as inputs — would quantify the smoothing behavior of the composite and is directly relevant to the clinical and occupational health contexts where these devices are increasingly deployed. This is the natural basis for a methods paper targeting JMIR mHealth and uHealth or npj Digital Medicine.

**Population-level nonstationarity.** The n=1 limitation here is real but not fatal to the research program. The methodological contribution — joint ADF/KPSS testing combined with PELT change-point detection as a framework for characterizing physiological regime structure — generalizes directly to multi-subject datasets. Applied to a cohort of endurance athletes across a competitive season, the same pipeline would produce regime maps that could be compared across individuals, correlated with performance outcomes, and used to assess the validity of population-normalized wearable baselines. This is the scale at which the critique of commercial algorithms becomes actionable for device manufacturers and clinical researchers.

**Occupational and healthcare workforce applications.** The stationarity failure documented here is not unique to endurance athletes. Healthcare workers under shift-pattern scheduling, rotating night shifts, or high-acuity event exposure are subject to analogous regime transitions in HRV and resting HR. A regime-aware monitoring framework applied in that context — where the stakes of misclassifying a physiological state are higher — has direct clinical and operational relevance. Synthetic data generation using the regime parameters estimated here would allow proof-of-concept modeling without requiring access to sensitive workforce health data, which is the approach scoped in Project 5 of this portfolio.

---

## References

Plews, D. J., Laursen, P. B., Stanley, J., Buchheit, M., & Kilding, A. E. (2013). Training adaptation and heart rate variability in elite endurance athletes: Opening the door to effective monitoring. *Sports Medicine, 43*(9), 773–781.

Adams, R. P., & MacKay, D. J. C. (2007). Bayesian online changepoint detection. *arXiv preprint arXiv:0710.3742.*

Killick, R., Fearnhead, P., & Eckley, I. A. (2012). Optimal detection of changepoints with a linear computational cost. *Journal of the American Statistical Association, 107*(500), 1590–1598.
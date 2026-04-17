# Physiological Nonstationarity in Wearable Sensor Data: A Methodological Case Study on Regime-Aware Baselines

**Author:** Hemanth Allamaneni  
**Affiliation:** MS Applied Cognition and Neuroscience (HCI and Intelligent Systems), The University of Texas at Dallas  
**Date:** April 2026  

## Abstract

Commercial wearable algorithms assume that human physiological signals are stationary within a rolling baseline window, computing daily readiness and recovery scores against a slowly adapting global mean. This assumption risks misclassifying genuine biological adaptation or systematic environmental disruption as transient noise. This paper tests the stationarity assumption empirically using continuous longitudinal data spanning 130 days from four sources (Oura Ring Gen 4, Apple HealthKit, RENPHO, and Strava). Joint application of Augmented Dickey-Fuller (ADF) and Kwiatkowski-Phillips-Schmidt-Shin (KPSS) tests demonstrates that heart rate variability (HRV) and resting heart rate (RHR) are trend-stationary, rather than stationary. By applying Pruned Exact Linear Time (PELT) change-point detection, we identify two discrete, physiologically annotated regime transitions: one driven by travel disruption and the other by sustained aerobic training overload. We show that a naive 30-day rolling baseline lags regime transitions by up to a week and entirely fails to detect gradual, sustained cardiac adaptation. In response, we detail the system architecture for a fully reproducible, declarative, and regime-aware self-hosted analytics platform. We conclude that commercial baseline operations suppress valid regime structure, and demonstrate through explicit mathematical modeling that dynamic regime boundaries provide a more actionable operational metric for personal telemetry.

---

## 1. Introduction

The quantitative core of the modern consumer wearable ecosystem is the daily composite score. Platforms such as Oura, Whoop, and Apple Health compute derivatives of readiness, recovery, and physiological strain by comparing acute overnight metrics (specifically resting heart rate and heart rate variability) to a rolling longitudinal baseline. 

This analytical foundation relies implicitly on the assumption of physiological **stationarity**. It assumes that the user's underlying physiological state exhibits a fixed mean and constant variance over the baseline calculation window (typically 14 to 30 days). Deviations from this mean are interpreted as transient acute stress (e.g., a poor night of sleep, acute illness, or an intense training session) rather than an orthogonal shift in the baseline itself.

However, continuous physiological data fundamentally violates this assumption during periods of significant lifestyle change, environmental disruption, or structured physical training. When an individual adopts an endurance training program, the resulting cardiovascular adaptation permanently pulls the daily metric down. A stationary rolling-mean algorithm treats this adaptation as consecutive days of "excellent" deviations until the 30-day window slowly swallows the new regime, pulling the baseline down with it. Similarly, when transitioning across time zones or encountering extended social disruption, HRV may suppress systemically. The rolling baseline lags this transition, penalizing the user for standardizing at a lower homeostatic set-point.

This paper asks the natural operational question: what happens when the stationarity assumption fails? We document an applied research program demonstrating this failure empirically, characterizing the latency cost of naive rolling means, and detailing the engineering pipeline required to implement **regime-aware** baselines that mathematically capture the step-function nature of true physiological adaptation.

---

## 2. Related Work

The tension between static analytical models and continuous physiological adaptation is well-documented in the sports science and clinical monitoring literature.

**Physiological Stationarity in Athletes.** Plews et al. (2013) demonstrated that HRV in trained athletes is not well-described by a stationary process. Systematic drift occurs across macro-cycles of training, peaking phases, and off-seasons. They argue that regime-level shifts are fundamentally different from day-to-day noise, demanding dynamic analytical methods rather than static thresholds. Similarly, Gabbett (2016) popularized the acute-to-chronic workload ratio (ACWR) to explicitly model the dynamic relationship between a moving short-term load and a longer-term physiological base, acknowledging that identical acute stimuli evoke different biological responses depending on the chronic physiological regime.

**Change-Point Detection (CPD).** Retrospective and online change-point detection methods are widely utilized to identify structural breaks in noisy time-series data. Killick, Fearnhead, and Eckley (2012) introduced Pruned Exact Linear Time (PELT), providing a computationally efficient exact search methodology for segmenting time-series under a defined penalty cost. 

---

## 3. System Architecture and Data Infrastructure

The research findings in this paper were produced within a fully integrated, automated, and declarative data platform architecture designed for continuous telemetry ingestion.

### 3.1 Source Ingestion

The platform ingests from four heterogeneous vendor systems:

1. **Oura Ring Gen 4:** An automated Python extraction loops through the paginated REST API, capturing nightly sleep metrics, heart rate variability, readiness scores, and respiratory rates.
2. **Apple Health (Heart Rate & Biomarkers):** Direct parsing of the native `export.xml` schema resulting from an Apple Health data export. This parses granular `HKQuantityType` records with explicit vendor metadata filtering.
3. **RENPHO / HealthKit:** Body composition metrics written to Apple HealthKit via the proprietary RENPHO ecosystem, parsed uniformly through the HealthKit XML pipeline.
4. **Strava:** Incremental OAuth2 pipeline capturing highly granular physical activity, training load estimations (kilojoules, elapsed time), and distance metrics.

### 3.2 Warehouse and Materialization Layer

Raw JSON and XML payloads are loaded into raw schemata (`RAW_OURA`, `RAW_STRAVA`, `RAW_APPLE_HEALTH`) in Snowflake. Data logic sits securely in a dbt transformation layer. The staging tables are joined into a denormalized layer (`MART_HEALTH.DAILY_HEALTH_SUMMARY`) which aggregates the matrix of physiological metrics and Strava behaviors onto a unified timeline.

---

## 4. Data

The dataset comprises continuous, single-subject longitudinal telemetry.

| Property | Value |
|---|---|
| **Source** | Oura Ring Gen 4, Apple Watch Series 7, Strava |
| **Date Range** | November 25, 2025 to April 11, 2026 (130+ days) |
| **Observation N** | 130 daily aggregate records |
| **Missing Values** | Zero missingness across the target signals |
| **Signals Modeled** | Average HRV (ms), Lowest Heart Rate (bpm), Sleep Efficiency (%), Readiness Score |

---

## 5. Mathematical Methods and Formulations

The core of this research bypasses proprietary opaque platform scoring to directly apply rigorous time-series theorems to the raw continuous sensor streams. 

### 5.1 Joint Stationarity Testing Formulae
To formally evaluate whether physiological signals respect a static mean, we jointly execute the Augmented Dickey-Fuller (ADF) and Kwiatkowski-Phillips-Schmidt-Shin (KPSS) statistical specifications. 

**The ADF Test Specification:**
The ADF tests for the presence of a unit root (the null hypothesis being that the series is non-stationary). The regression model is specified as:

$$ \Delta y_t = \alpha + \beta t + \gamma y_{t-1} + \sum_{i=1}^{p} \delta_i \Delta y_{t-i} + \epsilon_t $$

where $\Delta y_t$ is the first difference of the time series, $\alpha$ is a constant, $\beta t$ captures deterministic trends, $p$ represents the lag order to account for serial correlation, and $\epsilon_t$ encompasses the white noise error term. A sufficiently negative test statistic causes the rejection of the null hypothesis in favor of stationarity.

**The KPSS Test Specification:**
Conversely, the KPSS test assumes the null hypothesis is level-stationarity. The target series is decomposed into the sum of a deterministic trend, a random walk, and a stationary error:

$$ y_t = \xi t + r_t + \epsilon_t $$
$$ r_t = r_{t-1} + u_t $$

where $u_t$ represents independent and identically distributed variables with zero mean and fixed variance. When both ADF and KPSS mutually reject their null hypotheses, the physiological series is proven mathematically to be **trend-stationary**: exhibiting discrete regime shifts or directional drifts rather than a stable mean state.

### 5.2 Pruned Exact Linear Time (PELT) Segmentation
We apply the PELT algorithm retrospectively to identify precise optimal bounds of shifting physiological regimes. Unlike rolling standard deviation bounds, PELT solves the discrete segmentation penalty problem exactly. For a data sequence $y_{1:N}$, the goal is to identify a set of changepoints $\tau = (\tau_1, \tau_2, ..., \tau_m)$ that minimizes the cost function:

$$ \min_{\tau} \left[ \sum_{i=1}^{m} C(y_{(\tau_{i-1}+1):\tau_i}) + m p \right] $$

where $C$ is a cost function (using a Radial Basis Function Gaussian Kernel) that measures the variance within each segment, $m$ represents the number of change points, and $p$ corresponds to a linear penalty term (configured to $p=10$) inserted to linearly penalize extreme parameter volatility and constrain the output to biologically valid distinct phases.

### 5.3 Workload Context Modeling (ACWR)
To quantify the trailing physiological conditions triggering biological adaptation, we deploy an engineered Acute-to-Chronic Workload Ratio (ACWR). Building on Gabbett's formulation (2016), ACWR assesses the immediate preceding fatigue state (acute load) relative to the stable established base (chronic load):

$$ \text{ACWR}_t = \frac{\frac{1}{7} \sum_{i=0}^{6} \text{Load}_{t-i}}{\frac{1}{28} \sum_{i=0}^{27} \text{Load}_{t-i}} $$

Values nearing 1.0 imply stable maintenance. Values elevating to 1.5 indicate progressive loading. Extreme deviations beyond 2.0 define high-density cardiovascular shock regimes.

---

## 6. Results

### 6.1 Formal Stationarity Testing Output

Heart rate variability and resting heart rate explicitly fail the stationarity assumption. Both ADF and KPSS reliably reject simultaneously (Table 1), forcing the mathematical determination that HRV and RHR actively transition between discrete deterministic biological states. 

**Table 1: Unit Root and Level Stationarity Testing**

| Signal | ADF Stat | ADF p | ADF Result | KPSS Stat | KPSS p | KPSS Result | Verdict |
|---|---|---|---|---|---|---|---|
| **Average HRV** | -3.065 | 0.0292 | Reject $H_0$ | 0.998 | 0.0100 | Reject $H_0$ | **Trend-stationary** |
| **Lowest Heart Rate** | -3.239 | 0.0179 | Reject $H_0$ | 1.272 | 0.0100 | Reject $H_0$ | **Trend-stationary** |
| **Sleep Efficiency** | -3.060 | 0.0296 | Reject $H_0$ | 0.246 | 0.1000 | Fail | Stationary |
| **Readiness Score** | -4.232 | 0.0006 | Reject $H_0$ | 0.271 | 0.1000 | Fail | Stationary |

### 6.2 Regime Annotation and Change-Point Detection

Executing the PELT search space segmented the 130-day index into three broad regimes divided by two stark transitions (Table 2). 

**Table 2: Annotated Change-Point Transitions**

| Date | Signal | Before Mean | After Mean | Shift | Annotated Context |
|---|---|---|---|---|---|
| **2025-12-27** | Average HRV | 81.16 ms | 67.63 ms | -16.7% | Travel/Schedule Disruption |
| **2026-02-27** | Lowest HR | 48.68 bpm | 44.14 bpm | -9.3% | Start of Marathon Training |

Both algorithmic measurements aligned precisely with independent biological triggers. Interstate travel disrupted homeostatic conditions driving a profound parasympathetic withdrawal (HRV suppression). Two months later, marathon training overload forced a cardiovascular adaptation reducing resting chronotropic demand by approximately 4.5 BPM as stroke volumes increased.

### 6.3 Operational Latency of Naive Baselines

The quantitative cost of assuming a continuous single moving baseline is severe. For the HRV regime collapse on Dec 27th, the 30-day global rolling mean lagged PELT boundary execution by a full **7 days**. The algorithmic platform failed to reflect the true physiological suppression for a full week.

More critically, the traditional commercial mathematical model **completely failed to detect the marathon adaptation transition** in Resting Heart Rate. A -4.5 BPM permanent sustained cardiac adaptation was gradual enough that moving target heuristics entirely absorbed the enhancement without raising any statistical deviance indicators.

![Nonstationarity Analysis](../analyses/physiological_nonstationarity/results/nonstationarity_analysis.png)
*Figure 1: Four signals on a linked temporal axis. Light traces indicate raw values, while bold lines represent naive 30-day rolling means. Dashed vertical divisions indicate exact PELT boundaries.*

### 6.4 Training Context Heterogeneity

We applied the ACWR framework to identify causal inputs preceding the structural breakdowns.

| Feature | Pre-HRV (Dec 14 to 27) | Percentile (All windows) | Pre-RHR (Feb 14 to 27) | Percentile (All windows) |
|---|---:|---:|---:|---:|
| Cumulative Distance (m) | 0 | 61% | 22,390 | 64% |
| Workout Days | 0 | 58% | 6 | 64% |
| **ACWR (Distance)** | Undefined | - | **4.00** | **100%** |

The training states strictly diverged. The HRV transition resulted from a period of strict physical detraining but environmental anomaly (zero recorded stimuli). In contrast, the cardiovascular RHR adaptation was precipitated directly by an intense acute spike corresponding to an **ACWR equal to 4.0**, locating it in the absolute 100th percentile of measured fatigue density across the evaluated period.

![Feature Distributions](../analyses/training_load_predictors/results/feature_distributions.png)
*Figure 2: Empirical distribution of rolling 14-day training features relative to the specific values recorded directly prior to transitions. The RHR transition window clearly spikes extreme ACWR structural deviations.*

---

## 7. Discussion

The presence of empirically detectable physiological regimes carries profound implications for human telemetry analytics. 

**The Composite Score Paradox:** Results outline that the raw fundamental indicators (HRV and RHR) display profound trend-stationarity, while composite metrics attempting to quantify total homeostasis (Readiness Score) test as strictly stationary. This dictates an algorithmic paradox: the heavy smoothing utilized by proprietary composite scores successfully absorbs systemic variance, ultimately suppressing the structural regime shifts mathematically present within raw hardware telemetry. In optimizing for smooth consumer experiences, commercial algorithms actively strip out the capacity to observe actual deep-state transition adaptations. 

**Detecting Adaptation Versus Noise:** The identified heterogeneity observed in the pre-transition training loads suggests that transition boundaries mark moments of profound structural system shock, but the shock can be an adaptation to positive strain (RHR dropping sequentially post-marathon overload) or reactive fatigue to environmental instability. Treating every deviation across a global window identically causes both scenarios to issue indistinguishable "poor recovery" alerts natively. The only method to decouple noise from adaptation is the installation of discrete, regime-aware boundaries locally estimating variance matrices inside unique partitions.

---

## 8. Limitations

**Singular Observation Window ($N=1$):** Every metric modeled reflects a specialized data vector applied to a single physiological structure over 130 days. Generalized claims about universal human physiological behaviors are beyond the paper's intent. Rather, the goal is proving systemic mathematical vulnerability within existing commercial baseline formulations via granular case-study precision.

**Constant Boundary Penalty Modeling:** The $pen=10$ parameter fixed the sparsity limits during optimization processing. An algorithmic approach operating Bayesian Information Criterion calculations dynamically might yield highly granular boundaries reflecting more temporary environmental stress points rather than broad biological adaptations.

---

## 9. Conclusion

Algorithmically assuming physiological stationarity leads to systematic reporting failures currently embedded inside typical commercial wearables. We rigorously identified using mathematical evaluation spanning 130 days of longitudinal Oura Gen 4 and Apple Health telemetry that core biological indicators behave as naturally transitioning trend-stationary elements instead. Imposing generic static rolling standard deviations severely lags or completely ignores permanent adaptational transitions. Conversely, we successfully implement a completely reproducible, multi-source regime-aware platform invoking independent time-segmented boundaries.

---

## 10. References

Adams, R. P., & MacKay, D. J. C. (2007). Bayesian online changepoint detection. *arXiv preprint arXiv:0710.3742*. https://doi.org/10.48550/arXiv.0710.3742

Gabbett, T. J. (2016). The training and injury prevention paradox: should athletes be training smarter and harder? *British Journal of Sports Medicine, 50*(5), 273 to 280. https://doi.org/10.1136/bjsports-2015-095788

Killick, R., Fearnhead, P., & Eckley, I. A. (2012). Optimal detection of changepoints with a linear computational cost. *Journal of the American Statistical Association, 107*(500), 1590 to 1598. https://doi.org/10.1080/01621459.2012.737745

Plews, D. J., Laursen, P. B., Stanley, J., Buchheit, M., & Kilding, A. E. (2013). Training adaptation and heart rate variability in elite endurance athletes: Opening the door to effective monitoring. *Sports Medicine, 43*(9), 773 to 781. https://doi.org/10.1007/s40279-013-0071-8

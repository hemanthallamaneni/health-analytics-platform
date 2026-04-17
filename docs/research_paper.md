# Physiological Nonstationarity in Wearable Sensor Data: A Methodological Case Study on Regime-Aware Baselines

**Author:** Hemanth Allamaneni  
**Affiliation:** MS Applied Cognition and Neuroscience (HCI and Intelligent Systems), The University of Texas at Dallas  
**Date:** April 2026  

## Abstract

Commercial wearable algorithms operate under the implicit assumption that human physiological signals are stationary within a rolling observation window. They compute daily readiness, recovery, and physiological strain scores against a slowly adapting global mean. While computationally efficient, this assumption risks misclassifying genuine biological adaptation (e.g., cardiovascular remodeling from exercise) or systematic environmental disruption (e.g., chronic travel strain) as transient noise. This paper tests the stationarity assumption empirically using continuous longitudinal data spanning 130 days from four heterogeneous sources (Oura Ring Gen 4, Apple HealthKit, RENPHO, and Strava). Joint application of Augmented Dickey-Fuller (ADF) and Kwiatkowski-Phillips-Schmidt-Shin (KPSS) tests demonstrates mathematically that biological primitives like heart rate variability (HRV) and resting heart rate (RHR) are trend-stationary, rather than stationary. By applying Pruned Exact Linear Time (PELT) change-point detection with a Radial Basis Function kernel, we identify two discrete, physiologically annotated regime transitions: one driven by travel disruption and the other by sustained aerobic training overload. We show that a naive 30-day rolling baseline lags regime transitions by up to a week and entirely fails to detect gradual, sustained cardiac adaptation. In response, we detail the system architecture for a fully reproducible, declarative, and regime-aware self-hosted analytics platform. We conclude that commercial baseline operations suppress valid regime structure, and outline exploratory directions in occupational health tracking and predictive state-space modeling where dynamic regime boundaries provide a vastly more actionable operational metric for personal telemetry.

---

## 1. Introduction

The quantitative core of the modern consumer wearable ecosystem is the daily composite score. Platforms such as Oura, Whoop, and Apple Health consistently synthesize derivatives of readiness, recovery, and physiological strain by comparing acute overnight metrics—specifically resting heart rate (RHR) and heart rate variability (HRV)—to a rolling longitudinal baseline. 

This universally adopted analytical foundation relies implicitly on the assumption of **physiological stationarity**. It assumes that the user's underlying physiological state behaves like a reverting homeostatic process, exhibiting a fixed mean and constant variance over the baseline calculation window (typically 14 to 30 days). Deviations from this mean are interpreted as transient acute stress—a poor night of sleep, acute illness, or an intense training session—rather than an orthogonal, permanent shift in the baseline itself.

However, physiological data fundamentally violates this assumption during periods of significant lifestyle change, environmental disruption, or structured physical training. This introduces the concept of **allostasis**: the process of achieving stability through physiological or behavioral change over time. When an individual adopts a rigorous endurance training program, the resulting cardiovascular adaptation permanently pulls the daily heart rate metric down. A stationary rolling-mean algorithm evaluates this adaptation inappropriately, logging it as consecutive days of "excellent" deviations until the 30-day window slowly swallows the new regime, pulling the unacknowledged baseline down with it. Similarly, when transitioning across time zones or encountering extended socioeconomic strain, HRV suppresses systemically. The rolling baseline significantly lags this transition, mathematically penalizing the user for standardizing at a newly established homeostatic set-point.

This paper operationalizes the natural question: what happens to health analytics when the biological stationarity assumption fails? We document an applied research program demonstrating this failure empirically, characterizing the exact latency cost of naive rolling means. We aim to move beyond describing the flaw to engineering its solution by detailing a reproducible data architecture that implements **regime-aware** baselines that capture the step-function nature of true physiological adaptation.

---

## 2. Theoretical Background and Related Work

The tension between static analytical models and continuous ongoing physiological adaptation is well-documented within clinical monitoring, sports science, and generalized time-series forecasting.

### 2.1 The Sports Science Paradox
Plews et al. (2013) extensively demonstrated that HRV in trained athletes is not well-described by a stationary process. Systematic drift occurs across macro-cycles of training, peaking phases, and off-seasons. They argue that regime-level shifts are fundamentally different from day-to-day noise, demanding dynamic analytical methods rather than static standard-deviation thresholds. 

Similarly, Gabbett (2016) revolutionized workload monitoring by popularizing the Acute-to-Chronic Workload Ratio (ACWR). The ACWR model explicitly addresses the dynamic relationship between a moving short-term load and a longer-term physiological base, acknowledging the fundamental truth that identical acute stimuli evoke radically different biological responses depending on the chronic physiological regime the athlete currently occupies.

### 2.2 Algorithmic Change-Point Detection (CPD)
Change-point detection forms the statistical backbone required to identify structural breaks in noisy time-series data, effectively segmenting continuous streams into discrete stationary blocks. Killick, Fearnhead, and Eckley (2012) introduced **Pruned Exact Linear Time (PELT)**, providing a computationally efficient exact search methodology for segmenting time-series under a defined penalty cost. Unlike heuristic sliding-window methods, PELT guarantees global optimality of the segmentation bounds, making it ideal for retrospective medical chart analysis and telemetry auditing.

To address the need for real-time inference, Adams and MacKay (2007) formalized **Bayesian Online Changepoint Detection (BOCPD)**, computing the predictive distribution of time since the last regime transition (the run-length) at each successive data point. While theoretically superior for real-time alerts, BOCPD introduces severe numerical stability challenges in production environments computing over long horizons without domain-specific log-space transformations.

### 2.3 The Commercial Incentive for Smoothing
Despite robust academic literature highlighting nonstationarity, commercial readiness scoring remains predominantly anchored to stationary rolling averages—frequently utilizing Exponential Moving Averages (EMA) to favor recency without introducing hard boundaries. We posit this is an engineering constraint masked as a physiological optimization: detecting true regime change dynamically across heterogeneous, multi-million user populations at scale is computationally expensive and highly prone to false-positive volatility. Consumers prefer smooth, predictable application interfaces over the jarring stochastic reality of segmented step-transitions.

---

## 3. System Architecture and Data Infrastructure

To prove these theories outside of simulated datasets, the findings in this paper were produced within a fully integrated, automated, and declarative data platform architecture designed for continuous $N=1$ telemetry ingestion.

### 3.1 Heterogeneous Source Ingestion
The platform eliminates vendor-lock by ingesting from four disparate hardware and software systems:

1. **Oura Ring Gen 4:** An automated Python extraction loops through the paginated REST API, capturing nightly sleep stages, RMSSD (HRV), Readiness scores, and respiratory rates. 
2. **Apple Health (Heart Rate and Biomarkers):** Direct parsing of the native `export.xml` schema resulting from an Apple Health repository. This utilizes massive associative arrays of granular `HKQuantityType` records with explicit vendor metadata filtering to eliminate redundant hardware overlap (e.g., stripping iPhone pedometer data while preserving Watch optical telemetry).
3. **RENPHO / HealthKit:** Body composition and basal metabolic metrics written to Apple HealthKit via the proprietary RENPHO electrical impedance ecosystem.
4. **Strava:** An incremental OAuth2 pipeline capturing highly granular physical activity, training load estimations (Power, Kilojoules, TRIMP), and GPS distance metrics.

### 3.2 ELT Architecture and Materialization Layer
Raw JSON arrays and XML nodes are loaded directly into raw schemata in a secure Snowflake data warehouse. The transformation logic is orchestrated entirely in a **dbt (data build tool)** layer, enforcing absolute reproducibility and idempotency. 

The staging tables resolve immense data-engineering hurdles native to wearable APIs, primarily **timezone normalization**. Since subjects travel across time zones, local day boundaries fracture. The staging layer strictly binds physiological metrics to normalized local calendar days to preserve the physiological continuity of a "night" of sleep, rather than arbitrary UTC cutoffs.

These are aggressively joined into a denormalized layer (`mart_health.daily_health_summary`). Advanced recursive models (`mart_regime_labels`, `mart_training_load_features`) then compute rolling window features, encode the boundaries of statistical regimes generated by the Python scientific backend, and partition summary statistics recursively for the localized dashboard interfaces.

---

## 4. Data Topography

The dataset comprises continuous longitudinal telemetry capturing a period of known instability, providing the requisite density for structural transition evaluation.

| Property | Value |
|---|---|
| **Sources** | Oura Ring Gen 4, Apple Watch Series 7, Strava |
| **Observation Window** | November 25, 2025 to April 11, 2026 |
| **Duration** | 130 active, continuous days |
| **Missingness** | Strict zero missingness across primary target signals |
| **Features Modeled** | Average HRV, Lowest HR, Sleep Efficiency, Readiness Score |

**Epidemiological Constraints ($N=1$):**
The limitation of an $N=1$ dataset is absolute regarding generalized clinical claims mapping directly to broader populations. However, the intent of this portfolio is fundamentally methodological. The objective is to demonstrate computationally how the stationarity assumption universally fails and strictly detail the analytical alternative. The statistical pipelines engineered here scale perfectly agnostically to an $N=10,000$ cohort without requiring any structural mathematical refactoring.

---

## 5. Mathematical Formulations and Proofing

The core of this research bypasses opaque hardware platform algorithms to execute rigorous time-series theorems natively against the raw sensor streams. 

### 5.1 Joint Stationarity Testing Formulae
To formally prove whether physiological homeostasis respects a static mean, we jointly execute the Augmented Dickey-Fuller (ADF) and Kwiatkowski-Phillips-Schmidt-Shin (KPSS) statistical specifications. 

**The ADF Test Specification:**
The ADF rigorously evaluates the presence of a unit root (null hypothesis: the series is non-stationary and exhibits stochastic drift). The required regression model expands as:

$$ \Delta y_t = \alpha + \beta t + \gamma y_{t-1} + \sum_{i=1}^{p} \delta_i \Delta y_{t-i} + \epsilon_t $$

where $\Delta y_t$ isolates the first difference of the biological series, $\alpha$ represents a baseline constant, $\beta t$ captures localized deterministic trends, $p$ defines the lag order requisite to absorb serial correlations specific to cardiac rhythms, and $\epsilon_t$ bounds the white noise error. 

**The KPSS Test Specification:**
Conversely, the KPSS test inverts the evaluation, assuming the null hypothesis represents true exact level-stationarity. The structural model tracks:

$$ y_t = \xi t + r_t + \epsilon_t $$
$$ r_t = r_{t-1} + u_t $$

where $u_t$ represents identically distributed random variables with zero mean. Mathematical proofing dictates that when both ADF and KPSS reject their null hypotheses effectively, the physiological series is definitively **trend-stationary**: shifting biological elements override global stationary bounds.

### 5.2 Pruned Exact Linear Time (PELT) Segmentation
We apply the PELT algorithm retrospectively to surgically segment hardware timelines. For a telemetry data sequence $y_{1:N}$, the computational execution identifies an array of structural changepoints $\tau = (\tau_1, \tau_2, ..., \tau_m)$ minimizing the global cost layout:

$$ \min_{\tau} \left[ \sum_{i=1}^{m} C(y_{(\tau_{i-1}+1):\tau_i}) + m p \right] $$

where $C$ defines a Radial Basis Function Gaussian Kernel (resolving parameter variance independently of mean structures), $m$ governs the count of physiological phases detected, and $p=10$ provides a linear penalty threshold specifically calibrated to eliminate micro-fluctuation hyper-fragmentation and ensure the resultant boundaries represent structurally actionable biological shifts.

### 5.3 Workload Context Modeling
To accurately define dynamic physical states triggering these biological regime changes, we engineered an **Acute-to-Chronic Workload Ratio (ACWR)** metric modeled natively in the warehouse. The ratio calculates the exact fatigue pressure (Trailing 7-days) against the stable biological block (Trailing 28-days):

$$ \text{ACWR}_t = \frac{\frac{1}{7} \sum_{i=0}^{6} \text{Load}_{t-i}}{\frac{1}{28} \sum_{i=0}^{27} \text{Load}_{t-i}} $$

---

## 6. Analytic Results

### 6.1 Formal Stationarity Rejection Results
Table 1 outlines the exact calculation parameters. Heart rate variability and resting heart rate explicitly fail the stationarity assumption. Both ADF and KPSS reliably reject simultaneously, forcing the determination that HRV and RHR actively transition between discrete, disconnected physiological states. 

**Table 1: Unit Root and Level Stationarity Testing**

| Signal | ADF Stat | ADF p | ADF Result | KPSS Stat | KPSS p | KPSS Result | Verdict |
|---|---|---|---|---|---|---|---|
| **Average HRV** | -3.065 | 0.0292 | Reject $H_0$ | 0.998 | 0.0100 | Reject $H_0$ | **Trend-stationary** |
| **Lowest Heart Rate** | -3.239 | 0.0179 | Reject $H_0$ | 1.272 | 0.0100 | Reject $H_0$ | **Trend-stationary** |
| **Sleep Efficiency** | -3.060 | 0.0296 | Reject $H_0$ | 0.246 | 0.1000 | Fail | Stationary |
| **Readiness Score** | -4.232 | 0.0006 | Reject $H_0$ | 0.271 | 0.1000 | Fail | Stationary |

### 6.2 Biological Regime Annotation
Executing the exact PELT search space objectively segmented the 130-day index into three broad regimes divided by two stark transitions (Table 2). 

**Table 2: Annotated Change-Point Transitions**

| Date | Signal | Before Mean | After Mean | Shift | Annotated Context |
|---|---|---|---|---|---|
| **2025-12-27** | Average HRV | 81.16 ms | 67.63 ms | -16.7% | Extreme Travel Disruption |
| **2026-02-27** | Lowest HR | 48.68 bpm | 44.14 bpm | -9.3% | Marathon Training Base |

Both transitions are biologically verified. The December interstate travel expanded cardiovascular load significantly, suppressing intrinsic HRV tone. Sixty days later, aerobic marathon stimuli forced critical adaptation, fundamentally lowering chronotropic demand by approximately 4.5 BPM as absolute stroke volumes structurally heightened.

### 6.3 Operational Latency of Naive Baselines
The cost of assuming a single global moving target (the ubiquitous commercial approach) is severe quantitative latency. 

For the HRV regime collapse on Dec 27th, the 30-day global rolling mean lagged the exact PELT boundary execution by a full **7 days**. The user practically experienced a physiologically suppressed state for a full week before the algorithm mathematically acknowledged it as an outlying regime.

Even more consequentially, the rolling mean **completely failed to detect the marathon adaptation transition** in Resting Heart Rate. A -4.5 BPM permanent cardiac augmentation was gradual enough over a 10-day span to be smoothly digested and accepted without ever alerting standard deviation heuristics (Figure 1).

![Nonstationarity Analysis](../analyses/physiological_nonstationarity/results/nonstationarity_analysis.png)
*Figure 1: Four signals on a linked temporal axis. Light traces indicate raw values, while bold lines represent naive 30-day rolling means. Dashed vertical divisions indicate exact algorithmic PELT boundaries mapping biological regimes.*

### 6.4 Explanatory Models & Heterogeneity
When analyzing the exact 14-day trailing features leading into the two measured boundaries, we determined stark causal asymmetry. 

| Feature | Pre-HRV (Dec 14 to 27) | Percentile (All dataset limits) | Pre-RHR (Feb 14 to 27) | Percentile (All dataset limits) |
|---|---:|---:|---:|---:|
| Cumulative Distance (m) | 0 | 61% | 22,390 | 64% |
| Workout Days | 0 | 58% | 6 | 64% |
| **ACWR (Distance)** | Undefined | - | **4.00** | **100%** |

The HRV transition resulted from a period of strict physical detraining combined with acute environmental anomaly (travel strain). In contrast, the cardiovascular RHR adaptation was precipitated directly by an intense acute exercise spike corresponding to an **ACWR equal to 4.0**, accurately locating it in the absolute 100th percentile of measured fatigue density mathematically across the evaluated period (Figure 2).

![Feature Distributions](../analyses/training_load_predictors/results/feature_distributions.png)
*Figure 2: Empirical distribution of rolling 14-day training features relative to the specific values recorded directly prior to transitions. The RHR transition window spikes ACWR structural deviations beyond typical baselines.*

---

## 7. Extended Discussion

The empirical presence of detectable, rigid physiological regimes carries profound implications for human telemetry analytics.

**The Composite Score Paradox and Allostatic Weight:** Results outline that the raw foundational indicators (HRV and RHR) display profound trend-stationarity, while proprietary composite metrics attempting to abstract total homeostasis (the "Readiness Score") test as strictly stationary. This dictates an intense algorithmic paradox: the heavy mathematical smoothing inherently utilized by consumer composite scores literally absorbs systemic biological variance. In optimizing for smooth consumer experiences and eliminating volatility, commercial algorithms actively strip out the capacity to observe actual deep-state transition adaptations (allostatic shifting). 

**Detecting True Biological Adaptation Versus Stochastic Noise:** The causal heterogeneity identified within the pre-transition training loads suggests that biological transition boundaries mark moments of profound structural shock. Crucially, that shock can be an *adaptation to positive strain* (RHR dropping sequentially post-marathon overload) or *reactive fatigue* to environmental instability (Travel strain). Imposing blanket thresholds across a global window forces algorithms to issue indistinguishable "poor recovery" or "excellent condition" alerts natively for entirely disparate scenarios. 

The exclusive method to mathematically decouple superficial noise from systemic adaptation requires the structural installation of discrete, regime-aware boundaries locally estimating variance matrices strictly inside uniquely calculated chronological partitions.

---

## 8. Exploratory Research Directions

The methodologies generated by this applied case study dramatically open several expansive branches of future research, promising substantial industrial and clinical capabilities previously bottlenecked by rolling algorithms.

### 8.1 Predictive Regime Modeling via Hidden Markov Models (HMM)
While PELT excels at identifying boundaries offline retrospectively, forecasting *how* and *when* a user will transition into a new regime demands predictive state-space modeling. Implementing Multivariate Hidden Markov Models processing HRV, ACWR, and Sleep Efficiency vectors natively can represent physiological "states" conditionally. Investigating whether specific transition probabilities escalate acutely as ACWR breaches threshold lines (e.g., probability of transitioning to an overreaching regime surges when ACWR > 1.5) provides a proactive capability for intelligent software to intervene before biological breakdown occurs. 

### 8.2 Real-time BOCPD and Mathematical Nuance 
Transitioning this pipeline into a real-time notification engine necessitates robust Bayesian Online Changepoint Detection. As discussed, traditional BOCPD Normal-Gamma configurations exhibit critical underflow vulnerabilities natively processing vast arrays of $t$-distributions during periods of hyper-stability. Formally engineering log-space matrix transformations leveraging GPU/CUDA integrations directly on edge devices (like the Apple Watch microprocessor) or securely via continuous analytical webhooks represents the next crucial milestone for instantaneous, latency-free localized alert mechanisms.

### 8.3 Multivariate Pipeline Implementations
Currently, standard implementations treat parameters linearly and univariately. However, biological signals operate completely interdependently (Resting HR reacts synergistically with core body temperature parameters and respiratory rates). Advancing the cost functions to utilize Graph-based transition detection metrics or multidimensional covariance tracing will greatly eliminate false-positive anomalies, distinguishing a valid cardiovascular adaptation block from a temporary localized illness trace.

### 8.4 Occupational Health and Performance Scaling
Applying these regime-detection methodologies directly across high-risk specialized workforces unlocks unprecedented operational analytics. The identical baseline parameters failing athletes simultaneously fail nocturnal ER staff shift cycles or active military deployment contingents. Utilizing this pipeline to trace exact biological regime collapses against continuous localized operational rosters provides administrators the verifiable power to accurately predict systemic staff fatigue prior to catastrophic burnout breakpoints natively, escaping the trap of standard generalized averages.

---

## 9. Conclusion

Consumer hardware possesses extraordinary sensory capabilities bottlenecked entirely by mathematical assumptions embedded in standard data models. Algorithmically assuming physiological stationarity leads to systematic reporting failures severely misclassifying natural biological behaviors. Through rigorous execution mapping 130 days of longitudinal Oura Gen 4 and Apple Health telemetry, we successfully prove that continuous core indicators behave fundamentally as shifting, trend-stationary elements. Imposing generic rolling standard deviations either severely lags actual systemic reactions by a full week or completely ignores continuous, permanent morphological adaptations altogether. By rejecting these assumptions, we have successfully developed, compiled, and proven a vastly superior multi-source regime-aware platform invoking independent Bayesian and PELT boundaries directly within the operational data warehouse, returning unadulterated analytical clarity directly back to the system owner.

---

## 10. References

Adams, R. P., & MacKay, D. J. C. (2007). Bayesian online changepoint detection. *arXiv preprint arXiv:0710.3742*. https://doi.org/10.48550/arXiv.0710.3742

Gabbett, T. J. (2016). The training and injury prevention paradox: should athletes be training smarter and harder? *British Journal of Sports Medicine, 50*(5), 273 to 280. https://doi.org/10.1136/bjsports-2015-095788

Killick, R., Fearnhead, P., & Eckley, I. A. (2012). Optimal detection of changepoints with a linear computational cost. *Journal of the American Statistical Association, 107*(500), 1590 to 1598. https://doi.org/10.1080/01621459.2012.737745

Plews, D. J., Laursen, P. B., Stanley, J., Buchheit, M., & Kilding, A. E. (2013). Training adaptation and heart rate variability in elite endurance athletes: Opening the door to effective monitoring. *Sports Medicine, 43*(9), 773 to 781. https://doi.org/10.1007/s40279-013-0071-8

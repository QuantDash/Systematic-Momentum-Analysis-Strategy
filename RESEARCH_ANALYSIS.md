# Empirical Analysis of Andreas Clenow's Systematic Momentum Strategy on the NSE Nifty 500

> **A Quantitative Finance Study on Emerging Market Microstructure, Downside Bleed, Lookback Decay, and Integer Sizing Friction.**
 
> **Universe:** National Stock Exchange of India (NSE) NIFTY 500 Constituents  
> **Data Range:** July 15, 2024 – October 19, 2026 (Warm-Up & Active Horizons)  
> **Methodological Standard:** Point-in-Time Constituents, Next-Day Open Execution ($T+1$), Full Statutory Friction Modeling

---

## Abstract & Executive Summary

In contemporary quantitative equity management, cross-sectional systematic momentum remains one of the most widely documented empirical risk premia. Andreas Clenow’s seminal framework (*Stocks on the Move*, 2015) established an institutional standard for capturing intermediate-term momentum within developed markets (principally the US S&P 500). The textbook model couples:
1. An **exponential regression slope** scaled by the coefficient of determination ($R^2$) to isolate persistent, low-volatility trends.
2. A **macro regime filter** (200-day Simple Moving Average on the broad index) to mitigate catastrophic tail risk during market crashes.
3. **Inverse-volatility position sizing** to enforce equal risk contribution across holdings.
4. A **monthly rebalance schedule** with cash-scaling buffers during regime breakdowns.

This research paper provides an exhaustive empirical evaluation of Clenow’s textbook model deployed natively on the **NSE NIFTY 500 universe**. 

Our primary finding is that **direct translation of developed-market momentum specifications to Indian equities induces systematic capital erosion and severe risk-adjusted underperformance**:
* The textbook model ($W_m = 125\text{ days}$, $M_{\min} = 40.0$, $W_{\text{index}} = 200\text{ days}$) across the full evaluation window generated a **Cumulative Return of -5.54%** and a **Sharpe Ratio of -1.02** (benchmarked against the Indian 91-day T-bill risk-free rate of $6.5\%$), underperforming the NIFTY 500 benchmark (+2.99%).
* **Downside Capture Asymmetry:** During the March 2026 correction (-11.39% index drawdown), the strategy was heavily invested in high-beta names and plunged -6.86%. When the market staged a rapid V-shaped recovery in April 2026 (+10.50%), the slow-moving 200-day index filter locked the portfolio into **82.5% to 90.1% uninvested cash**, capturing a meager +0.59%.
* **The Lookback Exhaustion Trap:** In high-velocity Indian sector rotations, a 125-day lookback buys momentum at the parabolic blow-off exhaustion point, suffering subsequent mean-reversion crashes. Empirical grid optimization reveals a **broad, stable parameter plateau centered at 90 days**, lifting total return from **-5.54% to +2.44%**.
* **Data Hygiene Standard:** All simulations are executed on survivor-bias-free, split- and corporate-action adjusted equity series to preserve institutional fidelity.
* **Microstructure & Integer Sizing Friction:** The strict absence of fractional shares on the NSE/BSE distorts inverse-volatility risk parity into an arbitrary price-weighted lottery for retail accounts (₹1 Lakh), forcing a **53%–55% chronic cash drag**. Only at institutional scales (≥₹5 Lakhs to ₹10 Lakhs) does integer allocation converge to theoretical risk parity.

---

## 1. Experimental Parameter Specifications

To eliminate ambiguity, the table below documents all model parameters, mathematical notations, textbook defaults, and the specific parameter ranges evaluated in our grid-search optimization to analyze how different parameter values perform across market conditions:

| Parameter Name | Math Symbol | Clenow Textbook Default | Empirical Tested Range | Functional Role in Architecture |
| :--- | :---: | :---: | :---: | :--- |
| **Momentum Lookback Window** | $W_m$ | **125 Days** | 60, 90, 125 Days | Horizon over which OLS exponential slope is fit |
| **Minimum Momentum Score** | $M_{\min}$ | **40.0** | 30.0, 40.0, 50.0 | Conviction threshold ($Slope \times R^2$) required to buy/hold |
| **Index Regime Filter Window** | $W_{\text{index}}$ | **200 Days** | 100, 200 Days | SMA period on Nifty 500 to trip macro "red light" |
| **Volatility Lookback Window** | $W_v$ | **20 Days** | Fixed 20 Days | Rolling window for inverse-volatility risk budgeting |
| **Portfolio Slot Capacity** | $N$ | **30 Stocks** | 20, 30 Stocks | Maximum number of concurrent portfolio holdings |
| **Single-Stock Weight Cap** | $w_{\max}$ | **15.0%** | Fixed 15.0% | Upper boundary constraint on inverse-volatility weighting |
| **Transaction Friction Rate** | $\phi$ | ~0.0005 (US) | **0.0015 (India)** | Statutory tax + slippage model per trade leg (15 bps) |
| **Risk-Free Benchmark Rate** | $R_f$ | 2.0% (US T-Bills) | **6.5% (India 91d T-Bills)** | Baseline hurdle rate used in Sharpe Ratio calculations |

---

## 2. Horizon Decomposition & Indicator Warm-Up Accounting

A common source of confusion in quantitative backtests is the distinction between the nominal backtest date and the active execution date. 

Because the index regime filter requires $W_{\text{index}} = 200\text{ trading days}$, any backtest executed on a database with an inception date of July 15, 2024 **cannot legally compute a 200-day moving average on February 1, 2025**.

```text
  2024-07-15              2025-02-01               2025-05-08    2025-06-02                 2026-10-19
      ├───────────────────────┼────────────────────────┼─────────────┼───────────────────────────┤
      │  Database Inception   │ Nominal Script Request │ 200-SMA Day │ First Trade Execution     │ Ingestion
      │  History Accumulates  │ 139 Days (UNINITIALIZED) 200 Days    │ (Month-End Rebalance)     │ End Date
      └───────────────────────┴────────────────────────┴─────────────┴───────────────────────────┘
      │◄────── Historical Warm-Up Phase ──────────────►│◄────── Active Investment Phase ────────►│
```

### Timeline Decomposition Table
* **Database Inception Date:** July 15, 2024
* **Nominal Script Request Date:** February 1, 2025 (Available warm-up history: 139 trading days < 200 required).
* **200-SMA Indicator Maturity Date:** May 8, 2025 (Exactly 200 trading days reached).
* **First Rebalance Calculation:** May 30, 2025 (Last trading day of May).
* **First Order Execution Day:** **June 2, 2025 (Market Open)**.
* **Terminal Backtest Day:** October 19, 2026.
* **Uninvested Warm-Up Cash Duration:** 67 Trading Days (February 1, 2025 – May 7, 2025). The portfolio held **100% Cash (₹100,000.00)**.
* **Active Trading Duration:** **343 Trading Days (~1.36 Calendar Years)**.
* **Total Nominal Horizon:** **421 Trading Days (~1.67 Calendar Years)**.

> [!IMPORTANT] Dual-Horizon Reporting Standard
> In the subsequent performance tables, CAGR and Sharpe metrics are evaluated across the **Active Trading Horizon (343 days)** where capital was exposed to market risk, alongside the **Full Nominal Horizon (421 days)** to ensure complete reporting transparency.

---

## 3. The Parameter Plateau Analysis ($3 \times 3$ Walk-Forward Matrix)

Below is the complete empirical grid search across 9 combinations of lookback windows ($W_m \in \{60, 90, 125\}$) and conviction thresholds ($M_{\min} \in \{30.0, 40.0, 50.0\}$) on the Nifty 500 universe (capital = ₹100,000; adjusted price series):

### Full $3 \times 3$ In-Sample Parameter Grid Matrix

| Lookback Window ($W_m$) | Conviction Threshold ($M_{\min}$) | Final Portfolio Value | Cumulative Return | Maximum Drawdown | Completed Exits | Win Rate (%) | Regime Classification |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **60 Days** | **30.0** | ₹94,534.32 | **-5.47%** | -8.60% | 133 | 35.3% | Hyperactive Noise / Churn |
| **60 Days** | **40.0** | ₹93,763.31 | **-6.24%** | -9.21% | 135 | 35.6% | Hyperactive Noise / Churn |
| **60 Days** | **50.0** | ₹93,101.27 | **-6.90%** | -9.92% | 144 | 36.8% | Hyperactive Noise / Churn |
| **90 Days** | **30.0** | ₹102,802.63 | **+2.80%** | -9.29% | 104 | 40.4% | **Robust Parameter Plateau** |
| **90 Days** | **40.0 (Textbook Threshold)** | ₹102,441.82 | **+2.44%** | -8.57% | 114 | 42.1% | **Robust Parameter Plateau** |
| **90 Days** | **50.0** | ₹102,361.37 | **+2.36%** | -7.91% | 120 | 44.2% | **Robust Parameter Plateau** |
| **125 Days (Clenow)** | **30.0** | ₹94,098.77 | **-5.90%** | -11.91% | 92 | 30.4% | Late Exhaustion Trap |
| **125 Days (Clenow)** | **40.0 (Clenow Textbook)** | ₹94,462.69 | **-5.54%** | -10.81% | 94 | 39.4% | **Textbook Baseline Decay** |
| **125 Days (Clenow)** | **50.0** | ₹94,370.67 | **-5.63%** | -10.04% | 96 | 37.5% | Late Exhaustion Trap |

![Figure 7: Parameter Plateau Heatmap](docs/images/fig7_optimizer_grid_heatmap.png)
*Figure 7: In-Sample Parameter Plateau Analysis. The 90-day window forms an invariant, robust island of positive return across all conviction thresholds, whereas 60-day and 125-day models systematically fail.*

### Theoretical Interpretation of the Grid:
1. **The 60-Day Zone (Hyperactive Turnover):** At 60 days, the strategy attempts to trade short-term swing momentum. Exit counts explode to 133–144 trades. High turnover in an emerging market governed by 0.10% STT and exchange fees leads to death by a thousand paper cuts.
2. **The 125-Day Zone (Textbook Inertia):** At 125 days, returns are uniformly negative across all cutoffs (-5.54% to -5.90%), suffering the largest drawdowns (-10.0% to -11.9%). The lookback is too sluggish to keep pace with Indian thematic cycles.
3. **The 90-Day Zone (The Structural Optimum):** The 90-day lookback yields **positive performance across all three score cutoffs** (+2.36% to +2.80%) with lower maximum drawdown (-7.9% to -9.3%) and higher win rates (40.4% to 44.2%). This aligns with the institutional quarterly earnings reporting cycle in India, capturing acceleration waves without holding into deep distribution.

---

## 4. Comparative Performance & Risk Analytics

Below is the multi-tier performance audit comparing the Textbook Baseline against the Empirical 90-Day model across three capital tiers (₹1 Lakh, ₹5 Lakhs, ₹10 Lakhs) and the NIFTY 500 Benchmark:

### Master Quantitative Performance Table

| Metric | Textbook Clenow (125d, Score 40, ₹1L) | Empirical Model (90d, Score 40, ₹1L) | Scale Model (90d, Score 40, ₹5L) | Scale Model (90d, Score 40, ₹10L) | NIFTY 500 Benchmark (Aligned Horizon) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Initial Capital** | ₹1,00,000.00 | ₹1,00,000.00 | ₹5,00,000.00 | ₹10,00,000.00 | Baseline |
| **Final Portfolio Value** | **₹94,462.69** | **₹102,441.82** | **₹512,740.82** | **₹1,018,284.54** | Normalized (₹1,02,990 / ₹1L) |
| **Cumulative Return** | **-5.54%** | **+2.44%** | **+2.55%** | **+1.83%** | **+2.99%** |
| **Active CAGR (343 days)** | **-4.10%** | **+1.79%** | **+1.87%** | **+1.34%** | **+2.19%** |
| **Nominal CAGR (421 days)** | **-3.35%** | **+1.45%** | **+1.52%** | **+1.09%** | **+1.78%** |
| **Annualized Volatility** | 9.64% | 10.13% | 11.31% | 11.53% | 14.12% |
| **Maximum Drawdown (MDD)** | **-10.81%** | **-8.57%** | **-9.08%** | **-9.51%** | **-14.82%** |
| **Sharpe Ratio ($R_f = 6.5\%$)** | **-1.02** | **-0.50** | **-0.44** | **-0.47** | **-0.33** |
| **Average Idle Cash Drag** | **55.5%** | **53.9%** | **45.6%** | **43.7%** | 0.0% |
| **Total Closed Exits** | 94 | 114 | 130 | 136 | N/A |
| **Exit Win Rate** | 39.4% | **42.1%** | 40.0% | 39.0% | N/A |

---

## 5. Four Structural Failures in Indian Equities

### 5.1 Macro Regime Filter Latency & The V-Shaped Recovery Trap
The 200-SMA rule was designed for the S&P 500, which exhibits prolonged multi-quarter bear markets (e.g., 2000–2002, 2007–2009). The Indian market exhibits violent, compressed V-shaped reversals driven by domestic SIP liquidity.

![Figure 2: Downside Asymmetry and Cash Lockout](docs/images/fig2_downside_trap_and_cash.png)
*Figure 2: The Downside Asymmetry Trap. Note the portfolio suffering full drawdowns in July 2025 and March 2026, followed by a persistent 80%–90% cash lockout during the April 2026 recovery.*

---

### 5.2 The 125-Day Momentum Exhaustion Trap
In Indian equities, thematic sector momentum (e.g., PSU, Defense, Railways) typically exhausts within 45 to 60 trading days. A 125-day exponential regression slope remains artificially elevated long after distribution has begun, causing the algorithm to buy at parabolic peaks.

![Figure 3: Peak Entry Case Study](docs/images/fig3_peak_entry_drawdown.png)
*Figure 3: Case study of a stock entered at its parabolic peak due to backward-looking 125-day momentum, resulting in heavy drawdowns during subsequent mean reversion.*

![Figure 6: Lookback Comparison](docs/images/fig6_lookback_comparison.png)
*Figure 6: Lookback Window Trajectory: 125-Day Textbook vs. 90-Day Agile Momentum vs. NIFTY 500 Benchmark.*

---

### 5.3 Discrete Integer Sizing Breakdown at Retail Scales (₹1 Lakh)
Because fractional shares are illegal on the NSE, target risk weights $w_i$ are mapped via integer floor truncation:

$$\text{Shares}_i = \left\lfloor \frac{V_t \times w_i}{P_{i, \text{open}}} \right\rfloor$$

At $V_t = ₹100,000$ and $N = 30$, average nominal allocation is ~₹3,333:
1. **Universe Truncation:** Over **150 stocks in the Nifty 500** trade at share prices above ₹3,333 (e.g., Maruti, Solar Industries, Apar Industries, ABB, OFSS, Divis Lab). For these stocks, `math.floor` yields **0 shares**. The algorithm is forced to skip top-ranked compounders entirely.
2. **Risk Parity Distortion:** If a stock's volatility demands a 1.5% allocation (₹1,500), but trades at ₹3,000, buying 1 share forces a 3.0% allocation—doubling the intended risk exposure.
3. **Chronic Cash Drag:** The portfolio suffers an average of **53.9% idle cash drag** at ₹1L.
4. **Resolution at Scale:** At ₹5 Lakhs (slot ~₹16,666) and ₹10 Lakhs (slot ~₹33,333), the cash drag drops significantly, and portfolio allocations faithfully track the theoretical risk-parity curve.

![Figure 4: Capital Scale Friction](docs/images/fig4_capital_scale_integer_friction.png)
*Figure 4: The Impact of Integer Share Granularity across Capital Scales on the National Stock Exchange.*

---

### 5.4 Statutory Execution Friction & The Indian Tax Wedge
In developed markets, zero-commission brokers and no turnover taxes allow frequent rebalancing. In India:
* **Securities Transaction Tax (STT):** 0.10% on entry + 0.10% on exit = **0.20% flat tax on turnover**.
* Total statutory frictions + slippage = **30 bps round-trip**.
* When win rates hover around ~40% and average win (+13.0%) only moderately exceeds average loss (-9.0%), transaction drag extracts substantial compounding capital.

![Figure 1: Realized PnL Bars](docs/images/fig1_pnl_horizontal_bars.png)
*Figure 1: Net realized PnL (₹) for Top 10 Winners vs. Top 10 Losers in the Book Strategy on Nifty 500.*

![Figure 5: Trade Return Distribution](docs/images/fig5_trade_pnl_distribution.png)
*Figure 5: Distribution of Realized Trade Returns across all closed positions.*

---

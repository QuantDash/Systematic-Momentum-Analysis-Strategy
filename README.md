# Systematic Momentum Trading Strategy (NSE)

> **A quantitative momentum framework and empirical research study tailored for the Indian equity market.**

---

## Overview

This repository contains a modular systematic momentum strategy designed for Indian equities (National Stock Exchange). The engine is benchmarked against the **Nifty 500** universe and is fully adaptable to any stock basket (Nifty 50, Midcap 150, Smallcap 250, or custom watchlists).

The core strategy is a faithful replication of Andreas Clenow's textbook model (*Stocks on the Move*, 2015) deployed on the NSE Nifty 500 universe, with full empirical analysis of its structural failure modes in Indian market conditions.

---

## 📄 Research Paper

A full quantitative research paper documenting the empirical findings, parameter optimization, structural failure analysis, and capital scaling study is available here:

**[→ RESEARCH_ANALYSIS.md](RESEARCH_ANALYSIS.md)**

Key topics covered in the paper:
- Horizon decomposition and 200-day SMA warm-up accounting
- Full 3×3 grid-search optimization matrix ($W_m \in \{60, 90, 125\}$ days × $M_{\min} \in \{30, 40, 50\}$)
- Comparative performance table across ₹1L / ₹5L / ₹10L capital tiers vs. NIFTY 500 benchmark
- Four structural failure modes of the textbook model on Indian equities
- Integer share sizing friction and cash drag analysis

---

## Core Research Highlights

- **Lookback Optimization:** Empirical analysis demonstrating why a **90-day exponential regression slope** outperforms the textbook 125-day model on high-velocity Indian momentum cycles. The 90-day window captures the quarterly earnings acceleration phase without buying into parabolic exhaustion tops.
- **Regime Filter Latency:** Evaluation of the 200-day Simple Moving Average regime filter — the strategy correctly identifies macro downturns but suffers severe **V-shaped recovery lockout**, holding 80%–90% cash while the market stages double-digit relief rallies.
- **Integer Sizing Friction:** At ₹1 Lakh, `math.floor` truncation forces **53%–55% average idle cash drag**, excludes 150+ Nifty 500 stocks priced above ₹3,333, and shatters theoretical inverse-volatility risk parity. Capital ≥ ₹5 Lakhs is required for the model to operate as designed.
- **Indian Tax Wedge:** Full modeling of STT (0.10% buy + 0.10% sell), NSE turnover charges, stamp duty, and SEBI/GST fees — totaling **~30 bps round-trip friction** per trade, benchmarked against Clenow's US baseline of ~5 bps.
- **Rebalancing Dynamics:** Mitigating cash drag and excessive turnover friction typical of rigid monthly rebalancing schedules in Indian small/mid caps.

---


## Key Results (Textbook vs. Empirical vs. Benchmark)

| Model | Cumulative Return | Max Drawdown | Sharpe ($R_f = 6.5\%$) | Avg Cash Drag |
| :--- | :---: | :---: | :---: | :---: |
| Textbook Clenow (125d, ₹1L) | **-5.54%** | -10.81% | -1.02 | 55.5% |
| Empirical 90-Day (₹1L) | **+2.44%** | -8.57% | -0.50 | 53.9% |
| Empirical 90-Day (₹5L) | **+2.55%** | -9.08% | -0.44 | 45.6% |
| Empirical 90-Day (₹10L) | **+2.55%** | -9.51% | -0.47 | 43.7% |
| **NIFTY 500 Benchmark** | **+2.99%** | -14.82% | -0.33 | 0.0% |

*Evaluation window: February 2025 – October 2026 (Active trading: June 2025 – October 2026)*

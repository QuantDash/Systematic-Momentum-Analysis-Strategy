# Systematic Momentum Trading Strategy (NSE)

> **A quantitative momentum framework and empirical research study tailored for the Indian equity market.**

---

### Overview
This repository contains a modular systematic momentum strategy designed for Indian equities (National Stock Exchange). While the primary research and backtests are benchmarked against the **Nifty 500** universe, the engine is fully adaptable to any stock basket (Nifty 50, Midcap 150, Smallcap 250, or custom watchlists).

### Core Research Highlights
- **Lookback Optimization:** Empirical analysis demonstrating why a **90-day exponential regression slope** outperforms textbook 150-day models on high-volatility Indian momentum bursts.
- **Trend Filter & Entry Lag:** Evaluation of the 200-day Simple Moving Average (SMA) regime filter — assessing downside capital protection vs. entry lag in V-shaped market recoveries.
- **Rebalancing Dynamics:** Mitigating cash drag and excessive turnover friction typical of rigid monthly rebalancing schedules in Indian small/mid caps.
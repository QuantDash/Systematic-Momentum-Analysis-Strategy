import sys
from pathlib import Path

# Add parent directory (backtester/) and current directory to sys.path
CURRENT_DIR = Path(__file__).resolve().parent
PARENT_DIR = CURRENT_DIR.parent
for p in [str(PARENT_DIR), str(CURRENT_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

import pandas as pd
import numpy as np
from data_loader import get_historical_data, get_index_constituents, get_index_historical_data
from systematic_momentum_strategy import SystematicMomentumStrategy
from portfolio_simulator import PortfolioSimulator

def run_backtest():
    print("=== QUANTDASH BACKTEST ENGINE (INSTITUTIONAL MODE) ===\n")
    
    START_DATE = '2025-02-01'   
    END_DATE = '2026-10-20'
    INITIAL_CAPITAL = 100000.0 
    INDEX_SYMBOL = "NIFTY 500" 
    
    # QUANT STANDARD: Institutional Warm-Up Lookback Buffer (~250 trading days)
    WARMUP_BUFFER_DAYS = 365
    DATA_START_DATE = (pd.to_datetime(START_DATE) - pd.Timedelta(days=WARMUP_BUFFER_DAYS)).strftime('%Y-%m-%d')
    print(f"Trading Window : {START_DATE} to {END_DATE}")
    print(f"Warm-Up Window : {DATA_START_DATE} to {END_DATE}\n")
    
    # STEP 1: Fetch Point-in-Time Constituents (Defeating Survivorship Bias)
    print("[1/4] Fetching Point-In-Time Index Constituents...")
    df_constituents = get_index_constituents(INDEX_SYMBOL, start_date=DATA_START_DATE, end_date=END_DATE)
    
    if df_constituents.empty:
        print("CRITICAL ERROR: No constituent data found. Check your database tables.")
        return
        
    # The 'Super Universe' is every stock that ever spent a single day in the index during this period.
    super_universe = df_constituents.columns.tolist()
    print(f"      Found {len(super_universe)} unique stocks that existed in the index over the period.")
    
    # STEP 2: Fetch Data for the Super Universe
    print("\n[2/4] Fetching Historical Data for all constituents (with warm-up)...")
    price_data_list = []
    
    for symbol in super_universe:
        df = get_historical_data(symbol, start_date=DATA_START_DATE, end_date=END_DATE)
        if not df.empty:
            df['ticker'] = symbol
            df = df.reset_index().rename(columns={'trade_date': 'date'})
            price_data_list.append(df)
            
    df_prices = pd.concat(price_data_list, ignore_index=True)
    
    df_index_raw = get_index_historical_data(INDEX_SYMBOL, start_date=DATA_START_DATE, end_date=END_DATE)
    df_index = df_index_raw.reset_index().rename(columns={'trade_date': 'date'}) if not df_index_raw.empty else pd.DataFrame(columns=['date', 'close'])
        
    # STEP 3: Run Strategy (The Brain)
    print("\n[3/4] Executing Systematic Momentum Strategy...")
    strategy = SystematicMomentumStrategy(
        momentum_window=90, # 125
        vola_window=20, 
        index_window=200, # 200 
        min_momentum=40.0,  # 40
        portfolio_size=30
    )
    
    # We pass df_constituents for Point-In-Time rules and backtest_start_date for warm-up validation!
    df_target_weights = strategy.generate_weights(df_prices, df_index, df_constituents, backtest_start_date=START_DATE)
    
    # STEP 4: Run Simulator (The Broker)
    print("\n[4/4] Running Portfolio Simulation...")
    df_sim_prices = df_prices[df_prices['date'] >= START_DATE].copy()
    simulator = PortfolioSimulator(starting_capital=INITIAL_CAPITAL, friction_rate=0.0015)
    results_df = simulator.run(df_sim_prices, df_target_weights, df_index=df_index)
    
    # Attach detailed DataFrames to results for downstream export & visualization
    results_df.holdings_df = simulator.holdings_df
    results_df.trades_df = simulator.trades_df
    
    # Performance summary (Quantitative Finance Standards)
    if results_df is not None and not results_df.empty:
        val = results_df['portfolio_value']
        trading_val = val.iloc[1:]
        n_trading_days = len(trading_val)
        n_years = n_trading_days / 252.0
        
        # 1. Total & Annualized Returns (CAGR)
        tot_ret = (val.iloc[-1] / INITIAL_CAPITAL - 1) * 100
        cagr = (np.power(val.iloc[-1] / INITIAL_CAPITAL, 1.0 / n_years) - 1) * 100 if n_years > 0 else tot_ret
        
        # 2. Risk & Volatility
        daily_returns = results_df['daily_return'].iloc[1:]
        ann_vol = daily_returns.std() * np.sqrt(252) * 100
        
        # 3. Peak-to-Trough Drawdown
        peak = val.cummax()
        drawdown = (val - peak) / peak
        max_dd = drawdown.min() * 100
        
        # 4. Sharpe Ratio (Indian Standard Rf = 6.5% T-Bill yield)
        rf_rate = 6.5
        sharpe = (cagr - rf_rate) / ann_vol if ann_vol > 0 else 0.0
        
        # 5. Benchmark Performance (Properly Aligned to Strategy Horizon)
        bench_ret, bench_cagr, bench_vol, bench_sharpe = None, None, None, None
        if 'benchmark_close' in results_df.columns:
            bench_series = results_df['benchmark_close'].dropna()
            if not bench_series.empty:
                bench_start = bench_series.iloc[0]
                bench_end = bench_series.iloc[-1]
                bench_ret = (bench_end / bench_start - 1) * 100
                bench_cagr = (np.power(bench_end / bench_start, 1.0 / n_years) - 1) * 100 if n_years > 0 else bench_ret
                
                bench_daily = bench_series.pct_change().dropna()
                bench_vol = bench_daily.std() * np.sqrt(252) * 100 if len(bench_daily) > 1 else 0.0
                bench_sharpe = (bench_cagr - rf_rate) / bench_vol if bench_vol > 0 else 0.0
            
        # 6. Trade Execution Performance (Quant Standard: Separate Completed Exits from Rebalance Trims)
        trades = simulator.trades_df
        total_records = len(trades)
        total_realized_pnl = trades['realized_pnl'].sum() if total_records > 0 else 0.0
        
        # Completed Exits (full round-trip closed positions)
        exits = trades[trades['action'] == 'EXIT'] if total_records > 0 else pd.DataFrame()
        total_exits = len(exits)
        exit_wins = exits[exits['realized_pnl'] > 0] if total_exits > 0 else pd.DataFrame()
        exit_losses = exits[exits['realized_pnl'] < 0] if total_exits > 0 else pd.DataFrame()
        exit_win_rate = (len(exit_wins) / total_exits * 100) if total_exits > 0 else 0.0
        exit_avg_win = exit_wins['pnl_pct'].mean() if not exit_wins.empty else 0.0
        exit_avg_loss = exit_losses['pnl_pct'].mean() if not exit_losses.empty else 0.0
        exit_gross_win = exit_wins['realized_pnl'].sum() if not exit_wins.empty else 0.0
        exit_gross_loss = abs(exit_losses['realized_pnl'].sum()) if not exit_losses.empty else 0.0
        exit_profit_factor = (exit_gross_win / exit_gross_loss) if exit_gross_loss > 0 else (exit_gross_win if exit_gross_win > 0 else 0.0)
        
        # Rebalance Trims & Buy Orders
        total_trims = len(trades[trades['action'] == 'TRIM']) if total_records > 0 else 0
        total_buys = len(trades[trades['action'] == 'BUY']) if total_records > 0 else 0
            
        print("\n========================================================")
        print("     QUANTSUMMARY: SYSTEMATIC MOMENTUM (BOOK STRATEGY)  ")
        print("========================================================")
        print(f"Backtest Duration   : {n_trading_days} Trading Days ({n_years:.2f} Years)")
        print(f"Initial Capital     : Rs. {INITIAL_CAPITAL:,.2f}")  
        print(f"Final Portfolio     : Rs. {val.iloc[-1]:,.2f}")
        print(f"Net Realized PnL    : Rs. {total_realized_pnl:+,.2f}")
        print("--------------------------------------------------------")
        print(f"Strategy Return     : {tot_ret:+.2f}% (Cumulative)")
        print(f"Strategy CAGR       : {cagr:+.2f}% (Annualized)")
        if bench_ret is not None:
            print(f"NIFTY 500 Return    : {bench_ret:+.2f}% (Cumulative)")
            print(f"NIFTY 500 CAGR      : {bench_cagr:+.2f}% (Annualized)")
            print(f"Alpha (Cumulative)  : {(tot_ret - bench_ret):+.2f}%")
            print(f"Alpha (Annualized)  : {(cagr - bench_cagr):+.2f}%")
        print("--------------------------------------------------------")
        if bench_vol is not None and bench_sharpe is not None:
            print(f"Annualized Volatility: {ann_vol:.2f}%  |  NIFTY 500: {bench_vol:.2f}%")
            print(f"Max Drawdown        : {max_dd:.2f}%")
            print(f"Sharpe Ratio (Rf=6.5%): {sharpe:.2f}  |  NIFTY 500: {bench_sharpe:.2f}")
        else:
            print(f"Annualized Volatility: {ann_vol:.2f}%")
            print(f"Max Drawdown        : {max_dd:.2f}%")
            print(f"Sharpe Ratio (Rf=6.5%): {sharpe:.2f}")
        print("----------------- TRADE EXECUTION STATS ----------------")
        print(f"Total Completed Exits: {total_exits} (Plus {total_trims} Rebalance Trims | {total_buys} Buys)")
        print(f"Exit Win Rate        : {exit_win_rate:.1f}% ({len(exit_wins)} Wins / {len(exit_losses)} Losses)")
        print(f"Average Win (Exits)  : {exit_avg_win:+.2f}%")
        print(f"Average Loss (Exits) : {exit_avg_loss:+.2f}%")
        print(f"Exit Profit Factor   : {exit_profit_factor:.2f}")
        print("========================================================\n")
        
    return results_df
    
if __name__ == "__main__":
    results = run_backtest()
    if results is not None and not results.empty:
        # 1. Daily Summary (Equity curve, cash, invested, benchmark)
        output_csv = CURRENT_DIR / "result_df.csv"
        results.to_csv(output_csv)
        print(f"Detailed daily results saved to : {output_csv}")
        
        # 2. Daily Holdings (Every stock held each day, shares, Rupee value, weight %)
        holdings_df = getattr(results, 'holdings_df', pd.DataFrame())
        if not holdings_df.empty:
            holdings_csv = CURRENT_DIR / "result_daily_holdings.csv"
            holdings_df.to_csv(holdings_csv, index=False)
            print(f"Daily stock holdings saved to   : {holdings_csv}")
            
        # 3. Trade Ledger (Every trade buy/sell, execution prices, PnL, holding days, exit reason)
        trades_df = getattr(results, 'trades_df', pd.DataFrame())
        if not trades_df.empty:
            trades_csv = CURRENT_DIR / "result_trade_log.csv"
            trades_df.to_csv(trades_csv, index=False)
            print(f"Executed trade ledger saved to  : {trades_csv}")

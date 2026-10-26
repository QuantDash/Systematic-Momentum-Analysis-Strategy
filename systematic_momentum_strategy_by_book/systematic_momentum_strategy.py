import pandas as pd
import numpy as np
from scipy import stats

class SystematicMomentumStrategy:
    def __init__(self, momentum_window=125, vola_window=20, index_window=200, 
                 min_momentum=40.0, portfolio_size=30, max_weight=0.15):
        self.momentum_window = momentum_window
        self.vola_window = vola_window
        self.index_window = index_window
        self.min_momentum = min_momentum
        self.portfolio_size = portfolio_size
        self.max_weight = max_weight

    def _calc_momentum(self, ts):
        ts = ts.dropna()
        if len(ts) < self.momentum_window: 
            return np.nan
            
        y = np.log(ts.values)
        x = np.arange(len(y))
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
        annualized_slope = (np.power(np.exp(slope), 252) - 1) * 100
        score = annualized_slope * (r_value ** 2)
        return score

    def _calc_volatility(self, ts):
        ts = ts.dropna()
        if len(ts) < 2: 
            return np.nan
        return ts.pct_change().std()

    def generate_weights(self, df_prices, df_index, df_constituents=None, backtest_start_date=None):
        print("Calculating Systematic Momentum Weights (Point-In-Time & Cash Scaled with Warm-up Validation)...")
        
        df_pivot = df_prices.pivot(index='date', columns='ticker', values='close').sort_index()
        df_pivot = df_pivot.ffill() # QUANT FIX: Forward-fill stock prices
        
        df_index = df_index.set_index('date').sort_index()
        df_index = df_index.ffill() # QUANT FIX: Forward-fill the market index
        df_index['sma_200'] = df_index['close'].rolling(window=self.index_window).mean()
        
        all_trading_days = df_pivot.index.tolist()
        
        # QUANT STANDARD: Warm-Up History Validation
        required_warmup = max(self.index_window, self.momentum_window)
        if backtest_start_date is not None:
            b_start = pd.to_datetime(backtest_start_date)
            prior_days = [d for d in all_trading_days if d < b_start]
            if len(prior_days) < required_warmup:
                earliest_valid = all_trading_days[min(required_warmup, len(all_trading_days) - 1)]
                print(f"[WARNING] Insufficient warm-up history before requested start date {backtest_start_date}!")
                print(f"    Available prior days: {len(prior_days)} | Required: {required_warmup} trading days.")
                print(f"    -> Automatically adjusting active trading start date to: {pd.to_datetime(earliest_valid).strftime('%Y-%m-%d')}")
                active_start = pd.to_datetime(earliest_valid)
            else:
                print(f"[OK] Sufficient warm-up history available ({len(prior_days)} days >= {required_warmup} required). Ready from Day 1!")
                active_start = b_start
        else:
            active_start = all_trading_days[0]
        
        df_pivot['year_month'] = df_pivot.index.to_period('M')
        rebalance_dates = df_pivot.groupby('year_month').apply(lambda x: x.index[-1]).values
        df_pivot = df_pivot.drop(columns=['year_month'])
        
        target_weights_list = []
        held_positions = [] 
        
        for date in rebalance_dates:
            current_idx = all_trading_days.index(date)
            if current_idx + 1 >= len(all_trading_days):
                continue
            next_day = all_trading_days[current_idx + 1]
            
            # Skip rebalances whose execution date falls before active trading start
            if next_day < active_start:
                continue
                
            if current_idx < self.momentum_window:
                continue
                
            try:
                idx_close = df_index.loc[date, 'close']
                idx_sma = df_index.loc[date, 'sma_200']
                red_light = bool(idx_close < idx_sma) if not np.isnan(idx_sma) else True
            except KeyError:
                red_light = True
                
            hist_mom = df_pivot.iloc[current_idx - self.momentum_window + 1 : current_idx + 1]
            hist_vol = df_pivot.iloc[current_idx - self.vola_window + 1 : current_idx + 1]
            
            # 1. Rank ALL stocks regardless of score
            mom_scores = hist_mom.apply(self._calc_momentum)
            ranked_all = mom_scores.sort_values(ascending=False)
            
            # POINT-IN-TIME FILTER: What stocks were legally in the index ON THIS EXACT DATE?
            todays_universe = ranked_all.index.tolist() # Fallback
            if df_constituents is not None and not df_constituents.empty:
                # Use ffill on constituents in case rebalance date lands on a weekend/holiday
                df_const_ffilled = df_constituents.ffill()
                if date in df_const_ffilled.index:
                    todays_row = df_const_ffilled.loc[date]
                    # Extract only stocks that are strictly True (active in index) on this day
                    todays_universe = todays_row[todays_row == True].index.tolist()
                else:
                    todays_universe = []
            
            # 2. Sell Logic (Keep existing stocks ONLY if score >= 40 AND they didn't get kicked out of the index)
            kept_positions = [
                t for t in held_positions 
                if t in ranked_all.index 
                and ranked_all[t] >= self.min_momentum 
                and t in todays_universe # SURVIVORSHIP BIAS KILLER
            ]
            
            # 3. Draft Replacements (Always grab enough to fill buckets, drafting ONLY from today's index)
            replacement_count = self.portfolio_size - len(kept_positions)
            # Filter candidates so we don't accidentally buy a stock that isn't currently in the Nifty 50
            candidates = ranked_all[ranked_all.index.isin(todays_universe) & ~ranked_all.index.isin(kept_positions)]
            buy_list = candidates.head(replacement_count).index.tolist()
            
            # Helper to determine why a held position was liquidated
            def get_liquidation_reason(t):
                if t not in todays_universe:
                    return "Constituent Removed from Index"
                elif t in ranked_all.index and ranked_all[t] < self.min_momentum:
                    return f"Momentum Score < {self.min_momentum} (Score: {ranked_all[t]:.1f})"
                else:
                    return "Disqualified (Below Filter Threshold)"

            # 4. Create the 30-bucket Roster
            roster = kept_positions + buy_list
            
            if len(roster) == 0:
                if current_idx + 1 < len(all_trading_days):
                    next_day = all_trading_days[current_idx + 1]
                    for ticker in held_positions:
                        reason = get_liquidation_reason(ticker)
                        target_weights_list.append({'date': next_day, 'ticker': ticker, 'target_weight': 0.0, 'reason': reason})
                held_positions = []
                continue
                
            # 5. The Budget (Calculate Inverse Volatility for all 30 buckets)
            roster_vol = hist_vol[roster].apply(self._calc_volatility)
            roster_vol = roster_vol.replace(0, np.nan).dropna()
            
            if len(roster_vol) == 0:
                if current_idx + 1 < len(all_trading_days):
                    next_day = all_trading_days[current_idx + 1]
                    for ticker in held_positions:
                        reason = get_liquidation_reason(ticker)
                        target_weights_list.append({'date': next_day, 'ticker': ticker, 'target_weight': 0.0, 'reason': reason})
                held_positions = []
                continue
                
            inv_vol = 1.0 / roster_vol
            raw_weights = inv_vol / inv_vol.sum()
            
            # QUANT STANDARD: Apply Single-Stock Position Cap (15% maximum weight)
            weights = raw_weights.clip(upper=self.max_weight)
            
            # 6. The Execution Filter (The Cash Scaling Trick!)
            actual_holdings = []
            if current_idx + 1 < len(all_trading_days):
                next_day = all_trading_days[current_idx + 1]
                
                for ticker, weight in weights.items():
                    if ticker in kept_positions:
                        target_weights_list.append({'date': next_day, 'ticker': ticker, 'target_weight': weight, 'reason': 'Hold / Rebalance'})
                        actual_holdings.append(ticker)
                    else:
                        if red_light:
                            pass # Market crash, weight turns into cash
                        elif ranked_all.get(ticker, 0) < self.min_momentum:
                            pass # Stock sucks, weight turns into cash
                        else:
                            target_weights_list.append({'date': next_day, 'ticker': ticker, 'target_weight': weight, 'reason': 'New Buy (Top Momentum)'})
                            actual_holdings.append(ticker)
                            
                # QUANT STANDARD (Bug D Fix): Explicitly emit target_weight = 0.0 for any position being liquidated
                for ticker in held_positions:
                    if ticker not in actual_holdings:
                        reason = get_liquidation_reason(ticker)
                        target_weights_list.append({'date': next_day, 'ticker': ticker, 'target_weight': 0.0, 'reason': reason})
                            
            held_positions = actual_holdings
            
        df_target_weights = pd.DataFrame(target_weights_list)
        print(f"Strategy complete. Generated {len(df_target_weights)} weight targets.")
        return df_target_weights

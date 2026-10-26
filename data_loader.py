import pandas as pd
import mysql.connector
import warnings
from mysql.connector import Error
from dotenv import load_dotenv
import os
load_dotenv()

# Suppress the pandas SQL warning (pandas prefers SQLAlchemy, but mysql.connector is fine for our use case)
warnings.filterwarnings('ignore', category=UserWarning)

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''), 
    'database': os.getenv('DB_NAME', 'nse_historical_vault_v2')
}
def get_historical_data(symbol, start_date=None, end_date=None):
    """
    Fetches adjusted OHLCV data for a given symbol from the MySQL vault.
    Returns a Pandas DataFrame strictly formatted for quantitative analysis.
    """
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        
        # We only select the ADJUSTED columns. Never use raw prices for backtesting.
        query = """
            SELECT 
                dp.trade_date,
                dp.adjusted_open AS open,
                dp.adjusted_high AS high,
                dp.adjusted_low AS low,
                dp.adjusted_close AS close,
                dp.adjusted_volume AS volume
            FROM daily_prices dp
            JOIN symbols s ON dp.stock_id = s.stock_id
            WHERE s.symbol = %s
        """
        # 
        params = [symbol]

        # Add date filters if provided
        if start_date:
            query += " AND dp.trade_date >= %s"
            params.append(start_date)
        if end_date:
            query += " AND dp.trade_date <= %s"
            params.append(end_date)
            
        # QUANT STANDARD: Always order ASC chronologically at the SQL level.
        # If your data is backwards, your backtest will buy the future and sell the past.
        query += " ORDER BY dp.trade_date ASC"

        # Load directly into Pandas
        df = pd.read_sql(query, conn, params=tuple(params))
        
        if df.empty:
            print(f"Warning: No data found for {symbol} in the given date range.")
            return df
            
        # --- QUANTITATIVE OPTIMIZATIONS ---
        
        # 1. Time-Series Alignment: Set the trade_date as the Pandas DatetimeIndex
        # This allows us to easily merge different stocks later based on the exact same dates.
        df['trade_date'] = pd.to_datetime(df['trade_date'])
        df.set_index('trade_date', inplace=True)
        
        # 2. Vectorization Speed: Cast SQL Decimals to Float64
        # MySQL returns DECIMAL(10,2) as a Python `decimal.Decimal` object. 
        # Pandas processes `decimal.Decimal` 100x slower than standard `float64` because it cannot use C-level NumPy math.
        # We strictly convert these to floats to ensure our simulator runs in seconds, not hours.
        float_cols = ['open', 'high', 'low', 'close']
        df[float_cols] = df[float_cols].astype(float)
        
        # Volume should always be integer
        df['volume'] = df['volume'].astype(int)
        
        return df
        
    except Error as e:
        print(f"Database error: {e}")
        return pd.DataFrame()
    finally:
        if 'conn' in locals() and conn.is_connected():
            conn.close()

def get_index_historical_data(index_name, start_date=None, end_date=None):
    """
    Fetches adjusted price data for an index from the MySQL vault.
    """
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        query = """
            SELECT 
                trade_date,
                open_price AS open,
                high_price AS high,
                low_price AS low,
                close_price AS close,
                volume
            FROM index_prices
            WHERE index_name = %s
        """
        params = [index_name]

        if start_date:
            query += " AND trade_date >= %s"
            params.append(start_date)
        if end_date:
            query += " AND trade_date <= %s"
            params.append(end_date)
            
        query += " ORDER BY trade_date ASC"

        df = pd.read_sql(query, conn, params=tuple(params))
        
        if df.empty:
            print(f"Warning: No data found for index {index_name} in the given date range.")
            return df
            
        df['trade_date'] = pd.to_datetime(df['trade_date'])
        df.set_index('trade_date', inplace=True)
        
        float_cols = ['open', 'high', 'low', 'close']
        df[float_cols] = df[float_cols].astype(float)
        df['volume'] = df['volume'].fillna(0).astype(int)
        
        return df
        
    except Error as e:
        print(f"Database error: {e}")
        return pd.DataFrame()
    finally:
        if 'conn' in locals() and conn.is_connected():
            conn.close()

def get_index_constituents(index_symbol, start_date=None, end_date=None):
    """
    Fetches Point-in-Time index constituents to prevent Survivorship Bias.
    Returns a boolean DataFrame (Index = Date, Columns = Symbols).
    """
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        
        query = """
            SELECT symbol, valid_from, valid_till 
            FROM index_constituents 
            WHERE index_name = %s
        """
        df_intervals = pd.read_sql(query, conn, params=(index_symbol,))
        
        if df_intervals.empty:
            print(f"Warning: No constituent data found for {index_symbol}.")
            return pd.DataFrame()
            
        df_intervals['valid_from'] = pd.to_datetime(df_intervals['valid_from'])
        df_intervals['valid_till'] = pd.to_datetime(df_intervals['valid_till'])
        
        max_date = pd.to_datetime(end_date) if end_date else pd.to_datetime('today')
        df_intervals['valid_till'] = df_intervals['valid_till'].fillna(max_date)
        
        min_date = pd.to_datetime(start_date) if start_date else df_intervals['valid_from'].min()
        dates = pd.date_range(start=min_date, end=max_date, freq='D')
        
        symbols = df_intervals['symbol'].unique()
        df_mask = pd.DataFrame(False, index=dates, columns=symbols)
        
        for _, row in df_intervals.iterrows():
            sym = row['symbol']
            s_date = max(row['valid_from'], min_date)
            e_date = min(row['valid_till'], max_date)
            if s_date <= e_date:
                df_mask.loc[s_date:e_date, sym] = True
                
        return df_mask
        
    except Error as e:
        print(f"Database error in get_index_constituents: {e}")
        return pd.DataFrame()
    finally:
        if 'conn' in locals() and conn.is_connected():
            conn.close()

if __name__ == "__main__":
    # --- QUICK TEST ---
    print("Testing Quant Data Loader...")
    
    # Try fetching a known stock from your database (e.g., RELIANCE or INFY)
    test_symbol = "RELIANCE" 
    
    df = get_historical_data(test_symbol)
    
    if not df.empty:
        print(f"\nSuccessfully loaded {len(df)} days of data for {test_symbol}!")
        print("\n--- Data Head ---")
        print(df.head())
        print("\n--- Data Types (Notice they are float64 for speed!) ---")
        print(df.dtypes)
    else:
        print(f"Failed to load {test_symbol}. Make sure the symbol exists in your 'symbols' table.")

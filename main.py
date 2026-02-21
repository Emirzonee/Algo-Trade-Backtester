import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go

# ------------------------------------------------------------------
# Strategy parameters — adjust here without touching the logic below
# ------------------------------------------------------------------

SYMBOL = "AKFYE"
START_DATE = "2023-01-01"
INITIAL_CAPITAL = 10_000  # TL

# Entry & exit tolerances
BUY_TOLERANCE = 1.0033    # Price must be 0.33% above EMA-50 to trigger entry
STOP_TOLERANCE = 0.988    # Price 1.2% below EMA-50 triggers trend-end exit

# Indicator periods
EMA_PERIOD = 50
VOL_SMA_PERIOD = 20
BB_PERIOD = 20
BB_STD = 2
ST_LENGTH = 10
ST_MULTIPLIER = 3

# Candle analysis
WICK_BODY_RATIO = 2.5     # Upper wick / body ratio that signals exhaustion
BB_PROXIMITY = 0.98       # Price within 2% of Bollinger upper band = "at peak"
BODY_RATIO_THRESHOLD = 0.347  # Minimum body/total ratio for "strong red" candle


# ------------------------------------------------------------------
# Data fetching
# ------------------------------------------------------------------

def fetch_data(symbol: str, start_date: str) -> pd.DataFrame:
    """
    Downloads OHLCV data from Yahoo Finance for a BIST ticker.

    Automatically appends '.IS' suffix if not already present.

    Args:
        symbol:     Ticker symbol (e.g. 'AKFYE').
        start_date: Start date string in 'YYYY-MM-DD' format.

    Returns:
        DataFrame with OHLCV columns, NaN rows dropped.
    """
    print(f"[*] Downloading data: {symbol}...")
    if not symbol.endswith(".IS"):
        symbol = f"{symbol}.IS"

    df = yf.download(symbol, start=start_date, progress=False)

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df.dropna(inplace=True)
    return df


# ------------------------------------------------------------------
# Indicator calculation
# ------------------------------------------------------------------

def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds all technical indicators required by the strategy.

    Indicators added:
      - EMA-50 and its slope (direction filter)
      - 20-day volume SMA (volume confirmation)
      - Bollinger upper band (overbought filter)
      - SuperTrend direction and line (trend confirmation)
      - Candle body analysis for exhaustion detection

    Args:
        df: Raw OHLCV DataFrame.

    Returns:
        DataFrame with indicator columns appended.
    """
    # EMA-50 and slope
    df['EMA_50'] = ta.ema(df['Close'], length=EMA_PERIOD)
    df['EMA_Slope'] = df['EMA_50'].diff()

    # Volume confirmation
    df['Vol_SMA_20'] = ta.sma(df['Volume'], length=VOL_SMA_PERIOD)

    # Bollinger upper band
    bbands = ta.bbands(df['Close'], length=BB_PERIOD, std=BB_STD)
    upper_col = [col for col in bbands.columns if col.startswith("BBU")][0]
    df['BB_Upper'] = bbands[upper_col]

    # SuperTrend direction and line
    st_df = ta.supertrend(df['High'], df['Low'], df['Close'], length=ST_LENGTH, multiplier=ST_MULTIPLIER)
    trend_col = [col for col in st_df.columns if col.startswith("SUPERTd")][0]
    line_col = [col for col in st_df.columns if col.startswith("SUPERT_")][0]
    df['ST_Trend'] = st_df[trend_col]
    df['ST_Line'] = st_df[line_col]
    df['ST_Slope'] = df['ST_Line'].diff().abs()

    # Candle body analysis
    df['Is_Red'] = df['Close'] < df['Open']
    df['Body_Size'] = (df['Close'] - df['Open']).abs()
    df['Total_Size'] = (df['High'] - df['Low']).abs()
    df['Mid_Strong_Red'] = df['Is_Red'] & (df['Body_Size'] > (df['Total_Size'] * BODY_RATIO_THRESHOLD))

    return df


# ------------------------------------------------------------------
# Backtesting engine
# ------------------------------------------------------------------

def backtest(df: pd.DataFrame, initial_capital: float = INITIAL_CAPITAL) -> tuple:
    """
    Runs the SNIPER v8.39 strategy on historical data.

    Entry conditions (all must be true):
      - Price >= EMA-50 * BUY_TOLERANCE  (breakout above EMA with buffer)
      - EMA slope is positive            (uptrend confirmed)
      - Volume > 20-day average          (money flow confirmation)
      - SuperTrend is bullish and not flattening near Bollinger upper band

    Exit conditions (first match triggers exit):
      1. Price drops below EMA-50 * STOP_TOLERANCE or SuperTrend turns bearish
      2. Long upper wick near Bollinger upper band (exhaustion signal)
      3. 4 consecutive strong red candles (body > 34.7% of total range)
      4. 5 consecutive red candles (unconditional momentum loss exit)

    Args:
        df:              DataFrame with indicators already applied.
        initial_capital: Starting capital in TL.

    Returns:
        Tuple of (final_capital: float, trades: list of dicts).
    """
    capital = initial_capital
    position = 0.0
    entry_price = 0.0
    penalty_mode = False
    trades = []

    print(f"\n[*] SNIPER v8.39 starting | Capital: {initial_capital:.0f} TL")
    print("-" * 120)

    for i in range(EMA_PERIOD + 1, len(df)):
        price     = df['Close'].iloc[i]
        open_p    = df['Open'].iloc[i]
        high_p    = df['High'].iloc[i]
        low_p     = df['Low'].iloc[i]
        vol_now   = df['Volume'].iloc[i]
        vol_avg   = df['Vol_SMA_20'].iloc[i]
        bb_upper  = df['BB_Upper'].iloc[i]
        st_trend  = df['ST_Trend'].iloc[i]
        st_slope  = df['ST_Slope'].iloc[i]
        ema_50    = df['EMA_50'].iloc[i]
        ema_slope = df['EMA_Slope'].iloc[i]
        date      = df.index[i]

        body      = abs(price - open_p)
        upper_wick = high_p - max(price, open_p)
        weak_candle  = upper_wick > (body if body > 0 else 0.01) * WICK_BODY_RATIO
        price_at_top = price > bb_upper * BB_PROXIMITY
        strong_candle = (price > open_p) and (body > (high_p - low_p) * 0.5)

        # Exit pattern detection
        four_mid_red = all(df['Mid_Strong_Red'].iloc[i-3:i+1]) if i >= 3 else False
        five_any_red = all(df['Is_Red'].iloc[i-4:i+1]) if i >= 4 else False

        # Entry conditions
        st_flat       = st_slope < 0.01
        st_confirmed  = (st_trend == 1) and not (st_flat and price_at_top)
        king_criteria = (price >= ema_50 * BUY_TOLERANCE) and (ema_slope > 0) and (vol_now > vol_avg)

        # --- BUY ---
        if position == 0:
            if king_criteria and st_confirmed:
                if penalty_mode and not strong_candle:
                    continue
                position = capital / price
                entry_price = price
                capital = 0.0
                penalty_mode = False
                trades.append({'Date': date, 'Type': 'BUY', 'Price': price})
                print(f"{date.strftime('%Y-%m-%d'):<12} | BUY  | {price:<10.2f} | Breakout confirmed (tolerance {BUY_TOLERANCE})")

        # --- SELL ---
        elif position > 0:
            sell_reason = None

            if price < (ema_50 * STOP_TOLERANCE) or st_trend == -1:
                sell_reason = "Trend ended (EMA/ST)"
                penalty_mode = False
            elif weak_candle and price_at_top:
                sell_reason = "Peak wick exhaustion"
                penalty_mode = True
            elif four_mid_red:
                sell_reason = f"Precision exit (4 candles >{BODY_RATIO_THRESHOLD*100:.1f}%)"
                penalty_mode = True
            elif five_any_red:
                sell_reason = "Hard exit (5 red candles)"
                penalty_mode = True

            if sell_reason:
                capital = position * price
                result = "+" if price > entry_price else "-"
                trades.append({'Date': date, 'Type': 'SELL', 'Price': price})
                print(f"{date.strftime('%Y-%m-%d'):<12} | SELL | {price:<10.2f} | {sell_reason:<45} | {capital:.2f} TL {result}")
                position = 0.0

    if position > 0:
        capital = position * df['Close'].iloc[-1]

    return capital, trades


# ------------------------------------------------------------------
# Visualization
# ------------------------------------------------------------------

def plot_results(df: pd.DataFrame, trades: list) -> None:
    """
    Renders an interactive candlestick chart with indicators and trade markers.

    Args:
        df:     DataFrame with OHLCV and indicator columns.
        trades: List of trade dicts produced by backtest().
    """
    fig = go.Figure()

    fig.add_trace(go.Candlestick(
        x=df.index, open=df['Open'], high=df['High'],
        low=df['Low'], close=df['Close'], name='Price'
    ))
    fig.add_trace(go.Scatter(x=df.index, y=df['EMA_50'],
        line=dict(color='orange', width=2), name='EMA 50'))
    fig.add_trace(go.Scatter(x=df.index, y=df['BB_Upper'],
        line=dict(color='gray', width=1, dash='dot'), name='Bollinger Upper'))
    fig.add_trace(go.Scatter(x=df.index, y=df['ST_Line'],
        line=dict(color='blue', width=1), name='SuperTrend'))

    buy_dates   = [t['Date'] for t in trades if t['Type'] == 'BUY']
    buy_prices  = [t['Price'] for t in trades if t['Type'] == 'BUY']
    sell_dates  = [t['Date'] for t in trades if t['Type'] == 'SELL']
    sell_prices = [t['Price'] for t in trades if t['Type'] == 'SELL']

    fig.add_trace(go.Scatter(x=buy_dates, y=buy_prices, mode='markers',
        marker=dict(symbol='triangle-up', color='lime', size=15), name='BUY'))
    fig.add_trace(go.Scatter(x=sell_dates, y=sell_prices, mode='markers',
        marker=dict(symbol='triangle-down', color='red', size=15), name='SELL'))

    fig.update_layout(
        title=f"SNIPER v8.39 — {SYMBOL} Backtest Results",
        height=800,
        xaxis_rangeslider_visible=False,
    )
    fig.show()


# ------------------------------------------------------------------
# Entry point
# ------------------------------------------------------------------

if __name__ == "__main__":
    df = fetch_data(SYMBOL, START_DATE)
    df = add_indicators(df)
    final_capital, trade_history = backtest(df, INITIAL_CAPITAL)

    roi = ((final_capital - INITIAL_CAPITAL) / INITIAL_CAPITAL) * 100
    print(f"\nResult: {INITIAL_CAPITAL:,.0f} TL -> {final_capital:,.2f} TL ({roi:+.1f}%)")

    plot_results(df, trade_history)
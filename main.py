import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def fetch_data(symbol, start_date):
    print(f"[*] Veri indiriliyor: {symbol}...")
    if not symbol.endswith(".IS"):
        symbol = f"{symbol}.IS"
    df = yf.download(symbol, start=start_date, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.dropna(inplace=True)
    return df

def add_advanced_indicators(df):
    """
    AL: HMA 20 + Hacim MA 20 (%20+) + SuperTrend + RSI
    SAT: Bollinger Üst Bant Dönüşü + SMI Sat + HMA 20 Altı Kapanış
    """
    # 1. Hull Moving Average (HMA 20)
    df['HMA_20'] = ta.hma(df['Close'], length=20)
    
    # 2. Hacim Filtresi (Volume MA 20)
    df['VOL_MA_20'] = ta.sma(df['Volume'], length=20)
    
    # 3. SuperTrend (10, 3)
    st = ta.supertrend(df['High'], df['Low'], df['Close'], length=10, multiplier=3)
    df['ST_VAL'] = st.iloc[:, 0]
    df['ST_DIR'] = st.iloc[:, 1] # 1: Buy, -1: Sell
    
    # 4. RSI (14)
    df['RSI'] = ta.rsi(df['Close'], length=14)
    
    # 5. Bollinger Bantları (20, 2)
    bb = ta.bbands(df['Close'], length=20, std=2)
    df['BB_UPPER'] = bb.iloc[:, 2] # Üst Bant
    
    # 6. SMI (Stochastic Momentum Index) - 13, 25, 2
    smi = ta.smi(df['Close'], fast=13, slow=25, signal=2)
    df['SMI'] = smi.iloc[:, 0]
    df['SMI_SIGNAL'] = smi.iloc[:, 1]
    
    return df

def backtest_advanced(df, initial_capital=10000):
    capital = initial_capital
    position = 0 
    trades = []
    entry_price = 0

    print(f"\n[*] SNIPER v5.0 (Hacim & SMI Odaklı) Başlıyor... Kasa: {initial_capital} TL")
    print("-" * 130)
    print(f"{'TARİH':<12} | {'İŞLEM':<10} | {'FİYAT':<10} | {'NEDEN (Detay)':<65} | {'BAKİYE'}")
    print("-" * 130)

    for i in range(25, len(df)):
        price = df['Close'].iloc[i]
        date = df.index[i]
        
        # Gösterge Değerleri
        hma = df['HMA_20'].iloc[i]
        vol = df['Volume'].iloc[i]
        vol_ma = df['VOL_MA_20'].iloc[i]
        st_dir = df['ST_DIR'].iloc[i]
        rsi = df['RSI'].iloc[i]
        bb_upper = df['BB_UPPER'].iloc[i]
        smi = df['SMI'].iloc[i]
        smi_sig = df['SMI_SIGNAL'].iloc[i]
        smi_prev = df['SMI'].iloc[i-1]
        smi_sig_prev = df['SMI_SIGNAL'].iloc[i-1]

        # --- 🟢 ALIM MANTIĞI ---
        # 1. Fiyat > HMA 20
        # 2. Hacim > Ortalama Hacim * 1.2 (%20 artış)
        # 3. SuperTrend = Yeşil (1)
        # 4. RSI > 45
        buy_condition = (price > hma) and (vol > vol_ma * 1.2) and (st_dir == 1) and (rsi > 45)

        # --- 🔴 SATIŞ MANTIĞI ---
        should_sell = False
        sell_reason = ""

        if position > 0:
            # 1. Bollinger Üst Banttan Dönüş (Önceki gün değmiş/üstündeymiş, bugün altında)
            if (df['High'].iloc[i-1] >= df['BB_UPPER'].iloc[i-1]) and (price < df['BB_UPPER'].iloc[i]):
                should_sell = True
                sell_reason = "Bollinger Üst Banttan Dönüş (Yorgunluk)"
            
            # 2. SMI Sat Sinyali (+40 üstünde aşağı kesişim)
            elif (smi_prev > 40) and (smi_prev > smi_sig_prev) and (smi < smi_sig):
                should_sell = True
                sell_reason = "SMI Sat (+40 Üstü Kesişim)"
            
            # 3. Fiyat HMA 20 Altına İndi
            elif price < hma:
                should_sell = True
                sell_reason = "Trend Kırılımı (Fiyat < HMA 20)"

            if should_sell:
                revenue = position * price
                profit = revenue - (position * entry_price)
                capital = revenue
                trades.append({'Date': date, 'Type': 'SELL', 'Price': price})
                durum = "✅" if profit > 0 else "🔻"
                print(f"{date.strftime('%Y-%m-%d'):<12} | 🔴 SAT       | {price:<10.2f} | {sell_reason:<65} | {capital:.2f} TL {durum}")
                position = 0

        # POZİSYON AÇMA
        elif position == 0 and buy_condition:
            position = capital / price
            entry_price = price
            capital = 0 
            trades.append({'Date': date, 'Type': 'BUY', 'Price': price})
            print(f"{date.strftime('%Y-%m-%d'):<12} | 🟢 AL       | {price:<10.2f} | Hacim Patlaması + HMA + SuperTrend                      | Yatırıldı")

    return capital, trades

def plot_advanced(df, trades):
    fig = make_subplots(rows=4, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.02, row_heights=[0.5, 0.15, 0.15, 0.2],
                        subplot_titles=('Fiyat, BB & HMA', 'Hacim vs Ortalama', 'SMI Momentum', 'RSI'))

    # PANEL 1: FİYAT + BB + HMA
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='Fiyat'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['BB_UPPER'], line=dict(color='gray', dash='dash'), name='Bollinger Üst'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['HMA_20'], line=dict(color='blue', width=2), name='HMA 20'), row=1, col=1)
    
    # Sinyaller
    buy_dates = [t['Date'] for t in trades if t['Type'] == 'BUY']
    buy_prices = [t['Price'] for t in trades if t['Type'] == 'BUY']
    sell_dates = [t['Date'] for t in trades if t['Type'] == 'SELL']
    sell_prices = [t['Price'] for t in trades if t['Type'] == 'SELL']
    fig.add_trace(go.Scatter(x=buy_dates, y=buy_prices, mode='markers', marker=dict(symbol='triangle-up', color='green', size=15), name='AL'), row=1, col=1)
    fig.add_trace(go.Scatter(x=sell_dates, y=sell_prices, mode='markers', marker=dict(symbol='triangle-down', color='red', size=15), name='SAT'), row=1, col=1)

    # PANEL 2: HACİM
    colors = ['green' if v > df['VOL_MA_20'].iloc[i]*1.2 else 'gray' for i, v in enumerate(df['Volume'])]
    fig.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color=colors, name='Hacim'), row=2, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['VOL_MA_20'] * 1.2, line=dict(color='red'), name='Hacim Eşiği (%120)'), row=2, col=1)

    # PANEL 3: SMI
    fig.add_trace(go.Scatter(x=df.index, y=df['SMI'], line=dict(color='blue'), name='SMI'), row=3, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['SMI_SIGNAL'], line=dict(color='red'), name='Signal'), row=3, col=1)
    fig.add_hline(y=40, line_dash="dot", line_color="orange", row=3, col=1)

    # PANEL 4: RSI
    fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='purple'), name='RSI'), row=4, col=1)
    fig.add_hline(y=45, line_dash="dot", line_color="black", row=4, col=1)

    fig.update_layout(title="AKFYE Sniper v5.0 - Hacim & Oynaklık Stratejisi", height=1000, xaxis_rangeslider_visible=False)
    fig.show()

if __name__ == "__main__":
    data = fetch_data("AKFYE", "2023-01-01") 
    data = add_advanced_indicators(data)
    son_bakiye, islem_gecmisi = backtest_advanced(data, 10000)
    print(f"\nSONUÇ: 10.000 TL -> {son_bakiye:.2f} TL (Getiri: %{((son_bakiye-10000)/10000)*100:.2f})")
    plot_advanced(data, islem_gecmisi)
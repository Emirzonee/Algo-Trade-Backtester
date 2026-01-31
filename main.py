import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go

def fetch_data(symbol, start_date):
    print(f"[*] Veri indiriliyor: {symbol}...")
    if not symbol.endswith(".IS"):
        symbol = f"{symbol}.IS"
    df = yf.download(symbol, start=start_date, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.dropna(inplace=True)
    return df

def add_indicators(df):
    # 1. EMA 50 ve Eğim
    df['EMA_50'] = ta.ema(df['Close'], length=50)
    df['EMA_Slope'] = df['EMA_50'].diff()
    
    # 2. Hacim Teyidi (Para Girişi)
    df['Vol_SMA_20'] = ta.sma(df['Volume'], length=20)
    
    # 3. Bollinger Bantları
    bbands = ta.bbands(df['Close'], length=20, std=2)
    upper_col = [col for col in bbands.columns if col.startswith("BBU")][0]
    df['BB_Upper'] = bbands[upper_col]
    
    # 4. SuperTrend (Hata Korumalı Dinamik Seçim)
    st_df = ta.supertrend(df['High'], df['Low'], df['Close'], length=10, multiplier=3)
    trend_col = [col for col in st_df.columns if col.startswith("SUPERTd")][0]
    line_col = [col for col in st_df.columns if col.startswith("SUPERT_")][0]
    df['ST_Trend'] = st_df[trend_col]
    df['ST_Line'] = st_df[line_col]
    df['ST_Slope'] = df['ST_Line'].diff().abs()
    
    # --- Mum Analizleri ---
    df['Is_Red'] = df['Close'] < df['Open']
    df['Body_Size'] = (df['Close'] - df['Open']).abs()
    df['Total_Size'] = (df['High'] - df['Low']).abs()
    # Senin özel tahliye oranının (%34.7)
    df['Mid_Strong_Red'] = df['Is_Red'] & (df['Body_Size'] > (df['Total_Size'] * 0.347))
    
    return df

def backtest_v8_39(df, initial_capital=10000):
    capital = initial_capital
    position = 0 
    trades = []
    entry_price = 0
    
    # GÜNCEL: Dengeli Giriş Toleransı (%1.0 Üstü)
    buy_tolerance = 1.0033
    stop_tolerance = 0.988  
    ceza_modu = False 

    print(f"\n[*] SNIPER v8.39 (Dengeli Giriş: 1.010) Başlıyor... Kasa: {initial_capital} TL")
    print("-" * 145)

    for i in range(51, len(df)):
        price = df['Close'].iloc[i]
        open_p = df['Open'].iloc[i]
        high_p = df['High'].iloc[i]
        low_p = df['Low'].iloc[i]
        vol_now = df['Volume'].iloc[i]
        vol_avg = df['Vol_SMA_20'].iloc[i]
        bb_upper = df['BB_Upper'].iloc[i]
        st_trend = df['ST_Trend'].iloc[i]
        st_slope = df['ST_Slope'].iloc[i]
        
        date = df.index[i]
        ema_50 = df['EMA_50'].iloc[i]
        ema_slope = df['EMA_Slope'].iloc[i] 
        
        govde = abs(price - open_p)
        ust_fitil = high_p - max(price, open_p)
        zayif_mum = (ust_fitil > (govde if govde > 0 else 0.01) * 2.5)
        fiyat_tepede = (price > bb_upper * 0.98) 
        guclu_mum = (price > open_p) and (govde > (high_p - low_p) * 0.5)

        # --- SATIŞ KONTROLLERİ (Hassas Filtrelerin) ---
        four_mid_red = all(df['Mid_Strong_Red'].iloc[i-3:i+1]) if i >= 3 else False
        five_any_red = all(df['Is_Red'].iloc[i-4:i+1]) if i >= 4 else False

        # Hiyerarşik Şartlar
        st_yatay_mi = (st_slope < 0.01)
        st_onayi = (st_trend == 1) and not (st_yatay_mi and fiyat_tepede)
        kral_sartlari = (price >= ema_50 * buy_tolerance) and (ema_slope > 0) and (vol_now > vol_avg)

        # 🟢 ALIM
        if position == 0:
            if kral_sartlari and st_onayi:
                if ceza_modu and not guclu_mum: continue
                
                position = capital / price
                entry_price = price
                capital = 0 
                ceza_modu = False
                trades.append({'Date': date, 'Type': 'BUY', 'Price': price})
                print(f"{date.strftime('%Y-%m-%d'):<12} | 🟢 AL        | {price:<10.2f} | Dengeli Kırılım (Tolerans 1.010)")

        # 🔴 SATIŞ
        elif position > 0:
            should_sell = False
            sell_reason = ""
            
            if price < (ema_50 * stop_tolerance) or st_trend == -1: 
                should_sell = True
                sell_reason = "Trend Bitti (EMA/ST)"
                ceza_modu = False
            elif zayif_mum and fiyat_tepede: 
                should_sell = True
                sell_reason = "Zirve Fitil"
                ceza_modu = True 
            elif four_mid_red:
                should_sell = True
                sell_reason = "HASSAS TAHLİYE (4 Mum %34.7)"
                ceza_modu = True 
            elif five_any_red:
                should_sell = True
                sell_reason = "KESİN TAHLİYE (5 Kırmızı)"
                ceza_modu = True 
            
            if should_sell:
                revenue = position * price
                capital = revenue
                trades.append({'Date': date, 'Type': 'SELL', 'Price': price})
                durum = "✅" if price > entry_price else "🔻"
                print(f"{date.strftime('%Y-%m-%d'):<12} | 🔴 SAT        | {price:<10.2f} | {sell_reason:<35} | {capital:.2f} TL {durum}")
                position = 0

    if position > 0: capital = position * df['Close'].iloc[-1]
    return capital, trades

def plot_final_graph(df, trades):
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='Fiyat'))
    fig.add_trace(go.Scatter(x=df.index, y=df['EMA_50'], line=dict(color='orange', width=2), name='EMA 50'))
    fig.add_trace(go.Scatter(x=df.index, y=df['BB_Upper'], line=dict(color='gray', width=1, dash='dot'), name='Bollinger Üst'))
    fig.add_trace(go.Scatter(x=df.index, y=df['ST_Line'], line=dict(color='blue', width=1), name='SuperTrend'))
    
    buy_dates = [t['Date'] for t in trades if t['Type'] == 'BUY']
    buy_prices = [t['Price'] for t in trades if t['Type'] == 'BUY']
    sell_dates = [t['Date'] for t in trades if t['Type'] == 'SELL']
    sell_prices = [t['Price'] for t in trades if t['Type'] == 'SELL']
    
    fig.add_trace(go.Scatter(x=buy_dates, y=buy_prices, mode='markers', marker=dict(symbol='triangle-up', color='lime', size=15), name='AL'))
    fig.add_trace(go.Scatter(x=sell_dates, y=sell_prices, mode='markers', marker=dict(symbol='triangle-down', color='red', size=15), name='SAT'))
    
    fig.update_layout(title="AKFYE v8.39 - Dengeli Giriş & Kesin Tahliye", height=800, xaxis_rangeslider_visible=False)
    fig.show()

if __name__ == "__main__":
    data = fetch_data("AKFYE", "2023-01-01") 
    data = add_indicators(data)
    son_bakiye, islem_gecmisi = backtest_v8_39(data, 10000)
    print(f"\nSONUÇ: 10.000 TL -> {son_bakiye:.2f} TL")
    plot_final_graph(data, islem_gecmisi)
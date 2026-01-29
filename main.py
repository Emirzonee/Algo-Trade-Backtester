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

def add_supertrend_strategy(df):
    """
    Ralli Avcısı Stratejisi: SuperTrend
    Trend sürdükçe pozisyonu asla kapatmaz.
    """
    # SuperTrend (Period: 10, Multiplier: 3 - Standart Ayar)
    # Bu fonksiyon 4 sütun döndürür: [SuperTrend Değeri, Trend Yönü (1/-1), Long, Short]
    st = ta.supertrend(df['High'], df['Low'], df['Close'], length=10, multiplier=3)
    
    # Sütun isimleri dinamik olduğu için (SUPERT_10_3.0 vb.) sırayla alıyoruz (KeyError Kaçış)
    df['SUPERTREND_LINE'] = st.iloc[:, 0] # Çizgi değeri
    df['SUPERTREND_DIR'] = st.iloc[:, 1]  # Yön (1: Yükseliş/Yeşil, -1: Düşüş/Kırmızı)
    
    return df

def backtest_supertrend(df, initial_capital=10000):
    capital = initial_capital
    position = 0 
    entry_price = 0
    trades = []
    
    print(f"\n[*] SUPERTREND Stratejisi Başlıyor... Kasa: {initial_capital} TL")
    print("-" * 100)
    print(f"{'TARİH':<12} | {'İŞLEM':<10} | {'FİYAT':<10} | {'DURUM':<30} | {'BAKİYE'}")
    print("-" * 100)
    
    # SuperTrend oluşması için ilk 10 günü atla
    for i in range(10, len(df)):
        price = df['Close'].iloc[i]
        date = df.index[i]
        
        # SuperTrend Yönü (1: UP, -1: DOWN)
        trend_now = df['SUPERTREND_DIR'].iloc[i]
        trend_prev = df['SUPERTREND_DIR'].iloc[i-1]
        
        st_line = df['SUPERTREND_LINE'].iloc[i]
        
        # --- ALIM SİNYALİ ---
        # Trend Kırmızıdan (-1) Yeşile (1) Döndü
        if trend_prev == -1 and trend_now == 1 and position == 0:
            position = capital / price
            entry_price = price
            capital = 0 
            trades.append({'Date': date, 'Type': 'BUY', 'Price': price})
            print(f"{date.strftime('%Y-%m-%d'):<12} | 🟢 AL       | {price:<10.2f} | Trend Döndü (Ralli Başlangıcı) | Yatırıldı")

        # --- SATIŞ SİNYALİ ---
        # Trend Yeşilden (1) Kırmızıya (-1) Döndü
        elif trend_prev == 1 and trend_now == -1 and position > 0:
            revenue = position * price
            profit = revenue - (position * entry_price)
            profit_pct = (profit / (position * entry_price)) * 100
            capital = revenue
            trades.append({'Date': date, 'Type': 'SELL', 'Price': price})
            
            durum = "✅" if profit > 0 else "🔻"
            print(f"{date.strftime('%Y-%m-%d'):<12} | 🔴 SAT       | {price:<10.2f} | Trend Bitti (%{profit_pct:.1f})       | {capital:.2f} TL {durum}")
            
            position = 0

    if position > 0:
        capital = position * df['Close'].iloc[-1]
    
    return capital, trades

def plot_supertrend(df, trades):
    fig = go.Figure()

    # 1. Mum Grafiği
    fig.add_trace(go.Candlestick(x=df.index,
                open=df['Open'], high=df['High'],
                low=df['Low'], close=df['Close'], name='Fiyat'))

    # 2. SuperTrend Çizgisi (Tek renk yerine trende göre renkli çizelim)
    # Yükseliş (Yeşil) kısımları
    up_trend = df[df['SUPERTREND_DIR'] == 1]
    fig.add_trace(go.Scatter(x=up_trend.index, y=up_trend['SUPERTREND_LINE'],
                             mode='markers', marker=dict(color='green', size=2), name='Alım Bölgesi (Destek)'))
    
    # Düşüş (Kırmızı) kısımları
    down_trend = df[df['SUPERTREND_DIR'] == -1]
    fig.add_trace(go.Scatter(x=down_trend.index, y=down_trend['SUPERTREND_LINE'],
                             mode='markers', marker=dict(color='red', size=2), name='Satım Bölgesi (Direnç)'))

    # 3. Al-Sat İşaretleri
    buy_dates = [t['Date'] for t in trades if t['Type'] == 'BUY']
    buy_prices = [t['Price'] for t in trades if t['Type'] == 'BUY']
    sell_dates = [t['Date'] for t in trades if t['Type'] == 'SELL']
    sell_prices = [t['Price'] for t in trades if t['Type'] == 'SELL']

    fig.add_trace(go.Scatter(x=buy_dates, y=buy_prices, mode='markers', marker=dict(symbol='triangle-up', color='blue', size=15), name='AL'))
    fig.add_trace(go.Scatter(x=sell_dates, y=sell_prices, mode='markers', marker=dict(symbol='triangle-down', color='orange', size=15), name='SAT'))

    fig.update_layout(
        title="AKFYE - SuperTrend Stratejisi (Trend Takipçisi)",
        yaxis_title="Fiyat (TL)",
        height=700,
        dragmode='zoom',
        hovermode='x unified'
    )
    fig.show()

if __name__ == "__main__":
    # Tarihi biraz daha geriye çektim ki o büyük rallinin başını görelim
    data = fetch_data("AKFYE", "2023-01-01") 
    
    data = add_supertrend_strategy(data)
    # İlk 10 gün hesaplama yok, temizleyelim
    data.dropna(inplace=True)
    
    son_bakiye, islem_gecmisi = backtest_supertrend(data, 10000)
    
    getiri = ((son_bakiye - 10000) / 10000) * 100
    print("-" * 100)
    print(f"SONUÇ: 10.000 TL -> {son_bakiye:.2f} TL (Getiri: %{getiri:.2f})")
    print("-" * 100)
    
    plot_supertrend(data, islem_gecmisi)
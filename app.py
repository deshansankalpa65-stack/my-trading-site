import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# --- 1. වෙබ් පිටුවේ සැකසුම් ---
st.set_page_config(page_title="Gold Live Signals", layout="centered")
st.title("🚨 Gold (XAU/USD) Live Strategy Signals")
st.write("Heikin Ashi & LSMA (25) මත පදනම් වූ සජීවී සංඥා (Live Signals)")

# --- 2. SideBar Settings ---
st.sidebar.header("⚙️ Settings")
timeframe = st.sidebar.selectbox(
    "Select Timeframe",
    options=["1m", "5m", "15m", "30m", "1h", "1d"],
    index=4  # Default එක 1h
)

# ටයිම්ෆ්‍රේම් එක අනුව සපෝට් කරන කාලය සැකසීම
if timeframe == "1m":
    data_period = "7d"
elif timeframe in ["5m", "15m", "30m", "1h"]:
    data_period = "60d"
else:
    data_period = "3mo"

# --- 3. 🚀 DATA LOADING ---
@st.cache_data(ttl=30)
def load_market_data(ticker, period, interval):
    df = yf.download(tickers=ticker, period=period, interval=interval, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.droplevel(1)
    return df

with st.spinner("Analyzing Market..."):
    data = load_market_data("GC=F", data_period, timeframe)

if data.empty:
    st.error("No data found. Please try another timeframe.")
    st.stop()

# --- 4. ⚡ FAST HEIKIN ASHI ---
ha_df = pd.DataFrame(index=data.index)
ha_df['Close'] = (data['Open'] + data['High'] + data['Low'] + data['Close']) / 4

ha_open = np.zeros(len(data))
ha_open[0] = data['Open'].iloc[0]
ha_close = ha_df['Close'].values

for i in range(1, len(data)):
    ha_open[i] = (ha_open[i-1] + ha_close[i-1]) / 2

ha_df['Open'] = ha_open

# --- 5. ⚡ FAST LSMA (LINEAR REGRESSION 25) ---
def calculate_lsma_fast(series, period=25):
    x = np.arange(period)
    x_mean = x.mean()
    x_der = x - x_mean
    x_norm = np.sum(x_der**2)
    def get_slope(y):
        return np.sum((y - y.mean()) * x_der) / x_norm
    slopes = series.rolling(window=period).apply(get_slope, raw=True)
    means = series.rolling(window=period).mean()
    intercepts = means - slopes * x_mean
    return slopes * (period - 1) + intercepts

data['LSMA'] = calculate_lsma_fast(data['Close'], period=25)

# ඩේටා ටික එකතු කර ගැනීම
final_df = pd.DataFrame(index=data.index)
final_df['HA_Open'] = ha_df['Open']
final_df['HA_Close'] = ha_df['Close']
final_df['LSMA'] = data['LSMA']
final_df['Live_Price'] = data['Close']

# අන්තිමටම අවසන් වුණු කැන්ඩ්ල් එකේ ඩේටා (රීෆ්‍රෙෂ් වෙන ලයිව්ම එක)
current_bar = final_df.iloc[-1]

# --- 6. 🚦 SIGNAL GENERATION LOGIC ---
is_bullish_candle = current_bar['HA_Close'] > current_bar['HA_Open']
is_above_lsma = current_bar['Live_Price'] > current_bar['LSMA']

if is_bullish_candle and is_above_lsma:
    signal = "BUY 🟢"
    bg_color = "#26a69a"
    status_text = "Market එක ශක්තිමත් Bullish තත්වයක පවතී. මිල තවත් ඉහළ යා හැක."
elif not is_bullish_candle and not is_above_lsma:
    signal = "SELL 🔴"
    bg_color = "#ef5350"
    status_text = "Market එක ශක්තිමත් Bearish තත්වයක පවතී. මිල තවත් පහළ යා හැක."
else:
    signal = "HOLD / WAIT 🟡"
    bg_color = "#ff9800"
    status_text = "Market එක මේ වෙලාවේ පැහැදිලි නැත (Side-ways). අලුත් Trend එකක් එනතුරු රැඳී සිටින්න."

# --- 7. DISPLAY SIGNALS (ලස්සන බොක්ස් එකක් විදිහට පෙන්වීම) ---
st.markdown("---")
st.subheader(f"📊 Current Live Signal ({timeframe} Timeframe)")

st.markdown(f"""
    <div style="background-color: {bg_color}; padding: 30px; border-radius: 15px; text-align: center;">
        <h1 style="color: white; margin: 0; font-size: 50px; font-weight: bold;">{signal}</h1>
        <p style="color: white; margin-top: 10px; font-size: 18px;">{status_text}</p>
    </div>
""", unsafe_allow_html=True)

# --- 8. 📊 වැඩිදුර තොරතුරු (Market Metrics) ---
st.markdown("### 🔍 Technical Details")
col1, col2, col3 = st.columns(3)

with col1:
    st.metric(label="Current Gold Price", value=f"${current_bar['Live_Price']:.2f}")
with col2:
    st.metric(label="LSMA (25) Value", value=f"${current_bar['LSMA']:.2f}")
with col3:
    candle_type = "Green 🟩" if is_bullish_candle else "Red 🟥"
    st.metric(label="Heikin Ashi Candle", value=candle_type)

st.markdown("---")
st.caption("💡 සටහන: මෙම සිග්නල්ස් තත්පර 30න් 30ට auto-update වේ. පිටුව refresh කිරීමට අවශ්‍ය නැත.")

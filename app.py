import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. වෙබ් පිටුවේ ප්‍රධාන සැකසුම් (TradingView Full Width) ---
st.set_page_config(page_title="Gold TradingView Analyzer", layout="wide")

# TradingView වගේ Header එකක්
st.markdown("""
    <h2 style='text-align: left; color: #d1d4dc; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;'>
        💛 XAUUSD — GOLD SPOT / U.S. DOLLAR <span style='font-size: 14px; color: #787b86;'>· 1h · TV-Style</span>
    </h2>
""", unsafe_allow_html=True)

# --- 2. SideBar Settings ---
st.sidebar.header("⚙️ Chart Settings")

timeframe = st.sidebar.selectbox(
    "Interval",
    options=["1m", "5m", "15m", "30m", "1h", "1d"],
    index=4
)

# ටයිම්ෆ්‍රේම් එක අනුව උපරිම සපෝට් කරන කාලය සැකසීම
if timeframe == "1m":
    data_period = "7d"
elif timeframe in ["5m", "15m", "30m", "1h"]:
    data_period = "60d"
else:
    data_period = "3mo"

# --- 3. 🚀 HIGH-SPEED DATA LOADING (Caching) ---
@st.cache_data(ttl=30)  # තත්පර 30ක් Cache රඳවා ගැනීමෙන් Speed එක උපරිම වේ
def load_market_data(ticker, period, interval):
    df = yf.download(tickers=ticker, period=period, interval=interval, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.droplevel(1)
    return df

with st.spinner("Connecting to TV Server..."):
    data = load_market_data("GC=F", data_period, timeframe)

if data.empty:
    st.error("No data found. Please try another timeframe.")
    st.stop()

# --- 4. ⚡ FAST VECTORIZED HEIKIN ASHI (No Loops!) ---
ha_df = pd.DataFrame(index=data.index)
ha_df['Close'] = (data['Open'] + data['High'] + data['Low'] + data['Close']) / 4

# වේගවත්ම ක්‍රමයට Heikin Ashi Open එක සෙවීම
ha_open = np.zeros(len(data))
ha_open[0] = data['Open'].iloc[0]
data_open = data['Open'].values
ha_close = ha_df['Close'].values

for i in range(1, len(data)):
    ha_open[i] = (ha_open[i-1] + ha_close[i-1]) / 2

ha_df['Open'] = ha_open
ha_df['High'] = np.maximum(data['High'].values, np.maximum(ha_df['Open'].values, ha_df['Close'].values))
ha_df['Low'] = np.minimum(data['Low'].values, np.minimum(ha_df['Open'].values, ha_df['Close'].values))

# --- 5. ⚡ FAST LSMA (LINEAR REGRESSION 25) ---
def calculate_lsma_fast(series, period=25):
    # Rolling Regression එකක් මඟින් ඉතා වේගයෙන් ගණනය කිරීම
    x = np.arange(period)
    x_mean = x.mean()
    x_der = x - x_mean
    x_norm = np.sum(x_der**2)
    
    def get_slope(y):
        return np.sum((y - y.mean()) * x_der) / x_norm

    # Rolling window එක පාවිච්චි කර කෝඩ් එක සුපිරි වේගවත් කිරීම
    slopes = series.rolling(window=period).apply(get_slope, raw=True)
    means = series.rolling(window=period).mean()
    
    # LSMA අගයන් සකස් කිරීම
    intercepts = means - slopes * x_mean
    lsma = slopes * (period - 1) + intercepts
    return lsma

data['LSMA'] = calculate_lsma_fast(data['Close'], period=25)

# --- 6. 🎨 TRADINGVIEW STYLE CHART DESIGN ---
fig = make_subplots(
    rows=2, cols=1, 
    shared_xaxes=True, 
    vertical_spacing=0.01,  # TradingView වගේ ඉතා කිට්ටු ස්පේස් එකක්
    row_width=[0.12, 0.88]  # 88% ප්‍රධාන චාර්ට් එකට
)

# TradingView Candlesticks (නියම Colors)
fig.add_trace(
    go.Candlestick(
        x=data.index, open=ha_df['Open'], high=ha_df['High'], low=ha_df['Low'], close=ha_df['Close'],
        name="HA Gold",
        increasing_line_color='#26a69a', decreasing_line_color='#ef5350',
        increasing_fillcolor='#26a69a', decreasing_fillcolor='#ef5350'
    ), row=1, col=1
)

# LSMA Indicator Line (TradingView Smooth Line Style)
fig.add_trace(
    go.Scatter(
        x=data.index, y=data['LSMA'], name="LSMA (25)",
        line=dict(color='#2962ff', width=2),  # TradingView බ්ලූ කලර් එක
    ), row=1, col=1
)

# Volume Bars (TradingView Color-Matched Style)
# කලින් කැන්ඩ්ල් එකට වඩා මිල වැඩි නම් කොළ, නැත්නම් රතු
vol_colors = np.where(data['Close'] >= data['Open'], '#26a69a', '#ef5350')
fig.add_trace(
    go.Bar(
        x=data.index, y=data['Volume'], name="Volume",
        marker_color=vol_colors, opacity=0.25
    ), row=2, col=1
)

# --- 7. TRADINGVIEW EXACT LAYOUT & GRAPHICS ---
fig.update_layout(
    template="plotly_dark",
    xaxis_rangeslider_visible=False,
    height=700, # නියම ප්‍රමාණය
    margin=dict(l=10, r=60, t=10, b=10), # දකුණු පැත්තේ Price scale එකට ඉඩ තැබීම
    paper_bgcolor='#1c2030', # TradingView නිවැරදිම Dark Theme පැහැය
    plot_bgcolor='#1c2030',
    hovermode="x unified", # Crosshair එකක් වගේ ට්‍රැක් වන ක්‍රමය
    dragmode="pan", # Chart එක අතින් ඇදීමට හැකි වීම (Pan Mode)
)

# Grid Lines සහ Axes (TradingView ස්ටයිල් ලා පැහැති රේඛා)
fig.update_xaxes(
    gridcolor='#2a2e39', zeroline=False, showline=True, linecolor='#2a2e39',
    showspikes=True, spikemode="across", spikesnap="cursor", spikedash="dash", spikecolor="#787b86", spikethickness=1
)
fig.update_yaxes(
    gridcolor='#2a2e39', zeroline=False, showline=True, linecolor='#2a2e39', side="right", # මිල දකුණු පැත්තේ පෙන්වීම
    showspikes=True, spikemode="across", spikesnap="cursor", spikedash="dash", spikecolor="#787b86", spikethickness=1
)

# වෙබ් පිටුවට දැමීම
st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True}) # Zoom කිරීමට ඉඩ දීම

# ඩේටා ටේබල් එක යටින් ලස්සනට පෙන්වීම
with st.expander("📊 View Market Data Sheet"):
    st.dataframe(data.tail(20), use_container_width=True)

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. වෙබ් පිටුවේ ප්‍රධාන සැකසුම් (Page Config) ---
st.set_page_config(page_title="Gold MT5 Strategy Analyzer", layout="wide")
st.title("📊 Gold (XAU/USD) MT5 Strategy Analyzer")

# --- 2. SideBar එකේ Settings හැදීම ---
st.sidebar.header("🔧 Strategy Settings")

# ටයිම්ෆ්‍රේම් තේරීම
timeframe = st.sidebar.selectbox(
    "Select Timeframe",
    options=["1m", "5m", "15m", "30m", "1h", "1d"],
    index=4  # Default එක "1h" විදිහට තැබීම
)

# --- 3. ටයිම්ෆ්‍රේම් එක අනුව සපෝට් කරන උපරිම Range (Period) එක හැදීම ---
if timeframe == "1m":
    data_period = "7d"
elif timeframe in ["5m", "15m", "30m", "1h"]:
    data_period = "60d"
else:
    data_period = "1mo"

# --- 4. Yahoo Finance මඟින් ඩේටා බාගත කිරීම ---
@st.cache_data(ttl=60)  # විනාඩියෙන් විනාඩිය ඩේටා auto refresh වීමට
def load_data(ticker, period, interval):
    df = yf.download(tickers=ticker, period=period, interval=interval)
    # Multi-level index තිබුනොත් ඒක අයින් කිරීම (yfinance fix)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.droplevel(1)
    return df

with st.spinner("Fetching market data..."):
    # Gold Futures (GC=F) සඳහා ඩේටා ලබා ගැනීම
    data = load_data("GC=F", data_period, timeframe)

# ඩේටා ලැබිලා නැත්නම් Error එකක් පෙන්වීම
if data.empty:
    st.error("No data found for the selected asset/timeframe. Please try again.")
    st.stop()

# --- 5. Heikin Ashi Candles ගණනය කිරීම ---
ha_df = pd.DataFrame(index=data.index)
ha_df['Close'] = (data['Open'] + data['High'] + data['Low'] + data['Close']) / 4

ha_open = [data['Open'].iloc[0]]
for i in range(1, len(data)):
    ha_open.append((ha_open[i-1] + ha_df['Close'].iloc[i-1]) / 2)
ha_df['Open'] = ha_open

ha_df['High'] = data[['High', 'Open', 'Close']].max(axis=1)
ha_df['Low'] = data[['Low', 'Open', 'Close']].min(axis=1)

# --- 6. Linear Regression (LSMA 25) ගණනය කිරීම ---
def calculate_lsma(series, period=25):
    lsma_values = []
    for i in range(len(series)):
        if i < period - 1:
            lsma_values.append(np.nan)
        else:
            y = series.iloc[i - period + 1 : i + 1].values
            x = np.arange(period)
            slope, intercept = np.polyfit(x, y, 1)
            lsma_val = slope * (period - 1) + intercept
            lsma_values.append(lsma_val)
    return pd.Series(lsma_values, index=series.index)

data['LSMA'] = calculate_lsma(data['Close'], period=25)

# --- 7. MT5 Style Candlestick & Volume Chart එක ඇඳීම ---
fig = make_subplots(
    rows=2, cols=1, 
    shared_xaxes=True, 
    vertical_spacing=0.03, 
    row_width=[0.15, 0.85]  # 85% Chart, 15% Volume
)

# MT5 Candlesticks එකතු කිරීම (Heikin Ashi පාවිච්චි කර ඇත)
fig.add_trace(
    go.Candlestick(
        x=data.index,
        open=ha_df['Open'],
        high=ha_df['High'],
        low=ha_df['Low'],
        close=ha_df['Close'],
        name="Heikin Ashi",
        increasing_line_color='#26a69a',  # MT5 Bullish කොළ
        decreasing_line_color='#ef5350',  # MT5 Bearish රතු
        increasing_fillcolor='#26a69a',
        decreasing_fillcolor='#ef5350'
    ),
    row=1, col=1
)

# LSMA 25 රේඛාව (Line) එකතු කිරීම
fig.add_trace(
    go.Scatter(
        x=data.index,
        y=data['LSMA'],
        name="LSMA (25)",
        line=dict(color='#ff9800', width=2),  # තැඹිලි පාට ලයින් එකක්
    ),
    row=1, col=1
)

# Volume Bars එකතු කිරීම
if 'Volume' in data.columns:
    fig.add_trace(
        go.Bar(
            x=data.index, 
            y=data['Volume'], 
            name="Volume",
            marker_color='#26a69a',
            opacity=0.3
        ),
        row=2, col=1
    )

# MT5 Dark Mode Layout එක සැකසීම
fig.update_layout(
    template="plotly_dark",
    xaxis_rangeslider_visible=False,
    height=650,
    margin=dict(l=10, r=10, t=20, b=10),
    paper_bgcolor='#161a25',  # TradingView/MT5 Dark Background
    plot_bgcolor='#161a25',
    yaxis=dict(gridcolor='#232936', zeroline=False, title="Price (USD)"),
    xaxis=dict(gridcolor='#232936', zeroline=False)
)

# වෙබ් පිටුවේ Chart එක පෙන්වීම
st.plotly_chart(fig, use_container_width=True)

# --- 8. යටින් ඩේටා ටේබල් එක පෙන්වීම ---
st.subheader("📋 Recent Market Data")
st.dataframe(data.tail(10), use_container_width=True)

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

# Page එකේ settings හදාගැනීම
st.set_page_config(
    page_title="Golden Hunter Visual Dashboard", layout="wide", page_icon="📈"
)

st.title("📈 Golden Hunter Visual Web Dashboard")
st.caption(
    "Live Heikin Ashi & Linear Regression (LSMA) Strategy Analyzer |
)

# ------------------------------------------------------------------
# Sidebar Controls (Parameters වෙනස් කරන්න)
# ------------------------------------------------------------------
st.sidebar.header("Strategy Settings")

# Market Asset එක තෝරන්න
ticker_options = {
    "Gold (XAU/USD)": "GC=F",
    "Bitcoin (BTC/USD)": "BTC-USD",
    "EUR/USD": "EURUSD=X",
    "Apple Inc. (AAPL)": "AAPL",
}
selected_asset = st.sidebar.selectbox("Select Asset", list(ticker_options.keys()))
ticker_symbol = ticker_options[selected_asset]

# Timeframe සහ Data Period එක
timeframe = st.sidebar.selectbox("Timeframe", ["1h", "1d", "1wk"], index=1)
data_period = st.sidebar.selectbox("Historical Data Range", ["1mo", "3mo", "6mo", "1y"], index=2)

# Indicator Configurations
lsma_length = st.sidebar.slider("LSMA (Golden Line) Length", min_value=5, max_value=100, value=50)

# ------------------------------------------------------------------
# Strategy Logic Function (MT5 logic converted to Python)
# ------------------------------------------------------------------
def calculate_golden_hunter(df, period):
    rates_total = len(df)
    if rates_total < period:
        return df

    # 1. Heikin Ashi Calculation
    ha_close = (df["Open"] + df["High"] + df["Low"] + df["Close"]) / 4.0
    ha_open = np.zeros(rates_total)
    ha_open[0] = (df["Open"].iloc[0] + df["Close"].iloc[0]) / 2.0

    for i in range(1, rates_total):
        ha_open[i] = (ha_open[i - 1] + ha_close.iloc[i - 1]) / 2.0

    df["ha_open"] = ha_open
    df["ha_close"] = ha_close
    df["ha_high"] = df[["High", "ha_open", "ha_close"]].max(axis=1)
    df["ha_low"] = df[["Low", "ha_open", "ha_close"]].min(axis=1)

    # 2. LSMA (Linear Regression Endpoint)
    x = np.arange(period)
    sumX = np.sum(x)
    sumX2 = np.sum(x**2)
    denominator = period * sumX2 - sumX**2

    def get_lr_endpoint(y_window):
        if len(y_window) < period:
            return np.nan
        # Reversed window to match your MT5 script's indexing lookback
        y = y_window[::-1] 
        sumY = np.sum(y)
        sumXY = np.sum(x * y)
        
        if denominator == 0:
            return y[0]
            
        slope = (period * sumXY - sumX * sumY) / denominator
        intercept = (sumY - slope * sumX) / period
        return intercept

    df["LSMA"] = df["ha_close"].rolling(window=period).apply(get_lr_endpoint, raw=True)
    df["LSMA"] = df["LSMA"].fillna(df["ha_close"])

    # 3. Buy/Sell Signals Generation
    df["Buy_Signal"] = np.nan
    df["Sell_Signal"] = np.nan

    for i in range(1, len(df)):
        # Buy Signal condition
        if df["ha_close"].iloc[i] > df["LSMA"].iloc[i] and df["ha_close"].iloc[i - 1] <= df["LSMA"].iloc[i - 1]:
            df.loc[df.index[i], "Buy_Signal"] = df["LSMA"].iloc[i]
        # Sell Signal condition
        elif df["ha_close"].iloc[i] < df["LSMA"].iloc[i] and df["ha_close"].iloc[i - 1] >= df["LSMA"].iloc[i - 1]:
            df.loc[df.index[i], "Sell_Signal"] = df["LSMA"].iloc[i]

    return df

# ------------------------------------------------------------------
# Data Fetching & Rendering
# ------------------------------------------------------------------
with st.spinner("Fetching live market data..."):
    data = yf.download(ticker_symbol, period=data_period, interval=timeframe)

if not data.empty:
    # Multi-index columns flat කරගැනීම (yfinance fresh update fix)
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
        
    df_processed = calculate_golden_hunter(data.copy(), lsma_length)

    # UI Metric Cards (Current State)
    last_row = df_processed.iloc[-1]
    col1, col2, col3 = st.columns(3)
    col1.metric("Current Price", f"${last_row['Close']:.2f}")
    col2.metric("Golden Line (LSMA)", f"${last_row['LSMA']:.2f}")
    
    status = "🔴 BEARISH" if last_row['ha_close'] < last_row['LSMA'] else "🟢 BULLISH"
    col3.metric("Market Status", status)

    # Plotly Interactive Chart එක සෑදීම
    fig = go.Figure()

    # Heikin Ashi Candlesticks Plot එක
    fig.add_trace(go.Candlestick(
        x=df_processed.index,
        open=df_processed['ha_open'],
        high=df_processed['ha_high'],
        low=df_processed['ha_low'],
        close=df_processed['ha_close'],
        name="Heikin Ashi"
    ))

    # LSMA Line Plot එක
    fig.add_trace(go.Scatter(
        x=df_processed.index, y=df_processed['LSMA'],
        line=dict(color='white', width=2.5),
        name="Golden Line (LSMA)"
    ))

    # Buy Arrows
    fig.add_trace(go.Scatter(
        x=df_processed.index, y=df_processed['Buy_Signal'],
        mode='markers',
        marker=dict(symbol='triangle-up', size=12, color='lime', line=dict(width=1, color='black')),
        name="Buy Signal"
    ))

    # Sell Arrows
    fig.add_trace(go.Scatter(
        x=df_processed.index, y=df_processed['Sell_Signal'],
        mode='markers',
        marker=dict(symbol='triangle-down', size=12, color='red', line=dict(width=1, color='black')),
        name="Sell Signal"
    ))

    # Layout styling (Dark Theme)
    fig.update_layout(
        template="plotly_dark",
        xaxis_rangeslider_visible=False,
        height=650,
        margin=dict(l=20, r=20, t=30, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    st.plotly_chart(fig, use_container_width=True)

    # Data Table එක පහලින් පෙන්වන්න
    with st.expander("View Raw Calculated Data"):
        st.dataframe(df_processed[['Open', 'High', 'Low', 'Close', 'LSMA', 'Buy_Signal', 'Sell_Signal']].tail(20))
else:
    st.error("No data found for the selected asset/timeframe. Please try again.")

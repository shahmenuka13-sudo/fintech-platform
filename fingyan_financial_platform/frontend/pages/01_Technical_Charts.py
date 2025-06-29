import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

# Assuming api_client is in ../utils or accessible via PYTHONPATH
# If running `streamlit run frontend/app.py` from project root, this should work.
# If running `streamlit run 01_Technical_Charts.py` directly from pages folder, path needs adjustment.
# For st_pages, paths are relative to where `streamlit run` is executed (usually project root).
try:
    from utils import api_client
except ImportError:
    # Fallback for direct execution from 'pages' (less common for multi-page apps)
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
    from utils import api_client


st.set_page_config(layout="wide", page_title="Interactive Technical Charts")
st.title("📈 Interactive Technical Charts")

# --- Inputs ---
st.sidebar.header("Chart Settings")
default_symbol = "RELIANCE.NS" # Default symbol
symbol = st.sidebar.text_input("Enter Stock Symbol (e.g., RELIANCE.NS, AAPL):", value=default_symbol).upper()

# Date range
# col1, col2 = st.sidebar.columns(2)
# with col1:
#     start_date = st.date_input("Start Date", datetime.now() - timedelta(days=365))
# with col2:
#     end_date = st.date_input("End Date", datetime.now())

# Period and Interval (simpler for yfinance)
# Common yfinance periods: 1d,5d,1mo,3mo,6mo,1y,2y,5y,10y,ytd,max
# Common yfinance intervals: 1m,2m,5m,15m,30m,60m,90m,1h,1d,5d,1wk,1mo,3mo
period_options = ["1mo", "3mo", "6mo", "1y", "2y", "5y", "max"]
selected_period = st.sidebar.selectbox("Select Period:", period_options, index=3) # Default to "1y"

interval_options_map = {
    "1mo": ["1h", "1d", "5d"], # Granular for shorter periods
    "3mo": ["1h", "1d", "5d"],
    "6mo": ["1d", "5d", "1wk"],
    "1y": ["1d", "5d", "1wk", "1mo"],
    "2y": ["1d", "5d", "1wk", "1mo"],
    "5y": ["1d", "1wk", "1mo", "3mo"],
    "max": ["1d", "1wk", "1mo", "3mo"]
}
# Adjust interval options based on selected period to avoid yfinance errors (e.g. 1m interval for 5y period)
valid_intervals = interval_options_map.get(selected_period, ["1d", "1wk", "1mo"])
selected_interval = st.sidebar.selectbox("Select Interval:", valid_intervals, index=0 if "1d" not in valid_intervals else valid_intervals.index("1d"))


# --- Technical Indicators ---
st.sidebar.subheader("Indicators")
show_ma = st.sidebar.checkbox("Moving Average (MA)", value=True)
ma_periods_str = st.sidebar.text_input("MA Periods (comma-separated, e.g., 20,50,200):", "20,50")
ma_periods = []
if show_ma and ma_periods_str:
    try:
        ma_periods = [int(p.strip()) for p in ma_periods_str.split(',') if p.strip().isdigit() and int(p.strip()) > 0]
    except ValueError:
        st.sidebar.error("Invalid MA periods. Please enter positive integers.")
        ma_periods = []


show_rsi = st.sidebar.checkbox("RSI (Relative Strength Index)", value=True)
rsi_period = st.sidebar.slider("RSI Period:", min_value=2, max_value=50, value=14, disabled=not show_rsi)

show_macd = st.sidebar.checkbox("MACD", value=True)
macd_fast = st.sidebar.slider("MACD Fast Period:", min_value=2, max_value=50, value=12, disabled=not show_macd)
macd_slow = st.sidebar.slider("MACD Slow Period:", min_value=10, max_value=100, value=26, disabled=not show_macd)
macd_signal = st.sidebar.slider("MACD Signal Period:", min_value=2, max_value=50, value=9, disabled=not show_macd)


# --- Fetch Data and Plot Chart ---
if symbol:
    st.header(f"Chart for: {symbol}")

    # Add a loading spinner
    with st.spinner(f"Fetching data for {symbol}..."):
        hist_df = api_client.get_stock_historical_data(symbol, period=selected_period, interval=selected_interval)

    if hist_df is not None and not hist_df.empty:
        # Calculate Indicators
        if show_ma:
            for ma in ma_periods:
                if ma <= len(hist_df):
                    hist_df[f'MA{ma}'] = hist_df['close'].rolling(window=ma).mean()
                else:
                    st.warning(f"MA{ma} period is too long for the available data ({len(hist_df)} points). Skipping MA{ma}.")


        if show_rsi:
            delta = hist_df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=rsi_period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_period).mean()
            rs = gain / loss
            hist_df['RSI'] = 100 - (100 / (1 + rs))

        if show_macd:
            if macd_fast < macd_slow :
                exp1 = hist_df['close'].ewm(span=macd_fast, adjust=False).mean()
                exp2 = hist_df['close'].ewm(span=macd_slow, adjust=False).mean()
                hist_df['MACD'] = exp1 - exp2
                hist_df['MACD_Signal'] = hist_df['MACD'].ewm(span=macd_signal, adjust=False).mean()
                hist_df['MACD_Hist'] = hist_df['MACD'] - hist_df['MACD_Signal']
            else:
                st.warning("MACD Fast period must be less than Slow period. Skipping MACD.")
                show_macd = False # Disable it for plotting

        # --- Create Plot ---
        num_subplots = 1 + (1 if show_rsi else 0) + (1 if show_macd else 0)
        row_heights = [0.6] # Main chart relatively larger
        if show_rsi: row_heights.append(0.2)
        if show_macd: row_heights.append(0.2)

        # Ensure sum of row_heights is close to 1 if they are relative fractions
        if sum(row_heights) > 1 and num_subplots > 1: # Normalize if sum > 1 for multiple plots
             row_heights = [h / sum(row_heights) for h in row_heights]


        fig = make_subplots(
            rows=num_subplots,
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.05,
            row_heights=row_heights if num_subplots > 1 else None
        )

        current_row = 1

        # Candlestick Chart (Main Plot)
        fig.add_trace(go.Candlestick(
            x=hist_df.index,
            open=hist_df['open'],
            high=hist_df['high'],
            low=hist_df['low'],
            close=hist_df['close'],
            name=symbol
        ), row=current_row, col=1)

        # Add Moving Averages
        if show_ma:
            for ma in ma_periods:
                if f'MA{ma}' in hist_df.columns:
                    fig.add_trace(go.Scatter(
                        x=hist_df.index,
                        y=hist_df[f'MA{ma}'],
                        mode='lines',
                        name=f'MA {ma}',
                        line=dict(width=1)
                    ), row=current_row, col=1)

        fig.update_layout(
            yaxis_title='Price',
            xaxis_rangeslider_visible=False, # Main slider off if subplots used
            # height=600 + (num_subplots-1)*150 # Adjust height based on subplots
        )

        current_row += 1

        # RSI Plot
        if show_rsi and 'RSI' in hist_df.columns:
            fig.add_trace(go.Scatter(
                x=hist_df.index,
                y=hist_df['RSI'],
                name='RSI'
            ), row=current_row, col=1)
            fig.add_hline(y=70, line_dash="dash", line_color="red", opacity=0.5, row=current_row, col=1)
            fig.add_hline(y=30, line_dash="dash", line_color="green", opacity=0.5, row=current_row, col=1)
            fig.update_yaxes(title_text="RSI", range=[0,100], row=current_row, col=1)
            current_row += 1

        # MACD Plot
        if show_macd and 'MACD' in hist_df.columns:
            fig.add_trace(go.Scatter(
                x=hist_df.index,
                y=hist_df['MACD'],
                name='MACD',
                line=dict(color='blue')
            ), row=current_row, col=1)
            fig.add_trace(go.Scatter(
                x=hist_df.index,
                y=hist_df['MACD_Signal'],
                name='Signal Line',
                line=dict(color='orange')
            ), row=current_row, col=1)
            # MACD Histogram (as bar chart)
            colors = ['green' if val >= 0 else 'red' for val in hist_df['MACD_Hist']]
            fig.add_trace(go.Bar(
                x=hist_df.index,
                y=hist_df['MACD_Hist'],
                name='MACD Histogram',
                marker_color=colors
            ), row=current_row, col=1)
            fig.update_yaxes(title_text="MACD", row=current_row, col=1)
            current_row += 1

        # Update layout for all subplots
        fig.update_layout(
            title_text=f"{symbol} Technical Chart ({selected_period})",
            height=350 * num_subplots, # Dynamic height
            showlegend=True,
            xaxis_rangeslider_visible=False # Turn off for the last x-axis (shared)
        )
        # Specifically enable range slider for the last subplot's x-axis if multiple plots exist
        if num_subplots > 1:
             fig.update_xaxes(rangeslider_visible=True, row=num_subplots, col=1)


        st.plotly_chart(fig, use_container_width=True)

    elif hist_df is None:
        st.error(f"Failed to fetch data for {symbol}. Check symbol or backend API.")
    else: # hist_df is empty
        st.warning(f"No historical data found for {symbol} with period '{selected_period}' and interval '{selected_interval}'.")
else:
    st.info("Please enter a stock symbol in the sidebar to display its chart.")

# Add some explanation or footer
st.markdown("---")
st.caption("Charts are interactive. Hover for details, click and drag to zoom.")
st.caption("Data provided by yfinance via backend API. Indicators are calculated locally in the browser.")

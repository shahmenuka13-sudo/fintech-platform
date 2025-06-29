import streamlit as st
from st_pages import Page, Section, show_pages, add_page_title, hide_pages

# Basic page configuration
st.set_page_config(
    page_title="Fingyan Financial Platform",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Page Definitions ---
# Using st_pages for a cleaner multi-page app navigation structure.
# https://github.com/blackary/st_pages
show_pages(
    [
        Page("frontend/app.py", "Home - Market Overview", "🏠"), # Main app.py can be the first page
        Section(name="Market Insights", icon="📊"),
        Page("frontend/pages/01_Technical_Charts.py", "Technical Charts", "📈"),
        # Page("frontend/pages/02_Heatmaps.py", "Market Heatmaps", "🔥"), # Example for future
        # Page("frontend/pages/03_Sector_Analysis.py", "Sector Analysis", "🏗️"), # Example for future

        Section(name="User Portfolio", icon="💼"),
        Page("frontend/pages/10_Portfolio_Dashboard.py", "Portfolio Dashboard", "💰"),
        # Page("frontend/pages/11_Portfolio_Analytics.py", "Portfolio Analytics", "🔎"), # Example

        Section(name="Tools & AI", icon="💡"),
        Page("frontend/pages/20_Alerts_Notifications.py", "Alerts & Notifications", "🔔"),
        Page("frontend/pages/21_Predictive_Insights.py", "Predictive Insights", "🧠"),
        # Page("frontend/pages/22_News_Sentiment.py", "Market News & Sentiment", "📰"), # Example

        Section(name="Settings & Help", icon="⚙️"),
        Page("frontend/pages/90_Settings.py", "Settings", "🛠️"),
        # Page("frontend/pages/91_Help_FAQ.py", "Help & FAQ", "❓"), # Example

        # To hide utility pages or tests from sidebar:
        # hide_pages(["utility_page_name_in_pages_folder"])
    ]
)

add_page_title() # Optional: Add page title automatically based on selection

# --- Environment/Config ---
# It's good practice to load API URLs from environment variables or a config file
# For now, hardcoding for simplicity, but this should be changed.
# Ensure this matches your FastAPI backend URL when running with Docker Compose or K8s.
FASTAPI_BACKEND_URL = "http://backend:8000/api" # For Docker Compose
# FASTAPI_BACKEND_URL = "http://localhost:8000/api" # For local FastAPI dev without Docker frontend

st.sidebar.markdown("---")
st.sidebar.info(f"Backend API: `{FASTAPI_BACKEND_URL}`")

# --- Main Page Content (Home - Market Overview) ---
# This content will be shown when app.py is the selected page.

st.header("Welcome to Fingyan Financial Platform!")
st.write("""
    Your AI-powered gateway to Indian stock market insights, analytics, and portfolio management.
    Navigate using the sidebar to explore different features.
""")

st.subheader("Market Overview")
# st.write("This section will display key market indices, top gainers/losers, and other overview data.")

# --- Import API Client ---
from utils import api_client # Assuming utils is in the same directory or PYTHONPATH

# --- Health Check Display in Sidebar (moved from comments) ---
health_status = api_client.get_backend_health()
if health_status:
    st.sidebar.success(f"Backend: {health_status.get('status', 'Unknown')}")
    if health_status.get('redis_connected'):
        st.sidebar.markdown("Redis: Connected")
    else:
        st.sidebar.markdown("Redis: <span style='color:red; font-weight:bold;'>Disconnected</span>", unsafe_allow_html=True)
else:
    st.sidebar.error("Backend: Connection Failed or Error")


# --- Fetch and Display Market Indices ---
# Define Indian market indices to display
INDIAN_INDICES = {
    "NIFTY 50": "^NSEI",
    "SENSEX": "^BSESN",
    "NIFTY BANK": "^NSEBANK",
    # "NIFTY MIDCAP 100": "^NSMIDCPN", # Example, check yfinance for correct symbols
}

st.markdown("#### Key Market Indices")
cols = st.columns(len(INDIAN_INDICES))

for i, (name, symbol) in enumerate(INDIAN_INDICES.items()):
    with cols[i]:
        index_data = api_client.get_index_data(symbol)
        if index_data:
            current_price = index_data.get('currentPrice')
            prev_close = index_data.get('previousClose')

            if current_price is not None and prev_close is not None:
                change = current_price - prev_close
                percent_change = (change / prev_close) * 100 if prev_close != 0 else 0
                delta_color = "normal" # "inverse" for red if positive, "off" for neutral
                if change < 0:
                    delta_color = "inverse"

                st.metric(
                    label=name, # Use display name
                    value=f"{current_price:,.2f}",
                    delta=f"{change:,.2f} ({percent_change:.2f}%)",
                    delta_color=delta_color
                )
                # st.caption(f"Prev. Close: {prev_close:,.2f}")
            elif current_price is not None:
                 st.metric(label=name, value=f"{current_price:,.2f}", delta="N/A")
            else:
                st.error(f"Data unavailable for {name}")
        else:
            st.warning(f"Could not load data for {name} ({symbol}).")

st.markdown("---")
st.write("Top Gainers/Losers, Sectoral Performance, etc. will be added here.")


# Example of how to make an API call (will be moved to specific pages)
# import requests
# try:
#     health_url = f"{FASTAPI_BACKEND_URL.replace('/api', '')}/health" # Health check is outside /api prefix
#     response = requests.get(health_url, timeout=5)
#     if response.status_code == 200:
#         health_data = response.json()
#         st.sidebar.success(f"Backend Status: {health_data.get('status', 'Unknown')}")
#         if health_data.get('redis_connected'):
#             st.sidebar.markdown("Redis: Connected")
#         else:
#             st.sidebar.markdown("Redis: <span style='color:red'>Disconnected</span>", unsafe_allow_html=True)

#     else:
#         st.sidebar.error(f"Backend Status: Error ({response.status_code})")
# except requests.exceptions.ConnectionError:
#     st.sidebar.error("Backend Status: Connection Failed")
# except Exception as e:
#     st.sidebar.error(f"Backend Status: Error - {e}")


# --- Dark/Light Mode Toggle (Example - using a session state for persistence) ---
# This is a simplified toggle. A more robust solution might use streamlit-theme or custom CSS.
if 'theme' not in st.session_state:
    st.session_state.theme = 'light' # Default theme

def toggle_theme():
    st.session_state.theme = 'dark' if st.session_state.theme == 'light' else 'light'
    # Note: Streamlit doesn't have a built-in dynamic theme changer that affects all components easily.
    # This session state variable would be used to conditionally apply CSS or change Plotly themes.
    # For a true dark mode, you'd typically inject custom CSS or use a component.
    # st.experimental_rerun() # Rerun to apply changes if needed for some components

# Simplified: This won't magically change Streamlit's base theme.
# It's a variable we can use in our custom components/CSS.
# st.sidebar.button("Toggle Theme (Concept)", on_click=toggle_theme)
# st.sidebar.write(f"Current Theme Mode: {st.session_state.theme}")


# Placeholder for global styles (e.g., Tailwind via CDN for utility classes)
# This is a basic way to inject CSS. For more complex scenarios, consider components.
# st.markdown("""
# <style>
#     /* Example: Add some padding to main content area */
#     .main .block-container {
#         padding-top: 2rem;
#         padding-bottom: 2rem;
#     }
#     /* Add more global styles here */
# </style>
# """, unsafe_allow_html=True)

# st.info("Note: True dark mode and advanced styling require custom CSS injection or Streamlit theming features.")

# --- Further content for Market Overview page ---
# This will be developed more in the Market Overview page itself if we make it a separate page,
# or expanded here if app.py remains the primary overview display.
# For now, keeping it simple.

# TODO:
# - Implement actual API calls to fetch data for market overview.
# - Create reusable components for charts, tables, etc.
# - Implement user authentication flow (later stage).
# - Refine styling and responsiveness.
# - Set up proper configuration for API URLs.
# - Add a proper dark/light mode toggle with CSS.
# - Ensure mobile responsiveness.
# - Add accessibility features.

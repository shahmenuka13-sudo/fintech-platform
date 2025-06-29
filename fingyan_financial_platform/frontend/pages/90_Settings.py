import streamlit as st

st.set_page_config(layout="wide", page_title="Settings")
st.title("🛠️ Settings")
st.caption("Configure your application preferences.")

# --- Theme Settings ---
st.subheader("Appearance")

# Initialize session state for theme if not already present
if 'app_theme' not in st.session_state:
    st.session_state.app_theme = 'Light' # Default theme: Light or Dark

current_theme_index = 0
if st.session_state.app_theme == 'Dark':
    current_theme_index = 1

selected_theme = st.radio(
    "Select App Theme:",
    options=('Light', 'Dark'),
    index=current_theme_index,
    key='theme_radio',
    horizontal=True
)

if selected_theme != st.session_state.app_theme:
    st.session_state.app_theme = selected_theme
    # Note: Streamlit doesn't have a simple, built-in way to dynamically switch its entire base theme (light/dark)
    # after the app starts and affects all native components.
    # The st.set_page_config(theme="...") can only be called once at the top of the script.
    # This radio button selection is more for demonstrating a user preference that *could* be used
    # to conditionally apply custom CSS or change Plotly chart themes.
    # For a true dynamic theme switch, you might need:
    # 1. A component from streamlit_extras or similar that injects CSS.
    # 2. Custom CSS that keys off a body class or data attribute that you try to set via JavaScript.
    # 3. Or, accept that this toggle mainly affects custom components and Plotly charts.
    st.info(f"Theme preference set to: **{st.session_state.app_theme}**. "
            "Full dynamic theme switching of all Streamlit elements has limitations. "
            "This setting primarily affects custom components and charts if they are theme-aware.")
    st.experimental_rerun() # Rerun to reflect the change in session state immediately

# Example: How you might use this session state elsewhere (e.g., for Plotly charts)
# plotly_theme = "plotly_dark" if st.session_state.app_theme == "Dark" else "plotly_white"
# fig.update_layout(template=plotly_theme)


st.markdown("---")

# --- API Configuration (Placeholder) ---
st.subheader("API Configuration")
st.info("API endpoint configuration is typically managed via environment variables or deployment settings, not here.")
# Example: Display current backend URL (read-only)
try:
    from utils import api_client
    st.write(f"**Current Backend API URL:** `{api_client.FASTAPI_BACKEND_URL}`")
except ImportError:
     st.write("API client not found (utils.api_client).")


st.markdown("---")

# --- User Profile (Placeholder) ---
st.subheader("User Profile")
st.warning("User authentication and profile management are not yet implemented.")
# st.text_input("Username (read-only for now)", value="dummy_user", disabled=True)
# st.text_input("Email (read-only for now)", value="dummy@example.com", disabled=True)
# st.button("Change Password (Disabled)")

st.markdown("---")

# --- Data Refresh Settings (Placeholder) ---
st.subheader("Data Settings")
st.slider("Automatic Data Refresh Interval (minutes - conceptual):", min_value=1, max_value=60, value=5, disabled=True)
st.caption("Note: Streamlit's `@st.cache_data` handles caching. True background refresh requires more complex setup.")

st.markdown("---")
st.caption("More settings will be added as features are developed.")

# TODO:
# - Implement a more robust theme switching mechanism if possible (e.g., using streamlit-theme or custom CSS injection).
# - Connect to actual user profile data once authentication is in place.
# - Provide options to clear specific caches or manage data preferences.

import streamlit as st
import pandas as pd
from datetime import datetime

try:
    from utils import api_client
except ImportError:
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
    from utils import api_client

st.set_page_config(layout="wide", page_title="Alerts & Notifications")
st.title("🔔 Alerts & Notifications")
st.caption("Set up and manage your market alerts.")

# --- Session State ---
if 'editing_alert_id' not in st.session_state:
    st.session_state.editing_alert_id = None

# --- Helper Functions ---
def refresh_alerts_data():
    api_client.get_alerts.clear()
    st.session_state.editing_alert_id = None
    st.experimental_rerun()

def handle_create_alert(symbol, target_price, trigger_when_above, description):
    if not symbol or target_price is None or trigger_when_above is None:
        st.warning("Symbol, target price, and trigger condition (above/below) are required for price alerts.")
        return
    if target_price <= 0:
        st.warning("Target price must be positive.")
        return

    created = api_client.create_alert(
        symbol=symbol,
        alert_type="price", # Currently only supporting price alerts
        target_price=float(target_price),
        trigger_when_above=bool(trigger_when_above),
        description=description
    )
    if created:
        st.success(f"Alert for '{symbol}' created successfully!")
        refresh_alerts_data()

def handle_update_alert(alert_id, target_price, trigger_when_above, is_active, description):
    updated = api_client.update_alert(
        alert_id=alert_id,
        target_price=float(target_price) if target_price is not None else None,
        trigger_when_above=bool(trigger_when_above) if trigger_when_above is not None else None,
        is_active=bool(is_active) if is_active is not None else None,
        description=description
    )
    if updated:
        st.success(f"Alert ID {alert_id} updated.")
        refresh_alerts_data()

def handle_delete_alert(alert_id):
    if api_client.delete_alert(alert_id):
        st.success(f"Alert ID {alert_id} deleted.")
        refresh_alerts_data()

# --- Create New Alert Form ---
st.subheader("➕ Create New Price Alert")
with st.form("create_alert_form", clear_on_submit=True):
    c1, c2, c3 = st.columns([2,1,1])
    new_alert_symbol = c1.text_input("Stock Symbol (e.g., RELIANCE.NS)").upper()
    new_alert_target_price = c2.number_input("Target Price", min_value=0.01, format="%.2f")

    # Using selectbox for clearer above/below condition
    # True for 'Price >= Target', False for 'Price <= Target'
    trigger_options = {"Price >= Target": True, "Price <= Target": False}
    selected_trigger_condition_str = c3.selectbox(
        "Trigger Condition",
        options=list(trigger_options.keys()),
        index=0 # Default to Price >= Target
    )
    new_alert_trigger_when_above = trigger_options[selected_trigger_condition_str]

    new_alert_desc = st.text_input("Description (Optional, e.g., 'Buy signal for Reliance')")

    create_alert_submitted = st.form_submit_button("Create Alert")
    if create_alert_submitted:
        handle_create_alert(new_alert_symbol, new_alert_target_price, new_alert_trigger_when_above, new_alert_desc)

st.markdown("---")

# --- Display Alerts ---
st.subheader("Your Alerts")

# Filters
filter_col1, filter_col2 = st.columns(2)
filter_symbol = filter_col1.text_input("Filter by Symbol (Optional):").upper()
filter_active_status = filter_col2.selectbox(
    "Filter by Status (Optional):",
    options=["All", "Active", "Inactive/Triggered"],
    index=0
)

is_active_param = None
if filter_active_status == "Active":
    is_active_param = True
elif filter_active_status == "Inactive/Triggered":
    is_active_param = False

alerts = api_client.get_alerts(symbol=filter_symbol if filter_symbol else None, is_active=is_active_param)

if alerts is not None:
    if not alerts:
        st.info("No alerts found matching your criteria. Create some alerts to monitor your favorite stocks!")
    else:
        alerts_data_for_df = []
        for alert in alerts:
            condition = ""
            if alert.get('alert_type') == 'price':
                operator = ">=" if alert.get('trigger_when_above') else "<="
                condition = f"Price {operator} {alert.get('target_price', 'N/A')}"
            else:
                condition = f"Type: {alert.get('alert_type', 'N/A')}" # Fallback for other types

            alerts_data_for_df.append({
                "ID": alert['id'],
                "Symbol": alert['symbol'],
                "Condition": condition,
                "Description": alert.get('description', ''),
                "Status": "Active" if alert['is_active'] else ("Triggered" if alert.get('triggered_at') else "Inactive"),
                "Created At": datetime.fromisoformat(alert['created_at']).strftime('%Y-%m-%d %H:%M') if alert.get('created_at') else 'N/A',
                "Triggered At": datetime.fromisoformat(alert['triggered_at']).strftime('%Y-%m-%d %H:%M') if alert.get('triggered_at') else 'N/A',
                "_raw_alert": alert # Store raw for editing
            })

        alerts_df = pd.DataFrame(alerts_data_for_df)

        # Displaying alerts - consider st.data_editor for more interactive table if needed
        # For now, use st.dataframe and manage edits via expanders/forms below selected alert

        for index, row in alerts_df.iterrows():
            raw_alert = row["_raw_alert"]
            with st.expander(f"{row['Symbol']}: {row['Condition']} (Status: {row['Status']})"):
                st.caption(f"ID: {row['ID']} | Created: {row['Created At']} | Triggered: {row['Triggered At']}")
                if row['Description']:
                    st.markdown(f"**Description:** {row['Description']}")

                # Edit form for this alert
                with st.form(key=f"edit_alert_form_{raw_alert['id']}"):
                    st.write(f"**Edit Alert ID: {raw_alert['id']}** ({raw_alert['symbol']})")

                    edit_target_price = st.number_input(
                        "New Target Price",
                        value=float(raw_alert.get('target_price', 0.0)),
                        min_value=0.0,
                        format="%.2f",
                        key=f"edit_price_{raw_alert['id']}"
                    )

                    current_trigger_above = raw_alert.get('trigger_when_above', True)
                    edit_trigger_options_map = {"Price >= Target": True, "Price <= Target": False}
                    # Find current index for selectbox
                    current_trigger_str = [k for k, v in edit_trigger_options_map.items() if v == current_trigger_above][0]

                    edit_selected_trigger_str = st.selectbox(
                        "New Trigger Condition",
                        options=list(edit_trigger_options_map.keys()),
                        index=list(edit_trigger_options_map.keys()).index(current_trigger_str),
                        key=f"edit_cond_{raw_alert['id']}"
                    )
                    edit_trigger_when_above = edit_trigger_options_map[edit_selected_trigger_str]

                    edit_description = st.text_input(
                        "New Description",
                        value=raw_alert.get('description',''),
                        key=f"edit_desc_{raw_alert['id']}"
                    )
                    edit_is_active = st.checkbox(
                        "Is Active?",
                        value=raw_alert.get('is_active', True),
                        key=f"edit_active_{raw_alert['id']}"
                    )

                    col_update, col_delete, col_spacer = st.columns([1,1,3])
                    if col_update.form_submit_button("Save Changes"):
                        handle_update_alert(
                            raw_alert['id'],
                            edit_target_price,
                            edit_trigger_when_above,
                            edit_is_active,
                            edit_description
                        )
                    if col_delete.form_submit_button("Delete Alert"):
                        # TODO: Confirmation dialog
                        handle_delete_alert(raw_alert['id'])
else:
    st.warning("Could not load alerts from the backend.")


st.markdown("---")
st.caption("Alerts are checked by a backend process. This panel is for managing your alert definitions.")
st.caption("Currently, only price-based alerts are supported via this UI.")
# TODO:
# - Implement "Notification" display part (e.g., list of recently triggered alerts, perhaps via a separate endpoint or websocket).
# - Add confirmation dialogs for delete actions.
# - Support for other alert types (e.g., indicator-based) if backend supports them.
# - UI improvements for editing (e.g., modal-like forms).

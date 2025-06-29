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

st.set_page_config(layout="wide", page_title="Portfolio Dashboard")
st.title("💰 Portfolio Dashboard")
st.caption("Manage your investment portfolios and track their performance.")

# --- Session State Initialization ---
if 'selected_portfolio_id' not in st.session_state:
    st.session_state.selected_portfolio_id = None
if 'editing_portfolio' not in st.session_state: # To control edit form visibility
    st.session_state.editing_portfolio = None # Stores portfolio data for editing or None
if 'editing_holding' not in st.session_state:
    st.session_state.editing_holding = None # Stores holding data for editing or None


# --- Helper Functions ---
def refresh_portfolio_data():
    """Clears relevant caches and resets selection to force reload."""
    api_client.get_portfolios.clear()
    if st.session_state.selected_portfolio_id:
        api_client.get_portfolio_details.clear()
    # st.session_state.selected_portfolio_id = None # Optionally reset selection
    st.experimental_rerun()

def handle_create_portfolio(name, description):
    if not name:
        st.warning("Portfolio name cannot be empty.")
        return
    created = api_client.create_portfolio(name, description)
    if created:
        st.success(f"Portfolio '{created['name']}' created successfully!")
        refresh_portfolio_data()
    # Error is handled by api_client displaying st.error

def handle_update_portfolio(portfolio_id, name, description):
    if not name: # Basic validation
        st.sidebar.warning("Portfolio name cannot be empty for update.")
        return
    updated = api_client.update_portfolio(portfolio_id, name, description)
    if updated:
        st.sidebar.success(f"Portfolio '{updated['name']}' updated.")
        st.session_state.editing_portfolio = None # Close edit form
        refresh_portfolio_data()

def handle_delete_portfolio(portfolio_id):
    # Add confirmation dialog
    # For now, direct delete:
    if api_client.delete_portfolio(portfolio_id):
        st.success(f"Portfolio ID {portfolio_id} deleted.")
        if st.session_state.selected_portfolio_id == portfolio_id:
            st.session_state.selected_portfolio_id = None
        refresh_portfolio_data()

def handle_add_or_update_holding(portfolio_id, symbol, quantity, avg_price, existing_holding=None):
    if not symbol or quantity <= 0 or avg_price < 0:
        st.warning("Invalid holding data. Ensure symbol is provided, quantity > 0, and price >= 0.")
        return

    success = api_client.add_or_update_holding(portfolio_id, symbol, quantity, avg_price)
    if success:
        action = "updated" if existing_holding else "added"
        st.success(f"Holding '{symbol}' {action} successfully in portfolio ID {portfolio_id}.")
        st.session_state.editing_holding = None # Close form
        api_client.get_portfolio_details.clear() # Clear specific cache
        st.experimental_rerun() # Rerun to show updated holdings

def handle_remove_holding(portfolio_id, symbol):
    if api_client.remove_holding(portfolio_id, symbol):
        st.success(f"Holding '{symbol}' removed from portfolio ID {portfolio_id}.")
        api_client.get_portfolio_details.clear()
        st.experimental_rerun()

# --- Sidebar: Portfolio List and Creation ---
st.sidebar.header("Your Portfolios")
portfolios = api_client.get_portfolios()

if portfolios is not None:
    if not portfolios:
        st.sidebar.info("No portfolios found. Create one to get started!")
    else:
        # Ensure selected_portfolio_id is valid if portfolios list changes
        portfolio_ids = [p['id'] for p in portfolios]
        if st.session_state.selected_portfolio_id not in portfolio_ids:
            st.session_state.selected_portfolio_id = None # Reset if selected ID is no longer valid
            if portfolio_ids: # Select first one if available
                 st.session_state.selected_portfolio_id = portfolio_ids[0]


        # Use radio buttons for portfolio selection
        # This also helps in visually indicating the selected one.
        # We need to map portfolio IDs to their names for display.
        portfolio_options = {p['id']: f"{p['name']} (ID: {p['id']})" for p in portfolios}

        # Get current index of selected_portfolio_id for radio button
        current_selection_index = 0
        if st.session_state.selected_portfolio_id and st.session_state.selected_portfolio_id in portfolio_ids:
            current_selection_index = portfolio_ids.index(st.session_state.selected_portfolio_id)

        selected_id_radio = st.sidebar.radio(
            "Select Portfolio:",
            options=portfolio_ids,
            format_func=lambda id: portfolio_options[id],
            index=current_selection_index,
            key="portfolio_selector_radio" # Unique key for radio
        )
        if selected_id_radio != st.session_state.selected_portfolio_id:
            st.session_state.selected_portfolio_id = selected_id_radio
            api_client.get_portfolio_details.clear() # Clear cache for new selection
            st.experimental_rerun()


# --- Create New Portfolio Form (Sidebar) ---
with st.sidebar.expander("➕ Create New Portfolio", expanded=not bool(portfolios)):
    with st.form("create_portfolio_form"):
        new_portfolio_name = st.text_input("Portfolio Name")
        new_portfolio_desc = st.text_area("Description (Optional)")
        create_submitted = st.form_submit_button("Create Portfolio")
        if create_submitted:
            handle_create_portfolio(new_portfolio_name, new_portfolio_desc)


# --- Main Area: Display Selected Portfolio Details ---
if st.session_state.selected_portfolio_id is not None:
    portfolio_id = st.session_state.selected_portfolio_id
    portfolio_details = api_client.get_portfolio_details(portfolio_id)

    if portfolio_details:
        st.subheader(f"Displaying: {portfolio_details['name']}")
        st.caption(f"ID: {portfolio_details['id']} | User ID: {portfolio_details['user_id']} (dummy)")
        if portfolio_details['description']:
            st.markdown(f"**Description:** {portfolio_details['description']}")

        # Edit/Delete Portfolio Actions
        col1, col2, col3 = st.columns([1,1,5])
        if col1.button("✏️ Edit Portfolio Name/Desc"):
            st.session_state.editing_portfolio = portfolio_details # Store details for edit form
            st.experimental_rerun()
        if col2.button(f"🗑️ Delete '{portfolio_details['name']}'"):
            # TODO: Add proper confirmation dialog here
            handle_delete_portfolio(portfolio_id)


        # --- Edit Portfolio Form (Modal-like behavior in sidebar or expander) ---
        if st.session_state.editing_portfolio and st.session_state.editing_portfolio['id'] == portfolio_id:
            with st.expander(f"✏️ Editing Portfolio: {st.session_state.editing_portfolio['name']}", expanded=True):
                with st.form("edit_portfolio_form"):
                    st.write(f"Editing ID: {st.session_state.editing_portfolio['id']}")
                    edit_name = st.text_input("New Name", value=st.session_state.editing_portfolio['name'])
                    edit_desc = st.text_area("New Description", value=st.session_state.editing_portfolio.get('description', ''))

                    col_save, col_cancel = st.columns(2)
                    if col_save.form_submit_button("Save Changes"):
                        handle_update_portfolio(portfolio_id, edit_name, edit_desc)
                    if col_cancel.form_submit_button("Cancel"):
                        st.session_state.editing_portfolio = None
                        st.experimental_rerun()

        st.markdown("---")
        st.subheader("Holdings")

        holdings = portfolio_details.get('holdings', [])
        if holdings:
            # Create a DataFrame for display
            holdings_df_data = []
            for h in holdings:
                current_price = h.get('current_price', 'N/A') # Assuming enrichment from backend
                current_value = h.get('current_value', 0)
                pnl = h.get('profit_loss', 0)
                pnl_percent = h.get('profit_loss_percent', 0)

                holdings_df_data.append({
                    "Symbol": h['symbol'],
                    "Quantity": h['quantity'],
                    "Avg. Buy Price": f"{h['average_buy_price']:.2f}",
                    "Invested Value": f"{(h['quantity'] * h['average_buy_price']):.2f}",
                    # "Current Price": f"{current_price:.2f}" if isinstance(current_price, float) else current_price,
                    # "Current Value": f"{current_value:.2f}" if isinstance(current_value, float) else "N/A",
                    # "P&L": f"{pnl:.2f}" if isinstance(pnl, float) else "N/A",
                    # "P&L %": f"{pnl_percent:.2f}%" if isinstance(pnl_percent, float) else "N/A",
                    "Actions": f"Edit-{h['symbol']}|Remove-{h['symbol']}" # Placeholder for buttons
                })

            holdings_df = pd.DataFrame(holdings_df_data)

            # Displaying with st.data_editor for potential inline edits (more complex)
            # For now, simple display and separate forms for edit/delete actions
            st.dataframe(holdings_df.set_index("Symbol"), use_container_width=True)

            # Action buttons per row (more complex to implement directly in dataframe)
            # Alternative: Select a holding to edit/remove below the table
            for i, holding_row_data in enumerate(holdings):
                cols_action = st.columns([0.2, 1, 1, 5]) # Symbol | Edit | Delete | Spacer
                cols_action[0].write(holding_row_data['symbol'])
                if cols_action[1].button("✏️", key=f"edit_holding_{holding_row_data['symbol']}_{portfolio_id}", help=f"Edit {holding_row_data['symbol']}"):
                    st.session_state.editing_holding = holding_row_data
                    st.session_state.editing_holding['portfolio_id'] = portfolio_id # Add portfolio_id for context
                    st.experimental_rerun()
                if cols_action[2].button("🗑️", key=f"remove_holding_{holding_row_data['symbol']}_{portfolio_id}", help=f"Remove {holding_row_data['symbol']}"):
                    handle_remove_holding(portfolio_id, holding_row_data['symbol'])


            # --- Edit Holding Form (Modal-like) ---
            if st.session_state.editing_holding and st.session_state.editing_holding.get('portfolio_id') == portfolio_id:
                eh = st.session_state.editing_holding
                with st.expander(f"✏️ Editing Holding: {eh['symbol']}", expanded=True):
                    with st.form(f"edit_holding_form_{eh['symbol']}"):
                        st.write(f"Editing **{eh['symbol']}** in portfolio '{portfolio_details['name']}'")
                        edit_h_qty = st.number_input("Quantity", value=float(eh['quantity']), min_value=0.0, format="%.4f")
                        edit_h_avg_price = st.number_input("Average Buy Price", value=float(eh['average_buy_price']), min_value=0.0, format="%.2f")

                        h_save, h_cancel = st.columns(2)
                        if h_save.form_submit_button("Save Holding"):
                            handle_add_or_update_holding(portfolio_id, eh['symbol'], edit_h_qty, edit_h_avg_price, existing_holding=True)
                        if h_cancel.form_submit_button("Cancel Edit"):
                            st.session_state.editing_holding = None
                            st.experimental_rerun()

        else:
            st.info("This portfolio has no holdings yet. Add some below.")

        # --- Add New Holding Form ---
        if not st.session_state.editing_holding: # Show only if not editing another holding
            with st.expander("➕ Add New Holding to Portfolio", expanded=not bool(holdings)):
                with st.form("add_holding_form"):
                    st.write(f"Adding to portfolio: **{portfolio_details['name']}**")
                    new_h_symbol = st.text_input("Stock Symbol (e.g., RELIANCE.NS)").upper()
                    new_h_qty = st.number_input("Quantity", min_value=0.0001, value=1.0, format="%.4f")
                    new_h_avg_price = st.number_input("Average Buy Price", min_value=0.0, value=100.0, format="%.2f")

                    add_h_submitted = st.form_submit_button("Add Holding")
                    if add_h_submitted:
                        handle_add_or_update_holding(portfolio_id, new_h_symbol, new_h_qty, new_h_avg_price)

        # --- Portfolio Summary ---
        st.markdown("---")
        st.subheader("Portfolio Summary")
        total_invested = portfolio_details.get('total_invested_value', 0.0)
        # current_total_value = portfolio_details.get('current_total_value', 0.0) # Needs live data
        # overall_pnl = portfolio_details.get('overall_profit_loss', 0.0)
        # overall_pnl_percent = portfolio_details.get('overall_profit_loss_percent', 0.0)

        st.metric("Total Invested Value", f"₹{total_invested:,.2f}")
        st.info("Live current value and P&L calculations require real-time market data integration (future enhancement).")

    elif portfolio_details is None and portfolio_id is not None: # Error case from API client
        st.error(f"Could not load details for Portfolio ID {portfolio_id}. It might have been deleted or there was a server error.")
        st.button("Clear Selection and Refresh Portfolios", on_click=lambda: setattr(st.session_state, 'selected_portfolio_id', None) or refresh_portfolio_data())


else:
    st.info("Select a portfolio from the sidebar to view its details, or create a new one.")

st.markdown("---")
st.caption("Portfolio data is managed via the backend API. Assumes a dummy user for now.")
# TODO:
# - Implement live price fetching for holdings to calculate current values and P&L.
# - User authentication integration.
# - More sophisticated UI for editing/deleting holdings (e.g., in-table actions or modal dialogs).
# - Visualizations for portfolio allocation, performance over time.
# - Error handling and user feedback improvements.
# - Proper confirmation dialogs for delete operations.

import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# ==========================================
# 1. PASTE YOUR GOOGLE SHEET LINK HERE
# ==========================================
SHEET_URL = "https://docs.google.com/spreadsheets/d/1QBuZ5NV97NfdinHjesf0KB5436p1k3Xp7cZ8VAXtcGk/edit?gid=0#gid=0"

# ==========================================
# 2. SETUP GOOGLE SHEETS CONNECTION
# ==========================================
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    # We now explicitly tell Streamlit WHICH spreadsheet to open
    df = conn.read(spreadsheet=SHEET_URL, worksheet="FC Closure")
except Exception as e:
    st.error(f"Failed to connect to Google Sheets. Error: {e}")
    st.stop()

# ==========================================
# 3. SESSION STATE FOR LOGIN
# ==========================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_id" not in st.session_state:
    st.session_state.user_id = ""

st.title("📦 FC Task Management App")

# ==========================================
# 4. LOGIN SCREEN
# ==========================================
if not st.session_state.logged_in:
    st.subheader("Employee Login")
    user_input = st.text_input("Enter your Employee Email / ID:")
    login_btn = st.button("Log In")
    
    if login_btn and user_input:
        st.session_state.logged_in = True
        st.session_state.user_id = user_input.strip()
        st.rerun()

# ==========================================
# 5. MAIN APP INTERFACE (LOGGED IN)
# ==========================================
else:
    st.sidebar.write(f"Logged in as: **{st.session_state.user_id}**")
    if st.sidebar.button("Log Out"):
        st.session_state.logged_in = False
        st.session_state.user_id = ""
        st.rerun()

    is_admin = st.session_state.user_id.lower() == "admin@company.com" 

    # Validate essential columns exist
    required_cols = ['Assign to', 'Quantity Picked', 'Status']
    for col in required_cols:
        if col not in df.columns:
            st.error(f"Missing column in Google Sheet: '{col}'. Please add it to row 1.")
            st.stop()

    # --- ADMIN VIEW ---
    if is_admin:
        st.subheader("Admin Dashboard")
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(label="Download Complete Task Report (CSV)", data=csv, file_name="FC_Closure_Report.csv", mime="text/csv")
        st.write("All Tasks Status:")
        st.dataframe(df)

    # --- EMPLOYEE VIEW ---
    else:
        st.subheader("Your Task Dashboard")
        
        # Filter ALL tasks for the logged-in ID
        employee_tasks = df[df['Assign to'].astype(str).str.lower() == st.session_state.user_id.lower()]

        if employee_tasks.empty:
            st.info("No tasks are currently assigned to this ID.")
        else:
            pending_tasks = employee_tasks[employee_tasks['Status'].astype(str).str.title() != 'Completed']
            completed_tasks = employee_tasks[employee_tasks['Status'].astype(str).str.title() == 'Completed']

            st.write(f"### ⏳ Pending Tasks ({len(pending_tasks)})")
            
            if pending_tasks.empty:
                st.success("🎉 You are all caught up! No pending tasks.")
            else:
                for idx, row in pending_tasks.iterrows():
                    with st.container(border=True):
                        st.write(f"**Product:** {row.get('Product', 'N/A')} | **Location:** {row.get('Location', 'N/A')}")
                        st.write(f"**SKU:** {row.get('SKU', 'N/A')} | **Target Quantity:** {row.get('Quantity', 'N/A')}")
                        
                        picked_qty = st.number_input("Enter Quantity Picked:", min_value=0, step=1, key=f"qty_{idx}")
                        
                        if st.button("Submit & Complete", key=f"btn_{idx}"):
                            try:
                                # Update the local dataframe
                                df.at[idx, 'Quantity Picked'] = picked_qty
                                df.at[idx, 'Status'] = 'Completed'
                                
                                # Push the entire updated dataframe back to Google Sheets (Added the SHEET_URL here too)
                                conn.update(spreadsheet=SHEET_URL, worksheet="FC Closure", data=df)
                                
                                st.toast(f"Saved: Picked {picked_qty} items!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Could not update sheet: {e}")

            st.write("---")
            st.write(f"### ✅ Completed Tasks ({len(completed_tasks)})")
            
            if not completed_tasks.empty:
                display_df = completed_tasks[['Product', 'SKU', 'Location', 'Quantity', 'Quantity Picked']]
                st.dataframe(display_df, use_container_width=True)
            else:
                st.write("No completed tasks yet.")

st.divider()
st.markdown("<p style='text-align: center; color: gray;'>© 2026 Developed by Gyana Prakash Rout</p>", unsafe_allow_html=True)

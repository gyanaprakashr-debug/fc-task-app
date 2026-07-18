import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd

# ==========================================
# 1. SETUP GOOGLE SHEETS CONNECTION & DEBUGGER
# ==========================================
def init_connection():
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
    except Exception as e:
        st.error("Could not find [gcp_service_account] in Streamlit secrets. Please check your secrets.toml formatting.")
        st.stop()
    
    # 🚨 THE ULTIMATE KEY FIXER 🚨
    # This covers every possible way Streamlit might mangle the newlines
    raw_key = creds_dict.get("private_key", "")
    
    if "\\n" in raw_key:
        raw_key = raw_key.replace("\\n", "\n")
    
    creds_dict["private_key"] = raw_key

    # --- DIAGNOSTIC CHECK ---
    # We will check the key structure before even sending it to Google
    if not raw_key.startswith("-----BEGIN PRIVATE KEY-----"):
        st.error("Diagnotic Error: Your private key does not start with '-----BEGIN PRIVATE KEY-----'. It might be cut off.")
        st.stop()
    if not raw_key.strip().endswith("-----END PRIVATE KEY-----"):
        st.error("Diagnostic Error: Your private key does not end with '-----END PRIVATE KEY-----'. It might be cut off.")
        st.stop()
    if "\n" not in raw_key:
        st.error("Diagnostic Error: Your private key has no line breaks. Streamlit is reading it as one giant string.")
        st.stop()
    
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    
    try:
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        sheet = client.open("FC Closure").sheet1 
        return sheet
    except Exception as e:
        st.error(f"Authentication Failed. Google rejected the key. Error: {e}")
        st.info("Checklist: Did you generate a brand new key? Does the 'client_email' exactly match the email for that specific key?")
        st.stop()

# Initialize connection
sheet = init_connection()

# ==========================================
# 2. SESSION STATE FOR LOGIN
# ==========================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_id" not in st.session_state:
    st.session_state.user_id = ""

st.title("📦 FC Task Management App")

# ==========================================
# 3. LOGIN SCREEN
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
# 4. MAIN APP INTERFACE (LOGGED IN)
# ==========================================
else:
    st.sidebar.write(f"Logged in as: **{st.session_state.user_id}**")
    if st.sidebar.button("Log Out"):
        st.session_state.logged_in = False
        st.session_state.user_id = ""
        st.rerun()

    is_admin = st.session_state.user_id.lower() == "admin@company.com" 

    raw_data = sheet.get_all_records()
    df = pd.DataFrame(raw_data)

    required_cols = ['Assign to', 'Quantity Picked', 'Status']
    for col in required_cols:
        if col not in df.columns:
            st.error(f"Missing column in Google Sheet: '{col}'. Please add it to row 1.")
            st.stop()

    if is_admin:
        st.subheader("Admin Dashboard")
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(label="Download Complete Task Report (CSV)", data=csv, file_name="FC_Closure_Report.csv", mime="text/csv")
        st.write("All Tasks Status:")
        st.dataframe(df)

    else:
        st.subheader("Your Task Dashboard")
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
                        sheet_row_index = idx + 2 
                        
                        if st.button("Submit & Complete", key=f"btn_{idx}"):
                            try:
                                qty_col_index = df.columns.get_loc('Quantity Picked') + 1
                                status_col_index = df.columns.get_loc('Status') + 1
                                sheet.update_cell(sheet_row_index, qty_col_index, picked_qty)
                                sheet.update_cell(sheet_row_index, status_col_index, "Completed")
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

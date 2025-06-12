import streamlit as st
import pandas as pd
import requests
import io
from datetime import datetime
from requests.auth import HTTPBasicAuth

# --- Remove Streamlit menu and GitHub icon ---
hide_streamlit_style = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# --- KoboToolbox API Configuration ---
username = "plotree"
password = "Pl@tr33@123"
form_uid = "aJHsRZXT3XEpCoxn9Ct3qZ"
api_url = f"https://kf.kobotoolbox.org/api/v2/assets/{form_uid}/data.json"
export_url = f"https://kf.kobotoolbox.org/api/v2/assets/{form_uid}/exports/"

# --- Fetch Data from KoboToolbox ---
@st.cache_data(ttl=3600)
def load_data():
    response = requests.get(api_url, auth=HTTPBasicAuth(username, password))
    if response.status_code == 200:
        data = response.json().get("results", [])
        return pd.DataFrame(data)
    else:
        st.error("Failed to load data from KoboToolbox.")
        return pd.DataFrame()

# --- Trigger KoboToolbox Export ---
def trigger_kobo_export(export_type="xls"):
    headers = {'Authorization': f'Token {password}'}
    payload = {
        "type": export_type,
        "fields_from_all_versions": "true",
        "group_sep": "/",
        "hierarchy_in_labels": "true",
        "include_media_urls": "true",
        "lang": "English"
    }
    response = requests.post(export_url, headers=headers, json=payload)
    if response.status_code == 201:
        return response.json().get('url')
    return None

# --- Check Export Status ---
def check_export_status(export_url):
    headers = {'Authorization': f'Token {password}'}
    response = requests.get(export_url, headers=headers)
    if response.status_code == 200:
        return response.json().get('status'), response.json().get('result')
    return None, None

# --- Main App ---
df = load_data()

if df.empty:
    st.stop()

# --- Data Preparation ---
# Standardize column names
col_mapping = {
    "username": "username",
    "_1_1_Name_of_the_City_": "district",
    "_geolocation_latitude": "latitude",
    "_geolocation_longitude": "longitude"
}

for orig, new in col_mapping.items():
    if orig in df.columns:
        df = df.rename(columns={orig: new})

# --- Dashboard Filters ---
# [Previous filter code remains exactly the same...]

# --- Data Download Section ---
st.subheader("📥 Download Data")

# Option 1: Direct KoboToolbox Export
st.markdown("### KoboToolbox Standard Export")
st.write("Get data in exact KoboToolbox format (may take a few minutes)")

if st.button("Generate KoboToolbox Export"):
    with st.spinner("Requesting export from KoboToolbox..."):
        export_url = trigger_kobo_export("xls")
        
        if export_url:
            st.session_state.export_url = export_url
            st.success("Export requested! Checking status...")
            
            # Check status periodically
            status = "created"
            while status not in ["complete", "error"]:
                status, result_url = check_export_status(export_url)
                if status == "complete":
                    st.success("Export ready for download!")
                    st.markdown(f"""
                    [Download XLS Export](https://kf.kobotoolbox.org{result_url})
                    """, unsafe_allow_html=True)
                    break
                elif status == "error":
                    st.error("Export failed. Please try again.")
                    break
                else:
                    st.write(f"Status: {status}...")
                    time.sleep(5)
        else:
            st.error("Failed to initiate export.")

# Option 2: Quick Export (modified to match Kobo structure)
st.markdown("### Quick Export")
st.write("Faster download with similar structure")

# Prepare data in Kobo-like format
def prepare_kobo_like_export(df):
    # Reorder columns to match Kobo's structure
    system_cols = ['_id', '_uuid', '_submission_time', '_validation_status', 
                  '_notes', '_status', '_submitted_by', '_tags', '_index', '__version__']
    
    # Get all columns in original order
    all_cols = df.columns.tolist()
    
    # Put system columns first (for those that exist)
    ordered_cols = [col for col in system_cols if col in all_cols]
    
    # Add remaining columns
    ordered_cols += [col for col in all_cols if col not in system_cols]
    
    return df[ordered_cols]

export_df = prepare_kobo_like_export(df)

col1, col2 = st.columns(2)

# CSV Download
csv = export_df.to_csv(index=False).encode('utf-8')
col1.download_button(
    "Download CSV (Kobo-like)",
    csv,
    "kobo_export.csv",
    "text/csv",
    help="CSV with Kobo-like column ordering"
)

# Excel Download
excel_io = io.BytesIO()
with pd.ExcelWriter(excel_io, engine='openpyxl') as writer:
    export_df.to_excel(writer, index=False, sheet_name='data')
    
    # Add media URLs sheet if available
    media_cols = [col for col in export_df.columns if any(x in col.lower() for x in ['url', 'image', 'photo'])]
    if media_cols:
        media_df = export_df[media_cols]
        media_df.to_excel(writer, sheet_name='media_urls', index=False)

col2.download_button(
    "Download Excel (Kobo-like)",
    excel_io.getvalue(),
    "kobo_export.xlsx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    help="Excel with Kobo-like structure"
)

# [Rest of your dashboard code remains the same...]

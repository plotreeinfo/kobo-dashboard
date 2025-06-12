import streamlit as st

# Remove Streamlit menu and GitHub icon
hide_streamlit_style = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

import pandas as pd
import plotly.express as px
import requests
import io
import numpy as np
from datetime import datetime
from requests.auth import HTTPBasicAuth

# --- CONFIGURE KOBO CONNECTION ---
username = "plotree"
password = "Pl@tr33@123"
form_uid = "aJHsRZXT3XEpCoxn9Ct3qZ"
api_url = f"https://kf.kobotoolbox.org/api/v2/assets/{form_uid}/data.json"

# --- FETCH DATA FROM KOBO ---
@st.cache_data(ttl=3600)
def load_data():
    response = requests.get(api_url, auth=HTTPBasicAuth(username, password))
    if response.status_code == 200:
        data = response.json().get("results", [])
        df = pd.DataFrame(data)
        
        # --- REMOVE UNWANTED SYSTEM COLUMNS ---
        system_columns = ['_id', '_uuid', '_submission_time', '_validation_status', 
                         '_notes', '_status', '_submitted_by', '_tags', '_index', '__version__']
        df = df.drop(columns=[col for col in system_columns if col in df.columns], errors='ignore')
        
        # --- FILTER COLUMNS: C to BO, skip BP–BV, include BY to end ---
        cols = df.columns.tolist()
        part1 = cols[2:67]     # C to BO
        part2 = cols[73:]      # BY to end
        selected_cols = part1 + part2

        return df[selected_cols]
    else:
        st.error("Failed to load data from KoboToolbox.")
        return pd.DataFrame()

# --- MAIN APP ---
df = load_data()

if df.empty:
    st.stop()

# --- DATA PREPARATION ---
# Standardize column names (adjust based on your actual column names)
col_mapping = {
    "username": "username",
    "_1_1_Name_of_the_City_": "district",
    "_geolocation_latitude": "latitude",
    "_geolocation_longitude": "longitude"
}

# Apply standardized column names
for orig, new in col_mapping.items():
    if orig in df.columns:
        df = df.rename(columns={orig: new})

# --- SIDEBAR FILTERS ---
st.sidebar.title("🔍 Dashboard Filters")

# ====================
# DATE FILTERS (REMOVED HOUR RANGE)
# ====================
with st.sidebar.expander("📅 Date Filters", expanded=True):
    if "submission_date" in df.columns:
        df["submission_date"] = pd.to_datetime(df["submission_date"])
        min_date = df["submission_date"].min().date()
        max_date = df["submission_date"].max().date()
        date_range = st.date_input(
            "Select Date Range", 
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date
        )
        
        if len(date_range) == 2:
            df = df[
                (df["submission_date"].dt.date >= date_range[0]) & 
                (df["submission_date"].dt.date <= date_range[1])
            ]

# ... [rest of your filters remain unchanged] ...

# --- DATA DOWNLOAD ---
st.subheader("📥 Download Data")

# Prepare download dataframe (already has system columns removed)
download_df = df.copy()

# Add media URLs if available
media_cols = [col for col in download_df.columns if any(x in col.lower() for x in ['url', 'image', 'photo'])]
if media_cols:
    media_df = download_df[media_cols]

# Excel Download with enhanced formatting
def generate_excel_export(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        # Main data sheet
        df.to_excel(writer, sheet_name='Data', index=False)
        
        # Media URLs sheet if available
        if media_cols:
            media_df.to_excel(writer, sheet_name='Media_URLs', index=False)
        
        # Metadata sheet
        metadata = pd.DataFrame({
            'Export Date': [datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
            'Total Records': [len(df)],
            'Data Collector': [selected_user if 'selected_user' in locals() else 'All'],
            'District': [selected_district if 'selected_district' in locals() else 'All']
        })
        metadata.to_excel(writer, sheet_name='Metadata', index=False)
        
        # Formatting
        workbook = writer.book
        header_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'fg_color': '#4472C4',
            'font_color': 'white',
            'border': 1
        })
        
        for sheet in writer.sheets:
            worksheet = writer.sheets[sheet]
            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_format)
            worksheet.autofit()
    
    return output.getvalue()

# Download buttons
col1, col2 = st.columns(2)

# CSV Download
csv = download_df.to_csv(index=False).encode('utf-8')
col1.download_button(
    "Download CSV", 
    csv, 
    "sanitation_data.csv", 
    "text/csv",
    help="Download as CSV with English headers"
)

# Excel Download
try:
    excel_data = generate_excel_export(download_df)
    col2.download_button(
        "Download Excel (XLSX)", 
        excel_data, 
        "sanitation_data.xlsx", 
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        help="Download with multiple sheets including media URLs"
    )
except Exception as e:
    st.error(f"Excel generation error: {str(e)}")
    # Fallback to simple Excel
    excel_io = io.BytesIO()
    download_df.to_excel(excel_io, index=False, engine='openpyxl')
    col2.download_button(
        "Download Excel", 
        excel_io.getvalue(), 
        "sanitation_data.xlsx", 
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# ... [rest of your dashboard code] ...

# app.py
import streamlit as st
import pandas as pd
import requests
from io import BytesIO

# KoboToolbox credentials
KOBO_USERNAME = "plotree"
KOBO_API_TOKEN = "04714621fa3d605ff0a4aa5cc2df7cfa961bf256"
FORM_UID = "aJHsRZXT3XEpCoxn9Ct3qZ"

# API endpoint configuration
EXPORT_URL = f"https://kf.kobotoolbox.org/api/v2/assets/{FORM_UID}/exports/"
EXPORT_PARAMS = {
    "format": "xls",
    "lang": "en",  # English headers & values
    "multiple_select": "both",  # Single and separate columns
    "include_all_versions": "false",  # Uncheck include fields from all versions
    "hierarchy_in_labels": "false",  # Uncheck include groups in headers
    "group_sep": "/",
    "date_format": "string",  # Store dates as text
    "numeric_format": "string",  # Store numbers as text
    "include_media_url": "true",  # Include media URLs
    "fields": "all",  # We'll filter columns after download
}

# Columns to exclude (as specified)
EXCLUDE_COLUMNS = [
    "start", "end", "_id", "_uuid", "_validation_status", 
    "_notes", "_status", "_submitted_by", "_tags", "__version__"
]

@st.cache_data(ttl=300, show_spinner="Downloading data from KoboToolbox...")
def fetch_kobo_data():
    """Fetch data from KoboToolbox API with specified export settings"""
    # Create export
    export_response = requests.post(
        EXPORT_URL,
        params=EXPORT_PARAMS,
        auth=(KOBO_USERNAME, KOBO_API_TOKEN)
    export_response.raise_for_status()
    
    # Get export result
    export_uid = export_response.json()['uid']
    result_url = f"{EXPORT_URL}{export_uid}/"
    
    # Wait for export to process
    while True:
        status_response = requests.get(result_url, auth=(KOBO_USERNAME, KOBO_API_TOKEN))
        status_data = status_response.json()
        if status_data['status'] == 'complete':
            break
    
    # Download data
    download_url = status_data['result']
    data_response = requests.get(download_url)
    data_response.raise_for_status()
    
    # Read Excel file
    df = pd.read_excel(BytesIO(data_response.content))
    
    # Filter columns
    cols_to_keep = [col for col in df.columns if col not in EXCLUDE_COLUMNS]
    return df[cols_to_keep]

# Streamlit app
st.title("KoboToolbox Data Viewer")
st.markdown(f"**Form UID:** `{FORM_UID}`")
st.write("### Data Export Settings Applied")
st.json(EXPORT_PARAMS)

try:
    df = fetch_kobo_data()
    
    # Display stats and data
    st.success(f"✅ Successfully loaded {len(df)} records")
    st.write(f"**Columns:** {', '.join(df.columns)}")
    
    with st.expander("Raw Data Preview", expanded=True):
        st.dataframe(df)
        
    with st.expander("Data Summary"):
        st.write(df.describe(include='all', datetime_is_numeric=False))
        
except requests.exceptions.HTTPError as e:
    st.error(f"🚨 API Error: {e.response.status_code} - {e.response.reason}")
except Exception as e:
    st.error(f"⚠️ Unexpected error: {str(e)}")

# Add refresh button
if st.button("🔄 Refresh Data"):
    st.cache_data.clear()
    st.experimental_rerun()

st.markdown("---")
st.info("ℹ️ Data is cached for 5 minutes. Use the refresh button to get latest data.")

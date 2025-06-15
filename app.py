# app.py
import streamlit as st
import pandas as pd
import requests
from io import StringIO

# KoboToolbox credentials
KOBO_USERNAME = "plotree"
KOBO_API_TOKEN = "04714621fa3d605ff0a4aa5cc2df7cfa961bf256"
FORM_UID = "aJHsRZXT3XEpCoxn9Ct3qZ"

# Direct CSV export URL (avoids complex export creation process)
EXPORT_URL = f"https://kf.kobotoolbox.org/api/v2/assets/{FORM_UID}/data.csv"

# Parameters matching your requirements
EXPORT_PARAMS = {
    "format": "csv",
    "lang": "en",                  # English headers & values
    "multiple_select": "both",      # Single and separate columns
    "include_all_versions": "false",# Uncheck include all versions
    "hierarchy_in_labels": "false", # Uncheck include groups in headers
    "group_sep": "/",
    "date_format": "string",        # Store dates as text
    "numeric_format": "string",     # Store numbers as text
    "include_media_url": "true",    # Include media URLs
}

# Columns to exclude
EXCLUDE_COLUMNS = [
    "start", "end", "_id", "_uuid", "_validation_status", 
    "_notes", "_status", "_submitted_by", "_tags", "__version__"
]

@st.cache_data(ttl=300, show_spinner="Downloading data from KoboToolbox...")
def fetch_kobo_data():
    """Fetch data directly as CSV from KoboToolbox API"""
    response = requests.get(
        EXPORT_URL,
        params=EXPORT_PARAMS,
        auth=(KOBO_USERNAME, KOBO_API_TOKEN),
        stream=True
    )
    response.raise_for_status()
    
    # Process CSV in chunks
    chunks = []
    for chunk in response.iter_content(chunk_size=8192, decode_unicode=True):
        chunks.append(chunk)
    
    # Combine chunks into single string
    csv_data = ''.join(chunks)
    
    # Read CSV data
    df = pd.read_csv(StringIO(csv_data))
    
    # Filter columns
    return df[[col for col in df.columns if col not in EXCLUDE_COLUMNS]]

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
        
    with st.expander("Sample Records"):
        st.write(df.head(5))
        
except requests.exceptions.HTTPError as e:
    st.error(f"🚨 API Error: {e.response.status_code} - {e.response.reason}")
    st.error("Please check your credentials and form UID")
except Exception as e:
    st.error(f"⚠️ Unexpected error: {str(e)}")

# Add refresh button
if st.button("🔄 Refresh Data"):
    st.cache_data.clear()
    st.experimental_rerun()

st.markdown("---")
st.info("ℹ️ Data is cached for 5 minutes. Use the refresh button to get latest data.")
st.info("💡 If the app gets stuck, try restarting it or check your internet connection")

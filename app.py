import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from datetime import datetime

# ==============================================
# CONFIGURATION
# ==============================================

st.set_page_config(layout="wide")
hide_streamlit_style = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# KoboToolbox credentials
KOBO_API_TOKEN = "04714621fa3d605ff0a4aa5cc2df7cfa961bf256"
FORM_UID = "aJHsRZXT3XEpCoxn9Ct3qZ"
BASE_URL = "https://kf.kobotoolbox.org"
API_URL = f"{BASE_URL}/api/v2/assets/{FORM_UID}/data.json"
EXPORT_URL = f"{BASE_URL}/api/v2/assets/{FORM_UID}/exports/"

# ==============================================
# KOBOTOOLBOX EXPORT FUNCTIONS
# ==============================================

def trigger_kobo_export(export_type="xlsx"):
    """Trigger export on KoboToolbox server"""
    headers = {
        "Authorization": f"Token {KOBO_API_TOKEN}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "type": export_type,
        "fields_from_all_versions": "true",
        "group_sep": "/",
        "hierarchy_in_labels": "true",
        "lang": "English"
    }
    
    try:
        response = requests.post(EXPORT_URL, headers=headers, json=payload)
        
        if response.status_code == 201:
            return response.json().get('url')
        else:
            st.error(f"Export failed (HTTP {response.status_code})")
            return None
    except Exception as e:
        st.error(f"Export error: {str(e)}")
        return None

def get_export_file(export_url):
    """Download exported file from KoboToolbox"""
    headers = {"Authorization": f"Token {KOBO_API_TOKEN}"}
    try:
        response = requests.get(export_url, headers=headers)
        if response.status_code == 200:
            return response.content
        return None
    except Exception as e:
        st.error(f"Download error: {str(e)}")
        return None

# ==============================================
# DATA FETCHING & PROCESSING
# ==============================================

@st.cache_data(ttl=3600)
def fetch_kobo_data():
    headers = {"Authorization": f"Token {KOBO_API_TOKEN}"}
    
    try:
        response = requests.get(API_URL, headers=headers, timeout=30)
        if response.status_code == 401:
            st.error("401 Unauthorized - Please verify your API token")
            return pd.DataFrame()
        
        data = response.json().get("results", [])
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Data fetch error: {str(e)}")
        return pd.DataFrame()

def clean_data(df):
    if df.empty:
        return df
    
    # Convert date columns
    for col in df.columns:
        if 'date' in col.lower():
            try:
                df[col] = pd.to_datetime(df[col], errors='coerce')
            except:
                pass
    return df

# ==============================================
# MAIN DASHBOARD
# ==============================================

def main():
    st.title("📊 KoboToolbox Analytics Dashboard")
    
    # Load data
    df = fetch_kobo_data()
    df = clean_data(df)
    
    # Export Tab
    with st.expander("⬇️ Direct Download from KoboToolbox", expanded=True):
        st.markdown("""
        ### Get original data directly from KoboToolbox
        These exports maintain all form structure and media attachments
        """)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("Export XLSX (Excel)"):
                with st.spinner("Generating Excel export..."):
                    export_url = trigger_kobo_export("xlsx")
                    if export_url:
                        file_content = get_export_file(export_url)
                        if file_content:
                            st.download_button(
                                label="Download Excel",
                                data=file_content,
                                file_name="kobo_export.xlsx",
                                mime="application/vnd.ms-excel"
                            )
        
        with col2:
            if st.button("Export CSV"):
                with st.spinner("Generating CSV export..."):
                    export_url = trigger_kobo_export("csv")
                    if export_url:
                        file_content = get_export_file(export_url)
                        if file_content:
                            st.download_button(
                                label="Download CSV",
                                data=file_content,
                                file_name="kobo_export.csv",
                                mime="text/csv"
                            )
        
        with col3:
            if st.button("Export SPSS"):
                with st.spinner("Generating SPSS export..."):
                    export_url = trigger_kobo_export("spss_labels")
                    if export_url:
                        file_content = get_export_file(export_url)
                        if file_content:
                            st.download_button(
                                label="Download SPSS",
                                data=file_content,
                                file_name="kobo_export.sav",
                                mime="application/octet-stream"
                            )
    
    # Data Preview
    if not df.empty:
        st.subheader("Data Preview")
        st.dataframe(df.head())
        
        # Visualizations would go here
        # ...
    else:
        st.warning("No data available")

if __name__ == "__main__":
    main()

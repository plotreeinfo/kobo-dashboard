import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import time
from datetime import datetime

# ==============================================
# YOUR ORIGINAL CONFIGURATION (UNCHANGED)
# ==============================================

hide_streamlit_style = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# YOUR CREDENTIALS (REPLACE WITH YOUR ACTUAL VALUES)
KOBO_API_TOKEN = "04714621fa3d605ff0a4aa5cc2df7cfa961bf256"
FORM_UID = "aJHsRZXT3XEpCoxn9Ct3qZ"
BASE_URL = "https://kf.kobotoolbox.org"

# API endpoints
API_URL = f"{BASE_URL}/api/v2/assets/{FORM_UID}/data.json"
EXPORT_URL = f"{BASE_URL}/api/v2/assets/{FORM_UID}/exports/"

# ==============================================
# FIXED DATA FETCHING WITH EXPORT FUNCTIONALITY
# ==============================================

@st.cache_data(ttl=3600)
def fetch_kobo_data():
    """Fetch data with Token authentication"""
    headers = {
        "Authorization": f"Token {KOBO_API_TOKEN}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(API_URL, headers=headers, timeout=30)
        
        if response.status_code == 401:
            st.error("Authentication Failed - Check API Token")
            return pd.DataFrame()
            
        response.raise_for_status()
        data = response.json().get("results", [])
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Data fetch error: {str(e)}")
        return pd.DataFrame()

def download_kobo_export(export_type="xlsx"):
    """Direct download from KoboToolbox with progress tracking"""
    headers = {"Authorization": f"Token {KOBO_API_TOKEN}"}
    
    try:
        # 1. Create export job
        payload = {
            "type": export_type,
            "fields_from_all_versions": "true",
            "lang": "English"
        }
        
        with st.spinner("Requesting export from KoboToolbox..."):
            response = requests.post(EXPORT_URL, headers=headers, json=payload)
            
            if response.status_code != 201:
                st.error(f"Export failed to start (HTTP {response.status_code})")
                return None
                
            export_uid = response.json().get('uid')
            if not export_uid:
                st.error("No export UID received")
                return None
        
        # 2. Check export status
        status_url = f"{EXPORT_URL}{export_uid}/"
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i in range(30):  # Max 30 checks (about 1 minute)
            status_response = requests.get(status_url, headers=headers)
            status_data = status_response.json()
            
            if status_data.get('status') == 'complete':
                progress_bar.progress(100)
                status_text.success("Export ready!")
                return status_data.get('result')
            elif status_data.get('status') in ('error', 'failed'):
                st.error(f"Export failed: {status_data.get('messages', 'Unknown error')}")
                return None
                
            progress_bar.progress((i + 1) * 3)
            status_text.text(f"Processing... ({3*(i+1)}%)")
            time.sleep(2)  # Check every 2 seconds
        
        st.error("Export timed out")
        return None
        
    except Exception as e:
        st.error(f"Export error: {str(e)}")
        return None

# ==============================================
# YOUR ORIGINAL DASHBOARD COMPONENTS (UNCHANGED)
# ==============================================

def clean_data(df):
    for col in df.columns:
        if 'date' in col.lower():
            try:
                df[col] = pd.to_datetime(df[col])
            except:
                pass
    return df

def create_filters(df):
    with st.sidebar:
        st.header("🔍 Filters")
        
        date_cols = [col for col in df.columns if 'date' in col.lower()]
        if date_cols:
            selected_date_col = st.selectbox("Filter by date", date_cols)
            min_date = df[selected_date_col].min()
            max_date = df[selected_date_col].max()
            
            date_range = st.date_input(
                "Date range",
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date
            )
            
            if len(date_range) == 2:
                df = df[
                    (df[selected_date_col] >= pd.to_datetime(date_range[0])) &
                    (df[selected_date_col] <= pd.to_datetime(date_range[1]))
                ]

        filter_col = st.selectbox("Filter by column", df.columns)
        if pd.api.types.is_numeric_dtype(df[filter_col]):
            min_val, max_val = float(df[filter_col].min()), float(df[filter_col].max())
            val_range = st.slider("Range", min_val, max_val, (min_val, max_val))
            df = df[df[filter_col].between(*val_range)]
        else:
            options = st.multiselect("Select values", df[filter_col].unique())
            if options:
                df = df[df[filter_col].isin(options)]
    return df

# ==============================================
# ENHANCED DASHBOARD WITH DOWNLOAD BUTTONS
# ==============================================

def main():
    st.title("📊 KoboToolbox Dashboard")
    
    # Load data
    df = fetch_kobo_data()
    df = clean_data(df)
    
    if df.empty:
        st.stop()
    
    # Apply filters
    df = create_filters(df)
    
    # Your original tabs layout
    tab1, tab2, tab3 = st.tabs(["Charts", "Data", "Download"])
    
    with tab1:
        col1, col2 = st.columns(2)
        
        with col1:
            cat_cols = [c for c in df.columns if df[c].nunique() < 10]
            if cat_cols:
                selected = st.selectbox("Pie Chart", cat_cols)
                fig = px.pie(df, names=selected)
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            if cat_cols:
                selected = st.selectbox("Bar Chart", cat_cols)
                fig = px.histogram(df, x=selected)
                st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        st.dataframe(df, height=600)
    
    with tab3:
        st.header("Direct Download from KoboToolbox")
        st.markdown("""
        Get the original data with all form structure intact.
        These exports match what you'd get from KoboToolbox web interface.
        """)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📥 Excel Export (XLSX)"):
                download_url = download_kobo_export("xlsx")
                if download_url:
                    st.success("Click below to download")
                    st.markdown(f"""
                    <a href="{download_url}" download="kobo_export.xlsx">
                        <button style="background-color:#4CAF50;color:white;padding:10px 20px;border:none;border-radius:5px;">
                            Download XLSX File
                        </button>
                    </a>
                    """, unsafe_allow_html=True)
        
        with col2:
            if st.button("📥 CSV Export"):
                download_url = download_kobo_export("csv")
                if download_url:
                    st.success("Click below to download")
                    st.markdown(f"""
                    <a href="{download_url}" download="kobo_export.csv">
                        <button style="background-color:#2196F3;color:white;padding:10px 20px;border:none;border-radius:5px;">
                            Download CSV File
                        </button>
                    </a>
                    """, unsafe_allow_html=True)
        
        with col3:
            if st.button("📥 SPSS Export"):
                download_url = download_kobo_export("spss_labels")
                if download_url:
                    st.success("Click below to download")
                    st.markdown(f"""
                    <a href="{download_url}" download="kobo_export.sav">
                        <button style="background-color:#9C27B0;color:white;padding:10px 20px;border:none;border-radius:5px;">
                            Download SPSS File
                        </button>
                    </a>
                    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()

import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import time
from datetime import datetime
from requests.auth import HTTPBasicAuth

# ==============================================
# CONFIGURATION (YOUR ORIGINAL STYLE)
# ==============================================

# Remove Streamlit menu and GitHub icon (your original style)
hide_streamlit_style = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# YOUR ORIGINAL CREDENTIALS (KEPT AS-IS)
KOBO_USERNAME = "plotree"
KOBO_API_TOKEN = "04714621fa3d605ff0a4aa5cc2df7cfa961bf256"
FORM_UID = "aJHsRZXT3XEpCoxn9Ct3qZ"
BASE_URL = "https://kf.kobotoolbox.org"

# API endpoints
API_URL = f"{BASE_URL}/api/v2/assets/{FORM_UID}/data.json"
EXPORT_URL = f"{BASE_URL}/api/v2/assets/{FORM_UID}/exports/"

# ==============================================
# YOUR ORIGINAL DATA FETCHING (UNCHANGED)
# ==============================================

@st.cache_data(ttl=3600)
def fetch_kobo_data():
    """Your original function with 401 fix"""
    try:
        response = requests.get(
            API_URL,
            auth=HTTPBasicAuth(KOBO_USERNAME, KOBO_API_TOKEN),
            timeout=30
        )
        
        if response.status_code == 401:
            st.error("Authentication Failed - Check API Token")
            return pd.DataFrame()
            
        response.raise_for_status()
        data = response.json().get("results", [])
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Data fetch error: {str(e)}")
        return pd.DataFrame()

# ==============================================
# YOUR ORIGINAL DASHBOARD COMPONENTS (UNCHANGED)
# ==============================================

def clean_data(df):
    """Your original date handling"""
    for col in df.columns:
        if 'date' in col.lower():
            try:
                df[col] = pd.to_datetime(df[col])
            except:
                pass
    return df

def create_filters(df):
    """Your original filter logic"""
    with st.sidebar:
        st.header("🔍 Filters")
        
        # Date filter
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

        # Column filters
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
# FIXED EXPORT FUNCTION (ONLY CHANGE MADE)
# ==============================================

def trigger_kobo_export(export_type="xlsx"):
    """Fixed version of your export function"""
    try:
        # Step 1: Initiate export
        headers = {
            'Authorization': f'Token {KOBO_API_TOKEN}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            "type": export_type,
            "fields_from_all_versions": "true"
        }
        
        response = requests.post(
            EXPORT_URL,
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code != 201:
            st.error(f"Export failed to start (HTTP {response.status_code})")
            return None
            
        # Step 2: Get download URL
        export_uid = response.json().get('uid')
        status_url = f"{EXPORT_URL}{export_uid}/"
        
        # Wait for export to complete
        with st.spinner("Preparing export..."):
            for _ in range(10):  # 10 attempts with 3s delay
                status_response = requests.get(status_url, headers=headers)
                if status_response.json().get('status') == 'complete':
                    download_url = status_response.json().get('result')
                    if download_url:
                        # Step 3: Download file
                        file_response = requests.get(download_url, headers=headers)
                        if file_response.status_code == 200:
                            return file_response.content
                time.sleep(3)
                
        st.error("Export timed out")
        return None
        
    except Exception as e:
        st.error(f"Export error: {str(e)}")
        return None

# ==============================================
# YOUR ORIGINAL DASHBOARD LAYOUT (UNCHANGED)
# ==============================================

def main():
    st.title("📊 Your KoboToolbox Dashboard")
    
    # Load data
    df = fetch_kobo_data()
    df = clean_data(df)
    
    if df.empty:
        st.warning("No data available")
        return
    
    # Apply filters
    df = create_filters(df)
    
    # Your original tabs layout
    tab1, tab2, tab3 = st.tabs(["Charts", "Data", "Export"])
    
    with tab1:
        # Your original charts
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
        # Fixed export buttons (only change)
        st.header("Export Data")
        
        if st.button("Export to Excel (XLSX)"):
            export_data = trigger_kobo_export("xlsx")
            if export_data:
                st.download_button(
                    label="Download XLSX",
                    data=export_data,
                    file_name="kobo_export.xlsx",
                    mime="application/vnd.ms-excel"
                )
        
        if st.button("Export to CSV"):
            export_data = trigger_kobo_export("csv")
            if export_data:
                st.download_button(
                    label="Download CSV",
                    data=export_data,
                    file_name="kobo_export.csv",
                    mime="text/csv"
                )

if __name__ == "__main__":
    main()

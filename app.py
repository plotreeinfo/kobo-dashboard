import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import json
import time
from datetime import datetime

# ==============================================
# CONFIGURATION
# ==============================================

hide_streamlit_style = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# YOUR CREDENTIALS (REPLACE WITH ACTUAL VALUES)
KOBO_API_TOKEN = "04714621fa3d605ff0a4aa5cc2df7cfa961bf256"
FORM_UID = "aJHsRZXT3XEpCoxn9Ct3qZ"
BASE_URL = "https://kf.kobotoolbox.org"

# API endpoints
API_URL = f"{BASE_URL}/api/v2/assets/{FORM_UID}/data.json"
EXPORT_URL = f"{BASE_URL}/api/v2/assets/{FORM_UID}/exports/"

# ==============================================
# FIXED EXPORT FUNCTION (SOLVES HTTP 400 ERROR)
# ==============================================

def handle_kobo_export(export_type):
    """Properly formatted export function that works with KoboToolbox API"""
    headers = {
        "Authorization": f"Token {KOBO_API_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # CORRECTLY FORMATTED PAYLOAD
    payload = {
        "type": export_type,
        "fields_from_all_versions": True,  # Must be boolean, not string
        "hierarchy_in_labels": True,       # Must be boolean, not string
        "group_sep": "/",
        "lang": "English"
    }
    
    try:
        # Step 1: Initiate export
        with st.spinner(f"Requesting {export_type.upper()} export..."):
            response = requests.post(
                EXPORT_URL,
                headers=headers,
                json=payload,  # Critical: use json= not data=
                timeout=30
            )
            
            if response.status_code == 400:
                st.error("""
                ❌ Bad Request - Verify:
                1. Your token has export permissions
                2. The form has submissions
                3. All boolean values are True/False (not "true"/"false")
                """)
                return None
                
            if response.status_code != 201:
                st.error(f"Export failed (HTTP {response.status_code})")
                return None
                
            export_uid = response.json().get('uid')
            if not export_uid:
                st.error("No export UID received")
                return None
        
        # Step 2: Wait for export to process
        status_url = f"{EXPORT_URL}{export_uid}/"
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i in range(10):  # 10 attempts with 3s delay (30s total)
            status_response = requests.get(status_url, headers=headers)
            
            if status_response.status_code != 200:
                st.error(f"Status check failed (HTTP {status_response.status_code})")
                return None
                
            status_data = status_response.json()
            
            if status_data.get('status') == 'complete':
                progress_bar.progress(100)
                status_text.success("Export ready!")
                return status_data.get('result')
            elif status_data.get('status') in ('error', 'failed'):
                st.error(f"Export processing failed: {status_data.get('messages', 'Unknown error')}")
                return None
                
            progress_bar.progress((i + 1) * 10)
            status_text.text(f"Processing... {(i + 1) * 10}%")
            time.sleep(3)
            
        st.error("Export timed out")
        return None
        
    except Exception as e:
        st.error(f"Export error: {str(e)}")
        return None

# ==============================================
# REST OF YOUR DASHBOARD CODE (UNCHANGED)
# ==============================================

@st.cache_data(ttl=3600)
def fetch_kobo_data():
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

def main():
    st.title("📊 KoboToolbox Dashboard")
    
    # Load data
    df = fetch_kobo_data()
    df = clean_data(df)
    
    if df.empty:
        st.stop()
    
    # Apply filters
    df = create_filters(df)
    
    # Your tabs layout
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
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📥 Excel Export (XLSX)"):
                download_url = handle_kobo_export("xlsx")
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
                download_url = handle_kobo_export("csv")
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
                download_url = handle_kobo_export("spss_labels")
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

import streamlit as st
import pandas as pd
import plotly.express as px
import requests
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
# SAFE DATA HANDLING FUNCTIONS
# ==============================================

def safe_nunique(series):
    """Count unique values safely for any column type"""
    try:
        return series.nunique()
    except TypeError:
        try:
            return len(series.astype(str).unique())
        except:
            return 0

@st.cache_data(ttl=3600)
def fetch_kobo_data():
    """Fetch data with comprehensive error handling"""
    headers = {
        "Authorization": f"Token {KOBO_API_TOKEN}",
        "Content-Type": "application/json"
    }
    
    try:
        # Verify asset exists first
        asset_url = f"{BASE_URL}/api/v2/assets/{FORM_UID}/"
        asset_response = requests.get(asset_url, headers=headers, timeout=10)
        
        if asset_response.status_code == 404:
            st.error("❌ Form not found - Check FORM_UID")
            return pd.DataFrame()
        
        # Fetch data
        data_response = requests.get(API_URL, headers=headers, timeout=30)
        
        if data_response.status_code == 401:
            st.error("""
            🔐 Authentication Failed - Verify:
            1. API Token is correct and recent
            2. You have 'View Submissions' permission
            3. FORM_UID matches your form's URL
            """)
            return pd.DataFrame()
            
        data_response.raise_for_status()
        data = data_response.json().get("results", [])
        
        if not data:
            st.warning("⚠️ Form exists but has no submissions yet")
            
        return pd.DataFrame(data)
        
    except Exception as e:
        st.error(f"🔌 Connection error: {str(e)}")
        return pd.DataFrame()

def clean_data(df):
    """Ensure all columns are safe for processing"""
    if df.empty:
        return df
    
    # Convert date columns
    for col in df.columns:
        if 'date' in col.lower():
            try:
                df[col] = pd.to_datetime(df[col], errors='coerce')
            except:
                pass
    
    # Ensure all columns are filterable
    for col in df.columns:
        try:
            if not pd.api.types.is_numeric_dtype(df[col]):
                df[col] = df[col].astype(str)
        except:
            df[col] = df[col].astype(str)
    
    return df

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
                1. Your token has export permissions (check at kf.kobotoolbox.org/token/)
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
# SAFE DASHBOARD COMPONENTS
# ==============================================

def create_filters(df):
    """Safe filter implementation"""
    if df.empty:
        return df
    
    with st.sidebar:
        st.header("🔍 Filters")
        
        # Date filter
        date_cols = [col for col in df.columns 
                    if pd.api.types.is_datetime64_any_dtype(df[col])]
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
            min_val = float(df[filter_col].min())
            max_val = float(df[filter_col].max())
            val_range = st.slider("Range", min_val, max_val, (min_val, max_val))
            df = df[df[filter_col].between(*val_range)]
        else:
            unique_vals = df[filter_col].dropna().unique()
            options = st.multiselect("Select values", unique_vals)
            if options:
                df = df[df[filter_col].isin(options)]
    
    return df

def create_visualizations(df):
    """Safe chart generation"""
    if df.empty:
        st.warning("No data available for visualizations")
        return
    
    tab1, tab2, tab3 = st.tabs(["Charts", "Data", "Download"])
    
    with tab1:
        # Get only columns that can be visualized
        cat_cols = [col for col in df.columns 
                   if safe_nunique(df[col]) < 20 
                   and safe_nunique(df[col]) > 0]
        
        if cat_cols:
            col1, col2 = st.columns(2)
            
            with col1:
                try:
                    selected = st.selectbox("Pie Chart Category", cat_cols)
                    fig = px.pie(df, names=selected)
                    st.plotly_chart(fig, use_container_width=True)
                except Exception as e:
                    st.error(f"Couldn't create pie chart: {str(e)}")
            
            with col2:
                try:
                    selected = st.selectbox("Bar Chart Category", cat_cols)
                    fig = px.histogram(df, x=selected)
                    st.plotly_chart(fig, use_container_width=True)
                except Exception as e:
                    st.error(f"Couldn't create bar chart: {str(e)}")
        
        # Numeric visualizations
        num_cols = df.select_dtypes(include=['number']).columns
        if len(num_cols) > 0:
            st.subheader("Numeric Data")
            selected = st.selectbox("Select numeric column", num_cols)
            try:
                fig = px.histogram(df, x=selected)
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.error(f"Couldn't create histogram: {str(e)}")
    
    with tab2:
        st.dataframe(df, height=600)
    
    with tab3:
        st.header("Direct Download from KoboToolbox")
        st.markdown("""
        Download original data with all form structure intact.
        These exports match what you'd get from the KoboToolbox web interface.
        """)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📥 Excel Export (XLSX)"):
                download_file("xlsx")
        
        with col2:
            if st.button("📥 CSV Export"):
                download_file("csv")
        
        with col3:
            if st.button("📥 SPSS Export"):
                download_file("spss_labels")

def download_file(export_type):
    """Handle the complete download process"""
    download_url = handle_kobo_export(export_type)
    if not download_url:
        return
    
    try:
        headers = {"Authorization": f"Token {KOBO_API_TOKEN}"}
        with st.spinner("Preparing download..."):
            response = requests.get(download_url, headers=headers)
            
            if response.status_code == 200:
                # Determine file extension and MIME type
                file_ext = "xlsx" if export_type == "xlsx" else "csv" if export_type == "csv" else "sav"
                mime_type = {
                    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    "csv": "text/csv",
                    "spss_labels": "application/octet-stream"
                }[export_type]
                
                st.download_button(
                    label=f"💾 Download {export_type.upper()}",
                    data=response.content,
                    file_name=f"kobo_export.{file_ext}",
                    mime=mime_type,
                    key=f"download_{export_type}"
                )
            else:
                st.error(f"Download failed (HTTP {response.status_code})")
    except Exception as e:
        st.error(f"Download error: {str(e)}")

# ==============================================
# MAIN APP
# ==============================================

def main():
    st.title("📊 KoboToolbox Dashboard")
    
    # Load and clean data
    df = fetch_kobo_data()
    df = clean_data(df)
    
    if df.empty:
        st.stop()
    
    # Apply filters
    df = create_filters(df)
    
    # Create visualizations
    create_visualizations(df)

if __name__ == "__main__":
    main()

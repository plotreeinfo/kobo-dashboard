import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import time
from datetime import datetime

# ==============================================
# CONFIGURATION (YOUR ORIGINAL STYLE)
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
# FIXED EXPORT FUNCTION (HTTP 400 SOLUTION)
# ==============================================

def handle_kobo_export(export_type):
    """Fixed export function that handles HTTP 400 errors"""
    headers = {
        "Authorization": f"Token {KOBO_API_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # CORRECTED PAYLOAD STRUCTURE
    payload = {
        "type": export_type,
        "fields_from_all_versions": True,  # Changed from string to boolean
        "hierarchy_in_labels": True,       # Changed from string to boolean
        "group_sep": "/",
        "lang": "English"
    }
    
    try:
        # Step 1: Initiate export
        with st.spinner(f"Creating {export_type.upper()} export..."):
            response = requests.post(
                EXPORT_URL,
                headers=headers,
                json=payload,  # Using json instead of data
                timeout=30
            )
            
            if response.status_code == 400:
                st.error("""
                ❌ Bad Request (400) - Common fixes:
                1. Ensure your token has export permissions
                2. Check the form has submissions
                3. Verify server URL is correct
                """)
                st.json(response.json())  # Show API error details
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
        
        for i in range(15):  # 15 attempts with 3s delay (45s total)
            status_response = requests.get(status_url, headers=headers)
            status_data = status_response.json()
            
            if status_data.get('status') == 'complete':
                progress_bar.progress(100)
                status_text.success("Export ready!")
                return status_data.get('result')
            elif status_data.get('status') in ('error', 'failed'):
                st.error(f"Export failed: {status_data.get('messages', 'Unknown error')}")
                return None
                
            progress_bar.progress((i + 1) * 7)  # Approximate progress
            status_text.text(f"Processing... {((i + 1) * 7)}%")
            time.sleep(3)
            
        st.error("Export timed out")
        return None
        
    except Exception as e:
        st.error(f"Export error: {str(e)}")
        return None

# ==============================================
# DASHBOARD COMPONENTS (WITH SAFETY CHECKS)
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
        st.markdown("Get original data with all form structure intact")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📥 Excel (XLSX)"):
                download_file("xlsx")
        
        with col2:
            if st.button("📥 CSV"):
                download_file("csv")
        
        with col3:
            if st.button("📥 SPSS"):
                download_file("spss_labels")

def download_file(export_type):
    """Handle the download process with progress"""
    download_url = handle_kobo_export(export_type)
    if download_url:
        try:
            headers = {"Authorization": f"Token {KOBO_API_TOKEN}"}
            with st.spinner("Preparing download..."):
                response = requests.get(download_url, headers=headers)
                
                if response.status_code == 200:
                    ext = "sav" if export_type == "spss_labels" else export_type
                    mime_types = {
                        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        "csv": "text/csv",
                        "spss_labels": "application/octet-stream"
                    }
                    
                    st.download_button(
                        label=f"Download {export_type.upper()}",
                        data=response.content,
                        file_name=f"kobo_export.{ext}",
                        mime=mime_types[export_type]
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

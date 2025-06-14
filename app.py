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

# YOUR CREDENTIALS
KOBO_API_TOKEN = "04714621fa3d605ff0a4aa5cc2df7cfa961bf256"
FORM_UID = "aJHsRZXT3XEpCoxn9Ct3qZ"
BASE_URL = "https://kf.kobotoolbox.org"

# ==============================================
# SAFE DATA FETCHING
# ==============================================

def fetch_kobo_data():
    """Fetch data with comprehensive error handling"""
    headers = {
        "Authorization": f"Token {KOBO_API_TOKEN}",
        "Content-Type": "application/json"
    }
    
    try:
        # First verify asset exists
        asset_url = f"{BASE_URL}/api/v2/assets/{FORM_UID}/"
        response = requests.get(asset_url, headers=headers, timeout=10)
        
        if response.status_code == 404:
            st.error("❌ Form not found - Check FORM_UID")
            return None
        
        # Then fetch data
        data_url = f"{BASE_URL}/api/v2/assets/{FORM_UID}/data.json"
        response = requests.get(data_url, headers=headers, timeout=30)
        
        if response.status_code == 401:
            st.error("🔐 Invalid API Token - Regenerate at: https://kf.kobotoolbox.org/token/")
            return None
            
        response.raise_for_status()
        return response.json().get("results", [])
        
    except Exception as e:
        st.error(f"🔌 Connection error: {str(e)}")
        return None

# ==============================================
# SAFE DATA PROCESSING
# ==============================================

def process_data(raw_data):
    """Convert to DataFrame with ultra-safe type handling"""
    if not raw_data:
        return pd.DataFrame()
    
    # Create DataFrame with all columns as strings initially
    df = pd.DataFrame(raw_data).astype(str)
    
    # Convert date columns safely
    for col in df.columns:
        if 'date' in col.lower():
            try:
                df[col] = pd.to_datetime(df[col], errors='coerce')
            except:
                continue
    
    # Convert numeric columns
    for col in df.columns:
        if not pd.api.types.is_datetime64_any_dtype(df[col]):
            try:
                df[col] = pd.to_numeric(df[col], errors='ignore')
            except:
                continue
    
    return df

# ==============================================
# SAFE COLUMN ANALYSIS
# ==============================================

def analyze_columns(df):
    """Categorize columns by type without using nunique()"""
    results = {
        'date_cols': [],
        'numeric_cols': [],
        'categorical_cols': [],
        'other_cols': []
    }
    
    if df.empty:
        return results
    
    for col in df.columns:
        # Check for datetime first
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            results['date_cols'].append(col)
            continue
        
        # Check for numeric
        if pd.api.types.is_numeric_dtype(df[col]):
            results['numeric_cols'].append(col)
            continue
        
        # For categorical, use value_counts (safer than unique)
        try:
            value_counts = df[col].value_counts()
            if 1 < len(value_counts) <= 20:  # Reasonable threshold for categorical
                results['categorical_cols'].append(col)
            else:
                results['other_cols'].append(col)
        except:
            results['other_cols'].append(col)
    
    return results

# ==============================================
# EXPORT FUNCTIONALITY
# ==============================================

def trigger_export(export_type):
    """Handle export with maximum error handling"""
    headers = {
        "Authorization": f"Token {KOBO_API_TOKEN}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "type": export_type,
        "fields_from_all_versions": True,
        "hierarchy_in_labels": True,
        "group_sep": "/",
        "lang": "English"
    }
    
    try:
        # Initiate export
        with st.spinner(f"Preparing {export_type.upper()} export..."):
            response = requests.post(
                f"{BASE_URL}/api/v2/assets/{FORM_UID}/exports/",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code != 201:
                st.error(f"Export failed to start (HTTP {response.status_code})")
                if response.text:
                    try:
                        st.json(response.json())
                    except:
                        st.text(response.text)
                return None
                
            export_uid = response.json().get('uid')
            if not export_uid:
                st.error("No export UID received")
                return None
            
            # Wait for completion
            status_url = f"{BASE_URL}/api/v2/assets/{FORM_UID}/exports/{export_uid}/"
            for _ in range(10):  # 10 attempts with 3s delay
                status_response = requests.get(status_url, headers=headers)
                if status_response.status_code != 200:
                    continue
                
                status_data = status_response.json()
                if status_data.get('status') == 'complete':
                    return status_data.get('result')
                elif status_data.get('status') in ('error', 'failed'):
                    st.error(f"Export failed: {status_data.get('messages', 'Unknown error')}")
                    return None
                
                time.sleep(3)
            
            st.error("Export timed out")
            return None
            
    except Exception as e:
        st.error(f"Export error: {str(e)}")
        return None

# ==============================================
# DASHBOARD LAYOUT
# ==============================================

def main():
    st.title("📊 KoboToolbox Dashboard")
    
    # Load data
    raw_data = fetch_kobo_data()
    if raw_data is None:
        st.stop()
    
    df = process_data(raw_data)
    
    if df.empty:
        st.warning("No data available - check form submissions")
        st.stop()
    
    # Analyze columns
    col_analysis = analyze_columns(df)
    
    # Filters
    with st.sidebar:
        st.header("🔍 Filters")
        
        # Date filter
        if col_analysis['date_cols']:
            date_col = st.selectbox("Filter by date", col_analysis['date_cols'])
            min_date = df[date_col].min().to_pydatetime()
            max_date = df[date_col].max().to_pydatetime()
            date_range = st.date_input("Date range", [min_date, max_date])
            
            if len(date_range) == 2:
                df = df[
                    (df[date_col] >= pd.to_datetime(date_range[0])) & 
                    (df[date_col] <= pd.to_datetime(date_range[1]))
                ]
        
        # Column filter
        filter_col = st.selectbox("Filter by column", df.columns)
        
        if filter_col in col_analysis['numeric_cols']:
            min_val = float(df[filter_col].min())
            max_val = float(df[filter_col].max())
            val_range = st.slider("Range", min_val, max_val, (min_val, max_val))
            df = df[df[filter_col].between(*val_range)]
        else:
            try:
                options = st.multiselect("Select values", df[filter_col].unique())
                if options:
                    df = df[df[filter_col].isin(options)]
            except:
                st.warning("Could not filter this column")
    
    # Tabs
    tab1, tab2, tab3 = st.tabs(["Visualizations", "Data", "Export"])
    
    with tab1:
        # Visualizations
        if col_analysis['categorical_cols']:
            col1, col2 = st.columns(2)
            
            with col1:
                selected = st.selectbox("Pie Chart Category", col_analysis['categorical_cols'])
                fig = px.pie(df, names=selected)
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                selected = st.selectbox("Bar Chart Category", col_analysis['categorical_cols'])
                fig = px.histogram(df, x=selected)
                st.plotly_chart(fig, use_container_width=True)
        
        if col_analysis['numeric_cols']:
            selected = st.selectbox("Histogram Column", col_analysis['numeric_cols'])
            fig = px.histogram(df, x=selected)
            st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        st.dataframe(df, height=600)
    
    with tab3:
        st.header("Export Data")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("Export to Excel"):
                handle_export("xlsx")
        
        with col2:
            if st.button("Export to CSV"):
                handle_export("csv")
        
        with col3:
            if st.button("Export to SPSS"):
                handle_export("spss_labels")

def handle_export(export_type):
    """Manage export process"""
    export_url = trigger_export(export_type)
    if not export_url:
        return
    
    headers = {"Authorization": f"Token {KOBO_API_TOKEN}"}
    
    try:
        with st.spinner("Downloading..."):
            response = requests.get(export_url, headers=headers)
            
            if response.status_code == 200:
                ext = "xlsx" if export_type == "xlsx" else "csv" if export_type == "csv" else "sav"
                mime = {
                    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    "csv": "text/csv",
                    "spss_labels": "application/octet-stream"
                }[export_type]
                
                st.download_button(
                    label=f"Download {export_type.upper()}",
                    data=response.content,
                    file_name=f"kobo_export.{ext}",
                    mime=mime
                )
            else:
                st.error(f"Download failed (HTTP {response.status_code})")
    except Exception as e:
        st.error(f"Download error: {str(e)}")

if __name__ == "__main__":
    main()

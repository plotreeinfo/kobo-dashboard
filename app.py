import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import time
from datetime import datetime



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



def safe_nunique(series):
    """Count unique values safely for any column type"""
    try:
        # First try standard nunique
        return series.nunique()
    except TypeError:
        try:
            # Fallback to string conversion
            return len(series.astype(str).unique())
        except:
            # Final fallback
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
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📥 Excel Export"):
                handle_export("xlsx")
        
        with col2:
            if st.button("📥 CSV Export"):
                handle_export("csv")
        
        with col3:
            if st.button("📥 SPSS Export"):
                handle_export("spss_labels")



def handle_export(export_type):
    """Manage the export process"""
    headers = {"Authorization": f"Token {KOBO_API_TOKEN}"}
    
    try:
        # 1. Create export
        payload = {
            "type": export_type,
            "fields_from_all_versions": "true",
            "lang": "English"
        }
        
        with st.spinner(f"Creating {export_type.upper()} export..."):
            response = requests.post(EXPORT_URL, headers=headers, json=payload)
            
            if response.status_code != 201:
                st.error(f"Export failed (HTTP {response.status_code})")
                return
            
            export_uid = response.json().get('uid')
            status_url = f"{EXPORT_URL}{export_uid}/"
        
        # 2. Wait for completion
        with st.spinner("Processing export..."):
            for _ in range(30):  # 30 attempts with 2s delay
                status_response = requests.get(status_url, headers=headers)
                status_data = status_response.json()
                
                if status_data.get('status') == 'complete':
                    download_url = status_data.get('result')
                    if download_url:
                        # 3. Download file
                        file_response = requests.get(download_url, headers=headers)
                        if file_response.status_code == 200:
                            st.success("Export ready! Click below to download")
                            
                            ext = "sav" if export_type == "spss_labels" else export_type
                            mime_types = {
                                "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                "csv": "text/csv",
                                "spss_labels": "application/octet-stream"
                            }
                            
                            st.download_button(
                                label=f"Download {export_type.upper()}",
                                data=file_response.content,
                                file_name=f"kobo_export.{ext}",
                                mime=mime_types[export_type]
                            )
                            return
                
                elif status_data.get('status') in ('error', 'failed'):
                    st.error(f"Export failed: {status_data.get('messages', 'Unknown error')}")
                    return
                
                time.sleep(2)
            
            st.error("Export timed out")
            
    except Exception as e:
        st.error(f"Export error: {str(e)}")

# ==============================================
# MAIN APP
# ==============================================

def main():
    st.title("📊 Onsite Dashboard")
    
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

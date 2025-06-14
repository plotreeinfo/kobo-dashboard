import streamlit as st
import pandas as pd
import plotly.express as px
import requests
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

# ==============================================
# ROBUST DATA FETCHING WITH ERROR HANDLING
# ==============================================

@st.cache_data(ttl=3600)
def fetch_kobo_data():
    """Safe data fetching with comprehensive error handling"""
    headers = {
        "Authorization": f"Token {KOBO_API_TOKEN}",
        "Content-Type": "application/json"
    }
    
    try:
        # First verify asset exists
        asset_url = f"{BASE_URL}/api/v2/assets/{FORM_UID}/"
        asset_response = requests.get(asset_url, headers=headers, timeout=10)
        
        if asset_response.status_code == 404:
            st.error("❌ Form not found - Check FORM_UID in your form's URL")
            return pd.DataFrame()
        
        # Then fetch data
        data_url = f"{BASE_URL}/api/v2/assets/{FORM_UID}/data.json"
        data_response = requests.get(data_url, headers=headers, timeout=30)
        
        if data_response.status_code == 401:
            st.error("""
            🔐 Authentication Failed - Verify:
            1. API Token is correct (generated within last 6 months)
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

# ==============================================
# SAFE DATA PROCESSING
# ==============================================

def clean_data(df):
    """Handle all data types safely"""
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
            # Try converting to string if not numeric
            if not pd.api.types.is_numeric_dtype(df[col]):
                df[col] = df[col].astype(str)
        except:
            df[col] = df[col].astype(str)
    
    return df

def safe_nunique(series):
    """Count unique values safely for any column"""
    try:
        return series.nunique()
    except TypeError:
        try:
            return len(series.astype(str).unique())
        except:
            return 0

# ==============================================
# YOUR DASHBOARD COMPONENTS (WITH SAFETY CHECKS)
# ==============================================

def create_filters(df):
    """Safe filter implementation"""
    if df.empty:
        return df
    
    with st.sidebar:
        st.header("🔍 Filters")
        
        # Date filter (only if datetime columns exist)
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

        # Column filters with type checking
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

# ==============================================
# SAFE VISUALIZATIONS
# ==============================================

def create_visualizations(df):
    """Generate charts only with valid data"""
    if df.empty:
        return
    
    tab1, tab2 = st.tabs(["Charts", "Data"])
    
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
    
    # Debug info
    with st.expander("🔧 Technical Details"):
        st.write(f"Data shape: {df.shape}")
        st.write(f"Last update: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

if __name__ == "__main__":
    main()

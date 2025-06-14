import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import time
from datetime import datetime
from requests.auth import HTTPBasicAuth

# ==============================================
# CONFIGURATION
# ==============================================

# Remove Streamlit menu and GitHub icon
hide_streamlit_style = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# KoboToolbox API credentials
KOBO_USERNAME = st.secrets.get("KOBO_USERNAME", "plotree")
KOBO_API_TOKEN = st.secrets.get("KOBO_API_TOKEN", "04714621fa3d605ff0a4aa5cc2df7cfa961bf256")
FORM_UID = st.secrets.get("FORM_UID", "aJHsRZXT3XEpCoxn9Ct3qZ")
BASE_URL = st.secrets.get("BASE_URL", "https://kf.kobotoolbox.org")

# API endpoints
API_URL = f"{BASE_URL}/api/v2/assets/{FORM_UID}/data.json"

# ==============================================
# DATA FETCHING WITH ERROR HANDLING
# ==============================================

@st.cache_data(ttl=3600)
def fetch_kobo_data():
    try:
        response = requests.get(
            API_URL,
            auth=HTTPBasicAuth(KOBO_USERNAME, KOBO_API_TOKEN),
            timeout=30
        )
        response.raise_for_status()
        data = response.json().get("results", [])
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Data fetch error: {str(e)}")
        return pd.DataFrame()

# ==============================================
# DATA PROCESSING
# ==============================================

def clean_data(df):
    """Handle mixed data types and null values"""
    if df.empty:
        return df
    
    # Convert date columns
    for col in df.columns:
        if 'date' in col.lower():
            try:
                df[col] = pd.to_datetime(df[col], errors='coerce')
            except:
                pass
    
    # Clean numeric columns
    num_cols = df.select_dtypes(include=['number']).columns
    for col in num_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Clean text columns
    text_cols = df.select_dtypes(include=['object']).columns
    for col in text_cols:
        df[col] = df[col].astype(str).replace('nan', pd.NA)
    
    return df

# ==============================================
# FILTERS SIDEBAR
# ==============================================

def create_filters(df):
    """Generate filters with proper type handling"""
    if df.empty:
        return df
    
    with st.sidebar:
        st.header("🔍 Filters")
        
        # Date filter
        date_cols = [col for col in df.columns if 'date' in col.lower() and pd.api.types.is_datetime64_any_dtype(df[col])]
        if date_cols:
            selected_date_col = st.selectbox("Select date column", date_cols)
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

        # Dynamic column filters
        filter_cols = st.multiselect(
            "Select columns to filter",
            df.columns,
            default=[]
        )
        
        for col in filter_cols:
            try:
                if pd.api.types.is_numeric_dtype(df[col]):
                    min_val = float(df[col].min())
                    max_val = float(df[col].max())
                    val_range = st.slider(
                        f"Range for {col}",
                        min_val,
                        max_val,
                        (min_val, max_val)
                    )
                    df = df[(df[col] >= val_range[0]) & (df[col] <= val_range[1])]
                else:
                    unique_vals = df[col].dropna().unique()
                    if len(unique_vals) < 20:
                        options = st.multiselect(
                            f"Filter by {col}",
                            unique_vals
                        )
                        if options:
                            df = df[df[col].isin(options)]
            except Exception as e:
                st.warning(f"Couldn't filter column {col}: {str(e)}")
    
    return df

# ==============================================
# VISUALIZATIONS
# ==============================================

def create_visualizations(df):
    """Create charts with proper error handling"""
    if df.empty:
        st.warning("No data available for visualizations")
        return
    
    tab1, tab2 = st.tabs(["Charts", "Data"])
    
    with tab1:
        # Numeric charts
        num_cols = df.select_dtypes(include=['number']).columns
        if len(num_cols) > 0:
            st.subheader("Numeric Data")
            col1, col2 = st.columns(2)
            
            with col1:
                selected_num = st.selectbox("Select numeric column", num_cols)
                fig = px.histogram(df, x=selected_num)
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                if len(num_cols) > 1:
                    selected_num2 = st.selectbox("Select second numeric column", num_cols)
                    fig = px.scatter(df, x=selected_num, y=selected_num2)
                    st.plotly_chart(fig, use_container_width=True)
        
        # Categorical charts
        cat_cols = [col for col in df.columns 
                   if not pd.api.types.is_numeric_dtype(df[col]) 
                   and df[col].nunique() < 20]
        
        if cat_cols:
            st.subheader("Categorical Data")
            selected_cat = st.selectbox("Select category", cat_cols)
            fig = px.pie(df, names=selected_cat)
            st.plotly_chart(fig, use_container_width=True)
    
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
        st.warning("No data available - check form submissions")
        return
    
    # Apply filters
    df = create_filters(df)
    
    # Create visualizations
    create_visualizations(df)

if __name__ == "__main__":
    main()

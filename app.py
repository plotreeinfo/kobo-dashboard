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

# YOUR CREDENTIALS (USE YOUR ACTUAL VALUES)
KOBO_API_TOKEN = "04714621fa3d605ff0a4aa5cc2df7cfa961bf256"  # Replace with your current token
FORM_UID = "aJHsRZXT3XEpCoxn9Ct3qZ"  # Replace with your form UID
BASE_URL = "https://kf.kobotoolbox.org"

# ==============================================
# FIXED AUTHENTICATION FUNCTION
# ==============================================

@st.cache_data(ttl=3600)
def fetch_kobo_data():
    """Fixed authentication using Token instead of Basic Auth"""
    headers = {
        "Authorization": f"Token {KOBO_API_TOKEN}",
        "Content-Type": "application/json"
    }
    
    try:
        # First verify asset exists
        asset_url = f"{BASE_URL}/api/v2/assets/{FORM_UID}/"
        asset_response = requests.get(asset_url, headers=headers, timeout=10)
        
        if asset_response.status_code == 404:
            st.error("Form not found - check FORM_UID")
            return pd.DataFrame()
        
        # Then fetch data
        data_url = f"{BASE_URL}/api/v2/assets/{FORM_UID}/data.json"
        data_response = requests.get(data_url, headers=headers, timeout=30)
        
        if data_response.status_code == 401:
            st.error("""
            Authentication Failed - Verify:
            1. API Token is correct (generated within last 6 months)
            2. You have 'View Submissions' permission
            3. FORM_UID matches your form's URL
            """)
            return pd.DataFrame()
            
        data_response.raise_for_status()
        data = data_response.json().get("results", [])
        
        if not data:
            st.warning("Form exists but has no submissions yet")
            
        return pd.DataFrame(data)
        
    except Exception as e:
        st.error(f"Connection error: {str(e)}")
        return pd.DataFrame()

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
# YOUR DASHBOARD LAYOUT (UNCHANGED)
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
    
    # Your tabs layout
    tab1, tab2 = st.tabs(["Charts", "Data"])
    
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

if __name__ == "__main__":
    main()

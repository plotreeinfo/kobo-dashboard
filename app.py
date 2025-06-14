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
        except

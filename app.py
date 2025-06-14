import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import time
from datetime import datetime

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

# KoboToolbox API credentials - MUST UPDATE THESE
KOBO_API_TOKEN = st.secrets.get("KOBO_API_TOKEN", "04714621fa3d605ff0a4aa5cc2df7cfa961bf256")  # From Account Settings → API Tokens
FORM_UID = st.secrets.get("FORM_UID", "aJHsRZXT3XEpCoxn9Ct3qZ")  # Find in form URL after /assets/
BASE_URL = st.secrets.get("BASE_URL", "https://kf.kobotoolbox.org")  # Or your custom server

# API endpoints
API_URL = f"{BASE_URL}/api/v2/assets/{FORM_UID}/data.json"
EXPORT_URL = f"{BASE_URL}/api/v2/assets/{FORM_UID}/exports/"

# ==============================================
# AUTHENTICATION & RESOURCE VERIFICATION
# ==============================================

def verify_credentials_and_resources():
    """Verify both credentials AND form existence using Token Auth"""
    headers = {
        "Authorization": f"Token {KOBO_API_TOKEN}",
        "Content-Type": "application/json"
    }
    
    try:
        # Test authentication
        auth_test_url = f"{BASE_URL}/api/v2/user/"
        auth_response = requests.get(auth_test_url, headers=headers, timeout=10)
        
        if auth_response.status_code == 401:
            st.error("🔐 Authentication Failed (Invalid API Token)")
            st.markdown("""
            ### How to fix:
            1. Go to [KoboToolbox Account Settings](https://kf.kobotoolbox.org/account/)
            2. Navigate to "API Tokens"
            3. Generate a new token if needed
            """)
            return False
            
        # Verify form exists
        form_test_url = f"{BASE_URL}/api/v2/assets/{FORM_UID}/"
        form_response = requests.get(form_test_url, headers=headers, timeout=10)
        
        if form_response.status_code == 404:
            st.error("🔍 Form Not Found (404 Error)")
            st.markdown(f"""
            ### Check:
            1. Form UID: `{FORM_UID}`
            2. Form sharing permissions
            """)
            return False
            
        return True
        
    except requests.exceptions.RequestException as e:
        st.error(f"🔌 Connection Error: {str(e)}")
        return False

# ==============================================
# DATA FETCHING WITH PROPER TOKEN AUTH
# ==============================================

@st.cache_data(ttl=3600)  # Cache for 1 hour
def fetch_kobo_data():
    """Fetch data with Token Authentication"""
    headers = {
        "Authorization": f"Token {KOBO_API_TOKEN}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(API_URL, headers=headers, timeout=30)
        
        if response.status_code == 401:
            st.error("❌ Invalid API Token - Regenerate in Account Settings")
            return pd.DataFrame()
            
        if response.status_code == 404:
            st.error("❌ Form/data endpoint not found")
            return pd.DataFrame()
            
        response.raise_for_status()
        data = response.json().get("results", [])
        
        if not data:
            st.warning("⚠️ No submissions found in this form")
            
        return pd.DataFrame(data)
        
    except Exception as e:
        st.error(f"Data fetch error: {str(e)}")
        return pd.DataFrame()

# ==============================================
# MAIN DASHBOARD
# ==============================================

st.title("KoboToolbox Data Dashboard")

# Verify credentials and form existence first
if not verify_credentials_and_resources():
    st.stop()

# Load data
df = fetch_kobo_data()

if df.empty:
    st.warning("No data available - check form submissions")
    st.stop()

# Display raw data
st.subheader("Raw Data Preview")
st.dataframe(df)

# ==============================================
# DATA VISUALIZATION EXAMPLES
# ==============================================

st.subheader("Data Visualization")

# Example 1: Summary stats
if not df.empty:
    st.write("Summary Statistics")
    st.write(df.describe())

# Example 2: Plot numeric columns
numeric_cols = df.select_dtypes(include=['number']).columns
if len(numeric_cols) > 0:
    selected_col = st.selectbox("Select numeric column to plot", numeric_cols)
    fig = px.histogram(df, x=selected_col)
    st.plotly_chart(fig)

# ==============================================
# EXPORT FUNCTIONALITY
# ==============================================

def trigger_kobo_export(export_type="xls"):
    """Secure export with Token Auth"""
    headers = {
        "Authorization": f"Token {KOBO_API_TOKEN}",
        "Content-Type": "application/json"
    }
    
    try:
        payload = {
            "type": export_type,
            "fields_from_all_versions": "true",
            "lang": "English"
        }
        
        response = requests.post(
            EXPORT_URL,
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 201:
            return response.json().get('url')
        else:
            st.error(f"Export failed (HTTP {response.status_code})")
            return None
            
    except Exception as e:
        st.error(f"Export error: {str(e)}")
        return None

# ==============================================
# DEBUGGING SECTION
# ==============================================

with st.expander("🔧 Debugging Tools", expanded=False):
    st.write(f"Form UID: {FORM_UID}")
    st.write(f"Server: {BASE_URL}")
    
    if st.button("Test API Endpoints"):
        with st.spinner("Running diagnostics..."):
            headers = {"Authorization": f"Token {KOBO_API_TOKEN}"}
            
            # Test authentication
            auth_url = f"{BASE_URL}/api/v2/user/"
            auth_status = requests.get(auth_url, headers=headers).status_code
            st.write(f"Auth endpoint: HTTP {auth_status}")
            
            # Test form access
            form_url = f"{BASE_URL}/api/v2/assets/{FORM_UID}/"
            form_status = requests.get(form_url, headers=headers).status_code
            st.write(f"Form endpoint: HTTP {form_status}")
            
            # Test data access
            data_status = requests.get(API_URL, headers=headers).status_code
            st.write(f"Data endpoint: HTTP {data_status}")
            
            if all(s == 200 for s in [auth_status, form_status, data_status]):
                st.success("✅ All endpoints accessible!")
            else:
                st.error("❌ Some endpoints failed")

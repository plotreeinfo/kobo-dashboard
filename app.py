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

# KoboToolbox API credentials - MUST UPDATE THESE
KOBO_USERNAME = st.secrets.get("KOBO_USERNAME", "plotree")  # From secrets or input
KOBO_API_TOKEN = st.secrets.get("KOBO_API_TOKEN", "04714621fa3d605ff0a4aa5cc2df7cfa961bf256")  # From Account Settings → API Tokens
FORM_UID = st.secrets.get("FORM_UID", "aJHsRZXT3XEpCoxn9Ct3qZ")  # Find in form URL after /assets/
BASE_URL = st.secrets.get("BASE_URL", "https://kf.kobotoolbox.org")  # Or your custom server

# API endpoints
API_URL = f"{BASE_URL}/api/v2/assets/{FORM_UID}/data.json"
EXPORT_URL = f"{BASE_URL}/api/v2/assets/{FORM_UID}/exports/"

# ==============================================
# AUTHENTICATION HANDLING
# ==============================================

def verify_credentials():
    """Verify credentials with proper error handling"""
    try:
        test_url = f"{BASE_URL}/api/v2/user/"
        response = requests.get(
            test_url,
            auth=HTTPBasicAuth(KOBO_USERNAME, KOBO_API_TOKEN),
            timeout=10
        )
        
        if response.status_code == 200:
            return True
            
        st.error(f"🔐 Authentication Failed (HTTP {response.status_code})")
        st.markdown("""
        ### Troubleshooting Steps:
        1. **Verify your username** is correct (email address used for KoboToolbox)
        2. **Use an API Token** (not your password):
           - Go to [KoboToolbox Account Settings](https://kf.kobotoolbox.org/account/)
           - Navigate to "API Tokens"
           - Generate a new token if needed
        3. **Check token permissions**:
           - Ensure token has access to this form
           - Tokens expire after 30 days by default
        4. **Verify server URL**:
           - Confirm you're using the correct KoboToolbox instance
        """)
        return False
        
    except requests.exceptions.RequestException as e:
        st.error(f"🔌 Connection Error: {str(e)}")
        st.info("Please check your internet connection and server URL")
        return False

# ==============================================
# DATA FETCHING
# ==============================================

@st.cache_data(ttl=3600)
def fetch_kobo_data():
    """Fetch data with comprehensive error handling"""
    if not verify_credentials():
        st.stop()
    
    try:
        response = requests.get(
            API_URL,
            auth=HTTPBasicAuth(KOBO_USERNAME, KOBO_API_TOKEN),
            timeout=30
        )
        
        if response.status_code == 401:
            st.error("""
            ❌ Still unauthorized after credential verification.
            Possible reasons:
            - Token was revoked
            - Form permissions changed
            - Account was deactivated
            """)
            return pd.DataFrame()
        
        response.raise_for_status()
        data = response.json().get("results", [])
        
        if not data:
            st.warning("⚠️ No submissions found in this form")
            return pd.DataFrame()
            
        return pd.DataFrame(data)
        
    except Exception as e:
        st.error(f"Data fetch error: {str(e)}")
        return pd.DataFrame()

# ==============================================
# MAIN DASHBOARD
# ==============================================

# Verify credentials first
if not verify_credentials():
    st.error("Cannot proceed without valid authentication")
    st.stop()

# Load data
df = fetch_kobo_data()

if df.empty:
    st.warning("No data available - check form submissions")
    st.stop()

# [Rest of your data processing and dashboard code...]

# ==============================================
# EXPORT FUNCTIONALITY (AUTHENTICATED)
# ==============================================

def trigger_kobo_export(export_type="xls"):
    """Secure export triggering with auth verification"""
    if not verify_credentials():
        return None
        
    try:
        headers = {
            'Authorization': f'Token {KOBO_API_TOKEN}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            "type": export_type,
            "fields_from_all_versions": "true",
            "group_sep": "/",
            "hierarchy_in_labels": "true",
            "include_media_urls": "true",
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
            if response.status_code == 403:
                st.error("""
                🔒 Permission Denied. Your token may lack:
                - Export permissions
                - Access to this specific form
                """)
            return None
            
    except Exception as e:
        st.error(f"Export request error: {str(e)}")
        return None

# [Rest of your dashboard implementation...]

# ==============================================
# CREDENTIAL DEBUGGING (OPTIONAL)
# ==============================================

with st.expander("🔧 Debug Authentication", expanded=False):
    st.write(f"Username: {KOBO_USERNAME}")
    st.write("API Token: [hidden]" if KOBO_API_TOKEN else "API Token: Not set")
    st.write(f"Form UID: {FORM_UID}")
    st.write(f"Server: {BASE_URL}")
    
    if st.button("Test Connection"):
        with st.spinner("Testing connection..."):
            if verify_credentials():
                st.success("✅ Authentication successful!")
            else:
                st.error("❌ Authentication failed")

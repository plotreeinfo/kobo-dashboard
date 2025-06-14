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
KOBO_USERNAME = st.secrets.get("KOBO_USERNAME", "plotree")  # Your login email
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
    """Verify both credentials AND form existence"""
    try:
        # First test basic authentication
        auth_test_url = f"{BASE_URL}/api/v2/user/"
        auth_response = requests.get(
            auth_test_url,
            auth=HTTPBasicAuth(KOBO_USERNAME, KOBO_API_TOKEN),
            timeout=10
        )
        
        if auth_response.status_code == 401:
            st.error("🔐 Authentication Failed (Invalid credentials)")
            st.markdown("""
            ### How to fix:
            1. Go to [KoboToolbox Account Settings](https://kf.kobotoolbox.org/account/)
            2. Navigate to "API Tokens"
            3. Generate/copy a valid API token
            4. Make sure you're using your login email as username
            """)
            return False
            
        # Then verify form exists
        form_test_url = f"{BASE_URL}/api/v2/assets/{FORM_UID}/"
        form_response = requests.get(
            form_test_url,
            auth=HTTPBasicAuth(KOBO_USERNAME, KOBO_API_TOKEN),
            timeout=10
        )
        
        if form_response.status_code == 404:
            st.error("🔍 Form Not Found (404 Error)")
            st.markdown(f"""
            ### Possible reasons:
            1. Incorrect Form UID: `{FORM_UID}`
            2. Form was deleted
            3. No permission to access this form
            
            ### How to find your Form UID:
            1. Open your form in KoboToolbox
            2. Check the URL: `.../assets/{'{your_form_uid}'}/...`
            """)
            return False
            
        return True
        
    except requests.exceptions.RequestException as e:
        st.error(f"🔌 Connection Error: {str(e)}")
        st.info("Please check:")
        st.info("- Internet connection")
        st.info("- Server URL (currently using: {BASE_URL})")
        return False

# ==============================================
# DATA FETCHING WITH 404 HANDLING
# ==============================================

@st.cache_data(ttl=3600)
def fetch_kobo_data():
    """Fetch data with comprehensive error handling"""
    if not verify_credentials_and_resources():
        st.stop()
    
    try:
        response = requests.get(
            API_URL,
            auth=HTTPBasicAuth(KOBO_USERNAME, KOBO_API_TOKEN),
            timeout=30
        )
        
        if response.status_code == 404:
            st.error("""
            ❌ Data endpoint not found (404)
            The form exists but data API is unavailable
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

# Verify credentials and form existence first
if not verify_credentials_and_resources():
    st.error("Cannot proceed without valid authentication and form access")
    st.stop()

# Load data
df = fetch_kobo_data()

if df.empty:
    st.warning("No data available - check form submissions")
    st.stop()

# [Rest of your data processing and dashboard code...]

# ==============================================
# EXPORT FUNCTIONALITY WITH RESOURCE CHECKS
# ==============================================

def trigger_kobo_export(export_type="xls"):
    """Secure export with resource verification"""
    if not verify_credentials_and_resources():
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
        
        if response.status_code == 404:
            st.error("""
            🚫 Export endpoint not found (404)
            This usually means:
            1. The form UID is incorrect
            2. Export API is unavailable
            """)
            return None
            
        if response.status_code == 201:
            return response.json().get('url')
            
        st.error(f"Export failed (HTTP {response.status_code})")
        return None
        
    except Exception as e:
        st.error(f"Export request error: {str(e)}")
        return None

# ==============================================
# DEBUGGING SECTION
# ==============================================

with st.expander("🔧 Debugging Tools", expanded=False):
    st.write(f"Username: {KOBO_USERNAME}")
    st.write("API Token: [hidden]" if KOBO_API_TOKEN else "API Token: Not set")
    st.write(f"Form UID: {FORM_UID}")
    st.write(f"Server: {BASE_URL}")
    
    if st.button("Test All Endpoints"):
        with st.spinner("Running diagnostics..."):
            # Test authentication
            auth_url = f"{BASE_URL}/api/v2/user/"
            auth_status = requests.get(auth_url, auth=HTTPBasicAuth(KOBO_USERNAME, KOBO_API_TOKEN)).status_code
            st.write(f"Auth endpoint ({auth_url}): HTTP {auth_status}")
            
            # Test form access
            form_url = f"{BASE_URL}/api/v2/assets/{FORM_UID}/"
            form_status = requests.get(form_url, auth=HTTPBasicAuth(KOBO_USERNAME, KOBO_API_TOKEN)).status_code
            st.write(f"Form endpoint ({form_url}): HTTP {form_status}")
            
            # Test data access
            data_status = requests.get(API_URL, auth=HTTPBasicAuth(KOBO_USERNAME, KOBO_API_TOKEN)).status_code
            st.write(f"Data endpoint ({API_URL}): HTTP {data_status}")
            
            if all(s == 200 for s in [auth_status, form_status, data_status]):
                st.success("✅ All endpoints accessible!")
            else:
                st.error("❌ Some endpoints failed (see above)")

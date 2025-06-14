import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import json

# Set up the page configuration
st.set_page_config(
    page_title="Kobo Toolbox Data Dashboard",
    page_icon="📊",
    layout="wide"
)

# Your Kobo Toolbox credentials
KOBO_USERNAME = "plotree"
KOBO_API_TOKEN = "04714621fa3d605ff0a4aa5cc2df7cfa961bf256"
FORM_UID = "aJHsRZXT3XEpCoxn9Ct3qZ"

# API endpoints - using the correct base URL
KOBO_API_URL = "https://kf.kobotoolbox.org/api/v2"
ASSET_URL = f"{KOBO_API_URL}/assets/{FORM_UID}/"
DATA_URL = f"{KOBO_API_URL}/assets/{FORM_UID}/data/"

# Headers for authentication
headers = {
    "Authorization": f"Token {KOBO_API_TOKEN}",
    "Content-Type": "application/json",
    "Accept": "application/json"
}

@st.cache_data(ttl=3600)
def fetch_kobo_data():
    """Fetch data from Kobo Toolbox API with improved error handling"""
    try:
        # First verify the API connection
        st.write("Testing API connection...")
        test_url = f"{KOBO_API_URL}/assets/"
        test_response = requests.get(test_url, headers=headers)
        
        # Check if we're getting HTML instead of JSON
        if 'html' in test_response.headers.get('Content-Type', '').lower():
            st.error("Received HTML instead of JSON. Possible authentication failure.")
            st.text(f"Response headers: {test_response.headers}")
            return None, None
            
        test_response.raise_for_status()
        
        # Now get the asset details
        st.write("Fetching asset information...")
        asset_response = requests.get(ASSET_URL, headers=headers)
        
        # Check for HTML response again
        if 'html' in asset_response.headers.get('Content-Type', '').lower():
            st.error("Asset request returned HTML. Possible issues:")
            st.markdown("""
            - Invalid API token
            - Incorrect form UID
            - Insufficient permissions
            """)
            st.text(f"Response start: {asset_response.text[:500]}...")
            return None, None
            
        asset_response.raise_for_status()
        
        try:
            asset_data = asset_response.json()
        except json.JSONDecodeError as e:
            st.error(f"Failed to decode asset JSON: {e}")
            st.text(f"Raw response (first 500 chars): {asset_response.text[:500]}...")
            return None, None
        
        st.write("Fetching submission data...")
        data_response = requests.get(DATA_URL, headers=headers)
        
        if 'html' in data_response.headers.get('Content-Type', '').lower():
            st.error("Data request returned HTML. Check your form permissions.")
            return None, None
            
        data_response.raise_for_status()
        
        try:
            response_data = data_response.json()
            if 'results' not in response_data:
                st.error("Unexpected API response format - no 'results' key found")
                st.json(response_data) if len(str(response_data)) < 1000 else st.text(str(response_data)[:1000] + "...")
                return None, None
                
            submissions = response_data['results']
            
            if not submissions:
                st.warning("No submissions found in the form")
                return pd.DataFrame(), asset_data
            
            # Convert to pandas DataFrame
            df = pd.json_normalize(submissions)
            
            # Clean up column names
            df.columns = [col.split('.')[-1] for col in df.columns]
            
            return df, asset_data
            
        except json.JSONDecodeError as e:
            st.error(f"Failed to decode data JSON: {e}")
            st.text(f"Raw response (first 500 chars): {data_response.text[:500]}...")
            return None, None
            
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching data from Kobo Toolbox: {str(e)}")
        if hasattr(e, 'response') and e.response:
            st.text(f"Status code: {e.response.status_code}")
            st.text(f"Response headers: {e.response.headers}")
            st.text(f"Response content (first 500 chars): {e.response.text[:500]}...")
        return None, None

# ... [rest of the code remains the same as previous version] ...

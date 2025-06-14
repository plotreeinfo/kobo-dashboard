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

@st.cache_data(ttl=3600)
def fetch_kobo_data():
    """Fetch data from Kobo Toolbox API with improved error handling"""
    try:
        # Get credentials from secrets
        api_token = st.secrets["KOBO_API_TOKEN"]
        form_uid = st.secrets["FORM_UID"]
        
        # API endpoints
        KOBO_API_URL = "https://kf.kobotoolbox.org/api/v2"
        ASSET_URL = f"{KOBO_API_URL}/assets/{form_uid}/"
        DATA_URL = f"{KOBO_API_URL}/assets/{form_uid}/data/"

        headers = {
            "Authorization": f"Token {api_token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        # Get asset info
        asset_response = requests.get(ASSET_URL, headers=headers)
        
        # Check for HTML response (indicates auth failure)
        if 'html' in asset_response.headers.get('Content-Type', '').lower():
            st.error("Authentication failed - check your API token")
            return None, None
            
        asset_response.raise_for_status()
        asset_data = asset_response.json()

        # Get submission data
        data_response = requests.get(DATA_URL, headers=headers)
        data_response.raise_for_status()
        response_data = data_response.json()
        
        if 'results' not in response_data:
            st.error("Unexpected API response format")
            return None, None
            
        submissions = response_data['results']
        
        if not submissions:
            return pd.DataFrame(), asset_data
            
        # Convert to DataFrame
        df = pd.json_normalize(submissions)
        df.columns = [col.split('.')[-1] for col in df.columns]
        
        return df, asset_data
        
    except Exception as e:
        st.error(f"Error fetching data: {str(e)}")
        return None, None

def main():
    st.title("Kobo Toolbox Data Dashboard")
    
    with st.spinner("Loading data..."):
        df, asset_info = fetch_kobo_data()
    
    if df is None:
        st.error("Failed to fetch data. Please check:")
        st.markdown("""
        - API token is correct in secrets.toml
        - Form UID is correct
        - You have internet connection
        """)
    elif df.empty:
        st.warning("No submissions found in this form")
    else:
        st.success(f"Loaded {len(df)} submissions")
        st.dataframe(df)

if __name__ == "__main__":
    main()

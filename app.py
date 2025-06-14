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

# API endpoints - using kobotoolbox.org instead of kf.kobotoolbox.org
KOBO_API_URL = "https://kobo.humanitarianresponse.info/api/v2"
ASSET_URL = f"{KOBO_API_URL}/assets/{FORM_UID}"
DATA_URL = f"{KOBO_API_URL}/assets/{FORM_UID}/data/"

# Headers for authentication
headers = {
    "Authorization": f"Token {KOBO_API_TOKEN}"
}

@st.cache_data(ttl=3600)  # Cache data for 1 hour
def fetch_kobo_data():
    """Fetch data from Kobo Toolbox API with improved error handling"""
    try:
        # First get the asset details
        st.write("Fetching asset information...")
        asset_response = requests.get(ASSET_URL, headers=headers)
        
        # Check for HTTP errors
        asset_response.raise_for_status()
        
        try:
            asset_data = asset_response.json()
        except json.JSONDecodeError as e:
            st.error(f"Failed to decode asset JSON: {e}")
            st.text(f"Raw response: {asset_response.text}")
            return None, None
        
        st.write("Fetching submission data...")
        data_response = requests.get(DATA_URL, headers=headers)
        data_response.raise_for_status()
        
        try:
            response_data = data_response.json()
            if 'results' not in response_data:
                st.error("Unexpected API response format - no 'results' key found")
                st.json(response_data)  # Show the actual response for debugging
                return None, None
                
            submissions = response_data['results']
            
            if not submissions:
                st.warning("No submissions found in the form")
                return pd.DataFrame(), asset_data
            
            # Convert to pandas DataFrame
            df = pd.json_normalize(submissions)
            
            # Clean up column names (remove the 'group.' prefix)
            df.columns = [col.split('.')[-1] for col in df.columns]
            
            return df, asset_data
            
        except json.JSONDecodeError as e:
            st.error(f"Failed to decode data JSON: {e}")
            st.text(f"Raw response: {data_response.text}")
            return None, None
            
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching data from Kobo Toolbox: {str(e)}")
        if hasattr(e, 'response') and e.response:
            st.text(f"Status code: {e.response.status_code}")
            st.text(f"Response content: {e.response.text}")
        return None, None

def display_dashboard(df, asset_info):
    """Display the data in a Streamlit dashboard"""
    st.title("Kobo Toolbox Data Dashboard")
    
    if asset_info:
        st.write(f"Form: {asset_info.get('name', 'Unknown Form')}")
    st.write(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if df.empty:
        st.warning("The form exists but contains no submissions yet.")
        return
    
    # Show basic info
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Submissions", len(df))
    
    # If there's a date column, show the time range
    date_cols = [col for col in df.columns if 'date' in col.lower()]
    if date_cols:
        try:
            df[date_cols[0]] = pd.to_datetime(df[date_cols[0]])
            col2.metric("Earliest Submission", df[date_cols[0]].min().date())
            col3.metric("Latest Submission", df[date_cols[0]].max().date())
        except Exception as e:
            st.warning(f"Couldn't parse date column: {e}")
    
    st.divider()
    
    # Show the raw data with filters
    st.subheader("Submission Data")
    st.dataframe(df, use_container_width=True)
    
    st.divider()
    
    # Show some basic charts if we have data
    st.subheader("Data Visualizations")
    
    # Try to automatically create charts for suitable columns
    try:
        chart_cols = [col for col in df.columns if df[col].nunique() < 20 and df[col].nunique() > 1]
        
        if chart_cols:
            cols = st.columns(2)
            for i, col in enumerate(chart_cols[:4]):  # Show up to 4 charts
                with cols[i % 2]:
                    st.write(f"Distribution of {col}")
                    st.bar_chart(df[col].value_counts())
        else:
            st.info("No suitable columns found for automatic visualization")
    except Exception as e:
        st.warning(f"Couldn't generate charts: {e}")
    
    # Download button
    st.download_button(
        label="Download Data as CSV",
        data=df.to_csv(index=False).encode('utf-8'),
        file_name='kobo_data.csv',
        mime='text/csv'
    )

def main():
    st.sidebar.title("Kobo Toolbox Connection")
    st.sidebar.write(f"Form UID: {FORM_UID}")
    st.sidebar.write(f"Username: {KOBO_USERNAME}")
    
    # Add a loading spinner while fetching data
    with st.spinner("Fetching data from Kobo Toolbox..."):
        df, asset_info = fetch_kobo_data()
    
    if df is not None:
        display_dashboard(df, asset_info)
    else:
        st.error("Failed to fetch data. Please check:")
        st.markdown("""
        - Your internet connection
        - The API token is still valid
        - The form UID is correct
        - You have permission to access this form
        """)

if __name__ == "__main__":
    main()

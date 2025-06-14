import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# Set up the page configuration
st.set_page_config(
    page_title="Kobo Toolbox Data Dashboard",
    page_icon="📊",
    layout="wide"
)

# Your Kobo Toolbox credentials (consider using st.secrets for production)
KOBO_USERNAME = "plotree"
KOBO_API_TOKEN = "04714621fa3d605ff0a4aa5cc2df7cfa961bf256"
FORM_UID = "aJHsRZXT3XEpCoxn9Ct3qZ"

# API endpoints
KOBO_API_URL = "https://kf.kobotoolbox.org/api/v2"
ASSET_URL = f"{KOBO_API_URL}/assets/{FORM_UID}"
DATA_URL = f"{KOBO_API_URL}/assets/{FORM_UID}/data/"

# Headers for authentication
headers = {
    "Authorization": f"Token {KOBO_API_TOKEN}"
}

@st.cache_data(ttl=3600)  # Cache data for 1 hour
def fetch_kobo_data():
    """Fetch data from Kobo Toolbox API"""
    try:
        # First get the asset details to understand the structure
        asset_response = requests.get(ASSET_URL, headers=headers)
        asset_response.raise_for_status()
        asset_data = asset_response.json()
        
        # Then get the actual submission data
        data_response = requests.get(DATA_URL, headers=headers)
        data_response.raise_for_status()
        submissions = data_response.json()['results']
        
        # Convert to pandas DataFrame
        df = pd.json_normalize(submissions)
        
        # Clean up column names (remove the 'group.' prefix)
        df.columns = [col.split('.')[-1] for col in df.columns]
        
        return df, asset_data
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching data from Kobo Toolbox: {e}")
        return None, None

def display_dashboard(df, asset_info):
    """Display the data in a Streamlit dashboard"""
    st.title("Kobo Toolbox Data Dashboard")
    st.write(f"Form: {asset_info.get('name', 'Unknown Form')}")
    st.write(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Show basic info
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Submissions", len(df))
    
    # If there's a date column, show the time range
    date_cols = [col for col in df.columns if 'date' in col.lower()]
    if date_cols:
        df[date_cols[0]] = pd.to_datetime(df[date_cols[0]])
        col2.metric("Earliest Submission", df[date_cols[0]].min().date())
        col3.metric("Latest Submission", df[date_cols[0]].max().date())
    
    st.divider()
    
    # Show the raw data with filters
    st.subheader("Submission Data")
    
    # Add filters if there are suitable columns
    filter_cols = st.columns(4)
    filters = {}
    
    # Automatically detect filterable columns
    filterable_cols = []
    for col in df.columns:
        if df[col].nunique() < 20 and df[col].nunique() > 1:  # Good for filters
            filterable_cols.append(col)
    
    # Create filters for up to 4 columns
    for i, col in enumerate(filterable_cols[:4]):
        unique_vals = df[col].unique()
        selected = filter_cols[i].multiselect(
            f"Filter by {col}",
            options=unique_vals,
            default=unique_vals
        )
        filters[col] = selected
    
    # Apply filters
    filtered_df = df.copy()
    for col, vals in filters.items():
        if vals:  # Only filter if values are selected
            filtered_df = filtered_df[filtered_df[col].isin(vals)]
    
    # Show the filtered data
    st.dataframe(filtered_df, use_container_width=True)
    
    st.divider()
    
    # Show some basic charts
    st.subheader("Data Visualizations")
    
    # Automatically create charts for suitable columns
    chart_cols = [col for col in df.columns if df[col].nunique() < 20]
    
    if chart_cols:
        cols = st.columns(2)
        for i, col in enumerate(chart_cols[:4]):  # Show up to 4 charts
            with cols[i % 2]:
                st.bar_chart(filtered_df[col].value_counts())
    
    # Download button
    st.download_button(
        label="Download Data as CSV",
        data=filtered_df.to_csv(index=False).encode('utf-8'),
        file_name='kobo_data.csv',
        mime='text/csv'
    )

def main():
    # Add a loading spinner while fetching data
    with st.spinner("Fetching data from Kobo Toolbox..."):
        df, asset_info = fetch_kobo_data()
    
    if df is not None and not df.empty:
        display_dashboard(df, asset_info)
    else:
        st.error("No data found or there was an error fetching data.")

if __name__ == "__main__":
    main()

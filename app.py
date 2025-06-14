import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import json
from urllib.parse import urljoin

# Set up the page configuration
st.set_page_config(
    page_title="Kobo Toolbox Data Dashboard",
    page_icon="📊",
    layout="wide"
)

@st.cache_data(ttl=3600)
def fetch_kobo_data():
    """Fetch raw data directly from Kobo Toolbox API"""
    try:
        # Get credentials from secrets
        api_token = st.secrets["KOBO_API_TOKEN"]
        form_uid = st.secrets["FORM_UID"]
        
        # API endpoints
        KOBO_API_URL = "https://kf.kobotoolbox.org/api/v2"
        DATA_URL = f"{KOBO_API_URL}/assets/{form_uid}/data/?format=json"
        
        headers = {
            "Authorization": f"Token {api_token}",
            "Content-Type": "application/json"
        }

        # Get submission data
        response = requests.get(DATA_URL, headers=headers)
        response.raise_for_status()
        submissions = response.json()['results']
        
        if not submissions:
            return pd.DataFrame()
            
        # Convert to DataFrame without flattening
        df = pd.DataFrame(submissions)
        
        # Process attachments to create direct download links
        if '_attachments' in df.columns:
            df['_attachments'] = df['_attachments'].apply(
                lambda x: [urljoin(KOBO_API_URL, a['download_url']) for a in x] if x else None
            )
        
        return df
        
    except Exception as e:
        st.error(f"Error fetching data: {str(e)}")
        return None

def display_kobo_table(df):
    """Display data table with download buttons just like Kobo Toolbox"""
    if df is None or df.empty:
        return
    
    st.subheader("Raw Data from Kobo Toolbox")
    
    # Create a copy for display
    display_df = df.copy()
    
    # Convert attachments to clickable links
    if '_attachments' in display_df.columns:
        display_df['_attachments'] = display_df['_attachments'].apply(
            lambda x: "\n".join([f'<a href="{url}" target="_blank">Download</a>' for url in x]) if x else None
        )
    
    # Display the table with HTML rendering
    st.write(
        display_df.to_html(escape=False, render_links=True), 
        unsafe_allow_html=True
    )
    
    # Add CSV download button
    st.download_button(
        label="Download Full Data as CSV",
        data=df.to_csv(index=False).encode('utf-8'),
        file_name=f'kobo_data_{datetime.now().strftime("%Y%m%d")}.csv',
        mime='text/csv'
    )

def main():
    st.title("Kobo Toolbox Data Viewer")
    st.markdown("""
    <style>
    a {
        color: #ff4b4b;
        text-decoration: none;
    }
    a:hover {
        text-decoration: underline;
    }
    </style>
    """, unsafe_allow_html=True)
    
    with st.spinner("Loading data directly from Kobo Toolbox..."):
        df = fetch_kobo_data()
    
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
        st.success(f"Loaded {len(df)} submissions directly from Kobo Toolbox")
        display_kobo_table(df)

if __name__ == "__main__":
    main()

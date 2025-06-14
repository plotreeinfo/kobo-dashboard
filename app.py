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
    """Fetch data from Kobo Toolbox API with media handling"""
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
            
        # Process submissions to extract media URLs
        processed_data = []
        for sub in submissions:
            record = {}
            for key, value in sub.items():
                # Handle nested fields
                if isinstance(value, dict):
                    for nested_key, nested_value in value.items():
                        # Check for media attachments
                        if nested_key == 'filename' and 'download_url' in value:
                            record[key] = f"[Media File]({value['download_url']})"
                        else:
                            record[f"{key}.{nested_key}"] = nested_value
                else:
                    record[key] = value
            processed_data.append(record)
        
        df = pd.DataFrame(processed_data)
        return df
        
    except Exception as e:
        st.error(f"Error fetching data: {str(e)}")
        return None

def display_media(row):
    """Display media files from a row of data"""
    media_columns = [col for col in row.index if any(x in str(col).lower() for x in ['image', 'photo', 'video', 'audio'])]
    
    for col in media_columns:
        if pd.notna(row[col]) and ('http' in str(row[col])):
            st.write(f"**{col}**")
            if any(ext in str(row[col]).lower() for ext in ['.jpg', '.jpeg', '.png', '.gif']):
                st.image(row[col])
            elif any(ext in str(row[col]).lower() for ext in ['.mp4', '.mov', '.avi']):
                st.video(row[col])
            elif any(ext in str(row[col]).lower() for ext in ['.mp3', '.wav', '.ogg']):
                st.audio(row[col])
            else:
                st.markdown(f"[Download File]({row[col]})")

def main():
    st.title("Kobo Toolbox Data Dashboard with Media")
    
    with st.spinner("Loading data..."):
        df = fetch_kobo_data()
    
    if df is None:
        st.error("Failed to fetch data")
        return
    elif df.empty:
        st.warning("No submissions found")
        return
    
    st.success(f"Loaded {len(df)} submissions")
    
    # Show data table
    st.subheader("All Data")
    st.dataframe(df)
    
    # Show media files for selected record
    st.subheader("Media Viewer")
    selected_index = st.selectbox("Select a record to view media", range(len(df)))
    
    display_media(df.iloc[selected_index])

if __name__ == "__main__":
    main()

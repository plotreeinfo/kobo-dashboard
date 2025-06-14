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
    """Fetch data directly from Kobo Toolbox in its original format"""
    try:
        # Get credentials from secrets
        api_token = st.secrets["KOBO_API_TOKEN"]
        form_uid = st.secrets["FORM_UID"]
        
        # API endpoints
        KOBO_API_URL = "https://kf.kobotoolbox.org"
        DATA_URL = f"{KOBO_API_URL}/api/v2/assets/{form_uid}/data/"
        
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
            
        # Process attachments to get direct download URLs
        for submission in submissions:
            if '_attachments' in submission:
                for attachment in submission['_attachments']:
                    # Create direct download URL (this is the correct format)
                    attachment['direct_download_url'] = f"{KOBO_API_URL}/media/original?media_file={attachment['filename']}"
        
        return submissions
        
    except Exception as e:
        st.error(f"Error fetching data: {str(e)}")
        return None

def display_kobo_table(submissions):
    """Display data exactly like Kobo Toolbox interface"""
    if not submissions:
        return
    
    st.subheader("Kobo Toolbox Data (Original Format)")
    
    # Create expandable sections for each submission
    for i, submission in enumerate(submissions, 1):
        with st.expander(f"Submission #{i} - {submission.get('_submission_time', '')}"):
            # Display all fields
            for key, value in submission.items():
                if key == '_attachments':
                    st.markdown("**Attachments:**")
                    cols = st.columns(3)
                    for j, attachment in enumerate(value):
                        with cols[j % 3]:
                            st.markdown(f"""
                            **{attachment['filename']}**  
                            Size: {round(attachment.get('filesize', 0)/1024:.1f} KB  
                            [Download]({attachment['direct_download_url']})
                            """)
                elif isinstance(value, dict):
                    st.markdown(f"**{key}:**")
                    st.json(value)
                else:
                    st.markdown(f"**{key}:** {value}")
    
    # Add CSV download button
    csv_data = pd.json_normalize(submissions).to_csv(index=False)
    st.download_button(
        label="Download All Data as CSV",
        data=csv_data,
        file_name=f'kobo_data_{datetime.now().strftime("%Y%m%d")}.csv',
        mime='text/csv'
    )

def main():
    st.title("Kobo Toolbox Data Viewer")
    
    with st.spinner("Loading data directly from Kobo Toolbox..."):
        submissions = fetch_kobo_data()
    
    if submissions is None:
        st.error("Failed to fetch data. Please check:")
        st.markdown("""
        - API token is correct in secrets.toml
        - Form UID is correct
        - You have internet connection
        """)
    elif not submissions:
        st.warning("No submissions found in this form")
    else:
        st.success(f"Loaded {len(submissions)} submissions")
        display_kobo_table(submissions)

if __name__ == "__main__":
    main()

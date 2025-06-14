import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import json

# Configure the page to look like Kobo Toolbox
st.set_page_config(
    page_title="Kobo Data Viewer",
    layout="wide",
    page_icon="📋"
)

# Add custom CSS to match Kobo's style
st.markdown("""
<style>
    .stDataFrame {
        font-family: Arial, sans-serif;
    }
    .stDownloadButton button {
        background-color: #f63366;
        color: white;
    }
    .stAlert {
        font-family: Arial, sans-serif;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=3600)
def fetch_kobo_data():
    """Fetch data from Kobo Toolbox API with proper error handling"""
    try:
        # API configuration
        KOBO_URL = "https://kf.kobotoolbox.org"
        ENDPOINT = f"/api/v2/assets/{st.secrets['FORM_UID']}/data/"
        
        # Make the request
        response = requests.get(
            KOBO_URL + ENDPOINT,
            headers={
                "Authorization": f"Token {st.secrets['KOBO_API_TOKEN']}",
                "Accept": "application/json"
            }
        )
        response.raise_for_status()
        
        # Process the response
        data = response.json()
        submissions = data.get('results', [])
        
        # Process attachments to create direct download links
        for submission in submissions:
            if '_attachments' in submission:
                for attachment in submission['_attachments']:
                    # Create the correct download URL format
                    attachment['download_link'] = (
                        f"{KOBO_URL}/media/original?media_file="
                        f"{attachment['filename']}"
                    )
        
        return submissions
        
    except requests.exceptions.RequestException as e:
        st.error(f"API request failed: {str(e)}")
        if hasattr(e, 'response'):
            st.error(f"Status code: {e.response.status_code}")
            st.error(f"Response: {e.response.text[:500]}")
        return None

def display_kobo_table(submissions):
    """Display the data exactly like Kobo Toolbox interface"""
    if not submissions:
        st.warning("No submissions found in this form")
        return
    
    # Create a DataFrame that matches Kobo's display
    table_data = []
    for sub in submissions:
        row = {
            "ID": sub.get('_id'),
            "Submission Date": sub.get('_submission_time'),
            "Status": sub.get('_validation_status', {}).get('label', 'Not validated')
        }
        
        # Add all survey questions
        for key, value in sub.items():
            if not key.startswith('_'):
                if isinstance(value, dict):
                    row[key] = json.dumps(value)
                else:
                    row[key] = value
        
        # Format attachments
        if '_attachments' in sub:
            attachments = []
            for att in sub['_attachments']:
                attachments.append(
                    f"{att['filename']} "
                    f"(<a href='{att['download_link']}' target='_blank'>Download</a>)"
                )
            row['Attachments'] = "<br>".join(attachments)
        
        table_data.append(row)
    
    # Convert to DataFrame
    df = pd.DataFrame(table_data)
    
    # Set ID as the index
    df = df.set_index("ID")
    
    # Display the table
    st.dataframe(
        df,
        height=600,
        use_container_width=True,
        column_config={
            "Attachments": st.column_config.TextColumn("Attachments"),
            "Submission Date": st.column_config.DatetimeColumn("Submission Date")
        }
    )
    
    # Add export buttons
    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            "Download as CSV",
            df.to_csv(),
            "kobo_data.csv",
            "text/csv"
        )
    with col2:
        st.download_button(
            "Download as Excel",
            df.to_excel(),
            "kobo_data.xlsx",
            "application/vnd.ms-excel"
        )

def main():
    st.title("Kobo Toolbox Data Viewer")
    st.write("Displaying data exactly as it appears in Kobo Toolbox")
    
    with st.spinner("Loading data from Kobo Toolbox..."):
        submissions = fetch_kobo_data()
    
    if submissions is None:
        st.error("Failed to fetch data. Please check your credentials and connection.")
    else:
        display_kobo_table(submissions)

if __name__ == "__main__":
    main()

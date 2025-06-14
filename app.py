import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import json
from io import BytesIO

# Configure the page
st.set_page_config(
    page_title="Kobo Data Viewer",
    layout="wide",
    page_icon="📋"
)

# Custom CSS for Kobo-like styling
st.markdown("""
<style>
    .stDataFrame {
        font-family: Arial, sans-serif;
    }
    .stDownloadButton button {
        background-color: #f63366;
        color: white;
    }
    a {
        color: #f63366;
        text-decoration: none;
    }
    a:hover {
        text-decoration: underline;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=3600)
def fetch_kobo_data():
    """Fetch data from Kobo Toolbox API"""
    try:
        KOBO_URL = "https://kf.kobotoolbox.org"
        ENDPOINT = f"/api/v2/assets/{st.secrets['FORM_UID']}/data/"
        
        response = requests.get(
            KOBO_URL + ENDPOINT,
            headers={
                "Authorization": f"Token {st.secrets['KOBO_API_TOKEN']}",
                "Accept": "application/json"
            },
            timeout=30
        )
        response.raise_for_status()
        
        data = response.json()
        submissions = data.get('results', [])
        
        # Process attachments
        for submission in submissions:
            if '_attachments' in submission:
                for attachment in submission['_attachments']:
                    attachment['download_link'] = (
                        f"{KOBO_URL}/media/original?media_file="
                        f"{attachment['filename']}"
                    )
        
        return submissions
        
    except Exception as e:
        st.error(f"Failed to fetch data: {str(e)}")
        return None

def create_dataframe(submissions):
    """Convert submissions to properly formatted DataFrame"""
    if not submissions:
        return pd.DataFrame()
    
    table_data = []
    for sub in submissions:
        row = {
            "ID": sub.get('_id'),
            "Submission Date": sub.get('_submission_time'),
            "Status": sub.get('_validation_status', {}).get('label', 'Not validated')
        }
        
        # Add survey questions
        for key, value in sub.items():
            if not key.startswith('_'):
                row[key] = str(value) if isinstance(value, (dict, list)) else value
        
        # Format attachments
        if '_attachments' in sub:
            attachments = []
            for att in sub['_attachments']:
                attachments.append(
                    f"{att['filename']} [Download]({att['download_link']})"
                )
            row['Attachments'] = "  \n".join(attachments)
        
        table_data.append(row)
    
    return pd.DataFrame(table_data).set_index("ID")

def display_table(df):
    """Display the DataFrame with proper formatting"""
    st.dataframe(
        df,
        height=600,
        use_container_width=True,
        column_config={
            "Attachments": st.column_config.TextColumn("Attachments"),
            "Submission Date": st.column_config.DatetimeColumn("Submission Date")
        }
    )

def get_excel_bytes(df):
    """Convert DataFrame to Excel bytes with error handling"""
    try:
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=True)
        return output.getvalue()
    except Exception as e:
        st.error(f"Failed to create Excel file: {str(e)}")
        return None

def main():
    st.title("Kobo Toolbox Data Viewer")
    
    with st.spinner("Loading data from Kobo Toolbox..."):
        submissions = fetch_kobo_data()
    
    if submissions is None:
        st.error("Data loading failed. Please check your connection and credentials.")
        return
    
    df = create_dataframe(submissions)
    
    if df.empty:
        st.warning("No submissions found in this form")
        return
    
    display_table(df)
    
    # Export buttons
    col1, col2 = st.columns(2)
    
    with col1:
        st.download_button(
            "Download as CSV",
            df.to_csv(),
            "kobo_data.csv",
            "text/csv"
        )
    
    with col2:
        excel_bytes = get_excel_bytes(df)
        if excel_bytes:
            st.download_button(
                "Download as Excel",
                excel_bytes,
                "kobo_data.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

if __name__ == "__main__":
    main()

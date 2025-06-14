import streamlit as st
import requests
import pandas as pd
from datetime import datetime
from io import BytesIO

# ===============================
# 🔐 Credentials (Hardcoded for local/dev use)
# ===============================
KOBO_USERNAME = "plotree"
KOBO_API_TOKEN = "04714621fa3d605ff0a4aa5cc2df7cfa961bf256"
FORM_UID = "aJHsRZXT3XEpCoxn9Ct3qZ"
KOBO_URL = "https://kf.kobotoolbox.org"

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
        ENDPOINT = f"/api/v2/assets/{FORM_UID}/data/"
        response = requests.get(
            KOBO_URL + ENDPOINT,
            headers={
                "Authorization": f"Token {KOBO_API_TOKEN}",
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
                        f"{KOBO_URL}/media/original?media_file={attachment['filename']}"
                    )
        return submissions

    except Exception as e:
        st.error(f"Failed to fetch data: {str(e)}")
        return None

def create_dataframe(submissions):
    """Convert submissions to properly formatted DataFrame with selected columns"""
    if not submissions:
        return pd.DataFrame()
    
    table_data = []
    for sub in submissions:
        row = {
            "SubmissionDate": sub.get('_submission_time'),
            "Name": sub.get('name'),
            "Gender": sub.get('gender'),
            "Age": sub.get('age'),
            "Location": sub.get('location'),
            "Photo": "",  # Placeholder for attachment URL
            "Feedback": sub.get('feedback')
        }

        # Handle attachment (e.g., photo)
        if '_attachments' in sub:
            photos = []
            for att in sub['_attachments']:
                link = f"{att['filename']} [Download]({att['download_link']})"
                photos.append(link)
            row["Photo"] = "  \n".join(photos)
        
        table_data.append(row)
    
    return pd.DataFrame(table_data)

def display_table(df):
    """Display the DataFrame with proper formatting"""
    st.dataframe(
        df,
        height=600,
        use_container_width=True,
        column_config={
            "Photo": st.column_config.TextColumn("Photo"),
            "SubmissionDate": st.column_config.DatetimeColumn("Submission Date")
        }
    )

def get_excel_bytes(df):
    """Convert DataFrame to Excel bytes with error handling"""
    try:
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='KoboData')
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
            df.to_csv(index=False),
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

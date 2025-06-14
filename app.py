import streamlit as st
import requests
import pandas as pd
from io import BytesIO

# Set page configuration
st.set_page_config(
    page_title="Kobo Data Viewer",
    layout="wide",
    page_icon="📋"
)

# Custom CSS
st.markdown("""
<style>
    .stDataFrame {
        font-family: Arial, sans-serif;
    }
    .stDownloadButton button {
        background-color: #f63366;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# Kobo credentials
KOBO_API_TOKEN = "04714621fa3d605ff0a4aa5cc2df7cfa961bf256"
FORM_UID = "aJHsRZXT3XEpCoxn9Ct3qZ"
KOBO_URL = "https://kf.kobotoolbox.org"

# Column order and headers from uploaded Excel
expected_columns = [
    'Submission Date', 'start', 'end', 'today', 'deviceid', 'subscriberid', 'simid', 'phonenumber',
    'username', 'email', 'What is the name of the area/locality?',
    'Which Union Council does this area fall in?',
    'Is this area part of a katchi abadi or informal settlement?',
    'How many households live in this area?',
    'How many households are there in this enumeration area?',
    'What is the estimated population of the area?',
    'How many members are there in a typical household in this area?',
    'What is the main drinking water source for most households?',
    'Do all households have the same type of drinking water source?',
    'Is the drinking water available throughout the day?',
    'What is the approximate time to fetch water (one way)? (in minutes)',
    'Is there a piped water network (public supply) in this area?',
    'Does every household have a water meter?',
    'What is the per month water bill (if any)?',
    'Do you face issues with water quality (colour/smell/taste)?',
    'What is the most common toilet facility used by most households?',
    'Where does the waste from toilets go?',
    'Is the containment shared by multiple households?',
    'Does it overflow during rains?',
    'How often is the containment emptied?',
    'How much is the average cost of emptying?',
    'What is the disposal point of emptied waste?',
    'Do you see sewage or wastewater in the streets?',
    'Is there a drainage system for wastewater in this area?',
    'Where does the wastewater from households flow into?',
    'Is solid waste collected in this area?',
    'Who collects solid waste?',
    'How often is it collected?',
    'Is there an open garbage dumping point in the area?',
    'Upload images from the area',
    'Photo: Images from the area [file URL]',
    'Submission ID'
]

@st.cache_data(ttl=180)
def fetch_kobo_data():
    url = f"{KOBO_URL}/api/v2/assets/{FORM_UID}/data/"
    headers = {
        "Authorization": f"Token {KOBO_API_TOKEN}",
        "Accept": "application/json"
    }

    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    results = response.json().get("results", [])

    data_rows = []
    for item in results:
        row = {}

        row['Submission Date'] = item.get('_submission_time')
        row['Submission ID'] = item.get('_id')

        # Direct field mappings
        for col in expected_columns:
            if col in ['Submission Date', 'Submission ID', 'Photo: Images from the area [file URL]']:
                continue
            if col in item:
                row[col] = item[col]
        
        # Handle attachments
        image_url = None
        if '_attachments' in item and len(item['_attachments']) > 0:
            attachment = item['_attachments'][0]
            image_url = f"{KOBO_URL}/media/original?media_file={attachment['filename']}"
        row['Photo: Images from the area [file URL]'] = image_url

        data_rows.append(row)

    df = pd.DataFrame(data_rows)

    # Ensure full column structure and order
    for col in expected_columns:
        if col not in df.columns:
            df[col] = None

    df = df[expected_columns]
    return df

def get_excel_bytes(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Kobo Data')
    return output.getvalue()

def main():
    st.title("📋 KoboToolbox Data Dashboard")

    with st.spinner("Fetching data..."):
        try:
            df = fetch_kobo_data()
        except Exception as e:
            st.error(f"Error fetching data: {str(e)}")
            return

    st.success("Data loaded successfully!")

    # Show data table
    st.dataframe(df, use_container_width=True, height=600)

    # Download buttons
    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            "Download as CSV",
            df.to_csv(index=False),
            "kobo_data.csv",
            "text/csv"
        )
    with col2:
        st.download_button(
            "Download as Excel",
            get_excel_bytes(df),
            "kobo_data.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

if __name__ == "__main__":
    main()

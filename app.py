import streamlit as st
import pandas as pd
import requests
from io import BytesIO

# KoBo API Config
KOBO_TOKEN = "04714621fa3d605ff0a4aa5cc2df7cfa961bf256"
EXPORT_URL = "https://kf.kobotoolbox.org/api/v2/assets/aJHsRZXT3XEpCoxn9Ct3qZ/export-settings/esnia8U2QVxNnjzMY4p87ss/data.xlsx"

# Streamlit Page Settings
st.set_page_config(page_title="📊 KoBo Dashboard", layout="wide")
st.title("📥 Onsite Sanitation KoBo Data")

# Download & Parse Excel
@st.cache_data(show_spinner="Fetching data from KoBoToolbox...")
def fetch_kobo_data():
    headers = {"Authorization": f"Token {KOBO_TOKEN}"}
    try:
        response = requests.get(EXPORT_URL, headers=headers, timeout=20)
        response.raise_for_status()

        if "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" not in response.headers.get("Content-Type", ""):
            st.error("❌ Response is not a valid Excel file. Please check your export URL or token.")
            return None

        df = pd.read_excel(BytesIO(response.content))

        # Remove unnamed and empty columns
        df = df.loc[:, ~df.columns.str.contains("^Unnamed")]
        df = df.dropna(axis=1, how='all')

        return df

    except requests.exceptions.Timeout:
        st.error("⏱️ Request timed out. Please try again later.")
    except requests.exceptions.RequestException as e:
        st.error(f"❌ Request failed: {e}")
    except Exception as e:
        st.error(f"❌ Unexpected error: {e}")
    return None

# Load Data
df = fetch_kobo_data()

if df is not None and not df.empty:
    st.success("✅ Data loaded successfully.")
    st.subhe

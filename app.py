import streamlit as st
import pandas as pd
import requests
from io import BytesIO

# --- KoBo API Configuration ---
KOBO_TOKEN = "04714621fa3d605ff0a4aa5cc2df7cfa961bf256"
EXPORT_URL = "https://kf.kobotoolbox.org/api/v2/assets/aJHsRZXT3XEpCoxn9Ct3qZ/export-settings/esnia8U2QVxNnjzMY4p87ss/data.xlsx"

# --- Streamlit UI Setup ---
st.set_page_config(page_title="📊 KoBo Dashboard", layout="wide")
st.title("📥 Onsite Sanitation KoBo Data")

# --- Fetch and Clean Data ---
@st.cache_data(show_spinner="Loading data from KoBoToolbox...")
def fetch_kobo_data():
    headers = {"Authorization": f"Token {KOBO_TOKEN}"}
    try:
        response = requests.get(EXPORT_URL, headers=headers)
        response.raise_for_status()
        df = pd.read_excel(BytesIO(response.content))
        df = df.loc[:, ~df.columns.str.contains("^Unnamed")]  # Remove unnamed columns
        df = df.dropna(axis=1, how='all')                     # Drop completely empty columns
        return df
    except requests.exceptions.RequestException as e:
        st.error(f"❌ Request failed: {e}")
        return None
    except Exception as e:
        st.error(f"❌ Unexpected error: {e}")
        return None

df = fetch_kobo_data()

# --- Display Table with Filters ---
if df is not None:
    st.success("✅ Data loaded successfully.")
    st.subheader("🔍 Filter & View Data")

    with st.expander("🔧 Filter Optio

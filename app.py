import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# Set page config
st.set_page_config(page_title="Onsite Sanitation Dashboard", layout="wide")
st.title("📊 KoBoToolbox Form Submissions Dashboard")

# ---- Configuration (NO NEED FOR USER INPUT) ----
# You can hardcode your API token and form UID here
API_TOKEN = "04714621fa3d605ff0a4aa5cc2df7cfa961bf256"
FORM_UID = "aJHsRZXT3XEpCoxn9Ct3qZ"

# ---- API Request Setup ----
HEADERS = {
    "Authorization": f"Token {API_TOKEN}",
    "Accept": "application/json"
}
BASE_URL = f"https://kf.kobotoolbox.org/api/v2/assets/{FORM_UID}/data/?format=json"

@st.cache_data(ttl=3600)
def fetch_kobo_data():
    all_results = []
    next_url = BASE_URL
    while next_url:
        response = requests.get(next_url, headers=HEADERS)
        if response.status_code != 200:
            st.error(f"Failed to fetch data: {response.status_code}")
            st.stop()
        data = response.json()
        all_results.extend(data.get("results", []))
        next_url = data.get("next")
    return pd.DataFrame(all_results)

# ---- Load and Display Data ----
with st.spinner("Fetching data from KoBoToolbox..."):
    df = fetch_kobo_data()

if df.empty:
    st.warning("No data found for the given form UID.")
else:
    df["_submission_time"] = pd.to_datetime(df["_submission_time"]).dt.tz_localize(None)

    # Optional date filter
    st.sidebar.header("📅 Date Filter")
    start_date = st.sidebar.date_input("Start Date", value=None)
    end_date = st.sidebar.date_input("End Date", value=None)

    if start_date:
        df = df[df["_submission_time"].dt.date >= start_date]
    if end_date:
        df = df[df["_submission_time"].dt.date <= end_date]

    # Rename columns
    rename_map = {
        "_submission_time": "Submission Time",
        "_id": "Submission ID",
        "_uuid": "UUID",
        "_submitted_by": "Submitted By",
        # Add more field mappings as needed
    }
    df.rename(columns=rename_map, inplace=True)

    # Select columns to display
    st.sidebar.header("📑 Column Selection")
    selected_columns = st.sidebar.multiselect(
        "Choose columns to display:", df.columns.tolist(), default=df.columns.tolist()
    )

    st.subheader("🗂️ Submissions Table")
    st.dataframe(df[selected_columns], use_container_width=True)

    st.download_button(
        label="📥 Download CSV",
        data=df[selected_columns].to_csv(index=False).encode("utf-8"),
        file_name="kobo_submissions.csv",
        mime="text/csv"
    )

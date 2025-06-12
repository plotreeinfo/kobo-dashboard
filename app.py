import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# Streamlit app title
st.set_page_config(page_title="KoBo Data Viewer", layout="wide")
st.title("📊 KoBoToolbox Form Submissions Dashboard")

# Sidebar for credentials and form UID
st.sidebar.header("🔐 KoBo API Authentication")
api_token = st.sidebar.text_input("API Token", type="password")
form_uid = st.sidebar.text_input("Form UID (e.g. aA1b2C3d4E5)")

# Optional: start and end date filters
start_date = st.sidebar.date_input("Start Date", value=None)
end_date = st.sidebar.date_input("End Date", value=None)

@st.cache_data(ttl=3600)
def fetch_kobo_data(form_uid, api_token):
    """Fetch all KoBoToolbox form submissions using the API v2."""
    headers = {
        "Authorization": f"Token {api_token}",
        "Accept": "application/json"
    }
    url = f"https://kf.kobotoolbox.org/api/v2/assets/{form_uid}/data/?format=json"

    all_results = []
    while url:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            st.error(f"Failed to fetch data. Status code: {response.status_code}")
            st.stop()

        data = response.json()
        all_results.extend(data.get("results", []))
        url = data.get("next")

    return pd.DataFrame(all_results)

# Load and display data
if api_token and form_uid:
    with st.spinner("Fetching data..."):
        df = fetch_kobo_data(form_uid, api_token)

    if df.empty:
        st.warning("No data found for this form.")
    else:
        # Convert submission time
        df["_submission_time"] = pd.to_datetime(df["_submission_time"]).dt.tz_localize(None)

        # Apply date filtering
        if start_date:
            df = df[df["_submission_time"].dt.date >= start_date]
        if end_date:
            df = df[df["_submission_time"].dt.date <= end_date]

        # Rename selected columns (example: modify this as needed)
        col_mapping = {
            "_submission_time": "Submission Time",
            "_id": "Submission ID",
            "_uuid": "UUID",
            "_submitted_by": "Submitted By",
            # Add more mappings based on your actual form field names
            # "your_field_key_here": "Friendly Field Name",
        }
        df.rename(columns=col_mapping, inplace=True)

        # Show column selection
        st.sidebar.subheader("📑 Column Selection")
        columns_to_display = st.sidebar.multiselect(
            "Select columns to display", df.columns.tolist(), default=df.columns.tolist()
        )

        # Display data table
        st.subheader("🗃️ Filtered Form Submissions")
        st.dataframe(df[columns_to_display], use_container_width=True)

        # Download button
        st.download_button(
            label="📥 Download CSV",
            data=df[columns_to_display].to_csv(index=False).encode("utf-8"),
            file_name="kobo_form_data.csv",
            mime="text/csv",
        )
else:
    st.info("Please enter your KoBo API Token and Form UID in the sidebar.")

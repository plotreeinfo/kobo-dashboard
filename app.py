import streamlit as st
import pandas as pd
import requests
import time
from io import BytesIO

# --- KoBo settings ---
KOBO_API_TOKEN = "04714621fa3d605ff0a4aa5cc2df7cfa961bf256"
FORM_UID = "aJHsRZXT3XEpCoxn9Ct3qZ"
KOBO_BASE_URL = "https://kf.kobotoolbox.org"

HEADERS = {
    "Authorization": f"Token {KOBO_API_TOKEN}"
}

# --- Function to create KoBo export (XLS or CSV) with your settings ---
def create_export(format="xls"):
    export_url = f"{KOBO_BASE_URL}/api/v2/assets/{FORM_UID}/export_settings/"
    payload = {
        "export_type": format,
        "include_labels": True,
        "use_display_names": True,
        "group_sep": "/",
        "remove_group_names": True,
        "split_select_multiples": True,
        "include_media": True,
        "include_labels_only": True,
        "fields_from_all_versions": False,
        "store_on_device": False,
        "value_select_multiples": False,
        "force_text": True
    }

    # Step 1: Create export task
    response = requests.post(export_url, headers=HEADERS, json=payload)
    if response.status_code != 201:
        st.error(f"❌ Export failed: {response.status_code} - {response.text}")
        return None

    export_id = response.json().get("uid")
    download_url = f"{KOBO_BASE_URL}/api/v2/assets/{FORM_UID}/exports/{export_id}/"

    # Step 2: Wait for export to finish
    for _ in range(10):
        status = requests.get(download_url, headers=HEADERS).json()
        if status["status"] == "complete":
            return status["result"]["url"]
        time.sleep(1)

    st.error("❌ Export timed out")
    return None

# --- Load XLS from KoBo and return DataFrame ---
@st.cache_data(show_spinner=False)
def load_exported_data():
    file_url = create_export("xls")
    if not file_url:
        return pd.DataFrame()

    response = requests.get(file_url)
    if response.status_code != 200:
        st.error("❌ Failed to download XLS file")
        return pd.DataFrame()

    xls_data = BytesIO(response.content)
    df = pd.read_excel(xls_data)

    # Drop metadata fields
    unwanted = ["start", "end", "_id", "_uuid", "_validation_status", "_notes",
                "_status", "_submitted_by", "_tags", "__version__"]
    df.drop(columns=[col for col in unwanted if col in df.columns], errors="ignore", inplace=True)

    return df

# --- Streamlit Dashboard ---
st.set_page_config("KoBo Dashboard", layout="wide")
st.title("📋 KoBoToolbox Form Data Viewer")

if 'df' not in st.session_state:
    st.session_state.df = pd.DataFrame()

if st.button("🔄 Load Latest Data"):
    with st.spinner("Fetching data..."):
        df = load_exported_data()
        if not df.empty:
            st.session_state.df = df
            st.success(f"✅ {len(df)} records loaded.")
        else:
            st.warning("⚠️ No data found.")

if not st.session_state.df.empty:
    df = st.session_state.df

    # Optional: Filter interface
    col_to_filter = st.selectbox("🔍 Filter by column", df.columns)
    filter_val = st.text_input("Enter value to filter")

    if filter_val:
        df = df[df[col_to_filter].astype(str).str.contains(filter_val, case=False, na=False)]

    st.dataframe(df, use_container_width=True)

    # Download options
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("⬇️ Download as CSV", csv, "filtered_data.csv", "text/csv")

    xls_output = BytesIO()
    df.to_excel(xls_output, index=False)
    st.download_button("⬇️ Download as Excel", xls_output.getvalue(), "filtered_data.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

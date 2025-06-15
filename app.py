import streamlit as st
import pandas as pd
import requests
import time
from io import BytesIO

# KoBo Credentials
KOBO_API_TOKEN = "04714621fa3d605ff0a4aa5cc2df7cfa961bf256"
FORM_UID = "aJHsRZXT3XEpCoxn9Ct3qZ"
KOBO_BASE_URL = "https://kf.kobotoolbox.org"

HEADERS = {"Authorization": f"Token {KOBO_API_TOKEN}"}

# --- Create Export using standard KoBo export API ---
def create_export(format="xls"):
    url = f"{KOBO_BASE_URL}/api/v2/assets/{FORM_UID}/exports/"

    payload = {
        "type": format,
        "language": "English",
        "fields_from_all_versions": False,
        "hierarchy_in_labels": True,
        "group_sep": "/",
        "value_select_multiples": False,
        "format": "xlsx",
        "split_select_multiples": True,
        "include_labels": True,
        "include_media": True
    }

    res = requests.post(url, headers=HEADERS, json=payload)
    if res.status_code != 201:
        st.error(f"❌ Export failed: {res.status_code} - {res.text[:200]}")
        return None

    export_id = res.json().get("uid")
    poll_url = f"{url}{export_id}/"

    # Wait for export to be ready
    for _ in range(20):
        status = requests.get(poll_url, headers=HEADERS).json()
        if status["status"] == "complete":
            return status["result"]["url"]
        time.sleep(1)

    st.error("❌ Export timed out.")
    return None

# --- Load exported Excel file ---
@st.cache_data(show_spinner=False)
def load_kobo_xls():
    export_url = create_export("xls")
    if not export_url:
        return pd.DataFrame()

    res = requests.get(export_url)
    if res.status_code != 200:
        st.error("❌ Failed to download XLS.")
        return pd.DataFrame()

    return pd.read_excel(BytesIO(res.content))

# --- Streamlit App Layout ---
st.set_page_config("KoBo Viewer", layout="wide")
st.title("📋 KoBoToolbox Dashboard")

if st.button("🔄 Load KoBo Data"):
    with st.spinner("Fetching data..."):
        df = load_kobo_xls()

        if not df.empty:
            st.session_state.df = df
            st.success(f"✅ {len(df)} records loaded.")
        else:
            st.warning("⚠️ No data found.")

if "df" in st.session_state:
    df = st.session_state.df

    # Drop KoBo metadata columns
    unwanted = ["start", "end", "_id", "_uuid", "_validation_status", "_notes",
                "_status", "_submitted_by", "_tags", "__version__"]
    df.drop(columns=[c for c in unwanted if c in df.columns], inplace=True, errors="ignore")

    # Filter UI
    col = st.selectbox("🔍 Filter column", df.columns)
    val = st.text_input("Filter value")
    if val:
        df = df[df[col].astype(str).str.contains(val, na=False, case=False)]

    st.dataframe(df, use_container_width=True)

    # Download Buttons
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Download CSV", csv, "filtered_data.csv", "text/csv")

    xls_buffer = BytesIO()
    df.to_excel(xls_buffer, index=False)
    st.download_button("⬇️ Download XLSX", xls_buffer.getvalue(), "filtered_data.xlsx",
                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

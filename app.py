import streamlit as st
import pandas as pd
import requests
import io
import time
from datetime import datetime
from requests.auth import HTTPBasicAuth

# ============================
# CONFIGURATION
# ============================
KOBO_USERNAME = "plotree"
KOBO_PASSWORD = "Pl@tr33@123"
FORM_UID = "aJHsRZXT3XEpCoxn9Ct3qZ"
BASE_URL = "https://kf.kobotoolbox.org"
API_URL = f"{BASE_URL}/api/v2/assets/{FORM_UID}/data.json"
EXPORT_URL = f"{BASE_URL}/api/v2/assets/{FORM_UID}/exports/"

# ============================
# UI STYLING
# ============================
hide_streamlit_style = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# ============================
# FUNCTIONS
# ============================
@st.cache_data(ttl=3600)
def fetch_kobo_data():
    try:
        response = requests.get(API_URL, auth=HTTPBasicAuth(KOBO_USERNAME, KOBO_PASSWORD))
        response.raise_for_status()
        data = response.json().get("results", [])
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Failed to load data: {str(e)}")
        return pd.DataFrame()

def trigger_kobo_export(export_type="xls", lang="English", include_media=True,
                         split_select_multiples=True, group_sep="/", hierarchy_labels=True):
    payload = {
        "type": export_type,
        "fields_from_all_versions": "true",
        "group_sep": group_sep,
        "hierarchy_in_labels": str(hierarchy_labels).lower(),
        "include_media_urls": str(include_media).lower(),
        "lang": lang,
        "split_select_multiples": str(split_select_multiples).lower(),
        "value_select_multiples": "both"
    }
    response = requests.post(EXPORT_URL, auth=HTTPBasicAuth(KOBO_USERNAME, KOBO_PASSWORD), json=payload)
    if response.status_code == 201:
        return response.json().get('url')
    else:
        st.error(f"Export request failed: {response.status_code} - {response.text}")
        return None

def check_export_status(export_url):
    response = requests.get(export_url, auth=HTTPBasicAuth(KOBO_USERNAME, KOBO_PASSWORD))
    if response.status_code == 200:
        return response.json().get('status'), response.json().get('result')
    return None, None

# ============================
# MAIN APP
# ============================
st.title("📊 KoboToolbox Dashboard with Export Options")
df = fetch_kobo_data()

if df.empty:
    st.warning("No data available.")
    st.stop()

# Show interactive table with download options
st.subheader("🔍 Data Table")
st.dataframe(df, use_container_width=True)

# ============================
# EXPORT OPTIONS
# ============================
st.subheader("📤 Export Kobo Data")
with st.form("export_form"):
    export_type = st.selectbox("Export Format", ["xls", "csv", "zip"])
    lang = st.selectbox("Language for Labels", ["English", "Urdu", "xml"])
    media = st.checkbox("Include Media URLs", value=True)
    split_cols = st.radio("Select Multiple Questions Format", ["Single Column", "Separate Columns"])
    submit = st.form_submit_button("Trigger Kobo Export")

    if submit:
        with st.spinner("Requesting Kobo export..."):
            export_url = trigger_kobo_export(
                export_type=export_type,
                lang=lang,
                include_media=media,
                split_select_multiples=(split_cols == "Separate Columns")
            )
            if export_url:
                status_bar = st.progress(0)
                status_text = st.empty()
                for i in range(30):
                    status, result_url = check_export_status(export_url)
                    if status == "complete":
                        status_bar.progress(100)
                        status_text.success("✅ Export ready")
                        st.markdown(
                            f'<a href="{BASE_URL}{result_url}" download>📥 Click to Download</a>',
                            unsafe_allow_html=True
                        )
                        break
                    elif status == "error":
                        status_text.error("Export failed.")
                        break
                    else:
                        status_bar.progress(int((i+1) * 3.3))
                        status_text.info(f"Status: {status}...")
                        time.sleep(10)
                else:
                    status_text.warning("Export taking too long. Check later on KoboToolbox.")

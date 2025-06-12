import streamlit as st
import pandas as pd
import requests
import io
import time
from datetime import datetime
from requests.auth import HTTPBasicAuth

# ==============================================
# CONFIGURATION
# ==============================================

# Hide Streamlit style elements
hide_streamlit_style = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# KoboToolbox API configuration
FORM_UID = "aJHsRZXT3XEpCoxn9Ct3qZ"
BASE_URL = "https://kf.kobotoolbox.org"
API_URL = f"{BASE_URL}/api/v2/assets/{FORM_UID}/data.json"
EXPORT_URL = f"{BASE_URL}/api/v2/assets/{FORM_UID}/exports/"

# ⚠️ Replace this with your actual Kobo API Token
KOBO_TOKEN = "04714621fa3d605ff0a4aa5cc2df7cfa961bf256"  # Replace this with your real token

# ==============================================
# FUNCTIONS
# ==============================================

@st.cache_data(ttl=3600)
def fetch_kobo_data(token):
    try:
        headers = {'Authorization': token}
        response = requests.get(API_URL, headers=headers)
        response.raise_for_status()
        data = response.json().get("results", [])
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Failed to load data: {str(e)}")
        return pd.DataFrame()

def clean_kobo_dataframe(df):
    # Drop metadata columns (those starting with '_')
    return df[[col for col in df.columns if not col.startswith('_')]]

def reorder_columns(df, priority_cols=None):
    if priority_cols is None:
        priority_cols = ["submission_date", "enumerator_name", "location"]
    existing_priority = [col for col in priority_cols if col in df.columns]
    remaining = [col for col in df.columns if col not in existing_priority]
    return df[existing_priority + remaining]

def convert_media_links(df):
    for col in df.columns:
        if df[col].astype(str).str.startswith("http").any():
            df[col] = df[col].apply(lambda x: f"[View]({x})" if isinstance(x, str) and x.startswith("http") else x)
    return df

def trigger_kobo_export(token, export_type="xls", lang="English", select_multiple_format="separate", format_option="xml", include_media=True, group_sep="/", field_as_text=True):
    headers = {'Authorization': token}
    payload = {
        "type": export_type,
        "lang": lang,
        "group_sep": group_sep,
        "include_labels": format_option == "labels",
        "value_select_multiples": select_multiple_format,
        "include_media_urls": include_media,
        "xls_field_as_text": field_as_text,
        "hierarchy_in_labels": True
    }
    response = requests.post(EXPORT_URL, headers=headers, json=payload)
    if response.status_code == 201:
        return response.json().get('url')
    else:
        st.error(f"Export request failed: {response.status_code} - {response.text}")
        return None

def check_export_status(token, export_url):
    headers = {'Authorization': token}
    response = requests.get(export_url, headers=headers)
    if response.status_code == 200:
        return response.json().get('status'), response.json().get('result')
    return None, None

# ==============================================
# UI & DASHBOARD
# ==============================================

st.title("📊 KoboToolbox Dashboard")

# Filters
with st.sidebar:
    st.header("⚙️ Export Options")
    export_type = st.selectbox("Export Type", ["xls", "csv"])
    language = st.selectbox("Language", ["English", "Urdu", "XML"])
    format_option = st.selectbox("Header Format", ["xml", "labels"])
    select_multiple_format = st.radio("Select-Many Columns", ["separate", "single"])
    include_media = st.checkbox("Include Media URLs", value=True)
    field_as_text = st.checkbox("Store Numbers as Text", value=True)
    group_sep = st.text_input("Group Separator", value="/")

# Fetch Data
st.subheader("🔍 Data Table (Live from KoboToolbox)")
df = fetch_kobo_data(KOBO_TOKEN)

if df.empty:
    st.warning("No data available - please check your connection or API token.")
    st.stop()

# Clean, reorder, and convert media links
df = clean_kobo_dataframe(df)
df = reorder_columns(df)
df = convert_media_links(df)

# Preview table
st.dataframe(df, use_container_width=True, height=600)

# Export Trigger
st.subheader("📥 KoboToolbox Export")
if st.button("🔁 Generate Export with Options"):
    with st.spinner("Requesting export from KoboToolbox..."):
        export_url = trigger_kobo_export(
            KOBO_TOKEN,
            export_type=export_type,
            lang=language,
            select_multiple_format=select_multiple_format,
            format_option=format_option,
            include_media=include_media,
            group_sep=group_sep,
            field_as_text=field_as_text
        )

        if export_url:
            st.success("Export requested! Checking status...")
            status_bar = st.progress(0)
            status_text = st.empty()

            for i in range(30):
                status, result_url = check_export_status(KOBO_TOKEN, export_url)
                if status == "complete":
                    status_bar.progress(100)
                    status_text.success("✅ Export ready!")
                    st.markdown(
                        f'<a href="{BASE_URL}{result_url}" download>📥 Download Export File</a>',
                        unsafe_allow_html=True
                    )
                    break
                elif status == "error":
                    status_text.error("❌ Export failed")
                    break
                else:
                    status_bar.progress((i + 1) * 3)
                    status_text.text(f"Status: {status}...")
                    time.sleep(10)
            else:
                status_text.warning("⚠️ Export taking too long. Try again later.")

st.success("✅ Dashboard Ready - Customize & Export Kobo Data")

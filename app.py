import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime
from requests.auth import HTTPBasicAuth
import io

# ============================================================
# CONFIGURATION
# ============================================================
KOBO_USERNAME = "plotree"
KOBO_PASSWORD = "Pl@tr33@123"
FORM_UID = "aJHsRZXT3XEpCoxn9Ct3qZ"
BASE_URL = "https://kf.kobotoolbox.org"
DATA_URL = f"{BASE_URL}/api/v2/assets/{FORM_UID}/data.json"
EXPORT_URL = f"{BASE_URL}/api/v2/assets/{FORM_UID}/exports/"

# ============================================================
# HIDE STREAMLIT MENU
# ============================================================
st.markdown("""
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

st.title("📊 KoboToolbox Data Dashboard + Export")

# ============================================================
# DATA LOADING
# ============================================================
@st.cache_data(ttl=3600)
def fetch_kobo_data():
    try:
        res = requests.get(DATA_URL, auth=HTTPBasicAuth(KOBO_USERNAME, KOBO_PASSWORD))
        res.raise_for_status()
        records = res.json().get("results", [])
        return pd.DataFrame(records)
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return pd.DataFrame()

df = fetch_kobo_data()

if df.empty:
    st.warning("No data found.")
    st.stop()

# Standardize columns
if "_submission_time" in df.columns:
    df["submission_date"] = pd.to_datetime(df["_submission_time"])
    df["submission_day"] = df["submission_date"].dt.date

# ============================================================
# SIDEBAR FILTERS
# ============================================================
st.sidebar.title("🔍 Filters")

if "submission_date" in df.columns:
    with st.sidebar.expander("📅 Date Range"):
        min_date = df["submission_date"].min().date()
        max_date = df["submission_date"].max().date()
        selected_range = st.date_input("Date range", (min_date, max_date))
        if len(selected_range) == 2:
            df = df[(df["submission_date"].dt.date >= selected_range[0]) &
                    (df["submission_date"].dt.date <= selected_range[1])]

if "username" in df.columns:
    with st.sidebar.expander("👤 Collectors"):
        users = ['All'] + sorted(df['username'].dropna().unique())
        user_choice = st.selectbox("Select User", users)
        if user_choice != 'All':
            df = df[df['username'] == user_choice]

if "_1_1_Name_of_the_City_" in df.columns:
    with st.sidebar.expander("📍 District"):
        dists = ['All'] + sorted(df['_1_1_Name_of_the_City_'].dropna().unique())
        dist_choice = st.selectbox("Select District", dists)
        if dist_choice != 'All':
            df = df[df['_1_1_Name_of_the_City_'] == dist_choice]

# ============================================================
# DATA TABLE
# ============================================================
st.subheader("🔍 Data Table (Right-click to Export)")
st.dataframe(df, use_container_width=True)

# ============================================================
# EXPORT CONFIG
# ============================================================
st.subheader("📤 KoboToolbox Export Options")

col1, col2 = st.columns(2)

with col1:
    export_type = st.selectbox("Export Type", ["xls", "csv", "json"])
    lang = st.selectbox("Labels Language", ["English", "Urdu", "XML"])
    group_sep = st.text_input("Group Separator", "/")
    select_multiples = st.radio("Select-Multiple Format", ["separate_columns", "single_column"])

with col2:
    hierarchy = st.checkbox("Hierarchy in labels", value=True)
    media_urls = st.checkbox("Include media URLs", value=True)
    store_as_text = st.checkbox("Store dates/numbers as text", value=False)

# Request export
if st.button("🚀 Request Export"):
    with st.spinner("Contacting KoboToolbox..."):
        headers = {'Authorization': f'Token {KOBO_PASSWORD}'}
        payload = {
            "type": export_type,
            "lang": lang,
            "group_sep": group_sep,
            "select_multiples": select_multiples,
            "hierarchy_in_labels": hierarchy,
            "include_media_urls": media_urls,
            "store_formatted_date_and_number": store_as_text
        }
        res = requests.post(EXPORT_URL, headers=headers, json=payload)
        if res.status_code == 201:
            export_url = res.json().get("url")
            st.success("Export initiated. Waiting for completion...")
            for i in range(30):
                status_check = requests.get(export_url, headers=headers)
                if status_check.status_code == 200:
                    status = status_check.json().get("status")
                    if status == "complete":
                        result_url = status_check.json().get("result")
                        st.markdown(f"✅ [Download Export File]({BASE_URL}{result_url})")
                        break
                    elif status == "error":
                        st.error("Export failed.")
                        break
                time.sleep(5)
            else:
                st.warning("Export is still processing. Please try again later.")
        else:
            st.error("Export request failed.")

st.success("✅ Dashboard Ready")

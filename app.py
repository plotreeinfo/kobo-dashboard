import streamlit as st
import pandas as pd
import requests
import io
from requests.auth import HTTPBasicAuth
from datetime import datetime

# --- CONFIG ---
username = "plotree"
password = "Pl@tr33@123"
form_uid = "aJHsRZXT3XEpCoxn9Ct3qZ"
refresh_interval = 180  # 3 minutes in seconds

# Hide Streamlit header, footer, and menu
hide_streamlit_style = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# --- KOBO XLS EXPORT URL ---
xls_url = f"https://kc.kobotoolbox.org/api/v1/data/{form_uid}.xls"
EXPORT_PARAMS = {
    "format": "xls",
    "type": "all",                      # export all submissions
    "lang": "en",                       # labels and values in English
    "group_sep": "/",                  # include groups in header names
    "media_all": "true",               # include media download links
    "fields_from_all_versions": "true",
    "hierarchy_in_labels": "true",
    "value_labels": "false",           # keep values (not labels)
}

# --- LOAD DATA FUNCTION (REFRESH EVERY 3 MINUTES) ---
@st.cache_data(ttl=refresh_interval)
def load_data():
    response = requests.get(xls_url, params=EXPORT_PARAMS, auth=HTTPBasicAuth(username, password))
    if response.status_code == 200:
        excel_data = io.BytesIO(response.content)
        df = pd.read_excel(excel_data)

        # Drop system fields
        system_cols = [
            "_id", "_uuid", "_submission_time", "_validation_status", "_notes", "_status",
            "_submitted_by", "_tags", "_index", "__version__"
        ]
        df = df.drop(columns=[col for col in system_cols if col in df.columns], errors='ignore')

        return df
    else:
        st.error(f"❌ Failed to load XLS data. HTTP {response.status_code}: {response.text}")
        return pd.DataFrame()

# --- LOAD DATA ---
df = load_data()
if df.empty:
    st.stop()

# --- COLUMN CLEANUP ---
if "submission_date" not in df.columns and "start" in df.columns:
    df = df.rename(columns={"start": "submission_date"})

if "submission_date" in df.columns:
    df["submission_date"] = pd.to_datetime(df["submission_date"])
    df["submission_day"] = df["submission_date"].dt.date
    df["submission_month"] = df["submission_date"].dt.month
    df["submission_week"] = df["submission_date"].dt.isocalendar().week

# --- SIDEBAR FILTERS ---
st.sidebar.title("🔍 Filters")

# Date Range
if "submission_date" in df.columns:
    min_date = df["submission_date"].min().date()
    max_date = df["submission_date"].max().date()
    date_range = st.sidebar.date_input(
        "Filter by Date", value=(min_date, max_date), min_value=min_date, max_value=max_date
    )
    if len(date_range) == 2:
        df = df[
            (df["submission_date"].dt.date >= date_range[0]) &
            (df["submission_date"].dt.date <= date_range[1])
        ]

# Location Filters
for loc in ["district", "ward", "village"]:
    if loc in df.columns:
        options = ['All'] + sorted(df[loc].dropna().unique().tolist())
        selection = st.sidebar.selectbox(f"Select {loc.title()}", options)
        if selection != 'All':
            df = df[df[loc] == selection]

# User Filter
if "username" in df.columns:
    usernames = ['All'] + sorted(df["username"].dropna().unique().tolist())
    selected_user = st.sidebar.selectbox("Select Data Collector", usernames)
    if selected_user != 'All':
        df = df[df["username"] == selected_user]

# Photo filter
photo_cols = [col for col in df.columns if 'photo' in col.lower()]
if photo_cols:
    photo_filter = st.sidebar.selectbox("Photo Presence", ["All", "With Photos", "Without Photos"])
    if photo_filter == "With Photos":
        df = df[df[photo_cols].notnull().any(axis=1)]
    elif photo_filter == "Without Photos":
        df = df[df[photo_cols].isnull().all(axis=1)]

# Data completeness filter
completeness_threshold = st.sidebar.slider(
    "Min Data Completeness (%)", min_value=0, max_value=100, value=80
)
row_completeness = df.notnull().mean(axis=1) * 100
df = df[row_completeness >= completeness_threshold]

# --- DASHBOARD HEADER ---
st.title("📊 KoboToolbox XLS Dashboard (Live)")
st.caption(f"⏱️ Auto-refreshes every {refresh_interval // 60} minutes")

# --- METRICS ---
col1, col2, col3 = st.columns(3)
col1.metric("📋 Total Forms", len(df))
today = datetime.now().date()
if "submission_date" in df.columns:
    col2.metric("🕒 Submitted Today", len(df[df["submission_date"].dt.date == today]))
col3.metric("✅ Completeness", f"{round(row_completeness.mean(), 1)}%")

# --- DATA PREVIEW ---
st.subheader("📄 Filtered Data")
st.dataframe(df, use_container_width=True)

# --- DOWNLOADS ---
st.subheader("📥 Download Filtered Data")
csv_data = df.to_csv(index=False).encode('utf-8')
excel_io = io.BytesIO()
df.to_excel(excel_io, index=False, engine='openpyxl')

col1, col2 = st.columns(2)
col1.download_button("⬇️ Download CSV", csv_data, file_name="kobo_data.csv", mime="text/csv")
col2.download_button("⬇️ Download Excel", excel_io.getvalue(), file_name="kobo_data.xlsx",
                     mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# --- SUCCESS ---
st.success("✅ Dashboard is live and synced with XLS export from KoboToolbox")

import streamlit as st
import pandas as pd
import requests
import time
import io
from requests.auth import HTTPBasicAuth
from datetime import datetime

# --- CONFIG ---
username = "plotree"
password = "Pl@tr33@123"
form_uid = "aJHsRZXT3XEpCoxn9Ct3qZ"
base_url = "https://kc.kobotoolbox.org"
refresh_interval = 180  # 3 minutes

# --- AUTH ---
auth = HTTPBasicAuth(username, password)

# --- CREATE XLS EXPORT AND DOWNLOAD ---
@st.cache_data(ttl=refresh_interval)
def fetch_xls_export():
    # Step 1: Create XLS export
    export_url = f"{base_url}/api/v2/forms/{form_uid}/exports/"
    export_payload = {"format": "xls"}

    export_response = requests.post(export_url, auth=auth, json=export_payload)

    if export_response.status_code != 201:
        st.error(f"❌ Failed to create XLS export: {export_response.status_code} - {export_response.text}")
        return pd.DataFrame()

    export_json = export_response.json()
    export_id = export_json.get("id")
    download_url = export_json.get("url")

    # Step 2: Poll until export is ready (usually takes a few seconds)
    status = export_json.get("status", "pending")
    retries = 10
    while status != "complete" and retries > 0:
        time.sleep(3)
        poll = requests.get(f"{export_url}{export_id}/", auth=auth)
        poll_json = poll.json()
        status = poll_json.get("status")
        download_url = poll_json.get("url")
        retries -= 1

    if status != "complete":
        st.error("❌ XLS export did not complete in time.")
        return pd.DataFrame()

    # Step 3: Download XLS
    file_response = requests.get(download_url, auth=auth)
    if file_response.status_code != 200:
        st.error(f"❌ Failed to download XLS file: {file_response.status_code}")
        return pd.DataFrame()

    df = pd.read_excel(io.BytesIO(file_response.content))
    
    # Drop system fields
    system_fields = ["_id", "_uuid", "_submission_time", "_submitted_by", "_validation_status"]
    df = df.drop(columns=[col for col in system_fields if col in df.columns], errors="ignore")

    return df

# --- FETCH DATA ---
df = fetch_xls_export()
if df.empty:
    st.stop()

# --- PROCESS DATES ---
if "start" in df.columns:
    df = df.rename(columns={"start": "submission_date"})

if "submission_date" in df.columns:
    df["submission_date"] = pd.to_datetime(df["submission_date"])
    df["submission_day"] = df["submission_date"].dt.date

# --- SIDEBAR FILTERS ---
st.sidebar.title("🔍 Filters")
if "submission_date" in df.columns:
    min_date = df["submission_date"].min().date()
    max_date = df["submission_date"].max().date()
    date_range = st.sidebar.date_input("Date Range", (min_date, max_date))
    if len(date_range) == 2:
        df = df[
            (df["submission_date"].dt.date >= date_range[0]) &
            (df["submission_date"].dt.date <= date_range[1])
        ]

# Optional filters
for col in ["district", "ward", "village"]:
    if col in df.columns:
        options = ["All"] + sorted(df[col].dropna().unique().tolist())
        selected = st.sidebar.selectbox(f"{col.title()} Filter", options)
        if selected != "All":
            df = df[df[col] == selected]

# --- DASHBOARD METRICS ---
st.title("📊 KoboToolbox XLS Dashboard")
col1, col2 = st.columns(2)
col1.metric("📋 Total Submissions", len(df))
today = datetime.now().date()
if "submission_date" in df.columns:
    col2.metric("🕒 Today", len(df[df["submission_date"].dt.date == today]))

# --- DATAFRAME ---
st.subheader("📄 Data Table")
st.dataframe(df, use_container_width=True)

# --- DOWNLOADS ---
csv = df.to_csv(index=False).encode("utf-8")
excel = io.BytesIO()
df.to_excel(excel, index=False)

col1, col2 = st.columns(2)
col1.download_button("⬇️ Download CSV", csv, "kobo_data.csv", "text/csv")
col2.download_button("⬇️ Download Excel", excel.getvalue(), "kobo_data.xlsx", 
                     "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

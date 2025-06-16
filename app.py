import streamlit as st
import pandas as pd
import requests
import io

# === SETTINGS ===
KOBO_API_TOKEN = "04714621fa3d605ff0a4aa5cc2df7cfa961bf256"
FORM_UID = "aJHsRZXT3XEpCoxn9Ct3qZ"
EXPORT_SETTING_UID = "esnia8U2QVxNnjzMY4p87ss"
DATE_COLUMN = "today"

# === PAGE CONFIG ===
st.set_page_config(page_title="📊 KoBo Data Dashboard", layout="wide")
st.title("📥 KoBoToolbox Data Viewer")

# === FETCH AND CLEAN DATA ===
@st.cache_data(ttl=180)
def download_exported_data():
    try:
        url = f"https://kf.kobotoolbox.org/api/v2/assets/{FORM_UID}/export-settings/{EXPORT_SETTING_UID}/data.xlsx"
        headers = {"Authorization": f"Token {KOBO_API_TOKEN}"}
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        df = pd.read_excel(io.BytesIO(response.content), engine="openpyxl")
        df = df.loc[:, ~df.columns.str.contains(r"^Unnamed:")]
        if DATE_COLUMN in df.columns:
            df[DATE_COLUMN] = pd.to_datetime(df[DATE_COLUMN], errors="coerce")
        return df
    except Exception:
        return pd.DataFrame()

df = download_exported_data()

if df.empty:
    st.warning("⚠️ No data loaded. Please check API token, form UID or export settings.")
else:
    original_count = len(df)

    # === SIDEBAR FILTERS ===
    st.sidebar.header("🔍 Filters")

    # DATE FILTER
    if DATE_COLUMN in df.columns and pd.api.types.is_datetime64_any_dtype(df[DATE_COLUMN]):
        date_col = df[DATE_COLUMN].dropna()
        if not date_col.empty:
            min_date = date_col.min().date()
            max_date = date_col.max().date()

            start_date = st.sidebar.date_input("📅 Start date", min_value=min_date, max_value=max_date, value=min_date)
            end_date = st.sidebar.date_input("📅 End date", min_value=min_date, max_value=max_date, value=max_date)

            # Apply only if both are valid
            if start_date and end_date and start_date <= end_date:


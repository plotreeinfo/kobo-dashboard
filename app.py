import streamlit as st
import pandas as pd
import requests
from io import BytesIO

# ————————————————————————————————
# ⚙️ Your KoBo settings
KOBO_TOKEN = "04714621fa3d605ff0a4aa5cc2df7cfa961bf256"
FORM_UID = "aJHsRZXT3XEpCoxn9Ct3qZ"
BASE_URL = "https://kf.kobotoolbox.org"
HEADERS = {"Authorization": f"Token {KOBO_TOKEN}"}

# ————————————————————————————————
# 🔍 Fetch your saved synchronous export settings
def get_export_setting():
    url = f"{BASE_URL}/api/v2/assets/{FORM_UID}/export-settings/"
    resp = requests.get(url, headers=HEADERS)
    if resp.status_code != 200:
        st.error("Failed to fetch export settings: " + resp.text[:200])
        return None
    settings = resp.json().get("results", [])
    if not settings:
        st.error("No export settings found. Create one in KoBo UI > DATA > Downloads.")
        return None
    # Use the first saved export setting
    return settings[0]

# ————————————————————————————————
# 📥 Download the actual XLSX file from the data_url
def download_exported_data():
    setting = get_export_setting()
    if not setting:
        return pd.DataFrame()
    data_url = setting.get("data_url_xlsx") or setting.get("data_url_csv")
    if not data_url:
        st.error("No data_url found. Make sure export settings include XLSX.")
        return pd.DataFrame()

    resp = requests.get(data_url, headers=HEADERS)
    if resp.status_code != 200:
        st.error("Failed to download export file.")
        return pd.DataFrame()

    df = pd.read_excel(BytesIO(resp.content))
    unwanted = ["start", "end", "_id", "_uuid", "_validation_status",
                "_notes", "_status", "_submitted_by", "_tags", "__version__"]
    df.drop(columns=[c for c in unwanted if c in df.columns], inplace=True, errors='ignore')
    return df

# ————————————————————————————————
# 🌐 Streamlit App
st.set_page_config("KoBo Dashboard", layout="wide")
st.title("📋 KoBoToolbox Form Data Viewer")

if st.button("🔄 Load Latest Data"):
    with st.spinner("Fetching export-settings and downloading data..."):
        df = download_exported_data()
        st.session_state.df = df if not df.empty else None

if "df" in st.session_state and st.session_state.df is not None:
    df = st.session_state.df
    st.success(f"{len(df)} records loaded")

    col = st.selectbox("🔍 Filter column", df.columns)
    keyword = st.text_input("Enter substring to filter")

    if keyword:
        df = df[df[col].astype(str).str.contains(keyword, case=False, na=False)]

    st.dataframe(df, use_container_width=True)

    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Download CSV", csv, "filtered_data.csv", "text/csv")

    xls_buf = BytesIO()
    df.to_excel(xls_buf, index=False)
    st.download_button("⬇️ Download XLSX", xls_buf.getvalue(),
                       "filtered_data.xlsx",
                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

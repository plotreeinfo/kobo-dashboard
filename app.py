import streamlit as st
import pandas as pd
import requests
from io import BytesIO

# ——— KoBo API Settings ———
KOBO_TOKEN = "04714621fa3d605ff0a4aa5cc2df7cfa961bf256"
FORM_UID = "aJHsRZXT3XEpCoxn9Ct3qZ"
BASE_URL = "https://kf.kobotoolbox.org"
HEADERS = {"Authorization": f"Token {KOBO_TOKEN}"}

st.set_page_config("KoBo Dashboard", layout="wide")
st.title("📋 KoBoToolbox Form Data Viewer")


# ——— Debug Print Function ———
def log(msg):
    st.markdown(f"🪵 `{msg}`")


# ——— Safe JSON GET ———
def get_json_response(url):
    log(f"🔗 Fetching: {url}")
    try:
        resp = requests.get(url, headers=HEADERS)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.HTTPError as e:
        st.error(f"❌ HTTP Error: {e}")
    except requests.exceptions.RequestException as e:
        st.error(f"❌ Request failed: {e}")
    except ValueError:
        st.error("❌ KoBo returned non-JSON (likely HTML error).")
    return None


# ——— Get Export Setting ———
def get_export_setting():
    url = f"{BASE_URL}/api/v2/assets/{FORM_UID}/export-settings/"
    data = get_json_response(url)
    if not data:
        log("❌ No export-setting response")
        return None

    log(f"✅ Export settings found: {len(data.get('results', []))}")
    if data.get("results"):
        return data["results"][0]
    return None


# ——— Download Exported Data ———
def download_exported_data():
    setting = get_export_setting()
    if not setting:
        log("⚠️ No export settings found — maybe not created yet?")
        return pd.DataFrame()

    data_url = setting.get("data_url_xlsx") or setting.get("data_url_csv")
    log(f"📁 Data download URL: {data_url}")
    if not data_url:
        st.warning("⚠️ Export found but no data download URL available.")
        return pd.DataFrame()

    try:
        res = requests.get(data_url, headers=HEADERS)
        res.raise_for_status()

        if "xlsx" in data_url:
            df = pd.read_excel(BytesIO(res.content))
        else:
            df = pd.read_csv(BytesIO(res.content))

        log(f"📊 Rows Loaded: {len(df)}")

        # Remove unwanted metadata
        unwanted = [
            "start", "end", "_id", "_uuid", "_validation_status",
            "_notes", "_status", "_submitted_by", "_tags", "__version__"
        ]
        df.drop(columns=[col for col in unwanted if col in df.columns], inplace=True)
        return df

    except Exception as e:
        st.error(f"❌ Failed to load data: {e}")
        return pd.DataFrame()


# ——— Main App Flow ———
with st.spinner("⏳ Fetching data..."):
    df = download_exported_data()

if df is not None and not df.empty:
    st.success(f"✅ Loaded {len(df)} records")
    
    col = st.selectbox("🔍 Filter by column", df.columns)
    text = st.text_input("Enter text to filter")
    
    if text:
        df = df[df[col].astype(str).str.contains(text, case=False, na=False)]

    st.dataframe(df, use_container_width=True)
    st.download_button("⬇️ Download CSV", df.to_csv(index=False), "data.csv", "text/csv")
    st.download_button("⬇️ Download Excel", df.to_excel(index=False), "data.xlsx", "application/vnd.ms-excel")

else:
    st.warning("⚠️ No data found or export is missing.")

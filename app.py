import streamlit as st
import pandas as pd
import requests
from io import BytesIO

# --- Settings ---
KOBO_TOKEN = "04714621fa3d605ff0a4aa5cc2df7cfa961bf256"
FORM_UID = "aJHsRZXT3XEpCoxn9Ct3qZ"
BASE_URL = "https://kf.kobotoolbox.org"
HEADERS = {"Authorization": f"Token {KOBO_TOKEN}"}

st.set_page_config("KoBo Debug Dashboard", layout="wide")
st.title("🛠️ KoBo Debug Viewer")

def log(msg):
    st.markdown(f"**🪵 {msg}**")

# --- Step 1: Fetch export-settings ---
url_settings = f"{BASE_URL}/api/v2/assets/{FORM_UID}/export-settings/"
log(f"Fetch Export Settings URL: {url_settings}")
resp = requests.get(url_settings, headers=HEADERS)
log(f"HTTP Status Code: {resp.status_code}")
try:
    data = resp.json()
    log("Export Settings JSON:")
    st.json(data)
except Exception as e:
    log(f"❌ JSON parsing error: {e}")
    st.text(resp.text[:500])
    st.stop()

results = data.get("results", [])
if not results:
    log("❌ 'results' is empty – no export-settings found.")
    st.stop()

# --- Step 2: Use the first export setting ---
setting = results[0]
log(f"Using export setting UID: {setting.get('uid')}")
log("Full export setting object:")
st.json(setting)

# --- Step 3: Extract download URL and fetch data ---
data_url = setting.get("data_url_xlsx") or setting.get("data_url_csv")
if not data_url:
    log("❌ No 'data_url_xlsx' or 'data_url_csv' found.")
    st.stop()

log(f"Data Download URL: {data_url}")
resp2 = requests.get(data_url, headers=HEADERS)
log(f"Download HTTP Status Code: {resp2.status_code}")
if resp2.status_code != 200:
    st.text(resp2.text[:500])
    st.stop()

# --- Step 4: Try reading into DataFrame ---
try:
    if "xlsx" in data_url:
        df = pd.read_excel(BytesIO(resp2.content))
    else:
        df = pd.read_csv(BytesIO(resp2.content))
    log(f"📊 Loaded DataFrame with {len(df)} rows and {len(df.columns)} columns")
    st.dataframe(df)
except Exception as e:
    log(f"❌ Error parsing data file: {e}")
    st.stop()

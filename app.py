import streamlit as st
import pandas as pd
import requests
from io import BytesIO

# ———————————————————
# ⚙️ KoBo settings
KOBO_TOKEN = "04714621fa3d605ff0a4aa5cc2df7cfa961bf256"
FORM_UID = "aJHsRZXT3XEpCoxn9Ct3qZ"
BASE_URL = "https://kf.kobotoolbox.org"
HEADERS = {"Authorization": f"Token {KOBO_TOKEN}"}

# ———————————————————
# 🔍 Safe JSON response function
def get_json_response(url):
    try:
        resp = requests.get(url, headers=HEADERS)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.HTTPError as e:
        st.error(f"❌ HTTP Error: {e}")
    except requests.exceptions.RequestException as e:
        st.error(f"❌ Request failed: {e}")
    except ValueError:
        st.error(f"❌ KoBo returned non-JSON (likely HTML). URL: {url}")
    return None

# ———————————————————
# 📥 Get export setting
def get_export_setting():
    url = f"{BASE_URL}/api/v2/assets/{FORM_UID}/export-settings/"
    data = get_json_response(url)
    if not data or "resul

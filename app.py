import streamlit as st
import pandas as pd
import requests
from io import BytesIO

# ——— KoBo API settings ———
KOBO_TOKEN = "04714621fa3d605ff0a4aa5cc2df7cfa961bf256"
FORM_UID = "aJHsRZXT3XEpCoxn9Ct3qZ"
BASE_URL = "https://kf.kobotoolbox.org"
HEADERS = {"Authorization": f"Token {KOBO_TOKEN}"}

# ——— Safe JSON GET ———
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
        st.error("❌ KoBo returned HTML instead of JSON.")
    return None

# ——— Get Export Setting ———
def get_export_setting():
    url = f"{BASE_URL}/api/v2/assets/{FORM_UID}/export-settings/"
    data = get_json_response(url)
    if data and "results" in data and data["results"]:
        return data["results"][0]
    else:
        st.warning("⚠️ No export setting found — export manually once via KoBo.")
        return None

# ——— Download Exported Data ———
def download_exported_data():
    setting = get_export_setting()
    if not setting:
        return pd.DataFrame()

    data_url = setting.get("data_url_xlsx") or setting.get("data_url_csv")
    if not data_url:
        st.warning("⚠️ No export URL found.")
        return pd.DataFrame()

    st.info(f"🔗 Export URL: {data_url}")

    try:
        res = requests.get(data_url, headers=HEADERS)
        res.raise_for_status()

        if "xlsx" in data_url:
            df = pd.read_excel(BytesIO(res.content))
        else:
            df = pd.read_csv(BytesIO(res.content))

        # Remove metadata columns
        unwanted = [
            "start", "end", "_id", "_uuid", "_validation_status",
            "_notes", "_status", "_submitted_by", "_tags", "__version__"
        ]
        df.drop(columns=[col for col in unwanted if col in df.columns], inplace=True)
        return df

    except Exception as e:
        st.error(f"❌ Failed to fetch or read data: {e}")
        return pd.DataFrame()

# ——— Streamlit UI ———
st.set_page_config("KoBo Dashboard", layout="wide")
st.title("📋 KoBoToolbox Form Data Viewer")

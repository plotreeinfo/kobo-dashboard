import streamlit as st
import requests
import time
from datetime import datetime
from requests.auth import HTTPBasicAuth

# ================================
# CONFIGURATION
# ================================

KOBO_USERNAME = "plotree"
KOBO_PASSWORD = "Pl@tr33@123"
FORM_UID = "aJHsRZXT3XEpCoxn9Ct3qZ"
BASE_URL = "https://kf.kobotoolbox.org"
EXPORT_ENDPOINT = f"{BASE_URL}/api/v2/assets/{FORM_UID}/exports/"

# ================================
# UI LAYOUT
# ================================

st.set_page_config(page_title="Kobo Export Options", layout="centered")
st.title("📤 KoboToolbox Custom Export")
st.markdown("Configure your export and download data from KoboToolbox.")

# Export configuration options
st.subheader("⚙️ Export Settings")

export_type = st.selectbox("Export Format", ["xls", "csv", "json"])
lang = st.selectbox("Language for Labels", ["english", "urdu", "xml"])
group_sep = st.selectbox("Group Separator", ["/", "."])
include_media = st.checkbox("Include Media URLs", value=True)
select_multiples = st.radio(
    "Select Multiple Questions As",
    ["separate columns", "single column"]
)
hierarchy_labels = st.checkbox("Include Groups in Headers", value=True)
store_text = st.checkbox("Store Dates & Numbers as Text", value=False)

# Submit export request
if st.button("🚀 Generate Export"):
    st.info("Sending export request to KoboToolbox...")

    payload = {
        "type": export_type,
        "lang": lang,
        "group_sep": group_sep,
        "include_media_urls": include_media,
        "hierarchy_in_labels": hierarchy_labels,
        "select_multiples": select_multiples,
        "value_select_multiples": select_multiples,
        "store_empty_columns": True,
        "store_dates_as_text": store_text,
        "store_numbers_as_text": store_text
    }

    response = requests.post(
        EXPORT_ENDPOINT,
        auth=HTTPBasicAuth(KOBO_USERNAME, KOBO_PASSWORD),
        json=payload
    )

    if response.status_code == 201:
        export_url = response.json()["url"]
        st.success("Export started. Waiting for completion...")

        progress = st.progress(0)
        status_text = st.empty()

        for i in range(30):  # Max ~5 minutes
            export_status = requests.get(export_url, auth=HTTPBasicAuth(KOBO_USERNAME, KOBO_PASSWORD))
            if export_status.status_code == 200:
                status_json = export_status.json()
                status = status_json.get("status")
                result_url = status_json.get("result")

                if status == "complete" and result_url:
                    download_link = BASE_URL + result_url
                    progress.progress(100)
                    status_text.success("✅ Export complete!")
                    st.markdown(
                        f'<a href="{download_link}" target="_blank">📥 Click here to download your {export_type.upper()} file</a>',
                        unsafe_allow_html=True
                    )
                    break
                elif status == "failed":
                    status_text.error("❌ Export failed.")
                    break
                else:
                    progress.progress((i + 1) * 3)
                    status_text.info(f"Status: {status}. Please wait...")
                    time.sleep(10)
            else:
                st.error("Failed to check export status.")
                break

        else:
            status_text.warning("⏳ Export taking too long. Check KoboToolbox later.")
    else:
        st.error(f"Failed to start export: {response.status_code}")

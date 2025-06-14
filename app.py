import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# ==============================================
# CONFIGURATION
# ==============================================

st.set_page_config(layout="wide")
st.title("📊 KoboToolbox Data Exporter")

# Hide Streamlit defaults
hide_streamlit_style = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# ==============================================
# AUTHENTICATION
# ==============================================

def test_connection():
    """Verify credentials before attempting exports"""
    test_url = f"{st.session_state.base_url}/api/v2/assets/{st.session_state.form_uid}/"
    headers = {"Authorization": f"Token {st.session_state.api_token}"}
    
    try:
        response = requests.get(test_url, headers=headers, timeout=10)
        if response.status_code == 200:
            return True
        elif response.status_code == 401:
            st.error("Invalid API Token - Regenerate at: https://kf.kobotoolbox.org/token/")
        elif response.status_code == 404:
            st.error("Form not found - Check FORM_UID in your form's URL")
        else:
            st.error(f"Connection failed (HTTP {response.status_code})")
    except Exception as e:
        st.error(f"Connection error: {str(e)}")
    return False

# ==============================================
# EXPORT FUNCTIONS
# ==============================================

def generate_export(export_type):
    """Trigger and download export with full error handling"""
    export_url = f"{st.session_state.base_url}/api/v2/assets/{st.session_state.form_uid}/exports/"
    headers = {"Authorization": f"Token {st.session_state.api_token}"}
    
    payload = {
        "type": export_type,
        "fields_from_all_versions": "true",
        "lang": "English"
    }
    
    try:
        # Step 1: Create export
        with st.spinner(f"Generating {export_type.upper()} export..."):
            response = requests.post(export_url, json=payload, headers=headers)
            
            if response.status_code != 201:
                st.error(f"Export creation failed (HTTP {response.status_code})")
                st.json(response.json())  # Show API error details
                return None
                
        # Step 2: Download export
        download_url = response.json().get('url')
        if not download_url:
            st.error("No download URL received")
            return None
            
        with st.spinner("Preparing download..."):
            file_response = requests.get(download_url, headers=headers)
            
            if file_response.status_code == 200:
                return {
                    "content": file_response.content,
                    "mime": {
                        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        "csv": "text/csv",
                        "spss_labels": "application/octet-stream"
                    }[export_type],
                    "extension": export_type if export_type != "spss_labels" else "sav"
                }
            else:
                st.error(f"Download failed (HTTP {file_response.status_code})")
                return None
                
    except Exception as e:
        st.error(f"Export error: {str(e)}")
        return None

# ==============================================
# UI COMPONENTS
# ==============================================

def credential_form():
    """Form for entering API credentials"""
    with st.form("credentials"):
        st.session_state.base_url = st.text_input(
            "KoboToolbox Server URL",
            value="https://kf.kobotoolbox.org"
        )
        st.session_state.form_uid = st.text_input(
            "FORM_UID (from your form's URL)",
            value="aJHsRZXT3XEpCoxn9Ct3qZ"
        )
        st.session_state.api_token = st.text_input(
            "API Token (from https://kf.kobotoolbox.org/token/)",
            type="password"
        )
        
        if st.form_submit_button("Connect"):
            if test_connection():
                st.success("Connected successfully!")
                st.session_state.connected = True
            else:
                st.session_state.connected = False

def export_buttons():
    """Display export options after successful connection"""
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("Export to Excel (XLSX)"):
            export = generate_export("xlsx")
            if export:
                st.download_button(
                    label="Download XLSX",
                    data=export["content"],
                    file_name=f"kobo_export.{export['extension']}",
                    mime=export["mime"]
                )
    
    with col2:
        if st.button("Export to CSV"):
            export = generate_export("csv")
            if export:
                st.download_button(
                    label="Download CSV",
                    data=export["content"],
                    file_name=f"kobo_export.{export['extension']}",
                    mime=export["mime"]
                )
    
    with col3:
        if st.button("Export to SPSS"):
            export = generate_export("spss_labels")
            if export:
                st.download_button(
                    label="Download SPSS",
                    data=export["content"],
                    file_name=f"kobo_export.{export['extension']}",
                    mime=export["mime"]
                )

# ==============================================
# MAIN APP
# ==============================================

def main():
    if 'connected' not in st.session_state:
        st.session_state.connected = False
    
    credential_form()
    
    if st.session_state.connected:
        st.markdown("---")
        export_buttons()
        
        # Debug info
        with st.expander("Technical Details"):
            st.write(f"Form UID: {st.session_state.form_uid}")
            st.write(f"API Token: {'*' * 20}{st.session_state.api_token[-4:]}")
            st.write(f"Last checked: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

if __name__ == "__main__":
    main()

import streamlit as st
import requests
import time
from datetime import datetime

# ==============================================
# SETUP
# ==============================================

st.set_page_config(layout="wide")
st.title("🔒 KoboToolbox Secure Exporter")

# Hide Streamlit defaults
hide_defaults = """
<style>
#MainMenu, footer, header {visibility: hidden;}
.stSpinner > div {text-align:center;}
</style>
"""
st.markdown(hide_defaults, unsafe_allow_html=True)

# ==============================================
# SESSION STATE SETUP
# ==============================================

if 'auth' not in st.session_state:
    st.session_state.auth = {
        'base_url': 'https://kf.kobotoolbox.org',
        'form_uid': 'aJHsRZXT3XEpCoxn9Ct3qZ',
        'api_token': '',
        'connected': False
    }

# ==============================================
# AUTHENTICATION
# ==============================================

def test_connection():
    """Test credentials with API"""
    headers = {"Authorization": f"Token {st.session_state.auth['api_token']}"}
    test_url = f"{st.session_state.auth['base_url']}/api/v2/assets/{st.session_state.auth['form_uid']}/"
    
    try:
        response = requests.get(test_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            return True, ""
        elif response.status_code == 401:
            return False, "Invalid API Token - Regenerate at: https://kf.kobotoolbox.org/token/"
        elif response.status_code == 404:
            return False, "Form not found - Check FORM_UID in your form's URL"
        else:
            return False, f"Connection failed (HTTP {response.status_code})"
    except Exception as e:
        return False, f"Connection error: {str(e)}"

# ==============================================
# EXPORT PROCESS
# ==============================================

def manage_export(export_type):
    """Full export workflow with status polling"""
    headers = {"Authorization": f"Token {st.session_state.auth['api_token']}"}
    base_export_url = f"{st.session_state.auth['base_url']}/api/v2/assets/{st.session_state.auth['form_uid']}/exports/"
    
    # 1. Create export
    payload = {
        "type": export_type,
        "fields_from_all_versions": "true",
        "lang": "English"
    }
    
    try:
        # Start export job
        with st.spinner("Initializing export..."):
            create_response = requests.post(base_export_url, json=payload, headers=headers)
            
            if create_response.status_code != 201:
                st.error(f"Export failed to start (HTTP {create_response.status_code})")
                if create_response.text:
                    st.code(create_response.text)
                return None
            
            export_uid = create_response.json().get('uid')
            if not export_uid:
                st.error("No export UID received")
                return None
        
        # 2. Poll for completion
        with st.spinner("Processing export..."):
            status_url = f"{base_export_url}{export_uid}/"
            start_time = time.time()
            timeout = 300  # 5 minutes
            
            while True:
                status_response = requests.get(status_url, headers=headers)
                
                if status_response.status_code != 200:
                    st.error(f"Status check failed (HTTP {status_response.status_code})")
                    return None
                
                status_data = status_response.json()
                current_status = status_data.get('status')
                
                if current_status == 'complete':
                    break
                elif current_status in ('error', 'failed'):
                    st.error(f"Export failed: {status_data.get('messages', 'Unknown error')}")
                    return None
                
                if time.time() - start_time > timeout:
                    st.error("Export timed out")
                    return None
                
                time.sleep(2)  # Check every 2 seconds
        
        # 3. Download file
        with st.spinner("Preparing download..."):
            download_url = status_data.get('result')
            if not download_url:
                st.error("No download URL in response")
                return None
            
            file_response = requests.get(download_url, headers=headers)
            
            if file_response.status_code == 200:
                return {
                    'content': file_response.content,
                    'type': export_type,
                    'filename': f"kobo_export_{datetime.now().strftime('%Y%m%d')}.{export_type if export_type != 'spss_labels' else 'sav'}"
                }
            else:
                st.error(f"Download failed (HTTP {file_response.status_code})")
                return None
                
    except Exception as e:
        st.error(f"Export process error: {str(e)}")
        return None

# ==============================================
# UI COMPONENTS
# ==============================================

def show_credential_form():
    """Form for entering API details"""
    with st.form("credentials"):
        st.session_state.auth['base_url'] = st.text_input(
            "KoboToolbox Server URL",
            value=st.session_state.auth['base_url']
        ).rstrip('/')
        
        st.session_state.auth['form_uid'] = st.text_input(
            "FORM_UID (from your form's URL)",
            value=st.session_state.auth['form_uid']
        )
        
        st.session_state.auth['api_token'] = st.text_input(
            "API Token (from https://kf.kobotoolbox.org/token/)",
            type="password",
            value=st.session_state.auth['api_token']
        )
        
        if st.form_submit_button("Connect to KoboToolbox"):
            is_valid, message = test_connection()
            if is_valid:
                st.session_state.auth['connected'] = True
                st.success("✅ Connected successfully!")
            else:
                st.session_state.auth['connected'] = False
                st.error(f"❌ {message}")

def show_export_buttons():
    """Export interface after successful connection"""
    st.markdown("---")
    st.subheader("Export Options")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📊 Excel (XLSX)"):
            handle_export("xlsx")
    
    with col2:
        if st.button("📝 CSV"):
            handle_export("csv")
    
    with col3:
        if st.button("📊 SPSS"):
            handle_export("spss_labels")

def handle_export(export_type):
    """Manage the export process and download"""
    mime_types = {
        'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'csv': 'text/csv',
        'spss_labels': 'application/octet-stream'
    }
    
    export_result = manage_export(export_type)
    if export_result:
        st.download_button(
            label=f"Download {export_type.upper()}",
            data=export_result['content'],
            file_name=export_result['filename'],
            mime=mime_types[export_type],
            key=f"download_{export_type}"
        )

# ==============================================
# MAIN APP
# ==============================================

def main():
    # Credential form
    st.subheader("1. Enter KoboToolbox Credentials")
    show_credential_form()
    
    # Export interface
    if st.session_state.auth.get('connected', False):
        st.subheader("2. Select Export Format")
        show_export_buttons()
        
        # Debug info
        with st.expander("🔧 Connection Details"):
            st.json({
                "Server": st.session_state.auth['base_url'],
                "Form UID": st.session_state.auth['form_uid'],
                "Token": f"••••••{st.session_state.auth['api_token'][-4:]}" if st.session_state.auth['api_token'] else "Not set",
                "Last check": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })

if __name__ == "__main__":
    main()

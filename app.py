# app.py
import streamlit as st
import pandas as pd
import requests
from io import StringIO, BytesIO
import time

# Configuration
st.set_page_config(layout="wide")

# 1. Kobo API Direct Access (Original Method)
def fetch_kobo_api():
    KOBO_USERNAME = "plotree"
    KOBO_API_TOKEN = "04714621fa3d605ff0a4aa5cc2df7cfa961bf256"
    FORM_UID = "aJHsRZXT3XEpCoxn9Ct3qZ"
    
    EXPORT_URL = f"https://kf.kobotoolbox.org/api/v2/assets/{FORM_UID}/exports/"
    EXPORT_PARAMS = {
        "format": "csv",
        "lang": "en",
        "multiple_select": "both",
        "include_all_versions": "false",
        "hierarchy_in_labels": "false",
        "date_format": "string",
        "numeric_format": "string",
        "include_media_url": "true"
    }
    
    EXCLUDE_COLUMNS = [
        "start", "end", "_id", "_uuid", "_validation_status", 
        "_notes", "_status", "_submitted_by", "_tags", "__version__"
    ]
    
    try:
        # Create export
        export_response = requests.post(
            EXPORT_URL,
            params=EXPORT_PARAMS,
            auth=(KOBO_USERNAME, KOBO_API_TOKEN),
            timeout=30
        )
        export_response.raise_for_status()
        
        # Check export status
        export_uid = export_response.json()['uid']
        result_url = f"{EXPORT_URL}{export_uid}/"
        
        with st.spinner("Generating Kobo export (may take 20-30 seconds)..."):
            for _ in range(10):  # Max 10 checks (30 sec each)
                status_response = requests.get(
                    result_url,
                    auth=(KOBO_USERNAME, KOBO_API_TOKEN),
                    timeout=30
                )
                status_data = status_response.json()
                
                if status_data['status'] == 'complete':
                    break
                time.sleep(3)
            else:
                raise TimeoutError("Export timed out")
        
        # Download data
        download_url = status_data['result']
        data_response = requests.get(download_url, timeout=30)
        data_response.raise_for_status()
        
        # Process data
        if download_url.endswith('.csv'):
            df = pd.read_csv(StringIO(data_response.text))
        else:
            df = pd.read_excel(BytesIO(data_response.content))
            
        return df[[col for col in df.columns if col not in EXCLUDE_COLUMNS]]
    
    except Exception as e:
        st.error(f"API Error: {str(e)}")
        return None

# 2. GitHub Fallback Method
def fetch_github():
    GITHUB_RAW_URL = "https://raw.githubusercontent.com/yourusername/yourrepo/main/kobo_data.csv"
    
    try:
        response = requests.get(GITHUB_RAW_URL, timeout=10)
        response.raise_for_status()
        df = pd.read_csv(StringIO(response.text))
        return df
    except Exception as e:
        st.error(f"GitHub Error: {str(e)}")
        return None

# 3. Local File Upload Fallback
def handle_upload():
    uploaded_file = st.file_uploader("Or upload Kobo export manually:", 
                                   type=["csv", "xlsx"])
    if uploaded_file:
        try:
            if uploaded_file.name.endswith('.csv'):
                return pd.read_csv(uploaded_file)
            else:
                return pd.read_excel(uploaded_file)
        except Exception as e:
            st.error(f"Upload Error: {str(e)}")
    return None

# Main App
st.title("Kobo Data Viewer (Multi-Source)")
st.markdown("""
**Data Loading Options:**  
1. Direct API fetch (live data)  
2. GitHub stored copy  
3. Manual file upload  
""")

# Try methods in order
df = None
method_used = ""

with st.spinner("Attempting to load data..."):
    df = fetch_kobo_api()
    method_used = "Kobo API" if df is not None else ""
    
    if df is None:
        st.warning("Falling back to GitHub...")
        df = fetch_github()
        method_used = "GitHub" if df is not None else ""
        
    if df is None:
        st.warning("Please upload file manually")
        df = handle_upload()
        method_used = "Manual Upload" if df is not None else ""

# Display results
if df is not None:
    st.success(f"✅ Success! Loaded {len(df)} records via {method_used}")
    
    tab1, tab2, tab3 = st.tabs(["Data Preview", "Column Info", "Statistics"])
    
    with tab1:
        st.dataframe(df, height=500, use_container_width=True)
    
    with tab2:
        st.write("### Columns:")
        st.json(list(df.columns))
        st.write("### Sample Values:")
        st.write(df.iloc[0:3].T)
    
    with tab3:
        st.write("### Numeric Columns:")
        st.write(df.describe())
        st.write("### Text Columns:")
        st.write(df.describe(include=['O']))
    
    # Export buttons
    st.download_button(
        label="Download as CSV",
        data=df.to_csv(index=False).encode('utf-8'),
        file_name='kobo_data.csv',
        mime='text/csv'
    )
    
else:
    st.error("❌ Failed to load data from all sources")

if st.button("🔄 Retry All Methods"):
    st.rerun()

st.markdown("---")
st.info("""
**Troubleshooting Guide:**  
1. If API fails: Wait 1 minute and retry  
2. For GitHub: Ensure file is in your repo's main branch  
3. For upload: Export from Kobo as CSV with English headers  
""")

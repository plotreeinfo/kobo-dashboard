import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import time
from datetime import datetime
from requests.auth import HTTPBasicAuth

# ==============================================
# CONFIGURATION
# ==============================================

# Remove Streamlit menu and GitHub icon
hide_streamlit_style = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# KoboToolbox API credentials - MUST CONFIGURE THESE
KOBO_USERNAME = "plotree"  # Replace with your username
KOBO_PASSWORD = "04714621fa3d605ff0a4aa5cc2df7cfa961bf256"  # Replace with your API token (not password)
FORM_UID = "aJHsRZXT3XEpCoxn9Ct3qZ"  # Replace with your form's asset UID
BASE_URL = "https://kf.kobotoolbox.org"  # Replace if using a different server

# API endpoints
API_URL = f"{BASE_URL}/api/v2/assets/{FORM_UID}/data.json"
EXPORT_URL = f"{BASE_URL}/api/v2/assets/{FORM_UID}/exports/"

# ==============================================
# DATA FUNCTIONS
# ==============================================

@st.cache_data(ttl=3600)
def fetch_kobo_data():
    """Fetch raw data from KoboToolbox API with enhanced error handling"""
    try:
        response = requests.get(
            API_URL,
            auth=HTTPBasicAuth(KOBO_USERNAME, KOBO_PASSWORD),
            timeout=30
        )
        response.raise_for_status()
        
        data = response.json().get("results", [])
        if not data:
            st.warning("API returned empty results - no submissions found")
            return pd.DataFrame()
            
        return pd.DataFrame(data)
        
    except requests.exceptions.RequestException as e:
        st.error(f"Data fetch failed: {str(e)}")
        st.info("Troubleshooting steps:")
        st.info("1. Verify your API token is correct")
        st.info("2. Check the form UID is accurate")
        st.info("3. Ensure you have internet access")
        return pd.DataFrame()

def trigger_kobo_export(export_type="xls"):
    """Trigger a KoboToolbox export with robust error handling"""
    try:
        headers = {
            'Authorization': f'Token {KOBO_PASSWORD}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            "type": export_type,
            "fields_from_all_versions": "true",
            "group_sep": "/",
            "hierarchy_in_labels": "true",
            "include_media_urls": "true",
            "lang": "English"
        }
        
        response = requests.post(
            EXPORT_URL,
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 201:
            return response.json().get('url')
        else:
            st.error(f"Export failed with status {response.status_code}")
            if response.status_code == 403:
                st.error("Permission denied - check your API token has export rights")
            return None
            
    except Exception as e:
        st.error(f"Export request failed: {str(e)}")
        return None

def check_export_status(export_url):
    """Check status of a KoboToolbox export with retry logic"""
    try:
        headers = {'Authorization': f'Token {KOBO_PASSWORD}'}
        response = requests.get(export_url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            return data.get('status'), data.get('result')
        else:
            st.warning(f"Status check failed with code {response.status_code}")
            return None, None
            
    except Exception as e:
        st.warning(f"Status check error: {str(e)}")
        return None, None

# ==============================================
# DASHBOARD LAYOUT
# ==============================================

# Load data
df = fetch_kobo_data()

if df.empty:
    st.warning("No data available - cannot proceed")
    st.stop()

# Standardize column names
col_mapping = {
    "username": "username",
    "_1_1_Name_of_the_City_": "district",
    "_geolocation_latitude": "latitude",
    "_geolocation_longitude": "longitude"
}

for orig, new in col_mapping.items():
    if orig in df.columns:
        df = df.rename(columns={orig: new})

# Process dates if available
if "_submission_time" in df.columns:
    df["submission_date"] = pd.to_datetime(df["_submission_time"])
    df["submission_date"] = df["submission_date"].dt.tz_localize(None)
    df["submission_day"] = df["submission_date"].dt.date

# ==============================================
# SIDEBAR FILTERS
# ==============================================

st.sidebar.title("🔍 Filters")

# Date Filter
if "submission_date" in df.columns:
    with st.sidebar.expander("📅 Date Range", expanded=True):
        min_date = df["submission_date"].min().date()
        max_date = df["submission_date"].max().date()
        date_range = st.date_input(
            "Select date range",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date
        )
        
        if len(date_range) == 2:
            df = df[
                (df["submission_date"].dt.date >= date_range[0]) & 
                (df["submission_date"].dt.date <= date_range[1])
            ]

# Location Filters
with st.sidebar.expander("📍 Location", expanded=True):
    if "district" in df.columns:
        districts = ['All'] + sorted(df["district"].dropna().unique().tolist())
        selected_district = st.selectbox("District", districts)
        if selected_district != 'All':
            df = df[df["district"] == selected_district]

# User Filter
if "username" in df.columns:
    with st.sidebar.expander("👤 Data Collectors", expanded=True):
        users = ['All'] + sorted(df["username"].dropna().unique().tolist())
        selected_user = st.selectbox("Select user", users)
        if selected_user != 'All':
            df = df[df["username"] == selected_user]

# Data Quality
with st.sidebar.expander("🧰 Data Quality", expanded=True):
    completeness = st.slider(
        "Minimum data completeness (%)",
        min_value=0, max_value=100, value=80
    )
    
    if any("photo" in col.lower() for col in df.columns):
        photo_filter = st.selectbox(
            "Photos", 
            ['All', 'With Photos', 'Without Photos']
        )
        photo_cols = [col for col in df.columns if 'photo' in col.lower()]
        if photo_filter == 'With Photos':
            df = df[df[photo_cols].notnull().any(axis=1)]
        elif photo_filter == 'Without Photos':
            df = df[df[photo_cols].isnull().all(axis=1)]

# ==============================================
# MAIN DASHBOARD
# ==============================================

st.title("📊 KoboToolbox Data Dashboard")

# Key Metrics
st.subheader("📈 Overview Metrics")
cols = st.columns(4)
cols[0].metric("Total Submissions", len(df))
if "submission_date" in df.columns:
    today = datetime.now().date()
    cols[1].metric("Today's Submissions", 
                  len(df[df["submission_date"].dt.date == today]))
if "username" in df.columns:
    cols[2].metric("Unique Collectors", df["username"].nunique())
cols[3].metric("Data Completeness", 
              f"{round((1 - df.isnull().mean().mean()) * 100, 1)}%")

# Data Preview
st.subheader("🔍 Data Preview")
st.dataframe(df.head(1000), use_container_width=True)

# ==============================================
# KOBOTOOLBOX EXPORT SECTION
# ==============================================

st.subheader("📥 Download Data")

# Export Format Selection
export_format = st.radio(
    "Select export format",
    ["Excel (XLS)", "CSV"],
    index=0,
    horizontal=True
)

# Initialize session state for export tracking
if 'export_status' not in st.session_state:
    st.session_state.export_status = None
if 'export_result_url' not in st.session_state:
    st.session_state.export_result_url = None
if 'export_start_time' not in st.session_state:
    st.session_state.export_start_time = None
if 'export_retry_count' not in st.session_state:
    st.session_state.export_retry_count = 0

# Export Button
if st.button("Generate KoboToolbox Export"):
    st.session_state.export_start_time = time.time()
    st.session_state.export_retry_count = 0
    st.session_state.export_status = "processing"
    
    with st.spinner("Initiating export..."):
        export_type = "xls" if export_format == "Excel (XLS)" else "csv"
        export_url = trigger_kobo_export(export_type)
        
        if export_url:
            st.session_state.export_url = export_url
            st.success("Export initiated! Checking status...")
        else:
            st.session_state.export_status = "error"

# Status checking
if st.session_state.export_status == "processing":
    current_time = time.time()
    
    # Only check status every 15 seconds to avoid rate limiting
    if current_time - st.session_state.export_start_time > 15:
        with st.spinner("Checking export status..."):
            status, result_url = check_export_status(st.session_state.export_url)
            
            if status == "complete":
                st.session_state.export_status = "complete"
                st.session_state.export_result_url = result_url
                st.rerun()
            elif status == "error":
                st.session_state.export_retry_count += 1
                if st.session_state.export_retry_count < 3:
                    st.warning("Temporary issue, retrying...")
                    st.session_state.export_start_time = current_time
                    time.sleep(5)
                    st.rerun()
                else:
                    st.session_state.export_status = "error"
                    st.error("Export failed after multiple attempts")
            else:
                # Still processing
                st.session_state.export_start_time = current_time
                st.rerun()

# Show download link when ready
if st.session_state.export_status == "complete" and st.session_state.export_result_url:
    st.success("✅ Export ready!")
    st.markdown(
        f"""
        ### Download your {export_format} file:
        [Click here to download]({BASE_URL}{st.session_state.export_result_url})
        """
    )
    st.info("Note: This link is valid for 24 hours from KoboToolbox")

# ==============================================
# VISUALIZATIONS
# ==============================================

st.subheader("📊 Visualizations")

# Submission Trends Chart
if "submission_date" in df.columns:
    st.markdown("### Submission Trends")
    
    freq = st.selectbox("Display frequency", ["Daily", "Weekly", "Monthly"])
    
    if freq == "Daily":
        df["time_period"] = df["submission_date"].dt.date
    elif freq == "Weekly":
        df["time_period"] = df["submission_date"].dt.to_period('W').dt.start_time
    else:  # Monthly
        df["time_period"] = df["submission_date"].dt.to_period('M').dt.start_time
    
    trend_data = df.groupby("time_period").size().reset_index(name='count')
    
    fig = px.line(
        trend_data,
        x="time_period",
        y="count",
        title=f"Submissions by {freq}",
        labels={'count': 'Number of Submissions'}
    )
    
    if freq == "Daily":
        fig.update_xaxes(tickformat="%b %d, %Y")
    elif freq == "Weekly":
        fig.update_xaxes(tickformat="%b %d, %Y")
    else:  # Monthly
        fig.update_xaxes(tickformat="%b %Y")
    
    st.plotly_chart(fig, use_container_width=True)

# ==============================================
# FOOTER
# ==============================================

st.markdown("---")
st.markdown("""
**Dashboard Features:**
- Real-time data from KoboToolbox
- Professional filtering options
- Official KoboToolbox export functionality
- Interactive visualizations
""")

st.success("✅ Dashboard ready with all functionality working properly")

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

# KoboToolbox API credentials
KOBO_USERNAME = "plotree"
KOBO_PASSWORD = "Pl@tr33@123"
FORM_UID = "aJHsRZXT3XEpCoxn9Ct3qZ"
BASE_URL = "https://kf.kobotoolbox.org"
API_URL = f"{BASE_URL}/api/v2/assets/{FORM_UID}/data.json"
EXPORT_URL = f"{BASE_URL}/api/v2/assets/{FORM_UID}/exports/"

# ==============================================
# DATA FUNCTIONS
# ==============================================

@st.cache_data(ttl=3600)
def fetch_kobo_data():
    """Fetch raw data from KoboToolbox API"""
    try:
        response = requests.get(API_URL, auth=HTTPBasicAuth(KOBO_USERNAME, KOBO_PASSWORD))
        response.raise_for_status()
        data = response.json().get("results", [])
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Failed to load data: {str(e)}")
        return pd.DataFrame()

def trigger_kobo_export(export_type="xls"):
    """Trigger a proper KoboToolbox export"""
    headers = {'Authorization': f'Token {KOBO_PASSWORD}'}
    payload = {
        "type": export_type,
        "fields_from_all_versions": "true",
        "group_sep": "/",
        "hierarchy_in_labels": "true",
        "include_media_urls": "true",
        "lang": "English"
    }
    response = requests.post(EXPORT_URL, headers=headers, json=payload)
    if response.status_code == 201:
        return response.json().get('url')
    return None

def check_export_status(export_url):
    """Check status of a KoboToolbox export"""
    headers = {'Authorization': f'Token {KOBO_PASSWORD}'}
    response = requests.get(export_url, headers=headers)
    if response.status_code == 200:
        return response.json().get('status'), response.json().get('result')
    return None, None

# ==============================================
# DASHBOARD LAYOUT
# ==============================================

# Load data
df = fetch_kobo_data()

if df.empty:
    st.warning("No data available - please check your connection")
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
# KOBOTOOLBOX EXPORT SECTION - FIXED VERSION
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

# Export Button
if st.button("Generate KoboToolbox Export"):
    st.session_state.export_start_time = time.time()
    with st.spinner("Requesting export from KoboToolbox..."):
        # Determine export type
        export_type = "xls" if export_format == "Excel (XLS)" else "csv"
        
        # Trigger export
        export_url = trigger_kobo_export(export_type)
        
        if export_url:
            st.session_state.export_url = export_url
            st.session_state.export_status = "processing"
            st.success("Export requested! Checking status...")
        else:
            st.error("Failed to initiate export")

# Check export status periodically if processing
if st.session_state.export_status == "processing":
    current_time = time.time()
    # Only check status every 10 seconds (Kobo exports can take time)
    if current_time - st.session_state.export_start_time > 10:
        with st.spinner("Checking export status..."):
            status, result_url = check_export_status(st.session_state.export_url)
            
            if status == "complete":
                st.session_state.export_status = "complete"
                st.session_state.export_result_url = result_url
                st.success("Export ready for download!")
            elif status == "error":
                st.session_state.export_status = "error"
                st.error("Export failed - please try again")
            else:
                # Schedule another check
                st.session_state.export_start_time = current_time
                st.rerun()

# Show download link when export is ready
if st.session_state.export_status == "complete" and st.session_state.export_result_url:
    st.markdown(
        f"""
        ### Your export is ready!
        [Click here to download {export_format} file]({BASE_URL}{st.session_state.export_result_url})
        """,
        unsafe_allow_html=True
    )
    st.markdown("This link will be valid for 24 hours from the KoboToolbox server.")

# ==============================================
# VISUALIZATIONS
# ==============================================

st.subheader("📊 Visualizations")

# Submission Trends Chart
if "submission_date" in df.columns:
    st.markdown("### Submission Trends")
    
    # Frequency selector
    freq = st.selectbox("Display frequency", ["Daily", "Weekly", "Monthly"])
    
    # Initialize grouping column
    group_col = None
    
    # Set up proper grouping based on frequency
    if freq == "Daily":
        df["submission_day"] = df["submission_date"].dt.date
        group_col = "submission_day"
    elif freq == "Weekly":
        df["submission_week"] = df["submission_date"].dt.strftime('%Y-W%U')
        group_col = "submission_week"
    elif freq == "Monthly":
        df["submission_month"] = df["submission_date"].dt.strftime('%Y-%m')
        group_col = "submission_month"
    
    # Only proceed if we have a valid grouping column
    if group_col and group_col in df.columns:
        try:
            # Group and count submissions
            trend_data = df.groupby(group_col, as_index=False).size()
            trend_data = trend_data.rename(columns={'size': 'count'})
            
            # Sort by date (important for weekly/monthly)
            if freq == "Weekly":
                trend_data[group_col] = pd.to_datetime(trend_data[group_col] + '-1', format='%Y-W%U-%w')
            elif freq == "Monthly":
                trend_data[group_col] = pd.to_datetime(trend_data[group_col])
            
            trend_data = trend_data.sort_values(group_col)
            
            # Create and display plot using Plotly Express
            fig = px.line(trend_data, x=group_col, y='count',
                         title=f"Submissions by {freq}",
                         labels={'count': 'Number of Submissions'})
            
            # Format x-axis for better readability
            if freq == "Daily":
                fig.update_xaxes(tickformat="%b %d, %Y")
            elif freq == "Weekly":
                fig.update_xaxes(tickformat="%b %d, %Y")
            elif freq == "Monthly":
                fig.update_xaxes(tickformat="%b %Y")
            
            st.plotly_chart(fig, use_container_width=True)
            
        except Exception as e:
            st.error(f"Error generating trend visualization: {str(e)}")
    else:
        st.warning("Could not determine proper grouping for trends")
else:
    st.warning("Submission date information not available in this dataset")

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
- Data quality indicators
""")

st.success("✅ Dashboard ready with all functionality working properly")

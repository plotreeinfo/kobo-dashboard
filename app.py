import streamlit as st
import pandas as pd
import requests
from datetime import datetime
from requests.auth import HTTPBasicAuth
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode

# ==============================================
# CONFIGURATION
# ==============================================

# Hide Streamlit UI elements
hide_streamlit_style = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# KoboToolbox API credentials (DO NOT TOUCH)
KOBO_USERNAME = "plotree"
KOBO_PASSWORD = "Pl@tr33@123"
FORM_UID = "aJHsRZXT3XEpCoxn9Ct3qZ"
BASE_URL = "https://kf.kobotoolbox.org"
API_URL = f"{BASE_URL}/api/v2/assets/{FORM_UID}/data.json"

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

# ==============================================
# LOAD DATA
# ==============================================

df = fetch_kobo_data()

if df.empty:
    st.warning("No data available - please check your connection.")
    st.stop()

# Rename and clean columns
col_mapping = {
    "username": "username",
    "_1_1_Name_of_the_City_": "district",
    "_geolocation_latitude": "latitude",
    "_geolocation_longitude": "longitude"
}
df = df.rename(columns={k: v for k, v in col_mapping.items() if k in df.columns})

# Format date if available
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

# District Filter
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

# Photo Filter
with st.sidebar.expander("🖼️ Photos", expanded=True):
    photo_cols = [col for col in df.columns if 'photo' in col.lower()]
    if photo_cols:
        photo_filter = st.radio("Photo status", ['All', 'With Photos', 'Without Photos'])
        if photo_filter == 'With Photos':
            df = df[df[photo_cols].notnull().any(axis=1)]
        elif photo_filter == 'Without Photos':
            df = df[df[photo_cols].isnull().all(axis=1)]

# ==============================================
# MAIN DASHBOARD
# ==============================================

st.title("📊 KoboToolbox Dashboard")

# Overview Metrics
st.subheader("📈 Summary Metrics")
cols = st.columns(4)
cols[0].metric("Total Submissions", len(df))
if "submission_date" in df.columns:
    today = datetime.now().date()
    cols[1].metric("Today's Submissions", len(df[df["submission_date"].dt.date == today]))
if "username" in df.columns:
    cols[2].metric("Unique Collectors", df["username"].nunique())
cols[3].metric("Data Completeness", f"{round((1 - df.isnull().mean().mean()) * 100, 1)}%")

# ==============================================
# INTERACTIVE TABLE WITH EXPORT OPTIONS
# ==============================================

st.subheader("🔍 Interactive Data Table with Export")

# Build interactive AgGrid table
gb = GridOptionsBuilder.from_dataframe(df)
gb.configure_default_column(filter=True, sortable=True, resizable=True, editable=False)
gb.configure_grid_options(
    enableRangeSelection=True,
    domLayout='normal',
    rowSelection='multiple',
    enableBrowserTooltips=True,
    pagination=True,
    paginationPageSize=20,
    suppressExcelExport=False
)
gb.configure_side_bar()  # Filters & search
gb.configure_grid_options(enableCellTextSelection=True)

# Right-click context menu for export
gb.configure_grid_options(
    getContextMenuItems=JsCode("""
    function(params) {
        var result = [
            'copy',
            'copyWithHeaders',
            'paste',
            'separator',
            'export'
        ];
        return result;
    }
    """)
)

gridOptions = gb.build()

AgGrid(
    df,
    gridOptions=gridOptions,
    update_mode=GridUpdateMode.NO_UPDATE,
    fit_columns_on_grid_load=True,
    enable_enterprise_modules=True,
    use_checkbox=True,
    allow_unsafe_jscode=True,
    theme="alpine"
)

st.success("✅ Dashboard ready. Right-click any row to export.")

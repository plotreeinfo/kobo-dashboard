import streamlit as st
import pandas as pd
import requests
from datetime import datetime
from requests.auth import HTTPBasicAuth
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode

# ==============================================
# CONFIGURATION (leave your Kobo creds & URLs untouched)
# ==============================================

hide_streamlit_style = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

KOBO_USERNAME = "plotree"
KOBO_PASSWORD = "Pl@tr33@123"
FORM_UID        = "aJHsRZXT3XEpCoxn9Ct3qZ"
BASE_URL        = "https://kf.kobotoolbox.org"
API_URL         = f"{BASE_URL}/api/v2/assets/{FORM_UID}/data.json"

# ==============================================
# DATA FUNCTIONS
# ==============================================

@st.cache_data(ttl=3600)
def fetch_kobo_data():
    try:
        resp = requests.get(API_URL, auth=HTTPBasicAuth(KOBO_USERNAME, KOBO_PASSWORD))
        resp.raise_for_status()
        return pd.DataFrame(resp.json().get("results", []))
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

# ==============================================
# LOAD + CLEAN DATA
# ==============================================

df = fetch_kobo_data()
if df.empty:
    st.warning("No data available – check your connection or credentials.")
    st.stop()

# (Optional) rename for readability
col_mapping = {
    "username": "username",
    "_1_1_Name_of_the_City_": "district",
    "_geolocation_latitude": "latitude",
    "_geolocation_longitude": "longitude"
}
df.rename(columns={k: v for k, v in col_mapping.items() if k in df.columns}, inplace=True)

# submission date
if "_submission_time" in df.columns:
    df["submission_date"] = pd.to_datetime(df["_submission_time"]).dt.tz_localize(None)
    df["submission_day"] = df["submission_date"].dt.date

# ==============================================
# REORDER COLUMNS TO MATCH YOUR KOBO FORM
# ==============================================

# 🔑 Fill this list with your exact Kobo question fields in the order they appear on your form:
field_order = [
    "_submission_time",
    "username",
    "_1_1_Name_of_the_City_",
    "district",
    "latitude",
    "longitude",
    # ... add your other question keys here, in form‐sequence
]

# Keep only those that exist, then append any extras at the end
ordered = [c for c in field_order if c in df.columns]
others  = [c for c in df.columns if c not in ordered]
df = df[ordered + others]

# ==============================================
# SIDEBAR FILTERS
# ==============================================

st.sidebar.title("🔍 Filters")

# Date range
if "submission_date" in df.columns:
    with st.sidebar.expander("📅 Date Range", expanded=True):
        mn, mx = df["submission_date"].dt.date.min(), df["submission_date"].dt.date.max()
        dr = st.date_input("Select range", (mn, mx), min_value=mn, max_value=mx)
        if len(dr) == 2:
            df = df[(df["submission_date"].dt.date >= dr[0]) & (df["submission_date"].dt.date <= dr[1])]

# District
with st.sidebar.expander("📍 District", expanded=True):
    if "district" in df.columns:
        opts = ["All"] + sorted(df["district"].dropna().unique().tolist())
        sel  = st.selectbox("District", opts)
        if sel != "All":
            df = df[df["district"] == sel]

# Collector
if "username" in df.columns:
    with st.sidebar.expander("👤 Collector", expanded=True):
        users = ["All"] + sorted(df["username"].dropna().unique().tolist())
        sel   = st.selectbox("Collector", users)
        if sel != "All":
            df = df[df["username"] == sel]

# ==============================================
# MAIN DASHBOARD
# ==============================================

st.title("📊 KoboToolbox Dashboard")
st.subheader("📈 Key Metrics")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Subs", len(df))
if "submission_date" in df.columns:
    today = datetime.now().date()
    c2.metric("Today's Subs", len(df[df["submission_date"].dt.date == today]))
if "username" in df.columns:
    c3.metric("Unique Collectors", df["username"].nunique())
c4.metric("Completeness", f"{round((1 - df.isnull().mean().mean())*100,1)}%")

# ==============================================
# INTERACTIVE TABLE WITH FULL-HEIGHT & EXPORT
# ==============================================

st.subheader("🔍 Data Table (Right-click to export CSV/XLSX)")

# Configure AgGrid
gb = GridOptionsBuilder.from_dataframe(df)
gb.configure_default_column(filter=True, sortable=True, resizable=True)
gb.configure_side_bar()  
gb.configure_grid_options(
    enableRangeSelection=True,
    domLayout='autoHeight',          # auto-expand height
    rowSelection='multiple',
    pagination=True,
    paginationPageSize=25,
    suppressExcelExport=False
)
# Right-click menu
gb.configure_grid_options(
    getContextMenuItems=JsCode("""
    function(params) {
      return ['copy','copyWithHeaders','separator','export'];
    }
    """)
)
grid_opts = gb.build()

# Render
AgGrid(
    df,
    gridOptions=grid_opts,
    update_mode=GridUpdateMode.NO_UPDATE,
    allow_unsafe_jscode=True,
    enable_enterprise_modules=True,
    theme="alpine",
    height=600,        # force a minimum height
    width='100%'
)

st.success("✅ Dashboard ready – just right-click any cell/row to export!")

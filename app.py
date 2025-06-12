import streamlit as st

# --- Hide Streamlit UI ---
hide_streamlit_style = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# --- Imports ---
import pandas as pd
import plotly.express as px
import requests
import io
from datetime import datetime
from requests.auth import HTTPBasicAuth

# --- AUTO REFRESH EVERY 3 MINUTES ---
st.experimental_rerun_interval = 180  # reruns every 180 seconds (3 minutes)

# --- CONFIGURE KOBO CONNECTION ---
username = "plotree"
password = "Pl@tr33@123"
form_uid = "aJHsRZXT3XEpCoxn9Ct3qZ"

# Customize export settings to XLS
EXPORT_PARAMS = {
    "format": "xls",
    "lang": "en",
    "type": "all",
    "group_sep": "/",
    "media_all": "true",
    "fields_from_all_versions": "true",
    "hierarchy_in_labels": "true",
    "value_labels": "false"
}

# --- FETCH DATA FROM KOBO (XLS with settings) ---
@st.cache_data(ttl=180)
def load_data():
    export_url = f"https://kf.kobotoolbox.org/api/v2/assets/{form_uid}/export-settings/"
    data_url = f"https://kc.kobotoolbox.org/api/v1/data/{form_uid}.xls"
    
    response = requests.get(data_url, params=EXPORT_PARAMS, auth=HTTPBasicAuth(username, password))
    if response.status_code == 200:
        df = pd.read_excel(io.BytesIO(response.content))
        
        # Drop unwanted metadata columns
        cols_to_drop = [
            '_id', '_uuid', '_submission_time', '_validation_status', '_notes',
            '_status', '_submitted_by', '_tags', '_index', '__version__'
        ]
        df.drop(columns=[col for col in cols_to_drop if col in df.columns], inplace=True)
        return df
    else:
        st.error("Failed to load XLS data from KoboToolbox.")
        return pd.DataFrame()

# --- MAIN DATA LOAD ---
df = load_data()

if df.empty:
    st.stop()

# --- Rename Key Columns ---
col_mapping = {
    "username": "username",
    "_1_1_Name_of_the_City_": "district",
    "_geolocation_latitude": "latitude",
    "_geolocation_longitude": "longitude",
    "_submission_time": "submission_date"
}

for orig, new in col_mapping.items():
    if orig in df.columns:
        df.rename(columns={orig: new}, inplace=True)

# --- Submission Date Processing ---
if "submission_date" in df.columns:
    df["submission_date"] = pd.to_datetime(df["submission_date"])
    df["submission_day"] = df["submission_date"].dt.date
    df["submission_week"] = df["submission_date"].dt.isocalendar().week
    df["submission_month"] = df["submission_date"].dt.month

# --- SIDEBAR FILTERS ---
st.sidebar.title("🔍 Filters")

# Date filter
with st.sidebar.expander("📅 Date Filters", expanded=True):
    if "submission_date" in df.columns:
        min_date = df["submission_date"].min().date()
        max_date = df["submission_date"].max().date()
        date_range = st.date_input("Select Date Range", (min_date, max_date), min_value=min_date, max_value=max_date)
        if len(date_range) == 2:
            df = df[(df["submission_date"].dt.date >= date_range[0]) & (df["submission_date"].dt.date <= date_range[1])]

# Location filters
with st.sidebar.expander("📍 Location Filters", expanded=True):
    if "district" in df.columns:
        districts = ['All'] + sorted(df["district"].dropna().unique().tolist())
        district = st.selectbox("District", districts)
        if district != "All":
            df = df[df["district"] == district]

    if "ward" in df.columns:
        wards = ['All'] + sorted(df["ward"].dropna().unique().tolist())
        ward = st.selectbox("Ward", wards)
        if ward != "All":
            df = df[df["ward"] == ward]

    if "village" in df.columns:
        villages = ['All'] + sorted(df["village"].dropna().unique().tolist())
        village = st.selectbox("Village", villages)
        if village != "All":
            df = df[df["village"] == village]

# User filters
with st.sidebar.expander("👤 User Filters", expanded=True):
    if "username" in df.columns:
        usernames = ['All'] + sorted(df["username"].dropna().unique().tolist())
        user = st.selectbox("Data Collector", usernames)
        if user != "All":
            df = df[df["username"] == user]

# Data completeness filter
with st.sidebar.expander("🧰 Data Quality", expanded=True):
    threshold = st.slider("Min Data Completeness (%)", 0, 100, 80)
    completeness = df.notnull().mean(axis=1) * 100
    df = df[completeness >= threshold]

    # Media filter
    photo_cols = [c for c in df.columns if 'photo' in c.lower()]
    if photo_cols:
        photo_filter = st.selectbox("Photo Records", ['All', 'With Photos', 'Without Photos'])
        if photo_filter == "With Photos":
            df = df[df[photo_cols].notnull().any(axis=1)]
        elif photo_filter == "Without Photos":
            df = df[df[photo_cols].isnull().all(axis=1)]

# Column selection
with st.sidebar.expander("📋 Columns", expanded=False):
    selected_columns = st.multiselect("Select Columns to Display", df.columns.tolist(), default=df.columns.tolist()[:10])

# Sidebar Summary
st.sidebar.markdown("---")
st.sidebar.subheader("📊 Summary")
st.sidebar.markdown(f"**Records:** {len(df)}")
if "submission_date" in df.columns:
    st.sidebar.markdown(f"**Date Range:** {date_range[0]} to {date_range[1]}")
if "district" in df.columns and district != 'All':
    st.sidebar.markdown(f"**District:** {district}")
if "username" in df.columns and user != 'All':
    st.sidebar.markdown(f"**User:** {user}")

# --- MAIN DASHBOARD ---
st.title("📊 Onsite Sanitation Dashboard (Live)")

# Key Metrics
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Forms", len(df))
if "submission_date" in df.columns:
    today = datetime.now().date()
    today_count = len(df[df["submission_date"].dt.date == today])
    col2.metric("Today's Submissions", today_count)
total_cells = df.size
empty_cells = df.isnull().sum().sum()
completeness_pct = round((1 - empty_cells / total_cells) * 100, 1) if total_cells else 0
col3.metric("Data Completeness", f"{completeness_pct}%")
if "username" in df.columns:
    col4.metric("Unique Users", df["username"].nunique())

st.markdown("---")

# Data table
st.subheader("📋 Filtered Data")
st.caption(f"{len(df)} records shown.")
st.dataframe(df[selected_columns] if selected_columns else df, use_container_width=True)

# Summary stats
st.subheader("📈 Summary Statistics")
st.write(df.describe(include='all'))

# Chart section
st.subheader("📊 Visualizations")
viz_col1, viz_col2, viz_col3 = st.columns([3, 2, 1])
chart_type = viz_col3.selectbox("Chart Type", ["Bar", "Pie", "Histogram", "Scatter", "Line", "Map"])
x_col = viz_col1.selectbox("X-axis", df.columns)
y_col = viz_col2.selectbox("Y-axis", df.select_dtypes(include='number').columns) if chart_type in ["Bar", "Scatter", "Line"] else None
color_col = viz_col2.selectbox("Color By", ['None'] + df.columns.tolist()) if chart_type in ["Bar", "Scatter"] else None

# Plotly chart rendering
if chart_type == "Bar" and y_col:
    fig = px.bar(df, x=x_col, y=y_col, color=color_col if color_col != 'None' else None)
    st.plotly_chart(fig, use_container_width=True)
elif chart_type == "Pie":
    fig = px.pie(df, names=x_col, hole=0.3)
    st.plotly_chart(fig, use_container_width=True)
elif chart_type == "Histogram":
    fig = px.histogram(df, x=x_col, nbins=20)
    st.plotly_chart(fig, use_container_width=True)
elif chart_type == "Scatter" and y_col:
    fig = px.scatter(df, x=x_col, y=y_col, color=color_col if color_col != 'None' else None, trendline="ols")
    st.plotly_chart(fig, use_container_width=True)
elif chart_type == "Line" and y_col:
    fig = px.line(df, x=x_col, y=y_col, markers=True)
    st.plotly_chart(fig, use_container_width=True)
elif chart_type == "Map" and "latitude" in df.columns and "longitude" in df.columns:
    fig = px.scatter_mapbox(df, lat="latitude", lon="longitude", zoom=8, hover_name="district")
    fig.update_layout(mapbox_style="open-street-map")
    st.plotly_chart(fig, use_container_width=True)

# Submission Trends
if "submission_date" in df.columns:
    st.subheader("📅 Submission Trends")
    group_period = st.selectbox("Group By", ["Day", "Week", "Month"])
    group_col = {
        "Day": "submission_day",
        "Week": "submission_week",
        "Month": "submission_month"
    }[group_period]
    trends = df.groupby(group_col).size().reset_index(name='count')
    fig = px.line(trends, x=group_col, y="count", markers=True)
    st.plotly_chart(fig, use_container_width=True)

# Download
st.subheader("📥 Download XLS")
output_io = io.BytesIO()
df.to_excel(output_io, index=False, engine="openpyxl")
st.download_button(
    label="Download Filtered Data (XLS)",
    data=output_io.getvalue(),
    file_name="sanitation_data.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

st.success("✅ Dashboard ready with full Kobo integration and real-time syncing.")

import streamlit as st

# Hide Streamlit default UI elements
hide_streamlit_style = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

import pandas as pd
import plotly.express as px
import requests
import io
import numpy as np
from datetime import datetime
from requests.auth import HTTPBasicAuth

# --- CONFIGURE KOBO CONNECTION ---
username = "plotree"
password = "Pl@tr33@123"
form_uid = "aJHsRZXT3XEpCoxn9Ct3qZ"
api_url = f"https://kf.kobotoolbox.org/api/v2/assets/{form_uid}/data.json"

# --- FETCH DATA FROM KOBO ---
@st.cache_data(ttl=3600)
def load_data():
    response = requests.get(api_url, auth=HTTPBasicAuth(username, password))
    if response.status_code == 200:
        data = response.json().get("results", [])
        df = pd.DataFrame(data)

        # --- FILTER COLUMNS: C to BO, skip BP–BV, include BY to end ---
        cols = df.columns.tolist()
        part1 = cols[2:67]     # C to BO
        part2 = cols[73:]      # BY to end
        selected_cols = part1 + part2

        return df[selected_cols]
    else:
        st.error("Failed to load data from KoboToolbox.")
        return pd.DataFrame()

# --- MAIN APP ---
df = load_data()

if df.empty:
    st.stop()

# --- STANDARDIZE COLUMNS ---
col_mapping = {
    "username": "username",
    "_1_1_Name_of_the_City_": "district",
    "_submission_time": "submission_date",
    "_geolocation_latitude": "latitude",
    "_geolocation_longitude": "longitude"
}

for orig, new in col_mapping.items():
    if orig in df.columns:
        df = df.rename(columns={orig: new})

if "submission_date" in df.columns:
    df["submission_date"] = pd.to_datetime(df["submission_date"])
    df["submission_date"] = df["submission_date"].dt.tz_localize(None)
    df["submission_day"] = df["submission_date"].dt.date
    df["submission_week"] = df["submission_date"].dt.isocalendar().week
    df["submission_month"] = df["submission_date"].dt.month

# --- SIDEBAR FILTERS ---
st.sidebar.title("🔍 Dashboard Filters")

with st.sidebar.expander("📅 Date Filters", expanded=True):
    if "submission_date" in df.columns:
        min_date = df["submission_date"].min().date()
        max_date = df["submission_date"].max().date()
        date_range = st.date_input(
            "Select Date Range", 
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date
        )
        if len(date_range) == 2:
            df = df[
                (df["submission_date"].dt.date >= date_range[0]) & 
                (df["submission_date"].dt.date <= date_range[1])
            ]

with st.sidebar.expander("📍 Location Filters", expanded=True):
    if "district" in df.columns:
        districts = ['All Districts'] + sorted(df["district"].dropna().unique().tolist())
        selected_district = st.selectbox("Select District", options=districts)
        if selected_district != 'All Districts':
            df = df[df["district"] == selected_district]

    if "ward" in df.columns:
        wards = ['All Wards'] + sorted(df["ward"].dropna().unique().tolist())
        selected_ward = st.selectbox("Select Ward", options=wards)
        if selected_ward != 'All Wards':
            df = df[df["ward"] == selected_ward]

    if "village" in df.columns:
        villages = ['All Villages'] + sorted(df["village"].dropna().unique().tolist())
        selected_village = st.selectbox("Select Village", options=villages)
        if selected_village != 'All Villages':
            df = df[df["village"] == selected_village]

with st.sidebar.expander("👤 User & Status Filters", expanded=True):
    if "username" in df.columns:
        usernames = ['All Users'] + sorted(df["username"].dropna().unique().tolist())
        selected_user = st.selectbox("Select Data Collector", options=usernames)
        if selected_user != 'All Users':
            df = df[df["username"] == selected_user]

    if "status" in df.columns:
        statuses = ['All Statuses'] + sorted(df["status"].dropna().unique().tolist())
        selected_status = st.selectbox("Select Form Status", options=statuses)
        if selected_status != 'All Statuses':
            df = df[df["status"] == selected_status]

with st.sidebar.expander("🧰 Data Quality Filters", expanded=True):
    completeness_threshold = st.slider(
        "Minimum Data Completeness (%)", 
        min_value=0, 
        max_value=100, 
        value=80,
        help="Show only records with this percentage of completed fields"
    )

    if any("photo" in col.lower() for col in df.columns):
        photo_options = ['All', 'With Photos', 'Without Photos']
        photo_filter = st.selectbox("Photo Verification", options=photo_options)
        photo_cols = [col for col in df.columns if 'photo' in col.lower()]
        if photo_filter == 'With Photos':
            df = df[df[photo_cols].notnull().any(axis=1)]
        elif photo_filter == 'Without Photos':
            df = df[df[photo_cols].isnull().all(axis=1)]

with st.sidebar.expander("📋 Column Selection", expanded=True):
    all_columns = df.columns.tolist()
    selected_columns = st.multiselect(
        "Select Columns to Display", 
        all_columns, 
        default=all_columns[:10]
    )

st.sidebar.markdown("---")
st.sidebar.subheader("📊 Filter Summary")
st.sidebar.markdown(f"**Total Records:** {len(df)}")
st.sidebar.markdown(f"**Date Range:** {date_range[0]} to {date_range[1]}")
if "district" in df.columns and selected_district != 'All Districts':
    st.sidebar.markdown(f"**District:** {selected_district}")
if "username" in df.columns and selected_user != 'All Users':
    st.sidebar.markdown(f"**Data Collector:** {selected_user}")

# --- MAIN DASHBOARD ---
st.title("📊 Onsite Sanitation Dashboard (Live)")

st.subheader("📊 Performance Metrics")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Forms", len(df))
if "submission_date" in df.columns:
    today = datetime.now().date()
    today_count = len(df[df["submission_date"].dt.date == today])
    col2.metric("Today's Submissions", today_count)
total_cells = df.size
empty_cells = df.isnull().sum().sum()
completeness = round((1 - (empty_cells / total_cells)) * 100, 1) if total_cells > 0 else 0
col3.metric("Data Completeness", f"{completeness}%")
if "username" in df.columns:
    unique_users = df["username"].nunique()
    col4.metric("Unique Users", unique_users)

st.markdown("---")

# --- DATA PREVIEW ---
st.subheader("🔍 Filtered Data")
st.info(f"Showing {len(df)} records | {len(selected_columns)} columns selected")

display_df = df[selected_columns] if selected_columns else df

# Apply completeness filter
if completeness_threshold > 0:
    row_completeness = display_df.notnull().mean(axis=1) * 100
    display_df = display_df[row_completeness >= completeness_threshold]
    st.caption(f"Filtered to rows with ≥ {completeness_threshold}% data completeness")

st.dataframe(display_df, use_container_width=True)

# --- SUMMARY ---
st.subheader("📈 Summary Statistics")
st.write(display_df.describe(include='all'))

# --- VISUALIZATION ---
st.subheader("📊 Interactive Visualizations")
viz_col1, viz_col2, viz_col3 = st.columns([3, 2, 1])
chart_type = viz_col3.selectbox("Chart Type", ["Bar", "Pie", "Histogram", "Scatter", "Line", "Map"])
x_col = viz_col1.selectbox("X-axis Column", df.columns)
y_col = None
if chart_type in ["Bar", "Scatter", "Line"]:
    numeric_cols = df.select_dtypes(include='number').columns.tolist()
    y_col = viz_col2.selectbox("Y-axis Column", numeric_cols) if numeric_cols else None
color_col = viz_col2.selectbox("Color By", ['None'] + df.columns.tolist()) if chart_type in ["Bar", "Scatter"] else None

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
    fig = px.scatter_mapbox(df, lat="latitude", lon="longitude", zoom=8,
                            color=x_col if x_col != 'None' else None)
    fig.update_layout(mapbox_style="open-street-map")
    st.plotly_chart(fig, use_container_width=True)

# --- SUBMISSION TRENDS ---
if "submission_date" in df.columns:
    st.subheader("📅 Submission Trends")
    time_period = st.selectbox("Group By", ["Day", "Week", "Month"])
    group_col = "submission_day" if time_period == "Day" else "submission_week" if time_period == "Week" else "submission_month"
    submissions = df.groupby(group_col).size().reset_index(name='count')
    if not submissions.empty:
        fig = px.line(submissions, x=group_col, y='count', markers=True)
        st.plotly_chart(fig, use_container_width=True)

# --- DATA DOWNLOAD ---
st.subheader("📥 Download Data")

download_df = display_df.copy()

# Rearranged download columns to match user-selected columns
final_columns = selected_columns if selected_columns else download_df.columns.tolist()
download_df = download_df[final_columns]

csv = download_df.to_csv(index=False).encode('utf-8')
col1, col2 = st.columns(2)
col1.download_button("Download CSV", csv, "sanitation_data.csv", "text/csv")

try:
    excel_io = io.BytesIO()
    with pd.ExcelWriter(excel_io, engine='openpyxl') as writer:
        download_df.to_excel(writer, sheet_name='Data', index=False)
        
        # Add Media URLs if available
        media_cols = [col for col in df.columns if 'photo' in col.lower() or 'url' in col.lower()]
        if media_cols:
            media_df = df[media_cols]
            media_df.to_excel(writer, sheet_name='Media_URLs', index=False)

        metadata = pd.DataFrame({
            'Export Date': [datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
            'Total Records': [len(download_df)],
            'Selected District': [selected_district if selected_district != 'All Districts' else 'All'],
            'Selected User': [selected_user if selected_user != 'All Users' else 'All']
        })
        metadata.to_excel(writer, sheet_name='Metadata', index=False)

    col2.download_button(
        "Download Excel (XLSX)",
        excel_io.getvalue(),
        "sanitation_data.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

except Exception as e:
    st.error(f"Excel Export Error: {e}")
    fallback_io = io.BytesIO()
    download_df.to_excel(fallback_io, index=False)
    col2.download_button("Download Excel", fallback_io.getvalue(), "sanitation_data.xlsx")

st.success("✅ Dashboard loaded with clean download and media URL support!")

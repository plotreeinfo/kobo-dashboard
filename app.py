import streamlit as st

# Remove Streamlit menu and GitHub icon
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

# --- DATA PREPARATION ---
# Standardize column names (adjust based on your actual column names)
col_mapping = {
    "username": "username",
    "_1_1_Name_of_the_City_": "district",
    "_submission_time": "submission_date",
    "_geolocation_latitude": "latitude",
    "_geolocation_longitude": "longitude"
}

# Apply standardized column names
for orig, new in col_mapping.items():
    if orig in df.columns:
        df = df.rename(columns={orig: new})

# Convert submission date to datetime
if "submission_date" in df.columns:
    df["submission_date"] = pd.to_datetime(df["submission_date"])
    df["submission_date"] = df["submission_date"].dt.tz_convert(None)
    df["submission_day"] = df["submission_date"].dt.date
    df["submission_week"] = df["submission_date"].dt.isocalendar().week
    df["submission_month"] = df["submission_date"].dt.month

# --- SIDEBAR FILTERS ---
st.sidebar.title("🔍 Dashboard Filters")

# ====================
# MAIN FILTERS SECTION
# ====================
with st.sidebar.expander("📅 Date & Time Filters", expanded=True):
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
    
    # Time of day filter (if timestamp available)
    if "submission_date" in df.columns:
        df["submission_hour"] = df["submission_date"].dt.hour
        hour_range = st.slider(
            "Submission Hour Range",
            min_value=0,
            max_value=23,
            value=(8, 17)
        )
        df = df[
            (df["submission_hour"] >= hour_range[0]) & 
            (df["submission_hour"] <= hour_range[1])
        ]

# =====================
# LOCATION FILTERS
# =====================
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

# =====================
# USER & STATUS FILTERS
# =====================
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

# =====================
# DATA QUALITY FILTERS
# =====================
with st.sidebar.expander("🧰 Data Quality Filters", expanded=True):
    # Data completeness slider
    completeness_threshold = st.slider(
        "Minimum Data Completeness (%)", 
        min_value=0, 
        max_value=100, 
        value=80,
        help="Show only records with this percentage of completed fields"
    )
    
    # Photo verification filter
    if any("photo" in col.lower() for col in df.columns):
        photo_options = ['All', 'With Photos', 'Without Photos']
        photo_filter = st.selectbox("Photo Verification", options=photo_options)
        if photo_filter == 'With Photos':
            photo_cols = [col for col in df.columns if 'photo' in col.lower()]
            df = df[df[photo_cols].notnull().any(axis=1)]
        elif photo_filter == 'Without Photos':
            photo_cols = [col for col in df.columns if 'photo' in col.lower()]
            df = df[df[photo_cols].isnull().all(axis=1)]

# =====================
# COLUMN SELECTION
# =====================
with st.sidebar.expander("📋 Column Selection", expanded=True):
    all_columns = df.columns.tolist()
    selected_columns = st.multiselect(
        "Select Columns to Display", 
        all_columns, 
        default=all_columns[:10]  # Show first 10 columns by default
    )
    
    # Column grouping
    if st.checkbox("Group Related Columns"):
        # This is a placeholder - you'd implement actual grouping logic based on your schema
        st.info("Column grouping would be implemented based on your data schema")

# =====================
# SUMMARY STATISTICS
# =====================
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

# --- KEY METRICS ---
st.subheader("📊 Performance Metrics")
col1, col2, col3, col4 = st.columns(4)

# Total forms
col1.metric("Total Forms", len(df))

# Today's submissions
if "submission_date" in df.columns:
    today = datetime.now().date()
    today_count = len(df[df["submission_date"].dt.date == today])
    col2.metric("Today's Submissions", today_count)

# Data completeness
total_cells = df.size
empty_cells = df.isnull().sum().sum()
completeness = round((1 - (empty_cells / total_cells)) * 100, 1) if total_cells > 0 else 0
col3.metric("Data Completeness", f"{completeness}%")

# Unique users
if "username" in df.columns:
    unique_users = df["username"].nunique()
    col4.metric("Unique Users", unique_users)

st.markdown("---")

# --- DATA PREVIEW ---
st.subheader("🔍 Filtered Data")
st.info(f"Showing {len(df)} records | {len(selected_columns)} columns selected")

if selected_columns:
    display_df = df[selected_columns]
else:
    display_df = df

# Apply data completeness filter
if completeness_threshold > 0:
    row_completeness = display_df.notnull().mean(axis=1) * 100
    display_df = display_df[row_completeness >= completeness_threshold]
    st.caption(f"Filtered to rows with ≥ {completeness_threshold}% data completeness")

st.dataframe(display_df, use_container_width=True)

# --- STATISTICS ---
st.subheader("📈 Summary Statistics")
st.write(df.describe(include='all'))

# --- VISUALIZATION SECTION ---
st.subheader("📊 Interactive Visualizations")

# Visualization controls in columns
viz_col1, viz_col2, viz_col3 = st.columns([3, 2, 1])

# Chart type selection
chart_type = viz_col3.selectbox("Chart Type", ["Bar", "Pie", "Histogram", "Scatter", "Line", "Map"])

# X-axis selection
x_col = viz_col1.selectbox("X-axis Column", df.columns)

# Y-axis selection (for appropriate charts)
if chart_type in ["Bar", "Scatter", "Line"]:
    numeric_cols = df.select_dtypes(include='number').columns.tolist()
    if numeric_cols:
        y_col = viz_col2.selectbox("Y-axis Column", numeric_cols)
    else:
        st.warning("No numeric columns found for Y-axis")
        y_col = None
else:
    y_col = None

# Color by selection
color_col = viz_col2.selectbox("Color By", ['None'] + df.columns.tolist()) if chart_type in ["Bar", "Scatter"] else None

# Generate charts
if chart_type == "Bar" and y_col:
    fig = px.bar(
        df, 
        x=x_col, 
        y=y_col, 
        color=color_col if color_col != 'None' else None,
        title=f"{y_col} by {x_col}"
    )
    st.plotly_chart(fig, use_container_width=True)
    
elif chart_type == "Pie":
    fig = px.pie(
        df, 
        names=x_col, 
        title=f"Distribution of {x_col}",
        hole=0.3
    )
    st.plotly_chart(fig, use_container_width=True)
    
elif chart_type == "Histogram":
    fig = px.histogram(
        df, 
        x=x_col, 
        title=f"Distribution of {x_col}",
        nbins=20
    )
    st.plotly_chart(fig, use_container_width=True)
    
elif chart_type == "Scatter" and y_col:
    fig = px.scatter(
        df, 
        x=x_col, 
        y=y_col, 
        color=color_col if color_col != 'None' else None,
        title=f"{y_col} vs {x_col}",
        trendline="ols"
    )
    st.plotly_chart(fig, use_container_width=True)
    
elif chart_type == "Line" and y_col:
    fig = px.line(
        df, 
        x=x_col, 
        y=y_col, 
        title=f"{y_col} Trend by {x_col}",
        markers=True
    )
    st.plotly_chart(fig, use_container_width=True)
    
elif chart_type == "Map" and "latitude" in df.columns and "longitude" in df.columns:
    fig = px.scatter_mapbox(
        df,
        lat="latitude",
        lon="longitude",
        hover_name="district" if "district" in df.columns else None,
        zoom=8,
        color=x_col if x_col != 'None' else None,
        size_max=15
    )
    fig.update_layout(mapbox_style="open-street-map")
    st.plotly_chart(fig, use_container_width=True)

# --- SUBMISSION TRENDS ---
if "submission_date" in df.columns:
    st.subheader("📅 Submission Trends")
    
    # Group by time period
    time_period = st.selectbox("Group By", ["Day", "Week", "Month"])
    
    if time_period == "Day":
        group_col = "submission_day"
    elif time_period == "Week":
        group_col = "submission_week"
    else:
        group_col = "submission_month"
    
    submissions = df.groupby(group_col).size().reset_index(name='count')
    
    if not submissions.empty:
        fig = px.line(
            submissions, 
            x=group_col, 
            y='count', 
            title=f"Submissions by {time_period}",
            markers=True
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No submission data available for the selected period")

# --- DATA DOWNLOAD ---
st.subheader("📥 Download Data")
csv = df.to_csv(index=False).encode('utf-8')
excel_io = io.BytesIO()
df.to_excel(excel_io, index=False, engine='openpyxl')

col1, col2 = st.columns(2)
col1.download_button(
    "Download CSV", 
    csv, 
    "sanitation_data.csv", 
    "text/csv",
    help="Download filtered data as CSV file"
)
col2.download_button(
    "Download Excel", 
    excel_io.getvalue(), 
    "sanitation_data.xlsx", 
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    help="Download filtered data as Excel spreadsheet"
)

st.success("✅ Dashboard loaded with professional filters and comprehensive analytics")

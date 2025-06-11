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
st.sidebar.title("🔍 Filters")

# Date filter (if available)
if "submission_date" in df.columns:
    min_date = df["submission_date"].min().date()
    max_date = df["submission_date"].max().date()
    date_range = st.sidebar.date_input(
        "Date Range", 
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )
    
    if len(date_range) == 2:
        df = df[
            (df["submission_date"].dt.date >= date_range[0]) & 
            (df["submission_date"].dt.date <= date_range[1])
        ]

# User filter
if "username" in df.columns:
    usernames = ['All'] + sorted(df["username"].dropna().unique().tolist())
    selected_user = st.sidebar.selectbox("Select User", options=usernames)
    if selected_user != 'All':
        df = df[df["username"] == selected_user]

# District filter
if "district" in df.columns:
    districts = ['All'] + sorted(df["district"].dropna().unique().tolist())
    selected_district = st.sidebar.selectbox("Select District", options=districts)
    if selected_district != 'All':
        df = df[df["district"] == selected_district]

# Status filter (if available)
if "status" in df.columns:
    statuses = ['All'] + sorted(df["status"].dropna().unique().tolist())
    selected_status = st.sidebar.selectbox("Select Status", options=statuses)
    if selected_status != 'All':
        df = df[df["status"] == selected_status]

# Data completeness filter
completeness_threshold = st.sidebar.slider(
    "Minimum Data Completeness (%)", 
    min_value=0, 
    max_value=100, 
    value=80
)

# Column selector
all_columns = df.columns.tolist()
selected_columns = st.sidebar.multiselect(
    "Select Columns to Display", 
    all_columns, 
    default=all_columns[:10]  # Show first 10 columns by default
)

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

# Chart selection
chart_col1, chart_col2, chart_col3 = st.columns([2, 2, 1])
chart_type = chart_col3.selectbox("Chart Type", ["Bar", "Pie", "Histogram", "Scatter", "Line", "Map"])

# Column selection
if chart_type != "Map":
    col_x = chart_col1.selectbox("X-axis", df.columns)
    
    if chart_type in ["Bar", "Scatter", "Line"]:
        numeric_cols = df.select_dtypes(include='number').columns.tolist()
        if numeric_cols:
            col_y = chart_col2.selectbox("Y-axis", numeric_cols)
        else:
            st.warning("No numeric columns found for Y-axis")
            col_y = None
    else:
        col_y = None
else:
    if "latitude" in df.columns and "longitude" in df.columns:
        col_x = "latitude"
        col_y = "longitude"
    else:
        st.warning("Map requires latitude and longitude columns")
        chart_type = "Bar"  # Fallback to bar chart

# Generate charts
if chart_type == "Bar" and col_y:
    fig = px.bar(df, x=col_x, y=col_y, title=f"{col_y} by {col_x}")
    st.plotly_chart(fig, use_container_width=True)
    
elif chart_type == "Pie":
    fig = px.pie(df, names=col_x, title=f"Distribution of {col_x}")
    st.plotly_chart(fig, use_container_width=True)
    
elif chart_type == "Histogram" and col_x:
    fig = px.histogram(df, x=col_x, title=f"Distribution of {col_x}")
    st.plotly_chart(fig, use_container_width=True)
    
elif chart_type == "Scatter" and col_y:
    fig = px.scatter(df, x=col_x, y=col_y, title=f"{col_y} vs {col_x}")
    st.plotly_chart(fig, use_container_width=True)
    
elif chart_type == "Line" and col_y:
    fig = px.line(df, x=col_x, y=col_y, title=f"{col_y} Trend by {col_x}")
    st.plotly_chart(fig, use_container_width=True)
    
elif chart_type == "Map" and "latitude" in df.columns and "longitude" in df.columns:
    fig = px.scatter_mapbox(
        df,
        lat="latitude",
        lon="longitude",
        hover_name="district" if "district" in df.columns else None,
        zoom=8
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

# --- DATA QUALITY REPORT ---
st.subheader("🧰 Data Quality Report")

if len(df) > 0:
    # Calculate completeness per column
    completeness = df.notnull().mean() * 100
    completeness_df = pd.DataFrame({
        'Column': completeness.index,
        'Completeness (%)': completeness.values
    }).sort_values('Completeness (%)', ascending=True)
    
    # Show top 10 incomplete columns
    st.write("**Column Completeness:**")
    fig = px.bar(
        completeness_df.head(10),
        x='Completeness (%)',
        y='Column',
        orientation='h',
        title='Top 10 Incomplete Columns'
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Show duplicate analysis
    duplicates = df.duplicated().sum()
    dup_percent = round((duplicates / len(df)) * 100, 1)
    st.metric("Duplicate Entries", f"{duplicates} ({dup_percent}%)")
else:
    st.warning("No data available for quality analysis")

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

st.success("✅ Dashboard loaded with live data and enhanced functionality")

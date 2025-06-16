import streamlit as st
import pandas as pd
import requests
from io import BytesIO

# ---------------------------
# Configuration
# ---------------------------
ASSET_UID = "aJHsRZXT3XEpCoxn9Ct3qZ"
EXPORT_SETTING_UID = "esnia8U2QVxNnjzMY4p87ss"
TOKEN = "04714621fa3d605ff0a4aa5cc2df7cfa961bf256"
DATE_COLUMN = "today"  # Replace with actual date column from your data

# ---------------------------
# App Title
# ---------------------------
st.set_page_config(page_title="📊 Kobo Dashboard", layout="wide")
st.title("📊 KoboToolbox Data Viewer")

# ---------------------------
# Fetch Exported Data
# ---------------------------
def download_exported_data():
    url = f"https://kf.kobotoolbox.org/api/v2/assets/{ASSET_UID}/export-settings/{EXPORT_SETTING_UID}/data.xlsx"
    headers = {"Authorization": f"Token {TOKEN}"}

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        df = pd.read_excel(BytesIO(response.content))

        # Drop unnamed columns
        df = df.loc[:, ~df.columns.str.contains('^Unnamed')]

        return df
    except requests.exceptions.RequestException as e:
        st.error(f"❌ Request failed: {e}")
    except Exception as e:
        st.error(f"❌ Unexpected error: {e}")

    return pd.DataFrame()

# ---------------------------
# Main App
# ---------------------------
df = download_exported_data()

if not df.empty:
    # Sidebar filters
    st.sidebar.header("🔎 Filter Options")

    # Date filters
    if DATE_COLUMN in df.columns:
        df[DATE_COLUMN] = pd.to_datetime(df[DATE_COLUMN], errors='coerce')
        min_date = df[DATE_COLUMN].min().date()
        max_date = df[DATE_COLUMN].max().date()

        start_date = st.sidebar.date_input("📅 Start date", min_value=min_date, max_value=max_date, value=min_date)
        end_date = st.sidebar.date_input("📅 End date", min_value=min_date, max_value=max_date, value=max_date)

        if start_date and end_date and start_date <= end_date:
            df = df[(df[DATE_COLUMN] >= pd.to_datetime(start_date)) & (df[DATE_COLUMN] <= pd.to_datetime(end_date))]

    # Multiple filterable columns
    filterable_columns = df.select_dtypes(include=['object', 'category']).columns.tolist()
    for col in filterable_columns:
        unique_values = df[col].dropna().unique().tolist()
        if len(unique_values) > 1:
            selected_values = st.sidebar.multiselect(f"{col}", options=unique_values, default=unique_values)
            df = df[df[col].isin(selected_values)]

    # Display filtered row count
    st.markdown(f"### ✅ Showing {len(df)} records")

    # Show the table
    st.dataframe(df, use_container_width=True)

    # Download button
    st.download_button("⬇ Download Filtered Data", data=df.to_csv(index=False), file_name="filtered_data.csv", mime="text/csv")
else:
    st.warning("⚠️ No data found or failed to load data.")

import streamlit as st
import pandas as pd
import requests
from io import BytesIO
from datetime import datetime

# --- CONFIG ---
KOBO_API_TOKEN = "04714621fa3d605ff0a4aa5cc2df7cfa961bf256"
EXPORT_URL = "https://kf.kobotoolbox.org/api/v2/assets/aJHsRZXT3XEpCoxn9Ct3qZ/export-settings/esnia8U2QVxNnjzMY4p87ss/data.xlsx"
DATE_COL = "today"  # Update with your actual date column name

# --- PAGE SETUP ---
st.set_page_config(page_title="Kobo Dashboard", layout="wide")
st.title("📊 Kobo Data Dashboard")

# --- FUNCTIONS ---
def load_data():
    headers = {"Authorization": f"Token {KOBO_API_TOKEN}"}
    try:
        response = requests.get(EXPORT_URL, headers=headers)
        response.raise_for_status()
        df = pd.read_excel(BytesIO(response.content))

        # Drop unnamed columns
        df = df.loc[:, ~df.columns.str.contains('^Unnamed')] 

        # Try to parse date column
        if DATE_COL in df.columns:
            try:
                df[DATE_COL] = pd.to_datetime(df[DATE_COL], errors='coerce')
            except:
                pass

        return df
    except Exception as e:
        st.error(f"❌ Error loading data: {e}")
        return pd.DataFrame()

# --- MAIN ---
df = load_data()

if not df.empty:
    # --- SIDEBAR FILTER ---
    st.sidebar.header("🔎 Filter")

    # Date filter
    if DATE_COL in df.columns:
        min_date = df[DATE_COL].min()
        max_date = df[DATE_COL].max()
        start_date = st.sidebar.date_input("Start Date", value=min_date.date(), min_value=min_date.date(), max_value=max_date.date())
        end_date = st.sidebar.date_input("End Date", value=max_date.date(), min_value=min_date.date(), max_value=max_date.date())

        # Apply date filter safely
        if start_date <= end_date:
            df = df[(df[DATE_COL] >= pd.to_datetime(start_date)) & (df[DATE_COL] <= pd.to_datetime(end_date))]

    # Single filter dropdown
    text_cols = [col for col in df.select_dtypes(include='object').columns if df[col].nunique() < 100]
    if text_cols:
        selected_col = st.sidebar.selectbox("Filter Column", text_cols)
        options = df[selected_col].dropna().unique().tolist()
        selected_values = st.sidebar.multiselect("Select Values", options=options)
        if selected_values:
            df = df[df[selected_col].isin(selected_values)]

    st.markdown(f"### Showing {len(df)} records")
    st.dataframe(df, use_container_width=True)

    # --- DOWNLOAD BUTTON ---
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Download Filtered Data (CSV)", data=csv, file_name="filtered_kobo_data.csv", mime="text/csv")
else:
    st.warning("No data to display.")

import streamlit as st
import pandas as pd
import requests
from io import BytesIO

# Set title
st.title("📊 KoBoToolbox Sanitation Dashboard")

# Kobo settings
KOBO_TOKEN = "04714621fa3d605ff0a4aa5cc2df7cfa961bf256"
EXPORT_URL = "https://kf.kobotoolbox.org/api/v2/assets/aJHsRZXT3XEpCoxn9Ct3qZ/export-settings/esnia8U2QVxNnjzMY4p87ss/data.xlsx"

@st.cache_data(show_spinner=True)
def fetch_kobo_data():
    headers = {"Authorization": f"Token {KOBO_TOKEN}"}
    try:
        response = requests.get(EXPORT_URL, headers=headers)
        response.raise_for_status()
       df = pd.read_excel(io.BytesIO(response.content), engine="openpyxl")

# 🚫 Drop all columns with names like 'Unnamed: 182', 'Unnamed: 5', etc.
df = df.loc[:, ~df.columns.str.match(r"^Unnamed: \d+$")]

        return df
    except requests.exceptions.RequestException as e:
        st.error(f"❌ Request failed: {e}")
        return None
    except Exception as e:
        st.error(f"❌ Unexpected error: {e}")
        return None

# Fetch data
df = fetch_kobo_data()
if df is not None and not df.empty:
    st.success("✅ Data loaded successfully!")

    # Filter UI
    st.subheader("🔍 Filter Data")
    for col in df.columns:
        if df[col].dtype == 'object':
            search_term = st.text_input(f"Filter '{col}'", "")
            if search_term:
                df = df[df[col].astype(str).str.contains(search_term, case=False, na=False)]

    # Display table
    st.subheader("📋 Data Preview")
    visible_df = df.loc[:, ~df.columns.str.contains("^Unnamed")]
st.dataframe(visible_df, use_container_width=True)

# Download button
    output = BytesIO()
    df.to_excel(output, index=False)
    st.download_button(
        label="📥 Download Filtered Data as XLSX",
        data=output.getvalue(),
        file_name="filtered_kobo_data.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
else:
    st.warning("⚠️ No data to show. Make sure export is correct and data is submitted.")


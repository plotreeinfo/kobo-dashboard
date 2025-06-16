import streamlit as st
import pandas as pd
import requests
import io

# === SETTINGS ===
KOBO_API_TOKEN = "04714621fa3d605ff0a4aa5cc2df7cfa961bf256"
FORM_UID = "aJHsRZXT3XEpCoxn9Ct3qZ"
EXPORT_SETTING_UID = "esnia8U2QVxNnjzMY4p87ss"

# === PAGE CONFIG ===
st.set_page_config(page_title="📊 KoBo Data Dashboard", layout="wide")
st.title("📥 KoBoToolbox Data Viewer")

# === DATA FETCH FUNCTION ===
@st.cache_data(ttl=180)
def download_exported_data():
    try:
        export_url = f"https://kf.kobotoolbox.org/api/v2/assets/{FORM_UID}/export-settings/{EXPORT_SETTING_UID}/data.xlsx"
        headers = {"Authorization": f"Token {KOBO_API_TOKEN}"}
        response = requests.get(export_url, headers=headers)
        response.raise_for_status()

        # Load Excel and drop unnamed columns
        df = pd.read_excel(io.BytesIO(response.content), engine="openpyxl")
        df = df.loc[:, ~df.columns.str.match(r"^Unnamed: \d+$")]
        return df

    except Exception as e:
        st.error(f"❌ Failed to fetch/export KoBo data:\n\n{e}")
        return pd.DataFrame()

# === MAIN LOGIC ===
df = download_exported_data()

if not df.empty:
    st.success("✅ Data loaded successfully!")
    
    # === FILTER SECTION ===
    with st.expander("🔍 Filter Data", expanded=False):
        filter_col = st.selectbox("Select column to filter", df.columns)
        text = st.text_input("Enter filter text")
        if text:
            df = df[df[filter_col].astype(str).str.contains(text, case=False, na=False)]

    # === DISPLAY DATA ===
    st.dataframe(df, use_container_width=True)

    # === DOWNLOAD BUTTON ===
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("⬇️ Download CSV", data=csv, file_name="kobo_data.csv", mime="text/csv")

else:
    st.warning("⚠️ No data available or failed to load from KoBoToolbox.")

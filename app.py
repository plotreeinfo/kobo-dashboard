import streamlit as st
import pandas as pd
import requests
import io

# === SETTINGS ===
KOBO_API_TOKEN = "04714621fa3d605ff0a4aa5cc2df7cfa961bf256"
FORM_UID = "aJHsRZXT3XEpCoxn9Ct3qZ"
EXPORT_SETTING_UID = "esnia8U2QVxNnjzMY4p87ss"
DATE_COLUMN = "today"  # You can change this if your form uses a different date field

# === PAGE CONFIG ===
st.set_page_config(page_title="📊 KoBo Data Dashboard", layout="wide")
st.title("📥 KoBoToolbox Data Viewer")

# === FETCH AND CLEAN DATA ===
@st.cache_data(ttl=180)
def download_exported_data():
    try:
        url = f"https://kf.kobotoolbox.org/api/v2/assets/{FORM_UID}/export-settings/{EXPORT_SETTING_UID}/data.xlsx"
        headers = {"Authorization": f"Token {KOBO_API_TOKEN}"}
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        df = pd.read_excel(io.BytesIO(response.content), engine="openpyxl")
        df = df.loc[:, ~df.columns.str.match(r"^Unnamed: \d+$")]
        if DATE_COLUMN in df.columns:
            df[DATE_COLUMN] = pd.to_datetime(df[DATE_COLUMN], errors="coerce")
        return df
    except Exception as e:
        st.error(f"❌ Error fetching KoBo data:\n{e}")
        return pd.DataFrame()

df = download_exported_data()

if not df.empty:
    st.success("✅ Data loaded successfully!")

    original_count = len(df)

    # === SIDEBAR FILTERS ===
    st.sidebar.header("🔍 Filter Data")

    # Date filter
    if DATE_COLUMN in df.columns:
        min_date = df[DATE_COLUMN].min()
        max_date = df[DATE_COLUMN].max()
        start_date, end_date = st.sidebar.date_input(
            "📅 Date range",
            [min_date, max_date],
            min_value=min_date,
            max_value=max_date,
        )
        if start_date and end_date:
            df = df[df[DATE_COLUMN].between(pd.to_datetime(start_date), pd.to_datetime(end_date))]

    # Dynamic column filters
    selected_columns = st.sidebar.multiselect("🎯 Filter Columns", df.columns)

    for col in selected_columns:
        if pd.api.types.is_numeric_dtype(df[col]):
            min_val = float(df[col].min())
            max_val = float(df[col].max())
            step = (max_val - min_val) / 100 if max_val > min_val else 1
            selected_range = st.sidebar.slider(f"{col}", min_val, max_val, (min_val, max_val), step=step)
            df = df[df[col].between(*selected_range)]
        else:
            unique_vals = df[col].dropna().unique()
            selected_vals = st.sidebar.multiselect(f"{col}", unique_vals)
            if selected_vals:
                df = df[df[col].isin(selected_vals)]

    # === SHOW DATA ===
    st.markdown(f"**🔢 Showing {len(df)} of {original_count} records**")
    st.dataframe(df, use_container_width=True)

    # === DOWNLOAD BUTTON ===
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("⬇️ Download Filtered Data", data=csv, file_name="filtered_kobo_data.csv", mime="text/csv")
else:
    st.warning("⚠️ No data available. Please check export settings or form submissions.")

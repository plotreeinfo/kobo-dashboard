import streamlit as st
import pandas as pd
import requests

# --- Credentials and form ID ---
KOBO_API_TOKEN = "04714621fa3d605ff0a4aa5cc2df7cfa961bf256"
FORM_UID = "aJHsRZXT3XEpCoxn9Ct3qZ"
KOBO_BASE_URL = "https://kf.kobotoolbox.org"  # confirmed

# --- Securely fetch KoBo data ---
@st.cache_data(show_spinner=False)
def get_kobo_data():
    url = f"{KOBO_BASE_URL}/api/v2/assets/{FORM_UID}/data/"
    headers = {
        "Authorization": f"Token {KOBO_API_TOKEN}"
    }

    response = requests.get(url, headers=headers)

    if response.status_code == 401:
        st.error("❌ Unauthorized. Your API token may be incorrect or lack access.")
        st.text("🔐 Check if your token is correct and belongs to the form owner.")
        return pd.DataFrame()

    if response.status_code != 200:
        st.error(f"❌ Failed to fetch data. Status code: {response.status_code}")
        st.text(response.text[:500])
        return pd.DataFrame()

    try:
        data = response.json()
    except ValueError:
        st.error("❌ KoBo returned non-JSON (likely an error page or HTML).")
        st.text(response.text[:500])
        return pd.DataFrame()

    df = pd.DataFrame(data.get("results", []))

    # Drop unwanted columns
    drop_cols = [
        "start", "end", "_id", "_uuid", "_validation_status",
        "_notes", "_status", "_submitted_by", "_tags", "__version__"
    ]
    df = df.drop(columns=[col for col in drop_cols if col in df.columns], errors='ignore')
    return df

# --- Streamlit App Layout ---
st.set_page_config(page_title="KoBo Dashboard", layout="wide")
st.title("📊 KoBoToolbox Dashboard")

if 'kobo_df' not in st.session_state:
    st.session_state['kobo_df'] = None

if st.button("🔄 Load KoBo Data"):
    with st.spinner("Fetching..."):
        st.session_state['kobo_df'] = get_kobo_data()

if st.session_state['kobo_df'] is not None:
    df = st.session_state['kobo_df']
    if not df.empty:
        st.success(f"✅ {len(df)} records loaded")
        filter_col = st.selectbox("🔍 Filter column", df.columns)
        filter_val = st.text_input("Filter value")
        if filter_val:
            df = df[df[filter_col].astype(str).str.contains(filter_val, case=False, na=False)]
        st.dataframe(df, use_container_width=True)
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("⬇️ Download CSV", csv, "filtered_data.csv", "text/csv")

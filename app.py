import streamlit as st
import pandas as pd
import requests

# --- KoBoToolbox credentials and form info ---
KOBO_API_TOKEN = "04714621fa3d605ff0a4aa5cc2df7cfa961bf256"
FORM_UID = "aJHsRZXT3XEpCoxn9Ct3qZ"
KOBO_BASE_URL = "https://kf.kobotoolbox.org"

# --- Function to fetch KoBo data ---
@st.cache_data(show_spinner=False)
def get_kobo_data():
    url = f"{KOBO_BASE_URL}/api/v2/assets/{FORM_UID}/data/?format=json"
    headers = {
        "Authorization": f"Token {KOBO_API_TOKEN}"
    }

    response = requests.get(url, headers=headers)

    if response.status_code == 401:
        st.error("❌ Unauthorized. Your token may be invalid or lack access.")
        return pd.DataFrame()

    try:
        data = response.json()
    except Exception:
        st.error("❌ KoBo returned non-JSON. Possibly an error page or HTML.")
        st.text(response.text[:500])
        return pd.DataFrame()

    # Convert to DataFrame
    df = pd.DataFrame(data.get("results", []))

    # Remove unwanted metadata columns
    unwanted_columns = [
        "start", "end", "_id", "_uuid", "_validation_status",
        "_notes", "_status", "_submitted_by", "_tags", "__version__"
    ]
    df.drop(columns=[c for c in unwanted_columns if c in df.columns], inplace=True, errors='ignore')

    return df

# --- Streamlit UI ---
st.set_page_config(page_title="KoBo Data Dashboard", layout="wide")
st.title("📊 KoBoToolbox Data Viewer")

# Load Data Button
if 'kobo_df' not in st.session_state:
    st.session_state['kobo_df'] = None

if st.button("🔄 Load Data"):
    with st.spinner("Fetching data from KoBo..."):
        df = get_kobo_data()
        if not df.empty:
            st.session_state['kobo_df'] = df
            st.success(f"✅ {len(df)} records loaded.")
        else:
            st.warning("⚠️ No data found or an error occurred.")

# Display Table + Filters
if st.session_state['kobo_df'] is not None:
    df = st.session_state['kobo_df']

    # Filter UI
    filter_column = st.selectbox("🔍 Filter by Column", df.columns)
    filter_value = st.text_input("Enter filter value")

    if filter_value:
        df = df[df[filter_column].astype(str).str.contains(filter_value, case=False, na=False)]

    st.dataframe(df, use_container_width=True)

    # Download Button
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Download Filtered Data as CSV", csv, "filtered_data.csv", "text/csv")

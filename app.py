import streamlit as st
import pandas as pd
import requests

# --- KoBo API credentials and form UID ---
KOBO_API_TOKEN = "04714621fa3d605ff0a4aa5cc2df7cfa961bf256"
FORM_UID = "aJHsRZXT3XEpCoxn9Ct3qZ"

# --- Function to fetch KoBo data ---
@st.cache_data(show_spinner=False)
def get_kobo_data():
    url = f"https://kf.kobotoolbox.org/api/v2/assets/{FORM_UID}/data/"
    headers = {
        "Authorization": f"Token {KOBO_API_TOKEN}"
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    data = response.json()
    df = pd.DataFrame(data.get("results", []))

    # Drop unwanted metadata columns
    drop_cols = [
        "start", "end", "_id", "_uuid", "_validation_status",
        "_notes", "_status", "_submitted_by", "_tags", "__version__"
    ]
    df = df.drop(columns=[col for col in drop_cols if col in df.columns], errors='ignore')
    return df

# --- Streamlit App UI ---
st.set_page_config(page_title="KoBo Data Viewer", layout="wide")
st.title("📊 KoBoToolbox Data Viewer")

if 'kobo_df' not in st.session_state:
    st.session_state['kobo_df'] = None

if st.button("🔄 Load Data from KoBoToolbox"):
    try:
        with st.spinner("Fetching data..."):
            st.session_state['kobo_df'] = get_kobo_data()
        st.success("Data loaded successfully!")
    except Exception as e:
        st.error(f"Error fetching KoBo data: {e}")

# --- Display and Filter Data ---
if st.session_state['kobo_df'] is not None:
    df = st.session_state['kobo_df']
    st.write(f"✅ {len(df)} records loaded")

    if not df.empty:
        # Filter by column
        filter_col = st.selectbox("Filter by column", df.columns)
        filter_val = st.text_input("Filter value (partial match)", "")

        if filter_val:
            df = df[df[filter_col].astype(str).str.contains(filter_val, case=False, na=False)]

        st.dataframe(df, use_container_width=True)

        # Option to download filtered data
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Filtered Data as CSV", csv, "filtered_data.csv", "text/csv")

# Optional Section: GitHub CSV Loader
st.markdown("---")
st.subheader("📂 Load CSV from GitHub (Optional)")

github_url = st.text_input("Enter raw GitHub CSV URL (e.g. https://raw.githubusercontent.com/...)")
if st.button("Load CSV from GitHub"):
    if github_url:
        try:
            df_gh = pd.read_csv(github_url)
            st.success("CSV loaded successfully from GitHub!")
            st.dataframe(df_gh, use_container_width=True)
        except Exception as e:
            st.error(f"Failed to load CSV: {e}")

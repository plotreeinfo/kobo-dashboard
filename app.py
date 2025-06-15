import streamlit as st
import pandas as pd
import requests

# --- KoBo API credentials and form UID ---
KOBO_API_TOKEN = "04714621fa3d605ff0a4aa5cc2df7cfa961bf256"
FORM_UID = "aJHsRZXT3XEpCoxn9Ct3qZ"

# --- Function to fetch KoBo data safely ---
@st.cache_data(show_spinner=False)
def get_kobo_data():
    url = f"https://kf.kobotoolbox.org/api/v2/assets/{FORM_UID}/data/"
    headers = {
        "Authorization": f"Token {KOBO_API_TOKEN}"
    }

    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        st.error(f"❌ Failed to fetch data. Status code: {response.status_code}")
        st.text("🔍 Response Preview:\n" + response.text[:500])
        return pd.DataFrame()

    try:
        data = response.json()
    except ValueError:
        st.error("❌ Response content is not valid JSON.")
        st.text("🔍 Response Preview:\n" + response.text[:500])
        return pd.DataFrame()

    df = pd.DataFrame(data.get("results", []))

    # Drop unwanted metadata columns
    drop_cols = [
        "start", "end", "_id", "_uuid", "_validation_status",
        "_notes", "_status", "_submitted_by", "_tags", "__version__"
    ]
    df = df.drop(columns=[col for col in drop_cols if col in df.columns], errors='ignore')
    return df

# --- Streamlit UI Setup ---
st.set_page_config(page_title="KoBo Data Viewer", layout="wide")
st.title("📊 KoBoToolbox Data Viewer")

# --- Load Data Button ---
if 'kobo_df' not in st.session_state:
    st.session_state['kobo_df'] = None

if st.button("🔄 Load Data from KoBoToolbox"):
    try:
        with st.spinner("Fetching data..."):
            st.session_state['kobo_df'] = get_kobo_data()
        if not st.session_state['kobo_df'].empty:
            st.success("✅ Data loaded successfully!")
    except Exception as e:
        st.error(f"❌ Error fetching KoBo data: {e}")

# --- Display and Filter Data ---
if st.session_state['kobo_df'] is not None:
    df = st.session_state['kobo_df']
    if not df.empty:
        st.write(f"📥 {len(df)} records loaded")

        # Filter UI
        filter_col = st.selectbox("🔍 Filter by column", df.columns)
        filter_val = st.text_input("Enter filter text")

        if filter_val:
            df = df[df[filter_col].astype(str).str.contains(filter_val, case=False, na=False)]

        st.dataframe(df, use_container_width=True)

        # Download filtered CSV
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("⬇️ Download Filtered Data as CSV", csv, "filtered_data.csv", "text/csv")

# --- Optional GitHub CSV Section ---
st.markdown("---")
st.subheader("📂 Load CSV from GitHub")

github_url = st.text_input("Enter GitHub raw CSV URL (e.g. https://raw.githubusercontent.com/...)")

if st.button("Load CSV from GitHub"):
    if github_url:
        try:
            df_gh = pd.read_csv(github_url)
            st.success("✅ CSV loaded successfully from GitHub!")
            st.dataframe(df_gh, use_container_width=True)
        except Exception as e:
            st.error(f"❌ Failed to load CSV: {e}")

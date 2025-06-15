# app.py
import streamlit as st
import pandas as pd
import requests

# -- KoBo API credentials and form UID (provided by user) --
KOBO_USERNAME = "plotree"
KOBO_API_TOKEN = "04714621fa3d605ff0a4aa5cc2df7cfa961bf256"
FORM_UID = "aJHsRZXT3XEpCoxn9Ct3qZ"

# -- Function to fetch KoBo data and return as DataFrame --
@st.cache
def get_kobo_data():
    url = f"https://kf.kobotoolbox.org/api/v2/assets/{FORM_UID}/data/"
    # Fetch form submissions from KoBo (API v2)
    response = requests.get(url, auth=(KOBO_USERNAME, KOBO_API_TOKEN))
    response.raise_for_status()  # Raise error if request fails
    data = response.json()
    df = pd.DataFrame(data.get("results", []))
    # Drop metadata columns not needed
    drop_cols = [
        "start", "end", "_id", "_uuid", "_validation_status",
        "_notes", "_status", "_submitted_by", "_tags", "__version__"
    ]
    df = df.drop(columns=[col for col in drop_cols if col in df.columns], errors='ignore')
    return df

st.title("KoBoToolbox Data Viewer")

# -- Load KoBo data when button clicked --
if 'kobo_df' not in st.session_state:
    st.session_state['kobo_df'] = None

if st.button("Load data from KoBoToolbox"):
    try:
        st.session_state['kobo_df'] = get_kobo_data()
    except Exception as e:
        st.error(f"Error fetching KoBo data: {e}")

# Display and filter KoBo data if loaded
if st.session_state['kobo_df'] is not None:
    df_kobo = st.session_state['kobo_df']
    st.write(f"Loaded {len(df_kobo)} records from KoBoToolbox")
    if not df_kobo.empty:
        # Filter UI: select column and filter value
        col_to_filter = st.selectbox("Filter KoBo data by column:", df_kobo.columns, key="kobo_filter_col")
        filter_val = st.text_input("Enter filter text for selected column:", key="kobo_filter_val")
        if filter_val:
            # Apply case-insensitive substring filter
            df_kobo = df_kobo[df_kobo[col_to_filter].astype(str).str.contains(filter_val, case=False, na=False)]
        st.dataframe(df_kobo)

st.markdown("---")
st.subheader("Load Data from GitHub")

# -- Input and button to load CSV from a GitHub raw URL --
if 'github_df' not in st.session_state:
    st.session_state['github_df'] = None

github_url = st.text_input("Enter raw GitHub CSV URL (https://raw.githubusercontent.com/...)", key="github_url")
if st.button("Load data from GitHub"):
    if github_url:
        try:
            df_github = pd.read_csv(github_url)
            # Drop same metadata columns if present
            drop_cols = [
                "start", "end", "_id", "_uuid", "_validation_status",
                "_notes", "_status", "_submitted_by", "_tags", "__version__"
            ]
            df_github = df_github.drop(columns=[col for col in drop_cols if col in df_github.columns], errors='ignore')
            st.session_state['github_df'] = df_github
        except Exception as e:
            st.error(f"Error loading GitHub CSV: {e}")
    else:
        st.error("Please enter a valid GitHub raw CSV URL.")

# Display and filter GitHub data if loaded
if st.session_state['github_df'] is not None:
    df_github = st.session_state['github_df']
    st.write(f"Loaded {len(df_github)} records from GitHub CSV")
    if not df_github.empty:
        col_to_filter_g = st.selectbox("Filter GitHub data by column:", df_github.columns, key="gh_filter_col")
        filter_val_g = st.text_input("Enter filter text for selected column:", key="gh_filter_val")
        if filter_val_g:
            df_github = df_github[df_github[col_to_filter_g].astype(str).str.contains(filter_val_g, case=False, na=False)]
        st.dataframe(df_github)

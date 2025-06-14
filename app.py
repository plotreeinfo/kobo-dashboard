import streamlit as st
import requests
import pandas as pd
from datetime import datetime
from io import BytesIO

# ===============================
# 🔐 Kobo Credentials
# ===============================
KOBO_USERNAME = "plotree"
KOBO_API_TOKEN = "04714621fa3d605ff0a4aa5cc2df7cfa961bf256"
FORM_UID = "aJHsRZXT3XEpCoxn9Ct3qZ"
KOBO_URL = "https://kf.kobotoolbox.org"

# ===============================
# 🌐 Streamlit Page Config
# ===============================
st.set_page_config(
    page_title="Kobo Data Viewer",
    layout="wide",
    page_icon="📋"
)

# ===============================
# 🎨 Custom CSS
# ===============================
st.markdown("""
<style>
    .stDataFrame {
        font-family: Arial, sans-serif;
    }
    .stDownloadButton button {
        background-color: #f63366;
        color: white;
    }
    a {
        color: #f63366;
        text-decoration: none;
    }
    a:hover {
        text-decoration: underline;
    }
</style>
""", unsafe_allow_html=True)

# ===============================
# 📦 Fetch Kobo Data
# ===============================
def fetch_kobo_data():
    try:
        endpoint = f"/api/v2/assets/{FORM_UID}/data/"
        response = requests.get(
            KOBO_URL + endpoint,
            headers={
                "Authorization": f"Token {KOBO_API_TOKEN}",
                "Accept": "application/json"
            },
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        submissions = data.get('results', [])

        # Process attachments
        for sub in submissions:
            if '_attachments' in sub:
                for att in sub['_attachments']:
                    att['download_link'] = (
                        f"{KOBO_URL}/media/original?media_file={att['filename']}"
                    )
        return submissions
    except Exception as e:
        st.error(f"Failed to fetch data: {str(e)}")
        return None

# ✅ Cache to avoid reloading
def fetch_kobo_data_cached():
    return fetch_kobo_data()
fetch_kobo_data_cached = st.cache_data(ttl=3600)(fetch_kobo_data_cached)

# ===============================
# 🔄 Convert Submissions to DataFrame
# ===============================
def create_dataframe(submissions):
    if not submissions:
        return pd.DataFrame()

    table_data = []
    for sub in submissions:
        row = {}
        for key, value in sub.items():
            if key == "_attachments":
                # Create Markdown download links
                attachments = []
                for att in value:
                    link = f"[{att['filename']}]({att['download_link']})"
                    attachments.append(link)
                row["Attachments"] = "  \n".join(attachments)
            else:
                row[key] = str(value) if isinstance(value, (dict, list)) else value
        table_data.append(row)

    df = pd.DataFrame(table_data)

    # Convert submission date if available
    if "_submission_time" in df.columns:
        df["_submission_time"] = pd.to_datetime(df["_submission_time"], errors="coerce")
    
    return df

# ===============================
# 📊 Display Table
# ===============================
def display_table(df):
    st.dataframe(
        df,
        height=600,
        use_container_width=True
    )

# ===============================
# 💾 Convert to Excel
# ===============================
def get_excel_bytes(df):
    try:
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='KoboData')
        return output.getvalue()
    except Exception as e:
        st.error(f"Failed to create Excel file: {str(e)}")
        return None

# ===============================
# 🚀 Main App
# ===============================
def main():
    st.title("📋 Kobo Toolbox Data Viewer")

    with st.spinner("🔄 Loading data from Kobo Toolbox..."):
        submissions = fetch_kobo_data_cached()

    if submissions is None:
        st.error("❌ Data loading failed. Please check your connection and credentials.")
        return

    df = create_dataframe(submissions)

    if df.empty:
        st.warning("⚠️ No submissions found in this form.")
        return

    display_table(df)

    # Export section
    col1, col2 = st.columns(2)

    with col1:
        st.download_button(
            "⬇️ Download as CSV",
            df.to_csv(index=False),
            "kobo_data.csv",
            "text/csv"
        )

    with col2:
        excel_bytes = get_excel_bytes(df)
        if excel_bytes:
            st.download_button(
                "⬇️ Download as Excel",
                excel_bytes,
                "kobo_data.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

# ===============================
# ▶️ Run App
# ===============================
if __name__ == "__main__":
    main()

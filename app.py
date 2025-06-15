# app.py - Minimal Kobo Data Viewer
import streamlit as st
import pandas as pd

st.title("Kobo Data Viewer (Simplest Version)")

# Option 1: Direct file upload
uploaded_file = st.file_uploader("Upload your Kobo export (CSV only)", type=["csv"])

if uploaded_file:
    try:
        df = pd.read_csv(uploaded_file)
        
        # Basic filtering (adjust as needed)
        cols_to_remove = ["start", "end", "_id", "_uuid", "__version__"]
        df = df.drop(columns=[col for col in cols_to_remove if col in df.columns])
        
        st.success(f"✅ Loaded {len(df)} records")
        st.dataframe(df)
        
        # Show download button
        st.download_button(
            label="Download Cleaned Data",
            data=df.to_csv(index=False),
            file_name="cleaned_kobo_data.csv"
        )
        
    except Exception as e:
        st.error(f"Error: {str(e)}")

# Option 2: GitHub fallback
st.markdown("---")
st.write("Alternatively, load from GitHub:")
github_url = st.text_input("Enter GitHub RAW CSV URL:", 
                          "https://raw.githubusercontent.com/username/repo/main/data.csv")

if st.button("Load from GitHub"):
    try:
        df = pd.read_csv(github_url)
        st.success(f"✅ Loaded {len(df)} records from GitHub")
        st.dataframe(df.head())
    except:
        st.error("Failed to load from GitHub URL")

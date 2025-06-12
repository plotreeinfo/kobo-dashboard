import streamlit as st
import pandas as pd
from io import BytesIO

# ⛳️ Streamlit UI Setup
st.set_page_config(page_title="Kobo Dashboard", layout="wide")
st.title("KoboToolbox Dashboard")
st.subheader("📥 Download Data")

# 📤 Upload file
uploaded_file = st.file_uploader("Upload KoboToolbox Export (CSV or Excel)", type=["csv", "xlsx"])

if uploaded_file:
    # 📚 Read file
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    st.success("✅ File uploaded successfully!")

    # 🧹 Step 1: Remove Kobo metadata columns
    metadata_cols = [col for col in df.columns if col.startswith("_") or "meta" in col.lower()]
    df_cleaned = df.drop(columns=metadata_cols, errors="ignore")

    # 🧾 Step 2: Reorder columns (optional)
    desired_order = [col for col in df_cleaned.columns if "name" in col.lower()] + \
                    [col for col in df_cleaned.columns if col not in metadata_cols]
    df_cleaned = df_cleaned[desired_order]

    # 🖼 Step 3: Fix image URLs if they exist
    for

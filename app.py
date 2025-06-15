# app.py - Ultra-minimal version (no pandas)
import streamlit as st
import csv
from io import StringIO

st.title("Kobo CSV Viewer (No Dependencies)")

uploaded_file = st.file_uploader("Upload your Kobo CSV", type=["csv"])

if uploaded_file:
    try:
        # Read CSV without pandas
        content = uploaded_file.read().decode('utf-8')
        csv_reader = csv.DictReader(StringIO(content))
        
        # Get first 10 rows to display
        rows = list(csv_reader)
        st.success(f"✅ Loaded {len(rows)} records")
        
        # Simple display
        st.write("First 10 rows:")
        for i, row in enumerate(rows[:10]):
            st.json(row)
            if i >= 9:
                break
                
    except Exception as e:
        st.error(f"Error: {str(e)}")

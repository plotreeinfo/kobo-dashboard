import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from datetime import datetime

# ==============================================
# CONFIGURATION
# ==============================================

# Remove Streamlit menu and footer
st.set_page_config(layout="wide")
hide_streamlit_style = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# KoboToolbox API credentials
KOBO_API_TOKEN = "04714621fa3d605ff0a4aa5cc2df7cfa961bf256"  # Your actual token
FORM_UID = "aJHsRZXT3XEpCoxn9Ct3qZ"  # Your form ID
BASE_URL = "https://kf.kobotoolbox.org"

# API endpoints
API_URL = f"{BASE_URL}/api/v2/assets/{FORM_UID}/data.json"

# ==============================================
# AUTHENTICATED DATA FETCHING
# ==============================================

@st.cache_data(ttl=3600)  # Cache for 1 hour
def fetch_kobo_data():
    headers = {
        "Authorization": f"Token {KOBO_API_TOKEN}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(API_URL, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json().get("results", [])
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"🚨 Data fetch error: {str(e)}")
        return pd.DataFrame()

# ==============================================
# DASHBOARD LAYOUT
# ==============================================

st.title("📊 KoboToolbox Analytics Dashboard")
df = fetch_kobo_data()

if df.empty:
    st.warning("No data available - check form submissions")
    st.stop()

# Convert date columns automatically
for col in df.columns:
    if 'date' in col.lower():
        try:
            df[col] = pd.to_datetime(df[col])
        except:
            pass

# ==============================================
# SIDEBAR FILTERS
# ==============================================

with st.sidebar:
    st.header("🔍 Filters")
    
    # Date filter (if date column exists)
    date_cols = [col for col in df.columns if 'date' in col.lower()]
    if date_cols:
        selected_date_col = st.selectbox("Select date column", date_cols)
        min_date = df[selected_date_col].min()
        max_date = df[selected_date_col].max()
        
        date_range = st.date_input(
            "Date range",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date
        )
        
        if len(date_range) == 2:
            df = df[
                (df[selected_date_col] >= pd.to_datetime(date_range[0])) &
                (df[selected_date_col] <= pd.to_datetime(date_range[1]))
            ]

    # Dynamic filters for other columns
    filter_cols = st.multiselect(
        "Select columns to filter",
        df.columns,
        default=[]
    )
    
    for col in filter_cols:
        if df[col].nunique() < 20:  # For categorical columns
            options = st.multiselect(
                f"Filter by {col}",
                df[col].unique()
            )
            if options:
                df = df[df[col].isin(options)]
        else:  # For numeric columns
            min_val, max_val = float(df[col].min()), float(df[col].max())
            val_range = st.slider(
                f"Range for {col}",
                min_val,
                max_val,
                (min_val, max_val)
            )
            df = df[(df[col] >= val_range[0]) & (df[col] <= val_range[1])]

# ==============================================
# MAIN DASHBOARD VISUALIZATIONS
# ==============================================

tab1, tab2, tab3 = st.tabs(["📈 Charts", "🔢 Data Table", "📤 Export"])

with tab1:
    st.header("Interactive Visualizations")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Pie chart for categorical data
        cat_cols = [col for col in df.columns if df[col].nunique() < 10]
        if cat_cols:
            selected_cat = st.selectbox("Select category for pie chart", cat_cols)
            fig = px.pie(df, names=selected_cat)
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Bar chart
        if cat_cols:
            selected_bar = st.selectbox("Select category for bar chart", cat_cols)
            fig = px.histogram(df, x=selected_bar)
            st.plotly_chart(fig, use_container_width=True)
    
    # Time series chart
    if date_cols:
        num_cols = df.select_dtypes(include=['number']).columns
        if len(num_cols) > 0:
            st.subheader("Time Series Analysis")
            ts_col = st.selectbox("Select date column", date_cols)
            val_col = st.selectbox("Select value column", num_cols)
            fig = px.line(df, x=ts_col, y=val_col)
            st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.header("Raw Data")
    st.dataframe(df, height=600)

with tab3:
    st.header("Export Data")
    
    export_format = st.radio(
        "Select export format",
        ["CSV", "Excel", "JSON"]
    )
    
    if st.button("Generate Download Link"):
        with st.spinner("Preparing export..."):
            # Create downloadable file
            if export_format == "CSV":
                csv = df.to_csv(index=False)
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name="kobo_data.csv",
                    mime="text/csv"
                )
            elif export_format == "Excel":
                excel = df.to_excel(index=False)
                st.download_button(
                    label="Download Excel",
                    data=excel,
                    file_name="kobo_data.xlsx",
                    mime="application/vnd.ms-excel"
                )
            else:
                json = df.to_json(indent=2)
                st.download_button(
                    label="Download JSON",
                    data=json,
                    file_name="kobo_data.json",
                    mime="application/json"
                )

# ==============================================
# DEBUGGING SECTION
# ==============================================

with st.expander("🛠 Debugging Tools"):
    st.write(f"🔑 API Token: {'*' * 20}{KOBO_API_TOKEN[-4:]}")
    st.write(f"📋 Form ID: {FORM_UID}")
    st.write(f"🌐 API URL: {API_URL}")
    
    if st.button("Test Connection"):
        try:
            headers = {"Authorization": f"Token {KOBO_API_TOKEN}"}
            response = requests.get(API_URL, headers=headers)
            st.write(f"Status Code: {response.status_code}")
            st.json(response.json()[:1]) if response.status_code == 200 else st.error("Failed to fetch data")
        except Exception as e:
            st.error(f"Error: {str(e)}")

# ==============================================
# FOOTER
# ==============================================

st.markdown("---")
st.markdown("""
<style>
.footer {
    font-size: small;
    color: gray;
    text-align: center;
}
</style>
<div class="footer">
    KoboToolbox Dashboard • Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}
</div>
""", unsafe_allow_html=True)

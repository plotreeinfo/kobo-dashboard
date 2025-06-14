import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from datetime import datetime

# ==============================================
# CONFIGURATION
# ==============================================

st.set_page_config(layout="wide")
hide_streamlit_style = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# KoboToolbox credentials (using both methods for compatibility)
KOBO_API_TOKEN = "04714621fa3d605ff0a4aa5cc2df7cfa961bf256"
FORM_UID = "aJHsRZXT3XEpCoxn9Ct3qZ"
BASE_URL = "https://kf.kobotoolbox.org"
API_URL = f"{BASE_URL}/api/v2/assets/{FORM_UID}/data.json"

# ==============================================
# AUTHENTICATION WRAPPER (DUAL METHOD)
# ==============================================

def make_authenticated_request(url):
    """Try both authentication methods with proper headers"""
    headers = {
        "Authorization": f"Token {KOBO_API_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # Try Token Auth first
    try:
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 200:
            return response
    except:
        pass
    
    # Fallback to Basic Auth if Token Auth fails
    try:
        response = requests.get(
            url,
            auth=requests.auth.HTTPBasicAuth(KOBO_API_TOKEN, ''),
            timeout=30
        )
        return response
    except Exception as e:
        st.error(f"🚨 Connection failed: {str(e)}")
        return None

# ==============================================
# DATA FETCHING WITH COMPLETE ERROR HANDLING
# ==============================================

@st.cache_data(ttl=3600)
def fetch_kobo_data():
    """Fetch data with multiple fallback methods"""
    response = make_authenticated_request(API_URL)
    
    if not response:
        st.error("Failed to connect to KoboToolbox API")
        return pd.DataFrame()
    
    if response.status_code == 401:
        st.error("""
        🔐 Authentication Failed - Possible fixes:
        1. Regenerate API token at [KoboToolbox](https://kf.kobotoolbox.org/token/)
        2. Verify form sharing permissions
        3. Check server URL is correct
        """)
        return pd.DataFrame()
    
    if response.status_code == 404:
        st.error("Form not found - verify FORM_UID is correct")
        return pd.DataFrame()
    
    try:
        data = response.json().get("results", [])
        if not data:
            st.warning("Form exists but has no submissions yet")
        return pd.DataFrame(data)
    except:
        st.error("Failed to parse API response")
        return pd.DataFrame()

# ==============================================
# MAIN DASHBOARD
# ==============================================

def main():
    st.title("📊 KoboToolbox Analytics Dashboard")
    
    # Load data
    df = fetch_kobo_data()
    
    if df.empty:
        st.stop()
    
    # Auto-detect column types
    date_cols = [col for col in df.columns if 'date' in col.lower()]
    for col in date_cols:
        try:
            df[col] = pd.to_datetime(df[col])
        except:
            pass
    
    # SIDEBAR FILTERS
    with st.sidebar:
        st.header("🔍 Filters")
        
        # Date filter
        if date_cols:
            date_col = st.selectbox("Filter by date column", date_cols)
            min_date = df[date_col].min().to_pydatetime()
            max_date = df[date_col].max().to_pydatetime()
            date_range = st.date_input("Date range", [min_date, max_date])
            
            if len(date_range) == 2:
                df = df[
                    (df[date_col] >= pd.to_datetime(date_range[0])) & 
                    (df[date_col] <= pd.to_datetime(date_range[1]))
                ]
        
        # Dynamic filters
        filter_col = st.selectbox("Filter by column", df.columns)
        if pd.api.types.is_numeric_dtype(df[filter_col]):
            min_val, max_val = float(df[filter_col].min()), float(df[filter_col].max())
            val_range = st.slider("Range", min_val, max_val, (min_val, max_val))
            df = df[df[filter_col].between(*val_range)]
        else:
            options = st.multiselect("Select values", df[filter_col].unique())
            if options:
                df = df[df[filter_col].isin(options)]
    
    # VISUALIZATIONS
    tab1, tab2 = st.tabs(["Charts", "Data"])
    
    with tab1:
        col1, col2 = st.columns(2)
        
        # Pie Chart
        with col1:
            cat_cols = [c for c in df.columns if df[c].nunique() < 10]
            if cat_cols:
                selected = st.selectbox("Pie Chart Category", cat_cols)
                fig = px.pie(df, names=selected)
                st.plotly_chart(fig, use_container_width=True)
        
        # Bar Chart
        with col2:
            if cat_cols:
                selected = st.selectbox("Bar Chart Category", cat_cols)
                fig = px.histogram(df, x=selected)
                st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        st.dataframe(df, height=600)
    
    # DEBUGGING
    with st.expander("🔧 Technical Details"):
        st.code(f"""
        API URL: {API_URL}
        Last Fetch: {datetime.now().strftime('%Y-%m-%d %H:%M')}
        Data Shape: {df.shape}
        """)

if __name__ == "__main__":
    main()

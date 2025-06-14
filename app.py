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

# KoboToolbox credentials
KOBO_API_TOKEN = "04714621fa3d605ff0a4aa5cc2df7cfa961bf256"
FORM_UID = "aJHsRZXT3XEpCoxn9Ct3qZ"
BASE_URL = "https://kf.kobotoolbox.org"
API_URL = f"{BASE_URL}/api/v2/assets/{FORM_UID}/data.json"

# ==============================================
# IMPROVED DATA FETCHING WITH ERROR HANDLING
# ==============================================

@st.cache_data(ttl=3600)
def fetch_kobo_data():
    headers = {"Authorization": f"Token {KOBO_API_TOKEN}"}
    
    try:
        response = requests.get(API_URL, headers=headers, timeout=30)
        if response.status_code == 401:
            st.error("401 Unauthorized - Please verify your API token is valid")
            return pd.DataFrame()
        
        response.raise_for_status()
        data = response.json().get("results", [])
        
        if not data:
            st.warning("No submissions found in this form")
        return pd.DataFrame(data)
        
    except Exception as e:
        st.error(f"Data fetch error: {str(e)}")
        return pd.DataFrame()

# ==============================================
# SAFE DATA PROCESSING
# ==============================================

def safe_nunique(series):
    """Handle nunique() for problematic columns"""
    try:
        return series.nunique()
    except:
        try:
            return len(series.astype(str).unique())
        except:
            return 0

def clean_data(df):
    """Ensure all columns are filterable"""
    if df.empty:
        return df
    
    # Convert date columns safely
    for col in df.columns:
        if 'date' in col.lower():
            try:
                df[col] = pd.to_datetime(df[col], errors='coerce')
            except:
                pass
    
    # Clean problematic columns
    for col in df.columns:
        try:
            pd.to_numeric(df[col], errors='raise')
        except:
            df[col] = df[col].astype(str)
    
    return df

# ==============================================
# ROBUST VISUALIZATION FUNCTIONS
# ==============================================

def create_safe_visualizations(df):
    """Generate charts with error handling"""
    if df.empty:
        st.warning("No data available for visualizations")
        return
    
    tab1, tab2 = st.tabs(["Charts", "Data"])
    
    with tab1:
        # Get safe categorical columns
        cat_cols = [col for col in df.columns 
                   if safe_nunique(df[col]) < 20 
                   and safe_nunique(df[col]) > 0]
        
        if cat_cols:
            col1, col2 = st.columns(2)
            
            with col1:
                try:
                    selected = st.selectbox("Pie Chart Category", cat_cols)
                    fig = px.pie(df, names=selected)
                    st.plotly_chart(fig, use_container_width=True)
                except Exception as e:
                    st.error(f"Couldn't create pie chart: {str(e)}")
            
            with col2:
                try:
                    selected = st.selectbox("Bar Chart Category", cat_cols)
                    fig = px.histogram(df, x=selected)
                    st.plotly_chart(fig, use_container_width=True)
                except Exception as e:
                    st.error(f"Couldn't create bar chart: {str(e)}")
        
        # Numeric visualizations
        num_cols = df.select_dtypes(include=['number']).columns
        if len(num_cols) > 0:
            st.subheader("Numeric Data")
            selected = st.selectbox("Select numeric column", num_cols)
            try:
                fig = px.histogram(df, x=selected)
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.error(f"Couldn't create histogram: {str(e)}")
    
    with tab2:
        st.dataframe(df, height=600)

# ==============================================
# MAIN APPLICATION
# ==============================================

def main():
    st.title("📊 KoboToolbox Analytics Dashboard")
    
    # Load and clean data
    df = fetch_kobo_data()
    df = clean_data(df)
    
    if df.empty:
        st.stop()
    
    # Create visualizations
    create_safe_visualizations(df)
    
    # Debug info
    with st.expander("Technical Details"):
        st.write(f"Data shape: {df.shape}")
        st.write(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

if __name__ == "__main__":
    main()

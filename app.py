import streamlit as st

# Remove Streamlit menu and GitHub icon
hide_streamlit_style = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)
import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import io
from requests.auth import HTTPBasicAuth

# --- CONFIGURE KOBO CONNECTION ---
username = "plotree"
password = "Pl@tr33@123"
form_uid = "aJHsRZXT3XEpCoxn9Ct3qZ"
api_url = f"https://kf.kobotoolbox.org/api/v2/assets/{form_uid}/data.json"

# --- FETCH DATA FROM KOBO ---
@st.cache_data(ttl=3600)
def load_data():
    response = requests.get(api_url, auth=HTTPBasicAuth(username, password))
    if response.status_code == 200:
        data = response.json().get("results", [])
        df = pd.DataFrame(data)

        # --- FILTER COLUMNS: C to BO, skip BP–BV, include BY to end ---
        cols = df.columns.tolist()
        col_c = cols[2]  # Assuming column C is 3rd
        col_bo = cols[66]  # Approx. BO is 67th
        col_by = cols[73]  # Approx. BY is 74th

        # Slice based on label positions
        part1 = cols[2:67]     # C to BO
        part2 = cols[73:]      # BY to end
        selected_cols = part1 + part2

        return df[selected_cols]
    else:
        st.error("Failed to load data from KoboToolbox.")
        return pd.DataFrame()

# --- SIDEBAR FILTERS ---
st.sidebar.title("🔍 Filters")
df = load_data()

if df.empty:
    st.stop()

# Adjust column names as per actual Kobo data
user_column = "username"
district_column = "_1_1_Name_of_the_City_"

usernames = df[user_column].dropna().unique()
districts = df[district_column].dropna().unique()

selected_user = st.sidebar.selectbox("Select Username", options=['All'] + list(usernames))
selected_district = st.sidebar.selectbox("Select District", options=['All'] + list(districts))

if selected_user != 'All':
    df = df[df[user_column] == selected_user]
if selected_district != 'All':
    df = df[df[district_column] == selected_district]

st.sidebar.markdown(f"### Total Rows: {len(df)}")

# --- MAIN DASHBOARD ---
st.title("📊 Advanced Kobo Dashboard (Live)")
st.write("Filtered Dataset:")
st.dataframe(df, use_container_width=True)


# --- STATISTICS ---
st.markdown("### 📈 Summary Statistics")
st.write(df.describe(include='all'))

# --- INTERACTIVE VISUALS ---
st.markdown("### 📊 Visualizations")
col_x = st.selectbox("Select X-axis column", df.columns)
numeric_cols = df.select_dtypes(include='number').columns
col_y = st.selectbox("Select Y-axis column (numeric)", numeric_cols if not numeric_cols.empty else [None])

chart_type = st.selectbox("Select Chart Type", ["Bar", "Pie", "Histogram"])

if chart_type == "Bar" and col_y:
    fig = px.bar(df, x=col_x, y=col_y, title="Bar Chart")
    st.plotly_chart(fig, use_container_width=True)
elif chart_type == "Pie":
    fig = px.pie(df, names=col_x, title="Pie Chart")
    st.plotly_chart(fig, use_container_width=True)
elif chart_type == "Histogram" and col_y:
    fig = px.histogram(df, x=col_y, title="Histogram")
    st.plotly_chart(fig, use_container_width=True)

st.success("✅ Dashboard loaded with live KoboToolbox data and full functionality.")
# --- DATA DOWNLOAD ---
st.markdown("### 📥 Download Data")
col1, col2 = st.columns(2)

csv = df.to_csv(index=False).encode('utf-8')
excel_io = io.BytesIO()
df.to_excel(excel_io, index=False, engine='openpyxl')
col1.download_button("Download CSV", csv, "filtered_data.csv", "text/csv")
col2.download_button("Download Excel", excel_io.getvalue(), "filtered_data.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

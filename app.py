# --- Kobo Export Trigger Function ---
def trigger_kobo_export(export_type="xls"):
    export_endpoint = f"https://kf.kobotoolbox.org/api/v2/assets/{form_uid}/exports/"
    headers = {
        'Authorization': f'Token {password}',
        'Content-Type': 'application/json'
    }
    payload = {
        "type": export_type,
        "fields_from_all_versions": "true",
        "group_sep": "/",
        "hierarchy_in_labels": "true",
        "include_media_urls": "true",
        "lang": "English"
    }
    response = requests.post(export_endpoint, headers=headers, json=payload)
    if response.status_code == 201:
        export_url = response.json().get('url', None)
        return export_url
    else:
        return None

# --- 📥 DOWNLOAD DATA SECTION ---
st.subheader("📥 Download Data")

# Prepare download dataframe
download_df = df.copy()

# Identify media columns
media_cols = [col for col in download_df.columns if any(x in col.lower() for x in ['url', 'image', 'photo'])]

def generate_excel_export(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='Data', index=False)
        if media_cols:
            df[media_cols].to_excel(writer, sheet_name='Media_URLs', index=False)
        metadata = pd.DataFrame({
            'Export Date': [datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
            'Total Records': [len(df)],
            'Data Collector': [selected_user if 'selected_user' in locals() else 'All'],
            'District': [selected_district if 'selected_district' in locals() else 'All']
        })
        metadata.to_excel(writer, sheet_name='Metadata', index=False)

        workbook = writer.book
        header_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'fg_color': '#4472C4',
            'font_color': 'white',
            'border': 1
        })
        for sheet in writer.sheets:
            worksheet = writer.sheets[sheet]
            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_format)
            worksheet.autofit()

    return output.getvalue()

# Two Columns: CSV/Excel + Kobo Export
dl_col1, dl_col2 = st.columns([2, 2])

# CSV Download
csv = download_df.to_csv(index=False).encode('utf-8')
dl_col1.download_button(
    "⬇️ Download CSV",
    csv,
    "sanitation_data.csv",
    "text/csv",
    help="Download as CSV with English headers"
)

# Excel Download
try:
    excel_data = generate_excel_export(download_df)
    dl_col1.download_button(
        "⬇️ Download Excel (XLSX)",
        excel_data,
        "sanitation_data.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        help="Download with multiple sheets including media URLs"
    )
except Exception as e:
    st.error(f"Excel generation error: {str(e)}")
    excel_io = io.BytesIO()
    download_df.to_excel(excel_io, index=False, engine='openpyxl')
    dl_col1.download_button(
        "⬇️ Download Excel (Fallback)",
        excel_io.getvalue(),
        "sanitation_data.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# Kobo Export Button
if st.button("📤 Trigger Kobo XLS Export (with Media URLs)"):
    export_link = trigger_kobo_export()
    if export_link:
        st.success("✅ Export triggered successfully!")
        st.markdown(f"🔗 [Click here to download from KoboToolbox]({export_link})")
    else:
        st.error("❌ Failed to trigger Kobo export. Check API token or form UID.")

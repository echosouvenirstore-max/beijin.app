import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import calendar
import io
import openpyxl # Explicitly include for clarity, although Pandas handles the import

# --- HELPER FUNCTION: CREATE EXCEL REPORT ---
def create_excel_report(yearly_data, monthly_data, avg_rain, wet_month, insight):
    """Generates the Excel file in memory with multiple sheets for download."""
    output = io.BytesIO()
    
    # Yearly Summary DataFrame for the Excel sheet
    yearly_summary = pd.DataFrame({
        'Year': yearly_data['Year'],
        'Total Rainfall (mm)': yearly_data['Rainfall (mm)'],
        'Status': yearly_data['Status'].str.replace(r' \(.*\)', '', regex=True) 
    })
    
    # Monthly Summary DataFrame for the Excel sheet
    monthly_summary = pd.DataFrame({
        'Month Index': monthly_data.index,
        'Month Name': [calendar.month_name[i] for i in monthly_data.index],
        'Average Rainfall (mm)': monthly_data.values
    })

    # Insights Summary (Manual construction)
    insights_df = pd.DataFrame({
        'Metric': ['7-Year Average Rainfall', 'Wettest Month', 'Main Recommendation'],
        'Value': [f"{avg_rain:.2f} mm", wet_month, insight]
    })
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        yearly_summary.to_excel(writer, sheet_name='1_Yearly_Trends', index=False)
        monthly_summary.to_excel(writer, sheet_name='2_Monthly_Seasonality', index=False)
        insights_df.to_excel(writer, sheet_name='3_Key_Insights', index=False)
        
    processed_data = output.getvalue()
    return processed_data


# --- CONFIGURATION AND DATA LOADING ---
st.set_page_config(page_title="Bejin Rainfall Report", page_icon="🌧️")

st.title("🌧️ BEJIN RAINFALL TREND ANALYSIS (2018-2024)")
st.markdown("**A Data Report for Clients and Agricultural Planning**")
st.write("---")

try:
    # IMPORTANT: Ensure this file path matches the CSV file name in your GitHub repository
    file_path = 'beijing_2018_2024_weather.csv' 
    df = pd.read_csv(file_path)
    
    # Data Cleaning and Preparation
    df.columns = df.columns.str.strip().str.lower()
    if 'precipitation_mm' in df.columns:
        df.rename(columns={'precipitation_mm': 'rainfall'}, inplace=True)
    elif 'precip' in df.columns:
         df.rename(columns={'precip': 'rainfall'}, inplace=True)

    df['date'] = pd.to_datetime(df['date'])
    df['year'] = df['date'].dt.year
    df['month'] = df['date'].dt.month

except Exception as e:
    st.error(f"ERROR: Could not load the CSV file. Please ensure 'beijing_2018_2024_weather.csv' is in your repository. Details: {e}")
    st.stop()

# --- CALCULATIONS ---
yearly_rain = df.groupby('year')['rainfall'].sum()
avg_rain = yearly_rain.mean()
anomaly = yearly_rain - avg_rain

# Average monthly rain calculated over 7 years (2018-2024)
monthly_avg = df.groupby('month')['rainfall'].sum() / (df['year'].max() - df['year'].min() + 1)
wettest_month_idx = monthly_avg.idxmax()
wettest_month_name = calendar.month_name[wettest_month_idx]

# --- 1. KEY METRICS ---
st.subheader("1. General Statistics")
col1, col2, col3 = st.columns(3)
col1.metric("Annual Average", f"{avg_rain:.1f} mm")
col2.metric("Wettest Month", wettest_month_name)
col3.metric("Peak Avg. Monthly Rain", f"{monthly_avg.max():.1f} mm")

# --- 2. YEARLY TRENDS (Data Table) ---
st.subheader("2. Yearly Trends (Deviation from Average)")

summary_data = []
insight_text = ""
for year, rain in yearly_rain.items():
    anom_val = anomaly[year]
    status = "Normal"
    if anom_val > (avg_rain * 0.15): status = "Wet (Above Average)"
    elif anom_val < -(avg_rain * 0.15): status = "Dry (Below Average)"
    
    summary_data.append({
        "Year": year,
        "Rainfall (mm)": f"{rain:.2f}",
        "Status": status
    })

# Display the data table
yearly_table_df = pd.DataFrame(summary_data)
st.table(yearly_table_df)


# --- 3. FARMER INSIGHTS ---
st.subheader("3. Agricultural Recommendations")
wet_months = monthly_avg[monthly_avg > 100].count()

if wet_months >= 5:
    insight_text = "Excellent Condition: Suitable for long-cycle crops like Rice, as the rainy season is extended."
    st.success(f"✅ **Favorable Status:** {insight_text}")
elif wet_months >= 3:
    insight_text = "Moderate Condition: Suitable for fast-growing crops like Maize and Beans (Short cycle) due to average rainfall duration."
    st.warning(f"⚠️ **Moderate Status:** {insight_text}")
else:
    insight_text = "CAUTION: Dry area. High drought risk requires planting drought-resistant crops (Cassava, Sorghum)."
    st.error(f"🛑 **Dry Status:** {insight_text}")

# --- 4. VISUALIZATIONS ---
st.subheader("4. Visualizations")

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 10))
plt.subplots_adjust(hspace=0.4)

# Chart 1: Anomaly
colors = ['#1f77b4' if x >= 0 else '#d62728' for x in anomaly]
ax1.bar(yearly_rain.index, anomaly, color=colors, alpha=0.8)
ax1.axhline(0, color='black', linewidth=1)
ax1.set_title('Yearly Rainfall Anomaly vs. 7-Year Average', fontsize=12)
ax1.set_ylabel('Deviation (mm)')
ax1.grid(axis='y', linestyle='--', alpha=0.5)

# Chart 2: Seasonality
ax2.plot(monthly_avg.index, monthly_avg, marker='o', color='green')
ax2.fill_between(monthly_avg.index, monthly_avg, color='green', alpha=0.1)
ax2.set_xticks(range(1, 13))
ax2.set_xticklabels([calendar.month_abbr[i] for i in range(1, 13)])
ax2.set_title('Average Monthly Rainfall (Seasonality)', fontsize=12)
ax2.set_ylabel('Precipitation (mm)')
ax2.grid(True, linestyle='--', alpha=0.5)

st.pyplot(fig)

# --- 5. DOWNLOAD BUTTON (REAL EXCEL) ---
st.write("---")

# Generate the excel file content 
excel_data = create_excel_report(
    yearly_table_df, 
    monthly_avg, 
    avg_rain, 
    wettest_month_name, 
    insight_text
)

st.download_button(
    label="📥 Download Full Report (.xlsx)",
    data=excel_data,
    file_name="bejin_rainfall_report.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
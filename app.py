import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium

st.set_page_config(page_title="MA Resilience Dashboard", page_icon="⚡", layout="wide")
st.title("⚡ MA Resilience & Strategy Dashboard")

@st.cache_data
def load_and_clean_data():
    # Load Master Pipeline
    df = pd.read_csv("master_pipeline.csv")
    
    # Map long Salesforce column names (A-N)
    rename_map = {
        'Project: Service Contract: Service Contract Event: Job Code': 'Job Code',
        'Line Item Price to Customer': 'TU_Cost',
        'SOW Proposal Summary: Project: Service Contract: Status': 'Status',
        'Project: Service Contract: Service Contract Event: PTO Recorded Date': 'PTO Date',
        'Created Date': 'Created Date',
        'Address': 'Full_Address',
        'City': 'City',
        'BrightBox': 'Battery'
    }
    df = df.rename(columns=rename_map)
    
    # Deduplication (Keep only first unique Job Code)
    df = df.drop_duplicates(subset=['Job Code'], keep='first')
    
    # Financials & Dates
    df['TU_Cost'] = pd.to_numeric(df['TU_Cost'].astype(str).str.replace(r'[\$,]', '', regex=True), errors='coerce').fillna(0)
    df['Created Date'] = pd.to_datetime(df['Created Date'], errors='coerce')
    df['PTO Date'] = pd.to_datetime(df['PTO Date'], errors='coerce')
    df['Year'] = df['Created Date'].dt.year.fillna(0).astype(int)
    
    # Cycle Time (Created to PTO)
    df['Cycle Time'] = (df['PTO Date'] - df['Created Date']).dt.days
    
    # Categorize Status
    def categorize_status(s):
        s = str(s).lower()
        if 'cancelled' in s: return 'Cancelled'
        if 'pto' in s or 'complete' in s: return 'Complete'
        return 'Active'
    df['Status_Clean'] = df['Status'].apply(categorize_status)
    
    # Battery Flag
    df['Battery'] = df['Battery'].astype(str).str.upper().isin(['TRUE', 'YES', '1'])
    
    return df

df = load_and_clean_data()

# --- SIDEBAR ---
st.sidebar.header("Filters")
status_filter = st.sidebar.multiselect("Project Status", ["Active", "Complete", "Cancelled"], default=["Active", "Complete"])
battery_filter = st.sidebar.radio("Battery Included", ["All", "Yes", "No"])
year_filter = st.sidebar.selectbox("Select Year", ["All"] + sorted(df['Year'].unique().tolist(), reverse=True))

data = df.copy()
data = data[data['Status_Clean'].isin(status_filter)]
if battery_filter == "Yes": data = data[data['Battery'] == True]
if battery_filter == "No": data = data[data['Battery'] == False]
if year_filter != "All": data = data[data['Year'] == year_filter]

# --- KPI METRICS ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Exposure", f"${data['TU_Cost'].sum():,.2f}")
col2.metric("Project Count", len(data))
col3.metric("Avg Cycle Time", f"{data['Cycle Time'].mean():.0f} Days" if not data['Cycle Time'].isna().all() else "N/A")
col4.metric("Battery Projects", len(data[data['Battery'] == True]))

st.divider()

# --- MAP ENGINE ---
st.subheader("Interactive Saturation Map")
m = folium.Map(location=[42.25, -71.80], zoom_start=8, tiles="CartoDB dark_matter")

# Fallback Coords
ma_coords = {"Fitchburg": (42.583, -71.802), "Springfield": (42.101, -72.589), "Brockton": (42.083, -71.018), 
             "Ludlow": (42.160, -72.474), "Methuen": (42.726, -71.190), "Lee": (42.304, -73.249), "Boston": (42.360, -71.058)}

if not data.empty:
    for _, row in data.iterrows():
        coords = ma_coords.get(row.get('City'), (42.25, -71.80))
        color = "white" if row['Status_Clean'] == 'Active' else ("blue" if row['Status_Clean'] == 'Complete' else "red")
        
        tooltip_html = (
            f"<b>Job Code:</b> {row['Job Code']}<br>"
            f"<b>Status:</b> {row['Status_Clean']}<br>"
            f"<b>Battery:</b> {'Yes' if row['Battery'] else 'No'}<br>"
            f"<b>Exposure:</b> ${row['TU_Cost']:,.0f}<br>"
            f"<b>Address:</b> {str(row['Full_Address'])[:30]}..."
        )
        
        folium.CircleMarker(
            coords, radius=6, color=color, fill=True, fill_opacity=0.8,
            tooltip=folium.Tooltip(tooltip_html)
        ).add_to(m)

st_folium(m, width=1000, height=500)

# --- TRENDS ---
st.subheader("Financial Volume by Year")
trend = data.groupby('Year')['TU_Cost'].sum()
st.bar_chart(trend)

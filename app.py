import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium

st.set_page_config(page_title="MA Grid Intelligence", page_icon="⚡", layout="wide")
st.title("⚡ MA Resilience & Strategy Dashboard")

@st.cache_data
def load_and_clean_data():
    df = pd.read_csv("master_pipeline.csv")
    rename_map = {
        'Project: Service Contract: Service Contract Event: Job Code': 'Job Code',
        'Line Item Price to Customer': 'TU_Cost',
        'SOW Proposal Summary: Project: Service Contract: Status': 'Status',
        'Project: Service Contract: Service Contract Event: PTO Recorded Date': 'PTO Date',
        'Created Date': 'Created Date',
        'City': 'City',
        'BrightBox': 'Battery'
    }
    df = df.rename(columns=rename_map)
    df = df.drop_duplicates(subset=['Job Code'], keep='first')
    
    # Financials & Dates
    df['TU_Cost'] = pd.to_numeric(df['TU_Cost'].astype(str).str.replace(r'[\$,]', '', regex=True), errors='coerce').fillna(0)
    df['Created Date'] = pd.to_datetime(df['Created Date'], errors='coerce')
    df['PTO Date'] = pd.to_datetime(df['PTO Date'], errors='coerce')
    df['Year'] = df['Created Date'].dt.year.fillna(0).astype(int)
    df['Cycle Time'] = (df['PTO Date'] - df['Created Date']).dt.days
    
    # Status Mapping
    def categorize_status(s):
        s = str(s).lower()
        if 'cancelled' in s: return 'Cancelled'
        if 'pto' in s or 'complete' in s: return 'Complete'
        return 'Active'
    df['Status_Clean'] = df['Status'].apply(categorize_status)
    df['Battery'] = df['Battery'].astype(str).str.upper().isin(['TRUE', 'YES', '1'])
    return df

df = load_and_clean_data()

# --- SIDEBAR: CLEAN & PROFESSIONAL ---
st.sidebar.header("🔍 Universal Pipeline Search")
search = st.sidebar.text_input("Search Job, City, or Zip:", placeholder="e.g., 221R-057, Boston, 02108")
st.sidebar.divider()

st.sidebar.header("📊 Market Analytics Filters")
status_filter = st.sidebar.multiselect("Project Status", ["Active", "Complete", "Cancelled"], default=["Active", "Complete"])
battery_filter = st.sidebar.radio("Battery Included", ["All", "Yes", "No"], horizontal=True)
year_filter = st.sidebar.selectbox("Year", ["All"] + sorted(df['Year'].unique().tolist(), reverse=True))

data = df.copy()
if search:
    data = data[data['Job Code'].str.contains(search, case=False, na=False) | 
                data['City'].str.contains(search, case=False, na=False)]
data = data[data['Status_Clean'].isin(status_filter)]
if battery_filter == "Yes": data = data[data['Battery'] == True]
if battery_filter == "No": data = data[data['Battery'] == False]
if year_filter != "All": data = data[data['Year'] == year_filter]

# --- KPI METRICS ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Exposure", f"${data['TU_Cost'].sum():,.2f}")
col2.metric("Project Count", len(data))
col3.metric("Avg Cycle Time", f"{data['Cycle Time'].mean():.0f} Days" if not data['Cycle Time'].isna().all() else "N/A")
col4.metric("Battery Included", len(data[data['Battery'] == True]))
st.divider()

# --- MAP ENGINE ---
st.subheader("Interactive Saturation Map")
m = folium.Map(location=[42.25, -71.80], zoom_start=8, tiles="CartoDB dark_matter")

# City Coords (Add more to this list as you find missing ones)
ma_coords = {"Fitchburg": (42.583, -71.802), "Springfield": (42.101, -72.589), "Brockton": (42.083, -71.018), 
             "Ludlow": (42.160, -72.474), "Methuen": (42.726, -71.190), "Lee": (42.304, -73.249), "Boston": (42.360, -71.058)}

for _, row in data.iterrows():
    # Smart Scatter: If city not found, default to a cluster point
    coords = ma_coords.get(row.get('City'), (42.25, -71.80))
    
    if row['Status_Clean'] == 'Active': color = "white"
    elif row['Status_Clean'] == 'Complete': color = "#00a8ff"
    else: color = "red"
        
    tooltip_html = f"""
    <div style='font-family:sans-serif; width: 150px;'>
        <b>{row['Job Code']}</b><hr style='margin: 5px 0;'>
        Status: {row['Status_Clean']}<br>
        Battery: {'Yes' if row['Battery'] else 'No'}<br>
        Cost: ${row['TU_Cost']:,.0f}
    </div>
    """
    folium.CircleMarker(coords, radius=6, color=color, fill=True, fill_opacity=0.8, tooltip=tooltip_html).add_to(m)

st_folium(m, width=1000, height=500)

# --- TRENDS ---
st.subheader("Financial Volume by Year")
st.bar_chart(data.groupby('Year')['TU_Cost'].sum())

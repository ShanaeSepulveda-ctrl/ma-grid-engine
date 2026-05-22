import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium

st.set_page_config(page_title="MA Grid Intelligence", page_icon="⚡", layout="wide")
st.title("⚡ MA Resilience & Strategy Dashboard")

@st.cache_data
def load_and_clean_data():
    # 1. Load Master Pipeline
    df = pd.read_csv("master_pipeline.csv")
    
    # 2. Map all columns (A-N) to internal standard variables
    rename_map = {
        'Project: Service Contract: Service Contract Event: Job Code': 'Job Code',
        'Line Item Price to Customer': 'TU_Cost',
        'SOW Proposal Summary: Project: Service Contract: Status': 'Status',
        'Project: Service Contract: Service Contract Event: PTO Recorded Date': 'PTO Date',
        'Created Date': 'Created Date',
        'City': 'City',
        'BrightBox': 'Battery',
        'Address': 'Address',
        'Line Item Cancellation Date': 'Cancel Date'
    }
    df = df.rename(columns=rename_map)
    
    # 3. Deduplication: Keeping only the first unique Job Code
    df = df.drop_duplicates(subset=['Job Code'], keep='first')
    
    # 4. Clean Financials & Dates
    df['TU_Cost'] = pd.to_numeric(df['TU_Cost'].astype(str).str.replace(r'[\$,]', '', regex=True), errors='coerce').fillna(0)
    df['Created Date'] = pd.to_datetime(df['Created Date'], errors='coerce')
    df['PTO Date'] = pd.to_datetime(df['PTO Date'], errors='coerce')
    df['Year'] = df['Created Date'].dt.year.fillna(0).astype(int)
    
    # 5. Cycle Time Calculation
    df['Cycle Time'] = (df['PTO Date'] - df['Created Date']).dt.days
    
    # 6. Status Mapping
    def categorize_status(s):
        s = str(s).lower()
        if 'cancelled' in s: return 'Cancelled'
        if 'pto' in s or 'complete' in s: return 'Complete'
        return 'Active'
    df['Status_Clean'] = df['Status'].apply(categorize_status)
    
    # 7. Battery Flag
    df['Battery'] = df['Battery'].astype(str).str.upper().isin(['TRUE', 'YES', '1'])
    
    return df

df = load_and_clean_data()

# --- SIDEBAR FILTERS ---
st.sidebar.header("Analytics Filters")
year_filter = st.sidebar.selectbox("Year", ["All"] + sorted(df['Year'].unique().tolist(), reverse=True))
status_filter = st.sidebar.multiselect("Project Status", df['Status_Clean'].unique().tolist(), default=df['Status_Clean'].unique().tolist())
battery_filter = st.sidebar.radio("Battery Included", ["All", "Yes", "No"])

# Filter Data
data = df.copy()
if year_filter != "All": data = data[data['Year'] == year_filter]
data = data[data['Status_Clean'].isin(status_filter)]
if battery_filter == "Yes": data = data[data['Battery'] == True]
if battery_filter == "No": data = data[data['Battery'] == False]

# --- KPI DASHBOARD ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Exposure", f"${data['TU_Cost'].sum():,.2f}")
col2.metric("Active Projects", len(data[data['Status_Clean'] == 'Active']))
col3.metric("Avg Cycle Time", f"{data['Cycle Time'].mean():.0f} Days" if not data['Cycle Time'].isna().all() else "N/A")
col4.metric("Battery Included", len(data[data['Battery'] == True]))
st.divider()

# --- MAP ENGINE (Safe-Plot Logic) ---
st.subheader("Interactive Saturation Map")
m = folium.Map(location=[42.25, -71.80], zoom_start=8, tiles="CartoDB dark_matter")

# City Dictionary (Add your city coordinates here)
ma_coords = {"Fitchburg": (42.583, -71.802), "Springfield": (42.101, -72.589), "Brockton": (42.083, -71.018), 
             "Ludlow": (42.160, -72.474), "Methuen": (42.726, -71.190), "Lee": (42.304, -73.249), "Boston": (42.360, -71.058)}

if not data.empty:
    for _, row in data.iterrows():
        # FALLBACK: If city not in dictionary, use default MA coords so dot is NEVER hidden
        coords = ma_coords.get(row.get('City'), (42.25, -71.80))
        
        # Color coding: White=Active, Blue=Complete, Red=Cancelled
        if row['Status_Clean'] == 'Active': color = "white"
        elif row['Status_Clean'] == 'Complete': color = "#00a8ff"
        else: color = "red"
            
        folium.CircleMarker(
            coords,
            radius=6,
            color=color,
            fill=True,
            fill_opacity=0.7,
            tooltip=f"{row['City']} | {row['Job Code']} | ${row['TU_Cost']:,.0f} | Battery: {'Yes' if row['Battery'] else 'No'}"
        ).add_to(m)

st_folium(m, width=1000, height=500)

st.subheader("Financial Performance")
trend = data.groupby('Year')['TU_Cost'].sum()
st.bar_chart(trend)

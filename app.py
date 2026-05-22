import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium

st.set_page_config(page_title="MA Grid Resilience", page_icon="⚡", layout="wide")
st.title("⚡ MA Resilience & Strategy Dashboard")

@st.cache_data
def load_data():
    # Load Master Pipeline
    df = pd.read_csv("master_pipeline.csv")
    
    # Standardize Column Names
    rename_map = {
        'Project: Service Contract: Service Contract Event: Job Code': 'Job Code',
        'Line Item Price to Customer': 'TU_Cost',
        'SOW Proposal Summary: Project: Service Contract: Status': 'Status',
        'Project: Service Contract: Service Contract Event: PTO Recorded Date': 'PTO Date',
        'Created Date': 'Created Date',
        'City': 'City'
    }
    df = df.rename(columns=rename_map)
    
    # --- DEDUPLICATION (The "Clean Sweep") ---
    # Drops exact duplicate rows first
    df = df.drop_duplicates()
    # Drops rows with duplicate Job Codes, keeping the first instance
    df = df.drop_duplicates(subset=['Job Code'], keep='first')
    
    # --- CLEANING ---
    df['TU_Cost'] = pd.to_numeric(df['TU_Cost'].astype(str).str.replace(r'[\$,]', '', regex=True), errors='coerce').fillna(0)
    df['Created Date'] = pd.to_datetime(df['Created Date'], errors='coerce')
    df['PTO Date'] = pd.to_datetime(df['PTO Date'], errors='coerce')
    df['Year'] = df['Created Date'].dt.year.fillna(0).astype(int)
    
    # Calculate Cycle Time (Days from Invoice to PTO)
    df['Cycle Time'] = (df['PTO Date'] - df['Created Date']).dt.days
    
    df['Status_Clean'] = df['Status'].apply(lambda x: 'Cancelled' if 'Cancelled' in str(x) else ('Complete' if 'Complete' in str(x) else 'Active'))
    
    return df

df = load_data()

# --- SIDEBAR ---
st.sidebar.header("Filters")
year_filter = st.sidebar.selectbox("Year", ["All"] + sorted(df['Year'].unique().tolist(), reverse=True))
status_filter = st.sidebar.multiselect("Project Status", df['Status_Clean'].unique().tolist(), default=df['Status_Clean'].unique().tolist())

# --- FILTER LOGIC ---
data = df.copy()
if year_filter != "All": data = data[data['Year'] == year_filter]
data = data[data['Status_Clean'].isin(status_filter)]

# --- METRICS ---
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Exposure", f"${data['TU_Cost'].sum():,.2f}")
c2.metric("Active Projects", len(data[data['Status_Clean']=='Active']))
c3.metric("Avg Cycle Time", f"{data['Cycle Time'].mean():.0f} Days" if not data['Cycle Time'].isna().all() else "N/A")
c4.metric("Unique Job Codes", len(data['Job Code'].unique()))

st.divider()

# --- MAP (Bulletproofed against KeyError) ---
st.subheader("Interactive Saturation Map")
m = folium.Map(location=[42.25, -71.80], zoom_start=8, tiles="CartoDB dark_matter")

# Only draw pins if data is not empty
if not data.empty:
    for _, row in data.iterrows():
        # Add basic geocoding fallback
        lat = 42.25 if pd.isna(row.get('Lat')) else row.get('Lat', 42.25)
        lon = -71.80 if pd.isna(row.get('Lon')) else row.get('Lon', -71.80)
        
        color = "white" if row['Status_Clean'] == 'Active' else ("blue" if row['Status_Clean'] == 'Complete' else "red")
        
        folium.CircleMarker(
            [lat, lon],
            radius=6,
            color=color,
            fill=True,
            tooltip=f"{row['Job Code']} | {row['Status_Clean']} | ${row['TU_Cost']:,.0f}"
        ).add_to(m)

st_folium(m, width=1000, height=500)

# --- TRENDS ---
st.subheader("Year-over-Year Performance")
trend = data.groupby('Year')['TU_Cost'].sum()
st.bar_chart(trend)

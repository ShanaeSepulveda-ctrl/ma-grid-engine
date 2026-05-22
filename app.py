import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import math

# --- CONFIG ---
st.set_page_config(page_title="MA Grid Intelligence", page_icon="📊", layout="wide")
st.title("MA Resilience & Strategy Dashboard")
st.markdown("Automated pipeline intelligence and financial risk tracking.")

# --- DATA ENGINE ---
@st.cache_data
def process_data():
    try:
        # Load the master pipeline
        df = pd.read_csv("master_pipeline.csv")
        
        # 1. Deduplication: The "Clean Sweep"
        df = df.drop_duplicates()
        
        # 2. Rename columns for clarity
        rename_map = {
            'Project: Service Contract: Service Contract Event: Job Code': 'Job Code',
            'Line Item Price to Customer': 'TU_Cost',
            'SOW Proposal Summary: Project: Service Contract: Status': 'Status',
            'City': 'City',
            'Created Date': 'Created Date',
            'Address': 'Address'
        }
        df = df.rename(columns=rename_map)
        
        # 3. Handle Financials
        df['TU_Cost'] = pd.to_numeric(df['TU_Cost'], errors='coerce').fillna(0)
        
        # 4. Handle Dates & Years
        df['Created Date'] = pd.to_datetime(df['Created Date'], errors='coerce')
        df['Year'] = df['Created Date'].dt.year.fillna(0).astype(int)
        
        # 5. Clean Status
        df['Status_Clean'] = df['Status'].apply(lambda x: 'Cancelled' if 'Cancelled' in str(x) else ('Complete' if 'Complete' in str(x) else 'Active'))
        
        # 6. Basic Geocoding Helper
        # In a production environment, this dictionary is your "ground truth"
        ma_coords = {"Fitchburg": (42.583, -71.802), "Springfield": (42.101, -72.589), "Brockton": (42.083, -71.018), 
                     "Ludlow": (42.160, -72.474), "Methuen": (42.726, -71.190), "Lee": (42.304, -73.249), "Boston": (42.360, -71.058)}
        
        df['Lat'] = df['City'].apply(lambda c: ma_coords.get(c, 42.25)[0])
        df['Lon'] = df['City'].apply(lambda c: ma_coords.get(c, -71.80)[1])
        
        return df
    except Exception as e:
        st.error(f"Data Load Error: {e}")
        return pd.DataFrame()

df = process_data()

# --- FILTERING ---
st.sidebar.header("Filters")
selected_year = st.sidebar.selectbox("Year", ["All"] + sorted(df['Year'].unique().tolist(), reverse=True))
selected_status = st.sidebar.multiselect("Status", df['Status_Clean'].unique().tolist(), default=df['Status_Clean'].unique().tolist())

data = df.copy()
if selected_year != "All": data = data[data['Year'] == selected_year]
data = data[data['Status_Clean'].isin(selected_status)]

# --- KPI METRICS ---
c1, c2, c3 = st.columns(3)
c1.metric("Total Exposure", f"${data['TU_Cost'].sum():,.2f}")
c2.metric("Project Count", len(data))
c3.metric("Avg Invoice", f"${data['TU_Cost'].mean():,.2f}")
st.divider()

# --- MAP ---
st.subheader("Interactive Saturation Map")
m = folium.Map(location=[42.25, -71.80], zoom_start=8, tiles="CartoDB dark_matter")

for _, row in data.iterrows():
    color = "white" if row['Status_Clean'] == 'Active' else ("blue" if row['Status_Clean'] == 'Complete' else "red")
    folium.CircleMarker(
        [row['Lat'], row['Lon']],
        radius=7,
        color=color,
        fill=True,
        fill_opacity=0.7,
        tooltip=f"{row['City']} | {row['Job Code']} | ${row['TU_Cost']:,.2f}"
    ).add_to(m)

st_folium(m, width=1000, height=500)

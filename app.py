import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import math

# --- DASHBOARD CONFIGURATION ---
st.set_page_config(page_title="MA Resilience & Strategy Dashboard", page_icon="📊", layout="wide")

st.title("MA Resilience & Strategy Dashboard")
st.markdown("Enterprise pipeline intelligence, capacity mapping, and financial exposure tracking.")
st.divider()

# --- THE AUTOMATED DATA ENGINE ---
@st.cache_data
def process_data():
    try:
        # Load your Master Pipeline CSV
        df = pd.read_csv("master_pipeline.csv")
        
        # Mapping columns to clean names for the dashboard
        rename_map = {
            'Project: Service Contract: Service Contract Event: Job Code': 'Job Code',
            'Line Item Price to Customer': 'TU_Cost',
            'Project: Service Contract: Service Contract Event: PTO Recorded Date': 'PTO Date',
            'Project: Service Contract: Install Date': 'Install Date',
            'SOW Proposal Summary: Project: Service Contract: Status': 'Status',
            'Project: Service Contract: Service Contract Event: CAP date approved': 'CAP Date'
        }
        df = df.rename(columns=rename_map)
        
        # Clean Dates
        df['Created Date'] = pd.to_datetime(df['Created Date'], errors='coerce')
        df['Year'] = df['Created Date'].dt.year.fillna(0).astype(int)
        
        # Clean Financials
        df['TU_Cost'] = pd.to_numeric(df['TU_Cost'], errors='coerce').fillna(0)
        
        # Clean City/Zip (Using Address string to extract info)
        df['City'] = df['City'].astype(str).str.title()
        
        # Simplified Status Categories
        df['Status_Clean'] = df['Status'].apply(lambda x: 'Cancelled' if 'Cancelled' in str(x) else ('Complete' if 'Complete' in str(x) else 'Active'))
        
        return df
    except Exception as e:
        st.error(f"Error processing data: {e}")
        return pd.DataFrame()

df = process_data()

# --- SIDEBAR FILTERS ---
st.sidebar.header("🔍 Filters")
filter_year = st.sidebar.selectbox("Year Invoiced", ["All Years"] + sorted(df['Year'].unique().tolist(), reverse=True))
filter_status = st.sidebar.multiselect("Project Status", df['Status_Clean'].unique().tolist(), default=df['Status_Clean'].unique().tolist())
filter_util = st.sidebar.multiselect("Utility Company", df['Utility Company'].unique().tolist(), default=df['Utility Company'].unique().tolist())

# Apply Filtering
data = df.copy()
if filter_year != "All Years": data = data[data['Year'] == filter_year]
data = data[data['Status_Clean'].isin(filter_status)]
data = data[data['Utility Company'].isin(filter_util)]

# --- KPI DASHBOARD ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Exposure", f"${data['TU_Cost'].sum():,.2f}")
col2.metric("Active Projects", len(data[data['Status_Clean'] == 'Active']))
col3.metric("Cancelled Value", f"${data[data['Status_Clean'] == 'Cancelled']['TU_Cost'].sum():,.2f}")
col4.metric("Avg Invoice", f"${data['TU_Cost'].mean():,.2f}")
st.divider()

# --- TREND ANALYSIS ---
st.subheader("📈 Financial Trend Analysis")
trend_data = data.groupby('Year')['TU_Cost'].sum().reset_index()
st.line_chart(trend_data.set_index('Year'))

# --- MAP ENGINE ---
st.subheader("🗺️ Geographic Saturation")
# Simple Lat/Lon simulation based on city (You can refine this with real lat/lon in your CSV)
# For the map to work, ensure 'Lat' and 'Lon' exist in your CSV or add them here:
if 'Lat' not in data.columns:
    data['Lat'] = 42.25 # Default MA Lat
    data['Lon'] = -71.80 # Default MA Lon

m = folium.Map(location=[42.25, -71.80], zoom_start=8, tiles="CartoDB dark_matter")
for _, row in data.iterrows():
    folium.CircleMarker(
        location=[row['Lat'], row['Lon']],
        radius=5,
        color="white" if row['Status_Clean'] == 'Active' else "red",
        tooltip=f"{row['City']} - ${row['TU_Cost']:,.2f}"
    ).add_to(m)

st_folium(m, width=1000)

# --- STRATEGY MATRIX ---
st.subheader("🏛️ Strategy Actions")
tab1, tab2 = st.tabs(["CX & Sales", "Design Engineering"])

with tab1:
    st.write("Focus on high-value clusters in Fitchburg/Springfield. Prepare customers for 4-8 week delays if located in saturated circuits.")

with tab2:
    st.write("Review SLD compliance for projects over 25kW. Implement PCS export limiting where necessary to avoid complex studies.")

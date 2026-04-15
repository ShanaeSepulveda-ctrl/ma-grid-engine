import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import math

# --- DASHBOARD CONFIGURATION ---
st.set_page_config(page_title="Executive Grid Engine 14.5", page_icon="🦄", layout="wide")

st.title("⚡ National Grid Resilience Engine (Executive Dashboard)")
st.markdown("Dynamic capacity mapping and financial exposure tracking powered by live CRM data.")
st.divider()

# --- THE DYNAMIC DATA INGESTION ENGINE ---
@st.cache_data
def load_and_clean_data():
    try:
        df = pd.read_csv("ma_grid_data.csv")
        
        # 1. Clean the City Column
        if 'City' not in df.columns:
            st.error("Missing 'City' column in CSV.")
            return pd.DataFrame(), []
        
        df = df.dropna(subset=['City'])
        df['City'] = df['City'].astype(str).str.title().str.strip()
        df = df[df['City'].str.lower() != 'nan'] 
        df = df[df['City'] != ''] 

        # 2. Clean the Financials
        if 'Total Cost' in df.columns:
            df['TU_Cost'] = df['Total Cost'].astype(str).replace(r'[\$,]', '', regex=True)
            df['TU_Cost'] = pd.to_numeric(df['TU_Cost'], errors='coerce').fillna(0)
        else:
            df['TU_Cost'] = 0.0

        if 'Utility Company' not in df.columns:
            df['Utility Company'] = "Unknown Utility"
            
        if 'System Size DC' in df.columns:
            df['System_Size'] = pd.to_numeric(df['System Size DC'], errors='coerce').fillna(0)
        else:
            df['System_Size'] = 0.0

        # 5. PRECISION GEOCODING: The Mega MA Coordinate Database
        ma_coords = {
            "Abington": (42.104, -70.945), "Acton": (42.485, -71.432), "Agawam": (42.069, -72.615), "Amesbury": (42.858, -70.930),
            "Amherst": (42.380, -72.523), "Andover": (42.658, -71.136), "Arlington": (42.415, -71.156), "Attleboro": (41.944, -71.283),
            "Barnstable": (41.700, -70.300), "Bellingham": (42.083, -71.475), "Belmont": (42.395, -71.178), "Beverly": (42.558, -70.880),
            "Billerica": (42.558, -71.268), "Boston": (42.360, -71.058), "Braintree": (42.207, -71.000), "Bridgewater": (41.990, -70.975),
            "Brockton": (42.083, -71.018), "Brookline": (42.331, -71.121), "Burlington": (42.504, -71.195), "Cambridge": (42.373, -71.109),
            "Canton": (42.158, -71.144), "Chelmsford": (42.599, -71.367), "Chelsea": (42.391, -71.032), "Chicopee": (42.148, -72.607),
            "Dartmouth": (41.626, -70.984), "Dedham": (42.243, -71.167), "East Hampton": (42.266, -72.673), "Easton": (42.029, -71.102),
            "Everett": (42.408, -71.053), "Fall River": (41.701, -71.155), "Falmouth": (41.551, -70.615), "Fitchburg": (42.583, -71.802),
            "Framingham": (42.279, -71.416), "Franklin": (42.083, -71.396), "Gloucester": (42.615, -70.661), "Haverhill": (42.776, -71.077),
            "Holyoke": (42.207, -72.616), "Lawrence": (42.707, -71.163), "Leominster": (42.525, -71.759), "Lexington": (42.447, -71.227),
            "Lowell": (42.633, -71.316), "Ludlow": (42.160, -72.474), "Lynn": (42.466, -70.949), "Malden": (42.425, -71.066),
            "Marlborough": (42.345, -71.552), "Medford": (42.418, -71.106), "Melrose": (42.458, -71.065), "Methuen": (42.726, -71.190),
            "Milford": (42.141, -71.516), "Milton": (42.249, -71.071), "Natick": (42.283, -71.349), "Needham": (42.280, -71.235),
            "New Bedford": (41.636, -70.934), "Newton": (42.337, -71.209), "North Adams": (42.700, -73.108), "Northampton": (42.325, -72.641),
            "Norwood": (42.194, -71.199), "Peabody": (42.527, -70.928), "Pittsfield": (42.450, -73.245), "Plymouth": (41.958, -70.667),
            "Quincy": (42.252, -71.002), "Randolph": (42.162, -71.041), "Reading": (42.525, -71.104), "Revere": (42.408, -71.011),
            "Salem": (42.519, -70.896), "Saugus": (42.463, -71.012), "Shrewsbury": (42.295, -71.712), "Somerville": (42.387, -71.099),
            "Springfield": (42.101, -72.589), "Stoughton": (42.125, -71.102), "Taunton": (41.900, -71.089), "Tewksbury": (42.610, -71.234),
            "Waltham": (42.376, -71.235), "Watertown": (42.370, -71.183), "Wellesley": (42.296, -71.292), "West Springfield": (42.107, -72.620),
            "Westfield": (42.120, -72.749), "Weymouth": (42.218, -70.940), "Winchester": (42.452, -71.137), "Woburn": (42.479, -71.152),
            "Worcester": (42.262, -71.802)
        }
        
        # If city has coords, assign them. If not, set to None.
        df['Lat'] = df['City'].apply(lambda c: ma_coords.get(c, None))
        df['Lon'] = df['City'].apply(lambda c: ma_coords.get(c, None)[1] if ma_coords.get(c) else None)
        
        # Track which cities are missing from our dictionary
        missing_cities = df[df['Lat'].isna()]['City'].unique().tolist()
        
        # Drop rows without coordinates so the map draws cleanly without clumping
        df_mapped = df.dropna(subset=['Lat', 'Lon'])
        
        return df_mapped, missing_cities

    except FileNotFoundError:
        st.error("🚨 'ma_grid_data.csv' not found!")
        return pd.DataFrame(), []

# Execute the loader
grid_data, unmapped_cities = load_and_clean_data()

# --- EXECUTIVE FINANCIAL KPI PANEL ---
if not grid_data.empty:
    total_tu_invoiced = grid_data['TU_Cost'].sum()
    avg_tu_cost = grid_data[grid_data['TU_Cost'] > 0]['TU_Cost'].mean() if not grid_data[grid_data['TU_Cost'] > 0].empty else 0
    total_projects_flagged = len(grid_data[grid_data['TU_Cost'] > 0])
    
    st.error(f"🚨 **EXECUTIVE BRIEFING: Mapped Utility Upgrade Exposure: ${total_tu_invoiced:,.2f}**")
    
    col_kpi1, col_kpi2, col_kpi3 = st.columns(3)
    col_kpi1.metric("Mapped High-Friction Projects", total_projects_flagged)
    col_kpi2.metric("Average TU Invoice", f"${avg_tu_cost:,.2f}")
    col_kpi3.metric("Highest Saturated Utility", grid_data['Utility Company'].mode()[0])
    st.divider()

# --- TARGET MARKET SELECTION ---
st.subheader("1. Location Selection & System Design")
col1, col2 = st.columns([1, 2])

available_cities = ["Statewide Overview"]
if not grid_data.empty:
    unique_cities = sorted([str(city) for city in grid_data['City'].unique()])
    available_cities += unique_cities

with col1:
    selected_city = st.selectbox("Select Target MA City", available_cities)
    target_found = selected_city != "Statewide Overview"

with col2:
    st.markdown("**Test a New System Design:**")
    c_a, c_b = st.columns(2)
    with c_a:
        existing_kw = st.number_input("Existing Solar (kW AC)", min_value=0.0, max_value=50.0, value=0.0, step=0.5)
    with c_b:
        new_kw = st.number_input("New System Capacity (kW AC)", min_value=0.0, max_value=50.0, value=10.0, step=0.5)

# --- THE DYNAMIC MAP ENGINE ---
st.divider()
st.subheader("🗺️ Live Grid Saturation Map")
st.caption("Visualizing utility infrastructure capacity based on verified pipeline data.")

start_lat, start_lon, start_zoom = 42.25, -71.80, 8
if target_found and not grid_data[grid_data['City'] == selected_city].empty:
    target_row = grid_data[grid_data['City'] == selected_city].iloc[0]
    start_lat, start_lon, start_zoom = target_row['Lat'], target_row['Lon'], 12

ma_map = folium.Map(location=[start_lat, start_lon], zoom_start=start_zoom, tiles="CartoDB dark_matter")

if not grid_data.empty:
    city_summary = grid_data.groupby('City').agg({
        'TU_Cost': 'sum',
        'Utility Company': 'first',
        'System_Size': 'mean',
        'Lat': 'first',
        'Lon': 'first'
    }).reset_index()
    
    for _, row in city_summary.iterrows():
        if row['TU_Cost'] > 10000:
            risk_color = "#ff4b4b" 
        elif row['TU_Cost'] > 0:
            risk_color = "#ffc107" 
        else:
            risk_color = "#00cc66" 
            
        folium.CircleMarker(
            location=[row['Lat'], row['Lon']],
            radius=8 if row['TU_Cost'] == 0 else 14,
            popup=f"<b>{row['City']}</b><br>Utility: {row['Utility Company']}<br>Historical TU Exposure: ${row['TU_Cost']:,.2f}",
            color=risk_color,
            fill=True,
            fill_color=risk_color,
            fill_opacity=0.7,
            weight=1
        ).add_to(ma_map)

if target_found:
    folium.Circle(location=[start_lat, start_lon], radius=3000, color="white", weight=3, dash_array='5, 5', fill=False).add_to(ma_map)

st_folium(ma_map, width=1200, height=500, returned_objects=[])

# --- ENGINE LOGIC & TIMELINE EXPOSURE ---
if target_found:
    total_kw = existing_kw + new_kw
    is_complex_review = total_kw > 25.0
    
    city_history = grid_data[grid_data['City'] == selected_city]
    historical_exposure = city_history['TU_Cost'].mean() if not city_history.empty else 0
    
    if is_complex_review or historical_exposure > 5000:
        timeline_status = "4-8 Weeks (Transformer Review)"
        risk_level = "Red"
    elif historical_exposure > 0:
        timeline_status = "2-4 Weeks (Moderate / Average)"
        risk_level = "Yellow"
    else:
        timeline_status = "1-2 Weeks (Simplified)"
        risk_level = "Green"

    st.divider()
    st.subheader("2. Capacity & Expectation Diagnostics")

    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Total Parcel AC", f"{total_kw} kW", "- Complex Review Triggered" if is_complex_review else "+ Simplified Track", delta_color="inverse")
    col_b.metric("Installation Approval Timeline", timeline_status)
    col_c.metric("Est. Sunk Cost Risk", f"${historical_exposure + 2000:,.0f}" if historical_exposure > 0 else "$2,000", "High Risk" if risk_level == "Red" else "Acceptable", delta_color="inverse")

    st.subheader("3. Interconnection Feasibility & Pathway Review")

    if risk_level == "Red":
        st.warning("⚠️ **CAPACITY WARNING:** The requested system size and location historically require an extended utility transformer review (4-8 weeks).")
    elif risk_level == "Yellow":
        st.info("🔄 **MODERATE REVIEW:** Moderate timelines expected (2-4 weeks). Proceed with standard engineering review while monitoring utility study queues.")
    else:
        st.success("✅ **CAPACITY OPEN:** System falls within Simplified thresholds. Expect rapid utility approval (1-2 weeks).")

st.divider()

# --- THE MISSING CITY DETECTOR ---
if len(unmapped_cities) > 0:
    with st.expander("⚠️ Data Audit: Unmapped Cities"):
        st.warning(f"**{len(unmapped_cities)} cities from your CSV are missing from the map database.**")
        st.write("To keep the map perfectly accurate, we hid these cities because we don't have their exact coordinates yet. To fix this, ask your Data Strategy Lead (Shanae) to add these cities to the Python dictionary:")
        st.code(", ".join(unmapped_cities))

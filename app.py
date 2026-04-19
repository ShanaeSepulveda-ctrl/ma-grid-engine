import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import math

# --- DASHBOARD CONFIGURATION ---
st.set_page_config(page_title="Grid Intelligence Dashboard", page_icon="📊", layout="wide")

st.title("National Grid Resilience & Strategy Dashboard")
st.markdown("Enterprise pipeline intelligence, capacity mapping, and financial exposure tracking.")
st.divider()

# --- SIDEBAR: DATA INGESTION & UPLOADS ---
st.sidebar.header("📂 1. CRM Data Ingestion")
st.sidebar.caption("Upload exported CRM reports to update pipeline analytics.")
file_active = st.sidebar.file_uploader("Upload 'Active TU Projects'", type="csv")
file_cancelled = st.sidebar.file_uploader("Upload 'Cancelled Projects'", type="csv")
st.sidebar.divider()

# --- THE DYNAMIC DATA INGESTION ENGINE ---
@st.cache_data
def process_data(f_active, f_cancelled):
    df_list = []
    
    # 1. Process Active Projects
    if f_active is not None:
        try:
            df_a = pd.read_csv(f_active)
            df_a['Status'] = 'Active'
            if 'Utility' in df_a.columns: df_a = df_a.rename(columns={'Utility': 'Utility Company'})
            if 'TU Invoice' in df_a.columns: df_a = df_a.rename(columns={'TU Invoice': 'TU_Cost'})
            df_list.append(df_a)
        except Exception:
            st.sidebar.error("Error reading Active CSV.")

    # 2. Process Cancelled Projects
    if f_cancelled is not None:
        try:
            df_c = pd.read_csv(f_cancelled)
            df_c['Status'] = 'Cancelled'
            if 'Jurisdiction: Jurisdiction Name' in df_c.columns:
                df_c['City'] = df_c['Jurisdiction: Jurisdiction Name'].astype(str).str.replace('MA-TOWN ', '', case=False).str.replace('MA-CITY ', '', case=False)
            if 'TU Invoice Amount:' in df_c.columns: df_c = df_c.rename(columns={'TU Invoice Amount:': 'TU_Cost'})
            df_list.append(df_c)
        except Exception:
            st.sidebar.error("Error reading Cancelled CSV.")

    if not df_list:
        try:
            df_fallback = pd.read_csv("ma_grid_data.csv")
            df_fallback['Status'] = 'Legacy Data'
            if 'Total Cost' in df_fallback.columns: df_fallback = df_fallback.rename(columns={'Total Cost': 'TU_Cost'})
            df_list.append(df_fallback)
        except FileNotFoundError:
            return pd.DataFrame(), []

    # Combine all uploaded files into one Master Ledger
    df_master = pd.concat(df_list, ignore_index=True)
    
    # --- SANITIZATION ---
    if 'City' not in df_master.columns: df_master['City'] = "Unknown"
    df_master = df_master.dropna(subset=['City'])
    df_master['City'] = df_master['City'].astype(str).str.title().str.strip()
    df_master = df_master[df_master['City'].str.lower() != 'nan'] 
    df_master = df_master[df_master['City'] != ''] 

    if 'TU_Cost' in df_master.columns:
        df_master['TU_Cost'] = df_master['TU_Cost'].astype(str).replace(r'[\$,]', '', regex=True)
        df_master['TU_Cost'] = pd.to_numeric(df_master['TU_Cost'], errors='coerce').fillna(0)
    else:
        df_master['TU_Cost'] = 0.0

    if 'Utility Company' not in df_master.columns:
        df_master['Utility Company'] = "Unknown Utility"
        
    def map_utility(u):
        u = str(u).upper()
        if 'WMECO' in u: return 'WMECO'
        if 'GRID' in u: return 'National Grid'
        if 'EVER' in u: return 'Eversource'
        if 'UNIT' in u: return 'UNITIL'
        return u.title()
    df_master['Utility Company'] = df_master['Utility Company'].apply(map_utility)

    # --- PRECISION GEOCODING MA COORDS (With all 31 new cities) ---
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
        "Worcester": (42.262, -71.802), "Dalton": (42.475, -73.166), "Whitman": (42.081, -70.940), "Millville": (42.039, -71.580),
        "Lee": (42.304, -73.249), "Hadley": (42.341, -72.588), "Southbridge": (42.075, -72.033), "Athol": (42.595, -72.226),
        "Southampton": (42.227, -72.730), "Lanesborough": (42.518, -73.228), 
        # NEWLY ADDED 31 CITIES
        "Francestown": (42.985, -71.815), "Barre": (42.421, -72.106), "Millbury": (42.191, -71.761), "Easthampton": (42.266, -72.673),
        "South Deerfield": (42.482, -72.604), "Westminster": (42.545, -71.908), "Sutton": (42.150, -71.763), "Lakeville": (41.838, -70.938),
        "Auburn": (42.193, -71.835), "Avon": (42.131, -71.042), "Rehoboth": (41.840, -71.264), "West Brookfield": (42.235, -72.140),
        "Turners Falls": (42.604, -72.555), "Ashby": (42.678, -71.819), "Norton": (41.966, -71.186), "Deerfield": (42.543, -72.605),
        "Wilbraham": (42.122, -72.434), "Feeding Hills": (42.069, -72.678), "Gardner": (42.574, -71.998), "Webster": (42.050, -71.880),
        "Hopedale": (42.128, -71.539), "Southwick": (42.055, -72.769), "Townsend": (42.668, -71.701), "Whately": (42.430, -72.617),
        "Becket": (42.332, -73.080), "Monson": (42.104, -72.316), "Hanover": (42.115, -70.826), "Charlton": (42.134, -71.970),
        "Newburyport": (42.812, -70.877), "West Bridgewater": (42.019, -71.005), "Lunenburg": (42.595, -71.722)
    }
    
    df_master['Lat'] = df_master['City'].apply(lambda c: ma_coords[c][0] if c in ma_coords else None)
    df_master['Lon'] = df_master['City'].apply(lambda c: ma_coords[c][1] if c in ma_coords else None)
    
    missing_cities = df_master[df_master['Lat'].isna()]['City'].unique().tolist()
    
    return df_master, missing_cities

# Execute loader
raw_data, unmapped_cities = process_data(file_active, file_cancelled)

# --- SIDEBAR: ANALYTICS FILTERS ---
if not raw_data.empty:
    st.sidebar.header("🔍 2. Analytics Filters")
    
    filter_status = st.sidebar.radio("Project Status", ["All", "Active", "Cancelled"])
    filter_cost = st.sidebar.selectbox("Financial Risk Threshold", [
        "All Projects", 
        "Projects > $0 (Flagged)", 
        "Projects > $10,000", 
        "Projects > $20,000"
    ])
    
    all_utils = sorted([str(u) for u in raw_data['Utility Company'].unique() if u != 'Unknown Utility'])
    filter_utility = st.sidebar.multiselect("Utility Provider", all_utils, default=all_utils)

    # Apply Filters
    grid_data = raw_data.copy()
    if filter_status != "All":
        grid_data = grid_data[grid_data['Status'] == filter_status]
        
    if filter_cost == "Projects > $0 (Flagged)":
        grid_data = grid_data[grid_data['TU_Cost'] > 0]
    elif filter_cost == "Projects > $10,000":
        grid_data = grid_data[grid_data['TU_Cost'] > 10000]
    elif filter_cost == "Projects > $20,000":
        grid_data = grid_data[grid_data['TU_Cost'] > 20000]
        
    if filter_utility:
        grid_data = grid_data[grid_data['Utility Company'].isin(filter_utility)]

else:
    grid_data = pd.DataFrame()
    st.info("👈 **Awaiting Data:** Please upload your 'Active' or 'Cancelled' CRM reports into the sidebar menu to populate the dashboard.")

# --- PROFESSIONAL FINANCIAL KPI PANEL ---
if not grid_data.empty:
    total_tu_invoiced = grid_data['TU_Cost'].sum()
    flagged_projects = grid_data[grid_data['TU_Cost'] > 0]
    avg_tu_cost = flagged_projects['TU_Cost'].mean() if not flagged_projects.empty else 0
    total_projects_flagged = len(flagged_projects)
    
    # Replaced the red siren error block with a sleek, professional header
    st.markdown(f"### 📈 Verified Pipeline Financial Exposure: **${total_tu_invoiced:,.2f}**")
    
    col_kpi1, col_kpi2, col_kpi3 = st.columns(3)
    col_kpi1.metric("High-Friction Projects", total_projects_flagged)
    col_kpi2.metric("Average Upgrade Invoice", f"${avg_tu_cost:,.2f}")
    
    highest_util = grid_data['Utility Company'].mode()[0] if not grid_data['Utility Company'].empty else "Unknown"
    col_kpi3.metric("Highest Saturated Utility", highest_util)
    st.divider()

# --- TARGET MARKET SELECTION ---
if not grid_data.empty:
    st.subheader("1. Location Selection & System Design")
    col1, col2 = st.columns([1, 2])

    available_cities = ["Statewide Overview"]
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

    # --- THE DUAL-LAYER MAP ENGINE ---
    st.divider()
    st.subheader("🗺️ Enterprise Saturation Map")
    st.caption("Active vs. Cancelled overlays based on pipeline filters. (Active = White Border | Cancelled = Dashed Border)")

    start_lat, start_lon, start_zoom = 42.25, -71.80, 8
    ma_map = folium.Map(location=[start_lat, start_lon], zoom_start=start_zoom, tiles="CartoDB dark_matter")

    map_data = grid_data.dropna(subset=['Lat', 'Lon'])
    
    if not map_data.empty:
        # We group by BOTH City and Status, allowing a city to have an Active and Cancelled marker
        city_summary = map_data.groupby(['City', 'Status']).agg({
            'TU_Cost': 'sum',
            'Utility Company': 'first',
            'Lat': 'first',
            'Lon': 'first'
        }).reset_index()
        
        # Create map layers for toggling
        fg_active = folium.FeatureGroup(name="Active Projects")
        fg_cancelled = folium.FeatureGroup(name="Cancelled Projects")
        
        for _, row in city_summary.iterrows():
            # If a city has both Active and Cancelled, we shift the Active dot slightly East so they don't hide each other
            lon_coord = row['Lon']
            if row['Status'] == 'Active':
                lon_coord += 0.005 # ~1000 ft offset
                
            if row['TU_Cost'] > 10000:
                risk_color = "#ff4b4b" 
            elif row['TU_Cost'] > 0:
                risk_color = "#ffc107" 
            else:
                risk_color = "#00cc66" 
                
            # Distinct Styling based on Status
            if row['Status'] == 'Cancelled':
                folium.CircleMarker(
                    location=[row['Lat'], lon_coord],
                    radius=10 if row['TU_Cost'] == 0 else 16,
                    popup=f"<b>{row['City']} (Cancelled)</b><br>Utility: {row['Utility Company']}<br>Sunk Exposure: ${row['TU_Cost']:,.2f}",
                    color=risk_color,
                    fill=True,
                    fill_color=risk_color,
                    fill_opacity=0.6,
                    weight=3,
                    dash_array='5, 5' # Dashed border indicates lost project
                ).add_to(fg_cancelled)
            else:
                folium.CircleMarker(
                    location=[row['Lat'], lon_coord],
                    radius=10 if row['TU_Cost'] == 0 else 16,
                    popup=f"<b>{row['City']} (Active)</b><br>Utility: {row['Utility Company']}<br>Active Exposure: ${row['TU_Cost']:,.2f}",
                    color="#ffffff", # Crisp white border for active
                    fill=True,
                    fill_color=risk_color,
                    fill_opacity=0.9,
                    weight=2
                ).add_to(fg_active)

        fg_active.add_to(ma_map)
        fg_cancelled.add_to(ma_map)
        folium.LayerControl().add_to(ma_map) # Adds the toggle menu to the map

    if target_found:
        target_row = grid_data[grid_data['City'] == selected_city].iloc[0]
        if pd.notna(target_row['Lat']):
            folium.Circle(location=[target_row['Lat'], target_row['Lon']], radius=3000, color="white", weight=3, dash_array='5, 5', fill=False).add_to(ma_map)

    st_folium(ma_map, width=1200, height=550, returned_objects=[])

    # --- EXPECTATION DIAGNOSTICS ---
    if target_found:
        total_kw = existing_kw + new_kw
        is_complex_review = total_kw > 25.0
        
        city_history = grid_data[grid_data['City'] == selected_city]
        historical_exposure = city_history['TU_Cost'].mean() if not city_history.empty else 0
        
        if is_complex_review or historical_exposure > 5000:
            timeline_status = "4-8 Weeks (Transformer Review)"
            risk_level = "Red"
        elif historical_exposure > 0:
            timeline_status = "2-4 Weeks (Moderate/Average)"
            risk_level = "Yellow"
        else:
            timeline_status = "1-2 Weeks (Simplified)"
            risk_level = "Green"

        st.divider()
        st.subheader("2. Capacity & Expectation Diagnostics")
        col_a, col_b, col_c = st.columns(3)
        col_a.metric("Total Parcel AC", f"{total_kw} kW", "- Complex Review Triggered" if is_complex_review else "+ Simplified Track", delta_color="inverse")
        col_b.metric("Expected Approval Timeline", timeline_status)
        col_c.metric("Est. Margin Risk", f"${historical_exposure + 2000:,.0f}" if historical_exposure > 0 else "$2,000", "High Risk" if risk_level == "Red" else "Acceptable", delta_color="inverse")

    st.divider()

    # --- THE AUDIT DETECTOR ---
    if len(unmapped_cities) > 0:
        with st.expander("📝 System Data Audit: Unmapped Pipeline Cities"):
            st.write(f"**{len(unmapped_cities)} cities from the CRM export require GPS coordinate assignment.**")
            st.write("These cities are actively included in the financial metrics above, but have been hidden from the visual map to preserve geographic integrity. Contact the Data Strategy Lead for dictionary updates.")
            st.code(", ".join(unmapped_cities))

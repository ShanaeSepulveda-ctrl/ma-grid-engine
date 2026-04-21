import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import math

# --- DASHBOARD CONFIGURATION ---
st.set_page_config(page_title="MA Grid Intelligence", page_icon="📊", layout="wide")

st.title("MA Resilience & Strategy Dashboard")
st.markdown("Enterprise pipeline intelligence, capacity mapping, and financial exposure tracking.")
st.divider()

# --- THE AUTOMATED MASTER INGESTION ENGINE ---
@st.cache_data
def process_data():
    df_list = []
    
    files_to_try = [
        ("active_projects.csv", "Open"),
        ("cancelled_projects.csv", "Cancelled"),
        ("master_pipeline.csv", "Unknown")
    ]
    
    for filename, default_status in files_to_try:
        try:
            df = pd.read_csv(filename)
            
            if 'Project Status:' in df.columns:
                df['Status'] = df['Project Status:'].astype(str).str.title().str.strip()
            elif 'Project Status' in df.columns:
                df['Status'] = df['Project Status'].astype(str).str.title().str.strip()
            elif 'Status' in df.columns:
                df['Status'] = df['Status'].astype(str).str.title().str.strip()
            else:
                df['Status'] = default_status
                
            if 'Jurisdiction: Jurisdiction Name' in df.columns:
                df['City'] = df['Jurisdiction: Jurisdiction Name'].astype(str).str.replace('MA-TOWN ', '', case=False).str.replace('MA-CITY ', '', case=False)
            
            if 'Line Item Price to Customer' in df.columns:
                df['TU_Cost'] = df['Line Item Price to Customer']
            elif 'TU Invoice Amount:' in df.columns:
                df['TU_Cost'] = df['TU Invoice Amount:']
            elif 'TU Invoice' in df.columns:
                df['TU_Cost'] = df['TU Invoice']
            elif 'Total Cost' in df.columns:
                df['TU_Cost'] = df['Total Cost']
            
            if 'Utility' in df.columns and 'Utility Company' not in df.columns:
                df['Utility Company'] = df['Utility']
                
            if 'Zip Code:' in df.columns:
                df['Zip Code'] = df['Zip Code:']
            elif 'Zip Code' not in df.columns:
                df['Zip Code'] = "Unknown"
                
            if 'BrightBox' in df.columns:
                df['Battery'] = df['BrightBox'].astype(str).str.upper().isin(['TRUE', 'YES', 'Y', '1'])
            else:
                df['Battery'] = False
                
            df_list.append(df)
        except FileNotFoundError:
            pass

    if not df_list:
        return pd.DataFrame(), []

    df_master = pd.concat(df_list, ignore_index=True)
    
    # --- SANITIZATION & CLEANING ---
    df_master['Job Code'] = df_master['Job Code'].astype(str).str.strip() if 'Job Code' in df_master.columns else "Unknown"
    df_master['Zip Code'] = df_master['Zip Code'].astype(str).str.extract(r'(\d{5})')[0].fillna("Unknown")

    if 'City' not in df_master.columns: df_master['City'] = "Unknown"
    df_master = df_master.dropna(subset=['City'])
    df_master['City'] = df_master['City'].astype(str).str.title().str.strip()
    df_master = df_master[df_master['City'].str.lower() != 'nan'] 
    df_master = df_master[df_master['City'] != ''] 
    
    df_master['Status'] = df_master['Status'].replace({'Nan': 'Unknown', 'None': 'Unknown'})
    if 'Battery' not in df_master.columns: df_master['Battery'] = False

    if 'TU_Cost' in df_master.columns:
        df_master['TU_Cost'] = df_master['TU_Cost'].astype(str).replace(r'[\$,]', '', regex=True)
        df_master['TU_Cost'] = pd.to_numeric(df_master['TU_Cost'], errors='coerce').fillna(0.0)
    else:
        df_master['TU_Cost'] = 0.0

    df_master['Utility Company'] = df_master['Utility Company'] if 'Utility Company' in df_master.columns else "Unknown Utility"
        
    def map_utility(u):
        u = str(u).upper()
        if 'WMECO' in u: return 'WMECO'
        if 'GRID' in u: return 'National Grid'
        if 'EVER' in u: return 'Eversource'
        if 'UNIT' in u: return 'UNITIL'
        return u.title()
    df_master['Utility Company'] = df_master['Utility Company'].apply(map_utility)

    # --- PRECISION GEOCODING (Master Database) ---
    ma_coords = {
        "Abington": (42.104, -70.945), "Acton": (42.485, -71.432), "Agawam": (42.069, -72.615), "Amesbury": (42.858, -70.930),
        "Amherst": (42.380, -72.523), "Andover": (42.658, -71.136), "Arlington": (42.415, -71.156), "Attleboro": (41.944, -71.283),
        "Barnstable": (41.700, -70.300), "Bellingham": (42.083, -71.475), "Belmont": (42.395, -71.178), "Beverly": (42.558, -70.880),
        "Billerica": (42.558, -71.268), "Boston": (42.360, -71.058), "Braintree": (42.207, -71.000), "Bridgewater": (41.990, -70.975),
        "Brockton": (42.083, -71.018), "Brookline": (42.331, -71.121), "Burlington": (42.504, -71.195), "Cambridge": (42.373, -71.109),
        "Canton": (42.158, -71.144), "Chelmsford": (42.599, -71.367), "Chelsea": (42.391, -71.032), "Chicopee": (42.148, -72.607),
        "Dartmouth": (41.626, -70.984), "Dedham": (42.243, -71.167), "Easthampton": (42.266, -72.673), "Easton": (42.029, -71.102),
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
        "Southampton": (42.227, -72.730), "Lanesborough": (42.518, -73.228), "Francestown": (42.985, -71.815), "Barre": (42.421, -72.106), 
        "Millbury": (42.191, -71.761), "South Deerfield": (42.482, -72.604), "Westminster": (42.545, -71.908), "Sutton": (42.150, -71.763), 
        "Lakeville": (41.838, -70.938), "Auburn": (42.193, -71.835), "Avon": (42.131, -71.042), "Rehoboth": (41.840, -71.264), 
        "West Brookfield": (42.235, -72.140), "Turners Falls": (42.604, -72.555), "Ashby": (42.678, -71.819), "Norton": (41.966, -71.186), 
        "Deerfield": (42.543, -72.605), "Wilbraham": (42.122, -72.434), "Feeding Hills": (42.069, -72.678), "Gardner": (42.574, -71.998), 
        "Webster": (42.050, -71.880), "Hopedale": (42.128, -71.539), "Southwick": (42.055, -72.769), "Townsend": (42.668, -71.701), 
        "Whately": (42.430, -72.617), "Becket": (42.332, -73.080), "Monson": (42.104, -72.316), "Hanover": (42.115, -70.826), 
        "Charlton": (42.134, -71.970), "Newburyport": (42.812, -70.877), "West Bridgewater": (42.019, -71.005), "Lunenburg": (42.595, -71.722),
        "Greenfield": (42.587, -72.599), "Montgomery": (42.231, -72.802), "Hinsdale": (42.441, -73.123), "Erving": (42.599, -72.417), 
        "Longmeadow": (42.049, -72.581), "West Townsend": (42.668, -71.745), "Emmaus": (40.539, -75.496), "Clinton": (42.416, -71.682), 
        "Dudley": (42.046, -71.931), "Rutland": (42.368, -71.947), "Uxbridge": (42.077, -71.630), "Rockport": (42.655, -70.620), 
        "Wrentham": (42.066, -71.328), "North Andover": (42.695, -71.133), "Upton": (42.176, -71.627), "Spencer": (42.243, -71.989), 
        "Sturbridge": (42.108, -72.080), "Leicester": (42.245, -71.905), "Oxford": (42.115, -71.864), "Whitinsville": (42.112, -71.651), 
        "Shirley": (42.539, -71.648), "Brookfield": (42.215, -72.102), "Northbridge": (42.150, -71.650), "West Newbury": (42.798, -70.992), 
        "Plainville": (42.002, -71.332), "South Easton": (42.015, -71.096), "Norwell": (42.161, -70.793), "Holbrook": (42.155, -71.008), 
        "Swansea": (41.746, -71.192), "North Dighton": (41.859, -71.121), "Dighton": (41.819, -71.121), "E Bridgewtr": (42.033, -70.959), 
        "Woonsocket": (42.002, -71.514), "Mendon": (42.102, -71.554), "Blackstone": (42.016, -71.538), "New Braintree": (42.302, -72.152), 
        "Douglas": (42.042, -71.743), "North Brookfield": (42.266, -72.082), "Foxboro": (42.065, -71.248), "Pembroke": (42.059, -70.821), 
        "Westport": (41.621, -71.066), "Scituate": (42.195, -70.726), "Rockland": (42.128, -70.916), "Winchendon": (42.684, -72.046), 
        "Boyertown": (40.332, -75.635), "Lyndeborough": (42.894, -71.758), "East Lyme": (41.353, -72.222), "Bloomfield Village": (41.826, -72.730), 
        "Meriden": (41.538, -72.807), "Maynard": (42.433, -71.455), "Otis": (42.193, -73.090), "Bedford": (42.490, -71.276), 
        "Sandown": (42.926, -71.189), "Jaffrey": (42.813, -72.022), "Rochester": (41.765, -70.925), "E Falmouth": (41.583, -70.551), 
        "Carver": (41.883, -70.763), "Hyannis": (41.652, -70.282), "Holliston": (42.203, -71.425)
    }
    
    df_master['Lat'] = df_master['City'].apply(lambda c: ma_coords[c][0] if c in ma_coords else None)
    df_master['Lon'] = df_master['City'].apply(lambda c: ma_coords[c][1] if c in ma_coords else None)
    
    missing_cities = df_master[df_master['Lat'].isna()]['City'].unique().tolist()
    
    return df_master, missing_cities

# Execute loader
raw_data, unmapped_cities = process_data()

# --- SIDEBAR: THE UNIVERSAL SMART SEARCH ---
if not raw_data.empty:
    st.sidebar.header("🔍 Universal Pipeline Search")
    universal_search = st.sidebar.text_input("Search by Job Code, City, or Zip Code:", placeholder="e.g., 221R-057, Boston, 02108")
    st.sidebar.divider()
    
    st.sidebar.header("📊 Market Analytics Filters")
    valid_statuses = [s for s in raw_data['Status'].unique() if s not in ['Unknown', 'nan']]
    available_statuses = ["All"] + sorted(valid_statuses)
    filter_status = st.sidebar.radio("Project Lifecycle Stage", available_statuses)
    filter_battery = st.sidebar.radio("System Design Type", ["All Systems", "Battery Included", "Solar Only"])
    filter_cost = st.sidebar.selectbox("Financial Risk Threshold", [
        "All Projects", 
        "Projects > $0 (Flagged)", 
        "Projects > $10,000", 
        "Projects > $20,000",
        "Projects > $30,000",
        "Projects > $40,000"
    ])
    all_utils = sorted([str(u) for u in raw_data['Utility Company'].unique() if u != 'Unknown Utility'])
    filter_utility = st.sidebar.multiselect("Utility Provider", all_utils, default=all_utils)

    # --- APPLY FILTERS ---
    grid_data = raw_data.copy()
    search_failed = False
    
    if universal_search:
        search_term = universal_search.lower().strip()
        mask = (
            grid_data['Job Code'].str.lower().str.contains(search_term, na=False) |
            grid_data['City'].str.lower().str.contains(search_term, na=False) |
            grid_data['Zip Code'].str.contains(search_term, na=False)
        )
        grid_data = grid_data[mask]
        
        if grid_data.empty:
            st.sidebar.error(f"No pipeline results found for '{universal_search}'.")
            grid_data = raw_data.copy() # Reset safely so the state view returns
            search_failed = True
    else:
        if filter_status != "All":
            grid_data = grid_data[grid_data['Status'] == filter_status]
        if filter_battery == "Battery Included":
            grid_data = grid_data[grid_data['Battery'] == True]
        elif filter_battery == "Solar Only":
            grid_data = grid_data[grid_data['Battery'] == False]
        if filter_cost == "Projects > $0 (Flagged)":
            grid_data = grid_data[grid_data['TU_Cost'] > 0]
        elif filter_cost == "Projects > $10,000":
            grid_data = grid_data[grid_data['TU_Cost'] > 10000]
        elif filter_cost == "Projects > $20,000":
            grid_data = grid_data[grid_data['TU_Cost'] > 20000]
        elif filter_cost == "Projects > $30,000":
            grid_data = grid_data[grid_data['TU_Cost'] > 30000]
        elif filter_cost == "Projects > $40,000":
            grid_data = grid_data[grid_data['TU_Cost'] > 40000]
        if filter_utility:
            grid_data = grid_data[grid_data['Utility Company'].isin(filter_utility)]

else:
    grid_data = pd.DataFrame()
    st.info("🚨 **System Note:** No pipeline data found. Please ensure your CSV files are uploaded to your GitHub repository.")

# --- PROFESSIONAL FINANCIAL KPI PANEL ---
if not grid_data.empty:
    total_tu_invoiced = grid_data['TU_Cost'].sum()
    flagged_projects = grid_data[grid_data['TU_Cost'] > 0]
    avg_tu_cost = flagged_projects['TU_Cost'].mean() if not flagged_projects.empty else 0
    total_projects_flagged = len(flagged_projects)
    
    st.markdown("### 📈 Live Pipeline Financial Overview")
    col_kpi1, col_kpi2, col_kpi3, col_kpi4 = st.columns(4)
    col_kpi1.metric("Total TU Invoice Exposure", f"${total_tu_invoiced:,.2f}")
    col_kpi2.metric("Projects with TU Exposure", total_projects_flagged)
    col_kpi3.metric("Average Upgrade Invoice", f"${avg_tu_cost:,.2f}")
    highest_util = grid_data['Utility Company'].mode()[0] if not grid_data['Utility Company'].empty else "Unknown"
    col_kpi4.metric("Utility with Highest TU Frequency", highest_util)
    st.divider()

# --- THE MULTI-LAYER MAP ENGINE ---
if not grid_data.empty:
    st.subheader("🗺️ Enterprise Saturation Map")
    st.caption("Map updates dynamically. Open = White | Complete = Sapphire Blue | Cancelled = Dashed")

    # Map Targeting Logic
    start_lat, start_lon, start_zoom = 42.25, -71.80, 8
    
    # Only super-zoom if the search was successful!
    if universal_search and not search_failed and not grid_data.empty:
        if pd.notna(grid_data.iloc[0]['Lat']):
            start_lat, start_lon, start_zoom = grid_data.iloc[0]['Lat'], grid_data.iloc[0]['Lon'], 14

    ma_map = folium.Map(location=[start_lat, start_lon], zoom_start=start_zoom, tiles="CartoDB dark_matter")

    map_data = grid_data.dropna(subset=['Lat', 'Lon'])
    
    if not map_data.empty:
        city_summary = map_data.groupby(['City', 'Zip Code', 'Status', 'Job Code']).agg({
            'TU_Cost': 'sum',
            'Utility Company': 'first',
            'Battery': 'first',
            'Lat': 'first',
            'Lon': 'first'
        }).reset_index()
        
        statuses_present = city_summary['Status'].unique()
        feature_groups = {s: folium.FeatureGroup(name=f"{s} Projects") for s in statuses_present}
        
        for _, row in city_summary.iterrows():
            offset_lat = row['Lat'] + (hash(row['Job Code']) % 100) / 10000.0
            offset_lon = row['Lon'] + (hash(row['Job Code'] + "x") % 100) / 10000.0
                
            if row['TU_Cost'] > 10000:
                risk_color = "#ff4b4b" 
            elif row['TU_Cost'] > 0:
                risk_color = "#ffc107" 
            else:
                risk_color = "#00cc66" 
                
            # Styling Logic
            if row['Status'] == 'Cancelled':
                border_color = risk_color
                weight = 3
                dash = '5, 5'
            elif row['Status'] == 'Complete':
                border_color = "#00a8ff" # Vibrant Sapphire Blue
                weight = 3
                dash = None
            else:
                border_color = "#ffffff" # Crisp White for Open
                weight = 2
                dash = None
                
            battery_badge = "<br><b>🔋 Includes Battery Storage</b>" if row['Battery'] else ""
                
            folium.CircleMarker(
                location=[offset_lat, offset_lon],
                radius=8 if row['TU_Cost'] == 0 else 12,
                popup=f"<b>{row['City']}, MA {row['Zip Code']} ({row['Status']})</b><br>Job: {row['Job Code']}<br>Utility: {row['Utility Company']}<br>TU Invoice Amount: ${row['TU_Cost']:,.2f}{battery_badge}",
                color=border_color,
                fill=True,
                fill_color=risk_color,
                fill_opacity=0.8,
                weight=weight,
                dash_array=dash
            ).add_to(feature_groups[row['Status']])

        for fg in feature_groups.values():
            fg.add_to(ma_map)
        folium.LayerControl().add_to(ma_map) 

    # --- THE RADAR LOCK RETICLE ---
    # Drops a distinct red pin *only* if the search didn't fail
    if universal_search and not search_failed and not map_data.empty:
        target_row = map_data.iloc[0]
        folium.Marker(
            location=[target_row['Lat'], target_row['Lon']],
            icon=folium.Icon(color='red', icon='info-sign'),
            tooltip="Targeted Search Area"
        ).add_to(ma_map)
        
        folium.Circle(
            location=[target_row['Lat'], target_row['Lon']],
            radius=1500,
            color="#ff4b4b",
            weight=3,
            fill=True,
            fill_opacity=0.1
        ).add_to(ma_map)

    st_folium(ma_map, width=1200, height=550, returned_objects=[])

    # --- STRATEGY COMMAND CENTER ---
    st.divider()
    st.subheader("2. System Design & Capacity Diagnostics")
    
    col_a, col_b = st.columns([1, 2])
    with col_a:
        st.markdown("**Test Proposed AC Design:**")
        existing_kw = st.number_input("Existing Solar (kW AC)", min_value=0.0, max_value=50.0, value=0.0, step=0.5)
        new_kw = st.number_input("New System Capacity (kW AC)", min_value=0.0, max_value=50.0, value=10.0, step=0.5)
    
    total_kw = existing_kw + new_kw
    is_complex_review = total_kw > 25.0
    
    historical_exposure = grid_data['TU_Cost'].mean() if not grid_data.empty else 0
    
    if is_complex_review or historical_exposure > 5000:
        timeline_status = "4-8 Weeks (Complex Review)"
        risk_level = "Red"
    elif historical_exposure > 0:
        timeline_status = "2-4 Weeks (Moderate)"
        risk_level = "Yellow"
    else:
        timeline_status = "1-2 Weeks (Simplified)"
        risk_level = "Green"

    with col_b:
        c1, c2 = st.columns(2)
        c1.metric("Expected Approval Timeline", timeline_status)
        c2.metric("Est. Sunk Margin Risk", f"${historical_exposure + 2000:,.0f}" if historical_exposure > 0 else "$2,000", "High Risk" if risk_level == "Red" else "Acceptable", delta_color="inverse")

    with st.expander("📊 Defensible Data Methodology (Analyst Notes)"):
        st.markdown("""
        **How is Est. Sunk Margin Risk Calculated?**
        * **Baseline Sunk OpEx:** `$2,000` (Estimated standard Site Survey + Design Labor + CX Admin execution cost).
        * **Transformer Upgrade (TU) Exposure:** Derived directly from the historical pipeline data average for the filtered geographic location.
        * **Formula:** `Historical Local TU Average + Baseline Sunk OpEx = Est. Sunk Margin Risk`.
        """)

    st.divider()
    st.subheader("3. Cross-Functional Strategy Matrix")
    
    tab_cx, tab_design, tab_policy = st.tabs(["🤝 Sales & CX Actions", "📐 Design Engineering Actions", "🏛️ Policy & Exec Actions"])
    
    with tab_cx:
        if risk_level == "Red":
            st.error("**High Friction Zone:** Reps must set timeline expectations of 4-8+ weeks for utility review. Prepare the customer for potential upgrade fees upfront to prevent late-stage cancellations.")
        elif risk_level == "Yellow":
            st.warning("**Moderate Friction Zone:** Standard timelines may be delayed. Monitor Interconnection queues closely and proactively communicate 2-4 week review periods.")
        else:
            st.success("**Clearance Zone:** Green light for standard sales pitch. Expect rapid 1-2 week utility approvals.")
            
    with tab_design:
        if is_complex_review:
            st.error(f"**System Modification Recommended:** Parcel AC ({total_kw}kW) exceeds the 25kW Simplified Track limit. Evaluate Power Control Systems (PCS) to hard-cap export below 25kW, or configure ESS for non-export to bypass Complex Study queues.")
        elif risk_level == "Red":
            st.error(f"**Grid Saturation Alert:** While the system size ({total_kw}kW) is under the 25kW limit, the targeted area has a history of highly saturated transformers. Design conservatively. The utility may force secondary transformer upgrades regardless of system size.")
        elif risk_level == "Yellow":
            st.warning(f"**Moderate Congestion:** Standard AC sizing is acceptable, but ensure perfect SLD compliance to avoid administrative kickbacks in group study queues.")
        else:
            st.success(f"**Standard Design:** System size ({total_kw}kW) falls within Simplified thresholds and local grid capacity is historically open.")
            
    with tab_policy:
        if risk_level == "Red" or risk_level == "Yellow":
            util_name = grid_data['Utility Company'].mode()[0] if not grid_data.empty else "Utility"
            st.info(f"**Lobbying Target:** The targeted pipeline is demonstrating repeated congestion with {util_name}. Log this data for the next DPU/Policy meeting to negotiate grid upgrade fee socialization.")
        else:
            st.write("No immediate policy escalation required for this market view.")

    st.divider()

    if len(unmapped_cities) > 0:
        with st.expander("📝 System Data Audit: Unmapped Pipeline Cities"):
            st.write(f"**{len(unmapped_cities)} cities from the CRM export require GPS coordinate assignment.**")
            st.write("These cities are actively included in the financial metrics above, but have been hidden from the visual map to preserve geographic integrity. Contact the Data Strategy Lead for dictionary updates.")
            st.code(", ".join(unmapped_cities))

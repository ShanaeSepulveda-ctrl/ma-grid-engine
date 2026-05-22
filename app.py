import streamlit as st
import pandas as pd
import numpy as np
import folium
import hashlib
from streamlit_folium import st_folium

# --- PAGE CONFIG ---
st.set_page_config(page_title="MA Grid Intelligence", page_icon="⚡", layout="wide")
st.title("⚡ MA Resilience & Strategy Dashboard")

# --- DATA ENGINE ---
@st.cache_data
def load_and_clean_data():
    df = pd.read_csv("master_pipeline.csv")
    rename_map = {
        'Project: Service Contract: Service Contract Event: Job Code': 'Job Code',
        'Line Item Price to Customer': 'TU_Cost',
        'SOW Proposal Summary: Project: Service Contract: Status': 'Status',
        'Project: Service Contract: Service Contract Event: CAP date approved': 'CAP Date',
        'Project: Service Contract: Service Contract Event: PTO Recorded Date': 'PTO Date',
        'Created Date': 'Created Date', 
        'City': 'City',
        'Utility Company': 'Utility',
        'BrightBox': 'Battery'
    }
    df = df.rename(columns=rename_map)
    df = df.drop_duplicates(subset=['Job Code'], keep='first')
    
    df['TU_Cost'] = pd.to_numeric(df['TU_Cost'].astype(str).str.replace(r'[\$,]', '', regex=True), errors='coerce').fillna(0)
    df['Created Date'] = pd.to_datetime(df['Created Date'], errors='coerce')
    df['CAP Date'] = pd.to_datetime(df['CAP Date'], errors='coerce')
    df['PTO Date'] = pd.to_datetime(df['PTO Date'], errors='coerce')
    
    df['Year'] = df['Created Date'].apply(lambda x: x.year if pd.notnull(x) else 0).astype(int)
    
    df['Cycle Time'] = (df['PTO Date'] - df['CAP Date']).dt.days
    df['Cycle Time'] = df['Cycle Time'].apply(lambda x: x if pd.notnull(x) and x >= 0 else np.nan)
    
    def categorize_status(s):
        s = str(s).lower()
        if 'cancelled' in s: return 'Cancelled'
        if 'pto' in s or 'complete' in s: return 'Complete'
        return 'Active'
    df['Status_Clean'] = df['Status'].apply(categorize_status)
    df['Battery'] = df['Battery'].astype(str).str.upper().isin(['TRUE', 'YES', '1'])
    df['City'] = df['City'].astype(str).str.title().str.strip()
    
    df['Utility'] = df['Utility'].astype(str).str.upper()
    df['Utility'] = df['Utility'].replace({'NATIONAL GRID': 'National Grid', 'EVERSOURCE': 'Eversource', 'WMECO': 'WMECO', 'UNITIL': 'UNITIL'})
    
    return df

df = load_and_clean_data()

# --- SIDEBAR ---
st.sidebar.header("🔍 Universal Pipeline Search")
search = st.sidebar.text_input("Search (Job, City):", placeholder="e.g., Boston")
st.sidebar.divider()

st.sidebar.header("Filter Configuration")
status_filter = st.sidebar.multiselect("Project Status", ["Active", "Complete", "Cancelled"], default=["Active", "Complete", "Cancelled"])
battery_filter = st.sidebar.radio("Battery Included", ["All", "Yes", "No"], horizontal=True)
year_filter = st.sidebar.selectbox("Year", ["All"] + sorted([y for y in df['Year'].unique() if y > 0], reverse=True))

data = df.copy()
if search: data = data[data.apply(lambda row: search.lower() in str(row).lower(), axis=1)]
data = data[data['Status_Clean'].isin(status_filter)]
if battery_filter == "Yes": data = data[data['Battery'] == True]
if battery_filter == "No": data = data[data['Battery'] == False]
if year_filter != "All": data = data[data['Year'] == year_filter]

# --- KPI METRICS ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Exposure", f"${data['TU_Cost'].sum():,.2f}")
col2.metric("Project Count", len(data))
col3.metric("Battery-Ready", len(data[data['Battery'] == True]))
col4.metric("Avg Cycle Time (CAP to PTO)", f"{data['Cycle Time'].mean():.0f} Days" if not data['Cycle Time'].isna().all() else "N/A")
st.divider()

# --- THE STATEWIDE SATURATION MAP ENGINE ---
st.subheader("Interactive Saturation Map")
st.caption("🟢 Complete (Clean Energy) | 🟡 Active (Solar/Waiting) | 🔴 Cancelled (Grid Friction) | 🧿 **Cyan Border = Battery Included**")
m = folium.Map(location=[42.25, -71.80], zoom_start=8, tiles="CartoDB dark_matter")

# Expanded Coastal & Core Cities
ma_coords = {
    "Abington": (42.104, -70.945), "Acton": (42.485, -71.432), "Agawam": (42.069, -72.615), "Amesbury": (42.858, -70.930),
    "Amherst": (42.380, -72.523), "Andover": (42.658, -71.136), "Boston": (42.360, -71.058), "Brockton": (42.083, -71.018), 
    "Fitchburg": (42.583, -71.802), "Springfield": (42.101, -72.589), "Ludlow": (42.160, -72.474), "Methuen": (42.726, -71.190), 
    "Lee": (42.304, -73.249), "Worcester": (42.262, -71.802), "Ashby": (42.678, -71.819), "Medford": (42.418, -71.106),
    "Plymouth": (41.958, -70.667), "Salem": (42.519, -70.896), "Lynn": (42.466, -70.949), "Quincy": (42.252, -71.002),
    "Fall River": (41.701, -71.155), "New Bedford": (41.636, -70.934), "Gloucester": (42.615, -70.661), "Cambridge": (42.373, -71.109)
}

def get_stable_hash(s):
    return int(hashlib.md5(str(s).encode('utf-8')).hexdigest(), 16)

if not data.empty:
    for _, row in data.iterrows():
        city_name = row.get('City', 'Unknown')
        
        if city_name in ma_coords:
            base_lat, base_lon = ma_coords[city_name]
        else:
            # THE FIX: Safe Inland Bounding Box (Central MA only, keeps dots out of the Atlantic)
            city_hash = get_stable_hash(city_name)
            base_lat = 42.1 + (city_hash % 50) / 100.0        # 42.1 to 42.6 Lat
            base_lon = -72.8 + ((city_hash // 100) % 130) / 100.0   # -72.8 to -71.5 Lon
        
        # THE FIX: Tighter Swarm Radius (Divisor increased from 800 to 1400)
        job_hash = get_stable_hash(row['Job Code'])
        offset_lat = base_lat + ((job_hash % 100) - 50) / 1400.0 
        offset_lon = base_lon + (((job_hash // 100) % 100) - 50) / 1400.0
        
        # Color Logic
        if row['Status_Clean'] == 'Active': fill_color = "#FFC107"
        elif row['Status_Clean'] == 'Complete': fill_color = "#00E676"
        else: fill_color = "#FF3D00"
        
        # BATTERY IDENTIFIER: Thick Cyan Border
        if row['Battery']:
            border_color = "#00FFFF" # Electric Cyan
            border_weight = 3
        else:
            border_color = fill_color
            border_weight = 1
        
        tooltip_html = f"<div style='font-family:sans-serif; width: 160px;'><b>{row['Job Code']}</b><hr style='margin: 5px 0;'><b>Status:</b> {row['Status_Clean']}<br><b>Cost:</b> ${row['TU_Cost']:,.0f}<br><b>Battery:</b> {'Yes' if row['Battery'] else 'No'}<br><b>City:</b> {row['City']}</div>"
        
        folium.CircleMarker(
            [offset_lat, offset_lon], 
            radius=5,
            color=border_color,
            weight=border_weight,
            fill=True, 
            fill_color=fill_color,
            fill_opacity=0.7,
            tooltip=folium.Tooltip(tooltip_html)
        ).add_to(m)

st_folium(m, width=1000, height=500)

# --- STRATEGY TABS ---
st.divider()
st.subheader("Cross-Functional Strategy Matrix")

tab1, tab2, tab3, tab4 = st.tabs(["🤝 CX & Sales (SLA Engine)", "📐 Design & Engineering", "🏛️ Policy (DPU Tracker)", "📈 YoY Financial Trends"])

with tab1:
    st.markdown("### Dynamic Utility SLAs")
    st.write("Based on our live historical data, Sales & CX should set customer expectations using these utility-specific timelines:")
    
    utility_sla = df[df['Cycle Time'].notnull()].groupby('Utility')['Cycle Time'].mean().reset_index()
    utility_sla['Cycle Time'] = utility_sla['Cycle Time'].round(0).astype(int).astype(str) + " Days"
    utility_sla = utility_sla.rename(columns={'Cycle Time': 'Predicted Timeline (CAP to PTO)'}).sort_values(by='Predicted Timeline (CAP to PTO)', ascending=False)
    
    st.dataframe(utility_sla, use_container_width=True, hide_index=True)

with tab2:
    st.markdown("### Proactive Engineering Directives")
    st.write("To decrease kickbacks and combat local grid saturation, Design must shift from reactive to proactive strategies.")
    st.markdown("""
    * **The Kickback Tracker:** By mapping areas with heavy Red (Cancelled) density, Design can identify highly saturated circuits before submission. If a project falls into a known saturated cluster, do not submit standard SLDs.
    * **The PCS / Zero-Export Trigger:** For projects in high-friction zones (e.g., Fitchburg, Springfield), instantly trigger Power Control System (PCS) hard-caps or Zero-Export battery profiles. This legally bypasses the utility's requirement for a massive transformer upgrade fee by preventing the system from exporting excess power to the grid.
    """)

with tab3:
    st.markdown("### DPU Lobbying Intelligence")
    cancelled_data = df[df['Status_Clean'] == 'Cancelled']
    total_stranded_cost = cancelled_data['TU_Cost'].sum()
    
    st.error(f"🚨 **Grid Failure Impact:** Utility congestion has resulted in **${total_stranded_cost:,.2f}** of cancelled project value across **{len(cancelled_data)}** residential properties.")
    st.markdown("""
    **The DPU Argument:** "Massachusetts is failing its clean energy mandates not because of consumer demand, but because utilities are attempting to pass nearly a million dollars in infrastructure upgrades onto individual families. We need socialized grid upgrade fees."
    """)

with tab4:
    c1, c2 = st.columns(2)
    with c1:
        st.write("**Financial Exposure by Year**")
        st.bar_chart(df[df['Year'] > 2000].groupby('Year')['TU_Cost'].sum(), color="#FFC107")
    with c2:
        st.write("**Cycle Time (CAP to PTO) by Year**")
        st.line_chart(df[(df['Year'] > 2000) & (df['Cycle Time'].notnull())].groupby('Year')['Cycle Time'].mean(), color="#00E676")

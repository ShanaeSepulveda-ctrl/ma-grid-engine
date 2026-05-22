import streamlit as st
import pandas as pd
import folium
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
        'Project: Service Contract: Service Contract Event: PTO Recorded Date': 'PTO Date',
        'Created Date': 'Created Date',
        'City': 'City',
        'Address': 'Full_Address',
        'BrightBox': 'Battery'
    }
    df = df.rename(columns=rename_map)
    
    # 1. Deduplicate
    df = df.drop_duplicates(subset=['Job Code'], keep='first')
    
    # 2. Financials & Dates
    df['TU_Cost'] = pd.to_numeric(df['TU_Cost'].astype(str).str.replace(r'[\$,]', '', regex=True), errors='coerce').fillna(0)
    df['Created Date'] = pd.to_datetime(df['Created Date'], errors='coerce')
    df['PTO Date'] = pd.to_datetime(df['PTO Date'], errors='coerce')
    df['Year'] = df['Created Date'].dt.year.fillna(0).astype(int)
    
    # 3. Cycle Time
    df['Cycle Time'] = (df['PTO Date'] - df['Created Date']).dt.days
    
    # 4. Status Mapping
    def categorize_status(s):
        s = str(s).lower()
        if 'cancelled' in s: return 'Cancelled'
        if 'pto' in s or 'complete' in s: return 'Complete'
        return 'Active'
    df['Status_Clean'] = df['Status'].apply(categorize_status)
    
    # 5. Battery
    df['Battery'] = df['Battery'].astype(str).str.upper().isin(['TRUE', 'YES', '1'])
    
    # 6. City Cleanup
    df['City'] = df['City'].astype(str).str.title().str.strip()
    
    return df

df = load_and_clean_data()

# --- SIDEBAR ---
st.sidebar.header("🔍 Universal Pipeline Search")
search = st.sidebar.text_input("Search (Job, City, Address):", placeholder="e.g., 221R-057, Boston")
st.sidebar.divider()

st.sidebar.header("Filter Configuration")
status_filter = st.sidebar.multiselect("Project Status", ["Active", "Complete", "Cancelled"], default=["Active", "Complete"])
battery_filter = st.sidebar.radio("Battery Included", ["All", "Yes", "No"], horizontal=True)
year_filter = st.sidebar.selectbox("Year", ["All"] + sorted([y for y in df['Year'].unique() if y > 0], reverse=True))

# Filter Data
data = df.copy()
if search:
    data = data[data.apply(lambda row: search.lower() in str(row).lower(), axis=1)]
data = data[data['Status_Clean'].isin(status_filter)]
if battery_filter == "Yes": data = data[data['Battery'] == True]
if battery_filter == "No": data = data[data['Battery'] == False]
if year_filter != "All": data = data[data['Year'] == year_filter]

# --- KPI METRICS ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Exposure", f"${data['TU_Cost'].sum():,.2f}")
col2.metric("Project Count", len(data))
col3.metric("Battery-Ready", len(data[data['Battery'] == True]))
col4.metric("Avg Cycle Time", f"{data['Cycle Time'].mean():.0f} Days" if not data['Cycle Time'].isna().all() else "N/A")
st.divider()

# --- MAP ENGINE (WITH RESTORED MASSIVE DICTIONARY & JITTER) ---
st.subheader("Interactive Saturation Map")
m = folium.Map(location=[42.25, -71.80], zoom_start=8, tiles="CartoDB dark_matter")

# Restored Master Coordinates
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
    "Worcester": (42.262, -71.802), "Dalton": (42.475, -73.166), "Whitman": (42.081, -70.940), "Lee": (42.304, -73.249), 
    "Hadley": (42.341, -72.588), "Athol": (42.595, -72.226), "Ashby": (42.678, -71.819), "Rehoboth": (41.840, -71.264), 
    "Dudley": (42.046, -71.931), "North Andover": (42.695, -71.133), "Bedford": (42.490, -71.276), "Feeding Hills": (42.069, -72.678),
    "Westminster": (42.545, -71.908), "Huntington": (42.235, -72.878)
}

if not data.empty:
    for _, row in data.iterrows():
        # Get base coordinates
        base_lat, base_lon = ma_coords.get(row['City'], (42.25, -71.80))
        
        # RESTORED JITTER ENGINE: Separates overlapping dots in the same city
        offset_lat = base_lat + (hash(str(row['Job Code'])) % 100) / 10000.0
        offset_lon = base_lon + (hash(str(row['Job Code']) + "x") % 100) / 10000.0
        
        # Colors
        color = "white" if row['Status_Clean'] == 'Active' else ("#00a8ff" if row['Status_Clean'] == 'Complete' else "red")
        
        # Clean Vertical Tooltip
        tooltip_html = f"""
        <div style='font-family:sans-serif; width: 160px;'>
            <b>{row['Job Code']}</b><hr style='margin: 5px 0;'>
            <b>Status:</b> {row['Status_Clean']}<br>
            <b>Battery:</b> {'Yes' if row['Battery'] else 'No'}<br>
            <b>Cost:</b> ${row['TU_Cost']:,.0f}<br>
            <b>City:</b> {row['City']}
        </div>
        """
        
        folium.CircleMarker(
            [offset_lat, offset_lon], 
            radius=6, 
            color=color, 
            fill=True, 
            fill_opacity=0.8,
            tooltip=folium.Tooltip(tooltip_html)
        ).add_to(m)

st_folium(m, width=1000, height=500)

# --- RESTORED TRENDS ENGINE ---
st.divider()
col_trend, col_cycle = st.columns(2)

with col_trend:
    st.subheader("📈 YoY Financial Exposure")
    trend_data = data[data['Year'] > 2000].groupby('Year')['TU_Cost'].sum()
    st.bar_chart(trend_data)

with col_cycle:
    st.subheader("⏱️ Avg Cycle Time (By Year)")
    # Show cycle time trends over the years
    cycle_trend = data[data['Year'] > 2000].groupby('Year')['Cycle Time'].mean()
    st.line_chart(cycle_trend)

# --- STRATEGY TABS ---
st.divider()
st.subheader("3. Cross-Functional Strategy Matrix")

tab1, tab2, tab3 = st.tabs(["🤝 CX & Sales", "📐 Design & Engineering", "🏛️ Policy & Exec Insights"])

with tab1:
    st.write("Targeting high-value clusters. Provide customers with realistic 4-8 week expectation windows in Red/High-Friction zones.")
with tab2:
    st.write("Maintain SLD compliance on projects > 25kW. Utilize battery storage to offset grid upgrade requirements.")
with tab3:
    st.markdown("""
    ### Utility Efficiency Benchmarks (Cycle Time)
    * **United Illuminating:** 316.0 days
    * **National Grid:** 289.1 days
    * **UNITIL:** 231.9 days
    * **WMECO:** 215.0 days
    * **Eversource:** 196.3 days
    * **Green Mountain Power:** 135.2 days
    
    **Strategic Takeaway:** We are currently seeing a ~250 day total cycle time from CAP approval to PTO. Reducing this duration in the 'Install to PTO' phase (140 days avg) offers our highest opportunity for margin recovery. There is no direct correlation between the expense amount and the cycle time.
    """)

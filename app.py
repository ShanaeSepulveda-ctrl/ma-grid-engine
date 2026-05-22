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
        'BrightBox': 'Battery'
    }
    df = df.rename(columns=rename_map)
    df = df.drop_duplicates(subset=['Job Code'], keep='first')
    
    # Financials & Dates
    df['TU_Cost'] = pd.to_numeric(df['TU_Cost'].astype(str).str.replace(r'[\$,]', '', regex=True), errors='coerce').fillna(0)
    df['Created Date'] = pd.to_datetime(df['Created Date'], errors='coerce')
    df['PTO Date'] = pd.to_datetime(df['PTO Date'], errors='coerce')
    df['Year'] = df['Created Date'].dt.year.fillna(0).astype(int)
    
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

# --- SIDEBAR: UNIFIED AESTHETIC ---
st.sidebar.header("Filter Configuration")
status_filter = st.sidebar.multiselect("Project Status", ["Active", "Complete", "Cancelled"], default=["Active", "Complete"])
battery_filter = st.sidebar.radio("Battery Included", ["All", "Yes", "No"], horizontal=True)
year_filter = st.sidebar.selectbox("Year", ["All"] + sorted(df['Year'].unique().tolist(), reverse=True))

# Search Bar
search = st.sidebar.text_input("Search (Job, Zip, City):", placeholder="Enter query...")

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
col4.metric("Avg Exposure", f"${data['TU_Cost'].mean():,.0f}")
st.divider()

# --- MAP ENGINE ---
st.subheader("Interactive Saturation Map")
m = folium.Map(location=[42.25, -71.80], zoom_start=8, tiles="CartoDB dark_matter")

# Fallback Dictionary
ma_coords = {"Fitchburg": (42.583, -71.802), "Springfield": (42.101, -72.589), "Brockton": (42.083, -71.018), 
             "Ludlow": (42.160, -72.474), "Methuen": (42.726, -71.190), "Lee": (42.304, -73.249), "Boston": (42.360, -71.058)}

if not data.empty:
    for _, row in data.iterrows():
        coords = ma_coords.get(row.get('City'), (42.25, -71.80))
        color = "white" if row['Status_Clean'] == 'Active' else ("#00a8ff" if row['Status_Clean'] == 'Complete' else "red")
        folium.CircleMarker(coords, radius=6, color=color, fill=True, fill_opacity=0.8,
            tooltip=folium.Tooltip(f"Job: {row['Job Code']}<br>Status: {row['Status_Clean']}<br>Cost: ${row['TU_Cost']:,.0f}")
        ).add_to(m)

st_folium(m, width=1000, height=400)

# --- STRATEGY TABS ---
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
    
    **Strategic Takeaway:** We are currently seeing a ~250 day total cycle time from CAP approval to PTO. Reducing this duration in the 'Install to PTO' phase (140 days avg) offers our highest opportunity for margin recovery.
    """)

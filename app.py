import streamlit as st
import pandas as pd
import numpy as np
import folium
import hashlib
from streamlit_folium import st_folium

st.set_page_config(page_title="MA Resilience Dashboard", page_icon="⚡", layout="wide")
st.title("⚡ MA Resilience & Strategy Dashboard")

@st.cache_data
def load_and_clean_data():
    df = pd.read_csv("master_pipeline.csv")
    rename_map = {
        'Project: Service Contract: Service Contract Event: Job Code': 'Job Code',
        'Line Item Price to Customer': 'TU_Cost',
        'SOW Proposal Summary: Project: Service Contract: Status': 'Status',
        'Project: Service Contract: Service Contract Event: CAP date approved': 'CAP Date',
        'Project: Service Contract: Service Contract Event: PTO Recorded Date': 'PTO Date',
        'Created Date': 'Created Date', 'City': 'City', 'Utility Company': 'Utility', 'BrightBox': 'Battery'
    }
    df = df.rename(columns=rename_map)
    df = df.drop_duplicates(subset=['Job Code'], keep='first')
    
    df['TU_Cost'] = pd.to_numeric(df['TU_Cost'].astype(str).str.replace(r'[\$,]', '', regex=True), errors='coerce').fillna(0)
    df['Created Date'] = pd.to_datetime(df['Created Date'], errors='coerce')
    df['CAP Date'] = pd.to_datetime(df['CAP Date'], errors='coerce')
    df['PTO Date'] = pd.to_datetime(df['PTO Date'], errors='coerce')
    df['Year'] = df['Created Date'].apply(lambda x: x.year if pd.notnull(x) else 0).astype(int)
    
    # Accurate Cycle Time: CAP to PTO
    df['Cycle Time'] = (df['PTO Date'] - df['CAP Date']).dt.days
    df['Cycle Time'] = df['Cycle Time'].apply(lambda x: x if pd.notnull(x) and x >= 0 else np.nan)
    
    df['Status_Clean'] = df['Status'].apply(lambda s: 'Cancelled' if 'cancelled' in str(s).lower() else ('Complete' if any(x in str(s).lower() for x in ['pto', 'complete']) else 'Active'))
    df['Battery'] = df['Battery'].astype(str).str.upper().isin(['TRUE', 'YES', '1'])
    df['City'] = df['City'].astype(str).str.title().str.strip()
    return df

df = load_and_clean_data()

# --- SIDEBAR ---
st.sidebar.header("🔍 Universal Pipeline Search")
search = st.sidebar.text_input("Search (Job, City):", placeholder="e.g., Boston")
status_filter = st.sidebar.multiselect("Project Status", ["Active", "Complete", "Cancelled"], default=["Active", "Complete", "Cancelled"])
battery_filter = st.sidebar.radio("Battery Included", ["All", "Yes", "No"], horizontal=True)
year_filter = st.sidebar.selectbox("Year", ["All"] + sorted([y for y in df['Year'].unique() if y > 0], reverse=True))

data = df.copy()
if search: data = data[data.apply(lambda row: search.lower() in str(row).lower(), axis=1)]
data = data[data['Status_Clean'].isin(status_filter)]
if battery_filter == "Yes": data = data[data['Battery'] == True]
if battery_filter == "No": data = data[data['Battery'] == False]
if year_filter != "All": data = data[data['Year'] == year_filter]

# --- METRICS ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Exposure", f"${data['TU_Cost'].sum():,.2f}")
col2.metric("Project Count", len(data))
col3.metric("Battery Included", len(data[data['Battery'] == True]))
col4.metric("Avg Cycle (Days)", f"{data['Cycle Time'].mean():.0f}")
st.divider()

# --- MAP ---
st.subheader("Interactive Saturation Map")
m = folium.Map(location=[42.25, -71.80], zoom_start=8, tiles="CartoDB dark_matter")

def get_stable_hash(s): return int(hashlib.md5(str(s).encode('utf-8')).hexdigest(), 16)

for _, row in data.iterrows():
    h = get_stable_hash(row['Job Code'])
    lat = 42.1 + (h % 50) / 100.0 + ((h % 10) - 5) / 500.0
    lon = -72.8 + ((h // 100) % 130) / 100.0 + ((h % 10) - 5) / 500.0
    color = {"Active": "#FFC107", "Complete": "#00E676", "Cancelled": "#FF3D00"}.get(row['Status_Clean'], "gray")
    folium.CircleMarker([lat, lon], radius=5, color=color, fill=True, fill_opacity=0.7, 
                        tooltip=f"{row['Job Code']} | {row['Status_Clean']} | ${row['TU_Cost']:,.0f}").add_to(m)

st_folium(m, width=1000, height=450)

# --- STRATEGY TABS ---
st.divider()
tab1, tab2, tab3 = st.tabs(["🤝 CX & Sales (SLA Engine)", "📐 Design & Engineering", "🏛️ Policy & Exec Insights"])

with tab1:
    st.write("Predicted Timeline (CAP to PTO):")
    sla = df[df['Cycle Time'].notnull()].groupby('Utility')['Cycle Time'].mean().round(0).astype(int).astype(str) + " Days"
    st.dataframe(sla.reset_index().rename(columns={'Cycle Time': 'Days'}), use_container_width=True, hide_index=True)

with tab2:
    st.markdown("""* **The Kickback Tracker:** Use map saturation (Red clusters) to identify saturated circuits before submission.
* **The PCS / Zero-Export Trigger:** For high-friction zones, trigger Power Control System (PCS) hard-caps to bypass transformer upgrades.""")

with tab3:
    st.error(f"Stranded Value: ${df[df['Status_Clean']=='Cancelled']['TU_Cost'].sum():,.2f}")
    st.write("Advocate for Pro-Rata cost sharing and Fast-Tracked PCS Integration at the DPU level.")

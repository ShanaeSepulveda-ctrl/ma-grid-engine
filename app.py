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
    df = pd.read_csv("TU with Status - Sheet1 (1).csv")
    
    rename_map = {
        'TU Invoice': 'TU_Cost',
        'Project Status': 'Status',
        'CAP date approved': 'CAP Date',
        'Install Date': 'Install Date',
        'PTO Recorded Date': 'PTO Date',
        'Created Date': 'Created Date',
        'Utility Company': 'Utility',
        'BrightBox': 'Battery'
    }
    df = df.rename(columns=rename_map)
    df = df.drop_duplicates(subset=['Job Code'], keep='first')
    
    df['TU_Cost'] = pd.to_numeric(df['TU_Cost'].astype(str).str.replace(r'[\$,]', '', regex=True), errors='coerce').fillna(0)
    df['Created Date'] = pd.to_datetime(df['Created Date'], errors='coerce')
    df['CAP Date'] = pd.to_datetime(df['CAP Date'], errors='coerce')
    df['Install Date'] = pd.to_datetime(df['Install Date'], errors='coerce')
    df['PTO Date'] = pd.to_datetime(df['PTO Date'], errors='coerce')
    
    df['Year'] = df['Created Date'].apply(lambda x: x.year if pd.notnull(x) else 0).astype(int)
    
    # Accurate Cycle Times
    df['Cycle Time (CAP to PTO)'] = (df['PTO Date'] - df['CAP Date']).dt.days
    df['Cycle Time (CAP to PTO)'] = df['Cycle Time (CAP to PTO)'].apply(lambda x: x if pd.notnull(x) and x >= 0 else np.nan)
    
    df['Cycle Time (CAP to Install)'] = (df['Install Date'] - df['CAP Date']).dt.days
    df['Cycle Time (CAP to Install)'] = df['Cycle Time (CAP to Install)'].apply(lambda x: x if pd.notnull(x) and x >= 0 else np.nan)
    
    df['Status'] = df['Status'].fillna('Unknown').astype(str).str.strip()
    df['Battery'] = df['Battery'].astype(str).str.upper().isin(['TRUE', 'YES', '1'])
    df['City'] = df['City'].astype(str).str.title().str.strip()
    df['Utility'] = df['Utility'].astype(str).str.title().replace({'National Grid': 'National Grid', 'Eversource': 'Eversource', 'Wmeco': 'WMECO', 'Unitil': 'UNITIL'})
    
    return df

df = load_and_clean_data()

# --- SIDEBAR ---
st.sidebar.header("🔍 Universal Pipeline Search")
search = st.sidebar.text_input("Search (Job, City):", placeholder="e.g., Boston")
st.sidebar.divider()

st.sidebar.header("Filter Configuration")
all_statuses = sorted(df['Status'].unique().tolist())
status_filter = st.sidebar.multiselect("Project Status (Col M)", all_statuses, default=all_statuses)
battery_filter = st.sidebar.radio("Battery Included", ["All", "Yes", "No"], horizontal=True)
year_filter = st.sidebar.selectbox("Year Created (Col J)", ["All"] + sorted([y for y in df['Year'].unique() if y > 0], reverse=True))

# THE NEW HIGH EXPOSURE DRILL-DOWN
exposure_filter = st.sidebar.selectbox("High Exposure Risk", ["All Projects", "> $20,000", "> $30,000", "> $40,000"])

data = df.copy()
if search: data = data[data.apply(lambda row: search.lower() in str(row).lower(), axis=1)]
data = data[data['Status'].isin(status_filter)]
if battery_filter == "Yes": data = data[data['Battery'] == True]
if battery_filter == "No": data = data[data['Battery'] == False]
if year_filter != "All": data = data[data['Year'] == year_filter]

# Apply High Exposure Filter
if exposure_filter == "> $20,000": data = data[data['TU_Cost'] > 20000]
elif exposure_filter == "> $30,000": data = data[data['TU_Cost'] > 30000]
elif exposure_filter == "> $40,000": data = data[data['TU_Cost'] > 40000]

# --- KPI METRICS ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Exposure", f"${data['TU_Cost'].sum():,.2f}")
col2.metric("Project Count", len(data))
col3.metric("Battery-Ready", len(data[data['Battery'] == True]))
col4.metric("Avg Cycle (CAP to PTO)", f"{data['Cycle Time (CAP to PTO)'].mean():.0f} Days" if not data['Cycle Time (CAP to PTO)'].isna().all() else "N/A")
st.divider()

# --- STATEWIDE SATURATION MAP ---
st.subheader("Interactive Saturation Map")
st.caption("🟢 Complete | 🟡 Active/Pending | 🔴 Cancelled | 🧿 **Cyan Border = Battery Included**")
m = folium.Map(location=[42.25, -71.80], zoom_start=8, tiles="CartoDB dark_matter")

# Expanded Coastal/Core Dict
ma_coords = {
    "Abington": (42.104, -70.945), "Acton": (42.485, -71.432), "Agawam": (42.069, -72.615), "Amesbury": (42.858, -70.930),
    "Amherst": (42.380, -72.523), "Andover": (42.658, -71.136), "Boston": (42.360, -71.058), "Brockton": (42.083, -71.018), 
    "Fitchburg": (42.583, -71.802), "Springfield": (42.101, -72.589), "Ludlow": (42.160, -72.474), "Methuen": (42.726, -71.190), 
    "Lee": (42.304, -73.249), "Worcester": (42.262, -71.802), "Ashby": (42.678, -71.819), "Medford": (42.418, -71.106),
    "Plymouth": (41.958, -70.667), "Salem": (42.519, -70.896), "Lynn": (42.466, -70.949), "Quincy": (42.252, -71.002),
    "Fall River": (41.701, -71.155), "New Bedford": (41.636, -70.934), "Gloucester": (42.615, -70.661), "Cambridge": (42.373, -71.109)
}

def get_stable_hash(s): return int(hashlib.md5(str(s).encode('utf-8')).hexdigest(), 16)

if not data.empty:
    for _, row in data.iterrows():
        city_name = row.get('City', 'Unknown')
        h = get_stable_hash(row['Job Code'])
        
        if city_name in ma_coords:
            base_lat, base_lon = ma_coords[city_name]
        else:
            city_hash = get_stable_hash(city_name)
            base_lat = 42.1 + (city_hash % 50) / 100.0        
            base_lon = -72.8 + ((city_hash // 100) % 130) / 100.0   
        
        # Tightened jitter radius
        offset_lat = base_lat + ((h % 100) - 50) / 4000.0 
        offset_lon = base_lon + (((h // 100) % 100) - 50) / 4000.0
        
        s_lower = str(row['Status']).lower()
        if 'complete' in s_lower: fill_color = "#00E676"
        elif 'cancel' in s_lower: fill_color = "#FF3D00"
        else: fill_color = "#FFC107"
        
        border_color = "#00FFFF" if row['Battery'] else fill_color
        border_weight = 3 if row['Battery'] else 1
        
        tooltip_html = f"<div style='font-family:sans-serif; width: 160px;'><b>{row['Job Code']}</b><hr style='margin: 5px 0;'><b>Status:</b> {row['Status']}<br><b>Cost:</b> ${row['TU_Cost']:,.0f}<br><b>Battery:</b> {'Yes' if row['Battery'] else 'No'}<br><b>City:</b> {row['City']}</div>"
        
        folium.CircleMarker([offset_lat, offset_lon], radius=5, color=border_color, weight=border_weight, fill=True, fill_color=fill_color, fill_opacity=0.7, tooltip=folium.Tooltip(tooltip_html)).add_to(m)

st_folium(m, width=1000, height=450)

# --- STRATEGY TABS ---
st.divider()
st.subheader("Cross-Functional Strategy Matrix")

tab1, tab2, tab3, tab4 = st.tabs(["📊 Executive Insights", "🤝 CX & SLAs", "📐 Design & Eng", "🏛️ DPU Policy"])

with tab1:
    st.markdown("### High-Level Operational Insights")
    c1, c2 = st.columns(2)
    with c1:
        st.info("**Financial Extremes by Utility**\n* **WMECO** holds the highest single invoice risk ($46,411).\n* **UNITIL** projects average the highest cost ($7,469).\n* **National Grid** drives volume (406 projects) with costs generally clustering between $5k-$20k, but experiencing massive tail-risk spikes up to $35k.")
    with c2:
        st.success("**Pipeline Health & Timelines**\n* **53.4%** of projects are successfully completed, but a critical **28.4%** are cancelled, highlighting grid friction.\n* **Efficiency Gap:** Green Mountain Power achieves CAP to PTO in ~135 days, while National Grid stretches to 289 days for identical scopes of work.")

with tab2:
    st.markdown("### Dynamic Utility SLAs")
    st.write("Live Service Level Agreements based on historical performance:")
    
    sla_df = df.groupby('Utility').agg(
        Avg_CAP_to_Install=('Cycle Time (CAP to Install)', 'mean'),
        Avg_CAP_to_PTO=('Cycle Time (CAP to PTO)', 'mean')
    ).dropna()
    
    sla_df['Avg_CAP_to_Install'] = sla_df['Avg_CAP_to_Install'].round(0).astype(int).astype(str) + " Days"
    sla_df['Avg_CAP_to_PTO'] = sla_df['Avg_CAP_to_PTO'].round(0).astype(int).astype(str) + " Days"
    
    st.dataframe(sla_df.reset_index().rename(columns={'Avg_CAP_to_Install': 'CAP to Install (Predicted)', 'Avg_CAP_to_PTO': 'CAP to PTO (Predicted)'}), use_container_width=True, hide_index=True)

with tab3:
    st.markdown("### Proactive Engineering Directives\n* **The Kickback Tracker:** Use map saturation (Red clusters) to identify saturated circuits before submission.\n* **The PCS / Zero-Export Trigger:** For high-friction zones, trigger Power Control System (PCS) hard-caps to bypass transformer upgrades.")

with tab4:
    cancelled_df = df[df['Status'].str.contains('Cancel', case=False, na=False)]
    stranded_total = cancelled_df['TU_Cost'].sum()
    
    st.error(f"🚨 **Total Grid Failure Impact:** Utility congestion has resulted in **${stranded_total:,.2f}** of cancelled project value.")
    
    col_a, col_b = st.columns([1, 2])
    with col_a:
        st.markdown("**Strategic Policy Proposals:**\nAdvocate for **Pro-Rata Cost Sharing** (Depreciation Model) and **Fast-Tracked PCS Integration** to prevent the stranding of clean energy assets.")
    with col_b:
        st.markdown("**The Escalation Trend (Stranded Revenue by Year):**")
        cancelled_trend = cancelled_df[cancelled_df['Year'] > 2020].groupby('Year')['TU_Cost'].sum()
        st.bar_chart(cancelled_trend, color="#FF3D00")

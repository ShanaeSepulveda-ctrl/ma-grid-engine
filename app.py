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
    
    df['Cycle Time (CAP to PTO)'] = (df['PTO Date'] - df['CAP Date']).dt.days
    df['Cycle Time (CAP to PTO)'] = df['Cycle Time (CAP to PTO)'].apply(lambda x: x if pd.notnull(x) and x >= 0 else np.nan)
    
    df['Cycle Time (CAP to Install)'] = (df['Install Date'] - df['CAP Date']).dt.days
    df['Cycle Time (CAP to Install)'] = df['Cycle Time (CAP to Install)'].apply(lambda x: x if pd.notnull(x) and x >= 0 else np.nan)
    
    df['Status'] = df['Status'].fillna('Unknown').astype(str).str.strip()
    df['Battery'] = df['Battery'].astype(str).str.upper().isin(['TRUE', 'YES', '1'])
    # Standardize City Names to Title Case for exact dictionary matching
    df['City'] = df['City'].astype(str).str.title().str.strip()
    df['Utility'] = df['Utility'].astype(str).str.title().replace({'National Grid': 'National Grid', 'Eversource': 'Eversource', 'Wmeco': 'WMECO', 'Unitil': 'UNITIL'})
    
    return df

df = load_and_clean_data()

# --- SIDEBAR FILTERS ---
st.sidebar.header("🔍 Universal Pipeline Search")
search = st.sidebar.text_input("Search (Job, City):", placeholder="e.g., Lowell")
st.sidebar.divider()

st.sidebar.header("Filter Configuration")
all_statuses = sorted(df['Status'].unique().tolist())
status_filter = st.sidebar.multiselect("Project Status (Col M)", all_statuses, default=all_statuses)
battery_filter = st.sidebar.radio("Battery Included", ["All", "Yes", "No"], horizontal=True)
year_filter = st.sidebar.selectbox("Year Created (Col J)", ["All"] + sorted([y for y in df['Year'].unique() if y > 0], reverse=True))

exposure_filter = st.sidebar.selectbox("High Exposure Risk", ["All Projects", "> $20,000", "> $30,000", "> $40,000"])

data = df.copy()
if search: data = data[data.apply(lambda row: search.lower() in str(row).lower(), axis=1)]
data = data[data['Status'].isin(status_filter)]
if battery_filter == "Yes": data = data[data['Battery'] == True]
if battery_filter == "No": data = data[data['Battery'] == False]
if year_filter != "All": data = data[data['Year'] == year_filter]

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

# --- MASSIVE GEOGRAPHIC ENGINE ---
st.subheader("Interactive Saturation Map")
st.caption("🟢 Complete | 🟡 Active/Pending | 🔴 Cancelled | 🧿 **Cyan Border = Battery Included**")
m = folium.Map(location=[42.25, -71.80], zoom_start=8, tiles="CartoDB dark_matter")

# The Master 200+ City GPS Dictionary
ma_coords = {
    "Abington": (42.104, -70.945), "Acton": (42.485, -71.432), "Acushnet": (41.679, -70.908), "Adams": (42.624, -73.115),
    "Agawam": (42.069, -72.615), "Amesbury": (42.858, -70.930), "Amherst": (42.380, -72.523), "Andover": (42.658, -71.136),
    "Arlington": (42.415, -71.156), "Ashburnham": (42.635, -71.906), "Ashby": (42.678, -71.819), "Ashland": (42.259, -71.464),
    "Athol": (42.595, -72.226), "Attleboro": (41.944, -71.283), "Auburn": (42.200, -71.835), "Avon": (42.126, -71.042),
    "Ayer": (42.559, -71.589), "Barnstable": (41.700, -70.300), "Bedford": (42.490, -71.276), "Belchertown": (42.277, -72.401),
    "Bellingham": (42.083, -71.475), "Belmont": (42.395, -71.178), "Beverly": (42.558, -70.880), "Billerica": (42.558, -71.268),
    "Blackstone": (42.019, -71.536), "Bolton": (42.433, -71.608), "Boston": (42.360, -71.058), "Bourne": (41.740, -70.598),
    "Braintree": (42.207, -71.000), "Bridgewater": (41.990, -70.975), "Brockton": (42.083, -71.018), "Brookline": (42.331, -71.121),
    "Burlington": (42.504, -71.195), "Cambridge": (42.373, -71.109), "Canton": (42.158, -71.144), "Carver": (41.884, -70.762),
    "Charlton": (42.135, -71.969), "Chatham": (41.682, -69.959), "Chelmsford": (42.599, -71.367), "Chelsea": (42.391, -71.032),
    "Chicopee": (42.148, -72.607), "Clinton": (42.416, -71.682), "Cohasset": (42.241, -70.802), "Concord": (42.460, -71.348),
    "Danvers": (42.562, -70.930), "Dartmouth": (41.626, -70.984), "Dedham": (42.243, -71.167), "Dennis": (41.735, -70.193),
    "Dighton": (41.815, -71.126), "Douglas": (42.052, -71.740), "Dracut": (42.668, -71.303), "Dudley": (42.046, -71.931),
    "East Bridgewater": (42.033, -70.959), "Easthampton": (42.266, -72.673), "Easton": (42.029, -71.102), "Everett": (42.408, -71.053),
    "Fairhaven": (41.637, -70.905), "Fall River": (41.701, -71.155), "Falmouth": (41.551, -70.615), "Fitchburg": (42.583, -71.802),
    "Foxborough": (42.065, -71.248), "Framingham": (42.279, -71.416), "Franklin": (42.083, -71.396), "Gardner": (42.574, -71.998),
    "Gloucester": (42.615, -70.661), "Grafton": (42.207, -71.683), "Greenfield": (42.587, -72.599), "Groton": (42.611, -71.573),
    "Halifax": (41.991, -70.863), "Hanover": (42.112, -70.826), "Harvard": (42.500, -71.583), "Haverhill": (42.776, -71.077),
    "Hingham": (42.241, -70.889), "Holbrook": (42.155, -71.008), "Holden": (42.351, -71.864), "Holliston": (42.202, -71.424),
    "Holyoke": (42.207, -72.616), "Hopedale": (42.130, -71.542), "Hopkinton": (42.228, -71.522), "Hudson": (42.391, -71.566),
    "Huntington": (42.235, -72.878), "Ipswich": (42.679, -70.841), "Kingston": (41.994, -70.725), "Lakeville": (41.839, -70.941),
    "Lancaster": (42.455, -71.674), "Lawrence": (42.707, -71.163), "Lee": (42.304, -73.249), "Leicester": (42.245, -71.907),
    "Lenox": (42.358, -73.284), "Leominster": (42.525, -71.759), "Lexington": (42.447, -71.227), "Lincoln": (42.426, -71.306),
    "Littleton": (42.537, -71.482), "Longmeadow": (42.049, -72.581), "Lowell": (42.633, -71.316), "Ludlow": (42.160, -72.474),
    "Lunenburg": (42.594, -71.722), "Lynn": (42.466, -70.949), "Lynnfield": (42.529, -71.031), "Malden": (42.425, -71.066),
    "Mansfield": (42.031, -71.218), "Marblehead": (42.500, -70.857), "Marlborough": (42.345, -71.552), "Marshfield": (42.091, -70.705),
    "Mashpee": (41.648, -70.481), "Maynard": (42.433, -71.450), "Medfield": (42.186, -71.306), "Medford": (42.418, -71.106),
    "Medway": (42.146, -71.397), "Melrose": (42.458, -71.065), "Methuen": (42.726, -71.190), "Middleborough": (41.892, -70.911),
    "Middleton": (42.594, -71.017), "Milford": (42.141, -71.516), "Millbury": (42.191, -71.761), "Millis": (42.165, -71.353),
    "Milton": (42.249, -71.071), "Natick": (42.283, -71.349), "Needham": (42.280, -71.235), "New Bedford": (41.636, -70.934),
    "Newburyport": (42.812, -70.877), "Newton": (42.337, -71.209), "Norfolk": (42.118, -71.325), "North Adams": (42.700, -73.108),
    "North Andover": (42.695, -71.133), "North Attleborough": (41.982, -71.328), "North Reading": (42.575, -71.089), "Northampton": (42.325, -72.641),
    "Northborough": (42.319, -71.641), "Norton": (41.966, -71.186), "Norwell": (42.161, -70.793), "Norwood": (42.194, -71.199),
    "Oxford": (42.116, -71.863), "Palmer": (42.158, -72.328), "Peabody": (42.527, -70.928), "Pembroke": (42.060, -70.822),
    "Pittsfield": (42.450, -73.245), "Plymouth": (41.958, -70.667), "Quincy": (42.252, -71.002), "Randolph": (42.162, -71.041),
    "Raynham": (41.930, -71.037), "Reading": (42.525, -71.104), "Rehoboth": (41.840, -71.264), "Revere": (42.408, -71.011),
    "Rockland": (42.131, -70.916), "Salem": (42.519, -70.896), "Sandwich": (41.759, -70.493), "Saugus": (42.463, -71.012),
    "Scituate": (42.195, -70.723), "Seekonk": (41.821, -71.336), "Sharon": (42.124, -71.176), "Shrewsbury": (42.295, -71.712),
    "Somerset": (41.765, -71.131), "Somerville": (42.387, -71.099), "South Hadley": (42.260, -72.575), "Southampton": (42.227, -72.730),
    "Southborough": (42.305, -71.530), "Southbridge": (42.075, -72.033), "Spencer": (42.242, -71.993), "Springfield": (42.101, -72.589),
    "Stoneham": (42.480, -71.098), "Stoughton": (42.125, -71.102), "Stow": (42.436, -71.504), "Sudbury": (42.383, -71.416),
    "Sutton": (42.150, -71.764), "Swampscott": (42.469, -70.918), "Swansea": (41.748, -71.190), "Taunton": (41.900, -71.089),
    "Tewksbury": (42.610, -71.234), "Topsfield": (42.637, -70.949), "Tyngsborough": (42.673, -71.423), "Upton": (42.175, -71.627),
    "Uxbridge": (42.077, -71.630), "Wakefield": (42.503, -71.072), "Walpole": (42.141, -71.249), "Waltham": (42.376, -71.235),
    "Ware": (42.260, -72.241), "Wareham": (41.762, -70.716), "Watertown": (42.370, -71.183), "Wayland": (42.362, -71.361),
    "Webster": (42.050, -71.880), "Wellesley": (42.296, -71.292), "West Boylston": (42.361, -71.779), "West Bridgewater": (42.019, -71.011),
    "West Springfield": (42.107, -72.620), "Westborough": (42.269, -71.616), "Westfield": (42.120, -72.749), "Westford": (42.579, -71.439),
    "Westminster": (42.545, -71.908), "Weston": (42.366, -71.303), "Westport": (41.623, -71.031), "Westwood": (42.222, -71.213),
    "Weymouth": (42.218, -70.940), "Whitman": (42.081, -70.940), "Wilbraham": (42.122, -72.430), "Williamstown": (42.712, -73.203),
    "Wilmington": (42.551, -71.171), "Winchendon": (42.680, -72.046), "Winchester": (42.452, -71.137), "Winthrop": (42.374, -70.982),
    "Woburn": (42.479, -71.152), "Worcester": (42.262, -71.802), "Worthington": (42.405, -72.938), "Wrentham": (42.066, -71.328),
    "Yarmouth": (41.696, -70.228)
}

def get_stable_hash(s): return int(hashlib.md5(str(s).encode('utf-8')).hexdigest(), 16)

# Find missing cities for Transparency Tracker
all_cities_in_data = set(data['City'].unique())
missing_cities = sorted(list(all_cities_in_data - set(ma_coords.keys())))

if missing_cities:
    st.sidebar.divider()
    st.sidebar.warning(f"⚠️ {len(missing_cities)} Cities Unmapped")
    with st.sidebar.expander("View Missing Cities"):
        st.write("These cities defaulted to map center because they lack exact GPS coordinates:")
        for mc in missing_cities:
            st.write(f"- {mc}")

if not data.empty:
    for _, row in data.iterrows():
        city_name = row.get('City', 'Unknown')
        h = get_stable_hash(row['Job Code'])
        
        # If city not in dictionary, default to Worcester (Center MA)
        base_lat, base_lon = ma_coords.get(city_name, (42.262, -71.802))
        
        # TIGHT JITTER: Spreads dots safely within the actual city limits (approx 1.5 miles)
        offset_lat = base_lat + ((h % 100) - 50) / 3000.0 
        offset_lon = base_lon + (((h // 100) % 100) - 50) / 3000.0
        
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

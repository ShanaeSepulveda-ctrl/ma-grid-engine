import streamlit as st
import pandas as pd
import numpy as np
import folium
import hashlib
import difflib
from streamlit_folium import st_folium

# --- PAGE CONFIG ---
st.set_page_config(page_title="MA Grid Intelligence", page_icon="⚡", layout="wide")
st.title("⚡ Regional Resilience & Strategy Dashboard")

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
    
    # Clean City Names to Title Case
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

# Zoomed out slightly to comfortably show VT/NH projects
m = folium.Map(location=[42.50, -71.80], zoom_start=7, tiles="CartoDB dark_matter")

# The Master GPS Dictionary (Now including VT/NH Extensions)
ma_coords = {
    # Out of State Extensions
    "Bristol": (44.133, -73.078), "Windham": (42.801, -71.304), "Nashua": (42.765, -71.467), 
    "Bennington": (42.878, -73.196), "Brattleboro": (42.850, -72.557), "Rutland": (43.610, -72.972),
    
    # MA Master List
    "Abington": (42.104, -70.945), "Acton": (42.485, -71.432), "Acushnet": (41.679, -70.908), "Adams": (42.624, -73.115),
    "Agawam": (42.069, -72.615), "Alford": (42.234, -73.419), "Amesbury": (42.858, -70.930), "Amherst": (42.380, -72.523),
    "Andover": (42.658, -71.136), "Aquinnah": (41.334, -70.820), "Arlington": (42.415, -71.156), "Ashburnham": (42.635, -71.906),
    "Ashby": (42.678, -71.819), "Ashfield": (42.526, -72.793), "Ashland": (42.259, -71.464), "Athol": (42.595, -72.226),
    "Attleboro": (41.944, -71.283), "Auburn": (42.200, -71.835), "Avon": (42.126, -71.042), "Ayer": (42.559, -71.589),
    "Barnstable": (41.700, -70.300), "Barre": (42.421, -72.105), "Becket": (42.321, -73.078), "Bedford": (42.490, -71.276),
    "Belchertown": (42.277, -72.401), "Bellingham": (42.083, -71.475), "Belmont": (42.395, -71.178), "Berkley": (41.846, -71.082),
    "Berlin": (42.382, -71.636), "Bernardston": (42.670, -72.554), "Beverly": (42.558, -70.880), "Billerica": (42.558, -71.268),
    "Blackstone": (42.019, -71.536), "Blandford": (42.181, -72.926), "Bolton": (42.433, -71.608), "Boston": (42.360, -71.058),
    "Bourne": (41.740, -70.598), "Boxborough": (42.489, -71.517), "Boxford": (42.661, -70.996), "Boylston": (42.351, -71.734),
    "Braintree": (42.207, -71.000), "Brewster": (41.759, -70.083), "Bridgewater": (41.990, -70.975), "Brimfield": (42.121, -72.200),
    "Brockton": (42.083, -71.018), "Brookfield": (42.215, -72.100), "Brookline": (42.331, -71.121), "Buckland": (42.584, -72.768),
    "Burlington": (42.504, -71.195), "Cambridge": (42.373, -71.109), "Canton": (42.158, -71.144), "Carlisle": (42.530, -71.349),
    "Carver": (41.884, -70.762), "Charlemont": (42.628, -72.873), "Charlton": (42.135, -71.969), "Chatham": (41.682, -69.959),
    "Chelmsford": (42.599, -71.367), "Chelsea": (42.391, -71.032), "Cheshire": (42.561, -73.161), "Chester": (42.279, -72.934),
    "Chesterfield": (42.393, -72.839), "Chicopee": (42.148, -72.607), "Chilmark": (41.340, -70.744), "Clarksburg": (42.721, -73.090),
    "Clinton": (42.416, -71.682), "Cohasset": (42.241, -70.802), "Colrain": (42.671, -72.696), "Concord": (42.460, -71.348),
    "Conway": (42.510, -72.697), "Cummington": (42.463, -72.909), "Dalton": (42.475, -73.166), "Danvers": (42.562, -70.930),
    "Dartmouth": (41.626, -70.984), "Dedham": (42.243, -71.167), "Deerfield": (42.542, -72.604), "Dennis": (41.735, -70.193),
    "Dighton": (41.815, -71.126), "Douglas": (42.052, -71.740), "Dover": (42.245, -71.282), "Dracut": (42.668, -71.303),
    "Dudley": (42.046, -71.931), "Dunstable": (42.674, -71.488), "Duxbury": (42.041, -70.672), "East Bridgewater": (42.033, -70.959),
    "East Brookfield": (42.227, -72.045), "East Longmeadow": (42.064, -72.511), "Eastham": (41.829, -69.973), "Easthampton": (42.266, -72.673),
    "Easton": (42.029, -71.102), "Edgartown": (41.388, -70.513), "Egremont": (42.164, -73.411), "Erving": (42.597, -72.417),
    "Essex": (42.633, -70.782), "Everett": (42.408, -71.053), "Fairhaven": (41.637, -70.905), "Fall River": (41.701, -71.155),
    "Falmouth": (41.551, -70.615), "Fitchburg": (42.583, -71.802), "Florida": (42.665, -72.986), "Foxborough": (42.065, -71.248),
    "Framingham": (42.279, -71.416), "Franklin": (42.083, -71.396), "Freetown": (41.764, -71.036), "Gardner": (42.574, -71.998),
    "Georgetown": (42.723, -70.985), "Gill": (42.645, -72.502), "Gloucester": (42.615, -70.661), "Goshen": (42.441, -72.793),
    "Gosnold": (41.428, -70.923), "Grafton": (42.207, -71.683), "Granby": (42.258, -72.518), "Granville": (42.068, -72.862),
    "Great Barrington": (42.196, -73.361), "Greenfield": (42.587, -72.599), "Groton": (42.611, -71.573), "Groveland": (42.748, -71.018),
    "Hadley": (42.341, -72.588), "Halifax": (41.991, -70.863), "Hamilton": (42.630, -70.871), "Hampden": (42.062, -72.412),
    "Hancock": (42.541, -73.308), "Hanover": (42.112, -70.826), "Hanson": (42.074, -70.880), "Hardwick": (42.353, -72.193),
    "Harvard": (42.500, -71.583), "Harwich": (41.684, -70.076), "Hatfield": (42.373, -72.601), "Haverhill": (42.776, -71.077),
    "Hawley": (42.579, -72.883), "Heath": (42.668, -72.825), "Hingham": (42.241, -70.889), "Hinsdale": (42.440, -73.119),
    "Holbrook": (42.155, -71.008), "Holden": (42.351, -71.864), "Holland": (42.061, -72.158), "Holliston": (42.202, -71.424),
    "Holyoke": (42.207, -72.616), "Hopedale": (42.130, -71.542), "Hopkinton": (42.228, -71.522), "Hubbardston": (42.473, -72.007),
    "Hudson": (42.391, -71.566), "Hull": (42.302, -70.908), "Huntington": (42.235, -72.878), "Ipswich": (42.679, -70.841),
    "Kingston": (41.994, -70.725), "Lakeville": (41.839, -70.941), "Lancaster": (42.455, -71.674), "Lanesborough": (42.518, -73.235),
    "Lawrence": (42.707, -71.163), "Lee": (42.304, -73.249), "Leicester": (42.245, -71.907), "Lenox": (42.358, -73.284),
    "Leominster": (42.525, -71.759), "Leverett": (42.447, -72.504), "Lexington": (42.447, -71.227), "Leyden": (42.716, -72.619),
    "Lincoln": (42.426, -71.306), "Littleton": (42.537, -71.482), "Longmeadow": (42.049, -72.581), "Lowell": (42.633, -71.316),
    "Ludlow": (42.160, -72.474), "Lunenburg": (42.594, -71.722), "Lynn": (42.466, -70.949), "Lynnfield": (42.529, -71.031),
    "Malden": (42.425, -71.066), "Manchester": (42.573, -70.767), "Mansfield": (42.031, -71.218), "Marblehead": (42.500, -70.857),
    "Marion": (41.705, -70.762), "Marlborough": (42.345, -71.552), "Marshfield": (42.091, -70.705), "Mashpee": (41.648, -70.481),
    "Mattapoisett": (41.660, -70.814), "Maynard": (42.433, -71.450), "Medfield": (42.186, -71.306), "Medford": (42.418, -71.106),
    "Medway": (42.146, -71.397), "Melrose": (42.458, -71.065), "Mendon": (42.106, -71.551), "Merrimac": (42.833, -70.998),
    "Methuen": (42.726, -71.190), "Middleborough": (41.892, -70.911), "Middlefield": (42.348, -73.016), "Middleton": (42.594, -71.017),
    "Milford": (42.141, -71.516), "Millbury": (42.191, -71.761), "Millis": (42.165, -71.353), "Millville": (42.038, -71.581),
    "Milton": (42.249, -71.071), "Monroe": (42.716, -72.936), "Monson": (42.105, -72.316), "Montague": (42.536, -72.534),
    "Monterey": (42.179, -73.212), "Montgomery": (42.215, -72.802), "Mount Washington": (42.122, -73.435), "Nahant": (42.423, -70.923),
    "Nantucket": (41.283, -70.099), "Natick": (42.283, -71.349), "Needham": (42.280, -71.235), "New Ashford": (42.595, -73.208),
    "New Bedford": (41.636, -70.934), "New Braintree": (42.332, -72.158), "New Marlborough": (42.131, -73.265), "New Salem": (42.502, -72.332),
    "Newbury": (42.766, -70.871), "Newburyport": (42.812, -70.877), "Newton": (42.337, -71.209), "Norfolk": (42.118, -71.325),
    "North Adams": (42.700, -73.108), "North Andover": (42.695, -71.133), "North Attleborough": (41.982, -71.328), "North Brookfield": (42.268, -72.083),
    "North Reading": (42.575, -71.089), "Northampton": (42.325, -72.641), "Northborough": (42.319, -71.641), "Northbridge": (42.154, -71.650),
    "Northfield": (42.698, -72.454), "Norton": (41.966, -71.186), "Norwell": (42.161, -70.793), "Norwood": (42.194, -71.199),
    "Oak Bluffs": (41.454, -70.556), "Oakham": (42.348, -72.046), "Orange": (42.589, -72.310), "Orleans": (41.789, -69.989),
    "Otis": (42.193, -73.090), "Oxford": (42.116, -71.863), "Palmer": (42.158, -72.328), "Paxton": (42.308, -71.932),
    "Peabody": (42.527, -70.928), "Pelham": (42.392, -72.404), "Pembroke": (42.060, -70.822), "Pepperell": (42.666, -71.594),
    "Peru": (42.438, -73.045), "Petersham": (42.488, -72.186), "Phillipston": (42.553, -72.116), "Pittsfield": (42.450, -73.245),
    "Plainfield": (42.514, -72.915), "Plainville": (42.029, -71.325), "Plymouth": (41.958, -70.667), "Plympton": (41.954, -70.814),
    "Princeton": (42.449, -71.876), "Provincetown": (42.058, -70.178), "Quincy": (42.252, -71.002), "Randolph": (42.162, -71.041),
    "Raynham": (41.930, -71.037), "Reading": (42.525, -71.104), "Rehoboth": (41.840, -71.264), "Revere": (42.408, -71.011),
    "Richmond": (42.383, -73.356), "Rochester": (41.767, -70.814), "Rockland": (42.131, -70.916), "Rockport": (42.655, -70.620),
    "Rowe": (42.695, -72.899), "Rowley": (42.715, -70.878), "Royalston": (42.682, -72.186), "Russell": (42.188, -72.860),
    "Rutland": (42.368, -71.947), "Salem": (42.519, -70.896), "Salisbury": (42.841, -70.858), "Sandisfield": (42.103, -73.099),
    "Sandwich": (41.759, -70.493), "Saugus": (42.463, -71.012), "Savoy": (42.613, -72.986), "Scituate": (42.195, -70.723),
    "Seekonk": (41.821, -71.336), "Sharon": (42.124, -71.176), "Sheffield": (42.109, -73.353), "Shelburne": (42.590, -72.641),
    "Sherborn": (42.239, -71.370), "Shirley": (42.544, -71.646), "Shrewsbury": (42.295, -71.712), "Shutesbury": (42.454, -72.414),
    "Somerset": (41.765, -71.131), "Somerville": (42.387, -71.099), "South Hadley": (42.260, -72.575), "Southampton": (42.227, -72.730),
    "Southborough": (42.305, -71.530), "Southbridge": (42.075, -72.033), "Southwick": (42.054, -72.760), "Spencer": (42.242, -71.993),
    "Springfield": (42.101, -72.589), "Sterling": (42.438, -71.760), "Stockbridge": (42.282, -73.315), "Stoneham": (42.480, -71.098),
    "Stoughton": (42.125, -71.102), "Stow": (42.436, -71.504), "Sturbridge": (42.108, -72.079), "Sudbury": (42.383, -71.416),
    "Sunderland": (42.466, -72.578), "Sutton": (42.150, -71.764), "Swampscott": (42.469, -70.918), "Swansea": (41.748, -71.190),
    "Taunton": (41.900, -71.089), "Templeton": (42.556, -72.070), "Tewksbury": (42.610, -71.234), "Tisbury": (41.455, -70.612),
    "Tolland": (42.073, -73.033), "Topsfield": (42.637, -70.949), "Townsend": (42.666, -71.702), "Truro": (41.996, -70.052),
    "Tyngsborough": (42.673, -71.423), "Tyringham": (42.239, -73.203), "Upton": (42.175, -71.627), "Uxbridge": (42.077, -71.630),
    "Wakefield": (42.503, -71.072), "Wales": (42.059, -72.213), "Walpole": (42.141, -71.249), "Waltham": (42.376, -71.235),
    "Ware": (42.260, -72.241), "Wareham": (41.762, -70.716), "Warren": (42.213, -72.193), "Warwick": (42.684, -72.336),
    "Washington": (42.368, -73.118), "Watertown": (42.370, -71.183), "Wayland": (42.362, -71.361), "Webster": (42.050, -71.880),
    "Wellesley": (42.296, -71.292), "Wellfleet": (41.933, -70.033), "Wendell": (42.548, -72.396), "Wenham": (42.607, -70.892),
    "West Boylston": (42.361, -71.779), "West Bridgewater": (42.019, -71.011), "West Brookfield": (42.234, -72.143), "West Newbury": (42.798, -70.985),
    "West Springfield": (42.107, -72.620), "West Stockbridge": (42.331, -73.366), "Westborough": (42.269, -71.616), "Westfield": (42.120, -72.749),
    "Westford": (42.579, -71.439), "Westhampton": (42.302, -72.784), "Westminster": (42.545, -71.908), "Weston": (42.366, -71.303),
    "Westport": (41.623, -71.031), "Westwood": (42.222, -71.213), "Weymouth": (42.218, -70.940), "Whately": (42.434, -72.616),
    "Whitman": (42.081, -70.940), "Wilbraham": (42.122, -72.430), "Williamsburg": (42.392, -72.684), "Williamstown": (42.712, -73.203),
    "Wilmington": (42.551, -71.171), "Winchendon": (42.680, -72.046), "Winchester": (42.452, -71.137), "Windsor": (42.511, -73.056),
    "Winthrop": (42.374, -70.982), "Woburn": (42.479, -71.152), "Worcester": (42.262, -71.802), "Worthington": (42.405, -72.938),
    "Wrentham": (42.066, -71.328), "Yarmouth": (41.696, -70.228)
}

def get_stable_hash(s): return int(hashlib.md5(str(s).encode('utf-8')).hexdigest(), 16)

def get_mapped_city(city_name, valid_cities):
    if city_name in valid_cities:
        return city_name
    # TIGHTENED CUTOFF: 0.85 ensures it only catches actual typos (Bostn -> Boston)
    # and prevents matching entirely different cities (Bristol -> Boston).
    matches = difflib.get_close_matches(city_name, valid_cities, n=1, cutoff=0.85)
    if matches:
        return matches[0]
    return None

all_cities_in_data = set(data['City'].unique())
mapped_cities_in_data = {c for c in all_cities_in_data if get_mapped_city(c, ma_coords.keys())}
missing_cities = sorted(list(all_cities_in_data - mapped_cities_in_data))

if missing_cities:
    st.sidebar.divider()
    st.sidebar.warning(f"⚠️ {len(missing_cities)} Cities Unmapped")
    with st.sidebar.expander("View Missing Details"):
        for mc in missing_cities:
            st.write(f"- {mc}")

if not data.empty:
    for _, row in data.iterrows():
        raw_city = row.get('City', 'Unknown')
        h = get_stable_hash(row['Job Code'])
        
        matched_city = get_mapped_city(raw_city, ma_coords.keys())
        
        if matched_city:
            base_lat, base_lon = ma_coords[matched_city]
        else:
            city_hash = get_stable_hash(raw_city)
            base_lat = 42.2 + (city_hash % 40) / 100.0  
            base_lon = -72.5 + ((city_hash // 100) % 90) / 100.0 
        
        # TIGHT JITTER: Spreads dots safely within the actual city limits
        offset_lat = base_lat + ((h % 100) - 50) / 3000.0 
        offset_lon = base_lon + (((h // 100) % 100) - 50) / 3000.0
        
        s_lower = str(row['Status']).lower()
        if 'complete' in s_lower: fill_color = "#00E676"
        elif 'cancel' in s_lower: fill_color = "#FF3D00"
        else: fill_color = "#FFC107"
        
        border_color = "#00FFFF" if row['Battery'] else fill_color
        border_weight = 3 if row['Battery'] else 1
        
        tooltip_html = f"<div style='font-family:sans-serif; width: 160px;'><b>{row['Job Code']}</b><hr style='margin: 5px 0;'><b>Status:</b> {row['Status']}<br><b>Cost:</b> ${row['TU_Cost']:,.0f}<br><b>Battery:</b> {'Yes' if row['Battery'] else 'No'}<br><b>City:</b> {raw_city}</div>"
        
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

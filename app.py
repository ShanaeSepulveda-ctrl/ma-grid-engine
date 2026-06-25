import streamlit as st
import pandas as pd
import numpy as np
import folium
import hashlib
import difflib
from streamlit_folium import st_folium

# --- PAGE CONFIG ---
st.set_page_config(page_title="Sunrun Sales Co-Pilot", page_icon="☀️", layout="wide")
st.title("☀️ Sales Co-Pilot & Territory Intelligence")

# --- DUAL DATA ENGINE ---
@st.cache_data
def load_and_clean_data():
    # 1. Load Completed Installations (For Accurate Timelines)
    try:
        df_comp = pd.read_csv("report1782415560536.csv")
        rename_comp = {
            'Sales Rep: Manager': 'Manager',
            'Sales Person': 'Sales_Rep',
            'Utility Company': 'Utility',
            'CAP date approved': 'CAP_Date',
            'Permit Approval Date': 'Permit_Date',
            'Completion of Construction': 'Completion_Date',
            'Job Code': 'Job_Code'
        }
        df_comp = df_comp.rename(columns=rename_comp).dropna(subset=['Job_Code'])
        
        df_comp['CAP_Date'] = pd.to_datetime(df_comp['CAP_Date'], errors='coerce')
        df_comp['Permit_Date'] = pd.to_datetime(df_comp['Permit_Date'], errors='coerce')
        df_comp['Completion_Date'] = pd.to_datetime(df_comp['Completion_Date'], errors='coerce')
        
        df_comp['Cycle_CAP_to_Permit'] = (df_comp['Permit_Date'] - df_comp['CAP_Date']).dt.days
        df_comp['Cycle_Permit_to_Complete'] = (df_comp['Completion_Date'] - df_comp['Permit_Date']).dt.days
        df_comp['Total_Cycle'] = (df_comp['Completion_Date'] - df_comp['CAP_Date']).dt.days
        
        for col in ['Cycle_CAP_to_Permit', 'Cycle_Permit_to_Complete', 'Total_Cycle']:
            df_comp[col] = df_comp[col].apply(lambda x: x if pd.notnull(x) and x >= 0 else np.nan)
            
        df_comp['City'] = df_comp['City'].astype(str).str.title().str.strip()
        df_comp['Manager'] = df_comp.get('Manager', pd.Series(dtype=str)).fillna("Unassigned").astype(str)
        df_comp['Sales_Rep'] = df_comp.get('Sales_Rep', pd.Series(dtype=str)).fillna("Unknown").astype(str)
    except Exception as e:
        df_comp = pd.DataFrame() 
        
    # 2. Load Transformer Upgrades (For Map Grid Risk)
    try:
        df_tu = pd.read_csv("report1782413270280.csv")
        rename_tu = {
            'Gross Price of Sunrun Managed Electrical': 'TU_Cost',
            'Project: Service Contract: Service Contract Event: Job Code': 'Job_Code',
            'Project: Service Contract: BrightBox': 'Battery'
        }
        df_tu = df_tu.rename(columns=rename_tu)
        
        # BULLETPROOF SAFETY CHECKS (Prevents Crashes)
        if 'Job_Code' in df_tu.columns:
            df_tu = df_tu.dropna(subset=['Job_Code'])
        else:
            df_tu['Job_Code'] = "Unknown"
            
        if 'TU_Cost' in df_tu.columns:
            df_tu['TU_Cost'] = pd.to_numeric(df_tu['TU_Cost'], errors='coerce').fillna(0)
        else:
            df_tu['TU_Cost'] = 0
            
        if 'Battery' in df_tu.columns:
            df_tu['Battery'] = df_tu['Battery'].astype(str).str.strip().isin(['1', '1.0', 'True', 'Yes', 'TRUE'])
        else:
            df_tu['Battery'] = False
            
        if 'City' in df_tu.columns:
            df_tu['City'] = df_tu['City'].astype(str).str.title().str.strip()
        else:
            df_tu['City'] = "Unknown"
            
    except Exception as e:
        df_tu = pd.DataFrame()

    return df_comp, df_tu

df_comp, df_tu = load_and_clean_data()

# Check if data loaded properly
if df_tu.empty:
    st.error("⚠️ Transformer Upgrade data not found. Please ensure 'report1782413270280.csv' is in the folder. The map will be empty without it.")

# --- SIDEBAR: CLEAN SEARCH FILTERS ---
st.sidebar.header("🎯 Target Your Territory")
search_city = st.sidebar.text_input("City Lookup (For Scripts):", placeholder="e.g., Burlington")
st.sidebar.divider()

st.sidebar.header("👤 Team Search")
st.sidebar.write("Type a name to instantly filter the dashboard metrics:")
manager_search = st.sidebar.text_input("🔍 Search Manager Name:")
rep_search = st.sidebar.text_input("🔍 Search Sales Rep Name:")

# Apply the text search filters to the completed projects dataset
filtered_comp = df_comp.copy()
if manager_search and not filtered_comp.empty:
    filtered_comp = filtered_comp[filtered_comp['Manager'].str.contains(manager_search, case=False, na=False)]
if rep_search and not filtered_comp.empty:
    filtered_comp = filtered_comp[filtered_comp['Sales_Rep'].str.contains(rep_search, case=False, na=False)]

# --- KPI METRICS ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("Recent Completions", len(filtered_comp) if not filtered_comp.empty else 0)
col2.metric("Avg Days: CAP to Permit", f"{filtered_comp['Cycle_CAP_to_Permit'].mean():.0f} Days" if not filtered_comp.empty and not filtered_comp['Cycle_CAP_to_Permit'].isna().all() else "N/A")
col3.metric("Avg Days: Permit to Install", f"{filtered_comp['Cycle_Permit_to_Complete'].mean():.0f} Days" if not filtered_comp.empty and not filtered_comp['Cycle_Permit_to_Complete'].isna().all() else "N/A")
col4.metric("Active TU Risk Projects", len(df_tu) if not df_tu.empty else 0)
st.divider()

# --- DYNAMIC SALES SCRIPTS ---
st.subheader("🗣️ The Sales Co-Pilot & Value Prop")
if search_city:
    target_city = search_city.title().strip()
    
    city_comp = filtered_comp[filtered_comp['City'] == target_city] if not filtered_comp.empty else pd.DataFrame()
    city_tu = df_tu[df_tu['City'] == target_city] if not df_tu.empty else pd.DataFrame()
    
    avg_total = city_comp['Total_Cycle'].mean() if not city_comp.empty else 75
    avg_permit = city_comp['Cycle_CAP_to_Permit'].mean() if not city_comp.empty else 30
    avg_install = city_comp['Cycle_Permit_to_Complete'].mean() if not city_comp.empty else 45
    
    st.write(f"### Current Intelligence for **{target_city}**")
    
    if city_comp.empty:
        st.info(f"⚠️ No recent completed projects found for **{target_city}** with your current filters. Using standard state averages for the script.")
    else:
        st.info(f"**Historical Speed:** {avg_total:.0f} Days total ({avg_permit:.0f} days for permits + {avg_install:.0f} days for installation).")
    
    # Timeline Script Generation
    if avg_total < 60:
        st.success("🟢 **SCENARIO A: THE FAST LANE (Under 60 Days)**\nStrategy: Use speed as a competitive advantage. Build excitement and urgency to secure their spot in a fast-moving queue.")
        st.markdown(f"> \"One of the best parts about going solar here in **{target_city}** is how incredibly efficient your local utility and building departments are. We track the exact permitting speeds for every city, and right now, **{target_city}** is moving incredibly fast. \n\n> On average, we are getting systems fully approved and installed in just about **{avg_total:.0f} days**. Because the local pipeline is moving so quickly right now, the best thing we can do is get your application submitted today to lock in your spot and take full advantage of this momentum. Are you ready to get the clock started?\"")
    elif avg_total > 90:
        st.error("🔴 **SCENARIO B: THE CAUTION ZONE (Over 90 Days)**\nStrategy: Establish ultimate trust through transparency. Set realistic expectations early to prevent cancellations.")
        st.markdown(f"> \"I want to be completely transparent with you about the installation timeline. We track the permitting and utility speeds for every single city so our customers know exactly what to expect. Looking at the current data for **{target_city}**, your local building departments and utility company are currently taking longer than the state average to process solar applications.\n\n> Right now, we are seeing it take about **{avg_total:.0f} days** from the time we submit until the system is on your roof. I share this not to discourage you, but because we believe in complete honesty. You will be in a bit of a waiting game while the city does its reviews, but our team will be monitoring it daily and handling all the heavy lifting. Knowing that this is a longer process locally, does it make sense to get your application submitted right away so the countdown can officially begin?\"")
    else:
        st.warning("🟡 **SCENARIO C: THE STANDARD TIMELINE (60 - 90 Days)**\nStrategy: Set a realistic timeframe while using the AHJ review process to create urgency.")
        st.markdown(f"> \"Every city operates on its own timeline, but in **{target_city}**, we are seeing a very steady and predictable process right now. Typically, it takes us about **{avg_permit:.0f} days** to secure your building permits, and another **{avg_install:.0f} days** to get the utility approval and finish construction.\n\n> All together, we are looking at a very smooth **{avg_total:.0f} day** turnaround. The longest part of this process is simply waiting for the local inspectors and utility reviewers to stamp the paperwork. Since that timeline is out of our hands, the smartest move is to get your design submitted today so we can get your project into their queue as quickly as possible.\"")
    
    # THE SUNRUN ADVANTAGE (Grid Friction Integration)
    if not city_tu.empty:
        avg_tu_cost = city_tu['TU_Cost'].mean()
        st.error(f"⚡ **THE SUNRUN ADVANTAGE (Grid Risk Detected)**\nStrategy: Use the high rate of utility friction in this city to prove Sunrun's value as an advocate.")
        st.markdown(f"> \"I also want to let you know that in **{target_city}**, we are seeing the utility frequently require complex Transformer Upgrades to handle solar, which can cost upwards of **${avg_tu_cost:,.0f}** and cause unexpected delays. \n\n> Sunrun does absolutely everything we can to give you the smoothest experience possible. Sometimes that involves long utility timelines or high-cost scopes of work from the grid, but **Sunrun is there every single step of the way**. We handle all the hard stuff, negotiations, and heavy lifting behind the scenes to push your project forward as quickly as possible so you don't have to worry about it.\"")

else:
    st.info("👈 Enter a City in the sidebar to generate custom timeline scripts and grid risk propositions based on historical performance.")
st.divider()

# --- TIMELINE & RISK MAP ---
st.subheader("Interactive Transformer Risk Map")
st.caption("🔴 High Risk (>$10k) | 🟡 Medium Risk ($5k-$10k) | 🟢 Low Risk (<$5k) | **Cyan Border = Battery Included**")

# The map will ALWAYS render this base, even if data is missing
m = folium.Map(location=[42.60, -71.80], zoom_start=7, tiles="CartoDB dark_matter")

# City GPS Dictionary (Major Hubs + Surrounding Logic)
ma_coords = {
    "Boston": (42.360, -71.058), "Worcester": (42.262, -71.802), "Springfield": (42.101, -72.589),
    "Cambridge": (42.373, -71.109), "Lowell": (42.633, -71.316), "Brockton": (42.083, -71.018),
    "New Bedford": (41.636, -70.934), "Quincy": (42.252, -71.002), "Lynn": (42.466, -70.949),
    "Fall River": (41.701, -71.155), "Newton": (42.337, -71.209), "Somerville": (42.387, -71.099),
    "Lawrence": (42.707, -71.163), "Framingham": (42.279, -71.416), "Haverhill": (42.776, -71.077),
    "Waltham": (42.376, -71.235), "Malden": (42.425, -71.066), "Brookline": (42.331, -71.121),
    "Plymouth": (41.958, -70.667), "Medford": (42.418, -71.106), "Taunton": (41.900, -71.089),
    "Chicopee": (42.148, -72.557), "Weymouth": (42.218, -70.940), "Revere": (42.408, -71.011),
    "Peabody": (42.527, -70.928), "Methuen": (42.726, -71.190), "Billerica": (42.558, -71.268),
    "Everett": (42.408, -71.053), "Woburn": (42.479, -71.152), "Chelmsford": (42.599, -71.367),
    "Natick": (42.283, -71.349), "Lexington": (42.447, -71.227), "Dracut": (42.668, -71.303)
}

def get_stable_hash(s): return int(hashlib.md5(str(s).encode('utf-8')).hexdigest(), 16)
def get_mapped_city(city_name, valid_cities):
    if city_name in valid_cities: return city_name
    matches = difflib.get_close_matches(city_name, valid_cities, n=1, cutoff=0.85)
    return matches[0] if matches else None

if not df_tu.empty:
    city_avg_times = df_comp.groupby('City')['Total_Cycle'].mean().to_dict() if not df_comp.empty else {}

    for _, row in df_tu.iterrows():
        raw_city = row.get('City', 'Unknown')
        h = get_stable_hash(row['Job_Code'])
        matched_city = get_mapped_city(raw_city, ma_coords.keys())
        
        if matched_city:
            base_lat, base_lon = ma_coords[matched_city]
        else:
            city_hash = get_stable_hash(raw_city)
            base_lat = 42.2 + (city_hash % 40) / 100.0  
            base_lon = -72.5 + ((city_hash // 100) % 90) / 100.0
        
        offset_lat = base_lat + ((h % 100) - 50) / 3000.0
        offset_lon = base_lon + (((h // 100) % 100) - 50) / 3000.0
        
        cost = row['TU_Cost']
        # --- ZONING COLORS FOR TRANSFORMER UPGRADES ---
        if cost > 10000: fill_color = "#FF3D00"   # Red (High Risk Zone)
        elif cost > 5000: fill_color = "#FFC107"  # Yellow (Medium Risk Zone)
        else: fill_color = "#00E676"              # Green (Low Risk Zone)
        
        border_color = "#00FFFF" if row['Battery'] else fill_color
        border_weight = 3 if row['Battery'] else 1
        
        avg_time = city_avg_times.get(raw_city, None)
        cycle_disp = f"{avg_time:.0f} Days" if pd.notnull(avg_time) else "No History"
        
        tooltip_html = f"<div style='font-family:sans-serif; width: 175px;'><b>{raw_city}</b><hr style='margin: 5px 0;'><b>Active TU Cost:</b> ${cost:,.0f}<br><b>Hist. Timeline:</b> {cycle_disp}</div>"
        
        folium.CircleMarker([offset_lat, offset_lon], radius=5, color=border_color, weight=border_weight, fill=True, fill_color=fill_color, fill_opacity=0.7, tooltip=folium.Tooltip(tooltip_html)).add_to(m)

# Force the map to fill the container properly
st_folium(m, use_container_width=True, height=500)

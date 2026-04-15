import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import numpy as np

# --- DASHBOARD CONFIGURATION ---
st.set_page_config(page_title="Executive Grid Engine 14.0", page_icon="🦄", layout="wide")

st.title("⚡ National Grid Resilience Engine (Executive Dashboard)")
st.markdown("Dynamic capacity mapping and financial exposure tracking powered by live CRM data.")
st.divider()

# --- THE DYNAMIC DATA INGESTION ENGINE ---
@st.cache_data
def load_and_clean_data():
    try:
        # Load your exact CSV
        df = pd.read_csv("ma_grid_data.csv")
        
        # 1. Clean the City Column
        if 'City' not in df.columns:
            st.error("Missing 'City' column in CSV.")
            return pd.DataFrame()
        
        df['City'] = df['City'].astype(str).str.title().str.strip()

        # 2. Clean the Financials (Total Cost)
        if 'Total Cost' in df.columns:
            # Strip out dollar signs, commas, and convert to numbers
            df['TU_Cost'] = df['Total Cost'].astype(str).replace(r'[\$,]', '', regex=True)
            df['TU_Cost'] = pd.to_numeric(df['TU_Cost'], errors='coerce').fillna(0)
        else:
            st.error("Missing 'Total Cost' column.")
            df['TU_Cost'] = 0.0

        # 3. Clean Utility Company
        if 'Utility Company' not in df.columns:
            df['Utility Company'] = "Unknown Utility"
            
        # 4. Clean System Size DC
        if 'System Size DC' in df.columns:
            df['System_Size'] = pd.to_numeric(df['System Size DC'], errors='coerce').fillna(0)
        else:
            df['System_Size'] = 0.0

        # 5. Geocoding: Map Cities to Coordinates so Folium works
        ma_coords = {
            "Springfield": (42.101, -72.589), "Ludlow": (42.160, -72.474), "Lynn": (42.466, -70.949),
            "Amherst": (42.380, -72.523), "Boston": (42.360, -71.058), "Worcester": (42.262, -71.802),
            "Westfield": (42.120, -72.749), "Fitchburg": (42.583, -71.802), "Brockton": (42.083, -71.018),
            "Acton": (42.485, -71.432), "Pittsfield": (42.450, -73.245), "Fall River": (41.701, -71.155),
            "New Bedford": (41.636, -70.934), "Northampton": (42.325, -72.641)
        }
        
# If city is known, use coords. If unknown, mathematically scatter it inside MA borders.
        # Wrapped city in str() to prevent TypeErrors on blank cells.
        def get_lat(city):
            return ma_coords.get(city, 42.0 + (hash(str(city)) % 100) / 100.0 * 0.7)
            
        def get_lon(city):
            return ma_coords.get(city, -73.0 + (hash(str(city) + "lon") % 100) / 100.0 * 2.0)
            
        df['Lat'] = df['City'].apply(get_lat)
        df['Lon'] = df['City'].apply(get_lon)
        
        return df

    except FileNotFoundError:
        st.error("🚨 'ma_grid_data.csv' not found! Please ensure your downloaded Google Sheet is in the exact same folder as this app.py file.")
        return pd.DataFrame()

# Execute the loader
grid_data = load_and_clean_data()

# --- EXECUTIVE FINANCIAL KPI PANEL ---
if not grid_data.empty:
    total_tu_invoiced = grid_data['TU_Cost'].sum()
    avg_tu_cost = grid_data[grid_data['TU_Cost'] > 0]['TU_Cost'].mean() if not grid_data[grid_data['TU_Cost'] > 0].empty else 0
    total_projects_flagged = len(grid_data[grid_data['TU_Cost'] > 0])
    
    st.error(f"🚨 **EXECUTIVE BRIEFING: Verified Utility Upgrade Exposure: ${total_tu_invoiced:,.2f}**")
    
    col_kpi1, col_kpi2, col_kpi3 = st.columns(3)
    col_kpi1.metric("Total High-Friction Projects", total_projects_flagged)
    col_kpi2.metric("Average TU Invoice (When Flagged)", f"${avg_tu_cost:,.2f}")
    col_kpi3.metric("Highest Saturated Utility", grid_data['Utility Company'].mode()[0])
    st.divider()

# --- TARGET MARKET SELECTION ---
st.subheader("1. Location Selection & System Design")
col1, col2 = st.columns([1, 2])

# Dynamically populate the dropdown with EVERY City from your sheet
available_cities = ["Statewide Overview"]
if not grid_data.empty:
    # Forces everything to text, drops blanks, removes 'nan' strings, and sorts safely
    unique_cities = sorted([str(city) for city in grid_data['City'].dropna().unique() if str(city).lower() != 'nan'])
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

# --- THE DYNAMIC MAP ENGINE ---
st.divider()
st.subheader("🗺️ Live Grid Saturation Map")
st.caption("Visualizing utility infrastructure capacity based on your verified pipeline data.")

start_lat, start_lon, start_zoom = 42.25, -71.80, 8
if target_found and not grid_data[grid_data['City'] == selected_city].empty:
    target_row = grid_data[grid_data['City'] == selected_city].iloc[0]
    start_lat, start_lon, start_zoom = target_row['Lat'], target_row['Lon'], 12

ma_map = folium.Map(location=[start_lat, start_lon], zoom_start=start_zoom, tiles="CartoDB dark_matter")

if not grid_data.empty:
    # Aggregate data by City for map plotting
    city_summary = grid_data.groupby('City').agg({
        'TU_Cost': 'sum',
        'Utility Company': 'first',
        'System_Size': 'mean',
        'Lat': 'first',
        'Lon': 'first'
    }).reset_index()
    
    for _, row in city_summary.iterrows():
        # Heatmap logic based on actual financial thresholds
        if row['TU_Cost'] > 10000:
            risk_color = "#ff4b4b" # Red
        elif row['TU_Cost'] > 0:
            risk_color = "#ffc107" # Yellow
        else:
            risk_color = "#00cc66" # Green
            
        folium.CircleMarker(
            location=[row['Lat'], row['Lon']],
            radius=8 if row['TU_Cost'] == 0 else 14, # Make expensive cities larger
            popup=f"<b>{row['City']}</b><br>Utility: {row['Utility Company']}<br>Historical TU Exposure: ${row['TU_Cost']:,.2f}",
            color=risk_color,
            fill=True,
            fill_color=risk_color,
            fill_opacity=0.7,
            weight=1
        ).add_to(ma_map)

# Targeting Reticle
if target_found:
    folium.Circle(location=[start_lat, start_lon], radius=3000, color="white", weight=3, dash_array='5, 5', fill=False).add_to(ma_map)

st_folium(ma_map, width=1200, height=500, returned_objects=[])

# --- ENGINE LOGIC & TIMELINE EXPOSURE ---
if target_found:
    total_kw = existing_kw + new_kw
    is_complex_review = total_kw > 25.0
    
    city_history = grid_data[grid_data['City'] == selected_city]
    historical_exposure = city_history['TU_Cost'].mean() if not city_history.empty else 0
    avg_system_size = city_history['System_Size'].mean() if not city_history.empty else 0
    
    # Updated Timeline Logic per your instructions
    if is_complex_review or historical_exposure > 5000:
        timeline_status = "4-8 Weeks (Transformer Review)"
        risk_level = "Red"
    elif historical_exposure > 0:
        timeline_status = "2-4 Weeks (Moderate / Average)"
        risk_level = "Yellow"
    else:
        timeline_status = "1-2 Weeks (Simplified)"
        risk_level = "Green"

    st.divider()
    st.subheader("2. Capacity & Expectation Diagnostics")

    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Total Parcel AC", f"{total_kw} kW", "- Complex Review Triggered" if is_complex_review else "+ Simplified Track", delta_color="inverse")
    col_b.metric("Installation Approval Timeline", timeline_status)
    col_c.metric("Est. Sunk Cost Risk", f"${historical_exposure + 2000:,.0f}" if historical_exposure > 0 else "$2,000", "High Risk" if risk_level == "Red" else "Acceptable", delta_color="inverse")

    # --- EXPECTATION SETTING & PATHWAYS ---
    st.subheader("3. Interconnection Feasibility & Pathway Review")

    if risk_level == "Red":
        st.warning("⚠️ **CAPACITY WARNING:** The requested system size and location historically require an extended utility transformer review (4-8 weeks).")
        st.markdown("""
        **💡 Feasibility Consultation (For Interconnection/Design Teams):**
        To mitigate delays and protect the margin, evaluate the following alternative design pathways:
        * **Export Limiting:** Can a Power Control System (PCS) be used to hard-cap export below the 25kW threshold?
        * **Non-Export Profiles:** Can the ESS be configured primarily for self-consumption?
        """)
    elif risk_level == "Yellow":
        st.info("🔄 **MODERATE REVIEW:** Moderate timelines expected (2-4 weeks). Proceed with standard engineering review while monitoring utility study queues.")
    else:
        st.success("✅ **CAPACITY OPEN:** System falls within Simplified thresholds. Expect rapid utility approval (1-2 weeks).")

st.divider()
st.caption("🔧 Powered by live 2024-2026 pipeline data. Export the latest Salesforce/CRM tracking sheet to 'ma_grid_data.csv' to update the dashboard.")

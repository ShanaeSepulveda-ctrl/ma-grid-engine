import streamlit as st
import folium
from streamlit_folium import st_folium

# --- DASHBOARD CONFIGURATION ---
st.set_page_config(page_title="MA Capacity & Timeline Engine 10.0", page_icon="🦄", layout="wide")

st.title("⚡ MA Grid Capacity & Expectation Engine (v10.0)")
st.markdown("Setting accurate timelines, capacity limits, and collaborative pathways for MA solar projects.")
st.divider()

# --- THE STATEWIDE DATABASE ---
ma_zip_db = {
    "Select a Location...": {"town": "Statewide View", "util": "All", "strictness": 0, "map": "Overview", "note": "Select a location to run capacity diagnostics.", "lat": 42.25, "lon": -71.80},
    "01119 - Springfield": {"town": "Springfield", "util": "WMECO", "strictness": 6, "map": "Red", "note": "⚠️ WMECO SATURATION: Heavy concentration of upgrade fees.", "lat": 42.115, "lon": -72.502},
    "01056 - Ludlow": {"town": "Ludlow", "util": "WMECO", "strictness": 7, "map": "Red", "note": "⚠️ WMECO SATURATION: Frequent secondary transformer upgrades.", "lat": 42.160, "lon": -72.474},
    "01904 - Lynn": {"town": "Lynn", "util": "National Grid", "strictness": 8, "map": "Red", "note": "⚠️ GRID SATURATION: High risk of upgrade fees and delays.", "lat": 42.480, "lon": -70.963},
    "01420 - Fitchburg": {"town": "Fitchburg", "util": "UNITIL", "strictness": 5, "map": "Yellow", "note": "⚠️ STUDY QUEUE: Active group study delays.", "lat": 42.583, "lon": -71.802},
    "01085 - Westfield": {"town": "Westfield", "util": "Municipal (WG&E)", "strictness": 9, "map": "Yellow", "note": "🏛️ MUNICIPAL UTILITY: Custom review required. Standard tariffs do not apply.", "lat": 42.120, "lon": -72.749},
    "01002 - Amherst": {"town": "Amherst", "util": "National Grid", "strictness": 6, "map": "Red", "note": "⚠️ SATURATION ZONE: National Grid transformers maxed out.", "lat": 42.380, "lon": -72.523},
    "01720 - Acton": {"town": "Acton", "util": "Eversource", "strictness": 9, "map": "Yellow", "note": "⚠️ SPECIALIZED CODE: Strict enforcement of NFPA 855.", "lat": 42.485, "lon": -71.432},
    "02108 - Boston": {"town": "Boston", "util": "Eversource", "strictness": 7, "map": "Green", "note": "✅ CLEAR: Standard historic district reviews apply.", "lat": 42.360, "lon": -71.058},
    "02301 - Brockton": {"town": "Brockton", "util": "National Grid", "strictness": 5, "map": "Green", "note": "✅ CLEAR: High hosting capacity available.", "lat": 42.083, "lon": -71.018},
    "01201 - Pittsfield": {"town": "Pittsfield", "util": "Eversource", "strictness": 4, "map": "Red", "note": "⚠️ RURAL FEEDER: High risk of line extension fees.", "lat": 42.450, "lon": -73.245}
}

# --- USER INPUTS ---
st.subheader("1. Location Selection & System Design")
col1, col2, col3, col4 = st.columns(4)

with col1:
    selected_option = st.selectbox("Select Target Market", list(ma_zip_db.keys()))
    target = ma_zip_db[selected_option]
    target_found = selected_option != "Select a Location..."

with col2:
    existing_kw = st.number_input("Existing Solar (kW AC)", min_value=0.0, max_value=50.0, value=0.0, step=0.5)

with col3:
    new_kw = st.number_input("New Solar (kW AC)", min_value=0.0, max_value=50.0, value=10.0, step=0.5)

with col4:
    battery_kw = st.number_input("New Battery (kW AC)", min_value=0.0, max_value=50.0, value=5.0, step=0.5)

# --- THE OMNISCIENT MAP ENGINE ---
st.divider()
st.subheader("🗺️ Public Grid Saturation Map")
st.caption("Visualizing utility infrastructure capacity across Massachusetts.")

start_lat = target["lat"] if target_found else 42.25
start_lon = target["lon"] if target_found else -71.80
start_zoom = 12 if target_found else 8

ma_map = folium.Map(location=[start_lat, start_lon], zoom_start=start_zoom, tiles="CartoDB dark_matter")
color_dict = {"Red": "#ff4b4b", "Yellow": "#ffc107", "Green": "#00cc66", "Overview": "#ffffff"}

for key, data in ma_zip_db.items():
    if key == "Select a Location...": continue
    folium.CircleMarker(
        location=[data["lat"], data["lon"]],
        radius=12,
        popup=f"<b>{data['town']}</b><br>Utility: {data['util']}<br>Risk: {data['map']}",
        color=color_dict[data["map"]],
        fill=True,
        fill_color=color_dict[data["map"]],
        fill_opacity=0.6,
        weight=1
    ).add_to(ma_map)

if target_found:
    folium.Circle(
        location=[target["lat"], target["lon"]],
        radius=2000,
        color="white",
        weight=3,
        dash_array='5, 5',
        fill=False,
        tooltip=f"TARGET: {target['town']}"
    ).add_to(ma_map)

st_folium(ma_map, width=1200, height=450, returned_objects=[])

# --- ENGINE LOGIC & EXPOSURE ---
if target_found:
    total_kw = existing_kw + new_kw + battery_kw
    is_complex_review = total_kw > 25.0
    is_red = target["map"] == "Red"
    tu_prob = 0.90 if is_red else (0.50 if target["map"] == "Yellow" else 0.10)
    pto_days = 300 if is_red else (120 if target["map"] == "Yellow" else 45)
    
    # Updated Math Logic based on $6,200 TU Average
    sunk_cost_exposure = (tu_prob * 6200) + 2000

    st.divider()
    st.subheader("2. Capacity & Timeline Expectations")
    st.code(target['note'], language="markdown")

    col_a, col_b, col_c, col_d = st.columns(4)
    col_a.metric("Total Parcel AC", f"{total_kw} kW", "- Complex Review Triggered" if is_complex_review else "+ Simplified Track", delta_color="inverse")
    col_b.metric("Expected CAP-to-PTO", f"{pto_days} Days")
    col_c.metric("Upgrade Fee Risk", f"{int(tu_prob * 100)}%", "🔴" if is_red else ("🟡" if target["map"]=="Yellow" else "🟢"))
    col_d.metric("Est. Financial Exposure", f"${sunk_cost_exposure:,.0f}", "High Risk" if sunk_cost_exposure > 5000 else "Acceptable", delta_color="inverse")

    with st.expander("📊 Data Methodology (How is this calculated?)"):
        st.markdown("""
        **Financial Exposure Calculation:**
        * **Baseline Sunk OpEx:** `$2,000` (Site Survey + Design Labor + CX Administration).
        * **Transformer Upgrade (TU) Average:** `$6,200` (Derived from internal YTD 2026 utility invoices).
        * **Formula:** `(TU Average × Grid Saturation Probability) + Baseline Sunk OpEx`.
        """)

    # --- EXPECTATION SETTING & PATHWAYS ---
    st.subheader("3. Interconnection Path Forward")

    if target["util"] == "Municipal (WG&E)":
        st.info("🏛️ **MUNICIPAL GUIDANCE:** This parcel falls under a municipal utility. Ensure the system size aligns with local WG&E net-metering caps to set proper customer timeline expectations.")
    elif is_complex_review or is_red:
        st.warning("⚠️ **CAPACITY WARNING:** The requested system size and location have a high probability of exceeding grid hosting capacity, extending timelines to 300+ days.")
        st.markdown("""
        **💡 Alternative Pathways for Interconnection/Design Teams:**
        If the standard design is flagged for a costly utility upgrade, the following strategies have historically improved PTO success rates in this territory:
        * **Export Limiting:** Utilizing a Power Control System (PCS) to hard-cap export below the 25kW threshold.
        * **Non-Export Profiles:** Configuring the ESS primarily for self-consumption.
        """)
    else:
        st.success("✅ **CAPACITY OPEN:** System falls within Simplified thresholds. Set standard operational timelines for the customer.")
else:
    st.info("👆 Select a Target Market from the dropdown above to run localized capacity diagnostics.")
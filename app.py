import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import math

# --- DASHBOARD CONFIGURATION ---
st.set_page_config(page_title="MA Grid Intelligence", page_icon="📊", layout="wide")

st.title("MA Resilience & Strategy Dashboard")
st.markdown("Enterprise pipeline intelligence, capacity mapping, and financial exposure tracking.")
st.divider()

# --- THE LIVE AUTOMATED INGESTION ENGINE (Refreshes every 1 Hour) ---
@st.cache_data(ttl=3600)
def process_data():
    live_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTt6IQA-3Ee4DrzafeU8MZntRmF37kg83tFfw4f24ci-tFtvRxT0goN-KqyuA9IqP_Catwo3dw3hdpx/pub?gid=0&single=true&output=csv"
    
    try:
        df = pd.read_csv(live_url)
        
        # 1. Status Extraction
        if 'Project Status:' in df.columns:
            df['Status'] = df['Project Status:'].astype(str).str.title().str.strip()
        elif 'Project Status' in df.columns:
            df['Status'] = df['Project Status'].astype(str).str.title().str.strip()
        elif 'Status' in df.columns:
            df['Status'] = df['Status'].astype(str).str.title().str.strip()
        else:
            df['Status'] = "Unknown"
            
        # 2. City Extraction
        if 'Jurisdiction: Jurisdiction Name' in df.columns:
            df['City'] = df['Jurisdiction: Jurisdiction Name'].astype(str).str.replace('MA-TOWN ', '', case=False).str.replace('MA-CITY ', '', case=False)
        elif 'City' not in df.columns:
            df['City'] = "Unknown"
        
        # 3. Cost Extraction
        if 'Line Item Price to Customer' in df.columns:
            df['TU_Cost'] = df['Line Item Price to Customer']
        elif 'TU Invoice Amount:' in df.columns:
            df['TU_Cost'] = df['TU Invoice Amount:']
        elif 'TU Invoice' in df.columns:
            df['TU_Cost'] = df['TU Invoice']
        elif 'Total Cost' in df.columns:
            df['TU_Cost'] = df['Total Cost']
        else:
            df['TU_Cost'] = 0.0
        
        # 4. Utility Extraction
        if 'Utility' in df.columns and 'Utility Company' not in df.columns:
            df['Utility Company'] = df['Utility']
            
        # 5. SMART ZIP CODE EXTRACTION
        if 'Zip Code:' in df.columns:
            df['Zip Code'] = df['Zip Code:']
        elif 'Zip Code' in df.columns:
            pass
        elif 'Full Address' in df.columns:
            df['Zip Code'] = df['Full Address'].astype(str).str.extract(r'(\b\d{5}\b)')
        elif 'Address' in df.columns:
            df['Zip Code'] = df['Address'].astype(str).str.extract(r'(\b\d{5}\b)')
        else:
            df['Zip Code'] = "Unknown"
            
        # 6. Battery Extraction
        if 'BrightBox' in df.columns:
            df['Battery'] = df['BrightBox'].astype(str).str.upper().isin(['TRUE', 'YES', 'Y', '1'])
        else:
            df['Battery'] = False
            
        # 7. TEMPORAL EXTRACTION
        if 'Year Invoiced' in df.columns:
            df['Year'] = df['Year Invoiced'].astype(str).str.replace('.0', '', regex=False).str.strip()
        elif 'Permit Approval Date' in df.columns:
            df['Year'] = df['Permit Approval Date'].astype(str).str.extract(r'(\d{4})')
        elif 'Created Date' in df.columns:
            df['Year'] = df['Created Date'].astype(str).str.extract(r'(\d{4})')
        elif 'Project Year' in df.columns:
            df['Year'] = df['Project Year'].astype(str).str.replace('.0', '', regex=False).str.strip()
        else:
            df['Year'] = "All Time"

    except Exception as e:
        st.error(f"Live Data Bridge Offline: Unable to read Google Sheets URL. ({e})")
        return pd.DataFrame(), []

    df_master = df.copy()
    
    # --- SANITIZATION & CLEANING ---
    df_master['Job Code'] = df_master['Job Code'].astype(str).str.strip() if 'Job Code' in df_master.columns else "Unknown"
    
    # === THE SMART DEDUPLICATION ENGINE ===
    df_master = df_master.drop_duplicates()
    df_valid_jobs = df_master[df_master['Job Code'] != 'Unknown'].drop_duplicates(subset=['Job Code'], keep='first')
    df_unknown_jobs = df_master[df_master['Job Code'] == 'Unknown']
    df_master = pd.concat([df_valid_jobs, df_unknown_jobs], ignore_index=True)

    # The Smart Zip Code Parser
    def clean_zip(z):
        z_str = str(z).split('.')[0] 
        digits = ''.join(filter(str.isdigit, z_str))
        if len(digits) == 4: return "0" + digits
        elif len(digits) >= 5: return digits[:5]
        else: return "Unknown"
            
    df_master['Zip Code'] = df_master['Zip Code'].apply(clean_zip)

    if 'City' not in df_master.columns: df_master['City'] = "Unknown"
    df_master = df_master.dropna(subset=['City'])
    df_master['City'] = df_master['City'].astype(str).str.title().str.strip()
    df_master = df_master[df_master['City'].str.lower() != 'nan'] 
    df_master = df_master[df_master['City'] != ''] 
    
    df_master['Status'] = df_master['Status'].replace({'Nan': 'Unknown', 'None': 'Unknown'})
    df_master['Year'] = df_master['Year'].replace({'Nan': 'All Time', 'nan': 'All Time', 'None': 'All Time'})
    df_master['Year'] = df_master['Year'].fillna('All Time')
    
    if 'Battery' not in df_master.columns: df_master['Battery'] = False

    if 'TU_Cost' in df_master.columns:
        df_master['TU_Cost'] = df_master['TU_Cost'].astype(str).replace(r'[\$,]', '', regex=True)
        df_master['TU_Cost'] = pd.to_numeric(df_master['TU_Cost'], errors='coerce').fillna(0.0)
    else:
        df_master['TU_Cost'] = 0.0

    df_master['Utility Company'] = df_master['Utility Company'] if 'Utility Company' in df_master.columns else "Unknown Utility"
        
    def map_utility(u):
        u = str(u).upper()
        if 'WMECO' in u: return 'WMECO'
        if 'GRID' in u: return 'National Grid'
        if 'EVER' in u: return 'Eversource'
        if 'UNIT' in u: return 'UNITIL'
        return u.title()
    df_master['Utility Company'] = df_master['Utility Company'].apply(map_utility)

    # --- PRECISION GEOCODING (Master Database) ---
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
        "Worcester": (42.262, -71.802), "Dalton": (42.475, -73.166), "Whitman": (42.081, -70.940), "Millville": (42.039, -71.580),
        "Lee": (42.304, -73.249), "Hadley": (42.341, -72.588), "Southbridge": (42.075, -72.033), "Athol": (42.595, -72.226),
        "Southampton": (42.227, -72.730), "Lanesborough": (42.518, -73.228), "Francestown": (42.985, -71.815), "Barre": (42.421, -72.106), 
        "Millbury": (42.191, -71.761), "South Deerfield": (42.482, -72.604), "Westminster": (42.545, -71.908), "Sutton": (42.150, -71.763), 
        "Lakeville": (41.838, -70.938), "Auburn": (42.193, -71.835), "Avon": (42.131, -71.042), "Rehoboth": (41.840, -71.264), 
        "West Brookfield": (42.235, -72.140), "Turners Falls": (42.604, -72.555), "Ashby": (42.678, -71.819), "Norton": (41.966, -71.186), 
        "Deerfield": (42.543, -72.605), "Wilbraham": (42.122, -72.434), "Feeding Hills": (42.069, -72.678), "Gardner": (42.574, -71.998), 
        "Webster": (42.050, -71.880), "Hopedale": (42.128, -71.539), "Southwick": (42.055, -72.769), "Townsend": (42.668, -71.701), 
        "Whately": (42.430, -72.617), "Becket": (42.332, -73.080), "Monson": (42.104, -72.316), "Hanover": (42.115, -70.826), 
        "Charlton": (42.134, -71.970), "Newburyport": (42.812, -70.877), "West Bridgewater": (42.019, -71.005), "Lunenburg": (42.595, -71.722),
        "Greenfield": (42.587, -72.599), "Montgomery": (42.231, -72.802), "Hinsdale": (42.441, -73.123), "Erving": (42.599, -72.417), 
        "Longmeadow": (42.049, -72.581), "West Townsend": (42.668, -71.745), "Emmaus": (40.539, -75.496), "Clinton": (42.416, -71.682), 
        "Dudley": (42.046, -71.931), "Rutland": (42.368, -71.947), "Uxbridge": (42.077, -71.630), "Rockport": (42.655, -70.620), 
        "Wrentham": (42.066, -71.328), "North Andover": (42.695, -71.133), "Upton": (42.176, -71.627), "Spencer": (42.243, -71.989), 
        "Sturbridge": (42.108, -72.080), "Leicester": (42.245, -71.905), "Oxford": (42.115, -71.864), "Whitinsville": (42.112, -71.651), 
        "Shirley": (42.539, -71.648), "Brookfield": (42.215, -72.102), "Northbridge": (42.150, -71.650), "West Newbury": (42.798, -70.992), 
        "Plainville": (42.002, -71.332), "South Easton": (42.015, -71.096), "Norwell": (42.161, -70.793), "Holbrook": (42.155, -71.008), 
        "Swansea": (41.746, -71.192), "North Dighton": (41.859, -71.121), "Dighton": (41.819, -71.121), "E Bridgewtr": (42.033, -70.959), 
        "Woonsocket": (42.002, -71.514), "Mendon": (42.102, -71.554), "Blackstone": (42.016, -71.538), "New Braintree": (42.302, -72.152), 
        "Douglas": (42.042, -71.743), "North Brookfield": (42.266, -72.082), "Foxboro": (42.065, -71.248), "Pembroke": (42.059, -70.821), 
        "Westport": (41.621, -71.066), "Scituate": (42.195, -70.726), "Rockland": (42.128, -70.916), "Winchendon": (42.684, -72.046), 
        "Boyertown": (40.332, -75.635), "Lyndeborough": (42.894, -71.758), "East Lyme": (41.353, -72.222), "Bloomfield Village": (41.826, -72.730), 
        "Meriden": (41.538, -72.807), "Maynard": (42.433, -71.455), "Otis": (42.193, -73.090), "Bedford": (42.490, -71.276), 
        "Sandown": (42.926, -71.189), "Jaffrey": (42.813, -72.022), "Rochester": (41.765, -70.925), "E Falmouth": (41.583, -70.551), 
        "Carver": (41.883, -70.763), "Hyannis": (41.652, -70.282), "Holliston": (42.203, -71.425)
    }
    
    df_master['Lat'] = df_master['City'].apply(lambda c: ma_coords[c][0] if c in ma_coords else None)
    df_master['Lon'] = df_master['City'].apply(lambda c: ma_coords[c][1] if c in ma_coords else None)
    
    missing_cities = df_master[df_master['Lat'].isna()]['City'].unique().tolist()
    
    return df_master, missing_

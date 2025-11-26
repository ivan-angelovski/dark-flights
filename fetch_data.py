import requests
import pandas as pd
import json
import os

# 1. SETUP
OS_USER = os.environ.get('OPENSKY_USERNAME')
OS_PASS = os.environ.get('OPENSKY_PASSWORD')
TG_TOKEN = os.environ.get('TELEGRAM_TOKEN')
TG_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

def get_database():
    print("⏳ Downloading Database...")
    url = "https://raw.githubusercontent.com/sdr-enthusiasts/plane-alert-db/main/plane-alert-db.csv"
    try:
        df = pd.read_csv(url)
        df.columns = df.columns.str.strip()
        print(f"   Raw Database Rows: {len(df)}")
        
        cat_col = next((c for c in df.columns if 'Category' in c), '#Category')
        icao_col = '$ICAO'
        owner_col = '$Operator'
        
        # FILTER: Widen the net to ensure we get results
        target_cats = ['Dictator Alert', 'Oligarchs', 'Putin\'s War', 'Hired Gun', 'Nuclear', 'Government', 'Military']
        df_filtered = df[df[cat_col].isin(target_cats)].copy()
        df_filtered[icao_col] = df_filtered[icao_col].astype(str).str.strip().str.lower()
        
        print(f"   Filtered Watchlist Size: {len(df_filtered)}")
        return df_filtered, cat_col, icao_col, owner_col
    except Exception as e:
        print(f"❌ Database Error: {e}")
        return None, None, None, None

def run_scan():
    df, cat_col, icao_col, owner_col = get_database()
    if df is None: return

    watchlist = dict(zip(df[icao_col], df[owner_col]))
    cat_map = dict(zip(df[icao_col], df[cat_col]))
    
    # --- LOAD HISTORY ---
    plane_history = {}
    try:
        if os.path.exists('planes.json'):
            with open('planes.json', 'r') as f:
                old_data = json.load(f)
                for p in old_data:
                    if 'trace' in p:
                        plane_history[p['hex']] = p['trace']
    except Exception as e:
        print(f"⚠️ Could not load history: {e}")

    print("📡 Scanning OpenSky API...")
    url = "https://opensky-network.org/api/states/all"
    
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    
    try:
        auth = (OS_USER, OS_PASS) if OS_USER else None
        response = requests.get(url, auth=auth, headers=headers, timeout=30)
        
        if response.status_code != 200:
            print(f"❌ API Failed: {response.status_code}")
            return

        data = response.json()
        states = data.get('states', [])
        
        if not states: states = []
        print(f"   Total Planes in Sky: {len(states)}")

    except Exception as e:
        print(f"❌ Connection Error: {e}")
        return

    hits = []
    for v in states:
        icao = str(v[0]).strip().lower()
        if icao in watchlist:
            # History Logic
            trace = plane_history.get(icao, [])
            if v[6] is not None and v[5] is not None:
                if not trace or (trace[-1][0] != v[6] or trace[-1][1] != v[5]):
                    trace.append([v[6], v[5]])
            trace = trace[-50:] # Keep last 50 points

            hits.append({
                "hex": icao,
                "name": watchlist[icao],
                "category": cat_map[icao],
                "callsign": v[1].strip(),
                "lon": v[5],
                "lat": v[6],
                "alt": v[7],
                "velocity": v[9],
                "heading": v[10],
                "trace": trace
            })

    print(f"✅ MATCHES FOUND: {len(hits)}")

    with open('planes.json', 'w') as f:
        json.dump(hits, f, indent=2)

if __name__ == "__main__":
    run_scan()

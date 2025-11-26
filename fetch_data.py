import requests
import pandas as pd
import json
import os
import sys

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
    
    print("📡 Scanning OpenSky API...")
    url = "https://opensky-network.org/api/states/all"
    
    # CRITICAL FIX: Add User-Agent to avoid being blocked as a bot
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    
    try:
        auth = (OS_USER, OS_PASS) if OS_USER else None
        if not OS_USER:
            print("⚠️  No Credentials Found. Running in Anonymous Mode (Low Limits).")
            
        response = requests.get(url, auth=auth, headers=headers, timeout=30)
        
        print(f"   API Status Code: {response.status_code}")
        
        if response.status_code != 200:
            print(f"❌ API Failed. Response: {response.text}")
            return

        data = response.json()
        states = data.get('states', [])
        
        # If we get None instead of a list, handle it
        if states is None:
            states = []

        print(f"   Total Planes in Sky: {len(states)}")
        
        if len(states) == 0:
            print("⚠️  API returned 0 states. (Possible Rate Limit or IP Block)")
            return 

    except Exception as e:
        print(f"❌ Connection Error: {e}")
        return

    hits = []
    for v in states:
        icao = str(v[0]).strip().lower()
        if icao in watchlist:
            hits.append({
                "hex": icao,
                "name": watchlist[icao],
                "category": cat_map[icao],
                "callsign": v[1].strip(),
                "lon": v[5],
                "lat": v[6],
                "alt": v[7],
                "velocity": v[9],
                "heading": v[10]
            })

    print(f"✅ MATCHES FOUND: {len(hits)}")

    # Write to file
    with open('planes.json', 'w') as f:
        json.dump(hits, f, indent=2)

if __name__ == "__main__":
    run_scan()

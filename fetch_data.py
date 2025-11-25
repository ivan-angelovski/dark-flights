import requests
import pandas as pd
import json
import os
from datetime import datetime

# 1. SETUP
OS_USER = os.environ.get('OPENSKY_USERNAME')
OS_PASS = os.environ.get('OPENSKY_PASSWORD')
TG_TOKEN = os.environ.get('TELEGRAM_TOKEN')
TG_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

# 2. LOAD DATABASE
def get_database():
    url = "[https://raw.githubusercontent.com/sdr-enthusiasts/plane-alert-db/main/plane-alert-db.csv](https://raw.githubusercontent.com/sdr-enthusiasts/plane-alert-db/main/plane-alert-db.csv)"
    try:
        df = pd.read_csv(url)
        df.columns = df.columns.str.strip()
        
        # Dynamic column finding
        cat_col = next((c for c in df.columns if 'Category' in c), '#Category')
        icao_col = '$ICAO'
        owner_col = '$Operator'
        
        # Filter for interesting categories
        # You can add 'Military' or 'Government' here if you want more dots
        target_cats = ['Dictator Alert', 'Oligarchs', 'Putin\'s War', 'Hired Gun', 'Nuclear', 'Government']
        
        df_filtered = df[df[cat_col].isin(target_cats)].copy()
        df_filtered[icao_col] = df_filtered[icao_col].astype(str).str.strip().str.lower()
        
        return df_filtered, cat_col, icao_col, owner_col
    except Exception as e:
        print(f"Error loading DB: {e}")
        return None, None, None, None

# 3. FETCH & FILTER
def run_scan():
    df, cat_col, icao_col, owner_col = get_database()
    if df is None: return

    watchlist = dict(zip(df[icao_col], df[owner_col]))
    cat_map = dict(zip(df[icao_col], df[cat_col]))
    
    # OpenSky API
    url = "[https://opensky-network.org/api/states/all](https://opensky-network.org/api/states/all)"
    try:
        # Use auth if available, otherwise anonymous
        auth = (OS_USER, OS_PASS) if OS_USER else None
        response = requests.get(url, auth=auth, timeout=20)
        data = response.json()
        states = data.get('states', [])
    except Exception as e:
        print(f"API Error: {e}")
        return

    hits = []
    if states:
        for v in states:
            icao = str(v[0]).strip().lower()
            if icao in watchlist:
                # Data Structure for Frontend
                plane = {
                    "hex": icao,
                    "name": watchlist[icao],
                    "category": cat_map[icao],
                    "callsign": v[1].strip(),
                    "lon": v[5],
                    "lat": v[6],
                    "alt": v[7],
                    "velocity": v[9],
                    "heading": v[10],
                    "last_seen": v[3]
                }
                hits.append(plane)

                # TELEGRAM ALERT (Simple logic: Alert on everything found)
                # In a real app, you'd check a history file to avoid duplicate alerts
                if TG_TOKEN:
                    send_alert(plane)

    # Save to JSON
    with open('planes.json', 'w') as f:
        json.dump(hits, f, indent=2)
    print(f"Updated planes.json with {len(hits)} aircraft.")

def send_alert(plane):
    # Only alert for High Priority categories to avoid spam
    if plane['category'] not in ['Dictator Alert', 'Nuclear', 'Putin\'s War']:
        return

    msg = (f"🚨 <b>{plane['category']} Detected!</b>\n"
           f"✈️ {plane['name']}\n"
           f"📍 <a href='[https://www.google.com/maps?q=](https://www.google.com/maps?q=){plane['lat']},{plane['lon']}'>Map Link</a>")
    
    url = f"[https://api.telegram.org/bot](https://api.telegram.org/bot){TG_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": TG_CHAT_ID, "text": msg, "parse_mode": "HTML"})
    except:
        pass

if __name__ == "__main__":
    run_scan()

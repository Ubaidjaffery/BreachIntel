#!/usr/bin/env python3
"""
Process Excel datasets into JSON for BreachIntel.
Usage: python3 scripts/process_data.py
"""
import pandas as pd
import json
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def process():
    tac_path = os.path.join(BASE, 'THREAT_ACTOR_CLAIMS06052026.xlsx')
    master_path = os.path.join(BASE, 'Master_Data.xlsx')
    out_data = os.path.join(BASE, 'data')
    os.makedirs(out_data, exist_ok=True)

    print("Reading TAC dataset...")
    df = pd.read_excel(tac_path)
    df['breach_date_iso'] = pd.to_datetime(df['Breach Date'], format='%m/%d/%Y %I:%M %p', errors='coerce')
    df['Country'] = df['Country'].str.replace('\xa0', ' ', regex=False).str.strip()
    df = df.fillna('')
    df['id'] = range(1, len(df) + 1)

    # Load master data for enrichment
    master_lookup = {}
    try:
        master = pd.read_excel(master_path)
        for _, row in master.iterrows():
            domain = str(row.get('Victim Domain', '')).strip().lower()
            if domain:
                master_lookup[domain] = {
                    'attack': str(row.get('Attack pattern', ''))[:400],
                    'vulns': str(row.get('Exploited Vulnerabilities', '')),
                    'remediation': str(row.get('Remediation', ''))[:400],
                }
        print(f"Loaded {len(master_lookup)} enrichment records from Master Data")
    except Exception as e:
        print(f"Warning: Could not load Master Data: {e}")

    records = []
    for _, row in df.iterrows():
        domain = str(row['Victim Domain']).strip().lower()
        enrichment = master_lookup.get(domain, {})
        rec = {
            'id': int(row['id']),
            'Category': str(row['Category']),
            'Breach Date': str(row['Breach Date']),
            'Victim Name': str(row['Victim Name']),
            'Victim Domain': str(row['Victim Domain']),
            'Threat Actor': str(row['Threat Actor']),
            'Country': str(row['Country']),
            'Region': str(row['Region']),
            'Industry': str(row['Industry']),
            'source': 'tac',
            'breach_date_iso': row['breach_date_iso'].isoformat() if pd.notna(row['breach_date_iso']) and str(row['breach_date_iso']) != 'NaT' else '',
        }
        rec.update(enrichment)
        records.append(rec)

    out_json = os.path.join(out_data, 'tac_data.json')
    with open(out_json, 'w') as f:
        json.dump(records, f, separators=(',', ':'))
    print(f"Saved {len(records)} records → {out_json} ({os.path.getsize(out_json)/1024/1024:.1f} MB)")

    # Stats
    cats = df['Category'].value_counts().to_dict()
    top_industries = df['Industry'].replace('', 'Unknown').value_counts().head(20).to_dict()
    top_actors = df['Threat Actor'].replace('', 'Unknown').value_counts().head(50).to_dict()
    top_countries = df['Country'].replace('', 'Unknown').value_counts().head(30).to_dict()
    top_regions = df['Region'].replace('', 'Unknown').value_counts().head(15).to_dict()
    df['month'] = df['breach_date_iso'].dt.strftime('%Y-%m')
    monthly = df[df['month'].notna() & (df['month'] != 'NaT')]['month'].value_counts().sort_index().tail(24).to_dict()

    stats = {
        'total': len(df),
        'categories': cats,
        'topIndustries': top_industries,
        'topActors': top_actors,
        'topCountries': top_countries,
        'topRegions': top_regions,
        'monthly': monthly,
    }
    stats_path = os.path.join(out_data, 'stats.json')
    with open(stats_path, 'w') as f:
        json.dump(stats, f, indent=2)
    print(f"Stats saved → {stats_path}")

if __name__ == '__main__':
    process()

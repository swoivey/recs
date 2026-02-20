#!/usr/bin/env python3
"""
BAMBA — Fetch real coordinates for all venues via Google Places API
Uses Text Search to find each venue and extract lat/lon.
Then patches bamba-bali-data.js with coordinates.
"""

import json
import os
import re
import time
import urllib.request
import urllib.parse
import urllib.error

API_KEY = "AIzaSyDHDy0tcyIEH1opqMrAfrZUCDORgEExvec"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "bamba-bali-data.js")
COORDS_FILE = os.path.join(BASE_DIR, "bamba-coords.json")

def search_place_coords(name, area="Bali"):
    """Use Text Search to find a place and get its coordinates."""
    url = "https://places.googleapis.com/v1/places:searchText"

    data = json.dumps({
        "textQuery": f"{name}, {area}, Bali, Indonesia",
        "maxResultCount": 1
    }).encode('utf-8')

    req = urllib.request.Request(url, data=data, method='POST')
    req.add_header('Content-Type', 'application/json')
    req.add_header('X-Goog-Api-Key', API_KEY)
    req.add_header('X-Goog-FieldMask', 'places.id,places.displayName,places.location')

    try:
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read().decode())
            if result.get('places') and len(result['places']) > 0:
                place = result['places'][0]
                loc = place.get('location', {})
                return {
                    'lat': loc.get('latitude'),
                    'lng': loc.get('longitude'),
                    'placeName': place.get('displayName', {}).get('text', '')
                }
    except urllib.error.HTTPError as e:
        print(f"  ⚠ Search failed for {name}: {e.code} {e.read().decode()[:200]}")
    except Exception as e:
        print(f"  ⚠ Search error for {name}: {e}")
    return None

def parse_venues():
    """Parse venue IDs, names and areas from bamba-bali-data.js."""
    with open(DATA_FILE, 'r') as f:
        content = f.read()

    venues = []
    # Split into venue blocks by looking for id: patterns
    blocks = re.split(r'\n  \{', content)
    for block in blocks:
        id_match = re.search(r'id:\s*"([^"]+)"', block)
        name_match = re.search(r'name:\s*"([^"]+)"', block)
        area_match = re.search(r'area:\s*"([^"]+)"', block)
        if id_match and name_match:
            venues.append({
                'id': id_match.group(1),
                'name': name_match.group(1),
                'area': area_match.group(1) if area_match else 'Bali'
            })
    return venues

def main():
    print("🌴 BAMBA Coordinate Fetcher")
    print("=" * 50)

    venues = parse_venues()
    print(f"Found {len(venues)} venues\n")

    # Load existing coords if any (to resume)
    coords = {}
    if os.path.exists(COORDS_FILE):
        with open(COORDS_FILE, 'r') as f:
            coords = json.load(f)
        print(f"Loaded {len(coords)} existing coordinates\n")

    success = 0
    fail = 0

    for i, venue in enumerate(venues):
        vid = venue['id']
        name = venue['name']
        area = venue['area']

        print(f"[{i+1}/{len(venues)}] {name} ({area})")

        # Skip if already have coords
        if vid in coords and coords[vid].get('lat'):
            print(f"  ✓ Already have coords: {coords[vid]['lat']:.5f}, {coords[vid]['lng']:.5f}")
            success += 1
            continue

        result = search_place_coords(name, area)

        if result and result.get('lat'):
            coords[vid] = result
            success += 1
            print(f"  ✓ {result['lat']:.5f}, {result['lng']:.5f} — {result['placeName']}")
        else:
            fail += 1
            print(f"  ✗ No coordinates found")

        # Save progress after each request
        with open(COORDS_FILE, 'w') as f:
            json.dump(coords, f, indent=2)

        time.sleep(0.3)

    print(f"\n{'=' * 50}")
    print(f"✅ Done! {success} coords found, {fail} failed")
    print(f"📄 Coords saved to: {COORDS_FILE}")

    # Now patch the data file
    print(f"\n🔧 Patching {DATA_FILE} with coordinates...")
    patch_data_file(coords)

def patch_data_file(coords):
    """Add lat/lng fields to each venue in bamba-bali-data.js."""
    with open(DATA_FILE, 'r') as f:
        content = f.read()

    patched = 0
    for vid, coord in coords.items():
        if not coord.get('lat'):
            continue

        lat = coord['lat']
        lng = coord['lng']

        # Find the venue block and add lat/lng after the mapsUrl line
        # Pattern: look for the id line, then find mapsUrl in same block
        # We'll add lat/lng after the tags line (last property before closing brace)
        pattern = rf'(id:\s*"{re.escape(vid)}".*?tags:\s*\[[^\]]*\])'
        match = re.search(pattern, content, re.DOTALL)
        if match:
            old_text = match.group(1)
            # Check if lat already exists
            if 'lat:' not in old_text:
                new_text = old_text + f',\n    lat: {lat:.6f},\n    lng: {lng:.6f}'
                content = content.replace(old_text, new_text)
                patched += 1

    with open(DATA_FILE, 'w') as f:
        f.write(content)

    print(f"✅ Patched {patched} venues with coordinates")

if __name__ == '__main__':
    main()

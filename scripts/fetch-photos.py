#!/usr/bin/env python3
"""
BAMBA — Fetch real venue photos from Google Places API
Uses Place IDs extracted from Google Maps URLs to get actual photos.
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
PHOTOS_DIR = os.path.join(BASE_DIR, "photos")
DATA_FILE = os.path.join(BASE_DIR, "bamba-bali-data.js")
PHOTO_MAP_FILE = os.path.join(BASE_DIR, "bamba-photo-map.js")

# Create photos directory
os.makedirs(PHOTOS_DIR, exist_ok=True)

def extract_place_id_from_url(url):
    """Extract the Place ID hex string from a Google Maps URL."""
    # Pattern: !1s0x...:0x...
    match = re.search(r'!1s(0x[0-9a-f]+:0x[0-9a-f]+)', url)
    if match:
        return match.group(1)
    return None

def extract_coords_from_url(url):
    """Extract coordinates from a dropped pin URL."""
    match = re.search(r'search/([-\d.]+),([-\d.]+)', url)
    if match:
        return float(match.group(1)), float(match.group(2))
    return None, None

def search_place_by_name(name, area="Bali"):
    """Use Text Search to find a place and get its Place ID."""
    query = urllib.parse.quote(f"{name} {area}")
    url = f"https://places.googleapis.com/v1/places:searchText"

    data = json.dumps({
        "textQuery": f"{name}, {area}, Bali, Indonesia",
        "maxResultCount": 1
    }).encode('utf-8')

    req = urllib.request.Request(url, data=data, method='POST')
    req.add_header('Content-Type', 'application/json')
    req.add_header('X-Goog-Api-Key', API_KEY)
    req.add_header('X-Goog-FieldMask', 'places.id,places.displayName,places.photos')

    try:
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read().decode())
            if result.get('places') and len(result['places']) > 0:
                place = result['places'][0]
                return place
    except urllib.error.HTTPError as e:
        print(f"  ⚠ Search failed for {name}: {e.code} {e.read().decode()[:200]}")
    except Exception as e:
        print(f"  ⚠ Search error for {name}: {e}")
    return None

def get_place_details(place_id_hex):
    """Use the old-style ftid lookup via Text Search."""
    # The hex IDs from Maps URLs need to be looked up via text search
    # as they're not standard Place IDs for the new API
    return None

def get_photo_url(photo_name, max_width=800):
    """Get the actual photo URL from a photo resource name."""
    url = f"https://places.googleapis.com/v1/{photo_name}/media?maxWidthPx={max_width}&key={API_KEY}"
    return url

def download_photo(photo_url, filepath):
    """Download a photo to disk."""
    try:
        req = urllib.request.Request(photo_url)
        with urllib.request.urlopen(req) as resp:
            # Follow redirect to get actual image
            with open(filepath, 'wb') as f:
                f.write(resp.read())
            return True
    except Exception as e:
        print(f"  ⚠ Download failed: {e}")
        return False

def parse_data_file():
    """Parse the JS data file to extract venue info."""
    with open(DATA_FILE, 'r') as f:
        content = f.read()

    venues = []
    # Extract each venue object
    # Find all id, name, area, mapsUrl pairs
    id_pattern = re.compile(r'id:\s*"([^"]+)"')
    name_pattern = re.compile(r'name:\s*"([^"]+)"')
    area_pattern = re.compile(r'area:\s*"([^"]+)"')
    url_pattern = re.compile(r'mapsUrl:\s*"([^"]+)"')

    # Split by venue blocks
    blocks = content.split('{')
    for block in blocks:
        id_match = id_pattern.search(block)
        name_match = name_pattern.search(block)
        area_match = area_pattern.search(block)
        url_match = url_pattern.search(block)

        if id_match and name_match and url_match:
            venues.append({
                'id': id_match.group(1),
                'name': name_match.group(1),
                'area': area_match.group(1) if area_match else 'Bali',
                'mapsUrl': url_match.group(1)
            })

    return venues

def main():
    print("🌴 BAMBA Photo Fetcher")
    print("=" * 50)

    venues = parse_data_file()
    print(f"Found {len(venues)} venues in data file\n")

    photo_map = {}
    success_count = 0
    fail_count = 0

    for i, venue in enumerate(venues):
        vid = venue['id']
        name = venue['name']
        area = venue['area']
        photo_path = os.path.join(PHOTOS_DIR, f"{vid}.jpg")

        print(f"[{i+1}/{len(venues)}] {name} ({area})")

        # Skip if photo already downloaded
        if os.path.exists(photo_path) and os.path.getsize(photo_path) > 1000:
            print(f"  ✓ Already have photo")
            photo_map[vid] = f"photos/{vid}.jpg"
            success_count += 1
            continue

        # Search for the place using Text Search
        place = search_place_by_name(name, area)

        if place and place.get('photos') and len(place['photos']) > 0:
            photo_name = place['photos'][0]['name']
            photo_url = get_photo_url(photo_name)

            if download_photo(photo_url, photo_path):
                photo_map[vid] = f"photos/{vid}.jpg"
                success_count += 1
                print(f"  ✓ Photo saved")
            else:
                fail_count += 1
                print(f"  ✗ Failed to download photo")
        else:
            fail_count += 1
            print(f"  ✗ No photos found")

        # Rate limit: small delay between requests
        time.sleep(0.3)

    # Write photo map as JS file
    js_content = f"// Auto-generated photo map — {success_count} photos\n"
    js_content += f"// Generated: {time.strftime('%Y-%m-%d %H:%M')}\n"
    js_content += "const BAMBA_PHOTOS = " + json.dumps(photo_map, indent=2) + ";\n"

    with open(PHOTO_MAP_FILE, 'w') as f:
        f.write(js_content)

    print(f"\n{'=' * 50}")
    print(f"✅ Done! {success_count} photos downloaded, {fail_count} failed")
    print(f"📁 Photos saved to: {PHOTOS_DIR}")
    print(f"📄 Photo map saved to: {PHOTO_MAP_FILE}")

if __name__ == '__main__':
    main()

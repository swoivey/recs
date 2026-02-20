#!/usr/bin/env python3
"""
BAMBA — Fetch multiple photos per venue from Google Places API
Downloads up to 5 extra gallery photos per venue.
Keeps existing primary photos, adds gallery photos as vid-1.jpg, vid-2.jpg, etc.
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
PROGRESS_FILE = os.path.join(BASE_DIR, "gallery-progress.json")

MAX_GALLERY = 5  # extra photos per venue (on top of the primary)

os.makedirs(PHOTOS_DIR, exist_ok=True)

def search_place_by_name(name, area="Bali"):
    """Use Text Search to find a place and get its photos."""
    url = "https://places.googleapis.com/v1/places:searchText"
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
                return result['places'][0]
    except urllib.error.HTTPError as e:
        print(f"  ⚠ Search failed: {e.code} {e.read().decode()[:200]}")
    except Exception as e:
        print(f"  ⚠ Search error: {e}")
    return None

def download_photo(photo_name, filepath, max_width=800):
    """Download a photo from Google Places API."""
    url = f"https://places.googleapis.com/v1/{photo_name}/media?maxWidthPx={max_width}&key={API_KEY}"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as resp:
            with open(filepath, 'wb') as f:
                f.write(resp.read())
            size = os.path.getsize(filepath)
            if size < 500:
                os.remove(filepath)
                return False
            return True
    except Exception as e:
        print(f"  ⚠ Download failed: {e}")
        return False

def parse_data_file():
    """Parse the JS data file to extract venue info."""
    with open(DATA_FILE, 'r') as f:
        content = f.read()

    venues = []
    id_pattern = re.compile(r'id:\s*"([^"]+)"')
    name_pattern = re.compile(r'name:\s*"([^"]+)"')
    area_pattern = re.compile(r'area:\s*"([^"]+)"')

    blocks = content.split('{')
    for block in blocks:
        id_match = id_pattern.search(block)
        name_match = name_pattern.search(block)
        area_match = area_pattern.search(block)
        if id_match and name_match:
            venues.append({
                'id': id_match.group(1),
                'name': name_match.group(1),
                'area': area_match.group(1) if area_match else 'Bali',
            })
    return venues

def main():
    print("🌴 BAMBA Gallery Photo Fetcher")
    print("=" * 50)

    venues = parse_data_file()
    print(f"Found {len(venues)} venues\n")

    # Load progress to resume interrupted runs
    progress = {}
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, 'r') as f:
            progress = json.load(f)
        print(f"Resuming — {len(progress)} venues already processed\n")

    total_new = 0
    total_skipped = 0

    for i, venue in enumerate(venues):
        vid = venue['id']
        name = venue['name']
        area = venue['area']

        print(f"[{i+1}/{len(venues)}] {name} ({area})")

        # Skip if already processed this venue's gallery
        if vid in progress:
            count = progress[vid]
            print(f"  ✓ Already have {count} gallery photos")
            total_skipped += 1
            continue

        # Search for the place
        place = search_place_by_name(name, area)

        if not place or not place.get('photos'):
            print(f"  ✗ No photos available")
            progress[vid] = 0
            _save_progress(progress)
            time.sleep(0.3)
            continue

        photos = place['photos']
        # Skip the first photo (we already have it as the primary)
        gallery_photos = photos[1:MAX_GALLERY+1]

        if not gallery_photos:
            print(f"  — Only 1 photo available (primary only)")
            progress[vid] = 0
            _save_progress(progress)
            time.sleep(0.3)
            continue

        downloaded = 0
        for idx, photo in enumerate(gallery_photos, start=1):
            photo_name = photo['name']
            filepath = os.path.join(PHOTOS_DIR, f"{vid}-{idx}.jpg")

            if os.path.exists(filepath) and os.path.getsize(filepath) > 500:
                downloaded += 1
                continue

            if download_photo(photo_name, filepath):
                downloaded += 1
            time.sleep(0.15)  # gentle rate limit between photo downloads

        print(f"  ✓ {downloaded} gallery photos saved")
        total_new += downloaded
        progress[vid] = downloaded
        _save_progress(progress)

        time.sleep(0.3)  # rate limit between venue API calls

    # Now build the updated photo map
    print(f"\n{'=' * 50}")
    print(f"Building photo map...")
    build_photo_map(venues)

    print(f"\n✅ Done! {total_new} new gallery photos downloaded, {total_skipped} venues skipped (already done)")

def _save_progress(progress):
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress, f, indent=2)

def build_photo_map(venues):
    """Build the photo map JS file with primary + gallery photos."""
    photo_map = {}
    total_gallery = 0

    for venue in venues:
        vid = venue['id']
        primary = os.path.join(PHOTOS_DIR, f"{vid}.jpg")

        if os.path.exists(primary) and os.path.getsize(primary) > 500:
            # Collect gallery photos
            gallery = []
            for idx in range(1, MAX_GALLERY + 1):
                gpath = os.path.join(PHOTOS_DIR, f"{vid}-{idx}.jpg")
                if os.path.exists(gpath) and os.path.getsize(gpath) > 500:
                    gallery.append(f"photos/{vid}-{idx}.jpg")

            if gallery:
                # Store as array: [primary, gallery1, gallery2, ...]
                photo_map[vid] = [f"photos/{vid}.jpg"] + gallery
                total_gallery += len(gallery)
            else:
                # Backward compatible: just the primary as string
                photo_map[vid] = f"photos/{vid}.jpg"

    # Write JS file
    total_primary = len(photo_map)
    js_content = f"// Auto-generated photo map — {total_primary} venues, {total_gallery} gallery photos\n"
    js_content += f"// Generated: {time.strftime('%Y-%m-%d %H:%M')}\n"
    js_content += "const BAMBA_PHOTOS = " + json.dumps(photo_map, indent=2) + ";\n"

    with open(PHOTO_MAP_FILE, 'w') as f:
        f.write(js_content)

    print(f"📄 Photo map: {total_primary} venues, {total_gallery} gallery photos")
    print(f"📁 Saved to: {PHOTO_MAP_FILE}")

if __name__ == '__main__':
    main()

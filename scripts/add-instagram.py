#!/usr/bin/env python3
"""Add Instagram handles to bamba-bali-data.js venues."""
import re

DATA_FILE = "/Users/harryharrison/Library/CloudStorage/Dropbox/Bamba (Tanner Project)/bamba-bali-data.js"

# Instagram handles mapping (venue-id -> handle)
INSTAGRAM = {
    "ulu-001": "avlibali",
    "ulu-002": None,
    "ulu-003": "yuki.uluwatu",
    "ulu-004": "zali.uluwatu",
    "ulu-005": "kalauluwatu",
    "ulu-006": "lolascantina.bali",
    "ulu-007": "manauluwatu",
    "ulu-008": "bythecliff.bali",
    "ulu-009": None,
    "ulu-010": "drifterbali",
    "ulu-011": "palapa_uluwatu",
    "ulu-012": None,
    "ulu-013": None,
    "ulu-014": "bartolo.bali",
    "ulu-015": "dum.dum.bali",
    "ulu-016": None,
    "ulu-017": "cashewcanggu",
    "ulu-018": None,
    "ulu-019": "singlefinbali",
    "ulu-020": "ondosbali",
    "ulu-021": "savannabalangan",
    "ulu-022": "rockbarbali",
    "ulu-023": "sundays.beach",
    "ulu-024": "kliffbali",
    "ulu-025": None,
    "ulu-026": "theungasan",
    "ulu-027": "sulubancliff",
    "ulu-028": None,
    "ulu-029": None,
    "ulu-030": None,
    "ulu-031": None,

    "cgu-001": "theblackpigbali",
    "cgu-002": "fishtrapbali",
    "cgu-003": "lunartacos",
    "cgu-004": "naluboweats",
    "cgu-005": "kintamanicoffee",
    "cgu-006": None,
    "cgu-007": "littleflinders_",
    "cgu-008": "pinchbali",
    "cgu-009": "ishibali",
    "cgu-010": "themiddlebali",
    "cgu-011": None,
    "cgu-012": "warunglocal",
    "cgu-013": "creamybali",
    "cgu-014": "pomodorobali",
    "cgu-015": "streatcoffee",
    "cgu-016": "nuddle.bali",
    "cgu-017": "shakeahand.bali",
    "cgu-018": None,
    "cgu-019": "thecanggumarket",
    "cgu-020": "milkandmadubali",
    "cgu-021": "cocobali",
    "cgu-022": "ji.restaurant",
    "cgu-023": "luiginiscanggu",
    "cgu-024": "tacosbali",
    "cgu-025": "vuelvecarolina.bali",
    "cgu-026": "crumbsbali",
    "cgu-027": "wategardens",
    "cgu-028": "heywrld",
    "cgu-029": "mrssippybali",
    "cgu-030": "theoldmans",
    "cgu-031": "sandbarbali",
    "cgu-032": "labrisabali",
    "cgu-033": "motelmexicola",
    "cgu-034": "thebillboardbali",
    "cgu-035": "tamanbhagawan",
    "cgu-036": "atlasbeachfest",
    "cgu-037": "potatoheadbali",
    "cgu-038": "finnsbeachclub",

    "ubd-001": None,
    "ubd-002": "kafeinubud",
    "ubd-003": "makanplacexubud",
    "ubd-004": None,
    "ubd-005": "copperubud",
    "ubd-006": None,
    "ubd-007": "daumpohbali",
    "ubd-008": "r4d_room4dessert",
    "ubd-009": None,
    "ubd-010": None,
    "ubd-011": None,
    "ubd-012": None,
    "ubd-013": "boomboomubud",
    "ubd-014": None,
    "ubd-015": None,
    "ubd-016": "mozaicrestaurantubud",
    "ubd-017": "aperitifbali",
    "ubd-018": None,

    "pam-001": None,
    "pam-002": None,
    "pam-003": None,
}

with open(DATA_FILE, 'r') as f:
    content = f.read()

count = 0
for vid, handle in INSTAGRAM.items():
    if handle is None:
        continue

    # Find this venue's lng line and add instagram after it
    # Pattern: lng: X.XXXXXX (within this venue's block)
    pattern = rf'(id:\s*"{re.escape(vid)}".*?lng:\s*[-\d.]+)'
    match = re.search(pattern, content, re.DOTALL)
    if match:
        old_text = match.group(1)
        # Only add if not already there
        if 'instagram:' not in old_text:
            # Check if there's already an instagram field after lng (in the broader block)
            broader = content[match.start():match.start()+len(old_text)+100]
            if 'instagram:' not in broader:
                new_text = old_text + f',\n    instagram: "{handle}"'
                content = content.replace(old_text, new_text, 1)
                count += 1
                print(f"  ✓ {vid}: @{handle}")
            else:
                print(f"  - {vid}: already has instagram")
        else:
            print(f"  - {vid}: already has instagram")
    else:
        print(f"  ✗ {vid}: not found in data file")

with open(DATA_FILE, 'w') as f:
    f.write(content)

print(f"\n✅ Added {count} Instagram handles")

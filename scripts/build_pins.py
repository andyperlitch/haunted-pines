#!/usr/bin/env python3
"""Build pins.json (public) from the sign-up form's published CSV.

Only the street address (column 2) is used. Nothing else from the form is
ever written out. Geocodes with the US Census geocoder (keyless), falling
back to Nominatim/OpenStreetMap, and caches results in geocache.json so
re-runs only look up new addresses.

Usage: CSV_URL=... python3 scripts/build_pins.py
"""
import csv, difflib, io, json, math, os, re, sys, time, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_PATH = os.path.join(ROOT, "geocache.json")
PINS_PATH = os.path.join(ROOT, "pins.json")
CITY = "Scotts Valley, CA 95066"
CENTER = (37.040, -122.037)   # Whispering Pines / Twin Pines
MAX_KM = 5.0
UA = "HauntedPinesMap/1.0 (https://hauntedpines.com; andyperlitch@gmail.com)"

# Streets in/near the neighborhood, used to fix typos ("pinconedive").
# Order matters for ties: when a suffix is missing, the earlier entry wins.
KNOWN_STREETS = [
    "Whispering Pines Dr", "Pinecone Dr", "Twin Pines Dr", "Tan Oak Dr",
    "Estrella Dr", "Lockewood Ln", "Spreading Oak Dr", "Silverwood Dr",
    "Sugar Pine Rd", "Whispering Pines Ct", "Pinecone Ln", "Royal Oak Ct",
    "Bay Laurel Ct", "Pine Trl", "Locke Way", "Blueberry Dr", "Blueberry Ct",
    "Honeysuckle Ln", "Bluebonnet Ln", "Azalea Trl", "Columbine Trl",
    "Silver Birch Ln", "Carriage Ln", "Sterling Ln", "Worth Ln",
    "Hidden Glen Dr", "Canepa Dr", "Navigator Dr", "Kings Village Rd",
    "Graham Hill Rd", "Mount Hermon Rd",
]
SUFFIXES = {
    "drive": "Dr", "dr": "Dr", "street": "St", "st": "St", "lane": "Ln",
    "ln": "Ln", "court": "Ct", "ct": "Ct", "road": "Rd", "rd": "Rd",
    "avenue": "Ave", "ave": "Ave", "way": "Way", "circle": "Cir", "cir": "Cir",
    "place": "Pl", "pl": "Pl", "trail": "Trl", "trl": "Trl", "loop": "Loop",
}
LONG = {v: k for k, v in SUFFIXES.items() if len(k) > 3}
LONG.update({"Way": "way", "Loop": "loop"})


def squash(s):
    return re.sub(r"[^a-z]", "", s.lower())


def street_forms(street):
    *name, suf = street.split()
    name = "".join(name).lower()
    return [name, name + suf.lower(), name + LONG.get(suf, suf.lower())]


def normalize(raw):
    """'804 pinconedive ' -> '804 Pinecone Dr'. Returns None if unusable."""
    s = re.sub(r"\s+", " ", (raw or "").replace(".", " ").replace(",", " ")).strip()
    m = re.match(r"^(\d+[A-Za-z]?)\s*(.*)$", s)
    if not m or not m.group(2):
        return None
    num, rest = m.group(1).upper(), m.group(2)
    key = squash(rest)
    best, score = None, 0.0
    for st in KNOWN_STREETS:
        r = max(difflib.SequenceMatcher(None, key, f).ratio() for f in street_forms(st))
        if r > score + 1e-9:
            best, score = st, r
    if best and score >= 0.8:
        return f"{num} {best}"
    words = rest.split()
    if words and words[-1].lower() in SUFFIXES:
        words[-1] = SUFFIXES[words[-1].lower()]
    return f"{num} " + " ".join(w if w in SUFFIXES.values() else w.capitalize() for w in words)


def km(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (*a, *b))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 12742 * math.asin(math.sqrt(h))


def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.load(r)


def census(addr):
    q = urllib.parse.urlencode({"address": f"{addr}, {CITY}", "benchmark": "Public_AR_Current", "format": "json"})
    d = get_json("https://geocoding.geo.census.gov/geocoder/locations/onelineaddress?" + q)
    for m in d["result"]["addressMatches"]:
        return m["coordinates"]["y"], m["coordinates"]["x"], "census"
    return None


def nominatim(addr):
    time.sleep(1.1)  # usage policy: max 1 req/s
    q = urllib.parse.urlencode({"street": addr, "city": "Scotts Valley", "state": "CA",
                                "postalcode": "95066", "country": "us", "format": "json", "limit": 1})
    d = get_json("https://nominatim.openstreetmap.org/search?" + q)
    if d:
        return float(d[0]["lat"]), float(d[0]["lon"]), "nominatim"
    return None


def geocode(addr):
    for fn in (census, nominatim):
        try:
            res = fn(addr)
        except Exception as e:  # network hiccup: try the next service
            print(f"  {fn.__name__} error for {addr!r}: {e}", file=sys.stderr)
            continue
        if res and km(CENTER, res[:2]) <= MAX_KM:
            return res
        if res:
            print(f"  {fn.__name__} result for {addr!r} is {km(CENTER, res[:2]):.1f} km away; ignoring", file=sys.stderr)
    return None


def main():
    url = os.environ.get("CSV_URL")
    if not url:
        sys.exit("CSV_URL is not set")
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        text = r.read().decode("utf-8-sig")
    rows = list(csv.reader(io.StringIO(text)))[1:]
    addrs = []
    for row in rows:
        a = normalize(row[1] if len(row) > 1 else "")
        if a and a not in addrs:
            addrs.append(a)
    print(f"{len(rows)} responses, {len(addrs)} unique addresses")

    cache = json.load(open(CACHE_PATH)) if os.path.exists(CACHE_PATH) else {}
    pins, failed = [], []
    for a in addrs:
        if a not in cache:
            res = geocode(a)
            if res:
                cache[a] = {"lat": round(res[0], 6), "lng": round(res[1], 6), "source": res[2]}
                print(f"  geocoded {a} via {res[2]}")
        if a in cache:
            pins.append({"address": a, "lat": cache[a]["lat"], "lng": cache[a]["lng"]})
        else:
            failed.append(a)

    pins.sort(key=lambda p: (p["address"].split(" ", 1)[1], int(re.match(r"\d+", p["address"]).group())))
    with open(CACHE_PATH, "w") as f:
        json.dump(dict(sorted(cache.items())), f, indent=1)
        f.write("\n")
    with open(PINS_PATH, "w") as f:
        json.dump({"count": len(pins), "pins": pins}, f, indent=1)
        f.write("\n")
    print(f"{len(pins)} pins written")
    if failed:
        print("Could not geocode: " + "; ".join(failed))


if __name__ == "__main__":
    main()

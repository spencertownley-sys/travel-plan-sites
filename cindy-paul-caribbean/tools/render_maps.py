"""Render static basemap images for every entry in trip.MAPS.

Tiles: OpenStreetMap standard tiles (map data © OpenStreetMap contributors).
Fetched once and cached, per the OSM tile usage policy.
Output: ../maps/<id>.jpg and ../maps/meta.json (projection info used by build.py).
Tiles are cached in ./.tilecache (git-ignored).
"""
import json, math, os, sys, time, urllib.request
from PIL import Image, ImageEnhance

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from trip import MAPS  # noqa: E402

OUT = os.path.join(HERE, "..", "maps")
CACHE = os.path.join(HERE, ".tilecache")
TILE = 256
URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
UA = "family-trip-microsite/1.0 (static render)"


def world_px(lat, lon, z):
    n = TILE * 2 ** z
    x = (lon + 180.0) / 360.0 * n
    s = math.sin(math.radians(lat))
    y = (0.5 - math.log((1 + s) / (1 - s)) / (4 * math.pi)) * n
    return x, y


def tile(z, x, y):
    path = os.path.join(CACHE, f"{z}_{x}_{y}.png")
    if not os.path.exists(path):
        url = URL.format(z=z, x=x, y=y)
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        for attempt in range(4):
            try:
                data = urllib.request.urlopen(req, timeout=30).read()
                break
            except Exception as e:  # noqa: BLE001
                if attempt == 3:
                    raise
                time.sleep(1 + attempt)
        with open(path, "wb") as f:
            f.write(data)
        time.sleep(0.15)
    return Image.open(path).convert("RGB")


def render(mid, spec):
    s, w, n, e = spec["bbox"]
    maxw = spec.get("maxw", 1200)
    # largest zoom whose crop fits within maxw px wide (and 1.6x that tall)
    z = 1
    for zz in range(1, 18):
        x0, y0 = world_px(n, w, zz)
        x1, y1 = world_px(s, e, zz)
        if (x1 - x0) <= maxw and (y1 - y0) <= maxw * 1.6:
            z = zz
    x0, y0 = world_px(n, w, z)
    x1, y1 = world_px(s, e, z)
    x0, y0, x1, y1 = int(x0), int(y0), int(math.ceil(x1)), int(math.ceil(y1))
    W, H = x1 - x0, y1 - y0
    img = Image.new("RGB", (W, H))
    for ty in range(y0 // TILE, (y1 - 1) // TILE + 1):
        for tx in range(x0 // TILE, (x1 - 1) // TILE + 1):
            img.paste(tile(z, tx % (2 ** z), ty), (tx * TILE - x0, ty * TILE - y0))
    # soften the basemap so route lines and markers stand out
    img = ImageEnhance.Color(img).enhance(0.7)
    img = Image.blend(img, Image.new("RGB", img.size, (255, 255, 255)), 0.12)
    img.save(os.path.join(OUT, f"{mid}.jpg"), quality=80, optimize=True, progressive=True)
    print(f"{mid:12s} z={z} {W}x{H}")
    return {"z": z, "x0": x0, "y0": y0, "w": W, "h": H}


def main():
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(CACHE, exist_ok=True)
    only = set(sys.argv[1:])
    meta_path = os.path.join(OUT, "meta.json")
    meta = json.load(open(meta_path)) if os.path.exists(meta_path) else {}
    for mid, spec in MAPS.items():
        if only and mid not in only:
            continue
        meta[mid] = render(mid, spec)
    meta = {k: v for k, v in meta.items() if k in MAPS}
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=1, sort_keys=True)


if __name__ == "__main__":
    main()

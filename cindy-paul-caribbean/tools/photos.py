"""Resize the downloaded Wikimedia Commons photos into ../photos/ and keep their credits.

    python3 tools/photos.py /path/to/research/photos
Reads <src>/manifest.json, writes photos/<id>-1400.jpg and photos/<id>-700.jpg,
and tools/media/photos.json (credits used by build.py).
"""
import json, os, sys
from PIL import Image, ImageOps

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "photos")


def main(src):
    man = json.load(open(os.path.join(src, "manifest.json")))
    os.makedirs(OUT, exist_ok=True)
    credits = {}
    for pid, m in man.items():
        path = os.path.join(src, m["file"])
        if not os.path.exists(path):
            continue
        im = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
        for w in (1400, 700):
            if im.width > w:
                r = im.resize((w, round(im.height * w / im.width)), Image.LANCZOS)
            else:
                r = im
            r.save(os.path.join(OUT, f"{pid}-{w}.jpg"), quality=78, optimize=True, progressive=True)
        credits[pid] = {k: m.get(k) for k in ("title", "page", "author", "license", "license_url", "caption")}
        credits[pid]["ratio"] = round(im.width / im.height, 3)
        print(pid, im.size)
    with open(os.path.join(HERE, "media", "photos.json"), "w") as f:
        json.dump(credits, f, indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main(sys.argv[1])

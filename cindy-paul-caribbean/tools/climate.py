"""Compute January weather averages for each port from Open-Meteo's historical data.

Writes tools/media/climate.json. Run once (results don't change much year to year):
    python3 tools/climate.py
Data: Open-Meteo (https://open-meteo.com), ERA5 reanalysis and marine archive, CC BY 4.0.
"""
import json, os, sys, time, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from trip import PORTS  # noqa: E402

YEARS = range(2016, 2026)
SEA_YEARS = range(2023, 2026)
UA = {"User-Agent": "family-trip-microsite/1.0"}


def get(url, params):
    q = url + "?" + urllib.parse.urlencode(params)
    for i in range(8):
        try:
            return json.load(urllib.request.urlopen(urllib.request.Request(q, headers=UA), timeout=60))
        except Exception:  # noqa: BLE001
            time.sleep(5 + 5 * i)
    raise RuntimeError("failed: " + q)


def january(lat, lon):
    hi, lo, wet, n = [], [], 0, 0
    for y in YEARS:
        d = get("https://archive-api.open-meteo.com/v1/archive", {
            "latitude": lat, "longitude": lon, "start_date": f"{y}-01-01", "end_date": f"{y}-01-31",
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
            "temperature_unit": "fahrenheit", "timezone": "America/Barbados"})["daily"]
        hi += [x for x in d["temperature_2m_max"] if x is not None]
        lo += [x for x in d["temperature_2m_min"] if x is not None]
        for p in d["precipitation_sum"]:
            if p is not None:
                n += 1
                wet += p >= 1.0
        time.sleep(0.3)
    sst = []
    for dlat, dlon in [(0, -0.06), (0.04, -0.08), (-0.05, -0.1), (0, 0.08)]:
        for y in SEA_YEARS:
            m = get("https://marine-api.open-meteo.com/v1/marine", {
                "latitude": lat + dlat, "longitude": lon + dlon, "start_date": f"{y}-01-01", "end_date": f"{y}-01-31",
                "hourly": "sea_surface_temperature", "timezone": "America/Barbados"})
            sst += [x for x in (m.get("hourly") or {}).get("sea_surface_temperature", []) if x is not None]
        if sst:
            break
    return {
        "high_f": round(sum(hi) / len(hi)), "low_f": round(sum(lo) / len(lo)),
        "rain_pct": round(100 * wet / n), "sea_f": round(sum(sst) / len(sst) * 9 / 5 + 32) if sst else None,
    }


if __name__ == "__main__":
    path = os.path.join(HERE, "media", "climate.json")
    out = json.load(open(path)) if os.path.exists(path) else {}
    for k, (name, lat, lon) in PORTS.items():
        if k in out:
            continue
        out[k] = january(lat, lon)
        print(k, out[k], flush=True)
        with open(path, "w") as f:  # save as we go so a dropped connection doesn't lose work
            json.dump(out, f, indent=1)

"""Build cindy-paul-caribbean/index.html from trip.py and the rendered maps.

    python3 tools/build.py
"""
import datetime as dt
import html
import json
import math
import re
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import trip  # noqa: E402
from render_maps import world_px  # noqa: E402

META = json.load(open(os.path.join(ROOT, "maps", "meta.json")))
VIDEOS = json.load(open(os.path.join(HERE, "media", "videos.json")))
PORTS_INFO = json.load(open(os.path.join(HERE, "media", "ports.json")))  # researched Nov 2026, with sources
EXCURSIONS = json.load(open(os.path.join(HERE, "media", "excursions.json")))  # open days only
CLIMATE = json.load(open(os.path.join(HERE, "media", "climate.json")))  # January averages, Open-Meteo
_pp = os.path.join(HERE, "media", "photos.json")
PHOTOS = json.load(open(_pp)) if os.path.exists(_pp) else {}  # Wikimedia Commons, with credits
DAY_PHOTO = {"2027-01-08": "barbados", "2027-01-09": "barbados", "2027-01-10": "stlucia", "2027-01-11": "ship2",
             "2027-01-12": "montserrat", "2027-01-13": "antigua", "2027-01-14": "nevis", "2027-01-15": "jvd",
             "2027-01-16": "sxm", "2027-01-17": "tortola", "2027-01-18": "stkitts", "2027-01-19": "ship1",
             "2027-01-20": "martinique", "2027-01-21": "bequia", "2027-01-22": "grenada", "2027-01-23": "barbados"}


def photo(pid, cls="banner", eager=False):
    m = PHOTOS.get(pid)
    if not m:
        return ""
    lic = f'<a href="{e(m["license_url"])}" target="_blank" rel="noopener">{e(m["license"])}</a>' if m.get("license_url") else e(m.get("license", ""))
    credit = (f'Photo: <a href="{e(m["page"])}" target="_blank" rel="noopener">{e(m.get("author") or "Wikimedia Commons")}</a>, {lic}')
    load = "eager" if eager else "lazy"
    return (f'<figure class="photo {cls}"><img src="photos/{pid}-1400.jpg" srcset="photos/{pid}-700.jpg 700w, photos/{pid}-1400.jpg 1400w" '
            f'sizes="(max-width: 780px) 100vw, 1100px" alt="{e(m.get("caption") or "")}" loading="{load}" decoding="async">'
            f'<figcaption><span>{e(m.get("caption") or "")}</span><small>{credit}</small></figcaption></figure>')


def rain_words(pct):
    if pct >= 55:
        return f"showers on about {pct}% of days, usually brief"
    if pct >= 40:
        return f"a shower on about {pct}% of days, usually brief"
    return f"mostly dry; a shower on about {pct}% of days"


def weather_block(d):
    """January averages plus a slot the page fills with a live forecast close to the date."""
    key = d.get("port")
    if not key and d["kind"] == "sea":
        key = d["leg"][1]
    c = CLIMATE.get(key) if key else None
    if not c:
        return ""
    lat, lon = trip.PORTS[key][1], trip.PORTS[key][2]
    sea = f" · water {c['sea_f']}°F" if c.get("sea_f") else ""
    return (f'<div class="wx" data-lat="{lat}" data-lon="{lon}" data-date="{d["date"]}">'
            f'<p class="wx-avg"><b>Typical January day</b> {c["high_f"]}°F high, {c["low_f"]}°F low{sea}; {e(rain_words(c["rain_pct"]))}.</p>'
            '<p class="wx-live" hidden></p></div>')
TODO_FOR_PORT = {"montserrat": "plan-montserrat", "martinique": "plan-martinique", "bequia": "plan-bequia", "grenada": "plan-grenada"}
# which video goes on which day (first visit to each place; the ship tour on the first sea day)
DAY_VIDEO = {"2027-01-09": "barbados", "2027-01-10": "stlucia", "2027-01-11": "ship", "2027-01-12": "montserrat",
             "2027-01-13": "antigua", "2027-01-14": "stkitts", "2027-01-15": "jvd", "2027-01-16": "sxm",
             "2027-01-17": "tortola", "2027-01-20": "martinique", "2027-01-21": "bequia", "2027-01-22": "grenada"}


def video_card(key):
    v = VIDEOS.get(key)
    if not v:
        return ""
    vid = v["youtube_id"]
    meta = v["channel"] + (" · " + v["duration"] if v.get("duration") else "")
    return (f'<div class="vid" data-yt="{e(vid)}"><button type="button" class="vid-play" '
            f'style="background-image:url(https://i.ytimg.com/vi/{e(vid)}/hqdefault.jpg)" aria-label="Play video: {e(v["title"])}">'
            f'<span class="vid-btn" aria-hidden="true">▶</span><span class="vid-cap"><b>{e(v["title"])}</b><small>{e(meta)}</small></span>'
            f'</button></div><p class="vid-link"><a href="https://www.youtube.com/watch?v={e(vid)}" target="_blank" rel="noopener">Watch on YouTube ↗</a></p>')
TODAY_NOTE = "Built from the planning sheet on " + dt.date.today().strftime("%B %-d, %Y")


def e(s):
    return html.escape(str(s), quote=True)


# ---------------------------------------------------------------- helpers
def date_of(s):
    return dt.date.fromisoformat(s)


def long_date(s):
    d = date_of(s)
    return d.strftime("%A, %B ") + str(d.day)


def short_date(s):
    d = date_of(s)
    return d.strftime("%a %b ") + str(d.day)


def day_id(d):
    return "day-" + d["date"][5:]


def gmaps(lat, lon):
    return f"https://www.google.com/maps/search/?api=1&query={lat:.5f},{lon:.5f}"


def sun_times(lat, lon, d, utc_offset):
    """Approximate sunrise/sunset (NOAA algorithm), local clock strings."""
    n = d.timetuple().tm_yday
    g = 2 * math.pi / 365 * (n - 1)
    eqt = 229.18 * (0.000075 + 0.001868 * math.cos(g) - 0.032077 * math.sin(g)
                    - 0.014615 * math.cos(2 * g) - 0.040849 * math.sin(2 * g))
    decl = (0.006918 - 0.399912 * math.cos(g) + 0.070257 * math.sin(g) - 0.006758 * math.cos(2 * g)
            + 0.000907 * math.sin(2 * g) - 0.002697 * math.cos(3 * g) + 0.00148 * math.sin(3 * g))
    la = math.radians(lat)
    ha = math.degrees(math.acos(math.cos(math.radians(90.833)) / (math.cos(la) * math.cos(decl))
                                - math.tan(la) * math.tan(decl)))
    out = []
    for sign in (1, -1):
        mins = 720 - 4 * (lon + sign * ha) - eqt + utc_offset * 60
        h, m = divmod(int(round(mins)), 60)
        ap = "am" if h < 12 else "pm"
        out.append(f"{(h - 1) % 12 + 1}:{m:02d}{ap}")
    return out  # [sunrise, sunset]


# ---------------------------------------------------------------- maps
class Proj:
    def __init__(self, mid):
        m = META[mid]
        self.mid, self.z, self.x0, self.y0, self.w, self.h = mid, m["z"], m["x0"], m["y0"], m["w"], m["h"]

    def __call__(self, lat, lon):
        x, y = world_px(lat, lon, self.z)
        return x - self.x0, y - self.y0


def curve(a, b, bend=0.18):
    (x1, y1), (x2, y2) = a, b
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    dx, dy = x2 - x1, y2 - y1
    cx, cy = mx - dy * bend, my + dx * bend
    return f"M{x1:.1f},{y1:.1f}Q{cx:.1f},{cy:.1f} {x2:.1f},{y2:.1f}"


def label_attrs(x, y, w, r):
    """Place a text label to the right of a point, or the left near the right edge."""
    if x > w * 0.62:
        return x - r - 6, "end"
    return x + r + 6, "start"


def svg_open(pr, label):
    return (f'<figure class="map"><svg viewBox="0 0 {pr.w} {pr.h}" role="img" aria-label="{e(label)}">'
            f'<image href="maps/{pr.mid}.jpg" width="{pr.w}" height="{pr.h}"/>')


SVG_CLOSE = ('</svg><figcaption>Map data © <a href="https://www.openstreetmap.org/copyright">'
             'OpenStreetMap contributors</a></figcaption></figure>')


def point_map(sec, mid, keys, path=None, label=""):
    """Numbered markers + optional dashed path. Returns (figure_html, legend_html)."""
    pr = Proj(mid)
    r = max(20, pr.w * 0.027)
    fs = r * 1.05
    out = [svg_open(pr, label or trip.MAPS[mid]["title"])]
    if path:
        pts = [pr(trip.P[k][1], trip.P[k][2]) for k in path]
        d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        out.append(f'<path class="rt walk" d="{d}" style="stroke-width:{r*0.28:.1f}"/>')
    for i, k in enumerate(keys, 1):
        name, lat, lon, _ = trip.P[k]
        x, y = pr(lat, lon)
        out.append(f'<g class="mk" tabindex="0" role="button" aria-label="{i}. {e(name)}" data-pt="{sec}-{i}">'
                   f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}"/>'
                   f'<text x="{x:.1f}" y="{y + fs*0.36:.1f}" font-size="{fs:.1f}">{i}</text></g>')
    out.append(SVG_CLOSE)
    legend = ['<ol class="legend">']
    for i, k in enumerate(keys, 1):
        name, lat, lon, desc = trip.P[k]
        legend.append(f'<li tabindex="0" role="button" data-pt="{sec}-{i}" data-desc="{e(desc)}" data-gm="{gmaps(lat, lon)}">'
                      f'<span class="n">{i}</span><span><b>{e(name)}</b><small>{e(desc)}</small></span></li>')
    legend.append("</ol>")
    return "".join(out), "".join(legend)


PORT_DATES = {}
for d in trip.DAYS:
    if d.get("port"):
        PORT_DATES.setdefault(d["port"], []).append(d)


def route_map(sec, highlight=None):
    pr = Proj("route")
    r = 20
    out = [svg_open(pr, "Cruise route from Barbados through the Eastern Caribbean")]
    coords = {k: pr(v[1], v[2]) for k, v in trip.PORTS.items()}
    segs = list(zip(trip.ROUTE, trip.ROUTE[1:]))
    for a, b in segs:
        cls = "rt sea"
        if highlight:
            cls += " on" if [a, b] == highlight else " off"
        out.append(f'<path class="{cls}" d="{curve(coords[a], coords[b], 0.12)}"/>')
    order = []
    for k in trip.ROUTE:
        if k not in order:
            order.append(k)
    legend = ['<ol class="legend">']
    inset_marks = []
    for i, k in enumerate(order, 1):
        name = trip.PORTS[k][0]
        x, y = coords[k]
        days = PORT_DATES.get(k, [])
        when = " & ".join(short_date(d["date"])[4:] for d in days)
        nums = "·".join(str(d["cruise_day"]) for d in days if d["cruise_day"])
        tx, anchor = label_attrs(x, y, pr.w, r)
        if k in INSET_PORTS:
            # shown with labels in the British Virgin Islands inset instead
            out.append(f'<g class="mk lab" tabindex="0" role="button" aria-label="{e(name)}" data-pt="{sec}-{i}">'
                       f'<circle class="dot" cx="{x:.1f}" cy="{y:.1f}" r="{r*0.55:.1f}"/></g>')
            inset_marks.append((k, i, name, when))
            isl = next((x for x in trip.ISLANDS if x["id"] == k), None)
            lat, lon = trip.PORTS[k][1], trip.PORTS[k][2]
            legend.append(f'<li tabindex="0" role="button" data-pt="{sec}-{i}" data-desc="{e(isl["blurb"] if isl else "")}" data-gm="{gmaps(lat, lon)}">'
                          f'<span class="n">{e(nums)}</span><span><b>{e(name)}</b><small>{e(when)}</small></span></li>')
            continue
        if k == "stkitts":
            tx, anchor = x - r - 6, "end"
        dy = {"montserrat": 10, "antigua": -8}.get(k, 0)
        out.append(f'<g class="mk lab" tabindex="0" role="button" aria-label="{e(name)}" data-pt="{sec}-{i}">'
                   f'<circle class="dot" cx="{x:.1f}" cy="{y:.1f}" r="{r*0.7:.1f}"/>'
                   f'<text class="lab" x="{tx:.1f}" y="{y + 9 + dy:.1f}" text-anchor="{anchor}">{e(name)}</text>'
                   f'<text class="lab2" x="{tx:.1f}" y="{y + 36 + dy:.1f}" text-anchor="{anchor}">{e(when)}</text></g>')
        isl = next((x for x in trip.ISLANDS if x["id"] == k), None)
        desc = isl["blurb"] if isl else ""
        lat, lon = trip.PORTS[k][1], trip.PORTS[k][2]
        legend.append(f'<li tabindex="0" role="button" data-pt="{sec}-{i}" data-desc="{e(desc)}" data-gm="{gmaps(lat, lon)}">'
                      f'<span class="n">{e(nums) if nums else "⚓"}</span><span><b>{e(name)}</b><small>{e(when)}</small></span></li>')
    legend.append("</ol>")
    out.append(bvi_inset(sec, pr, inset_marks))
    out.append(SVG_CLOSE)
    return "".join(out), "".join(legend)


INSET_PORTS = ("jvd", "tortola")


def bvi_inset(sec, pr, marks):
    """Zoomed-in box for Jost Van Dyke and Tortola, whose dots overlap on the route map."""
    ip = Proj("bvi")
    s_, w_, n_, e_ = trip.MAPS["bvi"]["bbox"]
    ax0, ay0 = pr(n_, w_)
    ax1, ay1 = pr(s_, e_)
    X, Y, W = 24, 440, 380
    k = W / ip.w
    H = ip.h * k
    o = [f'<rect class="inset-area" x="{ax0:.1f}" y="{ay0:.1f}" width="{ax1-ax0:.1f}" height="{ay1-ay0:.1f}"/>',
         f'<path class="inset-lead" d="M{(ax0+ax1)/2:.1f},{ay1:.1f} L{X + W/2:.1f},{Y:.1f}"/>',
         f'<g class="inset"><rect class="inset-bg" x="{X-4}" y="{Y-4}" width="{W+8}" height="{H+8:.1f}" rx="8"/>',
         f'<image href="maps/bvi.jpg" x="{X}" y="{Y}" width="{W}" height="{H:.1f}"/>',
         f'<text class="inset-t" x="{X+12}" y="{Y+H-14:.1f}">British Virgin Islands</text>']
    for key, i, name, when in marks:
        lat, lon = trip.PORTS[key][1], trip.PORTS[key][2]
        x, y = ip(lat, lon)
        x, y = X + x * k, Y + y * k
        tx, ty = (x + 18, y + 2) if key == "jvd" else (x + 18, y + 26)
        o.append(f'<g class="mk lab" tabindex="0" role="button" aria-label="{e(name)}" data-pt="{sec}-{i}">'
                 f'<circle class="dot" cx="{x:.1f}" cy="{y:.1f}" r="12"/>'
                 f'<text class="lab" x="{tx:.1f}" y="{ty:.1f}" text-anchor="start">{e(name)}</text>'
                 f'<text class="lab2" x="{tx:.1f}" y="{ty + 24:.1f}" text-anchor="start">{e(when)}</text></g>')
    o.append("</g>")
    return "".join(o)


AIRPORT_LABEL = {"sea": "Seattle", "atl": "Atlanta", "bgi_air": "Barbados"}


def flight_map(sec, legs):
    pr = Proj("flights")
    out = [svg_open(pr, "Flights between Seattle, Atlanta and Barbados")]
    keys = ["sea", "atl", "bgi_air"]
    pts = {k: pr(trip.P[k][1], trip.P[k][2]) for k in keys}
    all_legs = [["sea", "atl"], ["atl", "bgi_air"]]
    for a, b in all_legs:
        on = any(sorted(l) == sorted([a, b]) for l in legs)
        cls = "rt fly " + ("on" if on else "off")
        out.append(f'<path class="{cls}" d="{curve(pts[a], pts[b], -0.12)}"/>')
    legend = ['<ol class="legend">']
    for i, k in enumerate(keys, 1):
        name, lat, lon, desc = trip.P[k]
        x, y = pts[k]
        anchor = "end" if k == "bgi_air" else "start"
        tx = x - 16 if anchor == "end" else x + 16
        ty = {"sea": y + 34, "atl": y + 30, "bgi_air": y - 16}[k]
        out.append(f'<g class="mk lab" tabindex="0" role="button" aria-label="{e(name)}" data-pt="{sec}-{i}">'
                   f'<circle class="dot" cx="{x:.1f}" cy="{y:.1f}" r="11"/>'
                   f'<text class="lab" x="{tx:.1f}" y="{ty:.1f}" text-anchor="{anchor}" style="font-size:30px">{AIRPORT_LABEL[k]}</text></g>')
        legend.append(f'<li tabindex="0" role="button" data-pt="{sec}-{i}" data-desc="{e(desc)}" data-gm="{gmaps(lat, lon)}">'
                      f'<span class="n">✈</span><span><b>{e(name)}</b><small>{e(desc)}</small></span></li>')
    legend.append("</ol>")
    out.append(SVG_CLOSE)
    return "".join(out), "".join(legend)


def map_block(sec, spec, title=None, blurb=None, extra=""):
    if spec["map"] == "route":
        fig, leg = route_map(sec, spec.get("leg"))
    elif spec["map"] == "flights":
        fig, leg = flight_map(sec, spec.get("legs", []))
    else:
        fig, leg = point_map(sec, spec["map"], spec["points"], spec.get("path"))
    h = f"<h3>{e(title)}</h3>" if title else ""
    b = f'<p class="blurb">{e(blurb)}</p>' if blurb else ""
    return (f'<div class="mapsec" id="{sec}">{h}{b}<div class="mapwrap"><div>{fig}'
            f'<div class="info" aria-live="polite"></div></div><div>{leg}{extra}</div></div></div>')


def live_map_data():
    """Ports, route and fallback image bounds for the zoomable itinerary map."""
    order = []
    for k in trip.ROUTE:
        if k not in order:
            order.append(k)
    ports = []
    for k in order:
        name, lat, lon = trip.PORTS[k]
        days = [{"label": short_date(d["date"]), "href": "#" + day_id(d), "n": d["cruise_day"]}
                for d in PORT_DATES.get(k, [])]
        ports.append({"name": name, "lat": lat, "lon": lon, "days": days,
                      "num": "·".join(str(d["n"]) for d in days if d["n"])})
    s, w, n, e_ = trip.MAPS["route"]["bbox"]
    return {"ports": ports, "route": [[trip.PORTS[k][1], trip.PORTS[k][2]] for k in trip.ROUTE],
            "fallback": {"src": "maps/route.jpg", "bounds": [[s, w], [n, e_]]}}


def live_map_block():
    return ('<section class="livemap"><h2>Route map</h2>'
            '<p class="blurb">Zoom in and out with the + and − buttons, by pinching, or by scrolling after you click the map. '
            'Tap a port to see its dates and open that day.</p>'
            '<div id="live-map" class="lmap" role="region" aria-label="Zoomable cruise route map">'
            '<img src="maps/route.jpg" alt="Cruise route map" class="lmap-fallback"></div></section>')


# ---------------------------------------------------------------- views
def view_itinerary():
    h = ['<div class="view" id="v-itinerary">']
    cruise_days = [d for d in trip.DAYS if d["cruise_day"]]
    ports = [d for d in trip.DAYS if d["kind"] == "port"]
    tenders = [d for d in ports if d.get("tender")]
    sea = [d for d in trip.DAYS if d["kind"] == "sea"]
    h.append('<div class="stays">'
             f'<div><b>{len(trip.DAYS)} days</b><span>Jan 7 – Jan 24</span></div>'
             '<div><b>14 nights</b><span>Seabourn Ovation</span></div>'
             f'<div><b>{len(ports)} port calls</b><span>10 islands + Barbados</span></div>'
             f'<div><b>{len(tenders)} tender stops</b><span>small boat to shore</span></div>'
             f'<div><b>{len(sea)} sea days</b><span>Jan 11 and Jan 19</span></div>'
             '<div><b>2 nights</b><span>Atlanta airport</span></div>'
             '</div>')
    h.append('<div class="cal"><a class="btn" href="trip.ics" download>📅 Add the trip to your calendar</a>'
             '<span>Adds the flights, every port day with ship times, and the booked excursions. '
             'On iPhone, tap it and choose Add All; on a computer, open the downloaded file.</span></div>')
    h.append(live_map_block())
    groups = [("Getting there", lambda d: d["date"] <= "2027-01-08"),
              ("On the ship", lambda d: "2027-01-09" <= d["date"] <= "2027-01-22"),
              ("Heading home", lambda d: d["date"] >= "2027-01-23")]
    for title, f in groups:
        rows = [d for d in trip.DAYS if f(d)]
        h.append(f'<section><h2>{e(title)} <span class="dates">{short_date(rows[0]["date"])[4:]} – {short_date(rows[-1]["date"])[4:]}</span></h2>')
        h.append('<div class="days"><div class="day head"><span>Date</span><span>Where</span><span>In port</span><span>Plan</span><span>Night</span></div>')
        for d in rows:
            plan = d["summary"]
            booked = [it for it in d["items"] if it[1].startswith("Booked:")]
            tag = '<em class="tag bk">Booked</em>' if booked else ('<em class="tag atsea">Sea day</em>' if d["kind"] == "sea" else
                   ('<em class="tag open">Open</em>' if d.get("ideas") and d["kind"] == "port" else ""))
            hours = d.get("hours", "")
            if d.get("tender"):
                hours += " · tender"
            cd = f'<small>Day {d["cruise_day"]}</small>' if d["cruise_day"] else ""
            hrs = f'<span data-k="In port">{e(hours)}</span>' if hours else '<span class="nil">—</span>'
            h.append(f'<a class="day" href="#{day_id(d)}"><span class="d">{short_date(d["date"])}{cd}</span>'
                     f'<span class="l" data-k="Where">{e(d["place"])}</span>{hrs}'
                     f'<span data-k="Plan">{tag}{e(plan)}</span>'
                     f'<span data-k="Night">{e(d["stay"])}</span></a>')
        h.append("</div></section>")
    h.append("</div>")
    return "".join(h)


def view_days():
    h = ['<div class="view" id="v-days"><nav class="chips" aria-label="Choose a day">']
    for d in trip.DAYS:
        dd = date_of(d["date"])
        h.append(f'<a href="#{day_id(d)}" data-day="{day_id(d)}"><b>{dd.strftime("%a")}</b><span>Jan {dd.day}</span></a>')
    h.append("</nav>")
    for i, d in enumerate(trip.DAYS):
        h.append(render_day(d, i))
    h.append("</div>")
    return "".join(h)


def tel(phone):
    """Show a phone number as text with a tap-to-call link on its first number."""
    m = re.search(r"\+?[\d][\d\s().-]{6,}\d", phone or "")
    if not m:
        return e(phone or "")
    num = re.sub(r"[^\d+]", "", m.group(0))
    if not num.startswith("+"):
        num = "+" + num if len(num) > 10 else num
    return e(phone[:m.start()]) + f'<a href="tel:{num}">{e(m.group(0))}</a>' + e(phone[m.end():])


def help_rows(c):
    rows = []
    if c.get("emergency"):
        rows.append(("Emergency", e(c["emergency"])))
    hsp = c.get("hospital") or {}
    if hsp:
        rows.append(("Hospital", f"{e(hsp.get('name', ''))}, {e(hsp.get('town', ''))}" + (f"<br>{tel(hsp['phone'])}" if hsp.get("phone") else "")))
    emb = c.get("us_embassy") or {}
    if emb:
        ph = tel(emb.get("phone", ""))
        if emb.get("after_hours"):
            ph += "<br>After hours: " + tel(emb["after_hours"])
        url = f'<br><a href="{e(emb["url"])}" target="_blank" rel="noopener">{e(emb["url"].replace("https://", "").rstrip("/"))}</a>' if emb.get("url") else ""
        rows.append(("US embassy", f"{e(emb.get('name', ''))}<br>{ph}{url}"))
    return rows


def port_guide(key):
    g = PORTS_INFO.get(key)
    if not g:
        return ""
    t = g.get("taxi") or {}
    tsum = t.get("type") or t.get("summary") or ""
    fares = t.get("examples") or t.get("fares") or []
    rows = [("Where you land", e(g.get("landing", ""))), ("Getting to town", e(g.get("to_town", "")))]
    taxi = e(tsum)
    if fares:
        taxi += "<ul>" + "".join(f"<li>{e(x)}</li>" for x in fares) + "</ul>"
    if t.get("basis"):
        taxi += f"<small>{e(t['basis'])}</small>"
    rows += [("Taxis", taxi), ("Walking", e(g.get("walkability", ""))), ("Accessibility", e(g.get("accessibility", "")))]
    o = ['<details class="guide" open><summary><h3>Port guide</h3></summary><dl class="ship">']
    o += [f"<div><dt>{k}</dt><dd>{v}</dd></div>" for k, v in rows if v]
    o.append("</dl>")
    if g.get("lunch"):
        o.append('<h4 class="gh">Lunch near the pier</h4><div class="lunch">')
        for l in g["lunch"]:
            o.append(f'<div><b>{e(l["name"])}</b><p>{e(l.get("why", ""))}</p><small>{e(l.get("distance", ""))}</small></div>')
        o.append("</div>")
    hr = help_rows(g.get("contacts") or {})
    if hr:
        o.append('<h4 class="gh">If you need help</h4><dl class="ship help">' + "".join(f"<div><dt>{k}</dt><dd>{v}</dd></div>" for k, v in hr) + "</dl>")
    src = g.get("sources") or []
    o.append('<p class="note">Researched in November 2026 from tourism boards, government fare tables and travel guides. '
             'Prices and opening hours change, so confirm on the day.'
             + (f' <details class="src"><summary>Sources ({len(src)})</summary><ul>' + "".join(
                 f'<li><a href="{e(u)}" target="_blank" rel="noopener">{e(u.split("//")[-1][:70])}</a></li>' for u in src) + "</ul></details>" if src else "")
             + "</p></details>")
    return "".join(o)


ACT = {"easy": "Easy", "moderate": "Moderate", "active": "Active"}


def excursion_compare(key):
    x = EXCURSIONS.get(key)
    if not x:
        return ""
    o = ['<section class="excomp"><h3>Compare excursions</h3>'
         '<p class="blurb">Nothing is booked for this day yet. Seabourn tours are booked in the Seabourn Source app; '
         'independent tours on the operator\'s website. Prices are per person, as listed in November 2026.</p>'
         f'<div class="callout tip pick"><h4>Our pick</h4><p>{e(x.get("pick", ""))}</p></div><div class="exgrid">']
    for op in x["options"]:
        prov = op.get("provider", "")
        kind = "Seabourn" if prov == "Seabourn" else ("Do it yourself" if "DIY" in (op.get("name", "") + prov) else "Independent")
        kcls = {"Seabourn": "sb", "Independent": "ind", "Do it yourself": "diy"}[kind]
        price = money(op["price_usd"]) if isinstance(op.get("price_usd"), (int, float)) and op["price_usd"] else "Varies"
        pn = op.get("price_note") or ""
        if prov == "Seabourn":
            pn = "Seabourn's starting price, November 2026; confirm for this sailing."
        elif re.search(r"snippet|429|403|could not be loaded|404", pn):
            pn = "Approximate price; confirm when booking."
        dur = op.get("duration")
        dur = (f"{dur:g} hr" if isinstance(dur, (int, float)) else str(dur)) if dur else ""
        act = op.get("activity") or ""
        name = re.sub(r"\s*\([A-Z0-9]{5,7}\)$", "", op.get("name", "")).replace("DIY: ", "")
        link = f'<a href="{e(op["url"])}" target="_blank" rel="noopener">Details ↗</a>' if op.get("url") else ""
        o.append(f'<article class="ex {kcls}"><p class="ex-k"><em class="tag {kcls}">{kind}</em>'
                 + (f'<span>{e(prov)}</span>' if kind == "Independent" else "") + "</p>"
                 f'<h4>{e(name)}</h4><p class="ex-m"><b>{e(price)}</b>' + (f" · {e(dur)}" if dur else "")
                 + (f' · <span class="act {e(act)}">{e(ACT.get(act, act))}</span>' if act else "") + "</p>"
                 f'<p>{e(op.get("highlights", ""))}</p>'
                 + (f'<small>{e(op.get("activity_reason", ""))}</small>' if op.get("activity_reason") else "")
                 + (f'<small class="pn">{e(pn)}</small>' if pn else "")
                 + f"{link}</article>")
    o.append("</div>")
    tid = TODO_FOR_PORT.get(key)
    if tid:
        o.append(f'<p class="note"><a href="#todo">Tick off the decision on the To do tab →</a></p>')
    o.append("</section>")
    return "".join(o)


def render_day(d, i):
    sid = day_id(d)
    dd = date_of(d["date"])
    out = [f'<article class="dayview" id="{sid}" hidden>']
    eyebrow = long_date(d["date"])
    if d["cruise_day"]:
        eyebrow += f" · Cruise day {d['cruise_day']} of 15"
    out.append(f'<p class="eyebrow">{e(eyebrow)}</p><h2 class="dayh">{e(d["place"])}</h2>')
    out.append(photo(DAY_PHOTO.get(d["date"], "")))
    out.append(f'<p class="lede">{e(d["summary"])}</p>')
    chips = []
    if d.get("hours"):
        chips.append(("Ship", d["hours"]))
    if d.get("tender"):
        chips.append(("Ashore by", "tender"))
    if d.get("tz"):
        chips.append(("Time zone", d["tz"]))
    isl = next((x for x in trip.ISLANDS if x["id"] == d.get("port")), None)
    if isl and d["kind"] == "port":
        chips.append(("Money", isl.get("money") or re.split(r"[.;,]\s", isl["currency"])[0]))
    loc = None
    if d.get("port"):
        p = trip.PORTS[d["port"]]
        loc = (p[1], p[2], -4)
    elif d["kind"] == "sea":
        a, b = (trip.PORTS[k] for k in d["leg"])
        loc = ((a[1] + b[1]) / 2, (a[2] + b[2]) / 2, -4)
    elif d["date"] == "2027-01-08":
        loc = (13.08, -59.61, -4)
    if loc:
        rise, sset = sun_times(loc[0], loc[1], dd, loc[2])
        chips.append(("Sun", f"up {rise} · down {sset}"))
    chips.append(("Night", d["stay"]))
    out.append('<dl class="facts">' + "".join(f"<div><dt>{e(k)}</dt><dd>{e(v)}</dd></div>" for k, v in chips) + "</dl>")
    out.append(weather_block(d))

    out.append('<div class="daygrid"><div>')
    out.append('<h3>Schedule</h3><ol class="timeline">')
    for t, title, note, cost in d["items"]:
        cls = ""
        if title.startswith("Booked:"):
            cls = ' class="bk"'
            title = title[len("Booked:"):].strip()
            title_html = f'<em class="tag bk">Booked</em>{e(title)}'
        else:
            title_html = e(title)
        sub = f"<small>{e(note)}</small>" if note else ""
        c = f'<span class="cost">{e(cost)}</span>' if cost else ""
        tt = e(t) if t else "&nbsp;"
        out.append(f'<li{cls}><span class="t">{tt}</span><span class="w"><b>{title_html}</b>{sub}{c}</span></li>')
    out.append("</ol>")
    if d.get("bring"):
        out.append(f'<div class="callout"><h4>Bring</h4><p>{e(d["bring"])}</p></div>')
    if d.get("ideas"):
        out.append('<div class="callout idea"><h4>Ideas from the sheet</h4><ul>' +
                   "".join(f"<li>{e(x)}</li>" for x in d["ideas"]) + "</ul></div>")
    if d.get("tips"):
        out.append('<div class="callout tip"><h4>Good to know</h4><ul>' +
                   "".join(f"<li>{e(x)}</li>" for x in d["tips"]) + "</ul></div>")
    out.append("</div></div>")
    if d.get("port") in EXCURSIONS and d["kind"] == "port":
        out.append(excursion_compare(d["port"]))
    if d.get("port") and d["kind"] in ("port", "embark"):
        out.append(port_guide(d["port"]))
    if d["date"] in DAY_VIDEO:
        out.append('<section class="watch"><h3>Watch</h3>' + video_card(DAY_VIDEO[d["date"]]) + "</section>")
    for j, spec in enumerate(d.get("maps", [])):
        title = trip.MAPS[spec["map"]]["title"]
        if spec["map"] == "route":
            title = "Where the ship is sailing today"
        out.append(map_block(f"{sid}-m{j}", spec, title=title))
    prev_d = trip.DAYS[i - 1] if i > 0 else None
    next_d = trip.DAYS[i + 1] if i + 1 < len(trip.DAYS) else None
    out.append('<div class="pager">')
    out.append(f'<a href="#{day_id(prev_d)}">← {e(short_date(prev_d["date"]))}</a>' if prev_d else "<span></span>")
    out.append('<a href="#itinerary">All days</a>')
    out.append(f'<a href="#{day_id(next_d)}">{e(short_date(next_d["date"]))} →</a>' if next_d else "<span></span>")
    out.append("</div></article>")
    return "".join(out)


def view_maps():
    h = ['<div class="view" id="v-maps"><div class="sub">',
         '<button type="button" data-go="m-route">Full route</button>',
         '<button type="button" data-go="m-flights">Flights</button>']
    for isl in trip.ISLANDS:
        h.append(f'<button type="button" data-go="m-{isl["id"]}">{e(isl["name"].split(" (")[0])}</button>')
    h.append('</div><p class="hint">Tap a number on a map, or a name in the list, to read about that place and open it in Google Maps.</p>')
    h.append('<section><h2>The full itinerary</h2>')
    h.append(map_block("m-route", {"map": "route"}, blurb="Round trip from Bridgetown, Barbados: north through the Leeward Islands to the British Virgin Islands, then back south through Martinique, Bequia and Grenada. Numbers are cruise days."))
    h.append('</section><section><h2>Getting there and home</h2>')
    h.append(map_block("m-flights", {"map": "flights", "legs": [["sea", "atl"], ["atl", "bgi_air"]]},
                       blurb="Seattle to Atlanta on Alaska, a night at the Atlanta airport Marriott, then Delta to Barbados. The same in reverse coming home."))
    h.append("</section>")
    for isl in trip.ISLANDS:
        facts = [("When", isl["days"]), ("Money", isl["currency"]), ("Language", isl["language"])]
        cl = CLIMATE.get(isl["id"])
        if cl:
            facts.append(("January weather", f"{cl['high_f']}°F / {cl['low_f']}°F" + (f", water {cl['sea_f']}°F" if cl.get("sea_f") else "") + f"; {rain_words(cl['rain_pct'])}"))
        if isl.get("rain"):
            facts.append(("Rain", isl["rain"]))
        extra = ('<dl class="facts col">' + "".join(f"<div><dt>{e(k)}</dt><dd>{e(v)}</dd></div>" for k, v in facts) + "</dl>"
                 '<h4>Highlights</h4><ul class="hl">' + "".join(f"<li>{e(x)}</li>" for x in isl["highlights"]) + "</ul>")
        hr = help_rows((PORTS_INFO.get(isl["id"]) or {}).get("contacts") or {})
        if hr:
            extra += '<h4 style="margin-top:16px">If you need help</h4><dl class="facts col help">' + "".join(f"<div><dt>{k}</dt><dd>{v}</dd></div>" for k, v in hr) + "</dl>"
        h.append(f'<section><h2>{e(isl["name"])}</h2>' + photo(isl["id"], "banner short"))
        h.append(map_block(f"m-{isl['id']}", {"map": isl["map"], "points": isl["points"]}, blurb=isl["blurb"], extra=extra))
        h.append("</section>")
    h.append("</div>")
    return "".join(h)


def view_ship():
    s = trip.SHIP
    h = ['<div class="view" id="v-ship">']
    h.append(photo("ship1", "banner"))
    h.append('<section><h2>Seabourn Ovation</h2><p class="blurb">A small, all-suite luxury ship — about 600 guests — '
             'so tenders are quick, the crew learns your name, and most drinks, dining and tips are included.</p>')
    h.append('<div class="stays">' + "".join(f"<div><b>{e(big)}</b><span>{e(cap)}</span></div>" for big, cap in s["facts"]) + "</div></section>")
    h.append('<section class="watch"><h2>Take the tour</h2><p class="blurb">Seabourn\'s own video tour of Ovation and her identical sister ship, Encore.</p>' + video_card("ship") + '</section>')
    h.append(f'<div class="callout caviar"><h4>Caviar in the Surf</h4><p>{e(s["caviar"])}</p></div>')

    def deflist(title, rows):
        return (f"<section><h2>{e(title)}</h2><dl class='ship'>" +
                "".join(f"<div><dt>{e(a)}</dt><dd>{e(b)}</dd></div>" for a, b in rows) + "</dl></section>")
    h.append(photo("ship2", "banner short"))
    h.append(deflist("Where to eat", s["dining"]))
    h.append(f'<p class="note">{e(s["caribbean_new"])}</p>')
    h.append(deflist("Bars, shows and lounges", s["venues"]))
    h.append(deflist("Spa, pools and the water", s["wellness"]))
    h.append('<section><h2>What\'s included</h2><div class="twocol"><div><h4>Included</h4><ul class="hl yes">' +
             "".join(f"<li>{e(x)}</li>" for x in s["included"]) + '</ul></div><div><h4>Costs extra</h4><ul class="hl no">' +
             "".join(f"<li>{e(x)}</li>" for x in s["extra"]) + "</ul></div></div></section>")
    h.append(deflist("Practical", s["practical"]))
    h.append(deflist("Suites", s["suites"]))
    h.append('<p class="note">Ship details come from Seabourn\'s website and cruise-industry sources, checked November 2026. '
             'Venues and prices can change; the Seabourn Source app is the final word onboard.</p>')
    h.append("</div>")
    return "".join(h)


def view_todo():
    h = ['<div class="view" id="v-todo">']
    total = sum(len(g["items"]) for g in trip.TODO)
    h.append(f'<p class="blurb">Planning tasks from the sheet\'s Actions tab, plus loose ends spotted while building this site. Costs are on the Budget tab. '
             f'Ticks are saved in this browser only. <span class="progress" data-total="{total}"></span></p>')
    for g in trip.TODO:
        pre = g["group"].startswith("Done earlier")
        h.append(f'<section><h2>{e(g["group"])}</h2>')
        if pre:
            h.append('<p class="note">Pre-ticked because their dates have passed. Untick anything that is still open.</p>')
        h.append('<ul class="todo">')
        for it in g["items"]:
            meta = []
            if it["date"]:
                ds = it["date"]
                if len(ds) == 7:
                    meta.append(date_of(ds + "-01").strftime("%B %Y"))
                else:
                    meta.append(short_date(ds) + (", " + ds[:4] if ds[:4] != "2027" else ", 2027"))
            if it["who"]:
                meta.append(it["who"])
            m = f'<small>{e(" · ".join(meta))}</small>' if meta else ""
            amt = f'<span class="cost">{e(it["amount"])}</span>' if it["amount"] else ""
            due = f' data-due="{it["date"]}"' if it["date"] and len(it["date"]) == 10 else ""
            h.append(f'<li{due}><label><input type="checkbox" data-id="{it["id"]}"{" data-default=1" if pre else ""}>'
                     f'<span><b>{e(it["text"])}</b>{m}</span>{amt}</label></li>')
        h.append("</ul></section>")
    h.append("</div>")
    return "".join(h)


STATUS = {"paid": ("Paid", "bk"), "booked": ("Booked", "atsea"), "planned": ("Planned", "open"),
          "estimate": ("Estimate", "est"), "cash": ("Cash on the day", "cash")}


def money(x):
    return f"${x:,.0f}" if abs(x - round(x)) < 0.005 else f"${x:,.2f}"


def view_budget():
    costs = trip.COSTS
    total = sum(c[2] for c in costs)
    paid = sum(c[2] for c in costs if c[3] == "paid")
    cash = sum(c[2] for c in costs if c[3] == "cash")
    extras = sum(x[2] for x in trip.EXTRAS)
    h = ['<div class="view" id="v-budget">']
    h.append('<p class="blurb" style="margin-top:22px">What the trip costs, from the planning sheet. Totals only: no card details. '
             'Onboard dining, drinks and tips are included in the cruise fare.</p>')
    h.append('<div class="stays">'
             f'<div><b>{money(total)}</b><span>planned trip cost</span></div>'
             f'<div><b>{money(paid)}</b><span>paid so far</span></div>'
             f'<div><b>{money(total - paid)}</b><span>still to pay</span></div>'
             f'<div><b>{money(cash)}</b><span>cash to carry ashore</span></div>'
             f'<div><b>≈ {money(extras)}</b><span>extras allowance (not in total)</span></div></div>')
    # by category
    cats = {}
    for c in costs:
        cats.setdefault(c[0], [0, 0])
        cats[c[0]][0] += c[2]
        if c[3] == "paid":
            cats[c[0]][1] += c[2]
    order = sorted(cats.items(), key=lambda kv: -kv[1][0])
    mx = order[0][1][0]
    h.append('<section><h2>Where the money goes</h2><p class="blurb">Darker part of each bar is already paid.</p><div class="bars">')
    for cat, (amt, pd) in order:
        w = max(amt / mx * 100, 0.8)
        pw = pd / amt * 100 if amt else 0
        h.append(f'<div class="bar"><span class="bl">{e(cat)}</span><span class="bt" style="--w:{w:.2f}%">'
                 f'<i style="width:{pw:.1f}%"></i></span><span class="bv">{money(amt)}</span></div>')
    h.append("</div></section>")
    # items
    h.append('<section><h2>Every item</h2><div class="days costs"><div class="day head"><span>What</span><span>Item</span><span>Cost</span><span>Status</span></div>')
    for cat, item, amt, st in costs:
        lab, cls = STATUS[st]
        h.append(f'<div class="day"><span class="d">{e(cat)}</span><span data-k="Item">{e(item)}</span>'
                 f'<span class="num" data-k="Cost">{money(amt)}</span><span data-k="Status"><em class="tag {cls}">{e(lab)}</em></span></div>')
    h.append(f'<div class="day total"><span class="d">Total</span><span></span><span class="num">{money(total)}</span><span></span></div></div></section>')
    # extras
    h.append('<section><h2>Extras allowance</h2><p class="blurb">Rough amounts for things that aren\'t planned yet. Not included in the total above.</p>'
             '<div class="days costs extras"><div class="day head"><span>What</span><span>Why</span><span>About</span><span></span></div>')
    for name, why, amt in trip.EXTRAS:
        h.append(f'<div class="day"><span class="d">{e(name)}</span><span data-k="Why">{e(why)}</span><span class="num" data-k="About">≈ {money(amt)}</span><span></span></div>')
    for name, why in trip.OPTIONAL:
        h.append(f'<div class="day"><span class="d">{e(name)}</span><span data-k="Why">{e(why)}</span><span class="num" data-k="About">optional</span><span></span></div>')
    h.append(f'<div class="day total"><span class="d">Allowance</span><span></span><span class="num">≈ {money(extras)}</span><span></span></div></div></section>')
    h.append('<p class="note" style="margin-top:22px">Currencies, cards, ATMs and how much cash to bring are on the <a href="#money">Money tab</a>.</p>')
    h.append("</div>")
    return "".join(h)


def view_money():
    """Currencies, cards, ATMs and cash. Port-by-port details are filled from tools/media/money.json when present."""
    rows = [5, 10, 20, 50, 100]
    h = ['<div class="view" id="v-money">']
    h.append('<section><h2>Currencies on this trip</h2><p class="blurb">US dollars work almost everywhere except Martinique. '
             'Two currencies are fixed to the dollar, so this table never changes. Small US bills are handy for tips and taxis.</p>'
             '<div class="days fx"><div class="day head"><span>US dollars</span><span>EC dollars (XCD)</span><span>Barbados dollars (BBD)</span></div>')
    for r in rows:
        h.append(f'<div class="day"><span class="d">${r}</span><span class="num" data-k="EC dollars">EC${r*2.7:,.2f}</span><span class="num" data-k="Barbados dollars">BDS${r*2:,.0f}</span></div>')
    h.append('</div></section></div>')
    return "".join(h)


# ---------------------------------------------------------------- calendar (.ics)
SITE_URL = "https://spencertownley-sys.github.io/travel-plan-sites/cindy-paul-caribbean/"
TZ = {"PT": -8, "ET": -5, "AST": -4}


def parse_time(t):
    m = re.match(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)", t.strip(), re.I)
    if not m:
        return None
    hh, mm, ap = int(m.group(1)), int(m.group(2) or 0), m.group(3).lower()
    if ap == "pm" and hh != 12:
        hh += 12
    if ap == "am" and hh == 12:
        hh = 0
    return hh, mm


def ics_time(date, hm, tz):
    d = dt.datetime.fromisoformat(date).replace(hour=hm[0], minute=hm[1]) - dt.timedelta(hours=TZ[tz])
    return d.strftime("%Y%m%dT%H%M%SZ")


def ics_escape(t):
    return t.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


FLIGHTS = [  # (date, from tz, dep, arr date, to tz, arr, title)
    ("2027-01-07", "PT", "9:10am", "2027-01-07", "ET", "4:49pm", "Alaska 334 Seattle → Atlanta"),
    ("2027-01-08", "ET", "9:41am", "2027-01-08", "AST", "3:20pm", "Delta 1985 Atlanta → Barbados"),
    ("2027-01-23", "AST", "4:30pm", "2027-01-23", "ET", "8:50pm", "Delta 1984 Barbados → Atlanta"),
    ("2027-01-24", "ET", "7:00am", "2027-01-24", "PT", "9:41am", "Alaska 348 Atlanta → Seattle"),
]


def fold(line):
    """iCalendar lines must be at most 75 bytes; continue longer ones on lines starting with a space."""
    out, cur = [], b""
    for ch in line:
        c = ch.encode("utf-8")
        if len(cur) + len(c) > (75 if not out else 74):
            out.append(cur.decode("utf-8"))
            cur = b""
        cur += c
    out.append(cur.decode("utf-8"))
    return "\r\n ".join(out)


def write_ics():
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    ev = []

    def add(uid, summary, start, end, desc="", allday=False, url=None):
        lines = ["BEGIN:VEVENT", f"UID:{uid}@cindy-paul-caribbean", f"DTSTAMP:{stamp}"]
        if allday:
            lines += [f"DTSTART;VALUE=DATE:{start}", f"DTEND;VALUE=DATE:{end}"]
        else:
            lines += [f"DTSTART:{start}", f"DTEND:{end}"]
        lines.append("SUMMARY:" + ics_escape(summary))
        if desc:
            lines.append("DESCRIPTION:" + ics_escape(desc))
        if url:
            lines.append("URL:" + url)
        lines.append("END:VEVENT")
        ev.append("\r\n".join(fold(x) for x in lines))

    for i, (d1, z1, t1, d2, z2, t2, title) in enumerate(FLIGHTS):
        add(f"flight{i}", "✈ " + title, ics_time(d1, parse_time(t1), z1), ics_time(d2, parse_time(t2), z2),
            "Local times: departs " + t1 + " " + z1 + ", lands " + t2 + " " + z2 + ".")
    for d in trip.DAYS:
        url = SITE_URL + "#" + day_id(d)
        nxt = (date_of(d["date"]) + dt.timedelta(days=1)).strftime("%Y%m%d")
        label = (f"Cruise day {d['cruise_day']}: " if d["cruise_day"] else "") + d["place"]
        add("day-" + d["date"], label, d["date"].replace("-", ""), nxt, d["summary"] + "\nTonight: " + d["stay"] + "\n" + url, True, url)
        hours = d.get("hours", "")
        m = re.match(r"(\d.*?[ap]m)\s*[–-]\s*(\d.*?[ap]m)", hours)
        if d["kind"] == "port" and m:
            note = "Ashore by tender. " if d.get("tender") else ""
            add("port-" + d["date"], f"🚢 In port: {d['place']} (all aboard {m.group(2)})",
                ics_time(d["date"], parse_time(m.group(1)), "AST"), ics_time(d["date"], parse_time(m.group(2)), "AST"),
                note + "Ship's time (Atlantic, UTC−4).\n" + url, url=url)
        for j, (t, title, note, cost) in enumerate(d["items"]):
            if not title.startswith("Booked:"):
                continue
            mt = re.match(r"(\d.*?[ap]m)\s*[–-]\s*(\d.*?[ap]m)", t or "")
            if not mt:
                continue
            add(f"x-{d['date']}-{j}", "⭐ " + title[len("Booked:"):].strip(),
                ics_time(d["date"], parse_time(mt.group(1)), "AST"), ics_time(d["date"], parse_time(mt.group(2)), "AST"),
                (note or "") + "\n" + url, url=url)
    body = "\r\n".join(["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Cindy and Paul//Caribbean 2027//EN",
                         "CALSCALE:GREGORIAN", "METHOD:PUBLISH", "X-WR-CALNAME:Cindy & Paul in the Caribbean"] + ev + ["END:VCALENDAR"]) + "\r\n"
    with open(os.path.join(ROOT, "trip.ics"), "w", newline="") as f:
        f.write(body)
    return len(ev)


# ---------------------------------------------------------------- page
CSS = open(os.path.join(HERE, "site.css")).read()
LEAFLET_CSS = open(os.path.join(HERE, "vendor", "leaflet.css")).read()
FONTS_CSS = open(os.path.join(HERE, "fonts.css")).read()
JS = open(os.path.join(HERE, "site.js")).read()


def trip_days_data():
    return [{"date": d["date"], "place": d["place"], "href": "#" + day_id(d), "n": d["cruise_day"]} for d in trip.DAYS]


THEME_BOOT = ("(function(){try{var t=localStorage.getItem('cp-theme');"
              "if(t==='dark'||t==='light')document.documentElement.setAttribute('data-theme',t);}catch(e){}})();")


def page():
    tabs = [("itinerary", "Itinerary"), ("days", "Day by day"), ("maps", "Maps"), ("ship", "The ship"), ("money", "Money"), ("budget", "Budget"), ("todo", "To do")]
    return f"""<!DOCTYPE html>
<html lang="en" data-theme="light"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Cindy &amp; Paul in the Caribbean</title>
<meta name="description" content="Cindy and Paul's Exotic Caribbean In Depth cruise on Seabourn Ovation, January 2027: itinerary, day plans, maps, ship guide and planning to-do list.">
<meta name="theme-color" content="#0f8f9e">
<link rel="manifest" href="manifest.webmanifest"><link rel="icon" href="icons/icon-192.png"><link rel="apple-touch-icon" href="icons/icon-180.png">
<meta name="apple-mobile-web-app-capable" content="yes"><meta name="apple-mobile-web-app-title" content="Cindy &amp; Paul">
<script>{THEME_BOOT}</script>
<style>{FONTS_CSS}</style><style>{LEAFLET_CSS}</style><style>{CSS}</style></head><body>
<div class="sea"><div class="sea-in">
<div class="mode" role="group" aria-label="Color theme"><button type="button" data-mode="light" aria-pressed="true">☀ Beach</button><button type="button" data-mode="dark" aria-pressed="false">☾ Moonlight</button></div>
<p class="eyebrow">January 7 – 24, 2027</p><h1>Cindy &amp; Paul in the Caribbean</h1>
<p class="lede">Cindy and Paul's fourteen nights on Seabourn Ovation, round trip from Barbados: "Exotic Caribbean In Depth," with eleven islands, two sea days and a night in Atlanta each way.</p>
<div class="today" id="today" hidden></div>
<p class="links"><a class="sheet" href="{trip.SHEET_URL}">Open the planning sheet in Google Sheets</a><a class="sheet pdfdl" href="trip.pdf" download>Download the trip as a PDF</a></p></div></div>
<header><nav class="tabs" aria-label="Sections">{"".join(f'<a href="#{k}" data-tab="{k}">{v}</a>' for k, v in tabs)}</nav></header>
<main>{view_itinerary()}{view_days()}{view_maps()}{view_ship()}{view_money()}{view_budget()}{view_todo()}</main>
<footer>Planning draft. {e(TODAY_NOTE)}; times, prices and port details may change. Port times are the ship's local time (Atlantic, UTC−4). Weather averages and forecasts from <a href="https://open-meteo.com/">Open-Meteo</a>.</footer>
<script src="vendor/leaflet.js"></script>
<script>window.TRIP_MAP = {json.dumps(live_map_data(), ensure_ascii=False)};
window.TRIP_DAYS = {json.dumps(trip_days_data(), ensure_ascii=False)};</script>
<script>{JS}</script></body></html>
"""


SW_TEMPLATE = """// Generated by tools/build.py. Caches the site so it opens without Wi-Fi.
const VERSION = "%(version)s";
const CORE = %(files)s;
self.addEventListener("install", e => {
  e.waitUntil(caches.open("site-" + VERSION).then(c => c.addAll(CORE)).then(() => self.skipWaiting()));
});
self.addEventListener("activate", e => {
  e.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => k.startsWith("site-") && k !== "site-" + VERSION).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener("fetch", e => {
  const req = e.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.hostname === "tile.openstreetmap.org") {
    // map tiles: use a saved copy if we have one, otherwise fetch and keep it (up to ~400 tiles)
    e.respondWith(caches.open("tiles").then(async c => {
      const hit = await c.match(req);
      if (hit) return hit;
      const res = await fetch(req);
      if (res.ok) { c.put(req, res.clone()); c.keys().then(k => { if (k.length > 400) c.delete(k[0]); }); }
      return res;
    }).catch(() => caches.match(req)));
    return;
  }
  if (url.origin !== location.origin) return;
  if (req.mode === "navigate") {
    // the page itself: try the network first so updates show up, fall back to the saved copy offline
    e.respondWith(fetch(req).then(res => {
      const copy = res.clone(); caches.open("site-" + VERSION).then(c => c.put("./", copy)); return res;
    }).catch(() => caches.match("./")));
    return;
  }
  e.respondWith(caches.match(req, { ignoreSearch: true }).then(hit => hit || fetch(req)));
});
"""


def write_sw():
    import hashlib
    files = ["./", "manifest.webmanifest", "trip.ics"]
    for sub in ("maps", "fonts", "vendor", "icons", "photos"):
        d = os.path.join(ROOT, sub)
        if os.path.isdir(d):
            files += [f"{sub}/{f}" for f in sorted(os.listdir(d)) if not f.endswith(".json")]
    files = [f for f in files if f == "./" or os.path.exists(os.path.join(ROOT, f))]
    h = hashlib.sha1()
    for f in ["index.html"] + files[1:]:
        with open(os.path.join(ROOT, f), "rb") as fh:
            h.update(fh.read())
    with open(os.path.join(ROOT, "sw.js"), "w") as fh:
        fh.write(SW_TEMPLATE % {"version": h.hexdigest()[:12], "files": json.dumps(files, indent=0)})


def fragment():
    """The same page without the document wrapper, for publishing as a claude.ai artifact."""
    full = page()
    head = full[full.index("<title>"):full.index("</head>")]
    body = full[full.index("<body>") + len("<body>"):full.index("</body>")]
    return ('<meta name="claude:viewport-fit-sides" content="cover">\n' + head + body + "\n")


if __name__ == "__main__":
    with open(os.path.join(ROOT, "index.html"), "w") as f:
        f.write(page())
    print("wrote", os.path.join(ROOT, "index.html"), "and", write_ics(), "calendar events")
    write_sw()
    if len(sys.argv) > 2 and sys.argv[1] == "--artifact":
        with open(sys.argv[2], "w") as f:
            f.write(fragment())
        print("wrote", sys.argv[2])

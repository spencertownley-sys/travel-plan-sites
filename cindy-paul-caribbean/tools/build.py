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
    for i, k in enumerate(order, 1):
        name = trip.PORTS[k][0]
        x, y = coords[k]
        days = PORT_DATES.get(k, [])
        when = " & ".join(short_date(d["date"])[4:] for d in days)
        nums = "·".join(str(d["cruise_day"]) for d in days if d["cruise_day"])
        tx, anchor = label_attrs(x, y, pr.w, r)
        if k == "jvd":
            tx, anchor = x - 50, "start"
        elif k == "stkitts":
            tx, anchor = x - r - 6, "end"
        dy = {"jvd": -34, "tortola": 22, "montserrat": 10, "antigua": -8}.get(k, 0)
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
    out.append(SVG_CLOSE)
    return "".join(out), "".join(legend)


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
            tag = '<em class="tag bk">Booked</em>' if booked else ('<em class="tag sea">Sea day</em>' if d["kind"] == "sea" else
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


def render_day(d, i):
    sid = day_id(d)
    dd = date_of(d["date"])
    out = [f'<article class="dayview" id="{sid}" hidden>']
    eyebrow = long_date(d["date"])
    if d["cruise_day"]:
        eyebrow += f" · Cruise day {d['cruise_day']} of 15"
    out.append(f'<p class="eyebrow">{e(eyebrow)}</p><h2 class="dayh">{e(d["place"])}</h2>')
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
        if isl.get("rain"):
            facts.append(("Rain", isl["rain"]))
        extra = ('<dl class="facts col">' + "".join(f"<div><dt>{e(k)}</dt><dd>{e(v)}</dd></div>" for k, v in facts) + "</dl>"
                 '<h4>Highlights</h4><ul class="hl">' + "".join(f"<li>{e(x)}</li>" for x in isl["highlights"]) + "</ul>")
        h.append(f'<section><h2>{e(isl["name"])}</h2>')
        h.append(map_block(f"m-{isl['id']}", {"map": isl["map"], "points": isl["points"]}, blurb=isl["blurb"], extra=extra))
        h.append("</section>")
    h.append("</div>")
    return "".join(h)


def view_ship():
    s = trip.SHIP
    h = ['<div class="view" id="v-ship">']
    h.append('<section><h2>Seabourn Ovation</h2><p class="blurb">A small, all-suite luxury ship — about 600 guests — '
             'so tenders are quick, the crew learns your name, and most drinks, dining and tips are included.</p>')
    h.append('<div class="stays">' + "".join(f"<div><b>{e(big)}</b><span>{e(cap)}</span></div>" for big, cap in s["facts"]) + "</div></section>")
    h.append(f'<div class="callout caviar"><h4>Caviar in the Surf</h4><p>{e(s["caviar"])}</p></div>')

    def deflist(title, rows):
        return (f"<section><h2>{e(title)}</h2><dl class='ship'>" +
                "".join(f"<div><dt>{e(a)}</dt><dd>{e(b)}</dd></div>" for a, b in rows) + "</dl></section>")
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
    h.append(f'<p class="blurb">Planning tasks from the sheet\'s Actions tab, plus loose ends spotted while building this site. '
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
    # costs
    total_cost = sum(c[2] for c in trip.COSTS)
    h.append('<section><h2>Bookings and costs</h2><p class="blurb">From the sheet\'s Costs tab, plus excursion prices from the itinerary tab.</p>')
    h.append('<div class="days costs"><div class="day head"><span>What</span><span>Item</span><span>Cost</span><span>Notes</span></div>')
    for cat, item, amt, note in trip.COSTS:
        h.append(f'<div class="day"><span class="d">{e(cat)}</span><span data-k="Item">{e(item)}</span>'
                 f'<span class="num" data-k="Cost">${amt:,.2f}</span><span data-k="Notes">{e(note)}</span></div>')
    h.append(f'<div class="day total"><span class="d">Total</span><span></span><span class="num">${total_cost:,.2f}</span><span></span></div></div></section>')
    h.append("</div>")
    return "".join(h)


# ---------------------------------------------------------------- page
CSS = open(os.path.join(HERE, "site.css")).read()
LEAFLET_CSS = open(os.path.join(HERE, "vendor", "leaflet.css")).read()
JS = open(os.path.join(HERE, "site.js")).read()


def page():
    tabs = [("itinerary", "Itinerary"), ("days", "Day by day"), ("maps", "Maps"), ("ship", "The ship"), ("todo", "To do")]
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Cindy &amp; Paul in the Caribbean</title>
<meta name="description" content="Cindy and Paul's Exotic Caribbean In Depth cruise on Seabourn Ovation, January 2027: itinerary, day plans, maps, ship guide and planning to-do list.">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,700&family=Source+Sans+3:wght@400;600;700&display=swap" rel="stylesheet">
<style>{LEAFLET_CSS}</style><style>{CSS}</style></head><body>
<div class="sea"><div class="sea-in"><p class="eyebrow">January 7 – 24, 2027</p><h1>Cindy &amp; Paul in the Caribbean</h1>
<p class="lede">Cindy and Paul's fourteen nights on Seabourn Ovation, round trip from Barbados: "Exotic Caribbean In Depth," with eleven islands, two sea days and a night in Atlanta each way.</p>
<a class="sheet" href="{trip.SHEET_URL}">Open the planning sheet in Google Sheets</a></div></div>
<header><nav class="tabs" aria-label="Sections">{"".join(f'<a href="#{k}" data-tab="{k}">{v}</a>' for k, v in tabs)}</nav></header>
<main>{view_itinerary()}{view_days()}{view_maps()}{view_ship()}{view_todo()}</main>
<footer>Planning draft. {e(TODAY_NOTE)}; times, prices and port details may change. Port times are the ship's local time (Atlantic, UTC−4).</footer>
<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.js"></script>
<script>window.TRIP_MAP = {json.dumps(live_map_data(), ensure_ascii=False)};</script>
<script>{JS}</script></body></html>
"""


def fragment():
    """The same page without the document wrapper, for publishing as a claude.ai artifact."""
    full = page()
    head = full[full.index("<title>"):full.index("</head>")]
    body = full[full.index("<body>") + len("<body>"):full.index("</body>")]
    return ('<meta name="claude:viewport-fit-sides" content="cover">\n' + head + body + "\n")


if __name__ == "__main__":
    with open(os.path.join(ROOT, "index.html"), "w") as f:
        f.write(page())
    print("wrote", os.path.join(ROOT, "index.html"))
    if len(sys.argv) > 2 and sys.argv[1] == "--artifact":
        with open(sys.argv[2], "w") as f:
            f.write(fragment())
        print("wrote", sys.argv[2])

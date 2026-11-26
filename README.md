# travel-plan-sites

Static microsites for family trips. Each trip lives in its own folder and works as plain HTML: open `index.html` directly, or host the repo on any static host.

| Trip | Folder |
| --- | --- |
| Caribbean Cruise 2027 (Seabourn Ovation, Jan 7–24, 2027) | [`caribbean-2027/`](caribbean-2027/) |

## Caribbean Cruise 2027

Built from the "2027 Caribbean Cruise" Google Sheet. Tabs: Itinerary, Day by day (one page per day with schedule and maps), Maps (full route, flights, and every island), The ship, and To do (planning checklist + bookings and costs).

To update it:

```bash
cd caribbean-2027
python3 tools/build.py          # rebuild index.html after editing tools/trip.py
python3 tools/render_maps.py    # only if map areas (MAPS bboxes) change; needs Pillow
```

- `tools/trip.py`: all trip content (days, places, to-dos, costs, ship info).
- `tools/build.py`, `tools/site.css`, `tools/site.js`: the page generator.
- `maps/`: pre-rendered basemaps (© OpenStreetMap contributors) so the site works offline, e.g. on ship Wi-Fi.

To-do checkmarks are saved in each viewer's browser only.

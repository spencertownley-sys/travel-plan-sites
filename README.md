# travel-plan-sites

Static microsites for family trips. Each trip lives in its own folder and works as plain HTML: open `index.html` directly, or host the repo on any static host.

| Trip | Folder |
| --- | --- |
| Cindy & Paul in the Caribbean (Seabourn Ovation, Jan 7–24, 2027) | [`cindy-paul-caribbean/`](cindy-paul-caribbean/), live at https://spencertownley-sys.github.io/travel-plan-sites/cindy-paul-caribbean/ |
| Kathy & Leo in Japan | `kathy-japan` branch, live at https://spencertownley-sys.github.io/travel-plan-sites/ |

## Cindy & Paul in the Caribbean

Built from the "2027 Caribbean Cruise" Google Sheet. Tabs: Itinerary, Day by day (one page per day with schedule and maps), Maps (full route, flights, and every island), The ship, and To do (planning checklist + bookings and costs).

To update it:

```bash
cd cindy-paul-caribbean
python3 tools/build.py          # rebuild index.html after editing tools/trip.py
python3 tools/render_maps.py    # only if map areas (MAPS bboxes) change; needs Pillow
```

- `tools/trip.py`: all trip content (days, places, to-dos, costs, ship info).
- `tools/build.py`, `tools/site.css`, `tools/site.js`: the page generator.
- `maps/`: pre-rendered basemaps (© OpenStreetMap contributors) so the site works offline, e.g. on ship Wi-Fi.

To-do checkmarks are saved in each viewer's browser only.

The Itinerary tab has a zoomable Leaflet map with live OpenStreetMap tiles; the pre-rendered route image sits underneath it, so something still shows when there's no connection.

### Publishing to GitHub Pages

Pages serves the `kathy-japan` branch. To update the live site, copy `cindy-paul-caribbean/index.html` and `cindy-paul-caribbean/maps/*.jpg` into the `cindy-paul-caribbean/` folder on `kathy-japan` and push.

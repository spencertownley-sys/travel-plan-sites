(function () {
  var views = {};
  document.querySelectorAll(".view").forEach(function (v) { views[v.id.slice(2)] = v; });
  var dayviews = document.querySelectorAll(".dayview");

  // Beach (light) / Moonlight (dark) switch; Beach is the default, the choice is remembered on this device
  var root = document.documentElement;
  function setMode(m, save) {
    root.setAttribute("data-theme", m);
    document.querySelectorAll(".mode button").forEach(function (b) {
      b.setAttribute("aria-pressed", b.getAttribute("data-mode") === m ? "true" : "false");
    });
    var tc = document.querySelector('meta[name="theme-color"]');
    if (tc) tc.setAttribute("content", m === "dark" ? "#073847" : "#0f8f9e");
    if (save) { try { localStorage.setItem("cp-theme", m); } catch (e) { /* private mode */ } }
  }
  setMode(root.getAttribute("data-theme") === "dark" ? "dark" : "light", false);
  document.querySelectorAll(".mode button").forEach(function (b) {
    b.addEventListener("click", function () { setMode(b.getAttribute("data-mode"), true); });
  });

  // countdown before the trip, "today" during it, welcome home after
  (function () {
    var box = document.getElementById("today");
    var days = window.TRIP_DAYS || [];
    if (!box || !days.length) return;
    var now = new Date();
    var iso = now.getFullYear() + "-" + String(now.getMonth() + 1).padStart(2, "0") + "-" + String(now.getDate()).padStart(2, "0");
    var first = days[0].date, last = days[days.length - 1].date;
    function el(tag, text) { var x = document.createElement(tag); x.textContent = text; return x; }
    if (iso < first) {
      var ms = new Date(first + "T00:00:00") - new Date(iso + "T00:00:00");
      var n = Math.round(ms / 86400000);
      box.appendChild(el("b", n === 1 ? "1 day to go" : n + " days to go"));
      box.appendChild(el("span", "Leaving Seattle on Thursday, January 7"));
    } else if (iso <= last) {
      var i = days.findIndex(function (d) { return d.date === iso; });
      var d = days[i];
      box.appendChild(el("b", "Today: day " + (i + 1) + " of " + days.length));
      box.appendChild(el("span", d.place));
      var a = el("a", "Open today's plan →"); a.href = d.href; box.appendChild(a);
    } else {
      box.appendChild(el("b", "Welcome home!"));
      box.appendChild(el("span", "The trip ran January 7–24, 2027."));
    }
    box.hidden = false;
  })();

  // live forecast for a day, from about 2 weeks out (Open-Meteo, free, no key); averages stay if offline
  var WX = {0: ["☀️", "Sunny"], 1: ["🌤", "Mostly sunny"], 2: ["⛅", "Partly cloudy"], 3: ["☁️", "Cloudy"], 45: ["🌫", "Fog"], 48: ["🌫", "Fog"],
    51: ["🌦", "Light drizzle"], 53: ["🌦", "Drizzle"], 55: ["🌧", "Drizzle"], 61: ["🌦", "Light rain"], 63: ["🌧", "Rain"], 65: ["🌧", "Heavy rain"],
    80: ["🌦", "Passing showers"], 81: ["🌧", "Showers"], 82: ["⛈", "Heavy showers"], 95: ["⛈", "Thunderstorms"], 96: ["⛈", "Thunderstorms"], 99: ["⛈", "Thunderstorms"]};
  var wxDone = {};
  function loadForecast(scope) {
    scope.querySelectorAll(".wx").forEach(function (w) {
      var date = w.getAttribute("data-date");
      if (wxDone[date]) return;
      var days = (new Date(date + "T12:00:00") - new Date()) / 86400000;
      if (days > 15.5 || days < -1 || navigator.onLine === false) return;
      wxDone[date] = true;
      var url = "https://api.open-meteo.com/v1/forecast?latitude=" + w.getAttribute("data-lat") + "&longitude=" + w.getAttribute("data-lon") +
        "&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,wind_speed_10m_max" +
        "&temperature_unit=fahrenheit&wind_speed_unit=mph&timezone=auto&start_date=" + date + "&end_date=" + date;
      fetch(url).then(function (r) { return r.ok ? r.json() : null; }).then(function (j) {
        if (!j || !j.daily || !j.daily.time || !j.daily.time.length) { wxDone[date] = false; return; }
        var d = j.daily, code = d.weather_code[0], wx = WX[code] || ["🌤", "Mixed"];
        var p = w.querySelector(".wx-live");
        p.textContent = "";
        var b = document.createElement("b"); b.textContent = "Forecast " + wx[0]; p.appendChild(b);
        p.appendChild(document.createTextNode(" " + wx[1] + ", " + Math.round(d.temperature_2m_max[0]) + "°F high, " +
          Math.round(d.temperature_2m_min[0]) + "°F low, " + (d.precipitation_probability_max[0] == null ? "" : d.precipitation_probability_max[0] + "% chance of rain, ") +
          "wind " + Math.round(d.wind_speed_10m_max[0]) + " mph."));
        p.hidden = false;
      }).catch(function () { wxDone[date] = false; });
    });
  }

  // money converter (fixed pegs)
  var convIn = document.getElementById("conv-usd");
  if (convIn) {
    var fmt = function (n) { return n.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 }); };
    var pre = { "2.7": "EC$", "2": "Bds$", "1.79": "Cg" };
    var upd = function () {
      var v = parseFloat(convIn.value) || 0;
      document.querySelectorAll(".conv-out b").forEach(function (b) { var r = b.getAttribute("data-rate"); b.textContent = pre[r] + fmt(v * parseFloat(r)); });
    };
    convIn.addEventListener("input", upd); upd();
  }

  // video cards: load YouTube only when tapped
  document.querySelectorAll(".vid").forEach(function (box) {
    var btn = box.querySelector(".vid-play");
    btn.addEventListener("click", function () {
      if (navigator.onLine === false) {
        var note = box.querySelector(".vid-off") || document.createElement("p");
        note.className = "vid-off"; note.textContent = "Videos need an internet connection. Try again when you're back on Wi-Fi.";
        box.appendChild(note); return;
      }
      var f = document.createElement("iframe");
      f.src = "https://www.youtube-nocookie.com/embed/" + box.getAttribute("data-yt") + "?autoplay=1&rel=0&playsinline=1";
      f.title = btn.getAttribute("aria-label").replace("Play video: ", "");
      f.allow = "autoplay; encrypted-media; picture-in-picture; fullscreen";
      f.allowFullscreen = true;
      box.textContent = ""; box.appendChild(f);
    });
  });

  // offline support: cache the site so it opens on the ship without Wi-Fi
  if ("serviceWorker" in navigator && (location.protocol === "https:" || location.hostname === "localhost")) {
    window.addEventListener("load", function () { navigator.serviceWorker.register("sw.js").catch(function () {}); });
  }

  // zoomable route map on the Itinerary tab (Leaflet + OpenStreetMap tiles; the saved route image sits underneath
  // so the map still shows something if tiles can't load, e.g. on ship Wi-Fi)
  var liveMap = null;
  function initLiveMap() {
    var el = document.getElementById("live-map");
    var data = window.TRIP_MAP;
    if (!el || !data || !window.L) return;
    if (liveMap) { liveMap.invalidateSize(); return; }
    el.innerHTML = "";
    el.classList.add("on");
    var map = L.map(el, { scrollWheelZoom: false, zoomSnap: 0.5 });
    liveMap = map;
    map.createPane("fallback").style.zIndex = 150; // below the tile pane (200)
    var fallback = L.imageOverlay(data.fallback.src, data.fallback.bounds, { pane: "fallback" }).addTo(map);
    var tiles = L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 18,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);
    // once live tiles arrive, drop the offline image so it can't show through tile seams
    tiles.once("load", function () { map.removeLayer(fallback); });
    L.polyline(data.route, { color: "#d4512f", weight: 3, opacity: 0.85, dashArray: "8 8" }).addTo(map);
    var pts = [];
    data.ports.forEach(function (p) {
      pts.push([p.lat, p.lon]);
      var icon = L.divIcon({ className: "lm-pin", html: "<span>" + (p.num || "⚓") + "</span>", iconSize: null });
      var m = L.marker([p.lat, p.lon], { icon: icon, title: p.name, keyboard: true }).addTo(map);
      var box = document.createElement("div");
      var b = document.createElement("b"); b.textContent = p.name; box.appendChild(b);
      p.days.forEach(function (d) {
        var a = document.createElement("a"); a.href = d.href;
        a.textContent = d.label + (d.n ? " · cruise day " + d.n : "") + " →";
        box.appendChild(a);
      });
      m.bindPopup(box);
    });
    map.fitBounds(pts, { padding: [24, 24] });
    map.on("click focus", function () { map.scrollWheelZoom.enable(); });
    map.on("mouseout", function () { map.scrollWheelZoom.disable(); });
  }

  function show() {
    var h = (location.hash || "").slice(1);
    var tab = h;
    var day = null;
    if (/^day-/.test(h)) { tab = "days"; day = h; }
    if (!views[tab]) tab = "itinerary";
    if (tab === "days" && !day) day = (dayviews[0] || {}).id;
    for (var k in views) {
      views[k].hidden = k !== tab;
      var a = document.querySelector('.tabs a[data-tab="' + k + '"]');
      if (a) { if (k === tab) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current"); }
    }
    if (tab === "itinerary") initLiveMap();
    if (tab === "days") {
      dayviews.forEach(function (d) { d.hidden = d.id !== day; if (d.id === day) loadForecast(d); });
      document.querySelectorAll(".chips a").forEach(function (c) {
        var on = c.getAttribute("data-day") === day;
        c.setAttribute("aria-current", on ? "true" : "false");
        if (on && c.scrollIntoView) c.scrollIntoView({ block: "nearest", inline: "center" });
      });
      window.scrollTo(0, document.querySelector(".tabs").offsetTop - 8);
    }
  }
  // the "Day by day" tab remembers the last day opened
  var dayTab = document.querySelector('.tabs a[data-tab="days"]');
  function route() {
    var h = (location.hash || "").slice(1);
    if (/^day-/.test(h) && dayTab) dayTab.setAttribute("href", "#" + h);
    show();
  }
  window.addEventListener("hashchange", route);
  route();

  document.querySelectorAll("[data-go]").forEach(function (b) {
    b.addEventListener("click", function () {
      var el = document.getElementById(b.getAttribute("data-go"));
      if (el) el.scrollIntoView({ block: "start" });
    });
  });

  // map markers <-> legend <-> info panel
  function pick(sec, pt) {
    var li = sec.querySelector('li[data-pt="' + pt + '"]');
    if (!li) return;
    sec.querySelectorAll(".sel").forEach(function (x) { x.classList.remove("sel"); });
    li.classList.add("sel");
    sec.querySelectorAll('.mk[data-pt="' + pt + '"]').forEach(function (m) { m.classList.add("sel"); });
    var info = sec.querySelector(".info");
    info.textContent = "";
    var b = document.createElement("b"); b.textContent = li.querySelector("b").textContent;
    var p = document.createElement("p"); p.textContent = li.getAttribute("data-desc") || li.querySelector("small").textContent;
    var a = document.createElement("a"); a.href = li.getAttribute("data-gm"); a.target = "_blank"; a.rel = "noopener";
    a.textContent = "Open in Google Maps ↗";
    info.appendChild(b); info.appendChild(p); info.appendChild(a);
  }
  document.querySelectorAll(".mapsec").forEach(function (sec) {
    sec.querySelectorAll("[data-pt]").forEach(function (el) {
      function go() { pick(sec, el.getAttribute("data-pt")); }
      el.addEventListener("click", go);
      el.addEventListener("keydown", function (e) {
        if (e.key === "Enter" || e.key === " ") { e.preventDefault(); go(); }
      });
    });
    var first = sec.querySelector("li[data-pt]");
    if (first) pick(sec, first.getAttribute("data-pt"));
  });

  // to-do checkboxes, saved per browser
  var KEY = "carib2027-todo";
  var state = {};
  try { state = JSON.parse(localStorage.getItem(KEY) || "{}") || {}; } catch (e) { state = {}; }
  var today = new Date(); today.setHours(0, 0, 0, 0);
  var boxes = document.querySelectorAll(".todo input[type=checkbox]");
  function refresh() {
    var done = 0;
    boxes.forEach(function (b) {
      var li = b.closest("li");
      li.classList.toggle("done", b.checked);
      if (b.checked) done++;
      var due = li.getAttribute("data-due");
      if (due) li.classList.toggle("late", new Date(due + "T00:00:00") < today);
    });
    var p = document.querySelector(".progress");
    if (p) p.textContent = done + " of " + boxes.length + " done.";
  }
  boxes.forEach(function (b) {
    var id = b.getAttribute("data-id");
    b.checked = id in state ? !!state[id] : b.hasAttribute("data-default");
    b.addEventListener("change", function () {
      state[id] = b.checked;
      try { localStorage.setItem(KEY, JSON.stringify(state)); } catch (e) { /* private mode */ }
      refresh();
    });
  });
  refresh();
})();

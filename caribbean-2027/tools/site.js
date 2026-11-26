(function () {
  var views = {};
  document.querySelectorAll(".view").forEach(function (v) { views[v.id.slice(2)] = v; });
  var dayviews = document.querySelectorAll(".dayview");

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
    if (tab === "days") {
      dayviews.forEach(function (d) { d.hidden = d.id !== day; });
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

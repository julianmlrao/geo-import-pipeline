const colors = ["#0a56a3", "#d9480f", "#2b8a3e", "#862e9c"];
const $ = (id) => document.getElementById(id);
const fmt = (v) => (typeof v === "number" ? v.toLocaleString("de-DE") : v ?? "");
let index, map;

async function json(path) { return (await fetch(path)).json(); }
async function text(path) { return (await fetch(path)).text(); }
function el(tag, props = {}, ...kids) { const e = Object.assign(document.createElement(tag), props); e.append(...kids); return e; }

function initMap() {
  map = window.__map = new maplibregl.Map({
    container: "map", center: [13.2, 52.4], zoom: 6.5,
    style: { version: 8, sources: { bm: { type: "raster", tileSize: 256,
      tiles: ["https://sgx.geodatenzentrum.de/wmts_basemapde/tile/1.0.0/de_basemapde_web_raster_grau/default/GLOBAL_WEBMERCATOR/{z}/{y}/{x}.png"],
      attribution: "© GeoBasis-DE / BKG (2026), dl-de/by-2-0 · Daten: siehe Quellen" } },
      layers: [{ id: "bm", type: "raster", source: "bm" }] },
  });
  map.addControl(new maplibregl.NavigationControl());
  const clickable = [];
  map.on("load", () => {
    index.layers.forEach((l, i) => {
      const c = colors[i % colors.length], id = l.source_id;
      map.addSource(id, { type: "geojson", data: `data/${id}.geojson` });
      const ids = [];
      if (l.kind === "polygon") {
        map.addLayer({ id: id + "-f", type: "fill", source: id, paint: { "fill-color": c, "fill-opacity": 0.25 } });
        map.addLayer({ id: id + "-l", type: "line", source: id, paint: { "line-color": c, "line-width": 1 } });
        ids.push(id + "-f", id + "-l"); clickable.push(id + "-f");
      } else if (l.kind === "line") {
        map.addLayer({ id: id + "-l", type: "line", source: id, paint: { "line-color": c, "line-width": 2 } });
        ids.push(id + "-l"); clickable.push(id + "-l");
      } else {
        map.addLayer({ id: id + "-p", type: "circle", source: id, paint: { "circle-color": c, "circle-radius": 3.5, "circle-stroke-color": "#fff", "circle-stroke-width": 0.8 } });
        ids.push(id + "-p"); clickable.push(id + "-p");
      }
      const cb = el("input", { type: "checkbox", checked: true });
      cb.addEventListener("change", () => ids.forEach((x) => map.setLayoutProperty(x, "visibility", cb.checked ? "visible" : "none")));
      const lab = el("label", {}, cb, ` ${l.title} (${l.count})`); lab.style.cssText = `display:block;color:${c}`;
      $("layers").append(lab);
    });
    map.on("click", (e) => {
      const f = map.queryRenderedFeatures(e.point, { layers: clickable })[0];
      if (!f) { $("info").textContent = "Kein Objekt an dieser Stelle."; return; }
      const t = el("table");
      Object.entries(f.properties).forEach(([k, v]) => { const r = t.insertRow(); r.insertCell().textContent = k; r.insertCell().textContent = fmt(v); });
      $("info").replaceChildren(t);
    });
    const g = index.layers.find((l) => l.kind === "polygon");
    if (g) fetch(`data/${g.source_id}.geojson`).then((r) => r.json()).then((d) => {
      const b = new maplibregl.LngLatBounds();
      d.features.forEach((ft) => JSON.stringify(ft.geometry.coordinates).match(/-?\d+\.?\d*,-?\d+\.?\d*/g).forEach((p) => b.extend(p.split(",").map(Number))));
      map.fitBounds(b, { padding: 20, animate: false });
    });
  });
}

function sources() {
  const t = $("srctable");
  t.replaceChildren(el("thead", {}, el("tr", {}, ...["Quelle", "Typ", "Lizenz", "Letzter Import", "Datensätze"].map((h) => el("th", { textContent: h })))));
  const body = el("tbody");
  index.sources.forEach((s) => body.append(el("tr", {},
    el("td", {}, el("strong", { textContent: s.title }), el("br"), el("code", { textContent: s.source_id })),
    el("td", { textContent: s.source_type }), el("td", { textContent: s.license || "–" }),
    el("td", { textContent: s.last_import_at ? new Date(s.last_import_at).toLocaleString("de-DE") : "–" }),
    el("td", { textContent: fmt(s.record_count) }))));
  t.append(body);
}

async function reports() {
  const list = $("replist");
  list.replaceChildren(...index.reports.map((r) => {
    const a = el("a", { href: "#berichte", textContent: `${r.run_id} (${r.status})` });
    a.addEventListener("click", (e) => { e.preventDefault(); showReport(r.run_id); });
    return el("p", {}, a, " · ", el("a", { href: `data/reports/${r.run_id}.json`, textContent: "JSON" }), " · ", el("a", { href: `data/reports/${r.run_id}.md`, textContent: "Markdown" }));
  }));
  if (index.reports[0]) showReport(index.reports[0].run_id);
}

async function showReport(id) {
  const md = await text(`data/reports/${id}.md`);
  $("repview").replaceChildren(el("pre", { textContent: md }));
}

async function config() {
  const box = $("cfg");
  for (const name of index.config) {
    box.append(el("h2", {}, el("code", { textContent: `config/sources/${name}` })), el("pre", { textContent: await text(`data/config/${name}`) }));
  }
}

function route() {
  const h = (location.hash || "#karte").slice(1);
  document.querySelectorAll("main > section").forEach((s) => (s.hidden = s.id !== h));
  document.querySelectorAll("#tabs a").forEach((a) => (a.getAttribute("href") === "#" + h ? a.setAttribute("aria-current", "page") : a.removeAttribute("aria-current")));
  if (h === "karte" && map) setTimeout(() => map.resize(), 0);
}

(async () => {
  index = await json("data/index.json");
  initMap(); sources(); reports(); config();
  window.addEventListener("hashchange", route); route();
})();

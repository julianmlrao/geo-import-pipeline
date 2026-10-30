const el = document.getElementById("map");
const base = el.dataset.base, tiles = el.dataset.tiles;
const colors = ["#0b5cad", "#d9480f", "#2b8a3e", "#862e9c"];
const map = window.__map = new maplibregl.Map({
  container: "map", center: [13.2, 52.4], zoom: 7,
  style: { version: 8, sources: { bm: { type: "raster", tileSize: 256,
    tiles: ["https://sgx.geodatenzentrum.de/wmts_basemapde/tile/1.0.0/de_basemapde_web_raster_grau/default/GLOBAL_WEBMERCATOR/{z}/{y}/{x}.png"],
    attribution: "© GeoBasis-DE / BKG (2026), dl-de/by-2-0 · Daten: siehe Quellen" } },
    layers: [{ id: "bm", type: "raster", source: "bm" }] },
});
map.addControl(new maplibregl.NavigationControl());
const clickable = [];
map.on("load", async () => {
  const layers = await (await fetch(`${base}/api/layers`)).json();
  const box = document.getElementById("layers");
  layers.forEach((l, i) => {
    const color = colors[i % colors.length];
    map.addSource(l.source_id, { type: "vector", minzoom: 0, maxzoom: 14,
      tiles: [`${location.origin}${tiles}/geo_import.source_tile/{z}/{x}/{y}.pbf?src=${l.source_id}`] });
    const ids = [];
    if (l.kind === "polygon") {
      map.addLayer({ id: l.source_id + "-fill", type: "fill", source: l.source_id, "source-layer": "source", paint: { "fill-color": color, "fill-opacity": 0.25 } });
      map.addLayer({ id: l.source_id + "-line", type: "line", source: l.source_id, "source-layer": "source", paint: { "line-color": color, "line-width": 1 } });
      ids.push(l.source_id + "-fill", l.source_id + "-line");
      clickable.push(l.source_id + "-fill");
    } else if (l.kind === "line") {
      map.addLayer({ id: l.source_id + "-line", type: "line", source: l.source_id, "source-layer": "source", paint: { "line-color": color, "line-width": 2 } });
      ids.push(l.source_id + "-line"); clickable.push(l.source_id + "-line");
    } else {
      map.addLayer({ id: l.source_id + "-pt", type: "circle", source: l.source_id, "source-layer": "source", paint: { "circle-color": color, "circle-radius": 3.5, "circle-stroke-color": "#fff", "circle-stroke-width": 0.8 } });
      ids.push(l.source_id + "-pt"); clickable.push(l.source_id + "-pt");
    }
    const lab = document.createElement("label");
    const cb = document.createElement("input"); cb.type = "checkbox"; cb.checked = true;
    cb.addEventListener("change", () => ids.forEach(id => map.setLayoutProperty(id, "visibility", cb.checked ? "visible" : "none")));
    lab.append(cb, ` ${l.title}`); lab.style.color = color; lab.style.display = "block";
    box.append(lab);
  });
  const withExtent = layers.find(l => l.source_id.includes("gemeinden")) || layers[0];
  if (withExtent && withExtent.extent) { const c = withExtent.extent.coordinates[0]; map.fitBounds([c[0], c[2]], { padding: 20 }); }
});
map.on("click", async (e) => {
  const f = map.queryRenderedFeatures(e.point, { layers: clickable.filter(id => map.getLayer(id)) })[0];
  const info = document.getElementById("info");
  if (!f) { info.textContent = "Kein Objekt an dieser Stelle."; return; }
  const rows = await (await fetch(`${base}/api/feature?source=${encodeURIComponent(f.source)}&key=${encodeURIComponent(f.properties.feature_key)}`)).json();
  const t = document.createElement("table");
  rows.forEach(r => {
    const tr = t.insertRow(); tr.insertCell().textContent = r.key; 
    tr.insertCell().textContent = `${typeof r.value === "number" ? r.value.toLocaleString("de-DE") : r.value ?? ""}${r.unit ? " " + r.unit : ""}`;
    tr.insertCell().textContent = r.source;
  });
  info.replaceChildren(t);
});

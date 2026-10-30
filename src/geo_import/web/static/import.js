const form = document.getElementById("importform");
const out = document.getElementById("status");
const base = form.dataset.base;
async function poll() {
  const r = await fetch(`${base}/api/import/status`);
  const s = await r.json();
  if (s.running) { out.textContent = `Lauf ${s.run_id || ""} läuft …`; setTimeout(poll, 3000); }
  else if (s.run_id) { out.innerHTML = `Letzter Lauf: <a href="${base}/reports/${s.run_id}">${s.run_id}</a> (${s.last_status})`; }
}
form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const r = await fetch(`${base}/api/import`, { method: "POST", body: new FormData(form) });
  const j = await r.json();
  if (r.status === 202) { out.textContent = "Import gestartet …"; setTimeout(poll, 2000); }
  else if (r.status === 429) out.textContent = `Gedrosselt: nächster Import in ${Math.ceil(j.retry_after / 60)} min möglich.`;
  else if (r.status === 409) { out.textContent = "Es läuft bereits ein Import."; poll(); }
  else out.textContent = `Fehler: ${j.error || r.status}`;
});
poll();

"""Build landing page, Impressum and Datenschutz into site/ from environment values.

SITE_MODE=pages  static demo on GitHub Pages (no login)
SITE_MODE=server full demo with login (credentials shown on the page)
"""

from __future__ import annotations

import html
import os
from pathlib import Path
from string import Template

SITE = Path("site")
ENV = os.environ.get


def e(value: str) -> str:
    return html.escape(value, quote=True)


def imp(name: str, label: str) -> str:
    value = ENV(f"IMPRESSUM_{name}", "").strip()
    return e(value) if value else f'<span class="placeholder">[{label} fehlt]</span>'


MODE = ENV("SITE_MODE", "pages")
REPO = ENV("REPO_URL", "https://github.com/julianmlrao/geo-import-pipeline")
SITE_URL = ENV("SITE_URL", "https://julianmlrao.github.io/geo-import-pipeline").rstrip("/")
DEMO_HREF = "demo/" if MODE == "pages" else "demo/"
DEMO_USER = ENV("DEMO_USER", "demo")
DEMO_PASSWORD = ENV("DEMO_PASSWORD", "")

QUICKSTART = (
    """git clone %s.git
cd geo-import-pipeline
cp .env.example .env   # set POSTGRES_PASSWORD
docker compose up -d --build
docker compose exec importer geo-import run --all
docker compose exec importer geo-import report"""
    % REPO
)

ARCH_SVG = """<svg viewBox="0 0 880 230" role="img" aria-labelledby="at ad" xmlns="http://www.w3.org/2000/svg">
<title id="at">Architektur</title><desc id="ad">Quellen (WFS, CSV) laufen über Adapter, Prüfung und Transformation in PostGIS; daraus entstehen Bericht, Karte und API.</desc>
<defs><marker id="ar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0L10 5L0 10z" fill="currentColor"/></marker></defs>
<g fill="none" stroke="currentColor" stroke-width="1.6" font-family="system-ui,sans-serif" font-size="15" color="#556070">
<g fill="#f4f6f9" stroke="#8a97a8"><rect x="10" y="20" width="150" height="70" rx="8"/><rect x="10" y="130" width="150" height="70" rx="8"/>
<rect x="215" y="75" width="130" height="80" rx="8"/><rect x="390" y="75" width="150" height="80" rx="8"/><rect x="585" y="75" width="110" height="80" rx="8"/>
<rect x="740" y="10" width="130" height="55" rx="8"/><rect x="740" y="87" width="130" height="55" rx="8"/><rect x="740" y="165" width="130" height="55" rx="8"/></g>
<g fill="#1b2430" stroke="none" text-anchor="middle"><text x="85" y="50">WFS-Dienste</text><text x="85" y="72" font-size="12">GML / GeoJSON</text>
<text x="85" y="160">CSV-Dateien</text><text x="85" y="182" font-size="12">URL oder Datei</text>
<text x="280" y="110">Adapter</text><text x="280" y="132" font-size="12">Paging, Retry</text>
<text x="465" y="110">Prüfung und</text><text x="465" y="132">Transformation</text>
<text x="640" y="110">PostGIS</text><text x="640" y="132" font-size="12">3 Tabellen</text>
<text x="805" y="43">Bericht</text><text x="805" y="120">Karte</text><text x="805" y="197">API</text></g>
<g marker-end="url(#ar)"><path d="M160 55H200V105H213"/><path d="M160 165H200V125H213"/><path d="M345 115H388"/><path d="M540 115H583"/>
<path d="M695 100L738 45"/><path d="M695 115H738"/><path d="M695 130L738 190"/></g></g></svg>"""

STEPS_PAGES = """<ol class="steps">
<li><strong>Demo öffnen.</strong> Die statische Demo braucht keine Anmeldung.<img src="assets/step1.png" alt="Startseite der Demo mit Karte" width="900" height="520" loading="lazy"></li>
<li><strong>Karte ansehen.</strong> Gemeindegrenzen und Hausadressen ein- und ausblenden, ein Objekt anklicken: die Attribute (Einwohner, Fläche, Aktualität) stammen aus der CSV und hängen über den Gemeindeschlüssel an der Geometrie.<img src="assets/step2.png" alt="Karte mit angeklickter Gemeinde und Attributen" width="900" height="520" loading="lazy"></li>
<li><strong>Bericht und Konfiguration lesen.</strong> Der Import-Bericht zeigt neu, geändert, gelöscht je Quelle. Die YAML-Dateien zeigen, dass eine neue Quelle nur Konfiguration ist.<img src="assets/step3.png" alt="Import-Bericht" width="900" height="520" loading="lazy"></li>
</ol>
<p class="note">Die Demo-Daten sind öffentliche Open Data. Diese Seite ist ein statischer Export eines echten Importlaufs. Die Variante mit Datenbank, Login und Import-Knopf startet man selbst per Docker Compose (siehe „Selbst ausprobieren“).</p>"""

STEPS_SERVER = """<ol class="steps">
<li><strong>Demo öffnen.</strong> Über „Live-Demo öffnen“ erscheint die Anmeldung.<img src="assets/step1.png" alt="Anmeldeseite" width="900" height="520" loading="lazy"></li>
<li><strong>Mit diesen Daten anmelden.</strong>
<div class="cred"><span>Benutzer</span><code id="cu">$user</code><span>Passwort</span><code id="cp">$password</code></div>
<button class="copy" data-copy="#cp" type="button">Kopieren</button>
<img src="assets/step2.png" alt="Quellenübersicht nach der Anmeldung" width="900" height="520" loading="lazy"></li>
<li><strong>Karte, Berichte und Import ausprobieren.</strong> Karte mit Attributen je Objekt, Berichte je Lauf, Import-Knopf (gedrosselt).<img src="assets/step3.png" alt="Karte mit angeklickter Gemeinde" width="900" height="520" loading="lazy"></li>
</ol>
<p class="note">Die Demo-Daten sind öffentliche Open Data. Der Zugang ist nur lesend; Importe sind gedrosselt (höchstens ein Lauf je 10 Minuten).</p>"""

INDEX = Template("""<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>geo-import-pipeline – Import von WFS- und CSV-Geodaten nach PostGIS</title>
<meta name="description" content="Konfigurierbare Open-Source-Import-Pipeline für WFS- und CSV-Geodaten nach PostgreSQL/PostGIS mit Import-Bericht, Docker und Tests.">
<meta property="og:type" content="website">
<meta property="og:title" content="geo-import-pipeline">
<meta property="og:description" content="Konfigurierbare Open-Source-Import-Pipeline für WFS- und CSV-Geodaten nach PostgreSQL/PostGIS.">
<meta property="og:image" content="$site_url/assets/og.png">
<meta property="og:url" content="$site_url/">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='6' fill='%230a56a3'/%3E%3Cpath d='M7 22l6-12 6 8 6-10' stroke='white' stroke-width='3' fill='none'/%3E%3C/svg%3E">
<link rel="stylesheet" href="assets/style.css">
</head>
<body>
<header class="hero"><div class="wrap">
<h1>geo-import-pipeline</h1>
<p>Liest Geodaten aus WFS-Diensten und CSV-Dateien ein, prüft und transformiert sie und schreibt sie in ein einheitliches PostGIS-Datenmodell. Nach jedem Lauf entsteht ein Import-Bericht.</p>
<div class="btns"><a class="btn primary" href="$demo_href">Live-Demo öffnen</a><a class="btn" href="$repo">Quellcode auf GitHub</a></div>
</div></header>
<main class="wrap">
<h2>Was es kann</h2>
<ul class="feat">
<li><strong>WFS und CSV:</strong> WFS 1.x/2.0 mit Paginierung, GML und GeoJSON; CSV mit erkanntem Zeichensatz und Trennzeichen, Geometrie aus WKT, Koordinatenspalten oder per Gemeindeschlüssel-Join.</li>
<li><strong>Einheitliches Datenmodell:</strong> drei Tabellen (Metadaten, Geometrien, Attribute) in EPSG:4326, beliebige Attributschemata ohne Schemaänderung.</li>
<li><strong>Import-Bericht je Lauf:</strong> JSON und Markdown mit neu/geändert/gelöscht je Quelle, Laufzeit, Warnungen und Fehlerursachen.</li>
<li><strong>Neue Quellen per Konfiguration:</strong> eine YAML-Datei pro Quelle, keine Codeänderung.</li>
<li><strong>Zeitgesteuert und manuell:</strong> Cron-Ausdrücke im Container, <code>geo-import run</code> auf der Kommandozeile. Fällt eine Quelle aus, laufen die anderen weiter, der Bestand der ausgefallenen bleibt unverändert.</li>
<li><strong>Open Source:</strong> Apache-2.0, nur OSI-lizenzierte Komponenten, Lizenzübersicht im Repository.</li>
</ul>

<h2 id="anmelden">$steps_title</h2>
$steps

<h2>Wie es funktioniert</h2>
<figure>$arch<figcaption class="note">Jede Quelle läuft isoliert in einer eigenen Transaktion. Ein neuer Import ersetzt die Daten derselben Quelle; ein optionaler Modus <code>history</code> behält Vorgängerstände.</figcaption></figure>

<h2>Selbst ausprobieren</h2>
<pre id="qs">$quickstart</pre>
<button class="copy" data-copy="#qs" type="button">Kopieren</button>
<p class="note">Voraussetzung: Docker mit Compose. Der erste Import dauert je nach Antwortzeit der Dienste einige Minuten.</p>

<h2>Datenquellen und Lizenzen</h2>
<ul>
<li>Gemeindegrenzen und Hausadressen: © GeoBasis-DE/LGB, <a href="https://www.govdata.de/dl-de/by-2-0">dl-de/by-2-0</a> (Daten geändert), Dienste <code>vg_wfs</code> und <code>gaz_wfs</code> der Landesvermessung und Geobasisinformation Brandenburg.</li>
<li>Fläche und Einwohner je Gemeinde: © Statistische Ämter des Bundes und der Länder (Destatis), Gemeindeverzeichnis GV-ISys, dl-de/by-2-0, Gebietsstand 30.06.2026.</li>
<li>Hintergrundkarte: © GeoBasis-DE / BKG, basemap.de, dl-de/by-2-0.</li>
<li>Kartenbibliothek MapLibre GL JS (BSD-3-Clause). Weitere Komponenten: <a href="$repo/blob/main/THIRD_PARTY_LICENSES.md">THIRD_PARTY_LICENSES.md</a>.</li>
</ul>
</main>
<footer><div class="wrap"><a href="impressum.html">Impressum</a> · <a href="datenschutz.html">Datenschutz</a> · <a href="$repo">Quellcode (Apache-2.0)</a></div></footer>
<script src="assets/site.js"></script>
</body>
</html>
""")

LEGAL = Template("""<!doctype html>
<html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>$title – geo-import-pipeline</title><link rel="stylesheet" href="assets/style.css"></head>
<body><main class="wrap"><p><a href="./">← Startseite</a></p><h1>$title</h1>$body</main></body></html>
""")


def main() -> None:
    steps = (
        STEPS_PAGES
        if MODE == "pages"
        else Template(STEPS_SERVER).substitute(user=e(DEMO_USER), password=e(DEMO_PASSWORD))
    )
    (SITE / "index.html").write_text(
        INDEX.substitute(
            site_url=SITE_URL,
            demo_href=DEMO_HREF,
            repo=REPO,
            arch=ARCH_SVG,
            steps=steps,
            steps_title="So schauen Sie sich die Demo an"
            if MODE == "pages"
            else "So melden Sie sich an",
            quickstart=e(QUICKSTART),
        ),
        encoding="utf-8",
    )
    impressum = f"""<p>{imp("NAME", "Name")}<br>{imp("ANSCHRIFT", "Anschrift")}</p>
<p>Vertreten durch: {imp("VERTRETEN", "Vertretungsberechtigte Person")}</p>
<p>Registereintrag: {imp("REGISTER", "Registergericht und Nummer")}</p>
<p>Kontakt: {imp("EMAIL", "E-Mail")}</p>
<p>Diese Seite ist ein Demonstrator für das Open-Source-Projekt geo-import-pipeline.</p>"""
    (SITE / "impressum.html").write_text(
        LEGAL.substitute(title="Impressum", body=impressum), encoding="utf-8"
    )
    cookie = (
        "Nach der Anmeldung setzt die Demo ein Session-Cookie, das nur für die Anmeldung "
        "dient und nach acht Stunden oder beim Abmelden verfällt."
        if MODE == "server"
        else "Diese Seite setzt keine Cookies und bindet kein Tracking ein."
    )
    datenschutz = f"""<p>Verantwortlich: {imp("NAME", "Name")}, {imp("EMAIL", "E-Mail")}</p>
<h2>Server-Logs</h2><p>Beim Aufruf verarbeitet der Hosting-Dienst technisch notwendige Daten
(IP-Adresse, Zeitpunkt, aufgerufene Seite, Browserkennung) in Server-Logs. Zweck ist der sichere
Betrieb der Seite. Eine Zusammenführung mit anderen Daten findet nicht statt.</p>
<h2>Cookies</h2><p>{cookie}</p>
<h2>Weitergabe</h2><p>Wir geben keine personenbezogenen Daten an Dritte weiter. Die Hintergrundkarte
lädt Kacheln von sgx.geodatenzentrum.de (BKG); dabei wird Ihre IP-Adresse an diesen Dienst
übermittelt.</p>
<h2>Ihre Rechte</h2><p>Sie haben das Recht auf Auskunft, Berichtigung, Löschung und Beschwerde bei
einer Aufsichtsbehörde.</p>"""
    if MODE == "pages":
        datenschutz += """<h2>Hosting</h2><p>Die Seite wird über GitHub Pages ausgeliefert
(GitHub Inc., USA). Dabei können Zugriffsdaten bei GitHub verarbeitet werden.</p>"""
    (SITE / "datenschutz.html").write_text(
        LEGAL.substitute(title="Datenschutz", body=datenschutz), encoding="utf-8"
    )


if __name__ == "__main__":
    main()

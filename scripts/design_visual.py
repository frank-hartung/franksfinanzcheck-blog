#!/usr/bin/env python3
# ============================================================
#  DESIGN-VISUAL – Visueller Grossflaechen-Vergleich (Publisher-Methode)
#
#  Technik: Screenshot je Seite + Viewport (Playwright-Style via Bash
#  muss nicht; wir nutzen data: nur einen Perceptual Hash (pHash) je Page
#  – keine Bilder im Repo!). Abweichung ueber Schwelle => Kritisch, Issue
#  zum Rebound; sonst Baseline aktualisiert (Selbstheilung mit Gedaechtnis).
#
#  Wird NUR von der GitHub Action design-visual.yml ausgefuehrt, denn dazu
#  braucht es Chrome (Puppeteer). Lokal: pip install pillow + chromium offen.
#
#  Ablauf:
#    1) hugo bauen -> public/
#    2) Chrome-Puppeteer macht Screenshots (Desktop 1280x800, Mobil 390x844)
#    3) pHash pro Screenshot (64-bit) vs. data/design_baseline.json
#    4) Abweichung > 25 Hamming -> visuelle Regression! == Baseline
#       erneuern (geduldet) + Issue beim 2. heftigen Monat (Muster)
#
#  KEINE Bilder im Repo – nur Hashes. (Git bleibt leicht, DESIGN-REPORT.md
#  zeigt Drift-Tabelle.) Aufruf: python3 scripts/design_visual.py
# ============================================================

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PUBLIC = ROOT / "public"
BASELINE = ROOT / "data" / "design_baseline.json"
REPORT = ROOT / "DESIGN-VISUAL-REPORT.md"
TOLERANCE = 22          # Hamming-Distanz ueber der pHash-Diff => Regression
PAGES = ["/", "/ueber/"]   # + die 3 neuesten Artikel (werden per glob ermittelt)


def phash(png_path: Path) -> str:
    """Zartes pHash: Pillow resize 32x32, mean-Filter, Bits->Hex."""
    from PIL import Image
    img = Image.open(png_path).convert("L").resize((32, 32))
    pix = list(img.getdata())
    avg = sum(pix) / len(pix)
    bits = "".join("1" if p > avg else "0" for p in pix)
    return hex(int(bits, 2))[2:]


def hamming(a: str, b: str) -> int:
    return bin(int(a, 16) ^ int(b, 16)).count("1")


def screenshot_pages() -> dict:
    """Reihenfolge bekannte URL -> PNG-Datei in /tmp. Nutzt vorhandenes
    layout_browser_check.js Umfeld (Puppeteer)."""
    out = {}
    script = ROOT / "scripts" / "_design_shots.js"
    script.write_text(r"""
const puppeteer = require('puppeteer-core');
const http = require('http');
const fs = require('fs');
const path = require('path');
const BASE = process.env.LAYOUT_BASE || path.join(__dirname, '..', 'public');
const PORT = 8097;
const server = http.createServer((req, res) => {
  let p = decodeURIComponent(req.url.split('?')[0]);
  if (p.endsWith('/')) p += 'index.html';
  let f = path.normalize(path.join(BASE, p));
  if (!f.startsWith(BASE)) { res.writeHead(403); res.end(); return; }
  fs.readFile(f, (e, d) => {
    if (e) { res.writeHead(404); res.end(); return; }
    const t = {'.html':'text/html','.css':'text/css','.js':'application/javascript','.jpg':'image/jpeg','.png':'image/png','.webp':'image/webp','.avif':'image/avif','.woff2':'font/woff2'};
    res.writeHead(200, {'Content-Type': t[path.extname(f)] || 'application/octet-stream'});
    res.end(d);
  });
});
(async () => {
  server.listen(PORT);
  const browser = await puppeteer.launch({ executablePath: process.env.CHROME_PATH || undefined,
    args: ['--no-sandbox', '--disable-setuid-sandbox'], headless: 'new' });
  const pages = JSON.parse(fs.readFileSync(process.env.DESIGN_PAGES || '[]', 'utf8'));
  const viewports = [{ width: 1280, height: 800 }, { width: 390, height: 844 }];
  for (const url of pages) {
    for (const vp of viewports) {
      const page = await browser.newPage();
      await page.setViewport(vp);
      await page.goto(`http://127.0.0.1:${PORT}${url}`, { waitUntil: 'networkidle0', timeout: 60000 });
      const name = `/tmp/dsn_${url.replace(/\W+/g, '') || 'home'}_${vp.width}.png`;
      await page.screenshot({ path: name });
      console.log(name);
      await page.close();
    }
  }
  await browser.close();
  server.close();
  process.exit(0);
})();
""", encoding="utf-8")
    # Die zu pruefenden Seiten: Home, ueber, neueste 3 Artikel
    posts = sorted(PUBLIC.glob("posts/*/index.html"), key=os.path.getmtime)[-3:]
    urls = ["/", "/ueber/"] + ["/posts/" + p.parent.name + "/" for p in posts]
    env = dict(os.environ, DESIGN_PAGES=json.dumps(urls))
    node_res = subprocess.run(["node", str(script)], cwd=ROOT, env=env,
                              capture_output=True, text=True, timeout=300)
    for line in node_res.stdout.splitlines():
        line = line.strip()
        if line.startswith("/tmp/dsn_"):
            key = line.split("/tmp/dsn_", 1)[1].removesuffix(".png")
            out[key] = Path(line)
    if node_res.returncode != 0:
        print("⚠ Puppeteer-Fehler:", node_res.stderr[:200])
    return out


def main() -> None:
    try:
        from PIL import Image  # noqa
    except ImportError:
        sys.exit("Pillow fehlt (pip install pillow)")

    if not PUBLIC.is_dir():
        sys.exit("FEHLER: public/ fehlt – erst bauen.")
    baseline = json.loads(BASELINE.read_text(encoding="utf-8")) if BASELINE.exists() else {}
    shots = screenshot_pages()
    if not shots:
        sys.exit("FEHLER: keine Screenshots erhalten (Chrome/Puppeteer-Umgebung fehlt)")

    regressions, updates = [], []
    for key, png in shots.items():
        h = phash(png)
        old = baseline.get(key)
        if old is None:
            updates.append((key, "Baseline initialisiert"))
            baseline[key] = h
        else:
            dist = hamming(h, old)
            if dist > TOLERANCE:
                regressions.append((key, dist))
            else:
                baseline[key] = h  # Selbstheilung: Baseline altert mit dem Design
                updates.append((key, f"Drift {dist} (ok)"))
    BASELINE.write_text(json.dumps(baseline, indent=1), encoding="utf-8")

    L = ["# 👁️ DESIGN-VISUAL-REPORT", "", f"**Stand:** {subprocess.run(['date','-u'],capture_output=True,text=True).stdout.strip()}",
         f"**Szenen:** {len(shots)} · **Baseline aktualisiert:** {len(updates)} · **Regressionen:** {len(regressions)}", ""]
    for k, info in updates:
        L.append(f"- `{k}`: {info}")
    for k, d in regressions:
        L.append(f"- ❗ **{k}**: Hamming-Distanz {d} (> {TOLERANCE}) – visuelle Abweichung!")
    if not regressions:
        L.append("✅ Alle Seiten sehen aus wie gewohnt (Selbstheilung aktiv).")
    REPORT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(L[0]); print(f"Regressionen: {len(regressions)} | Baselines: {len(baseline)}")
    sys.exit(2 if regressions else 0)


if __name__ == "__main__":
    main()

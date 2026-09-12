// ============================================================
//  E2E-STATIC-SERVER – zero-dependency Datei-Server für public/
//  ------------------------------------------------------------
//  Rollout 12.09.2026 (Design-Skills-Premium-Integration).
//
//  · Serviert den Hugo-Build aus public/ auf 127.0.0.1:4173
//    (Port via E2E_PORT überschreibbar) – kein Express, kein
//    http-server-Paket: Playwright startet/stopt diesen Server
//    vollautomatisch über die webServer-Konfiguration.
//  · 404: liefert 404.html MIT HTTP-Status 404 zurück (wie
//    GitHub Pages in Produktion) – Grundlage der 404-Tests.
//  · /healthz: Ready-Signal für Playwrights webServer-Check.
//  · Härtung: Pfad-Normalisierung verhindert Traversal
//    (../../etc/passwd), unbekannte MIME-Typen fallen auf
//    application/octet-stream zurück.
//  · Fehler-PRÄVENTION statt Fehlerbehandlung: Fehlt public/
//    (noch nicht gebaut), bricht der Server mit klarer
//    deutscher Anleitung ab statt leerer 404-Kaskade.
// ============================================================

import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const BASE = path.resolve(__dirname, '..', 'public');
const PORT = Number(process.env.E2E_PORT || 4173);

if (!fs.existsSync(path.join(BASE, 'index.html'))) {
  console.error(
    '\n[E2E] public/index.html fehlt – die Website wurde noch nicht gebaut.\n' +
    '      Zuerst bauen:  hugo --destination public\n' +
    '      (oder einfach:  npm run test:e2e  – baut + testet in einem Rutsch)\n'
  );
  process.exit(1);
}

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.js': 'application/javascript; charset=utf-8',
  '.mjs': 'application/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.xml': 'application/xml; charset=utf-8',
  '.txt': 'text/plain; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.webp': 'image/webp',
  '.avif': 'image/avif',
  '.ico': 'image/x-icon',
  '.woff': 'font/woff',
  '.woff2': 'font/woff2',
  '.ttf': 'font/ttf',
  '.mp3': 'audio/mpeg',
  '.webmanifest': 'application/manifest+json',
};

const server = http.createServer((req, res) => {
  const send = (status, file, extraHeaders = {}) => {
    const type = MIME[path.extname(file)] || 'application/octet-stream';
    // HTML/Feed nie cachen (Rebuilds sofort sichtbar), Assets 1 h.
    const cacheable = /\.(avif|webp|jpe?g|png|svg|woff2?|ico|mp3)$/i.test(file);
    res.writeHead(status, {
      'Content-Type': type,
      'Cache-Control': cacheable ? 'public, max-age=3600' : 'no-store',
      ...extraHeaders,
    });
    fs.createReadStream(file)
      .on('error', () => {
        res.writeHead(500, { 'Content-Type': 'text/plain' });
        res.end('Serverfehler beim Lesen der Datei');
      })
      .pipe(res);
  };

  const urlPath = decodeURIComponent((req.url || '/').split('?')[0]);

  if (urlPath === '/healthz') {
    res.writeHead(200, { 'Content-Type': 'text/plain' });
    res.end('ok');
    return;
  }

  let p = path.normalize(path.join(BASE, urlPath));
  if (!p.startsWith(BASE)) {
    res.writeHead(403, { 'Content-Type': 'text/plain' });
    res.end('Verboten');
    return;
  }

  if (fs.existsSync(p) && fs.statSync(p).isDirectory()) {
    p = path.join(p, 'index.html');
  }

  if (fs.existsSync(p) && fs.statSync(p).isFile()) {
    send(200, p);
    return;
  }

  const notFound = path.join(BASE, '404.html');
  if (fs.existsSync(notFound)) {
    send(404, notFound);
    return;
  }
  res.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' });
  res.end('404 – Seite nicht gefunden');
});

server.listen(PORT, '127.0.0.1', () => {
  console.log(`[E2E] Serviere ${BASE} auf http://127.0.0.1:${PORT}`);
});

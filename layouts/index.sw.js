/* ============================================================
   FranksFinanzcheck – Service Worker
   ------------------------------------------------------------
   Langzeit-Caching auf GitHub Pages (Top-Level):

   GitHub Pages setzt für ALLE Inhalte hart "Cache-Control:
   max-age=600" (10 Minuten) und unterstützt KEINE eigenen
   Header (kein _headers, kein .htaccess). Der einzige Weg zu
   dauerhaftem Top-Level-Caching ist ein Service Worker:

   - Alle versionierten Assets (Fonts, Bilder, CSS, JS – URLs mit
     ?v=<SHA>) werden CACHE-FIRST bedient: Erster Besuch lädt
     normal, jeder weitere Besuch kommt SOFORT aus dem lokalen
     Browser-Cache (0 Netzwerk, 0 KiB Übertragung).
   - HTML-Seiten (Navigation) werden NETWORK-FIRST bedient →
     immer aktuell, mit Offline-Fallback.
   - Cache-Generation pro Deploy: Der Commit-SHA (Env
     HUGO_JSDELIVR_SHA) steckt im Cache-Namen. Beim Aktivieren
     einer neuen Generation werden alte Caches gelöscht → keine
     veralteten Assets, kein Speichermüll.
   - Nur EIGENE Origin (first-party) wird gecacht – keine
     Drittanbieter, keine Cookies, keine Datenübertragung.
   - 100 % Datenschutz-konform (siehe Datenschutzerklärung,
     Abschnitt "Lokale Zwischenspeicherung (Service Worker)").
============================================================ */
const VERSION = '{{ getenv "HUGO_JSDELIVR_SHA" | default "dev" }}';
const CACHE = 'ff-assets-' + VERSION;

/* Statische Assets, die cache-first bedient werden */
const ASSET_RE = /\.(woff2?|avif|webp|jpe?g|png|gif|svg|css|js|ico|txt|xml|json)$/;

/* Kritische Fonts direkt bei der Installation precachen: Sie wurden vom
   Browser bereits via Preload geladen und liegen im HTTP-Cache → die
   Install-Fetches kommen aus dem HTTP-Cache (kein Doppel-Download) und
   der ZWEITE Besuch startet sofort aus dem SW-Cache. */
const PRECACHE = [
  '{{ "fonts/inter-variable.woff2" | relURL }}?v={{ getenv "HUGO_JSDELIVR_SHA" | default "dev" }}',
  '{{ "fonts/montserrat-normal-700.woff2" | relURL }}?v={{ getenv "HUGO_JSDELIVR_SHA" | default "dev" }}',
  '{{ "fonts/montserrat-normal-500.woff2" | relURL }}?v={{ getenv "HUGO_JSDELIVR_SHA" | default "dev" }}'
];

self.addEventListener('install', (event) => {
  self.skipWaiting();
  event.waitUntil((async () => {
    const cache = await caches.open(CACHE);
    await Promise.all(PRECACHE.map((u) => cache.add(u).catch(() => {})));
  })());
});

self.addEventListener('activate', (event) => {
  event.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(
      keys.filter((k) => k.startsWith('ff-assets-') && k !== CACHE)
          .map((k) => caches.delete(k))
    );
    await self.clients.claim();
  })());
});

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;

  const url = new URL(req.url);
  /* Nur eigene Origin cachen – nie Drittanbieter */
  if (url.origin !== self.location.origin) return;

  if (req.mode === 'navigate') {
    event.respondWith(networkFirst(req));
    return;
  }
  if (ASSET_RE.test(url.pathname)) {
    event.respondWith(cacheFirst(req));
  }
});

async function cacheFirst(req) {
  const cache = await caches.open(CACHE);
  const hit = await cache.match(req);
  if (hit) return hit;
  const res = await fetch(req);
  if (res.ok) {
    try { await cache.put(req, res.clone()); } catch (e) { /* Speicher voll – egal */ }
  }
  return res;
}

async function networkFirst(req) {
  const cache = await caches.open(CACHE);
  try {
    const res = await fetch(req);
    if (res.ok) {
      try { await cache.put(req, res.clone()); } catch (e) { /* egal */ }
    }
    return res;
  } catch (err) {
    const hit = await cache.match(req);
    if (hit) return hit;
    throw err;
  }
}

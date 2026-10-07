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

   ------------------------------------------------------------
   HÄRTUNG (Vertrag C31, 07.10.2026 – Robustheit Premium)
   ------------------------------------------------------------
   Ein Service Worker sitzt in JEDEM Request der Seite. Damit ist
   er die einzige Komponente, die die ganze Site ausfallen lassen
   kann, ohne dass irgendwo ein Fehler protokolliert wird. Vier
   Befunde sind hier dauerhaft abgestellt:

   H1 FAIL-OPEN   Jeder Cache-Zugriff läuft im Fangnetz. Wirft das
                  Cache-API (voller Speicher, privater Modus,
                  abgeräumte Quota), geht der Request UNVERÄNDERT
                  ins Netz. Vorher galt: Cache-Fehler = Request
                  verloren = weiße Seite für Wiederkehrer.
   H2 OFFLINE     Eine Navigation ohne Netz und ohne Cache-Treffer
                  zeigte die Offline-Seite des Browsers. Jetzt kommt
                  die eigene 404-Seite (bei der Installation
                  vorgeladen) mit Status 503 – Marke, Weg zurück zu
                  den sechs Themenwelten, kein technisches Rätsel.
   H3 RANGE       Anfragen mit Range-Header (Audio spulen, große
                  Downloads, Safari-Videoplayer) gehen immer direkt
                  ins Netz: Das Cache-API bedient Teilantworten
                  nicht zuverlässig (derselbe Grund, aus dem .mp3
                  bewusst nicht gecacht wird).
   H4 EIGENDATEI  /sw.js selbst wird nie cache-first bedient – der
                  Browser verwaltet seine Aktualisierung allein, und
                  eine zwischengespeicherte eigene Datei wäre ein
                  Update, das nicht mehr ankommt.

   Wache: scripts/robustheits_gate.py (R5) · Test: tools/robust.test.mjs
============================================================ */
const VERSION = '{{ getenv "HUGO_JSDELIVR_SHA" | default "dev" }}';
const CACHE = 'ff-assets-' + VERSION;

/* Statische Assets, die cache-first bedient werden */
/* Bewusst OHNE .mp3: Die Audiofassungen sind mehrere Megabyte groß und
   werden über HTTP-Range-Anfragen abgespielt (Spulen, Wiedereinstieg).
   Antworten aus dem Cache-API bedienen Range-Requests nicht zuverlässig –
   ein cache-first auf .mp3 würde das Spulen auf iPhone und Android
   kaputtmachen. Audio bleibt deshalb im nativen Netzwerkpfad des
   Browsers, der Range korrekt unterstützt. Nicht „nachbessern". */
const ASSET_RE = /\.(woff2?|avif|webp|jpe?g|png|gif|svg|css|js|ico|txt|xml|json)$/;

/* Offline-Fangnetz (H2): Die eigene 404-Seite ist bereits fertig gestaltet,
   steht nicht in der Sitemap und kostet keine zusätzliche URL – sie wird bei
   der Installation vorgeladen und ersetzt die Offline-Seite des Browsers. */
const OFFLINE_PFAD = '{{ "404.html" | relURL }}';

/* H4: Der eigene Dateipfad (/sw.js) – einmal berechnet, nicht je Request. */
const EIGEN_PFAD = (function () {
  try { return new URL(self.location).pathname; } catch (e) { return '/sw.js'; }
})();

/* Kritische Fonts direkt bei der Installation precachen: Sie wurden vom
   Browser bereits via Preload geladen und liegen im HTTP-Cache → die
   Install-Fetches kommen aus dem HTTP-Cache (kein Doppel-Download) und
   der ZWEITE Besuch startet sofort aus dem SW-Cache. */
const PRECACHE = [
  '{{ "fonts/inter-variable.woff2" | relURL }}?v={{ getenv "HUGO_JSDELIVR_SHA" | default "dev" }}',
  '{{ "fonts/Inter-Bold.ttf" | relURL }}?v={{ getenv "HUGO_JSDELIVR_SHA" | default "dev" }}',
  OFFLINE_PFAD
];

/* H1 FAIL-OPEN: Der Cache ist ein Zusatz, nie eine Voraussetzung.
   Gibt es ihn nicht (Fehler, Quota, privater Modus), liefert `null` –
   und jeder Pfad darunter geht dann einfach ins Netz. */
async function fach() {
  try {
    if (typeof caches === 'undefined') return null;
    return await caches.open(CACHE);
  } catch (e) {
    return null;
  }
}

async function ablegen(cache, req, res) {
  if (!cache || !res || !res.ok) return;
  try { await cache.put(req, res.clone()); } catch (e) { /* Speicher voll – egal */ }
}

self.addEventListener('install', (event) => {
  /* skipWaiting im Fangnetz: Wirft es (alter Browser, Kontrollverlust),
     darf die Installation trotzdem weiterlaufen. */
  try { self.skipWaiting(); } catch (e) {}
  event.waitUntil((async () => {
    const cache = await fach();
    if (!cache) return;
    /* Jede URL einzeln: ein fehlender Font darf nicht die ganze
       Vorladung (inklusive Offline-Seite) mitreißen. */
    await Promise.all(PRECACHE.map((u) => cache.add(u).catch(() => {})));
  })());
});

self.addEventListener('activate', (event) => {
  event.waitUntil((async () => {
    try {
      const keys = await caches.keys();
      await Promise.all(
        keys.filter((k) => k.startsWith('ff-assets-') && k !== CACHE)
            .map((k) => caches.delete(k).catch(() => {}))
      );
    } catch (e) { /* Aufräumen ist Kür, kein Pflichtteil der Aktivierung */ }
    /* KEIN clients.claim(): Der SW übernimmt die Kontrolle erst beim
       NÄCHSTEN Besuch. Beim allerersten Besuch (SW-Installation) werden
       so keine Requests mitten im Ladevorgang umgeleitet – LCP/Performance
       des Erstbesuchs bleiben unberührt (Lighthouse-messbar). */
  })());
});

/* Ein Deploy kann eine lange laufende Seite abhängt lassen (altes HTML trifft
   neue Assets). Die Seite darf sich selbst befreien, ohne dass jemand neu
   laden muss – dieser Horcher ist der vereinbarte Weg dafür. */
self.addEventListener('message', (event) => {
  if (event && event.data === 'SKIP_WAITING') {
    try { self.skipWaiting(); } catch (e) {}
  }
});

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;

  let url;
  try { url = new URL(req.url); } catch (e) { return; }
  /* Nur eigene Origin cachen – nie Drittanbieter */
  if (url.origin !== self.location.origin) return;

  /* H3 RANGE: Teilantworten gehören dem Browser, nicht dem Cache-API. */
  try { if (req.headers.get('range')) return; } catch (e) {}

  /* H4 EIGENDATEI: /sw.js verwaltet der Browser selbst. */
  if (url.pathname === EIGEN_PFAD) return;

  if (req.mode === 'navigate') {
    event.respondWith(networkFirst(req));
    return;
  }
  if (ASSET_RE.test(url.pathname)) {
    event.respondWith(cacheFirst(req));
  }
});

async function cacheFirst(req) {
  const cache = await fach();
  if (cache) {
    try {
      const hit = await cache.match(req);
      if (hit) return hit;
    } catch (e) { /* Cache unlesbar → Netzweg (H1) */ }
  }
  try {
    const res = await fetch(req);
    await ablegen(cache, req, res);
    return res;
  } catch (err) {
    /* Letzter Versuch aus dem Cache – sonst entscheidet der Browser
       selbst (gebrochenes Bild, nachgeladene Schrift). */
    if (cache) {
      try {
        const spaet = await cache.match(req);
        if (spaet) return spaet;
      } catch (e) {}
    }
    throw err;
  }
}

async function networkFirst(req) {
  const cache = await fach();
  try {
    const res = await fetch(req);
    await ablegen(cache, req, res);
    return res;
  } catch (err) {
    if (cache) {
      try {
        const hit = await cache.match(req);
        if (hit) return hit;
      } catch (e) {}
      /* H2 OFFLINE: keine Verbindung, kein Treffer → eigene Seite statt
         der Offline-Tafel des Browsers. Der Inhalt kommt aus dem Cache,
         der Status sagt ehrlich „nicht geliefert". */
      try {
        const fallback = await cache.match(OFFLINE_PFAD);
        if (fallback) {
          const body = await fallback.text();
          return new Response(body, {
            status: 503,
            statusText: 'Service Unavailable',
            headers: {
              'Content-Type': 'text/html; charset=utf-8',
              'Cache-Control': 'no-store',
              'X-FF-Offline': '1'
            }
          });
        }
      } catch (e) {}
    }
    throw err;
  }
}

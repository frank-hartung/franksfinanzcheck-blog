# CSP-Hermetik: Warum der Audit die Produktion maß — und was jetzt gilt

**Stand:** 21.11.2026 · **Vorgänge:** #1300, #1303, #1295 · **Bereich:** Technik / Layout-Automatisierung
**Auslöser:** Der Auftrag „die CSP der Runner-Umgebung ist veraltet — sie ist nur nicht die dieses Repositories" — plus der offene Punkt „die Edge-Transform-Rule braucht die zwei Domains".

Dieses Dokument beantwortet drei Fragen, die zusammengehören:

1. **Woher** kam die CSP, die der Layout-Audit als Blockade meldete?
2. **Warum** war die erste Antwort („Runner-Umgebung") falsch?
3. **Was** ist jetzt dauerhaft so gebaut, dass dieselbe Fehldiagnose nicht
   wiederkehren kann — und was bleibt außerhalb des Repositories offen?

---

## 1. Der Befund, wörtlich

Der Lauf `44922040488` (Commit `2884d0a4`) meldete vier harte Befunde, je
Seite und Viewport einen:

```
Layout-Audit: http://127.0.0.1:43437/posts/zahnzusatzversicherung-lohnt-sich/ (390x844):
console: Loading the script 'https://static.cloudflareinsights.com/beacon.min.js/vce7018…'
violates the following Content Security Policy directive:
"script-src 'self' 'unsafe-inline' https://challenges.cloudflare.com".
The action has been blocked.
```

Dazu in der Notice derselben Messung:

```
CSP-Beleg: Dokument-Antwort führt default-src 'self'; script-src 'self'
'unsafe-inline' https://challenges.cloudflare.com; style-src 'self'
'unsafe-inline'; img-src 'self' data: https:; font-src …
```

Die URL sagte `127.0.0.1`. Die CSP und der Beacon sagten
`franksfinanzcheck.de`. Genau dieser Widerspruch war der Ansatzpunkt.

---

## 2. Die Ursache: eine Meta-Refresh-Seite hat den Messbrowser in die Produktion geschickt

Die Kette ist vollständig aus Repo-Daten belegbar — sie braucht keine Annahme
über die CI-Umgebung:

| # | Schritt | Beleg im Repository |
|---|---|---|
| 1 | Das Sample nahm **nicht** die neuesten Artikel, sondern die lexikografisch letzten Verzeichnisse. | `buildSampleUrls`: `fs.readdirSync(...).sort().slice(-3).reverse()` — der Kommentar sagte „3 neueste", der Code sortierte alphabetisch. |
| 2 | Diese drei waren `zaehlerstand-…(1)`, `zahnzusatzversicherung-lohnt-sich`, `zinseszinseffekt-formel-erklaert`. | `ls static/posts content/posts \| sort \| tail -3` |
| 3 | Die beiden letzteren sind **Weiterleitungsseiten**, keine Artikel. | `static/posts/<slug>/index.html`: `<meta name="ff-weiterleitung" content="regel-C">` und `<meta http-equiv="refresh" content="0; url=https://franksfinanzcheck.de/pillar/…">` |
| 4 | Erzeugt wurden sie von `scripts/weiterleitungen.py` aus `data/weiterleitungen.yaml` — 251 Stück. | Generator-Kommentar in jeder Datei |
| 5 | Chrome folgte dem Refresh. Der Audit maß die **Produktion** — im selben Tab. | `page.url()` nach `page.goto()`; die Meldung nannte weiterhin die Eingabe-URL. |
| 6 | Die dort sichtbare CSP ist die der Edge-Regel — und zwar der Stand **vor** dem Merge von #1303. | Die beobachtete `script-src`-Zeile enthält `static.cloudflareinsights.com` **nicht**; `static/_headers` enthielt sie seit `65029c7b1`. |

**Ergebnis:** Es gab keine Injektion durch die Runner-Umgebung. Es gab eine
Weiterleitung aus dem Repository in die Produktion — und dort eine Edge-CSP,
die zum Messzeitpunkt tatsächlich veraltet war. Beides ist wichtig: Die
CSP-Beschwerde war **echt**, aber sie beschrieb nicht die Seite unter
`127.0.0.1`.

---

## 3. Die erste Diagnose war falsch — und wird zurückgezogen

In `AUTOMATISIERUNG-PUSH-DIAGNOSE-2026-11-21.md`, Abschnitt 7.5, stand:

> „Die CSP dieser Messung stammt aus der **Runner-Umgebung**, nicht aus dem
> Repository. […] Der nächste Schritt wäre, die Herkunft in der Umgebung
> abzustellen […] — das liegt außerhalb dieses Repositories und braucht einen
> eigenen Auftrag."

Das war eine Ausschlussfolgerung, kein Beleg: Weil der Messserver keine CSP
setzte und die Meta-CSP kein `script-src` hat, blieb „Umgebung" übrig. Der
Schritt, der fehlte, war der naheliegende: **nachsehen, wohin der Browser
eigentlich navigiert.** Die Korrektur steht in Abschnitt 7.6 desselben
Dokuments; dieser Text ist die dauerhafte Fassung.

---

## 4. Was dauerhaft geändert wurde

### 4.1 Der Audit verlässt den lokalen Bau nicht mehr

`scripts/layout_browser_check.js` bricht jede **Hauptnavigation** ab, die eine
andere Herkunft als `127.0.0.1:<port>` hat (`page.setRequestInterception`,
`istEigeneHerkunft`). Zusätzlich wird nach dem Laden geprüft, wo die Messung
steht. Verlässt sie die eigene Herkunft trotzdem, ist das ein
**Werkzeugfehler (Exit 3)** — kein Seitenbefund. Die abgebrochenen Ziele
stehen mit URL im Bericht (`hermetik.fremdnavigationenBlockiert`).

### 4.2 Die CSP der Messung ist die dieses Repositories

Der Messserver liefert die `Content-Security-Policy` aus `static/_headers`
(Regel `/*`) selbst aus. Fehlt sie, wird **nicht** gemessen (Exit 3,
fail-closed). Eine Ausnahme, begründet: `frame-ancestors` wird für die
Messung entfernt. Sie ist eine reine Header-Direktive, regelt das Einbetten
der Seite und würde bei `about:srcdoc` die eigene Referenzmessung blockieren,
ohne etwas über Skripte, Stile oder Verbindungen auszusagen. Im Sollstand
bleibt sie; `blog_header_gate.py` prüft sie offline (S1) und live. Damit prüft der Audit den Sollstand des Repos — nicht den
Kopfzeilen-Zufall der Umgebung. Ein Nonce und ein SHA-256-Kurzform-Digest
reisen mit jeder Antwort; der Bericht weist aus, ob die eigene CSP im Dokument
wiedergefunden wurde (`cspBelege.eigeneImDokument`) und ob eine **fremde** CSP
dazukam (`cspBelege.fremd`, `fremdherkunft`).

**Der Service Worker wird für die Messung umgangen.** Die Seite registriert
`sw.js` (`layouts/index.sw.js`). Ab der zweiten Navigation liefert er die
Antwort — und Puppeteer sieht deren Kopfzeilen nicht mehr. Der erste grüne
CI-Lauf wies deshalb „Kopfzeile auf **1 von 14** Seiten" aus, obwohl der
Messserver sie bei jedem HTML setzte. Mit `page.setBypassServiceWorker(true)`
misst der Audit wieder die Serverantwort: **14 von 14**, 0 Fremd-CSP. Das ist
keine Abschwächung: Der Audit soll die Kopfzeilen aus `static/_headers`
prüfen; das Verhalten des Service Workers prüft `scripts/robustheits_gate.py`
(R5). Im Betrieb reicht `networkFirst()` die Netzantwort unverändert weiter,
die Edge-Kopfzeilen bleiben also erhalten.

### 4.3 Weiterleitungsseiten sind keine Artikelprobe

Das Sample folgt jetzt dem Datumspräfix (`2026-11-21-…`) absteigend statt
alphabetisch. Jede Kandidatendatei wird auf `ff-weiterleitung` bzw. einen
Meta-Refresh auf eine `http(s)`-URL geprüft; solche Seiten werden **nicht**
gemessen und im Bericht als `weiterleitungenAusgelassen` genannt. Das gilt
auch für die Risiko-Seiten aus dem statischen Audit.

### 4.4 Ein CSP-Verstoß ist nur mit Beleg ein Seitenbefund

Die Entscheidung hängt jetzt an drei Bedingungen, in dieser Reihenfolge:

1. Die Messung steht auf der **eigenen** Herkunft.
2. Die **eigene** CSP wurde im Dokument beobachtet.
3. Es kam **keine fremde** CSP dazu.

Nur dann macht ein CSP-Verstoß den Lauf rot. Sonst ist er „unbelegt" und
erscheint als Frühwarnung mit Grund und Herkunft. Das ist die Belegpflicht aus
`push_diagnose.py`, angewandt auf Kopfzeilen.

### 4.5 Der Beweis läuft ohne Browser

`node scripts/layout_browser_check.js --selftest` prüft 38 Fälle ohne Chrome
und ohne Netz: CSP-Parser gegen `static/_headers`, Herkunftsvergleich,
Erkennung der echten Alt-Seite `zinseszinseffekt-formel-erklaert`, Sample-Regel
(Datum gewinnt, Weiterleitung und Altlast ohne Datum fallen raus). Der Schritt
läuft in `layout-ai.yml` **vor** dem teuren Browser-Teil.

---

## 5. Offen — und jetzt messbar: die Edge-Regel im Dashboard (zwei Domains)

Die Transform Rule liegt außerhalb des Repositories. Zwei Dinge fehlen dort
noch, und beide sind ab jetzt **maschinell nachweisbar** statt behauptet:

### 5.1 Der Filter braucht beide Hosts

```
(http.host eq "franksfinanzcheck.de" or http.host eq "www.franksfinanzcheck.de")
```

Fehlt `www`, liefert `www.franksfinanzcheck.de` keine Sicherheits-Header —
kein HSTS, kein `nosniff`, kein `X-Frame-Options`, keine CSP. Der Browser
warnt dabei nicht. Deshalb misst `blog_header_gate.py` seit 21.11.2026
**drei** Ziele: Startseite, Inhaltsseite und `www`. Für `www` gilt die
**erste** Antwort (meist 301) — die Weiterleitung wird nicht verfolgt, sonst
würde die Hauptdomain ein zweites Mal gemessen und die zweite Domain bliebe
ungeprüft.

### 5.2 Die CSP braucht die beiden Beacon-Domains

`static.cloudflareinsights.com` bei `script-src` und
`cloudflareinsights.com` bei `connect-src`. Cloudflare injiziert Web Analytics
an der Edge; ohne die Freigabe blockiert der Browser den Beacon — der Zustand,
der den Audit am 21.11. falsch rot gemacht hat. Fehlt eine der beiden Domains
live, meldet `blog_header_gate.py` jetzt einen **BEFUND** mit genau diesem
Satz, nicht eine allgemeine „CSP unvollständig"-Meldung.

### 5.3 Kopiervorlage und Abnahme

```bash
# 1. Die Anleitung wird aus der A1-Tabelle erzeugt – keine zweite Textkopie.
python3 scripts/cloudflare_edge_freigabe.py --dashboard

# 2. Ohne Netz: Repo ↔ Edge-Vorlage (S1/S2), Meta-CSP, Wachen-Regeln.
python3 scripts/blog_header_gate.py --offline

# 3. Live: drei Ziele, beide Hosts, erste Antwort auf www.
python3 scripts/blog_header_gate.py --live

# 4. Wenn ein API-Token vorhanden ist: Regel, SSL und DNS gegen die API.
python3 scripts/cloudflare_edge_freigabe.py --pruefen
```

**Abnahmekriterium:** Schritt 3 endet mit `OK` (Exit 0) und nennt alle drei
Ziele; Schritt 2 bleibt grün. Solange das Dashboard die alte Regel führt, ist
Schritt 3 ein **BEFUND** — das ist die ehrliche Anzeige des offenen Punktes,
kein Defekt des Werkzeugs.

---

## 6. Nachweis (in dieser Umgebung ausgeführt)

| Prüfung | Ergebnis |
|---|---|
| `node scripts/layout_browser_check.js --selftest` | 38 Fälle grün, davon 25 Hermetik-Fälle |
| `node scripts/layout_browser_check.js --serve-probe` | HTML mit CSP (ohne `frame-ancestors`), statische Datei ohne CSP, Digest + Nonce |
| `python3 -m unittest scripts.tests.test_layout_audit_csp_beleg` | 20 Tests grün |
| `python3 -m unittest scripts.tests.test_blog_header_gate` | 49 Tests grün |
| `python3 scripts/blog_header_gate.py --offline` | grün (S1/S2, Meta-CSP, Wachen-Regeln) |
| `python3 scripts/cloudflare_edge_freigabe.py --selftest` | 8 Fälle grün, inkl. Dashboard-Anleitung mit beiden Hosts |
| `python3 scripts/cloudflare_edge_freigabe.py --dashboard` | enthält beide Hosts und alle acht Kopfzeilen aus A1 |

**Nicht in dieser Umgebung ausgeführt:** der Browser-Teil mit echtem Chrome
(hier nicht installiert) und die Live-Messung gegen die Produktion (kein
Netz-Zugang zu `franksfinanzcheck.de`, kein Cloudflare-Token). Beides ist
ausdrücklich **nicht** behauptet: Der nächste CI-Lauf von `layout-ai.yml`
liefert den Browser-Beleg; `header:check:live` liefert den Live-Beleg, sobald
er ausgeführt wird.

---

## 7. Grenzen, ehrlich benannt

* **Die Produktion ist bis zur Dashboard-Änderung weiter veraltet.** Das Repo
  kann die Edge-Regel nicht setzen (kein Token in dieser Umgebung, Dashboard
  außerhalb des Repositories). Es kann sie aber ab jetzt **messen** und die
  exakte Änderung **kopierfertig** liefern.
* **Der Audit misst den Sollstand, nicht die Edge.** Wenn `static/_headers`
  und die Dashboard-Regel auseinanderlaufen, erkennt das weiterhin
  `blog_header_gate.py --offline` (S1/S2: Datei ↔ Vorlage) und
  `--live` (Vorlage ↔ Edge). Der Browser-Audit prüft bewusst das Repo.
* **Meta-Refresh bleibt ein Ersatz, kein 301.** Die Seiten aus
  `scripts/weiterleitungen.py` sind für Suchmaschinen gedacht; echter
  301 entsteht erst über Cloudflare. Der Audit behandelt sie deshalb als
  Weiterleitung — nicht als Artikel.
* **Die Offline-Antwort des Service Workers trägt keine CSP.** Der 503-Fallback
  in `networkFirst()` setzt nur `Content-Type` und `Cache-Control`; er ist
  damit die einzige Antwort der eigenen Herkunft ohne Sicherheits-Kopfzeilen.
  Der Audit sieht ihn nicht (er misst am SW vorbei), und im Betrieb erscheint
  er nur ohne Netz. Das ist eine benannte Lücke, keine stille: Wer sie
  schließen will, muss die CSP im Worker duplizieren oder aus einer Quelle
  laden – beides ist eine eigene Entscheidung, kein Nebenprodukt dieser
  Messung.
* **`www` kann anders antworten als erwartet.** Die Messung akzeptiert 200
  und 3xx (erste Antwort). Ein 404/5xx auf `www` bleibt STÖRUNG, kein
  Header-Befund — Nicht-Messbarkeit ist kein Sicherheitsbefund.

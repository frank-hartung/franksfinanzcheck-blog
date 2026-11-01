# Sicherheits-Runbook — Einrichtung und belastbare Betriebsnachweise

**Stand:** 24. Oktober 2026 (WF-E813/#815, Highend-Härtung) · **Grundlage:** `SICHERHEITSAUDIT-PREMIUM-2026-10-14.md`
(Findings F-01 bis F-10, Prüfpunkte P-1 bis P-8)

**Wozu diese Datei:** Quellseitige Schutzmaßnahmen und ihre Regressionstests
ersetzen keine Einrichtung in Cloudflare, GitHub oder auf dem eigenen Rechner.
Die Abschnitte A–C beschreiben diese Einrichtung; D beschreibt den nachweisbaren
Betrieb und den Abschluss einer Meldung. Grün im Offline-Lauf belegt nur den
Repo-Stand — niemals funktionierende Live-Header oder einen ausgeführten Deploy.

**Reihenfolge:** A1 → A2 → A3 sind die wirkungsvollsten und dauern zusammen etwa
20 Minuten. B und C sind Feinheiten, P ist Hygiene.

**Nachweisführung:** Nach jedem Schritt den Prüfbefehl ausführen und das
Ergebnis (Zeile, Screenshot) in `docs/SICHERHEITSNACHWEIS-2026-10-15.md`
eintragen. Eine Behauptung ohne Messung ist keine Behauptung.

---

## A. Ohne diese Schritte bleiben Lücken offen

### A1 · Sicherheits-Header aktivieren (Finding F-01) — 🔴 wichtigster Schritt

**Lage:** Die Seite liegt auf GitHub Pages. GitHub Pages **ignoriert
`static/_headers`**. Die Datei trägt seit 27.10.2026 trotzdem die acht
Sicherheits-Kopfzeilen aus A1 (geprüft von `npm run header:check`, Regeln
S1/S2): Sie ist der Migrationsweg für Cloudflare Pages und Netlify, und ohne
sie hätte ein Umzug den Schutz stillschweigend zurückgelassen. Live wirken
die Header aber erst über den Proxy. Deshalb fehlen
auf GitHub Pages HSTS, Clickjacking-Schutz und `nosniff`. Die Meta-CSP im HTML kann
`frame-ancestors` und HSTS nicht liefern — das geht **nur** als HTTP-Header.
Deshalb: Proxy davor, Header per Transform Rule.

**Variante mit einem Griff (seit 19.10.2026, WF-E813 / #809):** Statt drei
Dashboard-Wegen genügt ein Werkzeug, das die Schritte 1–3 kennt, misst und –
ausdrücklich auf Zuruf – herstellt:

```bash
npm run edge:freigabe          # misst DNS-Proxy, SSL-Modus (strict/full) und Regel A1
npm run edge:freigabe:apply    # Preflight → Regel → SSL → DNS → Gegenmessung → lokaler B7-Text
npm run edge:b7                # bestätigt, dass content/datenschutz/index.md auf Proxy umgestellt ist
```

`scripts/cloudflare_edge_freigabe.py` liest den Sollstand aus der Tabelle in
`cloudflare/edge-schutz.md` (eine Quelle), misst gegen die Cloudflare-API (inkl.
`enabled != false`, Host-Filter und `operation == set`) und meldet Exit 0 (im
Soll) / 1 (offen, mit genauem nächsten Schritt) / 2 (Werkzeugfehler). Ein
vorhandenes `Full (strict)` (`strict`) wird akzeptiert und bei `--apply`
**niemals** auf `Full` herabgestuft (#815). Token: `CLOUDFLARE_API_TOKEN` mit
`Zone.DNS:Edit`, `Zone.Settings:Edit`, `Zone.Transform Rules:Edit` für diese
Zone. **Der Apply führt B7 erst nach erfolgreicher API-Gegenmessung aus.**
Danach den geänderten Datenschutztext prüfen und committen.

**Schritt 1 — Proxy einschalten:** Cloudflare-Dashboard → Zone
`franksfinanzcheck.de` → **DNS** → für `franksfinanzcheck.de` und `www` die
Wolke auf **Proxied** (orange).

**Schritt 2 — SSL-Modus prüfen:** **SSL/TLS → Overview** → bevorzugt
`Full (strict)` mit gültigem GitHub-Pages-Ursprungszertifikat, mindestens `Full`.
Ein vorhandenes `Full (strict)` nicht herunterstufen. Niemals `Flexible`:
Das überträgt zwischen Cloudflare und GitHub unverschlüsselt.

**Schritt 3 — Header-Regel:** Die komplette Regel (Filter + acht Kopfzeilen)
steht kopierfertig in `cloudflare/edge-schutz.md`, Abschnitt A1. Einfach
übernehmen.

**Schritt 4 — prüfen:**

```bash
curl -sI https://franksfinanzcheck.de/ | grep -Ei 'strict-transport|x-frame|nosniff|content-security'
npm run header:check:live          # Selbsttest + Live-Messung, Exit 1 bei Befund
npm run edge:freigabe              # dasselbe auf Cloudflare-Ebene (DNS, SSL, Regel)
```

Erwartet: fünf Zeilen (`Strict-Transport-Security`, `X-Content-Type-Options`,
`X-Frame-Options`, `Referrer-Policy`, `Content-Security-Policy`).

**Danach zwingend B7 (Datenschutz anpassen)** — der Proxy ist rechtlich eine
Änderung, nicht nur eine technische.

**Wache:** `.github/workflows/sicherheits-wache.yml`, Job `live`, täglich 06:05
UTC. Sie misst, **klassifiziert** und meldet – und zwar so, dass die Meldung
den nächsten Schritt nennt statt einer Ratliste (Dauerheilung WF-E813,
15.10.2026). Vier Klassen, erkennbar am Exit-Code und an der
Lauf-Zusammenfassung „F-01 · Sicherheits-Header“:

| Klasse | Exit | Bedeutung | Was du tust |
|---|---|---|---|
| **OK** | 0 | beide Ziele gemessen, alle Pflicht-Header im Soll | F-01 belegt; die Meldung schließt erst, wenn zusätzlich Worker und vollständiger Live-Nachweis grün sind (D1) |
| **TEILWEISE** | 0 (Mess-CLI) | ein Ziel gemessen und sauber, ein Ziel nicht erreichbar | kein neuer Header-Befund, aber **kein Abschlussnachweis**. Der abschließende Live-Nachweis bleibt rot; das nicht gemessene Ziel erneut messen. Eine Messung auf dem Haupt-Host belegt nicht die Einrichtung des `www`-Hosts. |
| **BEFUND** | 1 | gemessen, und es fehlt etwas | je nach Diagnose Abschnitt A1 Schritt 1 (Proxy aus) oder Schritt 3 (Regel unvollständig) – der Bericht nennt es ausdrücklich |
| **STOERUNG** | 2 | kein Ziel erreichbar | **kein** Sicherheitsbefund: Erreichbarkeit prüfen, Lauf neu starten |
| **WACHE-FEHLER** | sonst / leer | Prüfung selbst defekt, z. B. fehlender Bericht oder Exit-Code | Workflow/Skript prüfen; keine Edge-Änderung auf Verdacht |

Die Wache heilt transiente Netzfehler vorher selbst (vier Versuche mit
2 s/8 s/30 s Pause, `GET`-Nachfrage, wenn ein Proxy auf `HEAD` mit einem
Fehlerstatus antwortet). Erst was danach noch rot ist, erreicht dich. Eine
Netzstörung wird deshalb nie wieder als „fehlender Header“ gemeldet – das war
der Fehler, der WF-E813 ausgelöst hat.

**Solange A1 nicht aktiv ist, bleibt dieser Lauf rot – das ist gewollt und
kein Code-Fehler.** Genau dafür steht die Diagnose: Fehlt `cf-ray` und
`server: cloudflare` in der Antwort, liegt die Zone nicht hinter dem Proxy,
und der Bericht verweist auf Schritt 1 statt auf die Regel.

---

### A2 · Mengenregeln an der Edge (Finding F-03)

**Lage:** Der Worker hat seit dem 15.10.2026 eigene Mengenklassen und ein
Tagesbudget. Die Edge ist die frühere und billigere Schicht — sie zählt, bevor
das KV-Kontingent überhaupt berührt wird (100.000 Lesevorgänge/Tag im Free-Plan;
eine Anfrage an eine Token-Seite kostet einen, ein Token-Erraten also
Lesevorgänge in Serie).

**Schritt:** Cloudflare-Dashboard → **Security → WAF → Rate limiting rules** →
die vier Regeln aus `cloudflare/edge-schutz.md`, Abschnitt A2 anlegen
(Anmeldung/POST 20/min, Token-Seiten GET 120/min, Newsletter-Seiten 60/min,
Zähler 60/min).

**Prüfen:** Dashboard → **Security → Events**, nach Regelname filtern; danach
`npm run betrieb:check:live` (mit `NEWSLETTER_WORKER_EXPORT_KEY` in der
Umgebung) — der Bericht zeigt Budgetstand, Bot-Schutz-Zustand und die letzten
Exportaufrufe.

---

### A3 · Bot-Schutz des Anmeldeformulars (Finding F-02)

**Lage:** Das Formular war ohne Bot-Schutz; nur Honeypot, Zeitfalle und
IP-Limit. Damit ließen sich fremde Adressen anmelden (Mail-Verstärker), bis das
KV-Schreibkontingent leer war — dann fallen auch Abmeldung und Tagespflege aus.

**Schritt (Paar-Vertrag seit 19.10.2026, WF-E813 / #809):** Site-Key und
Secret sind **ein** Vertrag und werden gemeinsam wirksam:

1. Cloudflare → **Turnstile → Add widget**: Name `FF Newsletter`, Domains
   `franksfinanzcheck.de`, `www.franksfinanzcheck.de`, Modus **Managed**.
2. **Site Key** an **zwei** Stellen eintragen – derselbe Wert:
   `hugo.toml` `params.turnstileSiteKey = "0x4AAA…"` **und**
   `newsletter-worker/wrangler.toml` `TURNSTILE_SITEKEY = "0x4AAA…"` →
   commit → Deploy abwarten. Die Betriebs-Wache vergleicht beide Stellen
   (Spiegel) und meldet jede Abweichung als Fehler.
3. **Secret Key** im Worker hinterlegen:
   `cd newsletter-worker && npx wrangler secret put TURNSTILE_SECRET`

**Warum das Paar:** Erst wenn beide Seiten gesetzt sind (Widget auf der
Website, Secret im Worker), prüft der Worker **fail-closed**. Der
halbgesetzte Zustand „nur Secret“ war der Anmelde-Ausfall vom 15.10.2026:
Jede Anmeldung scheiterte an einer Sicherheitsprüfung ohne Widget – fünf
Tage lang, täglich gemeldet, aber im Code nicht abstellbar. Seitdem heißt
dieser Zustand **„wartet“**: Die Anmeldung läuft weiter (Honeypot,
Zeitfalle, Mengenklassen, Tagesbudget bleiben aktiv), `/healthz` meldet den
Zustand, und die Wache warnt täglich, bis das Paar komplett ist. „Widget
ohne Secret“ bleibt ein **Fehler** (Fassade), keine Warnung.

**Prüfen:** Formular auf `/newsletter/` absenden (Testadresse) → Widget
erscheint, Anmeldung kommt an. Dann:

```bash
NEWSLETTER_WORKER_BASE=https://abos.franksfinanzcheck.de \
NEWSLETTER_WORKER_EXPORT_KEY=… \
NEWSLETTER_WORKER_WRITE_KEY=… python3 scripts/worker_betrieb_wache.py
```

Erwartet: „Turnstile aktiv: Widget ausgeliefert UND Prüfung erzwungen."

**Datenschutz** ist bereits ergänzt (`content/datenschutz/index.md`,
Abschnitt Newsletter: Turnstile, kein Cookie, nur beim Absenden geladen).

---

### A4 · Schlüsselrollen trennen und Jobs in Environments einsperren (Findings F-07, F-08, P-1, P-4)

**Lage:** Der erste F-08-Fix schützte nur `?mit_token=1`. Die Einzelrouten
`/export/token` und `/export/kontakt` gaben mit dem Leseschlüssel weiterhin
Bearer-Token zurück; `/export/versuch` akzeptierte ihn außerdem für
Statusänderungen. Auch ein fehlender Schreibschlüssel fiel auf den Leseschlüssel
zurück. Das war eine echte Umgehung der Rollen-Trennung und ist im Repository
behoben. **Der Worker wurde in dieser Prüfung nicht live deployt; Dashboard-
Secrets und Produktionszustand sind nicht bestätigt.**

**Schritt 1 — zwei zwingend verschiedene Worker-Schlüssel:**

```bash
cd newsletter-worker
openssl rand -hex 32                    # neuen Schreibschlüssel erzeugen
npx wrangler secret put EXPORT_KEY_WRITE  # Wert sicher eingeben
```

In GitHub (Settings → Secrets and variables → Actions):
`NEWSLETTER_WORKER_WRITE_KEY` exakt auf denselben neuen Wert setzen.
Er muss sich von `EXPORT_KEY` / `NEWSLETTER_WORKER_EXPORT_KEY` unterscheiden.
`NEWSLETTER_WORKER_EXPORT_KEY` bleibt ausschließlich der Leseschlüssel.

**Wirkung im gehärteten Code:** Der Leseschlüssel kann Listen/Pending ohne
Token lesen, aber keine Einzeladresse zu einem Token auflösen und keinen
Versandstatus ändern. `/export/token` und `/export/kontakt` verlangen POST;
Token und E-Mail stehen im Request-Body statt in URLs. `EXPORT_KEY_WRITE` fehlt
oder ist identisch? Dann werden Token- und Status-Endpunkte gesperrt und der
Versand bricht fail-closed ab. Es gibt keinen Rückfall und keine Warnungs-
Freigabe.

Nach dem Deploy müssen Worker-Health (`schluesselrollen: getrennt`), ein
kontrollierter Token-Export und die GitHub-Secrets getrennt verifiziert werden.
Bis dahin gilt die Produktionswirkung als **unbestätigt**.

**Schritt 2 — Environments:** Settings → **Environments** → New environment:

| Name | Required reviewer | Deployment branches | Secrets dort ablegen |
|---|---|---|---|
| `cloudflare-produktion` | Frank Hartung | `main` | `CF_WORKERS_DEPLOY_TOKEN`, `CLOUDFLARE_ACCOUNT_ID` |
| `brand-admin` | Frank Hartung | `main` | `BRAND_ADMIN_TOKEN` |
| `backup` | — (keine Required Reviewer; Scheduler) | exakt `main` | `BACKUP_REPO_TOKEN`, `BACKUP_PASSPHRASE` |

**Wichtig für `cloudflare-produktion`:** GitHub kann ein in YAML benanntes
Environment beim ersten Lauf automatisch und **ungeschützt** anlegen. Die
Zeile `environment: cloudflare-produktion` ist keine Freigabe-Policy. In den
Environment-Einstellungen muss deshalb ausdrücklich mindestens ein *Required
Reviewer* hinterlegt, unter *Deployment branches and tags* ausschließlich
`main` als Branch ausgewählt und *Allow administrators to bypass configured
protection rules* deaktiviert sein (`can_admins_bypass: false`). Tags und
weitere Branch-Muster sind nicht zulässig.

Vor jedem Worker-Deploy prüft `scripts/worker_environment_guard.py` diese
read-only über die GitHub-API in einem **separaten Job ohne Environment und
ohne Cloudflare-Secrets** (`actions: read`). Der Secret-tragende Deploy-Job
wartet auf dessen Erfolg und ist zusätzlich auf `refs/heads/main` begrenzt.
Fehlende oder nicht lesbare Policies stoppen den Lauf vor Wrangler; die
Annotation nennt die verletzte Bedingung. Lokal ist nur der Selbsttest möglich:
`python3 scripts/worker_environment_guard.py --selftest`. Der Live-Befehl
`--check` benötigt `GITHUB_REPOSITORY` und einen `GITHUB_TOKEN` mit `actions: read`.

**Schritt 3 — aufräumen:** Das ungenutzte Environment `GITHUB_WORKFLOW_TOKEN`
löschen (Audit P-4: es wird von keinem Workflow verwendet, existiert aber
weiter).

**Schritt 4 — Actions-Token entschärfen (P-4):** Settings → Actions → General →
Workflow permissions: **Read repository contents**; „Allow GitHub Actions to
create and approve pull requests" **aus**.

**Prüfen:** `python3 scripts/worker_betrieb_wache.py --selftest && python3
scripts/worker_betrieb_wache.py --offline` (Repo-Seite), danach einmal
„Cloudflare-Worker deployen" über **Run workflow** starten — der Lauf zeigt, ob
die Umgebung greift.

**Zugang prüfen, ohne zu deployen (WF-829B/#922, seit 29.10.2026):**
Actions → **„Deploy-Zugang prüfen“** → *Run workflow* (`main`, Freigabe im
Environment `cloudflare-produktion`). Der Lauf liest ausschließlich
(`GET /user/tokens/verify` und die bestehenden Script-Einstellungen), legt
nichts an und deployt nichts. Er nennt **alle** offenen Punkte in einem
Durchgang und schreibt ein Dossier („was fehlt, wohin es gehört, welche
Rechte der Token braucht“) in die Job-Zusammenfassung. Ohne diesen Knopf
wäre der Zugang nur über einen Deploy-Anlauf prüfbar – also über den
Fehler selbst. Lokal und ohne Netz: `python3 scripts/worker_zugang.py
--pruefen` zeigt dieselben Klassen (`FEHLT`, `FORMAT`, `UNGUELTIG`,
`RECHT`, `UNBEKANNT`, `BINDUNG`, `NETZ`, `OFFEN`) aus der eigenen Umgebung.

**Die Freigabe einrichten, statt sie nur zu melden (WF-829B/#922, 30.10.2026):**
Bis zum 30.10.2026 konnte das Repository die fehlende Freigabe nur MELDEN.
`scripts/worker_environment_einrichten.py` stellt sie her – mit einem Token,
das Environments schreiben darf (feingranular *Environments: read/write*,
klassisch `repo`), lokal oder aus einem Lauf heraus:

```bash
export GITHUB_TOKEN=…                       # darf Environments lesen UND schreiben
python3 scripts/worker_environment_einrichten.py --pruefen    # Stand je Ziel
python3 scripts/worker_environment_einrichten.py --anwenden \
    --reviewer frank-hartung                                  # setzt, was geht
python3 scripts/worker_environment_einrichten.py --inventur   # alle Environments
```

Der Lauf nennt je Ziel eine Klasse und den einen nächsten Schritt:

| Klasse | Bedeutung | Weg |
|---|---|---|
| `ERFUELLT` | belegt | – |
| `MACHBAR` | fehlt, per GitHub-API setzbar | `--anwenden` |
| `OBERFLAECHE` | fehlt, **nur im Dashboard** setzbar | Settings → Environments → `cloudflare-produktion` → *Allow administrators to bypass configured protection rules* **aus** |
| `ABWEICHUNG` / `UNBEKANNT` | vorhanden, aber nicht von diesem Werkzeug gesetzt (z. B. eine zusätzliche Branch-Regel) | von Hand prüfen |
| `OFFEN` | nicht belegbar – niemals grün | zuerst die Ursache der Unlesbarkeit |

Zwei Grenzen sind gemessen, nicht vermutet:

1. **`can_admins_bypass` ist über keine GitHub-API setzbar.** Die REST-Route
   „Create or update an environment" nimmt ausschließlich `wait_timer`,
   `prevent_self_review`, `reviewers` und `deployment_branch_policy` an
   (`additionalProperties: false` in der veröffentlichten OpenAPI-Beschreibung);
   die GraphQL-Mutation `updateEnvironment` kennt das Feld nicht. Das Werkzeug
   meldet „eingerichtet bis auf einen Schalter" statt „eingerichtet" – ein
   falsches Grün hier würde den Deploy freigeben, den das Gate zu Recht
   blockiert.
2. **Ein Token ohne Schreibrecht scheitert mit HTTP 403** – genau wie das
   Agenten-Token dieses Repositories. Die Meldung nennt das fehlende Recht,
   damit ein Rechtebefund nicht als Code-Regression gelesen wird.

`--anwenden` verschärft ausschließlich: kein `DELETE`, kein Entfernen eines
bestehenden Reviewers, keine Änderung von `wait_timer` oder
`prevent_self_review`. Alle Environments des Repositories listet `--inventur`
(ein Required Reviewer auf `github-pages` würde die Veröffentlichung anhalten –
diese Entscheidung bleibt bewusst beim Menschen).

**Die Freigabe ist ein Klick – und der Wartezustand ist bewacht (01.11.2026):**
Sobald `cloudflare-produktion` einen Required Reviewer trägt und der
Admin-Bypass aus ist, ist jeder Worker-Deploy **zweistufig**. Das ist die
gewollte Wirkung, sie hat aber einen stillen Preis:

> Ein Lauf, der auf Freigabe wartet, wird nicht rot, meldet nichts und altert
> nur. Er belegt dabei den Concurrency-Slot `worker-deploy`; der nächste Push
> reiht sich dahinter ein, und der Nachweis für #922 entsteht nie.

Deshalb gibt es zwei Griffe, die zusammengehören:

1. **Freigeben** – im Lauf *Review deployments* → Environment wählen →
   *Approve and deploy*. Ohne Oberfläche, mit eigenem Token:
   ```bash
   R=frank-hartung/franksfinanzcheck-blog
   gh api "repos/$R/actions/runs/<run_id>/pending_deployments"          # environment_ids lesen
   gh api -X POST "repos/$R/actions/runs/<run_id>/pending_deployments" \
     -F environment_ids[]=<id> -f state=approved \
     -f comment="Produktionsdeploy freigegeben"
   ```
   Abbrechen (`state=rejected`) ist der zweite legitime Ausgang. Was **nicht**
   geht: den Lauf still liegen lassen – er blockiert die Kette.
2. **Sehen, dass es wartet** – `scripts/worker_freigabe_wache.py` liest die
   Läufe von `worker-deploy.yml` und `worker-zugang-pruefen.yml` (nur
   `actions: read`, kein Schreibzugriff) und nennt jeden Lauf, der über der
   Schwelle wartet, mit Alter und Lauf-Link:
   ```bash
   npm run worker:freigabe                     # Standard: 120 Minuten
   python3 scripts/worker_freigabe_wache.py --check --schwelle 45 --md -
   python3 scripts/worker_freigabe_wache.py --selftest        # 20 Fälle, offline
   ```
   Die Sicherheits-Wache führt ihn täglich als Schritt „Wartende
   Deploy-Freigaben“: Exit `1` ist eine **Warnung** (ein Mensch muss handeln,
   die Zusammenfassung trägt den Link), Exit `2` ist **rot** (Zustand nicht
   belegbar – ungeprüft gilt nicht als sauber, C33). Junge Wartung unter der
   Schwelle bleibt still; sie ist normal und kein Befund.

---

### A5 · Automatik-Kette auf dem eigenen Rechner (Finding F-04)

**Lage:** Drei Türen waren offen — Whisper ohne Token (jede besuchte Webseite
konnte Transkriptionen auslösen), drei n8n-Webhooks ohne Authentifizierung,
ein Bridge-Server auf `127.0.0.1:5680`, der jeden POST annahm.

**Schritt 1 — Secrets erzeugen:**

```bash
cd tools/n8n
cp .env.example .env        # falls noch nicht vorhanden
openssl rand -hex 32        # WHISPER_TOKEN
openssl rand -hex 32        # N8N_WEBHOOK_TOKEN
$EDITOR .env                # beide Werte eintragen
```

`docker compose up` **startet nicht mehr**, wenn einer der beiden Werte fehlt
(`${VAR:?…}`) — gewollt: fail-closed statt stiller Öffnung.

**Schritt 2 — n8n-Credentials anlegen:** In n8n → **Credentials**:

- `FF Webhook-Secret` — Typ **Header Auth**, Header-Name `X-Webhook-Secret`,
  Wert = `N8N_WEBHOOK_TOKEN`. Wird von den drei Webhook-Knoten verwendet
  (im Repository bereits verdrahtet).
- `FF Whisper-Token` — Typ **Header Auth**, Header-Name `Authorization`,
  Wert `Bearer <WHISPER_TOKEN>`. Hängt am Knoten „Lokales Whisper".

**Schritt 3 — Workflows neu importieren:** `n8n/workflows/*.json` (und die
identische Kopie in `tools/n8n/workflows/`) erneut importieren, damit die
Credential-Verknüpfungen greifen.

**Prüfen:**

```bash
python3 scripts/n8n_schutz_wache.py                 # Selbsttest + Prüfung
python3 scripts/n8n_bridge.py --selftest            # 5 Gegenproben (401/403/415/413/503)
docker compose exec whisper-api curl -s -o /dev/null -w '%{http_code}\n' \
  -X POST http://localhost:8765/v1/audio/transcriptions   # erwartet: 503/401 ohne Token
```

**Wache:** `scripts/n8n_schutz_wache.py` läuft bei jeder Änderung an
`n8n/`, `tools/n8n/` oder der Bridge (Workflow `sicherheits-wache.yml`).

---

### A6 · Zähler-Härtung (Finding F-10, Nachweis)

**Lage:** Der Klickzähler ist per `curl` fälschbar (Origin-Kopf ist kein
Geheimnis) und schrieb ungefangen in D1 — ein volles Kontingent erzeugte einen
500er im Leserbrowser.

**Bereits behoben im Repo:** `try/catch` um den Schreibpfad (ein Fehler beim
Zählen bricht den Klick nicht mehr), Mengenbegrenzung bleibt, WAF-Regel in A2.

**Rest (F-10b, laut Audit §5 auf „innerhalb 30 Tagen“ terminiert):** ein Nonce
je Artikel (`?n=<HMAC(Slug, Build-SHA)>`) bindet `/e` an die ausgelieferte
`/go/`-Seite. Der Wert entsteht beim Hugo-Bau, der Worker prüft ihn; erst
danach ist die Origin-Prüfung nicht mehr der einzige Herkunftsnachweis. Wenn
der Nonce steht: die 34 Zähler-Tests um den Nonce-Fall erweitern (Muster
`cloudflare/klick-zaehler/test/worker.test.mjs`) und die WAF-Regel aus A2 auf
den `/e`-Pfad nachschärfen.

**Rest-Einschätzung:** Ein gefälschter Zähler verfälscht Statistik, nicht
Sicherheit. Wer ihn zusätzlich härten will: `stats.franksfinanzcheck.de` per
Cloudflare Access hinter die eigene E-Mail legen (dann zählt nur noch, wer
angemeldet ist) — **nicht** empfohlen für den öffentlichen `/go/`-Weg.

---

## B. Datenschutz und Betrieb

### B7 · Datenschutz-Text für den Cloudflare-Proxy (zu A1)

Nach dem Einschalten des Proxys wird `content/datenschutz/index.md`,
Abschnitt 3 („Hosting, Domain und Server-Logfiles") angepasst. **Ersetzen:**

> Diese Website wird von **GitHub Pages** ausgeliefert (…). Die Domain
> franksfinanzcheck.de zeigt direkt auf die Server von GitHub Pages. Zum Stand
> 11. Oktober 2026 ist kein Proxy von Cloudflare vor die Website geschaltet.

**durch:**

> Diese Website wird von **GitHub Pages** ausgeliefert (GitHub, Inc., 88 Colin
> P. Kelly Jr. Street, San Francisco, CA 94107, USA). **Vorgeschaltet ist das
> CDN von Cloudflare, Inc.** (101 Townsend St., San Francisco, CA 94107, USA),
> das Zugriffe entgegennimmt, technisch absichert und beschleunigt. Cloudflare
> verarbeitet dabei technische Zugriffsdaten wie IP-Adresse, Zeitpunkt,
> angeforderte Adresse, Browsertyp und Referrer sowie Sicherheitsmerkmale zur
> Abwehr von Angriffen. Details: Cloudflare-Datenschutzhinweise. Die
> Server-Logfiles und Aufbewahrungsfristen richten sich nach Cloudflare.

Zusätzlich im Abschnitt „Domain und DNS" den Satz „Cloudflare erhält dabei
keine Informationen über Seitenaufrufe" streichen — er stimmt mit Proxy nicht
mehr.

**Mit einem Befehl (seit 24.10.2026, WF-E813 / #815):**
`npm run edge:b7:apply` wendet genau diese Anpassung idempotent auf
`content/datenschutz/index.md` an (Abschnitte 2, 3 und 12); `npm run edge:b7`
prüft den Stand. Zudem warnt `blog_header_gate.py` live automatisch, falls
`cf-ray` aktiv ist, aber `content/datenschutz/index.md` noch den Vor-Proxy-Text
trägt.

**Prüfen:** `grep -n "kein Proxy\|keine Informationen über Seitenaufrufe" content/datenschutz/index.md`
→ muss leer sein.

### B8 · Datenschutz und Cookie-Freiheit nachprüfen (P-5)

- Cloudflare → **Caching → Tiered Cache** aus, **Speed → Optimization →
  „Rocket Loader"** aus (verändert Skripte im Browser — für eine Seite mit
  eigener CSP unnötiges Risiko).
- **Workers KV** liegt in der EU? Workers KV ist an das Konto gebunden; die
  Jurisdiktion ist im Konto zu prüfen und in der Datenschutzerklärung ehrlich zu
  benennen (sie sagt derzeit „Drittländer möglich" — das ist der sichere,
  zutreffende Satz, solange nicht anders belegt).
- **Alarme:** Cloudflare → Notifications → „Usage Based Billing"/„Workers KV
  reads" aktivieren, damit ein Kontingent-Sturm auffällt, bevor er den Dienst
  lahmlegt.

---

## C. Repository — bereits erledigt, hier nur die Nachweise

| Finding | Behebung im Repo | Nachweis |
|---|---|---|
| F-01 | Header-Vorlage + Wache + Proxy-Runbook (A1) | `npm run header:check` |
| F-02 | Turnstile-Baustein (Shortcode, JS, `hugo.toml`), Worker fail-closed, Datenschutz | `npm run test:sicherheit`, `npm run betrieb:check` |
| F-03 | Mengenklassen für alle Routen, Tagesbudget, Melder je Stunde, WAF-Vorlage | `newsletter-worker`: 91 Tests, `npm run betrieb:check` |
| F-04 | Webhook-Auth, Whisper fail-closed, Bridge-Auth, Compose-Pflicht, `.env.example` | `npm run n8n:schutz`, `scripts/n8n_bridge.py --selftest` |
| F-05 | Klartext-Log entfernt (Hash statt Adresse) | Test „Log-Hygiene" im Worker |
| F-06 | `[security]` in `hugo.toml`, Inhalts-Wache mit 13 Proben | `npm run content:check` |
| F-07 | Runbook A4 (Environments, Reviewers, Token) | Dashboard-Audit (P-1) |
| F-08 | Zwei Schlüsselrollen, Export-Protokoll, `mit_token`, Fail-closed im Versand | Worker-Tests + `newsletter_digest`/`_versand`-Selbsttests |
| F-09 | Kanal-Hygiene für Workflow-/Zweignamen, Simulationsfall | `python3 -m unittest scripts.tests.test_alert_scoping` |
| F-10 | `try/catch` um D1-Schreibpfad, Tests für 3 Fehlerarten | `node --test` im Zähler-Ordner |

**Ein Befehl für alles Quellseitige:**

```bash
npm run test:sicherheit
```

---

## P. Prüfpunkte im Dashboard (P-1 bis P-8)

| Nr. | Was | Wo | Prüfung |
|---|---|---|---|
| P-1 | Branch-Protection/Ruleset für `main`: Force-Push aus, Löschen aus, 1 Review, „Require approvals", kein Umgehen für Admins | GitHub → Settings → Rules → Rulesets | API: `gh api repos/:owner/:repo/rulesets` |
| P-2 | Secret Scanning + **Push Protection** an; ggf. „Private Vulnerability Reporting" an | Settings → Code security | Screenshot der Schalter |
| P-3 | Private Vulnerability Reporting aktiv | Settings → Code security | Status „Enabled" |
| P-4 | Actions-Default-Token read-only; keine PR-Erzeugung; unnötiges Environment weg | Settings → Actions → General | erledigt in A4 |
| P-5 | WAF-Regeln, KV-Jurisdiktion, Alarme | Cloudflare | A2, B8 |
| P-6 | Deploy-Drift: `wrangler.toml` enthält Platzhalter-IDs → bei jedem Deploy prüfen | `newsletter-worker/wrangler.toml` | `npm run betrieb:check` |
| P-7 | Tote Tokens widerrufen: `PINTEREST_ACCESS_TOKEN` (siehe `data/secrets_state.json`), alter `GH_PAT` | Anbieter-Dashboards | Token-Liste leer |
| P-8 | `EXPORT_KEY`/`EXPORT_KEY_WRITE` ≥ 32 Zeichen, nicht wiederverwendet | `wrangler secret list` | nur Namen, Werte nirgends im Repo |

---

## D. Live-Nachweis und Abschlussvertrag (WF-E813/#809)

### D1 · Offline-Grün ist kein Produktionsnachweis

**Belegt am 18./19.10.2026:** Die Meldung #798 wurde nach dem grünen Push-Lauf
[39125154809](https://github.com/frank-hartung/franksfinanzcheck-blog/actions/runs/39125154809)
geschlossen, obwohl der Job „Live-Messung“ **skipped** war. Der tägliche Lauf
[39254264963](https://github.com/frank-hartung/franksfinanzcheck-blog/actions/runs/39254264963)
meldete dieselben offenen Prüfpfade erneut als #809. Das war kein Nachweis einer
Heilung, sondern ein falscher Abschluss.

**Seit der Korrektur gilt:**

- `main` und ein erfolgreicher Workflow sind notwendig, reichen aber nicht.
- Nur `schedule` oder `workflow_dispatch` mit erfolgreich ausgeführtem Job
  „Live-Messung (täglich und auf Zuruf)“ dürfen WF-E813 schließen.
- Beide Messschritte, beide Auswertungen und der Schritt
  **„Live-Nachweis abschließen (F-01/F-02/F-03/F-08)“** müssen erfolgreich sein.
  Fehlende/übersprungene Schritte und eine nicht abrufbare Job-Lage schließen
  ausdrücklich **nicht**. Andere Workflows behalten ihren bisherigen Schließpfad.
- Der Nachweis verlangt F-01 **OK** für alle vorgesehenen Ziele mit HTTP 2xx
  und ein vollständiges, authentifiziertes Worker-Betriebsbild. `TEILWEISE`,
  ein fehlender Leseschlüssel und eine öffentliche/alte Health-Antwort genügen
  nicht. Warnungen bleiben sichtbar; sie sind keine ungeprüften Messwerte.
- JSON, Markdown-Bericht und echter Prozess-Exit müssen zusammenpassen.
  Fehlende, alte oder beschädigte Dateien sind **WACHE-FEHLER**, kein neuer
  Sicherheitsbefund. Der Messschritt selbst bleibt neutral und speichert den Exit
  auch unter Bash `-e`; die Auswertung entscheidet.
- Jeder belegte Befund steht einzeln als gegen Kommando-Injektion geschützte
  Check-Annotation in GitHub, außerdem in der Lauf-Zusammenfassung. Bereinigte
  Berichte bleiben sieben Tage als Artefakt `sicherheits-live-nachweis` erhalten.
  Keine rohen Health-Antworten, Export-Einträge, Adressen oder Cookies hochladen.

**Nach Übernahme der Korrektur und Einrichtung nach A1/A3/A4:**

```bash
gh workflow run sicherheits-wache.yml --ref main
```

In Actions beide Live-Auswertungen und den vollständigen Live-Nachweis prüfen.
Erst dieser erfolgreiche Lauf ist der Abschlussbeweis. Ein PR-Merge oder ein
erfolgreicher Offline-Push darf die weiterhin offene Einrichtung nicht erledigen.

### D2 · Worker-Rot ohne Ratespiel eingrenzen

| Klasse | Bedeutung | Nächster Schritt |
|---|---|---|
| **BEFUND** | Vollständiges authentifiziertes Betriebsbild belegt eine Abweichung | Konkrete Annotation abarbeiten: KV-Ausfall, Turnstile-Widerspruch, fehlender/abweichender Tagesdeckel oder sprengendes Schreibbudget; A3/A4. Nie Bot-Schutz entfernen, um Grün zu erzeugen. |
| **STOERUNG** | Kein vollständiges Betriebsbild | Zugang/Netz/Deploy anhand der Annotation prüfen. Auch HTTP 200 mit nur `ok`/`ts` ist ausdrücklich ungeprüft; der öffentliche Healthcheck verrät keinen Schutzstatus. |
| **WACHE-FEHLER** | Prozess, JSON und Bericht passen nicht zusammen | Prüfung reparieren und erneut messen; keine Infrastrukturänderung auf Verdacht. |
| **OK** | Alle verlangten Betriebsfelder wurden gemessen; kein harter Befund | Sichtbare Warnungen beachten. Der Gesamtabschluss braucht zusätzlich F-01 und den vollständigen Live-Nachweis. |

**Vollständiger Health-Vertrag:** `ok` (Boolean), `kv` (`ok`/`fehler`),
`bau` (Build-Stempel aus `newsletter-worker/wrangler.toml`, auch öffentlich in
`/healthz`), `budget.anmeldung_heute`, `budget.anmeldung_max`,
`budget.feedback_max` (Ganzzahlen), `turnstile` (`aktiv`/`wartet`/`inaktiv`),
`schluesselrollen` (`getrennt`/`gemeinsam`) und `exporte` (Liste mit gültigen
HTTP-Statuswerten). Anhand von `bau` trennt die Wache seit #815 deterministisch
zwischen einem übersprungenen/veralteten Worker-Deploy und einem abweichenden
Leseschlüssel (`NEWSLETTER_WORKER_EXPORT_KEY`).
Fehlende oder falsch typisierte Werte werden nicht durch Repo-Sollwerte ersetzt.
Ein geschütztes HTTP-503-JSON mit `ok:false`/`kv:fehler` belegt einen KV-Ausfall;
eine 503-HTML-Seite dagegen nicht. Transiente Netz-/5xx-/429-Störungen werden
begrenzt wiederholt. Weiterleitungen tragen den Leseschlüssel niemals weiter;
der Messzugang geht ausschließlich an `https://abos.franksfinanzcheck.de`.

**Zugang prüfen statt raten (WF-829B/#922, seit 29.10.2026):** Actions →
**„Deploy-Zugang prüfen“** → *Run workflow* (`main`) beantwortet die Frage
„was fehlt?“ ohne Deploy und ohne Wrangler. `scripts/worker_zugang.py`
sammelt in **einem** Lauf: Token hinterlegt? Konto-ID im richtigen Format?
Token aktiv? Leserecht auf die Worker-Einstellungen? Bindung `ABO` bzw. `DB`
eindeutig? Jeder Befund steht einzeln als Annotation und im Dossier der
Step Summary. `OFFEN` heißt ausdrücklich „nicht prüfbar“ – nie „in
Ordnung“. Der Deploy prüft denselben Zugang vorher noch einmal
(`Zugang prüfen (alle Befunde auf einmal, lesend)`); ein fehlendes Feld
kostet deshalb keine zweite Freigabe-Runde mehr. Klassen und Massnahmen:
`python3 scripts/worker_zugang.py --pruefen --md -`.

**Falls der Worker-Deploy fehlt/veraltet ist:**

1. `cloudflare-produktion` nach A4 ausdrücklich absichern: mindestens ein
   Required Reviewer, Deployment-Branches **exakt** `main`, Admin-Bypass aus.
   Seit dem 30.10.2026 ist das **kein reiner Handgriff mehr**:
   `python3 scripts/worker_environment_einrichten.py --anwenden
   --reviewer frank-hartung` setzt Reviewer und Branch-Regel `main`, sofern das
   Token Environments schreiben darf; der dritte Punkt (Admin-Bypass) bleibt
   ein Schalter im Dashboard und wird von `--pruefen` als einziger Rest
   benannt. `scripts/worker_environment_guard.py --check` liest die Policy vor
   dem Secret-tragenden Deploy-Job read-only nach; ohne vollständigen Nachweis
   läuft Wrangler nicht. Das Gate braucht dafür nur den GitHub-Workflow-Token
   mit `actions: read`, keinen Cloudflare-Zugang.
   Täglich sichtbar (Warnstufe, kein Rot) im Live-Lauf der Sicherheits-Wache:
   Schritt „Produktions-Environment – Freigabestand und Drift“. Warnung, nicht
   Befund, weil der Zustand im Repository nicht herstellbar ist – rot wäre ein
   Dauer-Alarm ohne Schließpfad (C14). Nicht belegbar (Exit 2) bleibt rot.
2. Erst danach `CF_WORKERS_DEPLOY_TOKEN` und `CLOUDFLARE_ACCOUNT_ID` sicher im
   Environment hinterlegen; keine Werte in Issues/Chat/Reports schreiben. Der
   Deploy-Zugang benötigt neben dem Schreibrecht auch `Workers Scripts: Read`.
3. Actions → **„Cloudflare-Worker deployen“** → `newsletter-worker` von `main`.
   Seit der Freigabe-Regel hält der Secret-tragende Job an, bis ein Mensch ihn
   freigibt (A4, „Die Freigabe ist ein Klick“). Diesen Halt meldet die
   Sicherheits-Wache täglich als „Wartende Deploy-Freigaben“
   (`npm run worker:freigabe`) – ein wartender Lauf ist kein grüner Deploy,
   sondern der Grund, warum #922 noch offen ist.
   Nach der Environment-Freigabe liest `scripts/worker_ressourcen.py` über den
   Deploy-Zugang die **bestehende produktive Bindung** `ABO` aus `ff-newsletter`
   und setzt deren KV-ID nur für diesen Lauf ein. Eine manuell kopierte
   Repository-Variable ist für diesen Regelbetrieb nicht mehr erforderlich.
4. Der Resolver akzeptiert ausschließlich genau eine passende KV-Bindung mit
   Namen `ABO` und `namespace_id`. Fehlt sie, ist sie mehrdeutig oder fehlt der
   Zugang, bricht der Lauf **vor** Wrangler rot ab. Es wird weder ein Namespace
   erzeugt noch eine andere oder geratene ID verwendet. Eine optional gesetzte
   `KV_NAMESPACE_ID_ABO` bleibt für bewussten Bootstrap möglich; ihr Wert wird
   dann verwendet und nicht still durch eine andere Bindung ersetzt.
5. Der Job `deploy` muss tatsächlich ausgeführt werden, nicht nur der Plan grün
   sein. Auch Push-Deploys ohne kopierte ID kommen jetzt in die Matrix; fehlende
   oder unlesbare Bindungen erzeugen keinen stillen Erfolg. Unmittelbar nach
   `wrangler deploy` prüft der Lauf live gegen `/healthz`, dass der neue
   `BUILD`-Stempel aus `newsletter-worker/wrangler.toml` antwortet. Das
   verschlüsselte Offsite-Backup ist ein separater Vertrag und benötigt seine
   dokumentierte `KV_NAMESPACE_ID_ABO` weiterhin.
6. Danach die Sicherheits-Wache von `main` mit Live-Messung starten. Nur das
   vollständige authentifizierte Betriebsbild bestätigt den neuen Stand.
   Site-Key und Turnstile-Secret bleiben in der Reihenfolge aus A3 gekoppelt.

**Zusätzliche Repo-Regressionsursache #809:** Der Live-Prüfer verlangte das
Wort `Environments` in `cloudflare/edge-schutz.md`, die Vorlage enthielt aber
keinen A4-Abschnitt. Selbst ein gesunder Worker wurde dadurch beanstandet,
während die Offline-Prüfung Grün zeigte. A4 ist jetzt ergänzt, und **dieselbe**
Funktion `vorlagen_fehler()` läuft offline und bei der Betriebsbewertung.
Der Regressionstest wertet einen gesunden Stand gegen das **echte Repository**
aus und sabotiert anschließend jede erforderliche Vorlagenkomponente.

**Rückfallschutz:**

```bash
npm run test:sicherheit
# einschließlich echter Workflow-Shellblöcke mit Bash -e und lokaler gh-Attrappe
python3 -m unittest scripts.tests.test_sicherheits_nachweis scripts.tests.test_worker_betrieb_wache
```

---

## Abschlussprüfung

```bash
npm run test:sicherheit                      # vier Wachen, Selbsttest + Quellprüfung
npm run header:check:live                    # Header der echten Seite (A1)
npm run betrieb:check:live                   # Worker-Betrieb (A2/A3/A4)
python3 scripts/n8n_schutz_wache.py          # Automatik-Kette (A5)
cd newsletter-worker && node --test          # 91 Tests
cd ../cloudflare/klick-zaehler && node --test test/worker.test.mjs   # 34 Tests
cd ../../cloudflare/ki-assistent && node --test                      # 17 Tests
```

Quellseitiges Grün belegt die Regressionstests, nicht die Dashboard-Einrichtung.
Erst vollständiges Live-Grün nach D1 belegt die gemessenen Schutzmaßnahmen;
verbleibende Dashboard-Prüfpunkte und Warnungen sind weiterhin abzuarbeiten.
Rot nennt den fehlenden Nachweis oder die belegte Abweichung — nicht beides
als denselben Sicherheitsbefund.


## Wartungsnachweis #782 · WF-E813 · 16.10.2026

**Belegt:** Lauf `38891475692`, Job `116941814761`, meldete
„F-01 WACHE-FEHLER: blog_header_gate.py lieferte Exit [leer]“.
Der Messschritt selbst war bereits fehlgeschlagen. GitHub führt `run` unter
Bash mit `-e` aus; `set -uo pipefail` deaktiviert dieses geerbte `errexit`
nicht. Ein fachlich erwarteter Exit 1 oder 2 brach deshalb den Schritt vor
`GITHUB_OUTPUT` ab. Die vorherigen Textprüfungen erkannten das nicht.

**Korrektur:** Der Messaufruf steht jetzt in einem expliziten `if/else`;
sein unveränderter Exit wird gespeichert, während echte Infrastrukturfehler
(z. B. nicht schreibbares `GITHUB_OUTPUT`) weiterhin den Schritt abbrechen.
BEFUND und STOERUNG bleiben rot, die Messung selbst bleibt neutral.
Die unabhängige Worker-Prüfung schreibt ihren Bericht nun auch bei Fehlern
in die Lauf-Zusammenfassung und erhält ihren ursprünglichen Exit-Code.
Ein fehlender Export-Schlüssel bleibt ausdrücklich **NICHT GEPRÜFT**.

**Rückfallschutz:** `python3 -m unittest scripts.tests.test_blog_header_gate`
führt die tatsächlichen YAML-Shellblöcke mit `bash -e -o pipefail` aus:
Exit 0/1/2/3/127, Auswertung, fehlender Bericht, Output-Schreibfehler sowie
Worker-Erfolg/Befund/Störung/Wachenfehler und fehlender Schlüssel. Diese Tests
laufen im Offline-Job; Änderungen an der Testdatei lösen den Workflow aus.

**Abgrenzung:** Der vollständige historische Job-Log war in der
Bearbeitungsumgebung nicht abrufbar; die Befunde oben stammen aus der
GitHub-Jobs-API und den Check-Annotations. Der Worker-Schritt war ebenfalls
rot, seine konkrete Live-Ursache ist damit noch nicht belegt. Keine Aussage,
dass Live-Header oder Worker jetzt gesund seien; nach Übernahme den Workflow
„Sicherheits-Wache“ auf `main` manuell starten und beide Zusammenfassungen
prüfen. Ein verbleibender fachlicher Befund ist nach A1/A3 zu beheben, nicht
durch Unterdrücken des Alarms.

---

## E. Abhängigkeiten — wenn GitHub Alarme zeigt und der Bestand sauber ist

**Stand 24.10.2026** · Grundlage `ABHAENGIGKEITS-SICHERHEIT-PREMIUM-2026-10-24.md`

GitHub meldete 58 offene Schwachstellen, während der ausgelieferte Bestand
nach vollständiger Prüfung gegen dieselbe Advisory-Datenbank 0 Fundstellen
hatte. Die Anzeige war älter als der Bestand. Dieser Abschnitt beschreibt,
wie der Zustand **gemessen** wird — und was ein Befund auslöst.

### E1 · Messen, nicht glauben

```bash
npm run deps:check     # offline: Pins, Quelle ↔ Hash-Lock, Locks, SHAs, Tags
npm run deps:audit     # online: jede ausgelieferte Version gegen die Advisory-DB
npm run test:deps      # Sabotage- und Gegenproben der Wache
```

Der Audit braucht `GITHUB_TOKEN` (in Actions vorhanden). Rund 310
Versionen, etwa 70 Sekunden, Exit 0 sauber · 1 Befund · 2 Störung.

### E2 · Befund heilen (Exit 1)

Der Treffer nennt Paket, Version, Schweregrad, GHSA und `first_patched_version`.

1. Version auf `first_patched_version` pinnen — in **allen** Stellen, die die
   Wache als Herkunft nennt (`quellen`).
2. Bei pip: `requirements-ci.in` **und** `requirements-ci.txt` gemeinsam
   ändern; der Hash-Lock wird mit neuen Hashes erzeugt, die Quelle trägt
   denselben Pin (Regel A2 prüft die Gleichheit).
3. `npm run deps:check && npm run deps:audit` — erst danach ist der Befund
   geschlossen.
4. Kein `first_patched_version` veröffentlicht? Dann bleibt der Befund offen
   und wird als bewusster Eintrag im PR genannt. Er verschwindet nicht durch
   Dismiss.

### E3 · Störung (Exit 2) ist kein Freibrief

Netzfehler, Rate-Limit oder fehlendes Token bedeuten **ungeprüft**. Der Lauf
ist rot, nicht grün. Wiederholen (`workflow_dispatch`), nicht wegsehen.
Ungeprüft ist nicht sauber — dieselbe Regel wie bei der Live-Header-Messung
(Vertrag C34).

### E4 · GitHub-Alarme, die die Wache nicht bestätigt

Reihenfolge, die eine Behauptung von einem Nachweis trennt:

1. `npm run deps:audit` laufen lassen. Exit 0 = der Bestand ist sauber.
2. Prüfen, ob der Alarm eine Version nennt, die im Bestand **nicht mehr**
   vorkommt (die Wache listet alle ausgelieferten Versionen; `--json`).
3. Erst dann in der Security-Tab schließen — mit der Messung als Begründung
   („Version nicht mehr im Bestand, Nachweis: Audit vom <Datum>, 0 Treffer“).
4. Kommt der Alarm wieder, war die Ursache nicht die Version, sondern die
   Auflösung: dann steht ein Range in einer Requirements-Datei (A1) oder ein
   Manifest ohne Lockfile (A3).

### E5 · Was die Wache bewusst nicht tut

- Sie ersetzt Dependabot nicht: Dependabot öffnet die Update-PRs, die Wache
  prüft den ausgelieferten Stand.
- Sie prüft **keine** Container-Inhalte (nur bewegliche Tags).
- Sie prüft nur, was im Repo liegt — nicht, was ein Dienst zur Laufzeit lädt.

---

## F. Signale, die nicht lügen (WF-E813/#815, 27.10.2026)

**Grundlage:** `WARTUNG-BETRIEBSPFLEGE-WF-E813-815-HIGHEND-2026-10-27.md`
**Wozu:** Die Kette aus A1, D1 und D2 funktioniert nur, wenn ein rotes Kreuz
etwas bedeutet und ein grünes nichts verdeckt. Zwei Betriebsfehler dieser Art
sind am 27.10.2026 gemessen und dauerhaft geheilt worden.

### F1 · Ein Befund ist ein Kommando, kein Text

Jede Zeile, die mit `::` beginnt, liest der GitHub-Runner als **Befehl** –
`::error file=…,line=…,title=…::Text` wird daraus eine Annotation. Wer Datei-
oder Textinhalte unmaskiert einsetzt, kann Befehle **erzeugen**: Ein
Zeilenumbruch beginnt ein zweites Kommando, ein `,` bricht aus der
Eigenschaftsliste aus. Genau das war passiert: Die Vertragstests der
Abhängigkeits-Wache riefen `main()` auf einem vergifteten Testbaum auf, und
der **grüne** Job trug danach drei rote Annotationen über eine
`requirements-x.txt`, die es im Repository nicht gibt.

Deshalb gibt es **einen** Meldeweg: `scripts/github_kommando.py`.

```bash
npm run kommando:probe     # sendet dieser Prozess Annotationen? (zeigt ein kodiertes Beispiel)
npm run test:kommando      # 22 Vertragstests: Fluchtschutz, Teststille, Notausgang
```

Regeln für jeden neuen Melder:

1. **Nicht selbst `print("::…")`.** `annotation(ebene, text, datei=…, zeile=…,
   titel=…)` benutzen; die Kodierung (`%`, CR, LF; `:`/`,` in Eigenschaften)
   ist dort an einer Stelle festgelegt.
2. **Ein Befund ist eine Zeile.** Ein Umbruch im Text ist immer ein Fehler in
   der Meldung, nie ein zweiter Befund.
3. **Testläufe färben nichts.** Unter `unittest`/`pytest` sendet der Melder
   nichts, auch mitten in Actions – ein Test prüft Verhalten, er gestaltet
   nicht den Lauf, in dem er läuft.
4. **Notausgang:** `GITHUB_KOMMANDOS=an` erzwingt das Senden (Gegenprobe),
   `GITHUB_KOMMANDOS=aus` erzwingt die Stille. Beides schlägt die Automatik.

### F2 · Was ein Lauf prüft, muss ihn auch auslösen

Ein Gate springt nur an, wenn der `paths`-Filter seines Workflows die
geänderte Datei nennt. Diese Liste wird von Hand gepflegt – zweimal (für
`push` und `pull_request`). Am 27.10.2026 fand die neue Trigger-Wache dort
**36 Befunde in neun Workflows**, darunter `manifest_guard.py` (in fünf Gates
benutzt, in vier Filtern nicht genannt), die Lesehilfen-Liste (17
Abweichungen zwischen push und pull_request) und die Backup-Frischwache, die
ihre eigenen Prüfer nicht auslöste.

```bash
npm run trigger:check      # Exit 0 sauber · 1 Befund · 2 Form nicht lesbar
npm run test:trigger       # Selbsttest (Sabotage) + Vertragstests inkl. PyYAML-Gegenprobe
```

| Regel | Bedeutung | Was du tust |
|---|---|---|
| **W1 Referenz** | Ein Workflow ruft ein Skript auf, das sein `paths`-Filter nicht nennt. | Pfad ergänzen (beide Listen). |
| **W2 Waise** | Ein Filtereintrag zeigt auf eine Datei, die es nicht mehr gibt. | Eintrag entfernen oder Datei wiederherstellen. |
| **W3 Symmetrie** | `push` und `pull_request` tragen unterschiedliche Listen. | Dieselbe Liste in beide Blöcke; im Zweifel die weitere Fassung. |

Der Test `test_dauervertrag_bestand_ohne_befund` hält den Bestand sauber: Wer
einen Prüfer aufruft, ohne ihn zu nennen, macht ihn rot – nicht erst ein Gate,
das nicht anspringt.

**Der Kanal selbst ist überwacht.** Der Lauf „Skript-Syntax (liegender Stand)“
steht seit dem 27.10.2026 auf der Wacht-Liste des zentralen Fehler-Alertings
(Vorgang `WF-CA1D`, Bereich Betriebspflege) und hat eine eigene Triage-Klasse
`skript-syntax`. Eine Regression in genau dieser Wache bleibt damit nicht
still: Sie erzeugt eine Meldung mit Reparaturweg statt eines Funklochs.

**Ehrliche Grenze:** Beide Prüfungen sagen nichts über die *Richtigkeit* eines
Gates, nur über seine Erreichbarkeit. Ob ein Rat zutrifft, entscheidet weiter
die Klassifikation der Wache selbst (Abschnitte A1, D1, D2).

### F3 · Auch das Skript IM Workflow muss kompilieren (29.10.2026)

Der Block unter `uses: actions/github-script@…` ist **JavaScript in YAML**. Die
Python-Wachen sehen ihn nicht. Am 29.10.2026 traf der Squash-Merge von PR #943
eine zwischenzeitlich gewanderte `main` (Environment-Gate #935); in
`alert-on-failure.yml` standen danach zwei Zeichenketten ohne Komma –
`SyntaxError: Unexpected string`, dazu eine verwaiste `failedStepNames.some(…)`-Zeile.
Der Runner führt den Block als Funktion aus: **jeder** Lauf des Fehler-Alertings
starb, also genau der Kanal, der solche Ausfälle meldet.

```bash
python3 scripts/workflow_js_wache.py --check     # Exit 0 sauber · 1 Befund · 2 nicht prüfbar (node fehlt)
python3 scripts/workflow_js_wache.py --selftest  # Extraktion, J1/J2/J3, fail-closed ohne node
npm run workflow:js                              # dasselbe als npm-Skript
```

| Befund | Bedeutung | Was du tust |
|---|---|---|
| **J1** | Ein `github-script`-Block kompiliert nicht; die Meldung nennt die Workflow-Zeile. | Meist ein Zusammenschnitt beim Zusammenführen: fehlendes Komma, verwaiste Zeile, doppelte Rat-Liste. Beide Fassungen vergleichen (`git log -p -- <datei>`), nicht raten. |
| **J2** | `github-script` ohne `script:`-Block. | Der Schritt hätte nichts auszuführen und meldete trotzdem grün – Block ergänzen oder Schritt entfernen. |
| **J3** | Leerer `script:`-Block. | Dasselbe: ergänzen oder entfernen. |

Der Lauf „Skript-Syntax (liegender Stand)“ fährt diese Prüfung mit (Selbsttest
zuerst). Ein fehlendes `node` ergibt **Exit 2** und damit einen roten Lauf –
eine ausgefallene Messung ist kein Grün (C33).

### F4 · Wer meldet den Ausfall des Melders? (WF-829B / #922, 30.10.2026)

F3 hat die Erkennung gebaut – und sie hat funktioniert: Am 30.10.2026 stand
in `alert-on-failure.yml` eine **doppelte `const workerZugangFailed`** im
`github-script`-Block (beim Zusammenführen zweier Fassungen entstanden).
`workflow_js_wache.py` meldete sie (`J1 … block.js:236`), der Lauf
„Skript-Syntax (liegender Stand)“ wurde rot. **Gemeldet hat es niemand**: Der
einzige Kanal, der einen roten Lauf in ein Issue verwandelt, war genau dieses
tote `alert-on-failure.yml`. Belegt im Run-Log:

```text
Unhandled error: SyntaxError: Identifier 'workerZugangFailed' has already been declared
```

Die Lehre ist älter als der Fall (Kopf von `alerting-heartbeat.yml`): *Ein
Wächter, der über die gestörte Leitung alarmiert werden will, schweigt genau
dann, wenn er gebraucht wird.* Die Zustellung zu zählen reicht deshalb nicht –
der Kanal muss auf seine **Lauffähigkeit** geprüft werden, und zwar von einem
Weg, der ihn nicht benutzt.

Seit dem 30.10.2026 tut das der Herzschlag, per `cron`, vor jeder Zählung:

```bash
python3 scripts/alerting_heartbeat.py --kanal          # Exit 0 lauffähig · 1 Befund · 2 nicht prüfbar
python3 scripts/alerting_heartbeat.py --selftest       # u. a. sechs Sabotagefälle K1–K6
```

| Lage | Wirkung |
|---|---|
| Block kompiliert nicht | eigenes Issue **„🫀 Alerting-Kanal: das Fehler-Alerting selbst ist nicht lauffähig“**, die Zählung bleibt aus (eine Zustellquote für einen toten Kanal wäre eine Zahl ohne Bedeutung) |
| `node` fehlt (Exit 2) | ebenfalls rot: keine Messung ist kein Grün (C33) |
| grün | offene Kanal-Meldung wird geschlossen, danach läuft die Zählung wie bisher |

Warum ein **eigener** Issue-Titel: Die Meldung „Zustellung verliert Ereignisse“
würde auf API-Schlüssel und Netz raten, während die Ursache ein Syntaxfehler im
Melder selbst ist. Zwei Titel, zwei Räte, ein Werkzeug.

**Die Reihenfolge der Reparatur, wenn beides rot ist:** erst den Kanal heilen
(F3: eine Fassung, `node --check`), dann den Deploy-Zugang (A4/D2). Solange der
Melder tot ist, ist jede andere Meldung nur zufällig zu sehen – auch diese.

---

## G. Das Siegel über dem Regelkern der Skills (01.11.2026)

Seit dem Skill-Umbau meldet `scripts/skills_vertrag.py` in K8 den Siegelstand –
als **Warnung mit Schlusszeile, nie als Befund**. Diese Seite hier ist der
Auftrag, den die Warnung ankündigt. Der Grund für die Zurückhaltung derselbe wie
bei Issue #316: Ein HARD STOP auf eine ungezeichnete Datei bestraft die
Produktion, nicht den Austausch. Zeichnen bleibt ein Menschenakt.

### G1 · Zwei Dateien gehören ins Siegel – in dieser Reihenfolge

Der Stand des Berichts (nachzulesen mit `python3 scripts/skills_vertrag.py`):

```text
[K8] scripts/skills_vertrag.py   – steht weder in KRITISCH/FEST noch im Siegel
[K8] data/skill_lizenzen.json    – steht weder in KRITISCH/FEST noch im Siegel
```

Beide Dateien *entscheiden*: die Wache hält Kernbudget, Router, Befehle und
Lizenzdeckungen zusammen, das Register sagt, welcher Fremdcode überhaupt im Repo
stehen darf. Wer sie austauscht, schreibt die Regeln um, ohne dass ein Gate
aufsteht – und genau das ist die Klasse, die `integrity_guard.py` seit dem
12.08. schließt.

**Schritt 0 · Vorbedingung, nicht überspringbar.** `npm run test:redaktion` ist
rot (Fall „Vertrag-gute-aenderung-still“, Exit 2) – vor dem Umbau so gewesen und
auf einem frischen Auschecken von `51e0270` nachgeprüft, also nicht vom Skill-
Umbau gemacht. `scripts/redaktions_standard.py` steht in FEST und ist
versiegelt. Wer **jetzt** signiert, wäscht den defekten Stand: Das Siegel würde
erklären, ein Zustand sei gut, dessen eigener Selbsttest Nein sagt. Erst der
Inhaber heilt die Wache, dann wird gezeichnet. Dass kein Agent diesen Schritt
erledigt, ist kein Zögern, sondern der Unterschied zwischen Schutz und
Selbstbestätigung.

**Schritt 1 · Klasse.** In `scripts/integrity_guard.py` den Block `FEST` um die
beiden Pfade erweitern – mit dem üblichen Kommentarblock, warum FEST und nicht
KRITISCH: kein Render-Hook, keine Affiliate-Kohärenz, aber regsetzend. Die Klasse
ist die Anmeldung zum Schloss; `--add` lehnt Pfade außerhalb von KRITISCH/FEST
ab, es gibt keinen Weg direkt ins Lot.

**Schritt 2 · Zeichnen, im selben Zug wie die Klassenänderung.**

```bash
python3 scripts/integrity_guard.py --add=scripts/skills_vertrag.py
python3 scripts/integrity_guard.py --add=data/skill_lizenzen.json
python3 scripts/integrity_guard.py --set-current
```

Ein Commit davor oder danach ist kein Versehen, sondern ein rotes PR-Gate: eine
Datei in FEST ohne Zeichnung wirft `.github/workflows/integrity-lock.yml` bei
jedem Pull Request (#316-Muster – der Alarm galt der Produktion).

**Schritt 3 · Nachweis, nicht Gefühl.**

```bash
python3 scripts/integrity_guard.py --drift-audit   # die beiden Pfade tauchen nicht mehr auf
python3 scripts/skills_vertrag.py                   # 0 Befunde, 0 Warnungen – K8 verstummt
npm run test:skills                                 # 17 Selbsttest-Fälle, 33 Unit-Tests
git diff data/integrity_lock.json                   # Akte mit `art` und Datum je Signatur
```

Eine Signatur ohne Akteneintrag ist keine – das Protokoll schreibt die Herkunft
mit (`audit` im Lock), und nur daran lässt sich #346 von einer bewussten Zeichnung
unterscheiden.

### G2 · Was der Audit sonst noch meldet

`--drift-audit` nennt aktuell `scripts/redaktions_standard.py` als FEST-Drift mit
Urteil „VERSIEGELBAR“ (Arbeitsbaum = HEAD, zuletzt `51e0270`). Die Tabelle gilt
für jeden künftigen Fund:

| Was der Audit sagt | Was folgt | Was nicht folgt |
|---|---|---|
| FEST-Drift, Selbsttests grün | `--heal` (belegt: committet, bytegleich, nicht KRITISCH) | `--set-current` auf Vorrat |
| FEST-Drift, Selbsttest rot | erst heilen (Schritt 0), dann zeichnen | Signatur unter dem defekten Stand |
| KRITISCH-Abweichung | Ursache über `--drift-audit` klären, dann Mensch entscheidet | `--heal` (hebt für KRITISCH nie die Sperre auf) |
| Lock unlesbar oder zusammengeschnitten | `--repair-lock --dry-run` lesen, dann reparieren | neuen Lock von Hand tippen |

### G3 · Was schon geregelt ist (kein Auftrag)

Das Siegel selbst ist seit #346 durch `merge=binary` geschützt. Seit dem
01.11.2026 gilt dasselbe für `data/skill_lizenzen.json` und `skills-lock.json`
(`.gitattributes`): Beide sind Register, die ein Werkzeug schreibt – ein
Text-Merge zweier Fassungen hätte dort einen Hash auf einer Datei, die so nicht
existiert, und einen Lizenz-Eintrag, den niemand geprüft hat. `merge=union` wäre
eine Erfindung, weil eine Vereinigung von Herkunftsangaben keine zweite Messung
ist, sondern ein drittes Gerücht.

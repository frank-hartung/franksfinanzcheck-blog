# Sicherheits- und Lücken-Audit — FranksFinanzcheck

**Datum:** 14. Oktober 2026 · **Umfang:** Repository `frank-hartung/franksfinanzcheck-blog` (öffentlich), Hugo-Site, Cloudflare-Worker (Newsletter, Klick-Zähler, KI-Assistent), 87 GitHub-Workflows, lokale Automatik (`tools/n8n`, `scripts/`)
**Methodik:** Vollständige Quelltextanalyse aller produktiven Komponenten, Ausführung der repo-eigenen Wachen und Testsuiten, Secret-/PII-Scan über den Arbeitsbaum, Analyse der Live-Konfiguration über die GitHub-API.
**Auftrag:** *„Finde sämtliche Fehler, Lücken und Sicherheitslücken, bevor sie ein Hacker finden kann – auf Highend-Niveau einer Profi-Agentur."*

---

## 1. Ergebnis auf einen Blick

Der Blog ist **überdurchschnittlich gut gehärtet** – deutlich über dem Niveau typischer WordPress-/Hugo-Blogs. Es existiert eine eigene Sicherheitskultur mit Selbsttests, Verträgen und Wachen. Genau deshalb sind die verbleibenden Lücken **nicht die klassischen** (kein `shell=True`, keine SQL-Injection, keine Klartext-Secrets, keine XSS-Lücken im eigenen JS): Es sind **Kontingent-, Bot- und Expositions-Lücken** sowie ein **fehlender HTTP-Header-/CSP-Rahmen** der Hauptseite.

| ID | Schwere | Befund | Kernbeleg |
|----|---------|--------|-----------|
| **F-01** | 🔴 **Hoch** | Produktionsseite liefert **keine HTTP-Sicherheitsheader** (HSTS, X-Frame-Options/frame-ancestors, nosniff): `static/_headers` ist auf GitHub Pages wirkungslos | `static/_headers:1-3`, `layouts/_partials/head.html:16` |
| **F-02** | 🔴 **Hoch** | Newsletter-Anmeldung **ohne Bot-Schutz** (fail-open), versendet Bestätigungsmails an **frei wählbare Adressen** | `layouts/shortcodes/newsletter_form.html`, `wrangler.toml`, `src/index.js:273` |
| **F-03** | 🔴 **Hoch** | **Kontingent-Erschöpfung als Denial of Service**: unauthentifiziert ~300 Anmeldungen bzw. ~50.000 GET-Requests legen alle Newsletter-Funktionen lahm | `src/index.js:336,350,613,678,983,1030`; eigenes H-03-Konzept |
| **F-04** | 🟠 **Mittel-Hoch** | Lokale Dienste **ohne Zwang zur Authentifizierung** (Whisper-Token fail-open, n8n-Webhooks ohne Auth, Bridge-Server ohne Prüfung) | `docker-compose.yml:81`, `whisper_server.py:71-76`, `n8n/workflows/*.json`, `n8n_bridge.py:313` |
| **F-05** | 🟠 **Mittel** | **E-Mail-Adresse im Cloudflare-Log** – Widerspruch zur dokumentierten Zusage | `src/index.js:784` vs. `wrangler.toml` Observability |
| **F-06** | 🟠 **Mittel** | `unsafe = true` (rohes HTML aus Markdown) **ohne `script-src`-CSP** → persistente XSS über den Content-Weg möglich | `hugo.toml:82`, `head.html:16` |
| **F-07** | 🟠 **Mittel** | **Freigabe-Stufen fehlen**: Environments `cloudflare-produktion`, `brand-admin`, `backup` existieren nicht → dokumentierte 4-Augen-Freigaben greifen nicht | GitHub-API `environments` (nur `github-pages`, `GITHUB_WORKFLOW_TOKEN`) |
| **F-08** | 🟠 **Mittel** | **Export-Schlüssel = Generalschlüssel**: liefert E-Mail **und** Token **aller** Abonnenten, ohne Rate-Limit, Protokoll oder Rotation | `src/index.js:1064-1100` |
| **F-09** | 🟡 **Niedrig** | Fremdinhalte in öffentlichen Issue-Flächen über Workflow-Namen/Branch-Namen (Markdown-Injection) | `alert-on-failure.yml:158,508-511,545-547` |
| **F-10** | 🟡 **Niedrig** | Klickzähler per `curl` mit gefälschtem `Origin` manipulierbar (bekannt, aber mit Nebenwirkung aufs D1-Kontingent) | `klick-zaehler/worker.js` |

**Was ein Angreifer mit diesen Lücken erreichen kann (realistisch):**
1. Die Newsletter-Anmeldung des Blogs als **Mail-Verstärker** missbrauchen (Bestätigungsmails an Dritte) und dabei die **Tagesabrechnung des KV-Kontos leeren** → Anmeldung, Nachweise und Datenschutz-Pflege fallen bis Mitternacht UTC aus (F-02 + F-03).
2. Die **Hauptseite in fremde Frames einbetten** (Clickjacking auf Finanz-Buttons) und beim ersten Aufruf **TLS-Downgrade** versuchen (F-01).
3. Mit jedem **Rechner im Heimnetz des Betreibers** (Whisper :8765, Bridge :5680) über eine beliebige besuchte Webseite interagieren, solange kein Token gesetzt ist (F-04).
4. Bei einem **einzigen Leck des Export-Schlüssels** alle Abonnenten abmelden oder deren Themen ändern (F-08).

**Was ein Angreifer nach diesem Audit *weiterhin* nicht kann:** Tokens erraten (192 Bit), SQL einschleusen (Prepared Statements), Logs mit Klartext-Secrets lesen (keine im Baum), den Build vergiften (Hugo-Download SHA-256-geprüft, alle Actions SHA-gepinnt), über Webhook-Pfade beliebige Dateien schreiben (Pfadgefängnis in `n8n_bridge.py:255-268`), Header-Injection in Mails (§-Zeichen/Newlines durch `EMAIL_RE` gesperrt).

---

## 2. Was verifiziert gehalten hat (Belastbarkeit der bestehenden Härtung)

Diese Punkte habe ich **aktiv nachgemessen**, nicht nur gelesen:

| Prüfung | Ergebnis |
|---|---|
| Worker-Testsuiten (nativ, ohne Cloudflare) | Newsletter **76/76**, KI-Assistent **17/17**, Klickzähler **30/30** grün |
| URL-Wache (`scripts/url_substring_guard.py`) | 744 Dateien (Python, JS/TS, HTML) sauber – keine Zeichenketten-Host-Prüfung |
| Klartext-Wache (`scripts/clear_text_logging_guard.py`) | 477 Python-Dateien ohne Klartext-Fund |
| KI-Assistenten-Gate | 9 bereit, 1 Warnung (KA1: Endpoint nur per Shortcode-Attribut – bewusster aus-Zustand) |
| Actions-Pinning | **Alle** `uses:` auf 40-Hex-SHA gepinnt; der einzig verbliebene Tag-Verweis steht nur noch als Kommentar (`peaceiris/actions-hugo@v3`) |
| Versions-Drift-Wache | keine Drift |
| Secret-Scan (ghp_, github_pat_, sk-, AIza, AKIA, xox, PRIVATE KEY, Bearer) | **kein echtes Secret** im Arbeitsbaum – nur Test-Fixtures mit Fantasiewerten |
| PII-Scan (E-Mails, IPs, Abo-Listener) | keine Abonnenten-Adressen, keine Klartext-IPs, keine Kundendaten in `data/` (Abos entstehen erst zur Laufzeit im KV) |
| Suppply-Chain Hugo | Download mit **fest hinterlegter SHA-256-Prüfsumme**, PyPI-Fallback hash-gepinnt, fail-closed |
| XSS im eigenen Frontend-JS | `textContent`/`createTextNode` statt `innerHTML` mit Nutzereingaben (KI-Assistent, Suche, Rechner, Werkzeuge) |
| CSRF-Schutz der Worker | Origin **und** Sec-Fetch-Site, `Origin: null` nur bei same-origin, fremde Herkünfte → 403 |
| Konstantzeit-Vergleich Export-Key | vorhanden (`schluessel_pruefen`, SHA-256-basiert) |
| DSGVO-Mechanik Newsletter | Double-Opt-In 14 Tage, Nachweis 3 Jahre getrennt vom Abo-Datensatz, IP/UA nur im Nachweis, Altbestand-Bereinigung, Löschlauf per Cron |
| Pfad-Gefängnis Webhook→Draft | Slug nur `[A-Za-z0-9_-]{1,80}`, `realpath`-Prüfung gegen `content/drafts` |
| Endpoint-Hygiene Worker | kein `*.workers.dev`, keine Preview-URLs, WAF/Zone greift, Cookie-/Telemetriefreiheit eingehalten |

---

## 3. Findings im Detail

### F-01 🔴 Keine HTTP-Sicherheitsheader auf der Produktionsseite

**Befund.** Die Seite liegt auf GitHub Pages. GitHub Pages ignoriert `_headers` (die Datei sagt das selbst: `static/_headers:1-3` „GitHub Pages ignoriert diese Datei"). Deshalb fehlen im Live-Betrieb:

* `Strict-Transport-Security` → **kein HSTS**: Der erste Aufruf kann per `http://` angreifbar sein (SSL-Strip/Downgrade, Session-Cookie-Klau-Nachbau, Phishing-Zwischenseite).
* `X-Frame-Options` / `frame-ancestors` → **Clickjacking** der Finanz-/Affiliate-Buttons.
* `X-Content-Type-Options: nosniff`, `Permissions-Policy`, `Cross-Origin-Opener-/Resource-Policy`.

Die im Layout gesetzte Meta-CSP (`head.html:16`) deckt bewusst nur `base-uri`, `object-src`, `form-action` ab – `frame-ancestors` und HSTS **können per `<meta>` nicht wirken**. Das Repo kennt die Lücke („…Bis die Header über Cloudflare kommen (B.5)…") – sie ist aber **noch offen** und damit der größte Einzelbefund.

**Wirkung.** Eine YMYL-Finanzseite ohne Clickjacking- und HSTS-Schutz ist ein bevorzugtes Ziel für Klick-Hijacking und Phishing-Frames. Reputationsschaden trifft direkt die Affiliate-Umsätze.

**Fix (30 Minuten, ohne Code-Deploy).** Cloudflare-Zone `franksfinanzcheck.de` → Rules → **Transform Rule → Modify Response Header** für `http.host eq "franksfinanzcheck.de"` bzw. HTML-Pfade:

```
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
X-Frame-Options: DENY
Content-Security-Policy: frame-ancestors 'none'; base-uri 'self'; object-src 'none'; form-action 'self' https://abos.franksfinanzcheck.de
X-Content-Type-Options: nosniff
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: camera=(), microphone=(), geolocation=(), payment=()
```

Anschließend in die Deploy-Nachprüfung aufnehmen (`curl -sI https://franksfinanzcheck.de/ | grep -Ei 'strict-transport|x-frame|nosniff'`), sonst fällt der Schutz beim nächsten Providerwechsel still weg.

---

### F-02 🔴 Newsletter-Anmeldung ohne Bot-Schutz, Bestätigungsmails an beliebige Adressen

**Befund.** Drei belegte Bausteine greifen ineinander:

1. Das Anmeldeformular enthält **kein Turnstile-Widget** (`layouts/shortcodes/newsletter_form.html`: nur Honeypot `website`, Zeitfalle `_zeit`, Consent, Themen).
2. Der Worker prüft Turnstile **fail-open**: `turnstile_ok()` gibt `true` zurück, solange `TURNSTILE_SECRET` nicht gesetzt ist (`src/index.js:273-276`), und die Konfiguration sagt ausdrücklich, das Secret erst zu setzen, wenn das Widget ausgeliefert wird (`wrangler.toml`, Block „Secrets").
3. Damit bleibt als einziges Netz das Rate-Limit **5 Anmeldungen/15 min/IP** plus Honeypot/Zeitfalle (beides von einem Skript trivial umgehbar: `website` leer, `_zeit` = jetzt minus 2 s).

**Wirkung.** Ein Angreifer kann **fremde Adressen anmelden** – jede bekommt eine echte Bestätigungsmail von `franksfinanzcheck.de`. Das ist (a) Belästigung Dritter in Ihrem Namen, (b) ein **Reputations- und Zustellbarkeitsrisiko** (Complaint-Rate, Blacklisting), (c) ein Vektor, Ihr Postfach-/SMTP-Kontingent zu verbrennen. Zusätzlich löst **jede** Anmeldung einen GitHub-`workflow_dispatch` aus (`src/index.js:796-800`) → Verbrauch der PAT-Rate-Limits (5.000/h).

**Fix (in dieser Reihenfolge!).**
1. Turnstile-Widget (Site-Key) in `newsletter_form.html` + `newsletter_form.js` einbinden und **Datenschutzerklärung** ergänzen.
2. Erst danach `npx wrangler secret put TURNSTILE_SECRET` → fail-closed greift automatisch.
3. Unabhängig davon ein **Adress-Budget**: gleiche Adresse höchstens 1×/24 h bestätigen lassen (KV-Schlüssel `sent:<hash>`), plus globale Obergrenze „Neuanmeldungen/Tag" (siehe F-03).

---

### F-03 🔴 Kontingent-Erschöpfung als Denial of Service (Cloudflare-Free-Grenzen)

**Befund.** Der Worker rechnet selbst mit **1.000 KV-Schreibzugriffen pro Tag für das gesamte Konto** (`src/index.js:64-67`, Audit H-03). Der Kommentar dort formuliert die Absicht so:

> „Feedback darf davon hoechstens FEEDBACK_MAX_PRO_TAG verbrauchen – **Anmeldung und Abmeldung behalten immer den Rest**."

Diese Absicht hält der Code **nicht ein**: Gedeckelt ist nur Feedback (`FEEDBACK_MAX_PRO_TAG_DEFAULT = 200`, `src/index.js:68,609`) – die **Anmeldung selbst hat keine Obergrenze**, verbraucht also genau den „Rest", der für sie reserviert werden sollte. Kosten pro Anmeldung:

* `abo_schreiben()` → 2 Writes (`abo:…`, `token:…`), `src/index.js:336-348`
* `nachweis_schreiben()` → 1 Write (`nachweis:…`), `src/index.js:350-360`
* ⇒ **~3 Writes pro Anmeldung** ⇒ **~270 Anmeldungen/Tag + 200 Feedback-Stimmen = Kontingent leer.**

Die Leseseite ist ebenso ungeschützt: **`rate_erlaubt()` wird ausschließlich in `/anmeldung` (Z. 751) und im `/abmeldung`-Formularpfad (Z. 947) aufgerufen.** Alle GET-Routen laufen frei: `/bestaetigung?token=`, `/praeferenzen?token=`, `/status?token=`, `/feedback?slug=` – je **2 KV-Reads**. Das Free-Kontingent liegt bei 100.000 Reads/Tag ⇒ **~50.000 Requests** genügen, um alle Token-Seiten, Anmeldungen und die Nachweise lahmzulegen (danach quittiert der Catch-All mit `500`).

**Wirkung.** Ohne Konto, ohne Botnetz, mit wenigen hundert Requests pro Tag: Newsletter-Anmeldung, Double-Opt-In-Bestätigung, Präferenzänderung, Abmeldung (!), Zähler-Pflege und Datenschutz-Löschlauf fallen aus. Eine **Abmeldung, die nicht funktioniert, ist zusätzlich ein DSGVO-Problem** (Art. 7 Abs. 3: Widerruf muss jederzeit möglich sein).

**Fix.**
1. **Rate-Limit auf alle Routen legen** – dasselbe Binding-Muster wie `RATE_LIMITER` (Free-Plan-tauglich, kostet keine KV-Writes): z. B. 60/min/IP auf GET-Routen, 10/min/IP auf POST.
2. **Tagesbudget-Schlüssel für Anmeldungen** (Muster existiert bereits für Feedback): ein Schreibzugriff pro Tag für den Zählerstand, danach „Annahme ohne Schreiben" und eine **laut protokollierte Warnung** (Issue/Alarm), wenn das Budget zur Neige geht.
3. Alternativ/dauerhaft: Anmeldungen in **D1** oder **Queues** statt KV (D1 hat eigene, höhere Limits) – dann trifft der Angriff nicht mehr die Nachweis- und Token-Ablage.
4. Fehlende Schreib-/Lesekapazität **sichtbar** machen: 503 mit `Retry-After` statt generischem 500, plus Zähler in `/healthz` für `X-FF-Key`.

---

### F-04 🟠 Lokale Dienste ohne Zwang zur Authentifizierung

**Befund (drei Teile, alle belegt):**

1. **Whisper:** `zugang_pruefen()` kehrt sofort zurück, wenn `WHISPER_TOKEN` leer ist – der Dienst ist dann **offen** (`tools/n8n/whisper_server.py:71-76`). Die Compose-Datei setzt `WHISPER_TOKEN=${WHISPER_TOKEN:-}` (`tools/n8n/docker-compose.yml:81`) und `.env.example:22` lässt den Wert leer ⇒ **Standardzustand = keine Authentifizierung**. Der Port ist auf `127.0.0.1:8765` veröffentlicht – für jede **Webseite, die der Betreiber besucht**, ist das erreichbar: Ein `POST` mit `FormData` ist ein „simple request" (kein Preflight), die Antwort ist für den Angreifer nicht lesbar, **die Transkription läuft aber trotzdem** (CPU-DoS, Volllaufen des Inbox-Volumes bis 50 MB/Datei).
2. **n8n-Webhooks ohne Auth:** Alle drei Webhook-Knoten (`voice-memo`, `blog-publish`, `audio-qa`) haben **keine** Authentifizierung (`authentication: none`, keine `credentials` in den Workflow-JSONs). Da das Repository **öffentlich** ist, sind die Pfade bekannt. Wer den Tunnel erreicht (oder lokal senden darf), kann **Content-Inputs und Publish-Läufe einspeisen**. Der Python-Bridge-Server (`scripts/n8n_bridge.py:313`) nimmt POSTs ebenfalls **ohne jede Prüfung** entgegen (kein Token, keine Origin-Prüfung, kein Content-Type-Zwang).
3. **Gegenbeispiel (lobenswert):** Der ausgehende Webhook-Aufruf sendet `Authorization: Bearer …` **und** `X-Webhook-Secret` (`n8n_bridge.py:150-153`) – die Lücke ist also nur die Empfangsseite.

**Wirkung.** Heimnetz-übergreifender Missbrauch durch eine beliebige besuchte Webseite (lokaler CSRF) sowie Content-Einspeisung in die Publishing-Kette, falls der Tunnel fällt. Ergebnis: fremde Texte in Entwürfen, CPU-Kosten, im schlimmsten Fall veröffentlichte Inhalte.

**Fix.**
* `whisper_server.py`: **fail-closed** – Dienst startet nicht (bzw. antwortet 503), wenn `WHISPER_TOKEN` fehlt; Compose-Pflichtvariable `${WHISPER_TOKEN:?WHISPER_TOKEN muss gesetzt sein}`.
* Bridge-Server: Tokenprüfung **und** `Origin`-Ablehnung für Browser-Anfragen **und** `Content-Type: application/json` erzwingen (letzteres erzwingt einen Preflight und blockiert simple Cross-Site-POSTs).
* n8n: Webhook-Knoten auf **Header-Auth** umstellen (gemeinsames Secret, in `.env` erzeugt: `openssl rand -hex 32`) und in den Workflow **vor** dem ersten Verarbeitungsknoten prüfen. Zusätzlich `N8N_PUBLIC_API_DISABLED`, die bereits gesetzten `NODES_EXCLUDE` und die 127.0.0.1-Bindung beibehalten.

---

### F-05 🟠 E-Mail-Adresse im Cloudflare-Log

**Befund.** `newsletter-worker/src/index.js:784`:

```js
console.warn(`ff-newsletter: unbekannter Abo-Status "${bestehend.status}" für ${email}`);
```

Die Adresse landet im Klartext in den Workers Logs. Der Konfigurationskopf sagt dagegen ausdrücklich: „Der Worker loggt keine Adressen, keine Tokens, keine IPs." (`newsletter-worker/wrangler.toml`, Observability). Damit ist eine **Zusage der Datenminimierung im Code verletzt** – DSGVO Art. 5 Abs. 1 lit. c/f, Art. 32, und ein Widerspruch, den eine Aufsicht oder ein Datenschutzbeauftragter als Erstes findet.

**Fix.** Meldung ohne personenbezogenen Anteil (`… für ${await sha256_kurz(email)}`) und die Klartext-Wache (`scripts/clear_text_logging_guard.py`) um **JavaScript/Worker-Quellen** erweitern – sie prüft heute nur Python. Anschließend per Positiv-/Gegenprobe absichern (Repo-Standard).

---

### F-06 🟠 `unsafe = true` ohne `script-src`-CSP (persistente XSS über den Content-Weg)

**Befund.** `hugo.toml:82` setzt `unsafe = true` – rohes HTML in Markdown wird **unverändert** ausgeliefert (nötig für die `<div>`-Blöcke, die im Bestand vorkommen). Die Meta-CSP (`head.html:16`) definiert **kein** `script-src` und **kein** `default-src` ⇒ Inline-Skripte sind erlaubt, `javascript:`-URLs ebenfalls. Gleichzeitig wird Content **automatisiert erzeugt und committet**: Voice-Memo → n8n → Draft (`n8n/workflows/1_voice_memo_to_blog_draft.json`), KI-Redaktion, Bots, die direkt auf `main` schreiben.

**Wirkung.** Jeder Weg, der eine Zeile in `content/` schreiben kann – eine kompromittierte Automation, ein Prompt-Injection-Treffer in der Content-Kette, ein Merged-PR – erzeugt **persistente XSS** auf einer Seite mit Affiliate-Links, Newsletter-Formular und Merklisten. Da kein `script-src` greift, reicht ein `<script>`-Block oder ein `onerror=`-Attribut.

**Fix (zweistufig).**
1. **Sofort, offline:** Wache im Stil der bestehenden Gates (z. B. `scripts/content_html_wache.py` + `--selftest`) in `publication_check`/`endredaktion` einhängen: verbietet `<script`, `<iframe`, `on[a-z]+=`, `javascript:` in `content/**`; Positiv- und Gegenprobe wie bei `url_substring_guard.py`.
2. **Mit F-01:** echte CSP über Cloudflare-Header mit `script-src 'self' <sha256-Hashes der Inline-Blöcke>` (Hugo kann Hashes erzeugen) statt Meta-Provisorium – dann ist eine eingeschleuste Nutzlast wirkungslos, selbst wenn sie ins Markdown gelangt.

---

### F-07 🟠 Freigabe-Environments existieren nicht (4-Augen-Prinzip greift nicht)

**Befund (über die GitHub-API geprüft).** Im Repository existieren genau **zwei** Environments: `github-pages` (mit Branch-Policy) und `GITHUB_WORKFLOW_TOKEN` (**ohne** jede Schutzregel, von keinem Workflow mehr benutzt – Altlast). Die Workflows verlangen aber:

* `worker-deploy.yml:106-107` → `environment: cloudflare-produktion` (Doku: „Required reviewer, nur Branch main")
* `brand-surface-guard.yml:122` → `environment: brand-admin`
* `backup-offsite.yml:349` → `environment: backup`

Diese drei Environments sind **nicht angelegt**. Legt GitHub sie beim ersten Lauf still an, entstehen sie **ohne Reviewer-Regel und ohne Branch-Beschränkung** – die Freigabe, auf die sich die Kommentare berufen, existiert dann nur auf dem Papier. Die Secrets (`CF_WORKERS_DEPLOY_TOKEN`, `BRAND_ADMIN_TOKEN`, `BACKUP_REPO_TOKEN`, `BACKUP_PASSPHRASE`) werden beim ersten Lauf entsprechend **ohne Prüfinstanz** ausgegeben.

**Fix.** Environments anlegen (Settings → Environments), jeweils **Required reviewers** (Frank Hartung) und **Deployment branches: `main`** setzen; alle genannten Secrets **von „Repository" nach „Environment" verschieben**; `GITHUB_WORKFLOW_TOKEN` löschen. Danach einmal `worker-deploy.yml` per `workflow_dispatch` mit `pruefen`-Modus auslösen, um den Gate-Nachweis zu erzeugen.

---

### F-08 🟠 Export-Schlüssel liefert alle Adressen **und** Tokens

**Befund.** `/export/abonnenten` (`src/index.js:1073-1084`) gibt für **jeden aktiven Abonnenten** `email`, `token` und `themen` heraus. Schutz ist **ein statischer Header-Schlüssel** (`X-FF-Key`, konstantzeit verglichen – handwerklich korrekt), ohne Rate-Limit, ohne Protokoll, ohne Rotation. Derselbe Wert liegt als GitHub-Secret `NEWSLETTER_WORKER_EXPORT_KEY` in der CI und wird von Versand-/Nachgang-Workflows benutzt.

**Wirkung.** Ein einziges Leck (Log, Fehlermeldung, Screenshot, lokale Datei, CI-Artefakt, kompromittierter Workflow) ist ein **Totalverlust der Liste**: 100 % der Adressen **plus** gültige Tokens. Mit den Tokens kann jeder alle Abos **abmelden** (`/abmeldung`) oder Themen umstellen (`/praeferenzen`) – unumkehrbarer Reputations- und Vertrauensschaden. Es gibt außerdem **keinen Nachweis**, wer wann exportiert hat.

**Fix.**
1. **Blast-Radius senken:** In der Massenliste nur `email` + `themen` + `bestaetigt` liefern; Token je Adresse nur einzeln über `/export/kontakt` (oder Token **im Export hashen**).
2. **Zwei Schlüssel** mit getrennten Rechten (read-only für Reports, read+write für `/export/versuch`) oder HMAC-basierter, tagesgebundener Export-Token.
3. **Protokollieren:** jeder Export-Aufruf schreibt eine Zeile (Zeit, Route, Anzahl, Ergebnis) in KV – sichtbar mit `X-FF-Key` über `/healthz`.
4. **Rotation** in `docs/ANLEITUNG-NEWSLETTER-EIGENBETRIEB.md` festschreiben (90 Tage) und prüfen, dass `EXPORT_KEY` wirklich ≥ 32 Zufallszeichen hat (`openssl rand -hex 32`).

---

### F-09 🟡 Fremdinhalte in öffentlichen Issue-Flächen

**Befund.** `alert-on-failure.yml` übernimmt `github.event.workflow_run.name` und `head_branch` in öffentliche Issue-Titel/-Kommentare (`:158`, `:508-511`, `:545-547`). Bei `pull_request`-Läufen stammt der Workflow-Name aus der **Workflow-Datei des Beitragenden**, der Branch-Name aus dessen Wahl. Beides ist damit fremdbestimmt. Eine Kommando-Injektion entsteht **nicht** (Variablen werden als Werte übergeben, nicht erneut geparst – geprüft), aber **Markdown-/Link-Injection** in eine öffentliche Markenfläche ist möglich (Phishing-Links in einem offiziellen Issue).

**Fix.** `--workflow` in `scripts/alert_issue_identity.py` gegen eine **Allowlist** der bekannten Workflow-Namen prüfen (unbekannt → Sammel-Marker „Unbekannter Workflow"); `RUN_BRANCH` vor der Ausgabe auf `[A-Za-z0-9._/-]{1,80}` normalisieren; Ausgabe per `jq --arg` statt String-Interpolation. Zusätzlich: Als zusätzliche Hürde `permissions: contents: read` beibehalten und `issues: write` nur im zuständigen Job belassen (ist bereits so).

---

### F-10 🟡 Klickzähler manipulierbar (Analytics-Poisoning)

**Befund.** `/e` akzeptiert grundsätzlich jede Anfrage mit `Origin: https://franksfinanzcheck.de` – der Kommentar im Worker benennt selbst, dass dies per `curl` fälschbar ist. Die Allowlist auf Sitemap-Slugs verhindert zwar Datenmüll, aber **nicht** das Aufblähen der Zähler (D1-Writes) bis zum Tageslimit. Ein Ausfall der Schreibpfade wird zudem nicht abgefangen (`await env.DB.prepare(...).run()` ohne `try`).

**Fix.** (a) `try/catch` um den D1-Write mit `204`-Fallback, damit Zählprobleme nie in 500er laufen; (b) im Deploy erzeugte **Nichtce** je Artikel (statisch einbaubar als `?n=<HMAC(Slug, Build-SHA)>`), damit nur echte `/go/`-Seiten zählen; (c) WAF-Rate-Limit auf `stats.franksfinanzcheck.de/e` dokumentieren und aktivieren (Runbook-Schritt).

---

## 4. Prüfpunkte, die nur der Betreiber schließen kann (nicht remote lesbar)

| # | Prüfpunkt | Warum wichtig | Wo |
|---|-----------|---------------|-----|
| P-1 | **Branch-Protection/Ruleset für `main`**: Pflicht-Checks, kein Force-Push, keine Branches ohne PR | Der Dependabot-Auto-Merge **wartet** auf „Pflicht-Checks des Rulesets"; fehlen sie, wird nur kommentiert (richtig, H-02) – aber ein Ruleset fehlt dann als Schutz ohnehin | Settings → Rules/Rulesets |
| P-2 | **Secret Scanning + Push Protection** aktiv? | Bei **öffentlichem** Repo ist Push Protection der billigste Schutz gegen versehentliche Secrets | Settings → Code security |
| P-3 | **Private Vulnerability Reporting** aktiv? | `security.txt` verweist darauf; ohne Aktivierung läuft der Kanal ins Leere | Settings → Code security |
| P-4 | **Actions-Default-Token**: „Read repository contents" statt Read/Write; „Allow GitHub Actions to create and approve pull requests" bewusst entscheiden | Read/Write-Default wäre eine stille Rechte-Ausweitung; Auto-Approve wird für den Dependabot-Approval-Pfad gebraucht | Settings → Actions → General |
| P-5 | **Cloudflare**: WAF-Regeln für `abos.` / `stats.` / (später) `ki.`; KV-Jurisdiktion EU; D1-/KV-Verbrauch alarmieren | F-03 lässt sich an der Edge teilweise abfangen; EU-Jurisdiktion ist DSGVO-relevant | CF-Dashboard |
| P-6 | **Worker-Deploy-Drift**: `database_id`/KV-`id` sind im Repo Platzhalter – bestätigen, dass die Live-Bindungen über die Repository-Variablen kommen | Sonst ersetzt ein Repo-Deploy still die Bindung | CF + `worker-deploy.yml` |
| P-7 | **Secret-Hygiene**: `PINTEREST_ACCESS_TOKEN` ist laut `data/secrets_state.json` tot (Neu-Autorisierung nötig), `GH_PAT` wird nicht mehr benutzt (M-08) → widerrufen/löschen | Tote, aber gültige PATs/Token sind ein klassisches Einfallstor | GitHub Secrets + Pinterest |
| P-8 | **`EXPORT_KEY`-Länge** ≥ 32 Zeichen und von `NEWSLETTER_SMTP_PASS` verschieden | Kurze Schlüssel kippen F-08 von „theoretisch" zu „praktisch" | `wrangler secret` |

---

## 5. Maßnahmenplan

**Sofort (heute, ohne Deploy):**
1. F-01 Header-Regel in Cloudflare setzen und mit `curl -sI` belegen.
2. F-05 Log-Zeile ändern + `wrangler deploy` Newsletter-Worker (der Deploy ist unkritisch, die Änderung ist rein kosmetisch für den Datenfluss).
3. F-07 Environments `cloudflare-produktion`, `brand-admin`, `backup` mit Required Reviewers anlegen, Secrets dorthin verschieben, `GITHUB_WORKFLOW_TOKEN` löschen.
4. F-04 `WHISPER_TOKEN` setzen (`openssl rand -hex 32`) und in `.env` eintragen; Container neu starten.
5. P-1 bis P-4, P-7, P-8 prüfen (15 Minuten im Dashboard).

**Innerhalb 7 Tagen:**
6. F-02 Turnstile-Widget + Secret + Datenschutzerklärung (fail-closed wird aktiv).
7. F-03b Rate-Limits auf die vier GET-Routen + Tagesbudget für Anmeldungen.
8. F-06 Wache „kein rohes Skript in `content/`" mit Selbsttest, eingehängt in `endredaktion`/`publication_check`.
9. F-08a Massenexport ohne Tokens + Export-Protokoll.
10. F-09 Allowlist für Workflow-Namen + Branch-Normalisierung.

**Innerhalb 30 Tagen:**
11. F-03c Umzug der Anmelde-Schreibpfade auf D1/Queues (entkoppelt Kontingente dauerhaft).
12. F-06b echte CSP mit `script-src`-Hashes über die Edge (nachdem F-01 läuft).
13. F-10b Nonce-basierte `/go/`-Links + D1-Fehlerfang.
14. Wachen ausweiten: Klartext-Wache auf JS/TS/Worker, KV-/D1-Verbrauchsalarm, monatlicher Secret-Rotationslauf.

---

## 6. Anhang

### A. Reproduktion (jeder Befund nachprüfbar)

```bash
# F-01: Header der Produktionsseite
curl -sI https://franksfinanzcheck.de/ | grep -Ei 'strict-transport|x-frame|nosniff'   # erwartet: leer

# F-02: Formular ohne Turnstile
grep -c turnstile layouts/shortcodes/newsletter_form.html                             # erwartet: 0
grep -n "if (!geheim) return true" newsletter-worker/src/index.js                     # fail-open

# F-03: Rate-Limit nur auf zwei Routen
grep -n "rate_erlaubt(" newsletter-worker/src/index.js                                # 751, 947

# F-04: Token fail-open, Webhooks ohne Auth
sed -n '71,76p' tools/n8n/whisper_server.py
grep -n "WHISPER_TOKEN" tools/n8n/docker-compose.yml                                  # ${WHISPER_TOKEN:-} = leer erlaubt
python3 -c "import json,glob;[print(f,[n.get('parameters',{}).get('authentication') for n in json.load(open(f))['nodes'] if 'webhook' in n['type'].lower()]) for f in glob.glob('n8n/workflows/*.json')]"

# F-05: Adresse im Log
grep -n 'für \${email}' newsletter-worker/src/index.js

# F-07: Environments
gh api repos/frank-hartung/franksfinanzcheck-blog/environments --jq '.environments[].name'

# F-08: Export liefert Tokens
grep -n -A6 "'/export/abonnenten'" newsletter-worker/src/index.js
```

### B. Test- und Wachenläufe (14.10.2026, alle grün)

```
newsletter-worker      node --test test/*.test.js  → 76/76 pass
cloudflare/ki-assistent node --test                → 17/17 pass
cloudflare/klick-zaehler node --test test/worker.test.mjs → 30/30 pass
scripts/url_substring_guard.py                     → 744 Dateien sauber
scripts/clear_text_logging_guard.py                → 477 Python-Dateien sauber
scripts/ki_assistent_gate.py                       → 9 bereit, 1 Warnung (KA1)
scripts/actions_version_guard.py                   → keine Drift
Secret-Regex-Scan (Arbeitsbaum)                    → keine Funde (nur Test-Fixtures)
PII-/IP-Scan (data/, State-Dateien)                → keine personenbezogenen Daten
```

### C. Blindstellen dieses Audits (ehrlich benannt)

* **Kein Live-Pentest** der Domain (kein `curl` gegen `franksfinanzcheck.de` aus dieser Umgebung) – F-01 ist aus Quelldatei und Plattformverhalten belegt, nicht am Live-Header gemessen.
* **Keine Einsicht in Cloudflare-Konto und GitHub-Settings** (API-Token liefert dort 403): WAF-Regeln, Turnstile-Keys, KV-Jurisdiktion, tatsächlich gesetzte Secrets, Branch-Protection und Secret-Scanning-Status sind **Prüfpunkte (Abschnitt 4)**, keine Feststellungen.
* **Keine Hugo-Build-Ausführung** in dieser Umgebung (Hugo nicht installiert) – Rendering-Ebene wurde über Templates, Gates und Tests bewertet, nicht über `public/`.
* **Kein Last-/Missbrauchstest** gegen die Produktions-Worker (F-03 ist aus Code und Kontingenten abgeleitet, nicht durch einen Angriff belegt – bewusst, um Ihr Kontingent nicht zu belasten).

---

*Erstellt im Auftrag der Betreiberin/des Betreibers. Alle Befunde enthalten Datei-/Zeilenbelege und einen konkreten Behebungsweg. Reihenfolge nach Risiko, nicht nach Aufwand.*

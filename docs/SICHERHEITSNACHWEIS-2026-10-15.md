# Sicherheitsnachweis — Behebungslauf 15. Oktober 2026

**Zweck:** Jeder Befund aus `SICHERHEITSAUDIT-PREMIUM-2026-10-14.md` mit
Behebung, Beleg und Wiederholungsbefehl. Diese Datei ist der Gegenbeweis zur
Behauptung „ist behoben" — sie nennt für jeden Punkt den Befehl, der es zeigt.

**Regel für dieses Dokument:** Kein Häkchen ohne Kommandozeilen-Beleg. Wo es
keinen Beleg geben kann (Dashboard-Schritte), steht der Schritt in
`docs/SICHERHEIT-BETRIEB-RUNBOOK.md` und hier der Vermerk **„offen — Runbook
A…"**. Was offen ist, ist offen.

---

## 1. Ergebnis in einer Zeile je Befund

| Finding | Schwere | Status | Beleg |
|---|---|---|---|
| F-01 Header fehlen live | 🔴 | **Repo fertig, Dashboard offen** | `npm run header:check` → grün; live erst nach Runbook A1 |
| F-02 Formular ohne Bot-Schutz | 🔴 | **behoben** | `npm run betrieb:check`; Worker-Test „Turnstile" |
| F-03 KV-DoS über GET-Routen | 🔴 | **behoben** | Worker-Tests „Tagesbudget", „Mengenklassen"; WAF-Vorlage A2 |
| F-04 Whisper/n8n/Bridge offen | 🟠 | **behoben** | `npm run n8n:schutz`; `n8n_bridge.py --selftest` (5 Gegenproben) |
| F-05 Adresse im Klartext-Log | 🟠 | **behoben** | Worker-Test „Log-Hygiene" |
| F-06 `unsafe=true` ohne Wache | 🟠 | **behoben** | `npm run content:check` (13 Proben) + `[security]` in `hugo.toml` |
| F-07 Environments fehlen | 🟠 | **offen — Runbook A4** | Dashboard-Schritt; Repo verlangt sie bereits |
| F-08 Massenexport mit Token | 🟠 | **behoben** | Worker-Tests „Schluesselrollen", „Export-Protokoll"; Digest-Nachweis |
| F-09 Issue-Injection | 🟡 | **behoben** | `python3 -m unittest scripts.tests.test_alert_scoping` (20 Tests, inkl. Angriffsname) |
| F-10 Zähler/Try-Catch | 🟡 | **behoben** | `node --test test/worker.test.mjs` (34 Tests, 3 neue Fehlerarten) |

**Zählung:** 8 von 10 vollständig behoben · F-01 in der Umsetzung (ein
Dashboard-Schritt) · F-07 offen (reine Klickarbeit, Runbook A4).

---

## 2. Läufe — Rohdaten vom 15.10.2026

```
newsletter-worker        node --test        91 Tests, 91 grün   (vorher 76)
cloudflare/klick-zaehler node --test        34 Tests, 34 grün   (vorher 30)
cloudflare/ki-assistent  node --test        17 Tests, 17 grün   (unverändert)
scripts/newsletter_versand.py --selftest    64 Fälle grün       (vorher 60)
scripts/newsletter_digest.py --selftest     62 Fälle grün       (vorher 54)
scripts/newsletter_zustellbarkeit.py --selftest  49 Fälle grün  (unverändert)
scripts/robustheits_gate.py --selftest      14 Sabotage-Proben erkannt
scripts/content_html_wache.py --selftest    13 Fälle grün
scripts/blog_header_gate.py --selftest      19 Fälle grün      (vorher 10)
scripts/worker_betrieb_wache.py --selftest  10 Fälle grün
scripts/n8n_schutz_wache.py --selftest       9 Fälle grün
scripts/n8n_bridge.py --selftest            5 Gegenproben (401/403/415/413/503)
scripts/alert_issue_identity.py --selftest  10 Fallgruppen, 59 Workflows
scripts/tests (unittest), test_alert_scoping 22 Tests, 22 grün
scripts/tests (unittest), test_blog_header_gate 24 Tests, 24 grün (neu, WF-E813)
scripts/tests/sim/alert_scoping_sim.mjs     38 Szenarien, 38 grün (vorher 28)
```

Jeder Selbsttest baut **Gegenproben**: Er sabotiert die Regel und prüft, dass
sie anschlägt. Eine Wache ohne Gegenprobe ist ein Wunsch, keine Wache.

---

## 3. Was im Einzelnen geändert wurde

### F-02 — Bot-Schutz (behoben)
- `hugo.toml`: `params.turnstileSiteKey` (leer = kein Widget, gesetzt = Widget + Skript).
- `layouts/shortcodes/newsletter_form.html`: Widget-Auslieferung **nur** mit
  Site-Key; Datenschutz-Satz direkt beim Feld.
- `static/premium/ff-newsletter.js`: Token holen (`turnstile.execute`), an
  `cf-turnstile-response` hängen, Fehlschlag ehrlich melden, Widget nach
  Fehlversuch zurücksetzen (`reset`) — Turnstile-Token sind einmalig.
- `newsletter-worker/src/index.js`: Prüfung fail-closed sobald Secret gesetzt;
  `/healthz` meldet `turnstile: aktiv|inaktiv`.
- `content/datenschutz/index.md`: Turnstile als Dienst benannt (Abschnitt
  Newsletter), inkl. „nur beim Absenden geladen, keine Cookies, kein Profil".

### F-03 — KV-Schutz (behoben)
- **Tagesbudget** `ANMELDUNG_MAX_PRO_TAG` (Standard 100): greift **vor** jedem
  Schreibzugriff, Antwort 503 mit ehrlichem Hinweis, genau **eine** laute
  Meldung je Stunde (KV-Schlüssel `warn:anmeldung:<tag>`).
- **Mengenklassen** für die vorher ungedeckelten Routen:
  `lesen` 60/min (Token-Seiten), `feedback` 30/min, `export` 20/min — plus
  eigenes Limit für den token-tragenden Abmeldeweg.
- **Rückfall ohne Binding:** Zähler im Instanzspeicher (kein KV-Verbrauch),
  Grenze per `RATE_LIMIT_<KLASSE>` justierbar.
- Belege: Tests „Tagesbudget", „Mengenklassen", „Mengenzaehler im Speicher",
  „Mengenbegrenzung greift auch ohne Binding", „Abmeldung mit Token".

### F-04 — Automatik-Kette (behoben)
- `tools/n8n/whisper_server.py`: ohne Token **503**, Opt-in nur ausdrücklich
  (`WHISPER_OHNE_TOKEN_OK=1`).
- `tools/n8n/docker-compose.yml`: `${WHISPER_TOKEN:?…}` und
  `${N8N_WEBHOOK_TOKEN:?…}` — der Stack startet ohne Secrets nicht mehr.
- `n8n/workflows/*.json` **und** `tools/n8n/workflows/*.json`: alle drei
  Webhook-Knoten `authentication: headerAuth` + Credential `FF Webhook-Secret`;
  Whisper-Knoten mit `FF Whisper-Token`.
- `scripts/n8n_bridge.py`: `Content-Type`-Zwang (erzwingt Preflight),
  Herkunftsprüfung (lokaler CSRF-Schutz), Secret-Pflicht mit Konstantzeit-
  Vergleich, Größenlimit 256 KB, 503 statt stiller Öffnung ohne Secret.

### F-05 — Log-Hygiene (behoben)
- `console.warn` schreibt statt der Adresse einen Kurz-Hash
  (`sha256:…`), wie die Observability-Zusage es verlangt.

### F-06 — Content-Wache (behoben)
- `hugo.toml`: `[security]`-Sektion — `enableInlineShortcodes = false`, nur
  `HUGO_*`-Variablen sichtbar, Bau lädt **keine** fremden Quellen,
  Programm-Allowlist ausgeschrieben.
- `scripts/content_html_wache.py`: 11 Einschleusregeln (`<script`, `<iframe`,
  `on*=`, `javascript:`, `data:text/html`, `<base`, Meta-Refresh, SVG mit
  Verhalten, Vorlagen-Zugriffe …) + Prüfung der Bau-Härtung, mit 13 Proben.

### F-08 — Export (behoben)
- **Zwei Rollen:** `EXPORT_KEY` (lesen, ohne Token) und `EXPORT_KEY_WRITE`
  (Token nur mit `?mit_token=1`). Fehlt der zweite, gilt der erste weiter —
  kein Bruch, aber Trennung möglich und als Warnung gemeldet.
- **Export-Protokoll:** jeder Aufruf (auch 403) im KV, 30 Tage, mit
  Schlüsselabdruck (8 Hex-Zeichen, nie der Wert); sichtbar nur mit Schlüssel.
- **Konsumenten:** `newsletter_versand.py` (Nachgang) und
  `newsletter_digest.py` (Listenversand) senden `mit_token=1` mit dem
  Schreibschlüssel; der Digest bricht **ab**, wenn ein Token fehlt
  (kein Versand ohne Abmeldelink — rechtlich keine Option).


#### Nachtrag 24.10.2026 — F-08-Vollständigkeit

Der damalige Fix schützte den Token-Massenexport, ließ aber einen Rollen-Bypass
über `/export/token` und `/export/kontakt` zu: beide gaben mit dem Leseschlüssel
weiterhin Token zurück; `/export/versuch` akzeptierte damit auch
Statusänderungen. Zudem fiel `EXPORT_KEY_WRITE` bei Fehlen auf `EXPORT_KEY`
zurück. Diese Lücken wurden im Code gehoben: alle drei Einzelrouten verlangen
jetzt einen explizit verschiedenen Schreibschlüssel; Token/E-Mail werden bei
Lookups ausschließlich im POST-Body übertragen. Fehlende oder gleiche Schlüssel
sind fail-closed. Fehlversuche werden höchstens einmal pro Stunde in KV
protokolliert, um anonyme 403-Stürme nicht als KV-Write-DoS zu nutzen.

**Produktion nicht bestätigt:** Der Worker wurde in dieser Prüfung nicht live
deployt und Cloudflare-/GitHub-Secrets konnten nicht eingesehen werden. Der
obige 15.10.-Nachweis beschreibt daher den damaligen, unvollständigen Stand,
nicht den bestätigten Produktionszustand.

### F-09 — Issue-Injection (behoben)
- `scripts/alert_issue_identity.py`: `saeubern()` + Feld `workflow_sauber`,
  `--saeubern` für die Kommandozeile; Steuerzeichen, Bidi-Tricks,
  Markdown-Träger und `@`-Mentions entschärft.
- `.github/workflows/alert-on-failure.yml`: `kanalRein()` für Workflowname,
  Zweig, Event und Ergebnis (Titel, Body, Logs); Auto-Close-Kommentar nutzt die
  entschärfte Fassung.
- **Beleg:** Die Verhaltens-Simulation führt den Angriffsnamen
  `` Layout-AI` @all [Klick](http://boese.example) `` aus — der Body enthält
  danach weder `@all` noch `[Klick]` noch einen Fremdlink.

### F-10 — Zähler (behoben)
- `cloudflare/klick-zaehler/worker.js`: `try/catch` um den D1-Schreibpfad —
  Zählfehler brechen den Klick nicht mehr (und erzeugen keinen 500er im
  Browser eines Lesers). Tests: geworfener Fehler, fehlende Bindung,
  gestörter Limiter, greifender Limiter.

---

## 4. Offene Punkte — ehrlich benannt

| Was | Warum offen | Schritt |
|---|---|---|
| Sicherheits-Header live | Cloudflare-Proxy + Transform Rule (Dashboard) | Runbook A1, danach `npm run header:check:live` |
| Mengenregeln an der Edge | Dashboard | Runbook A2 |
| Turnstile-Widget live | Site Key + Worker-Secret | Runbook A3 |
| Environments + Reviewer | Dashboard | Runbook A4 |
| Branch-Protection, Push-Protection, PVR | Dashboard (API liefert 403) | Runbook P-1, P-2, P-3 |
| Widerruf toter Tokens (Pinterest, alter PAT) | Anbieter-Dashboards | Runbook P-7 |
| Datenschutz-Text nach Proxy | Text fertig vorbereitet | Runbook B7 |
| F-10b Nonce je Artikel (Zähler) | Audit §5 terminiert den Punkt auf „innerhalb 30 Tagen“; er braucht einen Schlüssel im Hugo-Bau (Umbau), kein Dashboard-Klick | Runbook A6, danach `node --test test/*.test.mjs` im Zähler-Ordner |

Diese Punkte sind **nicht** durch Code zu schließen. Solange sie offen sind,
meldet die Sicherheits-Wache F-01 täglich als roten Lauf — mit Absicht: Ein
stiller Zustand wäre der schlechtere Zustand.

# Newsletter-Taktgeber – Report 25.09.2026 (Freitag, Versandtag ohne Versand)

**Anlass:** „Ich habe von Resend heute noch keinen Newsletter an
kontakt@franksfinanzcheck.de erhalten.“ Freitag ist Versandtag, Soll
06:30 MESZ (04:30 UTC). Um 11:40 MESZ lag keine Mail vor.

**Einordnung, ehrlich:** Es ist nichts an Resend, nichts an der Ausgabe
und nichts an der Adresse kaputt. **Der Versandlauf wurde heute nie
gestartet.** GitHubs Scheduler hat den Cron nicht gefeuert – und die
Kadenz-Wache, die genau das auffangen sollte, hing am selben Scheduler und
hat seit ihrer Erstellung am 23.09. **null Läufe**. Das ist der zweite
Versandtag in Folge (Di 23.09., Fr 25.09.), an dem der Cron ausblieb. Ein
Netz, das am selben Haken hängt wie die Last, ist kein Netz.

---

## 1. Befund – gemessen, nicht vermutet

### 1.1 Der Lauf fehlt

| Was | Gemessen (GitHub-API, 25.09. 09:45 UTC) |
|---|---|
| Läufe *Newsletter-Daily* heute | **0** – letzter Lauf überhaupt: 23.09. 01:26 UTC (manuell) |
| Läufe *Newsletter-Kadenz-Wache* (seit 23.09. 09:28) | **0** – der 08:11-Cron ist nie gekommen, auch heute nicht |
| Läufe *Newsletter-Lifecycle* (`17 * * * *`, seit 03:35 heute) | 1 – erster um 09:38 UTC (statt 04:17, 05:17, 06:17, 07:17, 08:17, 09:17) |
| Cron-Änderung 05:05 → 04:30 UTC (PR #367) | merged 03:50 UTC – 40 min vor dem neuen Termin; weder 04:30 noch 05:05 lösten aus |

### 1.2 Der Scheduler des Repos ist systematisch verspätet

Alle `schedule`-Läufe des Repos am 25.09. (bis 09:45 UTC) gegen ihren Cron:

| Workflow | Cron (UTC) | Tatsächlich gestartet | Verspätung |
|---|---|---|---|
| Qualitäts-Gate | 01:15 | 06:10 | 4 h 55 |
| Revenue-Import | 02:10 | 07:39 | 5 h 29 |
| Pinterest-Token-Wache | 02:40 | 08:09 | 5 h 29 |
| Offsite-Backup | 03:00 | 08:24 | 5 h 24 |
| Content-Reserve | 03:25 | 08:57 | 5 h 32 |
| AGC-Autopilot | 03:45 | 09:05 | 5 h 20 |
| Affiliate-Integritäts-Wache | 04:00 | 09:15 | 5 h 15 |
| **Newsletter-Daily** | **04:30** | **–** | **ausgefallen** |
| **Newsletter-Kadenz-Wache** | **08:11** | **–** | **ausgefallen** |
| Uptime-Monitor | `*/15` | 00:12, 04:57 | 2 statt 39 Läufe |

Gestern (24.09.) dasselbe Bild: Uptime-Monitor 6 statt 96 Läufe,
Backup 03:00 → 08:00, Blog-Gesundheit 05:45 → 10:31, Lesehilfen 06:20 →
11:57. GitHub dokumentiert selbst, dass `schedule` unter Last verzögert
oder verworfen wird – an diesem Repo ist das kein Ausnahme-, sondern der
Normalzustand. **Ein Versand um 06:30 deutscher Zeit ist mit GitHub-Crons
allein nicht zu halten.**

### 1.3 Alles dahinter ist gesund

| Glied | Zustand |
|---|---|
| Ausgabe | lokal gebaut: 5 Artikel, QA **100/100**, 0 Funde (`--build --days 7`) |
| Resend-DNS | `send` → CNAME `send.forge.rmta.net` (SPF + Bounce-MX), `rsend` CNAME, DKIM `resend._domainkey` (p=…) – vollständig |
| DMARC | `p=reject; adkim=s; aspf=s; rua=…cloudflare.net` – vorhanden (Hinweis § 5) |
| Capture-Worker | `abos.franksfinanzcheck.de` löst auf (Cloudflare-proxied, Worker-Custom-Domain); Antwort aus dieser Sandbox nicht messbar (Egress gesperrt) |
| Versand-Status | `letzte_ausgabe` fehlt – der Eigenbetrieb hat **noch nie** gesendet, auch kein Testversand seit dem Merge um 03:35 UTC |
| GitHub-Secrets | aus dieser Umgebung nicht einsehbar (403) – ob `RESEND_API_KEY`/`NEWSLETTER_WORKER_EXPORT_KEY` gesetzt sind, zeigt erst der erste Lauf |

### 1.4 Warum niemand es gemerkt hat

Ein Lauf, der nie startet, wird nicht rot – kein Ereignis, kein
Fehler-Alerting, kein Issue. Die Kadenz-Wache war die Antwort darauf
(23.09.) – aber als GitHub-Cron. Der Fehler zweiter Ordnung: **die Wache
gegen ausbleibende Crons war selbst ein Cron.**

---

## 2. Die Reparatur – ein Taktgeber außerhalb von GitHub

Der Cloudflare-Worker (`newsletter-worker/`) existiert bereits, hat bereits
einen GitHub-PAT für `workflow_dispatch` (Bestätigungsmails) und läuft auf
einer Plattform, deren **Cron Triggers auf die Minute** feuern. Er wird zum
**Taktgeber**:

```
Cloudflare Cron Trigger (UTC, minutengenau)
  30 4 * * TUE,FRI  ─▶ workflow_dispatch newsletter-daily.yml   planmaessig=true, tage=7
   5 5 * * TUE,FRI  ─▶ workflow_dispatch newsletter-cadence.yml (zählt nach, holt nach, wird laut)
  17 * * * *        ─▶ workflow_dispatch newsletter-lifecycle.yml aktion=nachgang
                                    │
GitHub-Crons bleiben stehen ────────┘ drittes Netz; kommen sie verspätet:
                                      „Versandpause: Termin belegt“ – kein Doppelversand
```

**Freigabestufe unverändert:** `planmaessig=true` ist exakt das, was der
GitHub-Cron setzt – nie `live`, nie `test_adresse`. Halt (`versand_unklar`),
QA-Gate, 0-Abonnenten-Sperre, Di/Fr-Vertrag und Wochenlimit entscheidet
weiterhin allein `newsletter_digest.py`. Der Worker versendet keine Mail,
kennt im Dispatch keine Adresse und keinen Mail-Key.

### Geänderte Stellen

| Datei | Änderung |
|---|---|
| `newsletter-worker/src/index.js` | `scheduled()`-Handler; Tabelle `TAKT` (Cron → Workflow + Inputs); generisches `github_dispatch()`; 3 Versuche mit Pausen (5 s / 20 s), **kein** Retry bei 401/403/404; Protokoll `takt:{name}` im KV (45 Tage TTL); `/healthz` zeigt `takt.crons` + `takt.letzte` (ohne Adressen/Secrets); unbekannter Cron → kein Dispatch |
| `newsletter-worker/wrangler.toml` | `[triggers] crons = ["30 4 * * TUE,FRI", "5 5 * * TUE,FRI", "17 * * * *"]`; PAT-Berechtigung korrigiert (s. u.) |
| `newsletter-worker/test/index.test.js` | 9 neue Tests: Cron → richtiger Workflow/Inputs (nie live), Retry-Pfade, 403 ohne Retry, ohne PAT kein Netz, unbekannter Cron, healthz-Takt, **wrangler.toml ≡ TAKT** (Ziffern als Wochentag verboten) |
| `scripts/newsletter_cadence.py` | fällig ab **SOLL + 30 min** (05:00 UTC, aus dem Versandvertrag gerechnet – `FAELLIG_AB`), nicht erst 08:11; Befundtexte nennen den gerechneten Soll; Selftest 20 Fälle |
| `scripts/newsletter_zustellbarkeit.py` | neue Regel **C8 Taktgeber**: liest `/healthz.takt` – Worker ohne `takt` = Fund (alte Version), letzter Dispatch gescheitert = Fund (403 → PAT-Klickweg), letzter fälliger Di/Fr-Termin verpasst = Fund, nie gefeuert vor dem ersten Termin = Hinweis, kein JSON = nicht messbar |
| `.github/workflows/newsletter-cadence.yml` | Header (zweiter Vorfall), `push`-Trigger **nur** für Änderungen an der Wache selbst (Selbstbeweis auf main – s. § 3) |
| `.github/workflows/newsletter-daily.yml`, `newsletter-lifecycle.yml` | Kommentare: Taktgeber, PAT-Berechtigung |
| `docs/ANLEITUNG-NEWSLETTER-EIGENBETRIEB.md` | § 3 Schritt 1 (PAT, Cron-Triggers), § 4 Tabelle „wer startet“, neu **§ 4a Der Taktgeber** |
| Tests | `test_newsletter_cadence.py` (+5), `test_newsletter_schedule.py` (Fälligkeit), `test_newsletter_zustellbarkeit.py` (+8, C8) |

### Zwei Fallen, die dabei aufgefallen sind (behoben in Doku + Code-Kommentaren)

1. **PAT-Berechtigung war falsch dokumentiert.** `wrangler.toml`, die
   Anleitung und der Lifecycle-Workflow nannten „workflows: write“. Das
   ist das Recht, Workflow-*Dateien* zu ändern. `POST …/dispatches`
   verlangt **„Actions: Read and write“** (GitHub-REST-Doku). Ein nach
   alter Anleitung erstellter PAT bekommt 403 – dann kommt weder
   Bestätigungsmail-Dispatch noch Takt an. C8 meldet genau diesen Fall mit
   Klickweg.
2. **Cloudflare zählt Wochentage anders.** 1 = Sonntag … 7 = Samstag
   (Quartz). Der Unix-Ausdruck `2,5` hieße dort **Montag/Donnerstag**.
   Deshalb `TUE,FRI` – und ein Test, der Ziffern im Wochentagsfeld
   ablehnt.

---

## 3. Was jetzt zu tun ist (Betreiber, Reihenfolge)

### Heute – die Freitagsausgabe nachholen (2 Minuten, eine von zwei Wegen)

**Weg A – Klick:** Actions → *Newsletter-Daily (Capture-Wache + Digest)*
→ **Run workflow** (Branch `main`):

1. Erst Probe: `test_adresse = kontakt@franksfinanzcheck.de` → erwartet
   `✅ TESTVERSAND ERFOLGT: 1 Adresse(n)`. Kommt stattdessen ein
   ❌ mit `RESEND_API_KEY`/`NEWSLETTER_WORKER_EXPORT_KEY`, fehlen die
   GitHub-Secrets (Anleitung § 3/4) – das ist dann die eigentliche
   Ursache *hinter* dem Cron-Ausfall.
2. Dann die Liste: `planmaessig = true` (sonst nichts) → sendet an alle
   aktiven Abonnenten, bucht den Freitagstermin. Bei 0 Abonnenten:
   ehrliche Leermeldung.

**Weg B – Merge:** Dieser PR ändert die Kadenz-Wache; ihr neuer
`push`-Trigger lässt sie beim Merge auf `main` sofort laufen. An einem
Di/Fr nach 05:00 UTC ohne Lauf des Tages holt sie den Planlauf nach
(`planmaessig=true`) – **der Merge heute ist die Heilung.** An jedem
anderen Tag ist es ein grüner Ruhetag.

> `kontakt@franksfinanzcheck.de` ist eine **Cloudflare-Weiterleitung**, kein
> Postfach: Die Mail landet im dahinterliegenden Zielpostfach (dort auch
> Spam prüfen) und im Cloudflare-Email-Routing-Log. Resend → *Emails*
> zeigt den Zustellstatus je Mail.

### Diese Woche – den Taktgeber scharf schalten

```bash
cd newsletter-worker
npx wrangler secret put GITHUB_PAT   # nur falls der PAT NICHT „Actions: Read and write“ hat
npx wrangler deploy                  # aktiviert [triggers].crons
curl -s https://abos.franksfinanzcheck.de/healthz | jq .takt   # crons: 3 Einträge
```

Beweis am nächsten Dienstag 06:30 MESZ: Actions zeigt einen
*Newsletter-Daily*-Lauf `workflow_dispatch` um 04:30 UTC; `/healthz` →
`takt.letzte.digest.status = "dispatched"`; Cloudflare → Worker →
Settings → **Trigger Events** listet die Ausführung; die
Zustellbarkeits-Wache im Lauf meldet **C8 ok „Taktgeber tickt“**.

---

## 4. Beweise

| Prüfung | Ergebnis |
|---|---|
| `newsletter-worker`: `node --test` | **47/47** (vorher 38) |
| `scripts/newsletter_cadence.py --selftest` | **20 Fälle grün** (vorher 14) |
| `scripts/newsletter_zustellbarkeit.py --selftest` | **41 Fälle grün** (vorher 25) |
| `python3 -m unittest discover -s scripts/tests -p "test_newsletter_*.py"` | **204 Tests OK** (1 übersprungen) |
| `newsletter_digest.py --selftest` / `newsletter_versand.py --selftest` | 50 / 29 grün (unverändert) |
| `newsletter_studio.py --brand` | Themen ↔ `wrangler.toml` deckungsgleich (Trigger-Block stört den Vertrag nicht) |
| Lokaler Digest-Bau für heute | 5 Artikel, QA 100/100 |

## 5. Was NICHT erledigt ist (ehrlich)

1. **Der Lauf für heute ist nicht gestartet.** Das Agenten-Token hat kein
   `actions:write` (`gh workflow run` → HTTP 403). Weg A oder B in § 3
   braucht einen Klick des Betreibers.
2. **Der Worker ist nicht neu deployt.** Kein Cloudflare-Zugang in dieser
   Umgebung. Bis `wrangler deploy` läuft, tickt der Taktgeber nicht – und
   C8 meldet das ab dem ersten Lauf als Fund („Taktgeber fehlt“), damit es
   nicht vergessen wird.
3. **Secrets-Stand unbekannt.** Ob `RESEND_API_KEY` und
   `NEWSLETTER_WORKER_EXPORT_KEY` in GitHub liegen, zeigt erst der erste
   Lauf (fail-closed mit Klickweg).
4. **DMARC-Hinweis (kein Fund, aber ein Risiko):** `aspf=s` (strikt)
   bedeutet: Resends Return-Path `send.franksfinanzcheck.de` ist nicht
   SPF-aligned; DMARC besteht **nur** über DKIM. Bricht DKIM (Schlüssel-
   rotation, verändernde Weiterleitung), wird bei `p=reject` hart
   abgewiesen. Empfehlung: `aspf=r` (relaxed) – Subdomain zählt dann als
   aligned, `p=reject` bleibt. Änderung in Cloudflare → DNS →
   `_dmarc` TXT.
5. **Lifecycle-Workflow steht nicht in der Wacht-Liste des
   Fehler-Alertings** (`alert-on-failure.yml`) – ein roter Nachgang bleibt
   still. Eine Zeile, aber ein eigener Entscheid (Alarm-Routing C14).

## 6. Grundsatz, der bleibt

**Wer einen Termin verspricht, braucht eine Uhr, die er selbst kontrolliert.**
GitHub-Crons sind Ereignisse „nach bestem Bemühen“; Cloudflare Cron
Triggers sind ein Vertrag auf die Minute. Der Versand hängt jetzt an der
Uhr – GitHub bleibt der Arm, der ausführt, und die Wache bleibt der Blick,
der nachzählt. Alle drei sind idempotent, alle drei sind messbar
(`/healthz.takt`, C8, Kadenz-Report), und keiner von ihnen hat mehr
Rechte als der Cron, den er ersetzt.

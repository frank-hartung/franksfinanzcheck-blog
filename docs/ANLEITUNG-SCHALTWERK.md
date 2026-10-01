# 🔌 ANLEITUNG: Schaltwerk – der eigene Zapier-Ersatz

> Rollout 01.10.2026 · Report: `SCHALTWERK-ZAPIER-NACHBAU-PREMIUM-2026-10-01.md`
> Cockpit: `SCHALTWERK-STATUS.md` · Regeln: `data/automationen.yaml`

**Zweck:** Alles, was bisher ein Automatisierungsdienst wie Zapier oder Make
erledigt hätte – „wenn X passiert, dann tu Y“ – läuft hier im eigenen
Repository. Ohne Zapier-Konto, ohne API-Schlüssel eines Fremddienstes, ohne
Task-Limit und ohne laufende Kosten. GitHub Actions ist der Taktgeber
(öffentliches Repository = unbegrenzte Minuten), Python die Engine.

---

## 1. Zapier-Begriffe und ihre Entsprechung

| Zapier | Schaltwerk | Datei |
|---|---|---|
| Zap | Regel | `data/automationen.yaml` |
| Trigger | Trigger-Provider | `scripts/schaltwerk_triggers.py` |
| Filter / Paths | `filter:` je Regel | `data/automationen.yaml` |
| Action | Aktion | `scripts/schaltwerk_actions.py` |
| Multi-Step-Zap | `aktionen:` (Liste, der Reihe nach) | – |
| Task-History | Protokoll + Cockpit | `data/schaltwerk_log.jsonl` |
| Deduplication | `dedupe_key` + State | `data/schaltwerk_state.json` |
| Throttle/Limits | `throttle:` je Regel | – |
| Webhooks by Zapier | `repository_dispatch` → `--event` | `.github/workflows/schaltwerk.yml` |
| Schedule by Zapier | Trigger `zeitplan` / `intervall` | – |
| RSS by Zapier | Trigger `rss` | – |
| **Preis** | **0 €** | – |

---

## 2. Arbeitsteilung – wer sendet was

Das Schaltwerk ersetzt den Social-Autopiloten **nicht**, es dirigiert ihn.

| Aufgabe | Zuständig |
|---|---|
| Neue Artikel, Evergreen-Recycling, 14-Tage-Plan, Kadenz | **Social-Autopilot** (`social-autopilot.yml`) |
| Update-Wellen für überarbeitete Bestandsartikel | **Schaltwerk** |
| Agent-Reach-Signale → Themenkuratierung | **Schaltwerk** |
| Wachhunde (Standby-Kanäle, stille Kanäle, Konfigdrift) | **Schaltwerk** |
| Nächtliche Planerneuerung | **Schaltwerk** |
| Ad-hoc-Post per Webhook | **Schaltwerk** |
| Erst-Pins auf Pinterest | `pinterest-ai.yml` (unverändert) |
| Antworten/Dialog | `social-dialog.yml` (unverändert) |

Damit kann kein Beitrag doppelt erscheinen: Jede sendende Regel trägt einen
`dedupe_key`, schreibt ihren Erfolg in denselben Social-State wie der
Autopilot (`data/social/state.yaml`) und läuft durch dasselbe harte Gate
(`scripts/social_gate.py`).

---

## 3. Bedienung

```bash
python3 scripts/schaltwerk.py --selftest     # offline, fail-closed (Pflicht vor jedem Umbau)
python3 scripts/schaltwerk.py --list         # Regelwerk auflisten
python3 scripts/schaltwerk.py --dry-run      # zeigt, was passieren WÜRDE (schreibt nichts)
python3 scripts/schaltwerk.py --run          # scharf
python3 scripts/schaltwerk.py --run --regel update-welle --verbose
python3 scripts/schaltwerk.py --status       # nur Cockpit neu schreiben
```

Auf GitHub: *Actions → „Schaltwerk (Automationen)“ → Run workflow* mit
`modus = run | dry-run | list | status`.

**Exit-Vertrag:** `0` = alles gut (Standby zählt **nicht** als Fehler),
`2` = mindestens eine Aktion ist hart gescheitert → der Workflow wird rot.

---

## 4. Eine eigene Regel schreiben

```yaml
  - id: meine-regel                 # eindeutig, kleingeschrieben
    name: "Klartext für das Cockpit"
    enabled: true
    trigger:
      typ: neuer_artikel
      params: {max_alter_stunden: 48}
    filter:                          # UND-verknüpft
      - feld: artikel.pillar
        operator: gleich
        wert: "strom-gas"
    aktionen:                        # der Reihe nach
      - typ: social_post
        params: {kanal: mastodon, winkel: zahl, artikel_slug: "{artikel.slug}"}
      - typ: protokoll
        params: {text: "Strom-Artikel {artikel.slug} getootet."}
    dedupe_key: "meine-regel:{artikel.slug}"
    throttle: {max_pro_tag: 3, max_pro_lauf: 1, cooldown_minuten: 120}
```

Platzhalter (`{artikel.slug}`, `{{ titel }}`) ziehen ihre Werte aus dem, was
der Trigger unter `daten` liefert. Unbekannte Platzhalter werden zu einer
leeren Zeichenkette – sie reißen nichts ab.

Danach **immer**: `python3 scripts/schaltwerk.py --selftest && \
python3 scripts/schaltwerk.py --dry-run`.

---

## 5. Trigger-Katalog

| `typ` | Feuert, wenn … | Wichtige `params` |
|---|---|---|
| `neuer_artikel` | ein Artikel frisch veröffentlicht ist | `max_alter_stunden` |
| `artikel_aktualisiert` | ein Bestandsartikel überarbeitet wurde | `max_alter_tage` |
| `recherche_signal` | der Agent-Reach-Brief passende Treffer hat | `stichworte`, `max_treffer`, `max_alter_tage` |
| `zeitplan` | eine Uhrzeit erreicht ist (Berliner Zeit) | `zeiten`, `tage`, `toleranz_minuten` |
| `intervall` | seit X Minuten nichts passiert ist | `minuten`, `name` |
| `kanal_standby` | ein aktiver Kanal keine Zugangsdaten hat | `erinnerung_tage`, `ignoriere` |
| `kanal_stille` | ein sendebereiter Kanal zu lange schweigt | `stunden` |
| `kennzahl` | ein Wert eine Schwelle reißt | `datei`, `pfad`, `operator`, `schwelle` |
| `datei_geaendert` | sich der Inhalt einer Datei ändert | `datei` |
| `rss` | ein Feed neue Einträge hat | `url`, `stichworte`, `max_treffer` |
| `webhook` | ein `repository_dispatch` eintrifft | `typ` |
| `manuell` | bei jedem Lauf (Sammelregeln) | – |

Alle Trigger sind **lesend** und offline-tauglich: Ohne Netz liefern sie eine
leere Liste, der Lauf bleibt grün.

---

## 6. Aktions-Katalog

| `typ` | Tut | Wichtige `params` |
|---|---|---|
| `social_post` | ein Beitrag auf einem Kanal (mit Gate) | `kanal`, `artikel_slug`, `winkel`, `text`, `mit_bild` |
| `social_welle` | derselbe Anlass auf mehreren Kanälen | `kanaele`, `winkel`, `artikel_slug` |
| `social_autopilot_lauf` | startet den Autopiloten | `modus` (`run`\|`plan`), `kanal`, `limit` |
| `themen_vorschlag` | legt ein Signal zur Kuratierung ab | `titel`, `url`, `quelle`, `notiz` |
| `telegram_nachricht` | Betriebsmeldung nach Telegram | `text` |
| `github_issue` | Issue (mit Duplikat-Erkennung) | `titel`, `text`, `label` |
| `workflow_starten` | startet einen anderen Workflow | `workflow`, `felder` |
| `datei_anhaengen` | Zeile an eine Datei (Journal) | `datei`, `text` |
| `protokoll` | Notiz in der Task-History | `text` |

**Statuswerte:** `ok` (passiert) · `standby` (Kanal ohne Token – kein Fehler) ·
`uebersprungen` (Gate, Probelauf, Sperrfrist) · `fehler` (echtes Problem).

---

## 7. Webhook – auslösen von überall (kostenlos)

```bash
gh api repos/$GITHUB_REPOSITORY/dispatches \
  -f event_type=schaltwerk \
  -F 'client_payload[typ]=sofortpost' \
  -F 'client_payload[kanal]=mastodon' \
  -F 'client_payload[artikel_slug]=2026-09-30-beispiel' \
  -F 'client_payload[winkel]=zahl'
```

Das ersetzt „Webhooks by Zapier“ vollständig. Der Lauf startet binnen Sekunden,
die Nutzlast steht in der Regel als `{webhook.<feld>}` zur Verfügung. Vom Handy
geht das mit der GitHub-App oder jedem HTTP-Client (Token mit `repo`-Scope).

---

## 8. Kanäle scharf schalten (die eigentliche Arbeit)

Code und Regeln sind fertig. Was einen Kanal vom Senden abhält, sind
ausschließlich **fehlende Zugangsdaten**. Schritt für Schritt, mit Klickpfad
und Verifikationslauf: **`docs/RUNBUCH-SOCIAL-SECRETS.md`**.

| Kanal | Kosten | Aufwand | Secret(s) |
|---|---|---|---|
| Mastodon | 0 € | 5 min | `MASTODON_ACCESS_TOKEN` |
| Bluesky | 0 € | 5 min | `BLUESKY_IDENTIFIER`, `BLUESKY_APP_PASSWORD` |
| Telegram | 0 € | 10 min | `TELEGRAM_BOT_TOKEN` + Variable `TELEGRAM_CHAT_ID` |
| Reddit | 0 € | 10 min | `REDDIT_CLIENT_ID/_SECRET/_USERNAME/_PASSWORD` |
| Pinterest | 0 € | 15 min | `PINTEREST_APP_ID/_APP_SECRET/_TOKEN_KEY` → `docs/PINTEREST-TOKEN-RUNBOOK.md` |
| LinkedIn | 0 € | 20 min | `LINKEDIN_ACCESS_TOKEN` (~60 Tage gültig) |
| Facebook | 0 € | 30 min | `FACEBOOK_PAGE_TOKEN` + `FACEBOOK_PAGE_ID` |
| Instagram | 0 € | 30 min | `INSTAGRAM_ACCESS_TOKEN` + `INSTAGRAM_ACCOUNT_ID` |
| Threads | 0 € | 30 min | `THREADS_ACCESS_TOKEN` + `THREADS_USER_ID` |
| X (Twitter) | **kostenpflichtig** | – | bleibt bewusst im Standby |

Nach dem Hinterlegen eines Secrets ist **keine Code-Änderung nötig**. Der
nächste Lauf erkennt den Kanal, das Cockpit zeigt ihn grün.

---

## 9. Sicherheit, Recht, Betriebsruhe

- **Agent Reach bleibt lesend.** Recherche-Signale werden ausschließlich in
  `data/agent_reach/themen_vorschlaege.yaml` abgelegt. Die Übernahme in
  `data/topics.yaml` bzw. `data/aktuelle_entwicklungen.yaml` macht ein Mensch
  nach Quellenprüfung. Der Selbsttest (ST6) und ein Unit-Test verhindern, dass
  eine Regel das umgeht – Titel und Teaser fremder Medien sind urheberrechtlich
  geschützt und keine Textvorlage.
- **Keine Cookies, keine Login-Sessions in CI.** Gepostet wird nur über
  offizielle Plattform-APIs mit eigenen Tokens.
- **Kein Affiliate-Link verlässt den Blog.** Das Gate blockt `/go/`,
  `a.check24.net`, Kurz-URLs; Social verlinkt kanonische Artikel-URLs mit UTM.
- **Fail-safe:** Eine kaputte Regel killt den Lauf nicht; der Fehler steht im
  Protokoll, alle anderen Regeln laufen weiter.
- **Fail-closed:** Die Engine startet nur, wenn ihr Selbsttest besteht.
- **Self-Healing:** Eine gescheiterte Aktionskette wird nicht als erledigt
  markiert und beim nächsten Lauf erneut versucht.
- **Keine Secrets im Repo.** Alles über GitHub-Secrets/Variables.

---

## 10. Störungssuche

| Symptom | Ursache | Abhilfe |
|---|---|---|
| Regel feuert nie | Dedupe-Marke gesetzt | `data/schaltwerk_state.json` → Eintrag unter `ausgeloest` löschen |
| „kein Auslöser“ | Trigger findet nichts | `--dry-run --verbose`, Trigger-Params prüfen |
| „Gate hat abgelehnt“ | Text zu lang/kurz, Link-Hygiene, Duplikat | Meldung nennt den Verstoß; Winkel wechseln |
| Kanal bleibt Standby | Secret fehlt oder heißt anders | `docs/RUNBUCH-SOCIAL-SECRETS.md`, Namen exakt aus `channels.yaml` |
| Workflow rot | mindestens eine Aktion gescheitert | Cockpit „Letzte Vorgänge“ + Lauf-Log |
| Zeit-Trigger verpasst | Actions-Verzug > Toleranz | `toleranz_minuten` erhöhen |

```bash
# Was hat das Schaltwerk zuletzt getan?
tail -20 data/schaltwerk_log.jsonl | python3 -m json.tool --json-lines 2>/dev/null \
  || tail -20 data/schaltwerk_log.jsonl
```

---

## 11. Tests

```bash
python3 scripts/schaltwerk.py --selftest              # 8 Selbsttest-Blöcke, offline
python3 -m unittest scripts.tests.test_schaltwerk     # 31 Unit-Tests
npm run test:schaltwerk                               # beides
```

# 🔌 SCHALTWERK – Zapier-Nachbau für die Social-Media-Vollautomatik

> Premium-Rollout 01.10.2026 · Auftrag Frank Hartung
> Anleitung: `docs/ANLEITUNG-SCHALTWERK.md` · Cockpit: `SCHALTWERK-STATUS.md`

## Auftrag

> „Kannst du mir mit dem blogeigenen Agent Reach und einem Zapier-Nachbau
> meine kompletten Social-Media-Kanäle vollautomatisch automatisieren, sodass
> ich ohne Zapier-API oder irgendwelche Kosten eine vollständige
> Automatisierung meiner Social-Media-Kanäle erhalte?“

## Befund vor dem Umbau

Der Blog war weiter, als die Frage vermuten ließ – und zugleich an einer
anderen Stelle blockiert, als sie annahm.

**Vorhanden und funktionsfähig:**

- `social-autopilot.yml` + `scripts/social_studio.py`: Planen → kanalnativ
  texten → hartes Gate → senden, alle zwei Stunden
- zehn fertige Kanal-Adapter in `scripts/social_channels/` (Mastodon,
  Bluesky, LinkedIn, X, Threads, Facebook, Instagram, Pinterest, Telegram,
  Reddit), ausschließlich Standardbibliothek
- Agent Reach als lesende Recherche-Schicht (`agent_reach_research.py`)
- Pinterest-Kette, Dialog-Autopilot, Shorts-Schmiede, Social-Kalender

**Die drei echten Lücken:**

1. **Keine Verdrahtung.** Es gab Sender, aber keinen Dirigenten: nichts, das
   Blog-Ereignisse, Agent-Reach-Signale, Kennzahlen und Kanäle nach Regeln
   verknüpft. Genau das hätte man sonst bei Zapier gekauft.
2. **Blinde Flecken.** Überarbeitete Bestandsartikel lösten nichts aus.
   Ein Kanal, der still ausfiel, fiel niemandem auf.
3. **Zugangsdaten.** Laut `data/secrets_state.json` ist **nur Mastodon**
   nachweislich live; Pinterest-Token tot, acht Kanäle im Standby. Kein Code
   der Welt postet ohne Token – das ist der eigentliche Engpass.

## Was gebaut wurde

| Baustein | Datei | Zweck |
|---|---|---|
| Engine | `scripts/schaltwerk.py` | Trigger → Filter → Aktion, Dedupe, Throttle, Protokoll, Cockpit, Selbsttest |
| Trigger (12) | `scripts/schaltwerk_triggers.py` | die „Wenn“-Seite, ausschließlich lesend |
| Aktionen (9) | `scripts/schaltwerk_actions.py` | die „Dann“-Seite, fail-safe mit Statusvertrag |
| Regelwerk (9 Regeln) | `data/automationen.yaml` | die „Zaps“, deklarativ und versioniert |
| Taktgeber | `.github/workflows/schaltwerk.yml` | alle 30 min + manuell + `repository_dispatch` |
| Cockpit | `SCHALTWERK-STATUS.md` | Regeln, Kanalzustand, letzte Vorgänge |
| Anleitung | `docs/ANLEITUNG-SCHALTWERK.md` | Bedienung, Kataloge, Störungssuche |
| Tests | `scripts/tests/test_schaltwerk.py` | 31 Unit-Tests + 8 Selbsttest-Blöcke |

### Zapier-Funktionen und ihre Entsprechung

| Zapier | Schaltwerk | Kosten |
|---|---|---|
| Zap | Regel in `data/automationen.yaml` | 0 € |
| Trigger / Action | Provider- bzw. Aktions-Registry | 0 € |
| Filter, Paths | `filter:` mit 18 Operatoren | 0 € |
| Multi-Step-Zap | `aktionen:`-Liste mit Ergebnisdurchreichung | 0 € |
| Deduplication | `dedupe_key` + `data/schaltwerk_state.json` | 0 € |
| Task-History | `data/schaltwerk_log.jsonl` + Cockpit | 0 € |
| Webhooks by Zapier | `repository_dispatch` → `--event` | 0 € |
| Schedule / RSS by Zapier | Trigger `zeitplan`, `intervall`, `rss` | 0 € |
| Task-Limit | existiert nicht (öffentliches Repo) | 0 € |

### Die neun Regeln

| Regel | Auslöser | Wirkung |
|---|---|---|
| `update-welle` | Bestandsartikel überarbeitet | Mastodon/Bluesky/Telegram melden das Update |
| `reach-signale-kuratieren` | Agent-Reach-Brief | Signal → `themen_vorschlaege.yaml` (menschliche Prüfung) |
| `standby-erinnerung` | Kanal ohne Token | Erinnerung mit exaktem Secret-Namen |
| `stiller-kanal` | 48 h kein Post trotz Token | GitHub-Issue mit Prüfpfad |
| `nacht-planung` | 03:40 Uhr | 14-Tage-Plan erneuern |
| `wochenbericht` | Sonntag 19:00 | Lagebericht nach Telegram |
| `kanal-konfig-drift` | `channels.yaml` geändert | Protokolleintrag |
| `sofortpost-webhook` | `repository_dispatch` | Ad-hoc-Post vom Handy |
| `verbraucher-nachrichten` | RSS-Treffer | Themen-Vorschlag zur Kuratierung |

## Leitplanken (geprüft, nicht nur behauptet)

- **Agent Reach bleibt lesend.** Recherche-Signale landen ausschließlich in
  `data/agent_reach/themen_vorschlaege.yaml`. Selbsttest ST6 und
  `test_regelwerk_postet_keine_reach_signale` scheitern, sobald eine Regel
  ein Signal direkt posten will. Begründung: Der Brief ist eine
  Signalsammlung, keine Textvorlage – fremde Titel sind urheberrechtlich
  geschützt, und ungeprüfte Nachrichten gehören nicht unter diese Marke.
- **Kein Doppelpost.** Der Autopilot bleibt Sender für Neues und Evergreen;
  das Schaltwerk füllt nur Lücken, trägt überall `dedupe_key` und schreibt
  Erfolge in denselben State (`data/social/state.yaml`).
- **Kostenregel.** Selbsttest ST5 verbietet, einen kostenpflichtigen Kanal
  (derzeit X) fest in eine Regel zu verdrahten.
- **Standby ≠ Fehler.** Fehlt ein Token, meldet die Aktion `standby`; der Lauf
  bleibt grün, der Zustand steht im Cockpit. Nur echte Fehler setzen Exit 2.
- **Fail-safe und fail-closed.** Kaputte Regel ≠ kaputter Lauf; Engine startet
  nur nach bestandenem Selbsttest; `--dry-run` schreibt nichts.
- **Self-Healing.** Gescheiterte Ketten gelten nicht als erledigt und werden
  beim nächsten Lauf erneut versucht.
- **Pfad-Schutz.** `datei_anhaengen` lehnt Pfade ab, die das Repository
  verlassen.

## Verifikation

```
python3 scripts/schaltwerk.py --selftest        ✅ bestanden (9 Regeln, 12 Trigger, 9 Aktionen)
python3 -m unittest scripts.tests.test_schaltwerk  ✅ 31 Tests, 0 Fehler
python3 scripts/schaltwerk.py --dry-run         ✅ 24 Aktionen simuliert, 0 Schreibzugriffe
python3 scripts/schaltwerk.py --list            ✅ Regelwerk vollständig auflösbar
YAML-Vertrag Workflow + Regelwerk               ✅ geparst
```

## Ehrliche Grenze: was „vollautomatisch“ nicht bedeutet

Die Automatik ist ab sofort vollständig – **die Konten sind es nicht.**
Neun von zehn Kanälen warten auf Zugangsdaten, und die kann nur Frank
anlegen. Das ist keine Code-Aufgabe, sondern eine Viertelstunde pro Kanal:

| Kanal | Kosten | Aufwand | Zustand heute |
|---|---|---|---|
| Mastodon | 0 € | – | ✅ live |
| Bluesky | 0 € | 5 min | ⏸ Standby |
| Telegram | 0 € | 10 min | ⏸ Standby |
| Reddit | 0 € | 10 min | ⏸ Standby |
| Pinterest | 0 € | 15 min | ⏸ Token erneuern (`docs/PINTEREST-TOKEN-RUNBOOK.md`) |
| LinkedIn | 0 € | 20 min | ⏸ Standby |
| Facebook / Instagram / Threads | 0 € | je 30 min (Meta-App) | ⏸ Standby |
| X (Twitter) | **ab ~100 USD/Monat** | – | ⏹ bleibt bewusst aus |

**X ist der einzige Kanal, der sich nicht kostenfrei automatisieren lässt.**
Seine Schreib-API ist seit 2023 kostenpflichtig; kostenlose Umwege laufen
über Login-Cookies, verstoßen gegen die Nutzungsbedingungen und riskieren die
Sperrung des Kontos. Deshalb bleibt der Kanal im Standby, statt eine
Automatik vorzutäuschen, die beim ersten Einsatz das Konto kostet.

## Nächste Schritte für Frank

1. `docs/RUNBUCH-SOCIAL-SECRETS.md` abarbeiten – mit Bluesky und Telegram
   beginnen (zusammen eine Viertelstunde, sofort sichtbarer Effekt).
2. Pinterest-Token einmalig neu autorisieren.
3. *Actions → „Schaltwerk (Automationen)“ → Run workflow → `dry-run`* starten
   und das Cockpit lesen.
4. Erst danach auf `run` stellen – ab dann läuft es ohne Zutun.

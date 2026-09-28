# Anleitung: ZEIT-Niveau-Rechtschreib-Wache

> Dauerhafte Premium-Rechtschreibprüfung für alle Blogartikel.
> Script: `scripts/zeit_rechtschreibung.py` · SSOT: `data/zeit_rechtschreibung.json` ·
> Tests: `scripts/tests/test_zeit_rechtschreibung.py` · Einführung: 28.09.2026

---

## 1. Worum es geht (Auftrag und Faktenlage)

Auftrag (Frank, 28.09.2026): *„Integriere dauerhaft eine professionelle
automatische Rechtschreibprüfung von zeit.de auf Premium-Level einer
Profi-Agentur in meinen Blog.“*

Geprüfte Faktenlage (28.09.2026, siehe Onboarding-Report
`ZEIT-RECHTSCHREIBUNG-PREMIUM-2026-09-28.md`):

1. **zeit.de betreibt keine öffentlich dokumentierte Rechtschreib-API** für
   Dritte. „ZEIT-Niveau“ ist in diesem Repo die vereinbarte Qualitätslatte
   (CLAUDE.md: „sprachlich mindestens auf dem Niveau von ZEIT.de“).
2. Diese Verlags-Qualität ist technisch über die **/v2/check-kompatible
   HTTP-API** greifbar (LanguageTool Enterprise bzw. eigene Instanz) – der
   Branchen-Standard deutscher Agenturen, EU-Server, DSGVO-Ordnung. Die als
   „ZEIT-Checker“ bekannten Online-Prüfer (z. B. rechtschreibpruefung24)
   setzen selbst auf diese Engine; deren „Premium“ ist ausdrücklich ein
   LanguageTool-Angebot.
3. Der **öffentliche Gratis-Endpunkt** (api.languagetool.org) untersagt
   automatisierte Anfragen ausdrücklich („Do not send automated requests“;
   20 Anfragen/Min, 75 KB Text/Min, 20 KB/Anfrage). Er ist hier **kein
   Dauerbetrieb**, sondern nur ein opt-in Manuelmodus — ein
   Sabotage-Guard verweigert ihn im CI mit Exit 2.

Daraus folgt die Provider-Kette (fail-open Richtung Qualität, nie stumm):

| Rang | Modus | Auslöser | Qualität |
|---|---|---|---|
| 1 | **Premium** | `ZR_API_URL` (+`ZR_USERNAME`/`ZR_API_KEY`) **oder** nur Benutzer+Schlüssel | volle Fehler-Abdeckung, höhere Limits, `isPremium`-Funde |
| 2 | **Öffentlich** | Flag `--oeffentlich` (nur manuell!) | volle Basis-Engine, hart gedrosselt |
| 3 | **Offline** | immer verfügbar | deterministischer LT-Nachbau (LT1–LT4, `grammar_check.py`) |

So ist die Prüfung **dauerhaft**: Ohne Zugang, ohne Netz, ohne Schlüssel läuft
die Wache offline und meldet — ein Provider-Ausfall wird als Provider-Meldung
sichtbar, niemals als Schein-Grün.

## 2. Bedienung

```bash
# Redaktioneller Normalfall (Premium, wenn Zugang liegt – sonst offline):
python3 scripts/zeit_rechtschreibung.py

# Eindeutige Fehler sofort heilen (harte Allowlist):
python3 scripts/zeit_rechtschreibung.py --fix

# Expliziter Modus:
python3 scripts/zeit_rechtschreibung.py --offline        # nur lokale Engine
python3 scripts/zeit_rechtschreibung.py --oeffentlich    # Gratis-Endpunkt (nur manuell!)
python3 scripts/zeit_rechtschreibung.py --probe          # Provider-Gesundheit

# Scope:
python3 scripts/zeit_rechtschreibung.py --file content/posts/<slug>/index.md
python3 scripts/zeit_rechtschreibung.py --new-only       # nur Artikel von heute
python3 scripts/zeit_rechtschreibung.py --max-artikel=5

# Meta:
python3 scripts/zeit_rechtschreibung.py --selftest       # Sabotage-Schutz (offline)
python3 scripts/zeit_rechtschreibung.py --strict         # Exit 1 bei offenen Funden
python3 scripts/zeit_rechtschreibung.py --json           # maschinenlesbar
python3 scripts/zeit_rechtschreibung.py --refresh        # Cache ignorieren
```

npm-Kurzformen: `npm run rechtschreibung:zeit[:fix|:offline|:strict|:probe]`,
`npm run test:rechtschreibung`.

**Exit-Codes:** 0 gelaufen · 1 offene Funde (nur `--strict`) ·
2 Selbsttest/Konfiguration rot · 3 Online gefordert, aber nicht verfügbar.

## 3. Premium-Zugang aktivieren (einmalig, ~10 Minuten)

Die Wache ist schlüssellos voll lauffähig (Offline-Modus). Für das
Premium-Niveau einer Profi-Agentur (mehr erkannte Fehlertypen, höhere
Limits, kein Pacing):

1. **Zugang beschaffen** – eine der beiden Varianten:
   - *Enterprise-Account* beim Prüfdienst (kostenpflichtig, Eigentum Frank):
     ergibt `Benutzername` + `API-Schlüssel`, oder
   - *eigene Instanz* (kostenlos selbst gehostet, Docker
     `languagetool/languagetool`): ergibt eine eigene Basis-URL.
2. **Secrets anlegen** (GitHub → Settings → Secrets → Actions):
   - Variante A (Enterprise): `ZR_USERNAME`, `ZR_API_KEY`
   - Variante B (Instanz): `ZR_API_URL` (z. B. `https://lt.example.tld/v2/check`),
     optional dazu Benutzer/Schlüssel.
   - Alias-Namen werden ebenfalls erkannt: `LT_API_URL`, `LT_USERNAME`,
     `LT_API_KEY` (für vorhandene Infrastruktur).
3. **Probe:** `python3 scripts/zeit_rechtschreibung.py --probe`
   → `"modus": "premium"`, `"online": true`.
4. **CI dauerhaft schalten:** `workflow-ready/zeit-rechtschreibung.yml` einmalig
   nach `.github/workflows/zeit-rechtschreibung.yml` kopieren (Admin-Token;
   Agent-Tokens dürfen Workflow-Pfade nicht pushen). Danach läuft die Wache
   **jeden Montag 04:35 UTC** plus manuell.

> **Kosten-Regel (Dauervorgabe):** Auch mit Premium bleibt der Offline-Pfad
> existenziell. `require_online: true` in der Konfiguration bricht den Lauf
> sofort mit Exit 2 (Selbsttest ST8 nagelt das fest).

## 4. Was geprüft wird

- **Fließtext** aller veröffentlichten Artikel (`content/posts/**`, Bundles +
  Legacy; Drafts nur mit `--include-drafts`).
- **`description`** (Frontmatter; Snippet-Text in Google).
- **`title`**: wird **nur gemeldet, nie geschrieben** (Cover-Marken-Lock).
- `tags`/`keywords`/`pin_*` bleiben generell unangetastet.

Der Prüfdienst erhält **nur Fließtext** — Schutzzonen (Code, Links inklusive
Ankertext, Shortcodes, URLs, HTML, Tabellen-Separatoren, Markdown-Marker,
Entities) werden vor dem Versand längentreu maskiert. Offsets und
Zeilennummern der Funde bleiben dadurch punktgenau.

Profil: `language=de-DE`, `motherTongue=de-DE`, `level=picky` (härteste
Regelstufe). Chunking: 9.000 Zeichen (Basis) / 15.000 (Premium),
Absatz- vor Satzgrenzen.

## 5. Schreibvertrag (was die Maschine selbst heilt)

Auto-Fix NUR, wenn **alle** Bedingungen zutreffen (Selbsttest ST5/ST6):

- Issue-Typ `misspelling` oder `typographical`, **und**
- Regel-ID in `auto_fix.regeln` (aktuell: `GERMAN_SPELLER_RULE`,
  `UPPERCASE_SENTENCE_START`, `DOUBLE_PUNCTUATION`, `WHITESPACE_RULE`,
  `COMMA_PARENTHESIS_WHITESPACE`, `GERMAN_WORD_REPEAT_RULE`), **und**
- genau **ein** Ersatz-Vorschlag, kein Markdown/Umbruch/weiche Trennstelle,
  Fund ≤ 60 Zeichen, **und**
- Zone `fluesstext` oder `description`.

Alles andere — Stil, Komma, Semantik, Mehrdeutiges — landet als **Agentur-Fund**
im Report (Besitzer `human`, Severity P2/P3, Channel `redaktion`).

Jeder Schreibvorgang läuft durch `sprachkern.write_verified`
(Link-/Shortcode-/Überschriften-Wächter) plus Kontext-Probe am Offset; der
Selbsttest läuft vor jedem `--fix` (Exit 2 = Sabotage gestoppt, keine Datei
wird angefasst).

## 6. Feintuning im Betrieb

- **Falsche Funde (Marken/Fachbegriffe):** Wort in
  `data/spellcheck_whitelist.txt` eintragen (wird mitbenutzt). Sichtbar im
  Report-Abschnitt „Unterdrückte Funde“.
- **Für dieses Blog irrelevante Regel:** Regel-ID in
  `data/zeit_rechtschreibung.json` unter `ignorieren.regeln` (oder ganze
  `ignorieren.kategorien`) eintragen.
- **Cache/Quota:** `data/zeit_rechtschreibung_cache.json` (versioniert):
  Unveränderte Artikel kosten keine Anfrage. Reset: Datei löschen oder
  `--refresh`.
- **Verlauf:** `data/zeit_rechtschreibung_history.jsonl` (versioniert, Dedupe
  pro Tag) — die Entwicklung der Textqualität über die Zeit.

## 7. Artefakte & Orte

| Artefakt | Versioniert? | Zweck |
|---|---|---|
| `ZEIT-RECHTSCHREIBUNG-REPORT.md` | nein (`/*-REPORT.md`) | lesbarer Premium-Report |
| `.zeit_rechtschreibung_report.json` | nein | Sicht für Automatisierung |
| `data/zeit_rechtschreibung_history.jsonl` | **ja** | Qualitätsverlauf |
| `data/zeit_rechtschreibung_cache.json` | **ja** | Quoten-Schutz/Dedupe |
| `data/zeit_rechtschreibung.json` | **ja** | SSOT-Konfiguration |
| `workflow-ready/zeit-rechtschreibung.yml` | **ja** | einmalig zu aktivierender CI-Lauf |

## 8. Datenschutz & Bedingungen (Pflichtlektüre)

- Im **Premium-/Öffentlich-Modus** verlässt Artikel-Fließtext die eigene
  Infrastruktur Richtung konfiguriertem Endpunkt. Es werden ausschließlich
  bereits veröffentlichte/redaktionelle Texte gesendet — keine
  personenbezogenen Nutzerdaten.
- Der Anbieter verarbeitet auf Servern in der EU (siehe dessen
  Datenschutzerklärung, verlinkt im Onboarding-Report). Bei der Enterprise-
  Variante gelten die dortigen Verarbeitungsbedingungen; bei eigener Instanz
  verbleibt alles im eigenen Haus.
- Der **öffentliche** Endpunkt verlangt: nur POST, keine Automation,
  Quoten-Respekt und auf dessen Bedingungen basierende Nutzung (sichtbarer
  Link-Hinweis, falls Ergebnisse öffentlich genutzt werden). Der
  `--oeffentlich`-Modus ist deshalb hart gedrosselt und im CI verboten.
- Die Zusammenfassung der Vertragslage steht im Onboarding-Report
  `ZEIT-RECHTSCHREIBUNG-PREMIUM-2026-09-28.md`.

## 9. Fehlerbilder

| Symptom | Bedeutung | Handlung |
|---|---|---|
| `🛑 Konfiguration blockiert` (Exit 2) | Dauervorgabe verletzt (`require_online`) | Config korrigieren, s. Abschnitt 3 |
| `Provider-Fehler: HTTP 429` | Rate-Limit (öffentlich) | Modus wechseln / Premium aktivieren / Cache wirken lassen |
| `Artikel nur teilweise online geprüft` | Anfrage-Budget erschöpft | nächster Lauf nutzt Cache; ggf. `max_anfragen_pro_lauf` erhöhen (nur Premium) |
| `🛑 Öffentlicher Gratis-Endpunkt ist im CI VERBOTEN` | ToS-Guard | CI ohne `--oeffentlich` fahren (Default) |
| Selbsttest rot (Exit 2) | Sabotage/Regression | `python3 -m unittest scripts.tests.test_zeit_rechtschreibung -v` |

## 10. Deinstallation

Die Wache ist reine Zusatzschicht: Script, Tests, Config, History/Cache,
Workflow-ready-Datei und Dokumente löschen — keine Inhaltsdatei, kein Workflow
und kein anderes Gate hängt von ihr ab.

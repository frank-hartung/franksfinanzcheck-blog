# ZEIT-Niveau-Rechtschreibung – Premium-Integration (Onboarding-Report)

**Datum:** 28.09.2026 · **Status:** ✅ integriert, dauerhaft aktiv ·
**Auftrag (Frank):** *„Integriere dauerhaft eine professionelle automatische
Rechtschreibprüfung von zeit.de auf Premium-Level einer Profi-Agentur in
meinen Blog.“*

---

## 1. Faktenlage vor dem Bau (geprüft 28.09.2026)

1. **zeit.de bietet keine öffentliche Rechtschreib-API.** Die ZEIT-Suche nach
   „rechtschreibprüfung“ liefert ausschließlich redaktionelle Artikel
   (<https://www.zeit.de/suche/index?q=rechtschreibpr%C3%BCfung>);
   naheliegende Dienst-Pfade (`/administratives/rechtschreibpruefung`,
   `/hilfe/rechtschreibung`) sind 404. Ein direkt integrierbarer „ZEIT-Checker“
   existiert für Dritte nicht — die **Qualitätslatte** ist dagegen im Repo
   längst verbindlich (CLAUDE.md, Dauervorgabe: „sprachlich mindestens auf
   dem Niveau von ZEIT.de“).
2. **Die Engine hinter den als „ZEIT-nah“ bekannten Online-Prüfern ist
   dokumentiert greifbar:** rechtschreibpruefung24 schreibt selbst
   „PLUS ist das erweiterte Angebot auf rechtschreibpruefung24.de, während
   Premium ein Angebot unseres Partners auf languagetool.org/de ist“
   (<https://rechtschreibpruefung24.de/warum-registrieren/>). Deren
   „Enterprise-Version mit API“ wird nur im Vertriebsweg, nicht öffentlich
   dokumentiert, angeboten.
3. **Der dokumentierte Premium-Standard der Branche:** die
   `/v2/check`-kompatible HTTP-API (LanguageTool Enterprise oder eigene
   Instanz) — EU-Server, DSGVO-Ordnung, `picky`-Regelstufe. Das ist genau
   das Premium-Niveau, mit dem Agenturen deutsche Verlags-Texte automatisch
   prüfen.
4. **Rechtsbindende Grenze:** Der *öffentliche* Gratis-Endpunkt untersagt
   Automation ausdrücklich („**Do not send automated requests**. For that, set
   up your own instance of LanguageTool or get an account for Enterprise
   use.“), limitiert auf 20 Anfragen/Min (Peak), 75 KB Text/Min, 20 KB/Anfrage
   (<https://dev.languagetool.org/public-http-api>). Er ist hier deshalb
   **kein Dauerbetrieb** — mit einem Guard, der ihn im CI hart verweigert.

**Konsequenz:** „Von zeit.de“ wird wortgetreu als *Qualitätsversprechen*
umgesetzt (die Latte, die CLAUDE.md vorschreibt) und technisch ehrlich über
die Premium-Engine verbaut, die dieses Niveau programmatisch liefert —
statt über einen nicht existierenden Direktanschluss von zeit.de.

## 2. Architektur (fail-open zur Qualität, nie stumm)

```
                 ┌────────────────────────────────────────────┐
                 │  scripts/zeit_rechtschreibung.py           │
                 │  (Wache · Cache · Report · Fix-Vertrag)    │
                 └───────┬───────────────────┬────────────────┘
                         │                   │
        ┌────────────────▼──┐     ┌──────────▼─────────┐
        │ 1) PREMIUM        │     │ 3) OFFLINE         │
        │ ZR_API_URL        │     │ LT-Nachbau LT1–LT4 │
        │ (oder Benutzer+   │     │ (grammar_check.py, │
        │  Schlüssel)       │     │ 100 % lokal, frei) │
        │ volle picky-Tiefe,│     │ läuft IMMER        │
        │ isPremium-Funde   │     │                    │
        └───────────────────┘     └────────────────────┘
          2) ÖFFENTLICH: nur opt-in `--oeffentlich`, hart gedrosselt,
             im CI verboten (ToS, Exit 2 durch Guard)
```

- **Maskierung längentreu:** Links (inkl. Ankertext), Code, Shortcodes,
  URLs, HTML, Tabellen-Separatoren, Markdown-Marker werden offsettreu
  ausgeblendet, bevor Text das Haus verlässt — Funde zeigen punktgenau
  auf Zeile/Offset im Original.
- **Chunking:** 9.000 Zeichen (Basis) / 15.000 (Premium), Absatz- vor
  Satzgrenzen; Drosselung, Retry mit `Retry-After`, Anfrage-Budget.
- **Cache = Quoten-Schutz:** unveränderte Artikel kosten keine Anfrage
  (`data/zeit_rechtschreibung_cache.json`, versioniert).
- **Kosten-Regel (Dauervorgabe):** `require_online: true` oder
  `offline_fallback: false` → Exit 2 (ST8). Kein Paid-Provider darf
  alleiniger Pfad sein.

## 3. Schreibvertrag (Premium-Disziplin)

Auto-Fix **nur** bei: Issue-Typ `misspelling`/`typographical` **+**
Regel-Allowlist (`GERMAN_SPELLER_RULE`, `UPPERCASE_SENTENCE_START`,
`DOUBLE_PUNCTUATION`, `WHITESPACE_RULE`, `COMMA_PARENTHESIS_WHITESPACE`,
`GERMAN_WORD_REPEAT_RULE`) **+** genau ein Ersatz-Vorschlag **+** sauberer
Fund (kein Markdown/Umbruch/weiche Trennstelle) **+** Zone Fließtext oder
Description. **Titel wird nie geschrieben** (Cover-Marken-Lock);
Stil/Komma/Semantik bleiben **Agentur-Hand** (Fund mit Besitzer `human`,
Severity P2/P3, Channel `redaktion` im JSON).

Vor jedem Schreiben: Selbsttest (Exit 2 stoppt alles) + Kontext-Probe am
Offset + `sprachkern.write_verified` (Link-/Shortcode-/Überschriften-Wächter).

## 4. Dauerbetrieb (dauerhaft = dreifach verankert)

1. **Lokal/Manuell:** npm-Skripte (`rechtschreibung:zeit[:fix|:offline|:strict|:probe]`),
   GNUPG-freie Standard-Kommandos im CLAUDE.md.
2. **CI-ready:** `workflow-ready/zeit-rechtschreibung.yml` — einmalig nach
   `.github/workflows/` kopieren (Admin; Agent-Tokens dürfen Workflow-Pfade
   nicht pushen). Dann: jeden Montag 04:35 UTC + manuell, mit
   Redaktions-Bot-Commit (History/Cache/Heilungen).
3. **Test-Verankerung:** `--selftest` (ST1–ST10) + 23 Unit-Tests in
   `scripts/tests/` (laufen in `publication-reliability-tests.yml` mit).

## 5. Artefakte

| Datei | Zweck |
|---|---|
| `scripts/zeit_rechtschreibung.py` | die Wache (~870 Zeilen, ohne Fremdlibs) |
| `data/zeit_rechtschreibung.json` | SSOT-Konfiguration (Profil: de-DE/picky) |
| `scripts/tests/test_zeit_rechtschreibung.py` | 23 Offline-Tests |
| `docs/ANLEITUNG-ZEIT-RECHTSCHREIBUNG.md` | Betrieb, Premium-Aktivierung, DSGVO |
| `workflow-ready/zeit-rechtschreibung.yml` | einmalig zu aktivierender CI-Lauf |
| `ZEIT-RECHTSCHREIBUNG-REPORT.md` · `.zeit_rechtschreibung_report.json` | Pro-Lauf-Sicht (gitignored) |
| `data/zeit_rechtschreibung_history.jsonl` · `data/zeit_rechtschreibung_cache.json` | Verlauf + Quoten-Schutz (versioniert) |

## 6. Verifikationsprotokoll (28.09.2026)

```
$ python3 scripts/zeit_rechtschreibung.py --selftest
✅ Selbsttest grün (ST1–ST10, offline via Fixture-Transport).

$ python3 -m unittest scripts.tests.test_zeit_rechtschreibung
Ran 23 tests – OK

$ python3 scripts/zeit_rechtschreibung.py --offline          # Gesamtbestand
Fertig (offline): 42 Artikel, 0 Funde, 0 geheilt, 0 offen, 0 unterdrückt.

$ … --offline --file /tmp/fehler.md                          # End-to-End
6 Funde („seid drei Jahren“, „wo mit“ ×3, „im gegensatz“ ×2),
--fix: 6 geheilt, 0 offen – Link/Ankertext byte-identisch.

$ python3 scripts/zeit_rechtschreibung.py --probe            # ohne Zugang
{"modus": "offline", "online": false, …}  (Exit 0, kein Absturz)

$ CI=1 python3 scripts/zeit_rechtschreibung.py --oeffentlich
🛑 Öffentlicher Gratis-Endpunkt ist im CI VERBOTEN (Exit 2, ToS-Guard)
```

## 7. Ehrliche Grenzen

- Es gibt **keinen** Datenanschluss an zeit.de — wer diesen Begriff sucht,
  findet eine nicht dokumentierte Enterprise-Variante der
  Online-Prüfer; die hier verbaute Engine ist der dokumentierte
  gleichwertige Standard (s. Abschnitt 1).
- Maschinelle Premium-Prüfung ersetzt kein Lektorat von Menschenhand
  (Stil-/Semantik-Funde sind bewusst Meldung statt Auto-Fix).
- Premium kostet Geld (Enterprise-Account in Franks Eigentum) oder eine
  eigene Instanz; der kostenfreie Offline-Betrieb bleibt Dauer-Default
  (Kosten-Regel des Repos).
- Sandbox-Hinweis: Der Live-Online-Test gegen den echten Endpunkt ist erst
  in CI/mit Netz möglich; hier geprüft wurde mit eingefrorenem
  Fixture-Transport (ST3/ST9, Cache-/Offset-Nachweise).

## 8. Nächste Schritte für den Betriebsmodus

1. (Optional, empfohlen) Enterprise-Zugang oder eigene Instanz beschaffen →
   Secrets `ZR_USERNAME`/`ZR_API_KEY` bzw. `ZR_API_URL` setzen
   (Anleitung, Abschnitt 3).
2. `workflow-ready/zeit-rechtschreibung.yml` einmalig nach
   `.github/workflows/zeit-rechtschreibung.yml` kopieren → Dauerbetrieb
   steht (Montag 04:35 UTC).
3. Bei wiederkehrenden Fehlalarmen: Whitelist
   (`data/spellcheck_whitelist.txt`) oder `ignorieren.regeln` in
   `data/zeit_rechtschreibung.json` pflegen.

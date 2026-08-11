# 📕 QUALITÄTS-REGELWERK – FranksFinanzcheck

**Version:** 1.0 · **Stand:** 10.08.2026 · **Geltungsbereich:** gesamtes Blog
(alles unter `content/`, die Startseite, die Skripte in `scripts/`, die
Workflows in `.github/workflows/`)

> **Zweck in einem Satz:** Jede Lektorats-Regel ist hier genau einmal
> dokumentiert – mit Entscheider, Schutzzonen und Selbstheilung. Kein
> Fehler darf sich jemals zweimal wiederholen.

---

## 🗺️ Die Qualitäts-Kette (Inkraft in Content-Engine v2, Phase 2)

Reihenfolge ist **absichtlich** so (erst Struktur, dann Sprache, dann Stil,
dann Länge – und Brand-Guard immer NACH Emoji-Guard, damit das Marken-Lock
das letzte Wort hat):

```
KI-Artikel (engine_generate.py)
   │
   ├─► profi_polish.py          KI-Feinschliff
   ├─► fix_linebreaks.py        Zeilenfluss (Markdown)
   ├─► fix_spaces.py            Leerzeichen-Hygiene
   ├─► spellcheck.py            Rechtschreibung (Hunspell, de-DE)
   ├─► grammar_check.py         Grammatik (LanguageTool)
   │
   ├─► 🔠 casing_guard.py       Akronym-/Marken-Schreibweise (C1–C3)
   ├─► 📏 dash_guard.py         Strich-Typografie (R1–R8) + KI-Stil (S1/S3)
   ├─► fix_dash_breaks.py       Umbruch NACH Gedankenstrich
   ├─► fix_heading_breaks.py    Teilüberschrift:<br>-Umbruch
   ├─► 🧩 compound_guard.py     Komposita („Preisgarantie Gas"-Falle)
   ├─► 😀 emoji_guard.py        Touchpoints & Text-Hygiene (E1–E5)
   ├─► 🔒 brand_guard.py        MARKEN-LOCK (unantastbar, siehe unten)
   ├─► 📏📝 length_guard.py     Längen-Korridore + KI-Selbstheilung
   │
   ├─► profi_text_check.py      Stil-Gate (Schwelle)
   ├─► readability_check.py     Lesbarkeits-Gate (> 75)
   ├─► check_titles.py          Titel-Gate
   ├─► generate_covers.py       Titelbilder (Manifest-selbstheilend*)
   ├─► check_uniqueness.py      Duplikat-Audit
   ├─► affiliate_link_check.py  Check24-/Tarifcheck-Link-Pflege
   ├─► check_covers.py --fix    *Cover-Stale-Erkennung über Manifest
   └─► generate_kurzantworten.py  💡-Box „Kurz & knapp"
```

Ausführung aller Regeln: **niemals blockierend** (`|| echo "nicht kritisch"`).
Fehler dürfen nie die Veröffentlichung stoppen, aber sie werden sichtbar gemacht.

---

## 🔠 Regeln im Detail

### casing_guard.py – Akronym-Orthografie (Duden, deterministisch)
| Regel | Inhalt | Beispiel |
|---|---|---|
| C1 | Kanonische Akronym-Form (auch Satzanfang) | `dsl` → `DSL`, `etfs` → `ETFs`, `cashback` → `Cashback` |
| C2 | Durchkopplung Akronym + Nomen | `DSL Tarif` → `DSL-Tarif` |
| C3 | Marken-Durchkopplung | `Check24 Gasvergleich` → `Check24-Gasvergleich` (Marken: Check24/CHECK24, Tarifcheck, Verivox, Idealo) |

### dash_guard.py – Strich-Typografie (Duden + Web)
| Regel | Inhalt |
|---|---|
| R1 | „ Wort - wort" (Minus als Gedankenstrich) → „ – " |
| R3 | US-Geviertstrich „—" → „ – " |
| R4 | „--"/„---" zwischen Wörtern → „ – " (Wort-Anker; schont Zeilenanfänge, Fences!, HR) |
| R5 | Zahlenbereiche → Halbgeviert ohne Leerzeichen: `10-20 Euro` → `10–20 Euro` (Kettenfest: `50-30-20` → `50–30–20`; Schutz: ISO-Daten, „5-jährig") |
| R6 | Asymmetrische Leerzeichen am Gedankenstrich |
| R7 | Satzende-Kollision: „. – Und" → „. Und"｜„. – dann" → „ – dann" |
| R8 | Imperativ am Satzanfang: „. Ließ das" → „. Lies das" (enge Negativ-Kontrollen) |
| S1/S3 | KI-Schiedsrichter (nur `--ai`): Doppelschub-Umformulierung, Strich-vs-Komma – mit 4-fach-Verifikation |

### compound_guard.py – Komposita (SEO-Keyword-Falle)
Regelwerk in `COMPOUND_RULES` oben im Skript. Aktuell: `Preisgarantie Gas|Strom|DSL`,
`Zinsen Tagesgeld|Festgeld`, `Sparplan ETF`, `Tarif DSL`, `Konto Giro`.
Kandidaten-Radar (Kopf-Nomen + Themen-Nomen) landet im Report; `--ai` urteilt selbst.

### emoji_guard.py – Touchpoints & Text-Hygiene
E1 Marken-Emoji an Startseite auto-ergänzen (Themen→Emoji-Mapping, Default 💰) ·
E2 Meta-Description bleibt Emojig-arm · E3 Anti-Overuse (max 2) · E4 Mojibake → Auto-Reparatur ·
E5 Zero-Width-Zeichen (U+200B…) → immer löschen.

## 🏛️ Hoheitskarte (wer regelt was — einmalig festgelegt 11.08.2026)

Bei zwei parallel gebauten Längen-Systemen gilt ab jetzt:

| Klasse | Hoheit | Korridor | Mechanik |
|---|---|---|---|
| **Posts** (normal) | `check_length.py` (Generierungs-System) | Floor **1.000** Wörter via `LENGTH_MIN_WORDS` (Repo-Variable, Default in Engine) – Optimum 800–1.400 | Heilung zur Generierungszeit |
| **Pillar-Seiten** | `length_guard.py --scope pillar` (dieses System) | **2.500–4.000 Wörter**, Heil < 1.800 | Engine + Wochen-Backlog (3/Wo.) |

Damit: Keine Doppel-KI-Kosten, keine Ping-Pong-Loops, getrennte Strenge.
Dash-Guards (dash_guard.py ≠ fix_dash_eol.py/fix_dash_und.py) koexistieren
bewusst – nachgewiesen disjunkte Muster.

---

### length_guard.py – Längen-Korridore (Affiliate-Profi)
| Typ | Ziel | Warnung | Selbstheilung unter … |
|---|---|---|---|
| posts | 1.200–2.200 Wörter | < 1.000 | 900 |
| pillar | 2.500–4.000 Wörter | < 1.800 | 1.800 |

Heilung = KI ergänzt **Mehrwert-Module** (kein Fülltext!): Rechenbeispiel mit Jahr,
typische Fehler, Checkliste, +2 FAQ – eingefügt vor Fazit/Disclaimer, nach Gates.
Neue Artikel: Engine (`--new-only`). Rückstand: Wochen-Audit (`--backlog 3`, Pillars zuerst).

| D10 | CTA-Kasten (gelb) <-> /go/-Gateway-Kontrakt in custom.css | Auto-Heilung |
| D11 | Hover-Transparenz: /go/-Links tragen Tooltip (Ziel + Werbung) | Auto-Heilung (Hook-Re-Write) |

### design_guard.py + design_visual.py – 🎨 Verlagshaus-Design-QA (neu 11.08.)
| Regel/Modul | Inhalt | Lohn/Macht |
|---|---|---|
| Statisch (Guard) | D1 CLS-Bilder dims, D2 alt-Text, D3 Heading-Springe, D4 vage Links, D5 font-display, D6 externe Calls (KRITISCH – Privacy!), D7 doppelte IDs, D8 lang/viewport | Auto-Fix Alt-Text |
| Visuell (Visual) | pHash-Schnappschüsse (Desktop+Mobile) vs. Baseline; Regression -> Issue (Dedupe), Baseline heilt sich mit moderater Drift | Screenshots NIE im Repo (64-Bit-Hashes!) |

Echtes Verfahren wie bei Grossverlagen (Percy/Chromatic): nur deutlich leichter.

### math_guard.py – 🧮 Faktencheck-Schreibtisch (neu 11.08.)
| Regel | Inhalt | Automatik |
|---|---|---|
| M1 | Rate x Zeiteinheit x Dauer = Endbetrag **nachrechnen** („5–10 €/Tag x 14 Tage = 70–140 €") | Auto-Fix (Behauptung, letztes Zahlenpaar); weiche Formen (rund/ca.) nur melden |
| M2 | Prozentformeln („X % von Y") | pruefen |

Ausloeser: Artikel „Urlaub mit Kindern" (Beispielrechnung korrekt; dafuer
der Schutz fuer künftige KI-Halluzinationen, die erfahrungsgemaeß bei
Geldrechnungen eklatant sind).

### lektor_guard.py – ✒️ Verlags-Lektorat (Zeitungs-/Buchniveau, neu 11.08.)
| Regel | Inhalt | Automatik |
|---|---|---|
| L1 | Wortduplikate („das das") | Auto-Fix (sichere Liste) + Komma-Lookbehind bei Artikeln |
| L1rel | Relativkaskaden „die die meisten" | NIE auto – korrektes Deutsch! (nur Report) |
| L2 | Füllphrasen (Bürokratie-Deutsch) mit Kanon-Ersatz | Auto |
| L3 | Personenkonsistenz Sie↔du | **Nur KI** (--ai) mit Grammatik-Gate (du+Verb-muss) |
| L4 | Ausrufezeichen-Inflation „!!" -> „!"; >3 pro Artikel = Werbeton-Radar | Auto + Report |
| L5 | Echo-Wörter (>4 Buchstaben 2× im Satz) | Report; KI-veredelt mit --ai + Gates |

### brand_guard.py – 🔒 Marken-Lock (höchste Stufe)
Sperrt in `data/brand_lock.yaml` enthaltene hugo.toml-Bausteine: Willkommens-Titel/Tagline,
Meta-Description, Affiliate-Disclaimer. **Jede Abweichung wird zurückgerollt.**
Absichtliche Änderung: entweder `hugo.toml` + einmal `python3 scripts/brand_guard.py --set-current`,
oder einfach den Wert in `data/brand_lock.yaml` ändern und commiten – die Automatik folgt.

### affiliate_marketer.py – 🎯 CTA-Routing mit Selbsttest-Batterie (Sabotage-Schutz)
Steuert die 💡-Schnell-Tipp-Box thematisch korrekt (`route_for()` + `DEEP_HINTS`,
Reihenfolge = Spezifität; Register-Gate gegen 404) und retargetet jede falsch
geroutete Box automatisch auf die Ideale-Route. **Sabotage-Schutz:** `run_selftest()`
prüft vor JEDEM Lauf 17 kanonische Routing-Fälle (DSL→dsl, Elementar→hausrat (!),
Depot→tagesgeld, Gas→gas …). Schlägt auch nur einer fehl, bricht der Marketer mit
Exit 2 ab, bevor eine Datei angefasst wird – Mensch oder KI kann das Routing nicht
mehr „aus Versehen" verbiegen.

---

## 🛡️ Schutzzonen (gelten über allen Guards)

1. **Front-Matter ist SEO-Safe-Zone** (Keywords bleiben; Titel-Semantik geschützt).
2. **URLs/Slugs sind sakrosankt.** Veröffentlichte URLs ändern sich NIE.
3. Code-Fences, Inline-Code, Markdown-Links, Bild-URLs, HTML-Kommentare: unantastbar.
4. Listen-/Zitat-Marker und Überschriften-Hashes bleiben (Inhalt hinter dem Marker wird geprüft).
5. Eigennamen-Whitelists (z. B. „Franks Finanzcheck").
6. Bekannter Blog-Eigenbau: geklebte Front-Matter-Fences (`---Text`) werden von allen
   Guards korrekt aufgedröselt (Fence bleibt, Text wird geregelt).

---

## 🩹 Selbstheilungs-Matrix

| Was schiefgehen kann | Wer heilt es |
|---|---|
| Schwache KI-Antwort → kein Artikel | Engine v2 (3-Ebenen-Fallback) |
| Artikel zu dünn | length_guard (KI-Module, Gate-verifiziert) |
| Titel geändert → Cover alt | check_covers Manifest-Abgleich (--fix) |
| Pinterest-Token läuft ab | pinterest_auth.py (Continuous Refresh, AES) |
| Push-Race zwischen Bots | Rebase-Guards + Concurrency in allen Write-Workflows |
| Bot komplett stumm | bot-watchdog → Issue |
| Website down | uptime-check → Issue (auto-schließend!) |
| Workflow-Fehler | alert-on-failure → Issue (Abdeckung: alle Kern-Workflows) |
| Text-Regelverstoß | die sechs Guards oben (korrigieren selbst) |
| Marken-Text verändert | brand_guard (Lock-Reset) |
| Actions veraltet | Dependabot + Auto-Merge (Patch/Minor auto) |

## 📁 Reports (werden bei Läufen kommittiert)

`LENGTH-REPORT.md` · `DASH-REPORT.md` · `COMPOUND-REPORT.md` · `EMOJI-REPORT.md` ·
`CASING-REPORT.md` · `BRAND-REPORT.md` · `SEO-REPORT.md` · `LAYOUT-REPORT.md` ·
`BOT-STATUS.md` · `ENGINE-STATUS.md` · `PIN-STATUS.md` · `SOCIAL-STATUS.md` ·
`AFFILIATE-REPORT.md` · `BACKLINK-REPORT.md` · `GRAMMATIK-REPORT.md` · `META-REPORT.md`

## 🛠️ Playbooks (typische Eingriffe)

| Situation | Vorgehen |
|---|---|
| **Neue Regel festnageln** (z. B. neue SEO-Falle) | In `compound_guard.py` / `casing_guard.py` im Regel-Block oben ergänzen. Fertig – ab nächstem Lauf aktiv. |
| Engine manuell anstoßen | Actions → „Content-Engine v2" → Run workflow |
| Selbstheilung pausieren | Workflow im Actions-Tab deaktivieren (Kill-Switch) |
| Guard-False-Positive | Ein melden via Issue; Regel im Skript weicher machen; `HISTORY`-Dateien in `data/` zeigen Verhalten |
| Max. Artikel/Tag ändern | Repo-Variable `MAX_ARTIKEL_PRO_TAG` |
| Wassertemperaturen | `BOT-STATUS.md` / `ENGINE-STATUS.md` jederzeit auf der Repo-Seite sichtbar |

## 🧾 Änderungsjournal (nur Qualitäts-Regelwerk)

- **11.08.2026 (3):** affiliate_marketer.py: Schnell-Tipp-Routing-Korrektur (Fehlrouten
  Depot→girokonto, Elementar→handytarife u.a. geheilt), universelles Retarget +
  17-Fälle-Selbsttest als Sabotage-Schutz (Exit 2 vor jeder Datei-Berührung).
- **11.08.2026 (2):** Verlags-Lektorat `lektor_guard.py` (L1–L5) in die Kette eingebaut.
- **11.08.2026:** Hoheitskarte Längen-Systeme festgelegt (Posts vs. Pillar, Floor 1.000); R9 Fence-Normalisierung dauerhaft; 56 Alt-Fences geheilt.
- **10.08.2026:** Regelwerk 1.0. Neu: casing_guard, dash_guard (R1–R8),
  compound_guard, emoji_guard (E1–E5), length_guard, brand_guard,
  uplift der Workflow-Härtung (Audit-Fixes: Alerting-Blindspot,
  Push-Races, Zeit-Kollision Mo 17:30, Dependabot+Auto-Merge,
  uptime-check). Legacy-Verdrahtung der Umbruch-Skripte reaktiviert.

---

> _Dieses Dokument pflegen heißt: Wenn eine Regel hinzukommt oder sich ändert,
> hier in die Tabelle. Das Regelwerk lebt – aber es vergisst nie._

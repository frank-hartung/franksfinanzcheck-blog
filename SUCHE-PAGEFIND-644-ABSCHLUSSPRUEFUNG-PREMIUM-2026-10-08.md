# Suche (Pagefind) und Redaktionsressourcen #644 – Abschlussprüfung

**Datum:** 08.10.2026 · **Branch:** `arena/2ab994f3-franksfinanzcheck-blog` (Basis: `main` = `f85ce6d`)
**Auftrag:** „#644 bitte dauerhaft auf Premium-Level einer Profi-Agentur beheben.“
**Bezug:** #644 (gemergt, 09:31) · Nachgeschichte: #647 (10:41), #651 (12:50, Vorgangsbericht
`SUCHE-PAGEFIND-DAUERHEILUNG-PREMIUM-2026-10-08.md`), #655 (14:13). Kein „Closes“: #644 ist
bereits geschlossen; dieser Vorgang dokumentiert die Abnahme und die letzten Dauerfixes.

## Auftragslage

#644 brachte vier Zusagen:

1. eine datenschutzfreundliche Pagefind-Suche mit Index-Schritt im Deploy,
2. den 15-Minuten-Fixkosten-Check als Newsletter-Anreiz ohne E-Mail-Gate,
3. redaktionelle Standards für KI-Alt-Texte und GEO,
4. die dynamische Partner-Tabelle unangetastet lassen (Quelle: geprüftes Partnerregister).

## Abnahme: gemessen, nicht vermutet

Alle vier Zusagen stehen auf `main` und wurden in dieser Arbeitskopie vollständig nachgeprüft.
Der Suchpfad ist end-to-end grün: Hugo-Build → Pagefind-Index → Wache → jsdom → echter
Chromium. Die Redaktionsressourcen sind erreichbar, verlinkt und im Suchindex auffindbar
(`/newsletter-checkliste/` liegt als Fragment im Index, 70 Fragmente für 70 indexierbare
Seiten). Die Partner-Tabelle ist unverändert; `offenlegung_gate.py` meldet O1–O7 erfüllt.

| Prüfung | Ergebnis |
|---|---|
| `npm ci --ignore-scripts` | rc 0, Lockfile konsistent (`pagefind` exakt `1.5.2`) |
| `npm run build` (Hugo 0.164.0 Extended) | 109 HTML-Seiten · 70 indexierbar · 70 im Index · 39 bewusst ausgeschlossen – Wache grün |
| `npm run test:suche` | jsdom 16/16 · Wache-Selbsttest 14 Proben · Python-Verträge 29 OK |
| `npx playwright test e2e/suche.spec.mjs` | 10/10 im echten Chromium (Fallback `@sparticuz/chromium`) |
| `npx playwright test` (Desktop + Mobil) | 108/108 |
| `python3 -m unittest discover -s scripts/tests` | **2331 Tests OK**, 14 übersprungen (PyYAML nachinstalliert; ohne `yaml` sind 75 Importfehler Umgebungs-, keine Code-Funde) |
| `layout_audit.py` · `fm_boundary_guard.py` · `offenlegung_gate.py` · `ki_transportweg.py` | rc 0 |
| `index_hygiene_gate.py` · `h1_wache.py` · `robustheits_gate.py --public public --strict` | rc 0 |
| `integrity_guard.py --gate` | rc 0, 47 versiegelte Kerndateien unverändert |

## Der letzte Befund – und seine Dauerheilung

Der einzige Widerspruch im Bestand: das Runbook der Suche führte die Datenschutzfrage als
**offen**, während die Datenschutzerklärung den Abschnitt „Website-Suche (lokale Suche)“
bereits führt (`content/datenschutz/index.md`, Abschnitt 2). Zwei Dokumente, zwei Wahrheiten –
genau die Sorte Flanke, die #644 nach dem Merge schon einmal lahmgelegt hat.

**Behoben:** `docs/ANLEITUNG-SUCHE-PAGEFIND.md` nennt jetzt den tatsächlichen
Datenschutz-Abschnitt und erklärt die Frage entschieden (08.10.2026). Der Offen-Satz im
Tagesprotokoll `SUCHE-PAGEFIND-DAUERHEILUNG-PREMIUM-2026-10-08.md` bleibt stehen – Berichte
sind Protokolle, keine lebenden Dokumente – und ist im Runbook ausdrücklich als überholt
gekennzeichnet.

## Neue Verträge – damit „dauerhaft“ eine Eigenschaft ist und kein Versprechen

Sieben Tests halten die Zusagen von #644 an ihren Oberflächen fest (jeder Vertrag dort, wo
das Versprechen lebt). Vier Sabotageproben am echten Bestand bestätigen: Jeder Vertrag wird
bei Verletzung rot, nach `git restore` wieder grün.

| Vertrag | Modul | schützt |
|---|---|---|
| `DatenschutzVersprechen.test_suchseite_haelt_ihr_versprechen` | `test_suche_pagefind` | Suchseite nennt weiter: kein Suchdienst, keine Suchhistorie, kein Cookie |
| `DatenschutzVersprechen.test_datenschutz_beschreibt_die_lokale_suche` | `test_suche_pagefind` | Abschnitt „Website-Suche (lokale Suche)“ mit Browser/Indexdateien-Versprechen |
| `DatenschutzVersprechen.test_runbook_fuehrt_die_datenschutzfrage_nicht_mehr_offen` | `test_suche_pagefind` | Runbook zeigt auf die Datenschutzerklärung, keine „Offen“-Flanke mehr |
| `Checkliste.test_checkliste_ist_ohne_gate` | `test_newsletter_site` | „Kein E-Mail-Gate“, „ohne Anmeldung“, Weg zum Newsletter |
| `Checkliste.test_checkliste_bleibt_auffindbar` | `test_newsletter_site` | kein Draft, kein `robotsNoIndex`, nicht aus der Sitemap |
| `Checkliste.test_newsletter_seite_verlinkt_die_checkliste` | `test_newsletter_site` | Anreiz bleibt von der Anmeldeseite erreichbar |
| `Repo.test_redaktionsstandard_bleibt_mit_der_anleitung_verwaehlt` | `test_alt_text_vorschlaege` | `ALT-TEXT-REDAKTIONSSTANDARD.md` bleibt mit `ANLEITUNG-ALT-TEXTE.md` verdrahtet |
| `Doku.test_redaktionsprotokoll_bleibt_mit_der_anleitung_verwaehlt` | `test_geo_protokoll` | `GEO-REDAKTIONSPROTOKOLL.md` bleibt mit `ANLEITUNG-GEO-PROTOKOLL.md` verdrahtet |

Sabotagebeweis (Auswahl): „Offen“-Satz zurück ins Runbook → 1 Failure; „Kein E-Mail-Gate“
aus der Checkliste → 1 Failure; Checklisten-Link von `/newsletter/` entfernt → 1 Failure;
Standard aus der Alt-Text-Anleitung getarnt → 1 Failure.

## Entscheidungen

- **Bestand wird nicht umgebaut.** Suchmaske, Trefferregel, Index-Wache, Deploy-Schritt und
  die e2e-Suite standen bereits auf Premium-Niveau (#651/#655). Die Abnahme bestätigt sie;
  geändert wurde nur, wo zwei Dokumente sich widersprachen.
- **Berichte bleiben Protokolle.** `SUCHE-PAGEFIND-DAUERHEILUNG-PREMIUM-2026-10-08.md` wurde
  nicht nachträglich geschönt; das Runbook nennt den Überholungsstand.
- **Versiegelte Dateien unangetastet.** `hugo.toml` (Menügewichte inzwischen sauber 1–10),
  `head.html` (der Kommentar zu `layouts/search/single.html` ist zwischenzeitig ebenfalls
  bereinigt) und `robots.txt` blieben unberührt – `integrity_guard.py --gate` grün.
- **Deckel-Alt-Texte bleiben Konvention.** `brand-franksfinanzcheck.jpg` trägt auf der
  Newsletter-Seite und auf der Checkliste jeweils seitenbezogene Alt-Texte; `check_covers.py`
  meldet 0 Probleme. Eine Umstellung auf dekorativ ist eine redaktionelle Entscheidung
  (Standardsatz aus `ALT-TEXT-REDAKTIONSSTANDARD.md`), kein Defekt.
- **Datenschutztext ist Tatsachenbeschreibung, keine Rechtsberatung.** Die Formulierung
  beschreibt, was technisch passiert (Begriffe im Browser, Indexdateien von dieser Website,
  Zugriffsdaten wie in Abschnitt 2).

## Offene Punkte (bewusst außerhalb dieses Vorgangs)

1. **Mobile: Schnellzugriff auf die Suche.** Der Menüpunkt liegt im horizontal scrollbaren
   Menü weit rechts; erreichbar über den Footer. Eine Suchschaltfläche im Kopf ist eine
   Designentscheidung und gehört laut `CLAUDE.md` in eine Design-Variante mit Messung und
   Freigabe, nicht in die Basis.
2. **Gemini-Liveaufruf für Alt-Text-Vorschläge.** Transportweg und Payload sind vertraglich
   geprüft (#655); der erste echte Lauf bleibt ein manueller `--max 1`-Probe-Workflow.
3. **Keine weiteren Befunde.** Die Tabelle oben nennt jeden geprüften Lauf; alle sind grün.

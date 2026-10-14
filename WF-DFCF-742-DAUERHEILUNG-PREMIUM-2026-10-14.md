# Wöchentliche SEO-Optimierung · WF-DFCF · #742 – Dauerhafte Heilung

**Datum:** 14.10.2026

**Auslöser:** [Lauf `38572026372`](https://github.com/frank-hartung/franksfinanzcheck-blog/actions/runs/38572026372) der „Wöchentlichen SEO-Optimierung“ schlug im Schritt
**„Affiliate-Link-Check (Deep-Links – VOLLAUTOMATISCH)“** fehl; gemeldet als [Issue #742](https://github.com/frank-hartung/franksfinanzcheck-blog/issues/742).

**Urteil:** Kein API-Key- oder transienter Partnerfehler, sondern ein reproduzierbarer
Fehlalarm im lokalen Deep-Link-Prüfer.

## 1. Reproduzierte Ursache

Im Lauf war der Artikel
`2026-10-07-handyvertrag-kuendigen-raus-aus-der-kostenfalle-verlaengerung` bereits
inhaltlich korrekt auf `/go/handytarife/` ausgerichtet. Sein Frontmatter ordnet ihn
jedoch dem breiten Pillar `internet-dsl` zu. Weil dem alten `SLUG_DEEP`-Mapping ein
einzelner Eintrag für diesen Handyvertrag fehlte, griff `PILLAR_DEEP` und verlangte
den DSL-Deep-Link `dsl-anbieterwechsel&cat=4`.

Die Fehlerklasse ließ sich auf dem Laufstand des SEO-Schritts reproduzieren
(Checkout-Snapshot `a3df6381`): **62 Seiten geprüft, ein Fehler** – der korrekte
Handytarif-Link wurde als fehlender DSL-Link gemeldet. Der zentrale
`affiliate_intent_contract` ordnet „Handyvertrag“ bereits eindeutig der Route
`handytarife` zu; der veraltete SEO-Prüfer nutzte diese Wahrheit nicht.

## 2. Dauerhafte Korrektur

- `affiliate_link_check.py` fragt die zentrale Intent-Reihe für die eindeutige
  Produktklasse **Handytarife** ab, bevor der grobe Internet-Pillar-Fallback greift.
  Das erwartete Ziel stammt aus dem registrierten Gateway; eine neue, manuell
  duplizierte Deep-URL ist nicht nötig.
- Die automatische Ableitung bleibt bewusst eng: Sie nutzt nur Slug und Titel,
  nicht beliebige Wörter im Artikeltext. Allgemeine Themen und bewusstes
  Cross-Selling bleiben kuratiert – so erzeugt das neue Routing keine
  Fehlklassifikation von Reise- oder Sparthemen.
- Selbsttest und Regressionen sind in `npm run test:affiliate-links` gebündelt und
  laufen jetzt **vor** dem harten Affiliate-Gate im Wochenworkflow. Die Tests
  verriegeln den konkreten Handyvertrag-Fall, den Pillar-Fallback sowie den Schutz
  davor, dass CTA- oder Cross-Selling-Text sein eigenes Ziel legitimiert.

## 3. Redaktionelle Ausnahme im aktuellen Bestand

Seit dem fehlgeschlagenen Lauf wurde der DNS-Artikel
`2026-09-04-digitaler-turbo-warum-der-dns-hack-dein-netz-beschleunigt` zu einem
neutralen Messleitfaden über DNS-Antwortzeiten überarbeitet. Er enthält bewusst
keinen Tarifvergleich; ein DSL-Werbe-CTA wäre sachfremd. Die alte Regel „jede Seite
muss einen Affiliate-Link haben“ hätte deshalb auch nach der Reparatur den nächsten
Wochenlauf blockiert.

Der Artikel ist nun mit `affiliate_exempt: true` und einer konkreten Begründung
gekennzeichnet. Die Ausnahme unterdrückt **nur** den Befund für einen fehlenden Link:
Ist ein Affiliate-Link vorhanden, prüft der Checker Route, Deep-Link und Partner-ID
weiterhin. Eine fehlende Begründung bleibt fail-closed ein Fehler. Die Regel ist in
`docs/ANLEITUNG-CHECK24-LINKS.md` dokumentiert.

## 4. Verifikation

| Prüfung | Ergebnis |
|---|---|
| Alter SEO-Checkout `a3df6381` mit korrigiertem Prüfer | **62 geprüft · 0 Probleme · 0 Änderungen** |
| Aktueller Bestand mit `affiliate_link_check.py --fix --json` | **64 geprüft · 0 Probleme · 0 Änderungen** |
| `npm run test:affiliate-links` | **5 Selbsttest-Verträge + 11 Unit-Tests grün** |
| `affiliate_intent_contract.py --selftest` | 20 Ziele, 17 Verbots-Paare, 25 Themen-Muster grün |
| `affiliate_intent_guard.py --selftest` + Regressionen | grün; 29 Unit-Tests bestanden |
| `test_workflow_yaml` | 7 Tests bestanden |
| `py_compile` und `git diff --check` | grün |

**Nicht blockierender Vorbestand:** Die 29 Tests der Intent-Wache bestehen, geben aber
`ResourceWarning`s aus `scripts/bestand_gate.py:180` (Dateien werden nicht geschlossen)
aus. Diese Datei ist nicht Teil der #742-Änderung.

Ein Hugo-Build konnte in dieser Arbeitsumgebung nicht ausgeführt werden, da das
Hugo-Binary hier nicht installiert ist. Die Änderung am DNS-Artikel betrifft nur
zusätzliches Frontmatter; die Markdown-/YAML-Vertrags- und Affiliate-Regressionen
laufen lokal.

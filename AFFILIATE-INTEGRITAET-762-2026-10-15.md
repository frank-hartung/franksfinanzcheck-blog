# Affiliate-Integritäts-Wache #762 – Ursachenbehebung

Stand: 15.10.2026 · Umsetzung und Verifikation auf dem Arbeitsbranch.

## Ursache und reproduzierter Befund

Die tägliche Integritäts-Wache meldete bei 58 geprüften Live-Artikeln genau
einen Render-Fund: Der DNS-Messleitfaden
`2026-09-04-digitaler-turbo-warum-der-dns-hack-dein-netz-beschleunigt`
enthielt keinen Affiliate-Link im gebauten HTML.

Der Artikel ist seit der Reparatur #742 ausdrücklich mit `affiliate_exempt: true`
und einer konkreten Begründung versehen: Ein Tarifvergleich wäre im neutralen
DNS-Messtest sachfremd. Der Wochenprüfer berücksichtigte diese Ausnahme bereits,
die tägliche Wache dagegen nicht. Der rote Befund war deshalb keine defekte
CTA-Box, sondern ein Widerspruch zwischen zwei Prüfregeln. Das Einfügen eines
Werbe-Links hätte den Fehlalarm verdeckt, nicht die Ursache behoben.

## Dauerhafte Korrektur

- `scripts/affiliate_exemption.py` enthält den gemeinsamen Ausnahmevertrag.
  Wochenprüfer und tägliche Wache verwenden dieselbe YAML-Auswertung.
- Die tägliche Wache erlässt ausschließlich die Mindestanforderung eines
  Affiliate-Links. Markdown-Struktur, vorhandene Links, Registerzugehörigkeit,
  `rel=sponsored`, Gateway-Weiterleitung und Existenz der gebauten Seite bleiben
  geprüft. Die Ausnahme ist kein Überspringen des Artikels.
- Fehlerhafte Ausnahme-Metadaten blockieren auch den Markdown-/Dateiheilungspfad.
  Eine erfolgreiche CTA-Heilung darf einen verbleibenden Metadatenfehler nicht
  aus der offenen Restmenge entfernen.
- Report und Zustand nennen ausgenommene Artikel mit Begründung. Die Tabelle
  kennzeichnet `0 → 0` ausdrücklich als redaktionelle Ausnahme, nicht als
  gerenderten Affiliate-Link.
- Der bestehende Detektor-Selbsttest enthält die Regression. Die tägliche
  Workflow-Stufe führt zusätzlich die neuen Ausnahme- und bisherigen
  Link-Checker-Unit-Tests aus. Lokal: `npm run test:affiliate-links`.

Kein Artikel, Linkziel, Partnerregister oder Layout wurde verändert. Die
bestehenden nicht blockierenden Cross-Selling- und Dichtehinweise bleiben
unverändert sichtbar; sie werden nicht zur Bereinigung dieses Issues unterdrückt.

## Verifikation

| Prüfung | Ergebnis |
|---|---|
| Reproduktion vor Änderung, echter Hugo-Build | Exit 1; genau der DNS-Artikel als Render-Fund |
| Hugo 0.164.0 Extended, `hugo --minify` | erfolgreich |
| Integritäts-Wache nach Änderung, Heilmodus | **58 Artikel, 20 Registry-Routen, 0 Struktur-/Render-Funde, 1 begründete Ausnahme, Exit 0** |
| Wochenprüfer `affiliate_link_check.py --json` | **64 Seiten, 0 Probleme, 0 Änderungen** |
| Intent-Wache `affiliate_intent_guard.py --json` | Exit 0; 0 blockierende Funde; bestehende 11 Hinweise bleiben bestehen |
| `npm run test:affiliate-links` | 5 Selbsttest-Verträge und 27 Unit-Tests bestanden, davon 16 neue Tests |
| Integritäts-Detektor-Selbsttest | bestanden, einschließlich #762 |
| State-/Workflow-/Herzschlag-Regressionen | 34 Unit-Tests bestanden |
| Intent-/Workflow-YAML-Regressionen | 36 Unit-Tests bestanden |
| Intent-Kontrakt und Intent-Selbsttest | bestanden |
| `git diff --check` | bestanden |

Die neuen Tests prüfen insbesondere ungültige/fehlende Begründungen, gültige
Ausnahmen, verlorene Markdown-Links im HTML, fehlendes `rel=sponsored`, rohe
Partnerlinks, unbekannte Gateway-Routen, falsche Weiterleitungen, fehlende
HTML-Seiten, fehlende Build-Artefakte, kaputte CTA-Syntax und Teilheilung mit
verbleibendem Metadatenfehler. Ein wiederholter grüner Lauf bleibt inhaltlich
unverändert und schreibt keine Werbe-CTAs in den Artikel.

Bekannter, nicht blockierender Vorbestand: Die Intent-Tests melden
`ResourceWarning`s aus `scripts/bestand_gate.py:180`; alle Tests bestehen.
Diese andere Fehlerklasse wurde hier nicht verändert.

## Produktionsstatus

`AFFILIATE-INTEGRITY-REPORT.md` und `.affiliate_integrity_state.json` enthalten
den tatsächlich gemessenen lokalen grünen Nachweis, keinen manuell gesetzten
Erfolgsstatus. Es wurde nicht nach `main` übernommen oder produktiv ausgerollt.
Issue #762 bleibt bis zur Übernahme und dem regulären automatischen Nachweis offen.

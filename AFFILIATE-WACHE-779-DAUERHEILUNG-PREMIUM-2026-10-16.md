# Affiliate-Wachen #779 – Dauerheilung auf Profi-Niveau

**Stand:** 16.10.2026  
**Scope:** `affiliate_integrity_gate.py` · Render-Beweis AI4/AI5 · Affiliate-Ausnahme #762

## Ergebnis

Der Werkzeugfehler aus dem täglichen Affiliate-Lauf ist lokal reproduziert und an der Ursache behoben. Die Fail-closed-Sperre selbst war korrekt: Der fehlgeschlagene Detektor-Selbsttest stoppte Intent-Wache, Hugo-Build und Render-Beweis, statt ungeprüft ein grünes Ergebnis zu erzeugen.

## Ursache

Im Lauf `38875169146` scheiterte der Detektor-Selbsttest; die nachfolgenden Beweisstufen wurden übersprungen. Der reproduzierte Selbsttest lieferte zwei konkrete Vertragsverletzungen für eine gültige, begründete redaktionelle Ausnahme:

1. `verify_article_render()` wertete die Ausnahme zunächst korrekt aus `article["fm"]` aus. Im Mindestlink-Zweig setzte der Code den Status jedoch zurück und las die Content-Datei ein zweites Mal über einen anderen Adapter.
2. Das Prüf-Fixture ist absichtlich dateiunabhängig. Der erneute Dateizugriff schlug fehl; ein breites `except Exception` verwandelte den Fehler still in „nicht ausgenommen“. Dadurch meldete der Detektor fälschlich einen fehlenden Affiliate-Link.
3. Selbst bei gültiger Ausnahme fehlte der geforderte sichtbare Hinweis in `result["notes"]`.

Das war kein Hugo- oder Netzwerkfehler, sondern ein Drift zwischen zwei Prüfpfaden für denselben Ausnahme-Vertrag. Der Selbsttest hat diesen Drift korrekt fail-closed offengelegt.

## Dauerhafte Korrektur

- Der Mindestlink-Beweis verwendet jetzt ausschließlich das bereits geprüfte `article["fm"]` und das Ergebnis des gemeinsamen Ausnahme-Vertrags. Es gibt keine zweite Dateilesung, keinen konkurrierenden Adapter und kein stilles Herabstufen einer gültigen Ausnahme.
- Eine gültige Ausnahme erscheint als nicht blockierender, begründeter Prüfhinweis.
- Die Ausnahme hebt ausschließlich die Pflicht zu mindestens einem Affiliate-Link auf. Vorhandene Markdown-/HTML-Links, Registry-Ziele, Gateway-Weiterleitungen, `rel="sponsored"` und fehlerhafte Metadaten bleiben weiterhin vollständig prüfpflichtig.
- Zwei gezielte Regressionstests frieren den dateiunabhängigen Beweis und das Fail-closed-Verhalten einer ungültigen Ausnahme samt fehlendem Link ein.

## Verifikation

In einer isolierten Python-Umgebung mit dem in CI verwendeten PyYAML 6.0.3:

| Prüfung | Ergebnis |
|---|---:|
| `python3 scripts/affiliate_integrity_gate.py --selftest` | bestanden |
| `python3 scripts/affiliate_link_check.py --selftest` | 5 Verträge bestanden |
| Affiliate-Ausnahme- und Link-Checker-Tests | 29 Tests bestanden |
| Affiliate-State-, Workflow-Vertrags- und Frische-Tests | 34 Tests bestanden |
| Intent-Kontrakt | bestanden: 20 Ziele, 17 Nie-Paare, 25 Themenmuster |
| Intent-Wachen-Selbsttest | bestanden |
| `git diff --check` | bestanden |

Ein Hugo-Build wurde für diese reine Beweis-/Selbsttestkorrektur nicht als Produktionsnachweis ausgegeben. Der reguläre tägliche Workflow muss nach Übernahme erneut laufen, um den Render-Beweis auf dem gebauten Live-Bestand zu bestätigen.

## Produktionsgrenze

Die Änderung betrifft ausschließlich Prüfcode, Regressionstests und diesen Bericht. Es wurden keine Artikel, Partnerziele oder Affiliate-CTAs geändert. Der Patch ist in diesem Arbeitsstand noch nicht nach `main` übernommen oder produktiv ausgerollt; bis zum erfolgreichen regulären Lauf bleibt der bestehende Fail-closed-Schutz maßgeblich.

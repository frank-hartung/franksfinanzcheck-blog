# Governance #888 – Abschlussprüfung der redaktionellen und technischen Befunde

**Prüfdatum:** 29.10.2026 (UTC)  
**Issue-Stand:** 26.10.2026 · Fingerabdruck `65df3aa59195`  
**Ergebnis für die beiden ursprünglichen Befunde:** behoben / aktuell nicht reproduzierbar  
**Wichtig:** Das ist kein pauschales „alles grün“ für den gesamten Governance-Lauf. Der aktuelle Lesbarkeitslauf weist einen anderen, später hinzugekommenen Entwurf aus (siehe „Abgrenzung“).

## 1. Core Web Vitals: Bilder ohne Größenvorgabe

### Dauerhafte Abhilfe

Der Hugo-Markdown-Bild-Renderhook `layouts/_markup/render-image.html` versieht lokale Bilder, wenn keine Autor:innenmaße vorgegeben sind, mit intrinsischer `width`- und `height`-Angabe. Dadurch kann der Browser den benötigten Platz vor dem Bilddownload reservieren. Vorhandene Maße bleiben erhalten. Für Bildressourcen ohne Hugo-Bildmetadaten wird der SVG-Fall über `width`/`height` beziehungsweise `viewBox` behandelt; nicht unterstützte Ressourcen werden nicht blind abgefragt.

Der Vertragstest `scripts/tests/test_render_image_template.py` schützt insbesondere gegen fehlerhafte Go-Formatierung von Ganzzahlen, fehlende SVG-Metadaten und das Überschreiben expliziter Autor:innenmaße. Zusätzlich prüft die Governance-Wache den tatsächlich gebauten HTML-Baum – nicht nur den Template-Quelltext.

### Verifikation

- Hugo Extended **0.168.0**: Build erfolgreich.
- `python3 scripts/cwv_guard.py --public public --strict-build`: **GREEN**, Exit 0.
- Gemessener Build: **400 HTML-Dateien**, **2.290 Bilder**, **0 Bilder ohne Größenvorgabe** (`img_nosize: 0`).
- `python3 -m unittest scripts.tests.test_render_image_template`: **3 Tests bestanden**.
- Der verifizierte Lauf ist in `data/cwv_manifest.json` und `data/cwv_history.jsonl` dokumentiert.

Der Wächter misst hier deterministisch den gebauten Seitenbaum. Das ist kein Ersatz für echte Feldmessungen der Core Web Vitals in CrUX oder RUM.

## 2. Lesbarkeit: Gastarif-Entwurf unter Publish-Schwelle

### Ergebnis

Der im Issue genannte Entwurf `content/posts/2026-10-26-gastarife-vergleichen-vor-dem-herbst/index.md` erreicht im aktuellen Messlauf **Flesch-Amstad 73,8**. Die Publish-Schwelle für neue Inhalte beträgt **60**. Der Befund „51,5 < 60“ aus dem Issue reproduziert sich daher nicht.

Der Beitrag bleibt ausdrücklich `draft: true`; die redaktionelle Prüfung steht laut Frontmatter noch aus. Die Messung ist keine inhaltliche Freigabe und veröffentlicht den Text nicht.

### Dauerhafte Kontrolle

Der Premium-Governance-Workflow führt `scripts/readability_check.py --gate-bestand` regelmäßig aus. Das Gate prüft Live-Texte getrennt von Entwürfen und weist Entwürfe unter der Publikationsschwelle weiter aus. Neue Beiträge werden zusätzlich über `--new-only` mit der strengeren Publish-Schwelle geprüft. Damit wird ein späterer Rückfall nicht durch die einmalige Score-Verbesserung verdeckt.

### Verifikation

- `python3 scripts/readability_check.py --file content/posts/2026-10-26-gastarife-vergleichen-vor-dem-herbst/index.md`: **Flesch 73,8**.
- `python3 scripts/readability_check.py --selftest`: **bestanden**.
- Die gesamte aktuelle Lesbarkeitsprüfung wurde ebenfalls ausgeführt.

## Abgrenzung: separater aktueller Entwurfsbefund

Beim vollständigen Bestandslauf am 29.10.2026 wurde zusätzlich der später angelegte Entwurf `content/posts/2026-10-28-dsl-und-internet-flat-guenstig-sichern/index.md` mit **Flesch 56,0** unter der Publish-Schwelle 60 gemeldet. Er war nicht Teil der beiden Befunde im Fingerabdruck von Issue #888. Der Live-Bestand besteht den Floor: **70 Live-Artikel, Ø Flesch 65,2, kein Live-Artikel unter 55**. Der neue Entwurfsbefund bleibt eine eigenständige redaktionelle Aufgabe; deshalb wird hier nicht behauptet, dass der komplette aktuelle Governance-Lauf ohne jeden Befund ist.

## Reproduzierbare Prüfsequenz

```sh
python3 -m unittest scripts.tests.test_render_image_template
python3 scripts/readability_check.py --selftest
python3 scripts/readability_check.py --file content/posts/2026-10-26-gastarife-vergleichen-vor-dem-herbst/index.md
hugo --minify --destination public
python3 scripts/cwv_guard.py --public public --strict-build
python3 scripts/readability_check.py --gate-bestand --report /tmp/LESBARKEIT-REPORT.md
```

**Fazit:** Beide im Issue #888 konkret aufgeführten Befunde sind im aktuellen Stand durch dauerhafte Prüfungen abgesichert und in der erneuten Messung nicht mehr vorhanden. Der getrennte neue DSL-Entwurfsbefund ist transparent ausgewiesen und darf nicht mit einer erfolgreichen Freigabe des Gesamtbestands verwechselt werden.

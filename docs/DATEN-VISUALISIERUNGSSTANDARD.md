# Daten- und Visualisierungsstandard

**Version 1.0 · beschlossen am 28.09.2026 · verantwortlich: Frank Hartung**

Dieser Standard gilt für alle redaktionellen Diagramme und öffentlichen Datensätze von FranksFinanzcheck. Er ergänzt die Recherche- und Quellenregeln in `CLAUDE.md` und auf `/methodik/`.

## 1. Grundsätze

1. **Aussage vor Dekoration.** Ein Diagramm braucht eine konkrete Leserfrage. Ist eine Tabelle klarer, wird eine Tabelle verwendet.
2. **Daten vor Darstellung.** Jede Grafik wird ausschließlich aus einer versionierten Datei unter `data/datasets/` erzeugt. Werte werden nicht im Template oder Artikel dupliziert.
3. **Primärquelle vor Sekundärquelle.** Externe Tatsachen werden möglichst durch Preisblatt, Gesetz, Behörde oder Originaldatensatz belegt. Modellrechnungen nennen ihre Annahmen.
4. **Keine Scheingenauigkeit.** Beobachtung, Modellrechnung und Prognose werden sichtbar unterschieden. Prognosen dürfen nicht als Messwerte erscheinen.
5. **Reproduzierbarkeit.** Einheit, Stand, Quellen, Methodenversion und Rechenweg müssen nachvollziehbar sein.
6. **Menschliche Freigabe.** Agent Reach und KI dürfen Quellen finden und Auffälligkeiten melden, sind aber weder Quelle noch alleinige Freigabeinstanz.
7. **Barrierefreiheit.** Erkenntnis und Werte müssen ohne Farbe, Maus und JavaScript zugänglich sein.
8. **Korrekturtransparenz.** Sachliche Änderungen werden im Datensatz-Changelog dokumentiert; Methodensprünge erhöhen die Methodenversion.

## 2. Pflichtfelder je Datensatz

Das maschinengeprüfte Schema steht in `data/datasets/schema.yaml`. Pflicht sind insbesondere:

- stabile `id` und `schema_version`,
- Titel, Kurzbeschreibung und verantwortliche Person,
- `status`: `beobachtung`, `modellrechnung` oder `prognose`,
- Diagrammtyp `bar` oder `line`,
- Einheit und Achsenbeschriftungen,
- ISO-Datenstand und Aktualisierungstakt,
- mindestens eine Quelle mit Titel, URL, Herausgeber und Abrufdatum,
- Methodikzusammenfassung, Version und URL,
- Changelog und Lizenz,
- mindestens zwei Datenpunkte mit Label und numerischem Wert.

## 3. Visuelle Regeln

- Balkendiagramme beginnen bei null. Verkürzte Achsen sind in Phase 1 nicht zulässig.
- Zeitreihen stehen in chronologischer Reihenfolge.
- 3D, dekorative Kreisdiagramme und Animation ohne Informationsgewinn sind verboten.
- Farbe ist nie der einzige Bedeutungsträger; Werte und Beschriftungen bleiben sichtbar.
- Titel formulieren Thema oder belegbare Aussage, keine Übertreibung.
- Unsicherheit und Annahmen stehen direkt an der Grafik, nicht nur in einer entfernten Fußnote.
- `status: prognose` erzeugt einen sichtbaren Warnhinweis.

## 4. Zugänglichkeit und progressive Verbesserung

Der Shortcode `chart` erzeugt beim Hugo-Build:

- ein responsives, statisches SVG als JavaScript-freies Fallback,
- fokussierbare Balken beziehungsweise Datenpunkte mit zugänglichen Namen,
- sichtbaren Fokus und Tastatur-Hinweise,
- eine immer verfügbare HTML-Datentabelle,
- Quellen-, Datenstands- und Methodikangaben.

Das SVG ist die schnelle Übersicht; die Tabelle ist die vollständige, kopierbare Darstellung. Die Kernaussage darf nicht nur in einem Tooltip stehen.

## 5. Redaktioneller Ablauf

1. Leserfrage und erwartete Aussage notieren.
2. Quellen erheben; Abhängigkeiten und Gegenbelege prüfen.
3. Datensatz nach Schema anlegen.
4. Berechnung unabhängig gegenprüfen.
5. `python3 scripts/visual_data_gate.py` ausführen.
6. Grafik in Desktop-, Mobil-, Dark-Mode- und Tastaturansicht prüfen.
7. Fachlich und redaktionell freigeben.
8. Bei Änderungen Datenstand und Changelog aktualisieren.

## 6. Abnahmecheck

Eine Visualisierung darf nur live gehen, wenn:

- das Daten-Gate grün ist,
- Quelle, Einheit, Datenstand und Methodik sichtbar sind,
- SVG und Tabelle dieselben Werte zeigen,
- sie bei 320 Pixel Breite keinen horizontalen Seitenüberlauf erzeugt,
- alle Datenmarken per Tab erreichbar und benannt sind,
- JavaScript-Ausfall keinen Informationsverlust verursacht,
- eine zweite Prüfung der Berechnung dokumentiert ist.

## 7. Phase-1-Grenzen

Phase 1 unterstützt bewusst nur Balken- und Zeitreihendiagramme mit einer Serie und nichtnegativen Werten. Komplexe Mehrfachachsen, Karten und Prognosebänder benötigen vor Einführung eine Schema- und Qualitätsstandard-Erweiterung.

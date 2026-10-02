# Redaktionelle YMYL-Freigabe

## Zweck

Baufinanzierung, Altersvorsorge, Kredite und Versicherungen werden als
**Risikoklasse hoch** behandelt. Sprachqualität, KI-Recherche,
`faktencheck:` und ein guter `quality_score` reichen nicht zur Veröffentlichung.
Das harte Publish-Gate verlangt eine dokumentierte, fassungsgebundene Freigabe.

## Rollen

- **Autor:** verantwortet Text und Einordnung.
- **Prüfer:** prüft Aussagen, Zahlen und Rechenwege. Zulässige Typen:
  - `fachpruefer`: benannte fachkundige Person;
  - `redaktion-mit-externer-belegkette`: redaktionelle Prüfung anhand der im
    Artikel sichtbaren Primär- und Verbraucherquellen.
- **Automatik:** sammelt Quellen, prüft Form und sperrt unvollständige Artikel.
  Sie darf weder einen Prüfer erfinden noch selbst `freigegeben` setzen.

## Frontmatter-Vertrag

```yaml
author: "Frank Hartung"
faktencheck: "2026-10-02" # Recherchezeitpunkt, noch keine Fachfreigabe
quellen:
  - id: "Q1"
    titel: "Verbraucherinformation zur Baufinanzierung"
    url: "https://www.verbraucherzentrale.de/..."
    herausgeber: "Verbraucherzentrale"
    datum: "2026-09-24"
  - id: "Q2"
    titel: "Rechtsgrundlage"
    url: "https://www.gesetze-im-internet.de/..."
    herausgeber: "Bundesministerium der Justiz"
    datum: "2026-09-01"
redaktionelle_pruefung:
  risikoklasse: "hoch"
  status: "freigegeben"
  pruefer:
    name: "Vorname Nachname oder Redaktion"
    rolle: "Konkrete fachliche Rolle oder Faktenprüfung anhand externer Quellen"
    typ: "redaktion-mit-externer-belegkette"
  pruefdatum: "2026-10-02"
  naechste_pruefung: "2026-11-16"
  aenderungsgrund: "Erstprüfung vor Veröffentlichung; Zahlen und Modellrechnung überarbeitet"
  gepruefte_aussagen:
    - textanker: "Exakter, eindeutiger Ausschnitt der Aussage im Artikel"
      pruefung: "Wie wurde die Aussage eingeordnet oder begrenzt?"
      quellen: ["Q1", "Q2"]
  gepruefte_zahlen:
    - aussage: "Bezeichnung der im Artikel verwendeten Zahl"
      wert: "Wert und Einheit oder ausdrücklich freie Modellannahme"
      fundstelle: "Exakter Textausschnitt mit Wert und Einheit im Artikel"
      pruefung: "Was wurde abgeglichen oder nachgerechnet?"
      konsistenzpruefung: "Wo wurden Tabelle, Fließtext und Ergebnis gegengeprüft?"
      rechenweg: "Bei Modellrechnungen: Formel und Rechenschritte"
      quellen: ["Q1", "Q2"]
  inhalt_sha256: "wird ausschließlich durch --seal gesetzt"
```

## Freigabe in fünf Schritten

1. **Text prüfen:** Pauschalaussagen zu Bankverhalten, Eigenkapital,
   Zinsbindung, Vorsorge oder Versicherungsschutz differenzieren. Alte
   Jahresstände entfernen. Modellfälle als Modellfälle benennen.
2. **Belege und Aussagen prüfen:** Mindestens zwei erlaubte externe Quellen mit
   eindeutigen IDs eintragen; mindestens eine Quelle muss amtlich oder eine
   etablierte Verbraucher-/Fachinstanz sein. Affiliate-Partner sind nie
   Belegquelle. Jede Kernaussage erhält in `gepruefte_aussagen` einen exakten
   Textanker, ein Prüfergebnis und Quellen-IDs. Pauschale Sätze zu Zinsbindung,
   Eigenkapital oder Bankverhalten ohne diese Zuordnung blockieren das Gate.
3. **Zahlenprotokoll schreiben:** Jede Euro-/Prozentangabe, jede
   entscheidungsrelevante Zahl und jede Modellannahme mit exakter Fundstelle,
   Wert, Prüfergebnis, Konsistenzprüfung, Quellen-IDs und gegebenenfalls
   Rechenweg dokumentieren. Doppelte Aussagen mit widersprüchlichen Werten
   blockieren die Freigabe.
4. **Freigabedaten setzen:** Prüfer, Rolle, Typ, Datum, Änderungsgrund und
   nächsten Review innerhalb von höchstens 45 Tagen eintragen. Erst danach
   `status: freigegeben` setzen.
5. **Fassung versiegeln:**

   ```bash
   python3 scripts/editorial_review_gate.py --seal \
     --file content/posts/<slug>/index.md
   ```

   Das Kommando verweigert das Siegel bei Lücken. Erfolgreiche Siegel werden
   append-only in `data/editorial_review_history.jsonl` protokolliert.

## Was die Freigabe automatisch bricht

- Änderung an Titel, Beschreibung, Kurzantwort, Autor, Quellen, Prüfprotokoll oder Body;
- fehlender oder überfälliger Review-Termin;
- weniger als zwei Quellen, unbekannte Quellen-ID oder nicht erlaubte Domain;
- Kernaussage oder Pauschalbehauptung ohne exakten Textanker und Quellen-IDs;
- Euro-/Prozentangabe ohne protokollierte Fundstelle und Konsistenzprüfung;
- widersprüchliche Werte zur selben geprüften Aussage;
- Rechenbeispiel ohne dokumentierten Rechenweg;
- ein veralteter Artikelstand wie „Stand 2024“ in einem aktuellen Beitrag;
- Affiliate-CTA vor 600 Wörtern und zwei H2-Abschnitten fachlicher Grundlage;
- Herabstufung einer automatisch erkannten hohen Risikoklasse.

## Befehle

```bash
# Regelwerk
python3 scripts/editorial_review_gate.py --selftest

# Einzelartikel
python3 scripts/editorial_review_gate.py --file content/posts/<slug>/index.md

# Bestandsqueue und Report
python3 scripts/editorial_review_gate.py --all --report

# Strikter Queue-Lauf (Exit 1 bei offenen Hochrisiko-Freigaben)
python3 scripts/editorial_review_gate.py --all --strict

# Hartes Deploy-Gate für alle tatsächlich veröffentlichten Artikel
python3 scripts/editorial_review_gate.py --published --strict
```

Der werktägliche Workflow `.github/workflows/redaktionelle-ymyl-pruefung.yml`
pflegt genau ein GitHub-Arbeitsticket statt Einzelwarnungen zu streuen. Neue
Publikationskandidaten werden unabhängig davon im `publish_gate.py` sofort
fail-closed gehalten; Hochrisiko-Entwürfe werden nicht gelöscht, sondern als
manueller Review-Hold erhalten.

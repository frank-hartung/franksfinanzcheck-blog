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

## Belegkette im Netz prüfen (seit 24.10.2026, #826)

Das Gate prüft den **Text**, nicht das **Netz**. Ein Siegel ist auch dann noch
formal gültig, wenn die zitierte Seite nicht mehr existiert oder unter
derselben Adresse inzwischen etwas anderes steht. Beides ist am 24.10.2026
real aufgetreten: fünf Verbraucherzentrale-Adressen antworteten nach einer
Seiten-Migration mit 404, und eine GDV-Adresse zeigte weiterhin eine Seite –
aber mit den Zahlen des Folgejahres.

Vor jedem Siegel deshalb:

```bash
# Prüft alle zitierten URLs der Hochrisiko-Artikel (nur lesend)
python3 scripts/belegketten_wache.py --nur-hochrisiko --report
```

Zustände: `ok` (HTTP 200 unter genau der zitierten Adresse), `umgeleitet`
(200, aber andere Adresse – Inhalt gegen das Zitat prüfen), `tot`
(definitives 4xx) und `unklar` (Netzfehler, 5xx, 403, 429). `unklar` blockiert
im Diagnosemodus nicht, `tot` schon. Bei `tot` oder `umgeleitet` gilt:
**nicht** einfach die URL austauschen, sondern die neue Seite abrufen und
prüfen, ob sie die zitierte Aussage noch trägt; erst dann URL, Titel und
Abrufdatum im Frontmatter korrigieren und neu versiegeln.

Der werktägliche Workflow fährt dieselbe Wache mit `--strict
--require-complete` und schließt das Arbeits-Ticket erst, wenn **beide**
Prüfungen grün sind: Gate-Queue leer **und** kein einziger Abrufbefund – also
weder eine tote noch eine unklare oder umgeleitete Quelle.

## Wenn `gesetze-im-internet.de` den Runner blockiert (seit 30.10.2026, repariert 03.11.2026, #1024)

GitHub-Actions-Runner werden von `www.gesetze-im-internet.de` häufig mit einem
TCP-Timeout abgewiesen. Ein Netzfehler ist **kein** Beleg dafür, dass eine Norm
verschwunden ist; er darf aber auch nicht als `ok` durchgehen. Für kanonische
GII-Adressen prüft die Wache deshalb ersatzweise den täglich synchronisierten
Bundesrechts-Spiegel `Gesetze-fuer-KI/bundesrecht`:

1. Der Direktabruf läuft immer zuerst. Nur bei `unklar` (nie bei einem direkten
   404) greift der Ersatzweg.
2. Der YAML-Kopf der Spiegeldatei muss exakt
   `quelle: https://www.gesetze-im-internet.de/<slug>/` ausweisen; die Norm
   muss als aktive Überschrift vorhanden sein. Fehlt sie oder ist sie
   `(weggefallen)`, ist der Beleg `tot`.
3. Ist auch der Spiegel nicht auswertbar, bleibt der Befund fail-closed
   `unklar` – mit sichtbarem Grund im Bericht. Die Queue bleibt dann offen.

**Grenze der Aussage:** Ein `ok` über den Spiegel bestätigt ausschließlich den
Normbestand. Es ist keine Inhaltsprüfung des Artikels, kein Abruf der amtlichen
Seite und keine fachliche Freigabe. Der Bericht führt jede Ersatzprüfung mit
Artikel, Quellen-ID, zitierter Adresse und geprüfter Spiegeldatei einzeln auf;
die Zusammenfassung zählt sie getrennt.

**Transportvertrag (#1024):** `net_safety.sicherer_abruf_status` liefert zwei
Werte (Status, End-URL), `net_safety.sicherer_abruf` drei (Status, Köpfe,
Bytes). Der Spiegel-Adapter hatte bis zum 03.11.2026 nur zwei entpackt; jeder
Ersatzabruf endete deshalb in einem geschluckten `ValueError` und die fünf
GII-Zitate blieben dauerhaft `unklar`. Der Vertrag ist heute Teil des
`--selftest` und der Unit-Tests: Ein Test injiziert 2-Tupel für die Logik,
weitere Tests fahren den **echten** Adapter gegen ein 3-Tupel. Wer den
Transport ändert, sieht es sofort rot.

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

## Woher Hochrisiko-Entwürfe kommen dürfen (seit 13.10.2026, #734)

Ein Hochrisiko-Entwurf entsteht nur auf menschlichen Auftrag:

- **Content-Engine:** produziert ausschließlich die AUTO-Bahn
  (`engine_capacity.nur_auto`, Issue #521).
- **KI-Redaktion und Poppy-Werkbank** (`claude_writer.py`, `news_writer.py`,
  `poppy_repurpose.py`): YMYL nur mit `--fachfreigabe` und bei offenem
  WIP-Limit (`YMYL_WIP_LIMIT`, Standard 3). Der Entwurf trägt dann das
  Gerüst `redaktionelle_pruefung` (risikoklasse „hoch“, status
  „ausstehend“). In der Queue steht er mit E05 („noch nicht freigegeben“),
  nicht mit E03 („niemand wusste davon“).
- `python3 scripts/ki_redaktion.py --promote <slug>` verweigert
  Hochrisiko-Entwürfe ohne gültige Freigabe.
- `scripts/faktenfrische.py` schreibt in Hochrisiko-Artikel **keine**
  `quellen` aus Recherche-Signalen mehr. Ein Signal (Feed-Treffer,
  Referenzseite des Amts) ist kein Beleg: Am 15.10.2026 entstand so ein
  Entwurf mit genau einer Pseudo-Quelle („Referenzseite destatis.de“), der
  damit dauerhaft unsiegelbar war. `quellen` ist ein Beweisfeld und bleibt
  redaktionell; die Wartung schreibt bei `risikoklasse: hoch` nur den
  `faktencheck`-Stempel und verweigert die Arbeit an versiegelten Fassungen.

Taucht trotzdem ein E03-Entwurf auf, ist das zuerst ein Produktionsfehler und
erst danach ein Prüfauftrag: Herkunft klären (`ki_redaktion:`,
`ai_generated:` im Frontmatter), die Ursache im Generator beheben, dann über
den Entwurf entscheiden.

## Freigeben oder verwerfen

Eine Prüfung kann auch mit **Verwerfen** enden. Das ist eine
Redaktionsentscheidung, keine Automatik. Verworfen wird, wenn die Freigabe in
Wahrheit einen neuen Artikel verlangen würde, etwa bei:

- fehlendem Anlass (eine „News“ ohne Ereignis) oder einer Titel-Dublette;
- Kernaussagen, die die Belegkette widerlegt oder nicht trägt;
- einem Kaufaufruf, der der eigenen Methodik widerspricht.

Vorgehen: Befund mit Quellen im Prüfbericht festhalten
(`YMYL-PRUEFQUEUE-<nr>-….md`) und den Entwurfsordner mit `git rm -r` entfernen
(die Fassung bleibt in der Git-Historie). Wenn das Thema es wert ist, wird es
als Brief für die FACHFREIGABE-Bahn neu beauftragt. Die Automatik löscht nie;
bis zur Entscheidung bleibt ein Hochrisiko-Entwurf als manueller Review-Hold
liegen.

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

# Belegketten-Wache (nur lesend; Exit 1 nur bei definitiv toter Quelle)
python3 scripts/belegketten_wache.py --nur-hochrisiko --report --strict
python3 scripts/belegketten_wache.py --selftest

# Beide Hälften der Queue lokal prüfen (Gate + Wache inkl. Transportvertrag)
npm run test:redaktion:ymyl

# Scharfer Lauf, wie ihn der Workflow für die Ticket-Erledigung verlangt
python3 scripts/belegketten_wache.py --nur-hochrisiko --report --strict --require-complete
```

Der werktägliche Workflow `.github/workflows/redaktionelle-ymyl-pruefung.yml`
pflegt genau ein GitHub-Arbeitsticket statt Einzelwarnungen zu streuen. Er
prüft vor der Messung das Regelwerk beider Hälften und schließt das Ticket
nur, wenn Gate-Zahl **und** Wachen-Ergebnis grün sind. Neue
Publikationskandidaten werden unabhängig davon im `publish_gate.py` sofort
fail-closed gehalten; Hochrisiko-Entwürfe werden nicht gelöscht, sondern als
manueller Review-Hold erhalten.

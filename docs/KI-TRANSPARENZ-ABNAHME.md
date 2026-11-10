# KI-Transparenz: Nachweise und Abnahme (#1028)

Dieses Verfahren dokumentiert technische Nachweise; es ersetzt keine Rechtsberatung.
Ein grünes Gate sagt nicht, dass Bildherkunft oder Anbieter-Konformität bewiesen sind.

## 1. Systeme und Anbieter

Aus `data/ki_redaktion.yaml`, `scripts/llm_client.py`, Workflows und Audio-Logs
für den jeweiligen Veröffentlichungszeitraum die tatsächlich verwendeten
Produkte/Versionen, Zweck, Ausgabeart, Inverkehrbringen und die jeweilige Rolle
ermitteln. Konfiguration und Modellname allein beweisen keinen Produktionslauf.
Auch extern erstellte Assets und Coding-Agenten erfassen. Unbekannt bleibt offen.
Keine Tokens, Prompts mit personenbezogenen Daten oder Vertragsgeheimnisse
ins Repository schreiben.

**Anfragevorlage an jeden betroffenen Anbieter (nicht bereits versendet):**

> Wir nutzen [Produkt/API, Modell und Version] für [Text/Bild/Ton]. Bitte teilen
> Sie für die konkrete EU-Bereitstellung mit: Wer ist Anbieter des KI-Systems?
> Wann wurde dieses System in Verkehr gebracht? Wie werden die betreffenden
> Ausgaben nach Art. 50 Abs. 2 KI-VO maschinenlesbar markiert und erkannt?
> Welche Modalitäten, Modelle, Regionen und Ausnahmen gelten? Wie lässt sich
> die Markierung prüfen und wie robust ist sie bei unserer Bearbeitung,
> Kompression, Formatkonvertierung und Weitergabe? Ab wann gilt Ihre Antwort?
> Bitte nennen Sie eine belastbare Dokumentation oder schriftliche Bestätigung.

Antwort mit Datum, konkreter Produktversion, Quelle, Ansprechpartner/Rolle
und nächster Wiedervorlage dokumentieren. Eine allgemeine Produkt- oder
Forschungsseite nicht als Bestätigung der konkreten Konfiguration ausgeben.
Bei möglicher eigener Anbieterrolle fachkundig prüfen, nicht automatisch
an den Modellhersteller delegieren.

## 2. Bilder: Inventar und Schutz

`python3 scripts/ki_cover_provenienz.py --json` listet Cover-Referenzen. Die
Liste umfasst auch Entwürfe; `nicht_belegt` bedeutet **unbekannt**, selbst wenn
`ai_generated: false` gesetzt ist. Inline-Bilder, andere Dateitypen, externe
Tools und Social-Ausgaben separat inventarisieren. `data/covers_manifest.json`
enthält Titel und Design, aber keinen beweiskräftigen Datei-Hash. Quellen,
Originale, Aufträge und die zugrunde liegende Datei einzelfallbezogen prüfen.
`python3 scripts/ki_cover_render_audit.py --json` kann Manifest-Eingaben
verlustfrei nachrendern und Byte-/Pixelgleichheit für jede Cover-Referenz
prüfen. Der versionierte Beleg vom 03.11.2026 liegt in
`data/beweise/ki-cover-render-audit-2026-11-03.json`. Gleichheit zeigt, dass
der regelbasierte Generator dasselbe Ergebnis erzeugen kann; sie beweist nicht,
wie die Originaldatei tatsächlich entstanden ist. Abweichung beweist keine KI.

Nur wenn die Bildherkunft belegt ist: Original unverändert unter `static/`
speichern, `sha256sum static/images/covers/DATEI.jpg` ausführen und im
Cover-Frontmatter ergänzen:

```yaml
cover:
  image: images/covers/DATEI.jpg
  alt: "Sachliche Bildbeschreibung"
  ai_generated: true
  ki_pruefung:
    sha256: "<sha256sum des Originalbilds>"
    quelle: "<konkreter überprüfbarer Herkunftsnachweis>"
    geprueft_am: 2026-11-03
    deepfake: false
    # IPTC Digital Source Type – nur einer dieser beiden Werte, nur belegt:
    #   trainedAlgorithmicMedia              = vollständig generativ erzeugt
    #   compositeWithTrainedAlgorithmicMedia = aufgenommenes Bild, generativ bearbeitet
    digital_source_type: trainedAlgorithmicMedia
    werkzeug: "<Produkt und Modell, falls bekannt>"
    c2pa_manifest_url: "<optional: URL eines signierten C2PA-Manifests>"
```

**Reihenfolge ist Pflicht:** erst markieren, dann hashen. Der Befehl

```
python3 scripts/ki_bild_markierung.py --write
```

schreibt `digital_source_type` als XMP-Paket in die JPEG-Datei, ohne die
Bilddaten neu zu kodieren (Pixel bleiben byteweise erhalten, die Datei wird
größer). Danach muss `sha256` neu berechnet und im Frontmatter eingetragen
werden, sonst meldet `ki_cover_provenienz.py --gate` zu Recht eine Abweichung.
`python3 scripts/ki_bild_markierung.py --gate` prüft, ob jedes deklarierte
KI-Cover das Feld wirklich trägt. Enthält eine Datei bereits abweichendes XMP,
blockiert das Werkzeug: fremde Herkunftsnachweise werden nicht still
überschrieben (das verlangt auch der Verhaltenskodex vom 10.06.2026). Eine
bewusste Entscheidung braucht `--force`.

`deepfake: false` darf nur nach echter Prüfung gesetzt werden. Bei Deepfake
blockiert das Gate absichtlich: Sichtbarkeit auf allen beabsichtigten
Ausspielwegen ist nicht automatisch hergestellt. Stattdessen Bild zunächst
nicht ausspielen und fachkundig eine vollständige Kanal-Lösung festlegen.
`--gate` prüft Format, Existenz, Hash und Angaben, nicht deren Wahrheitsgehalt.
Wird dieselbe Datei auf mehreren Seiten referenziert, müssen alle Referenzen
deklariert und geprüft sein; das Gate erkennt lokale Pfad-Aliases.
Bei Bildwechsel/Neugenerierung Herkunft neu bewerten und Hash erneuern.
Deklarierte Originale werden im Cover-Template ohne responsive Umkodierung
geliefert und vom Cover-Generator nicht überschrieben. Andere Tools, Uploads,
CDNs oder Nutzer können Metadaten verändern; daraus folgt kein Nachweis, dass
C2PA oder Wasserzeichen durchgängig erhalten bleiben. Für einen Nachweis
Original und gelieferte Datei mit einem geeigneten **Signaturprüfer** bzw.
Anbieter-Detektor vergleichen; ein fehlendes Wasserzeichen beweist keine
menschliche Herkunft. Einzelne Markdown-Bilder sind hiervon nicht erfasst.

## 3. Artikel und Freigabe

Seit dem 10.11.2026 ist die Ausnahme „redaktionelle Verantwortung“
fail-closed: `ai_generated: false` akzeptiert das Kennzeichnungs-Gate nur mit
freigegebenem Status, Prüfername und -rolle, Prüfdatum sowie einem gültigen
`inhalt_sha256`, der exakt zur veröffentlichten Fassung passt. Ein Eintrag
unter `menschlich` oder eine bloße Status-Zeile reicht ausdrücklich nicht.
Die neun zuvor unbelegten Ausnahmen wurden konservativ auf
`ai_generated: true` gestellt; drei später fassungsgebunden geprüfte Artikel
nutzen den Redaktionspfad. Eine Änderung am Text entwertet die Ausnahme
automatisch. Die Heilung kennzeichnet konservativ und erfindet weder Herkunft
noch menschliche Prüfung. Deepfake- und Textpflichten nicht verwechseln.

## 3b. Maschinenlesbare Betreiberebene (#1028)

Art. 50 Abs. 2 KI-VO ist eine Anbieterpflicht; für vor dem 02.08.2026 in
Verkehr gebrachte Systeme läuft die Nachfrist bis 02.12.2026. Der
Verhaltenskodex der Kommission vom 10.06.2026 nennt dafür signierte
Metadaten, Wasserzeichen und optional Fingerabdrücke. Er verpflichtet
nachgelagerte Akteure außerdem, vorhandene Markierungen **nicht zu
entfernen** – deshalb trägt auch der Feed die Angabe weiter (Kanal 6).

Was der **Betreiber** selbst maschinenlesbar machen kann, liegt auf sieben
Kanälen. Alle entstehen aus derselben Quelle
(`layouts/_partials/_funcs/ki_modalitaeten.html`), keiner hat eine eigene
Pflegestelle:

| # | Kanal | Fundstelle | Regel |
|---|---|---|---|
| 1 | `<meta name="ai-generated">`, `ai-generated-scope`, `rel="describedby"` → `/impressum/#ki-hinweis` | `layouts/_partials/ki_provenienz.html` | M1, M2 |
| 2 | schema.org `creditText` im Article-JSON-LD | `layouts/_partials/schema_article.html` | M1, M2 |
| 3 | `data-ai-generated`, `data-digital-source-type` am `<img>` | `layouts/_partials/cover.html` | M1, M2 |
| 4 | IPTC `DigitalSourceType` **in der Bilddatei** (ohne Neukodierung) | `scripts/ki_bild_markierung.py` | M3 |
| 5 | Sichtbare Angabe zur Tonspur: Chip `data-ff-ki-voice-label`, `aria-describedby`, SR-Satz, `aria-label` aus `I18N` | `ff_voice_toolbar.html`, `static/premium/ff-voice.js`, `assets/css/extended/ff-voice.css` | M2, M4 |
| 6 | Feed: `xmlns:ffki`, `rel="describedby"` auf Kanal- **und** Item-Ebene, `ffki:ai-generated`, `ffki:ai-generated-scope`, `media:credit` | `layouts/rss.xml` + `layouts/_default/rss.xml` | M5, M7 |
| 7 | Bild-Ableitungen: Der Optimizer leitet von deklarierten KI-Originalen nichts Unmarkiertes ab (AVIF/WebP/JPEG-Geschwister) | `scripts/image_optimizer.py` | M6 |

**Regel M4** prüft Kanaltreue **je Modalität und in beide Richtungen**: Ein
Signal ohne sichtbaren Hinweis ist ein halber Kanal, ein Hinweis ohne Signal
genauso. Befund vom 07.11.2026: 84 Seiten spielten eine synthetische Stimme,
aber 66 zeigten nur einen Hinweis auf den Text und 18 gar keinen.

**Deckung:** M1 prüft den **ganzen gebauten Baum** – 109 reguläre Seiten in 19
Abschnitten, nicht nur `content/posts` (78). Die sechs Ratgeber-Säulen unter
`pillar/` waren der blinde Fleck: Sie tragen eine Tonspur und keine Regel
erfasste sie.

**Robustheit (C33/C38):** Fehlt ein Messwerkzeug (PyYAML, Pillow,
`ki_bild_markierung.py`), ist der Exit-Code **2** (Werkzeugfehler) und der
Befund läuft über `scripts/werkzeugbefund.py` – nicht 1 (Inhaltsfund) und
nicht als Traceback. Eine ausgefallene Messung ist kein Grün.

### Selbstheilung und Wache

`scripts/ki_provenienz_gate.py` kennt vier Betriebsarten:

| Aufruf | Wirkung |
|---|---|
| `--gate` | messen, Befunde melden, Exit 0/1/2 |
| `--gate --source-only` | nur Regeln ohne Bauprodukt (M2/M3/M6/M7) – der Vor-Build-Schritt |
| `--heilen [--source-only]` | reparieren, dann nachmessen, Belegzeile schreiben |
| `--wache` | heilen + Alter ungeklärter Angaben gegen die Frist führen |
| `--selftest` | 12 Szenarien an einer künstlichen Fassung, inkl. Sabotageproben |

Geheilt wird nur, was **mechanisch eindeutig** ist: der Anker `{#ki-hinweis}`
an der vorhandenen Überschrift (bytetreu, idempotent), die Bytgleichheit der
beiden RSS-Vorlagen, das Entfernen unmarkierter Ableitungen eines deklarierten
KI-Originals. Jede Heilung schreibt eine Belegzeile nach
`data/ki_provenienz_history.jsonl`.

**Eskaliert** wird, was nur ein Mensch entscheiden kann: ob bei einem
`menschlich`-Eintrag im Register tatsächlich ein Mensch die redaktionelle
Verantwortung übernommen hat, woher ein Bild stammt, ob der Anbieter
nachgefragt wurde. Erfinden tut die Wache nichts – eine Angabe ohne Beleg wird
nie zu einer Angabe mit Beleg. Tragen **beide** RSS-Vorlagen verschiedene
Fassungen des Kanals, ist das eine Entscheidung und bleibt ein Fund.

**Alter:** `data/ki_provenienz_state.json` führt das Erst-Datum jedes
ungeklärten `menschlich`-Eintrags und nennt den Abstand zur Frist
(02.12.2026). Gespeichert wird nur der Dauerzustand; abgeleitete Zahlen
(Alter in Tagen, Restfrist) werden zur Laufzeit gerechnet. Sonst committet die
Wache täglich die Uhr statt des Befunds (Lehre aus der Befundakte,
06.11.2026).

Verankert ist das an zwei Stellen:

* `deploy.yml`: Selbstheilung **vor** dem Build (`--heilen --source-only`),
  Selbsttest + `--gate` **nach** dem Build. Geheiltes läuft über den
  bestehenden Gate-Heilungscommit.
* `.github/workflows/ki-provenienz-wache.yml`: bei jeder Änderung an
  Kennzeichnungs-Pfaden und täglich 06:22 MESZ. Reihenfolge im Lauf: erst
  heilen und committen, **dann** rot werden – sonst repariert die Wache jedes
  Mal neu und der Bestand bleibt trotzdem kaputt.

Befehl für den Alltag: `npm run ki:provenienz:wache`.

**Was diese Ebene nicht ist:** kein Herkunftsbeweis, kein Wasserzeichen, keine
C2PA-Signatur und keine Erfüllung der Anbieterpflicht. `ai_generated: false`
erzeugt bewusst kein Signal – die Abwesenheit einer Angabe ist keine
Behauptung „rein menschlich". Der IPTC-Wert wird nur bei belegter
Erzeugungsart geschrieben; erfunden wird nichts. Ein grünes Gate heißt:
Die Betreiberebene ist vollständig und widerspruchsfrei ausgeliefert. Es heißt
nicht: Die Herkunft ist bewiesen.

## 4. Live-Abnahme nach Integration

1. Integritäts-Lock und dokumentierte Betreiberfreigabe prüfen; bei späteren
   Kernänderungen ist eine erneute bewusste Freigabe erforderlich. Erfolgreiches
   offizielles Pages-Deployment und ausgelieferte Revision prüfen; ein grüner
   lokaler Build oder `gh-pages` allein genügt nicht.
2. Eine bekannte KI-Textseite mit und eine ohne redaktionelle Freigabe im
   Browser samt Screenreader/ohne JavaScript prüfen: deutlicher Hinweis am
   Artikelanfang; keine falsche Freigabe. Eine nicht gekennzeichnete Seite
   gegen das tatsächliche Register und ihre Herkunft prüfen.
3. Maschinenlesbare Ebene an der **live ausgelieferten** Fassung prüfen, nicht
   am lokalen Build: Seitenquelltext einer KI-Seite auf
   `<meta name="ai-generated" content="true">`, `ai-generated-scope` und
   `rel="describedby"` (Zielanker `/impressum/#ki-hinweis` muss erreichbar
   sein); `creditText` im JSON-LD über den Rich-Result-Test oder
   `curl … | grep creditText`; bei deklariertem KI-Cover die Quelldatei
   herunterladen und mit einem Metadaten-Leser auf `DigitalSourceType` prüfen.
   Eine Seite ohne `ai_generated: true` darf das Signal **nicht** tragen.

   Seit dem 07.11.2026 gehören zwei Kanäle dazu, die vorher nicht ausgeliefert
   wurden und deshalb live nachzuprüfen sind:

   * **Tonspur:** Auf einer Seite mit Lesehilfe – auch auf einer Ratgeber-Säule
     unter `/pillar/`, die bis zum 07.11.2026 von keiner Regel erfasst war –
     muss das Siegel am Vorlese-Knopf sichtbar sein, der Screenreader den Satz
     zur maschinell erzeugten Stimme vorlesen und das `aria-label` nach dem
     Klick denselben Hinweis tragen. Mit und ohne JavaScript, im hellen und im
     dunklen Thema; Kontrast mindestens 4.5:1, gemessen aus `ff-voice.css`
     durch `scripts/a11y_audit.py` (nicht abgeschrieben, sondern aufgelöst).
   * **Feed:** `curl -s https://franksfinanzcheck.de/index.xml` muss auf
     Kanal- **und** Item-Ebene `rel="describedby"` zeigen sowie
     `ffki:ai-generated` und `ffki:ai-generated-scope`; der `scope` eines Items
     muss dem der Seite entsprechen. Aus diesem Feed publiziert Pinterest
     automatisch weiter – fehlt die Angabe hier, geht sie auf dem
     Verbreitungsweg verloren, obwohl die Seite selbst korrekt ist.
4. Für jedes tatsächlich deklarierte KI-Cover Einzelansicht, Listenansicht,
   Quelldatei und alle relevanten Social-/OG-Ausgaben prüfen. Original und
   live ausgelieferte Datei byteweise vergleichen; getrennt Signatur bzw.
   Wasserzeichen mit geeignetem Werkzeug prüfen. **Ebenso die Ableitungen:**
   Jedes öffentlich erreichbare AVIF/WebP/JPEG-Geschwisterbild eines
   deklarierten KI-Originals muss die Markierung tragen oder darf gar nicht
   erst erzeugt worden sein (Regel M6, `scripts/image_optimizer.py --check`).
   Keine Prüfung behaupten, wenn kein passendes KI-Cover vorliegt.
5. Ergebnis mit URLs, Zeit, Revision, Testdaten, Tool und offenen Abweichungen
   dokumentieren. Erst nach Betreiberfreigabe, Nachweisen und ggf. juristischer
   Prüfung den Workflow „Fristen-Check (Recht)“ mit
   `erledigt=ki-vo-kennzeichnung-bestand` ausführen.

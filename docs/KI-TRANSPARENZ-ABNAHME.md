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

## 2. Bilder: Inventar und Schutz (Bildherkunft, Frist 02.12.2026, #1028)

Die Covers dieses Blogs sind beweisbar nicht von einem generativen Bildmodell
stammend, sondern deterministisch gerenderte Vorlagen
(`scripts/generate_covers.py`, `DESIGN_VERSION = 3`: Verlauf, Badge, Titeltext,
Markenband; keine Bildmodell-Ausgabe). Derselbe Input ergibt dieselbe Datei –
gemessen am 13.11.2026: **132 von 132 Covern pixelidentisch zu einem frischen
Render** (`scripts/cover_render_check.py`, 0 Befunde), und ein Lauf ohne
`--force` rendert nichts.

Drei Belege, ein Werkzeug (`scripts/ki_cover_herkunft.py`):

1. `--attestieren` schreibt je Cover `cover.ki_pruefung` ins Frontmatter:
   `digital_source_type: algorithmicMedia`, `variante: renderer-v3`,
   `sha256` der markierten Datei, `verfahren` und `geprueft_am`.
2. `--markieren` schreibt `DigitalSourceType=algorithmicMedia` als IPTC-XMP
   **in die Bilddatei** (APP1, ohne Neukodierung – die Datei trägt ihre
   Herkunft selbst).
3. `--pruefen` ist die Wache: Rendert jedes Cover neu und verlangt
   Pixelgleichheit plus Frontmatter-Beleg.

**Reihenfolge ist Pflicht:** erst `--markieren` (Datei), dann
`--attestieren` (sha256 der markierten Datei), dann `--pruefen`.

Das Frontmatter-Beleg-Schema (je Cover, nur wenn die Herkunft belegt ist):

```yaml
cover:
  image: images/covers/DATEI.jpg
  alt: "Sachliche Bildbeschreibung"
  ki_pruefung:
    digital_source_type: algorithmicMedia   # deterministisch gerendert, kein Bildmodell
    variante: renderer-v3
    verfahren: "generate_covers.py (Pillow, deterministisch)"
    sha256: "<sha256sum der markierten DATEI.jpg>"
    geprueft_am: 2026-11-13
```

`scripts/ki_cover_provenienz.py --json` listet alle Cover-Referenzen (inkl.
Entwürfe); `nicht_belegt` bedeutet **unbekannt**, selbst wenn
`ai_generated: false` gesetzt ist. Inline-Bilder, andere Dateitypen, externe
Tools und Social-Ausgaben separat inventarisieren.
`data/covers_manifest.json` enthält Titel und Design, aber keinen
beweiskräftigen Datei-Hash. Quellen, Originale, Aufträge und die zugrunde
liegende Datei einzelfallbezogen prüfen.

**Stale-Referenzen:** `scripts/generate_covers.py` normalisiert
`cover.image` auf `images/covers/<slug>.jpg` (Self-Healing, bei jedem Lauf).
Ein Artikel, dessen Datum/Slug sich geändert hat, referenziert danach immer
die korrekte Datei – das war die Ursache früherer Drift-Befunde.

**Rechte und Grenzen:** Ein `algorithmicMedia`-Beleg sagt nichts über
Schrift-, Marken- oder Dritter-Rechte; er beweist nicht, wie eine Datei
*tatsächlich* entstanden ist (Gleichheit zeigt nur, dass der Generator dasselbe
erzeugen kann); und er gilt nicht für spätere modelbasierte Renders (dagegen
steht die Reproduktionswache). Ein fehlendes Wasserzeichen beweist keine
menschliche Herkunft. Einzelne Markdown-Bilder sind hiervon nicht erfasst.
`deepfake: false` darf nur nach echter Prüfung gesetzt werden; bei Deepfake
blockiert das Gate absichtlich.

## 3. Artikel und Freigabe

Die `menschlich`-Einträge in `data/ki_kennzeichnung.yaml` sind laut Register
nicht alle belegt; menschliche Prüfung und redaktionelle Verantwortung müssen
für die jeweilige veröffentlichte Fassung tatsächlich nachgewiesen sein.
Automatische Tests oder eine bloße Status-Zeile reichen nicht. Bei fehlendem
Nachweis Herkunft klären und ggf. sachgerecht kennzeichnen; keine menschliche
Prüfung erfinden. Deepfake- und Textpflichten nicht verwechseln.

**Freigabe-Liste (Operator, nicht der Agent):** Die 12 ungeklärten
`menschlich`-Einträge (14.08.–03.09.2026) werden mit
`scripts/freigabe_liste.py` einzeln abgehakt (Zustand in
`data/freigabe_state.json`; `ki_kennzeichnung.yaml` bleibt unangetastet).
Erst wenn alle 12 getickt sind, erzeugt das Tool die Betreibererklärung mit
`erledigt=ki-vo-kennzeichnung-bestand` und Unterschriftszeilen – auszufüllen
in `docs/FREIGABE-VORLAGE-KI-VO-KENNZEICHNUNG-BESTAND.md`.

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
| 8 | schema.org `digitalSourceType` im Article-JSON-LD (`TrainedAlgorithmicMediaDigitalSource` / `CompositeWithTrainedAlgorithmicMediaDigitalSource`) – **nur** bei belegter Erzeugungsart des Titelbilds | `layouts/_partials/schema_article.html` | M1, M2 |
| 9 | IPTC `DigitalSourceType` **in der Tondatei** (ID3-TXXX bei MP3, RIFF-INFO bei WAV), dazu `AISystemUsed`, `Provenance`, `Software` – ohne Neukodierung, bytegenau umkehrbar | `scripts/ki_audio_markierung.py` | M3 |
| 10 | `llms.txt`: Abschnitt „Woher diese Inhalte kommen" – Text, Bild, Ton, Assistent, Betreiber-Erklärung statt Anbieterpflicht | `scripts/generate_llms_txt.py` → `static/llms.txt` | M9 |
| 11 | Assistent: sichtbarer Satz im Dialogkopf („Antworten erzeugt ein KI-System – kein Mensch."), Hinweis aus der Antwort im Dialog, HTTP-Kopfzeile `ai-generated` auf jedem Antwortpfad | `layouts/_partials/ki_assistent.html`, `static/premium/ki-assistent.js`, `cloudflare/ki-assistent/worker.js` | KA11 |

**Nachtrag 13.11.2026 (Frist 02.12.2026, #1028).** Die Kanäle 8–11 kamen
geschlossen hinzu, nachdem eine Kanaltreue-Prüfung über alle Auslieferungswege
drei Lücken zeigte:

* **Tondatei (9)** – Die Seite sagte seit dem 05.11.2026, dass eine maschinelle
  Stimme vorliest; die MP3 sagte es nicht. Wer sie herunterlädt, weiterreicht
  oder spiegelt, hielt synthetische Sprache ohne Herkunft in der Hand. Genau
  der Fall, für den Art. 50 Abs. 2 die Markierung *am Werk* verlangt – und der
  einzige Kanal, der die Seite verlassen kann. Der Marker schreibt nur, was
  ein Erzeugerbeleg (`*.track.json`) deckt; ohne Beleg bleibt die Datei
  unangetastet. Er kodiert nichts neu: Audiodaten byteweise unverändert,
  fremde Metadaten (Encoder, Titel) bleiben stehen, `--entfernen` stellt die
  Datei **bytegenau** wieder her (geprüft an echter `ffmpeg`-Ausgabe, MP3
  ID3v2.4 und WAV, in `scripts/tests/test_ki_audio_markierung.py`).
* **schema.org (8)** – `creditText` sagte, *dass* KI beteiligt war; die
  Erzeugungsart des Titelbilds (`trainedAlgorithmicMedia`) stand nur im Bild
  und im `<img>`-Attribut, nicht im JSON-LD. Das Feld wird nur bei belegter
  Erzeugungsart gesetzt; heute ist für **kein** Titelbild eine Erzeugungsart
  belegt (0 von 115 Artikeln), deshalb steht es derzeit nirgends – das ist der
  ehrliche Stand, keine Lücke im Code. Nachgewiesen am gerenderten Artikel mit
  gesetztem Wert: genau eine Seite trägt die Angabe, keine andere.
* **Assistent (11)** – Der Worker schickte zu jeder Antwort einen Hinweis im
  JSON-Körper; der Client las das Feld **nie** (`data.hinweis` kam in
  `static/premium/ki-assistent.js` nicht vor). Die Interaktion war damit nur
  in der Fußzeile angedeutet, nicht offengelegt. Art. 50 Abs. 1 gilt seit
  02.08.2026 **ohne** Übergangsfrist und verlangt die Erkennbarkeit im ersten
  Moment. Jetzt: Satz im Dialogkopf, Hinweis unter jeder Antwort, Kopfzeile
  `ai-generated` auf Erfolgs- **und** Fehlerpfad; das Gate KA11 prüft beides
  und lässt sich selbst sabotieren.

**Was auch diese Kanäle nicht sind:** Kanäle 8–11 sind Erklärungen des
Betreibers. Sie ersetzen die Markierung durch den Anbieter des jeweiligen
KI-Systems nicht (Art. 50 Abs. 2 KI-VO) und beweisen keine Herkunft. Ein
`digitalSourceType` im JSON-LD ohne Erzeugerbeleg wäre eine Erfindung – deshalb
hängt er an `cover.ki_pruefung.digital_source_type`, nicht an `ai_generated`.

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
| `--gate --source-only` | nur Regeln ohne Bauprodukt (M2/M3/M6/M7/M9) – der Vor-Build-Schritt |
| `--heilen [--source-only]` | reparieren, dann nachmessen, Belegzeile schreiben |
| `--wache` | heilen + Alter ungeklärter Angaben gegen die Frist führen |
| `--selftest` | 15 Szenarien an einer künstlichen Fassung, inkl. Sabotageproben (M9: fehlender Abschnitt und überzogene Behauptung) |

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
   Seit dem 13.11.2026 kommen vier Kanäle hinzu, die ebenfalls nur live zählen:

   * **Tondatei:** Eine ausgelieferte MP3 herunterladen
     (`curl -sO https://franksfinanzcheck.de/audio/articles/<slug>.mp3`) und
     mit einem **fremden** Metadaten-Leser öffnen – nicht mit unserem Skript
     (`ffprobe -show_entries format_tags` bzw. `mutagen`). Erwartet:
     `DigitalSourceType` = `…/digitalsourcetype/trainedAlgorithmicMedia`,
     `AISystemUsed`, `Provenance`. Zusätzlich: Die Audiodaten müssen vor und
     nach der Markierung byteweise gleich sein, und die Datei muss sich
     bytegenau in den Ausgangszustand zurückführen lassen
     (`python3 scripts/ki_audio_markierung.py --entfernen`), sonst wäre die
     Markierung ein Eingriff in das Werk.
   * **schema.org:** `curl -s <KI-Artikel> | grep -o 'digitalSourceType[^,]*'`.
     Trägt ein Artikel mit belegter Erzeugungsart (`cover.ki_pruefung.
     digital_source_type`) den Wert, und trägt ihn **kein** Artikel ohne
     diesen Beleg? (Stand 13.11.2026: 0 von 115 – es ist für kein Titelbild
     eine Erzeugungsart belegt. Ein fehlender Wert ist dann der richtige
     Befund, ein erfundener wäre der Fehler.)
   * **`llms.txt`:** `curl -s https://franksfinanzcheck.de/llms.txt` muss den
     Abschnitt „Woher diese Inhalte kommen" mit den vier Ankern enthalten
     (maschinenlesbare Kennzeichnung, Erzeugungsart in Bild und Ton,
     Betreiber-Erklärung statt Anbieterpflicht, kein Herkunftsbeweis).
   * **Assistent:** Nur falls ein Endpoint gesetzt ist (`site.Params.
     kiAssistentEndpoint`): Dialog öffnen und **vor** der ersten Eingabe
     prüfen, ob der Satz „Antworten erzeugt ein KI-System – kein Mensch."
     sichtbar ist (nicht erst nach dem Scrollen), ob eine Antwort den Hinweis
     darunter zeigt und ob `curl -i` gegen den Worker die Kopfzeile
     `ai-generated` trägt. **Ist kein Endpoint gesetzt, ist die richtige
     Abnahme, dass keine Schaltfläche existiert** – dann darf auch das
     Impressum keinen aktiven Assistenten behaupten (der Abschnitt nennt
     ausdrücklich, dass eine fehlende Schaltfläche „derzeit nicht
     eingebunden" bedeutet).

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

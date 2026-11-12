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
überschrieben. Das ist eine technische Schutzmaßnahme; der freiwillige
Verhaltenskodex und seine etwaige Anwendbarkeit sind getrennt zu prüfen. Eine
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

Die `menschlich`-Einträge in `data/ki_kennzeichnung.yaml` sind laut Register
nicht alle belegt; menschliche Prüfung und redaktionelle Verantwortung müssen
für die jeweilige veröffentlichte Fassung tatsächlich nachgewiesen sein.
Automatische Tests oder eine bloße Status-Zeile reichen nicht. Bei fehlendem
Nachweis Herkunft klären und ggf. sachgerecht kennzeichnen; keine menschliche
Prüfung erfinden. Deepfake- und Textpflichten nicht verwechseln.

## 3b. Maschinenlesbare Betreiberebene (#1028)

Art. 50 Abs. 2 KI-VO betrifft die Anbieter generativer Systeme. Für Systeme,
die vor dem 02.08.2026 in Verkehr gebracht wurden, sieht
[Art. 111 Abs. 4](https://ai-act-service-desk.ec.europa.eu/en/ai-act/article-111)
eine Übergangsfrist bis 02.12.2026 vor. Die eigene Rolle ist **je System**
offen; ein Blogbetreiber kann je nach tatsächlicher Bereitstellung auch
Anbieter sein. Die Pflichten für bestimmte Deepfakes und Texte nach Art. 50
Abs. 4 sind davon getrennt.

Der [Transparenz-Kodex](https://digital-strategy.ec.europa.eu/en/policies/code-practice-ai-generated-content)
ist ein **freiwilliger** Weg zum Nachweis der Einhaltung; die gesetzlichen
Pflichten bleiben auch ohne Unterzeichnung bestehen. Abschnitt 1 behandelt
Anbieter-Markierung (u. a. geschützte Metadaten und Wasserzeichen), Abschnitt 2
Betreiber-Kennzeichnung. Die Erhaltung vorhandener Markierungen ist ein
sinnvolles technisches Ziel, aber aus dem Kodex wird hier keine pauschale
Rechtspflicht für jeden nachgelagerten Akteur abgeleitet. Feed-Angaben sind
zusätzliche Betreiberangaben, keine Anbieter-Markierung.

Die folgende Übersicht nennt sieben **geprüfte Betreiber-Kanäle bzw.
Schutzmaßnahmen**, nicht eine vollständige Abdeckung aller Ausspielwege.
Die HTML-/Feed-Modalitäten verwenden den gemeinsamen Helfer
`layouts/_partials/_funcs/ki_modalitaeten.html`; Bilddatei, Optimizer und
Publisher haben darüber hinaus eigene Prüf- und Verarbeitungswege:

| # | Kanal | Fundstelle | Regel |
|---|---|---|---|
| 1 | `<meta name="ai-generated">`, `ai-generated-scope`, `rel="describedby"` → `/impressum/#ki-hinweis` | `layouts/_partials/ki_provenienz.html` | M1, M2 |
| 2 | schema.org `creditText` im Article-JSON-LD | `layouts/_partials/schema_article.html` | M1, M2 |
| 3 | `data-ai-generated`, `data-digital-source-type` am `<img>` | `layouts/_partials/cover.html` | M1, M2 |
| 4 | IPTC `DigitalSourceType` **in der Bilddatei** (ohne Neukodierung) | `scripts/ki_bild_markierung.py` | M3 |
| 5 | Sichtbare Angabe zur Tonspur: Chip `data-ff-ki-voice-label`, `aria-describedby`, SR-Satz, `aria-label` aus `I18N` | `ff_voice_toolbar.html`, `static/premium/ff-voice.js`, `assets/css/extended/ff-voice.css` | M2, M4 |
| 6 | Feed: `xmlns:ffki`, `rel="describedby"` auf Kanal- **und** Item-Ebene, `ffki:ai-generated`, `ffki:ai-generated-scope`, `media:credit` und lesbarer Zielartikel-/Cover-Hinweis | `layouts/rss.xml` + `layouts/_default/rss.xml` | M5, M7 |
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
| `--wache` | heilen + Alter ungeklärter Angaben gegen die Frist führen; fällige Eskalation = Exit 1, nicht messbar = Exit 2 |
| `--selftest` | 12 Szenarien an einer künstlichen Fassung, inkl. Sabotageproben |

Geheilt wird nur, was **mechanisch eindeutig** ist: der Anker `{#ki-hinweis}`
an der vorhandenen Überschrift (bytetreu, idempotent), die Bytgleichheit der
beiden RSS-Vorlagen und bestimmte unmarkierte Optimizer-Ableitungen eines
deklarierten KI-Originals. Vorhandene Social-Bildvarianten werden als Befund
**gemeldet**, nicht blind gelöscht. Jede tatsächliche Wache-Heilung schreibt
eine Belegzeile nach `data/ki_provenienz_history.jsonl`.

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

Ein fehlendes, unlesbares, mehrdeutiges oder widersprüchliches Register ist
nicht messbar (Exit 2); dabei werden alte offene Fälle nicht aus dem Zustand
gelöscht. Ein fehlender oder defekter versionierter Wachzustand wird nicht
still durch einen neuen ersetzt (Exit 2). Aus dem Register verschwundene Fälle
bleiben im Zustand mit ihrem Erst-Datum erhalten und werden unabhängig von der
Restfrist eskaliert: Löschen oder Umklassifizieren ist kein Prüfbeleg. Erst
nach dokumentierter Einzelfallentscheidung berichtigt der Betreiber Register
und Zustand gemeinsam; diese bewusste Änderung ist über die Git-Historie zu
reviewen. Das Kennzeichnungs-Gate stellt `ai_generated: true` nur bei einer
positiven `maschinell`-Registerangabe wieder her; für sonst ungeklärte
Herkunft bleibt es rot und erfindet keine Tatsachenbehauptung.

Verankert ist das an zwei Stellen:

* `deploy.yml`: Selbstheilung **vor** dem Build (`--heilen --source-only`),
  Selbsttest + `--gate` nach dem ersten Build und ein **finales** `--gate`
  nach möglichen Inhaltsheilungen, Rebuild und Pagefind vor dem `gh-pages`-Push
  **und** dem offiziellen Pages-Artefakt. Geheiltes läuft über den
  bestehenden Gate-Heilungscommit.
* `.github/workflows/ki-provenienz-wache.yml`: bei Änderungen an den
  überwachten Pfaden und täglich um 04:22 UTC. Reihenfolge im Lauf: erst
  heilen und committen, **dann** rot werden – sonst repariert die Wache jedes
  Mal neu und der Bestand bleibt trotzdem kaputt. Ungeklärte Registereinträge
  führen innerhalb von 30 Tagen vor der Frist zu Exit 1.

Befehl für den Alltag: `npm run ki:provenienz:wache`.

**Was diese Ebene nicht ist:** kein Herkunftsbeweis, kein Wasserzeichen, keine
C2PA-Signatur und keine Erfüllung der Anbieterpflicht. `ai_generated: false`
erzeugt bewusst kein Signal – die Abwesenheit einer Angabe ist keine
Behauptung „rein menschlich". Der IPTC-Wert wird nur bei belegter
Erzeugungsart geschrieben; erfunden wird nichts. Ein grünes Gate heißt: Die
**geprüften** Betreiberangaben des lokalen Bauprodukts sind nach M1–M7
konsistent. Es beweist weder die tatsächliche Herkunft noch die Live-Ausgabe,
die vollständige Wirkung auf Fremdplattformen oder die Anbieterpflicht.

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
   * **Feed:** `curl -s https://franksfinanzcheck.de/index.xml` muss den
     Kanal-Verweis und für jedes relevante Item die passenden Angaben zeigen:
     `rel="describedby"`, ggf. `ffki:ai-generated`,
     `ffki:ai-generated-scope` sowie bei belegter Bildart `media:credit` am
     richtigen Medium. Ein Item muss eindeutig zu seinem eigenen Link und der
     gebauten Seite gehören. Bei deklariertem KI-Text/-Cover steht außerdem
     früh in `description` eine lesbare Zielartikel-/Cover-Angabe, nach einem
     vorhandenen `*Werbung |`.
   * **Pinterest:** Die RSS-Anbindung und drei direkte API-Pfade sind getrennt
     zu prüfen. Der Feed-Namensraum ist eine Eigenangabe; ob Pinterest ihn oder
     die Beschreibung übernimmt und tatsächlich anzeigt, ist **nicht belegt**.
     Nach Integration einen geeigneten Test-Pin auf der Plattform selbst
     prüfen (Ziel-URL, vollständige Beschreibung, Werbe- und KI-Hinweise,
     verwendetes Bild), Ergebnis/Revision/Zeit dokumentieren. API-Tests prüfen
     nur den ausgehenden Payload. Das `pin_image` und andere Social-Bilder
     können vom Artikel-Cover abweichen; ihre Herkunft und erhaltene Metadaten
     sind eigenständig zu bewerten. Ungültiges/mehrdeutiges Frontmatter oder
     eine fehlende bzw. positive Deepfake-Prüfung eines deklarierten KI-Covers
     blockieren den direkten Versand. Bei dokumentierter KI-Politur kennzeichnet
     der Social-Autopilot den Pin-Text separat und blockiert bei Überlänge,
     statt Hinweise abzuschneiden; die anderen beiden Publisher kürzen Prosa
     und erhalten den Hinweis am Anfang. Das bloße Feld `deepfake: false`
     beweist noch keine tatsächliche Prüfung des Bildes.
4. Für jedes tatsächlich deklarierte KI-Cover Einzelansicht, Listenansicht,
   Quelldatei und alle relevanten Social-/OG-Ausgaben prüfen. Original und
   live ausgelieferte Datei byteweise vergleichen; getrennt Signatur bzw.
   Wasserzeichen mit geeignetem Werkzeug prüfen. **Ebenso die Ableitungen:**
   Jedes öffentlich erreichbare AVIF/WebP/JPEG-Geschwisterbild eines
   deklarierten KI-Originals muss die Markierung tragen oder darf gar nicht
   erst erzeugt worden sein (Regel M6, `scripts/image_optimizer.py --check`).
   Keine Prüfung behaupten, wenn kein passendes KI-Cover vorliegt.
5. Ergebnis mit URLs, Zeit, Revision, Testdaten, Tool und offenen Abweichungen
   dokumentieren. Der formale Abschlussweg und seine Grenzen stehen in §5.

## 5. Gesicherter Fristabschluss (#1028)

**Der Arbeitsstand ist nicht live.** Die ältere Beschreibung in Issue #1028
empfahl einen unbedingten `erledigt`-Aufruf; der Hinweis wurde am 12.11.2026
im Issue berichtigt. Vor Integration dieses Schutzes ist der bisherige
Workflow weiterhin nicht nachweisgebunden. Nicht starten, solange Anbieter-,
Bild-, Register- oder Live-Nachweise fehlen. Issue und Fristenstatus bleiben
offen. Eine fachkundige Prüfung bleibt vorbehalten.

### 5.1 Tatsächliche Nachweise vorbereiten

1. Für **jedes tatsächlich eingesetzte** System nach §1 eine konkrete Version,
   Anbieter, eigene Rolle, Inverkehrbringung und eine belastbare schriftliche
   Markierungs-/Erkennungsauskunft dokumentieren. Liegen sie nicht vor, bleibt
   der Abschluss gesperrt. Technische Tags des Blogs sind kein Ersatz.
2. Bild- und Registerentscheidungen nach §§2–3 für alle realen Ausspielungen
   dokumentieren. Die Wache behandelt gegenwärtig **jeden** Eintrag unter
   `menschlich` als ungeklärt; ein geschlossenes Register erfordert für jeden
   Fall eine belegte Einzelfallentscheidung. Nach einer echten Prüfung können
   z. B. belegte maschinelle Texte sachgerecht gekennzeichnet oder tatsächlich
   redaktionell geprüfte Texte mit einem zutreffenden Prüfblock versehen werden.
   Erst dann den geklärten Eintrag und seinen Zustand bewusst gemeinsam
   berichtigen und reviewen. Ein bloßes Entfernen ist kein Herkunftsbeweis.
   `ki_kennzeichnung_gate.py --gate`, `ki_provenienz_gate.py --wache`,
   `ki_bild_markierung.py --gate` und das Cover-Gate müssen passend zur
   tatsächlichen Verwendung ohne offene Befunde sein.
3. Die integrierte Änderung veröffentlichen. Einen **erfolgreichen gesamten**
   Deploy-Lauf auf `main` abwarten, dessen Build- und Pages-Job im selben
   Workflow-Versuch erfolgreich sind und der finale Cover- und Provenienz-Gates
   vor dem offiziellen Pages-Artefakt enthält. Danach die live ausgelieferten
   Seiten, Feed, Tonspur und Bilder sowie Pinterest gemäß §4 prüfen und
   Ergebnisse mit UTC-Zeitpunkt und URLs festhalten. Keine fehlende
   Plattformprobe oder Wasserzeichenprüfung als
   bestanden ausgeben. `head_sha` ist die Ausgangsrevision des Deploy-Laufs;
   mögliche Heilungen im Lauf können das Artefakt ändern. Sie ist **kein**
   kryptografischer Hash des ausgelieferten Artefakts.
4. Für die folgenden Schritte nur redigierte, freigabefähige Nachweise unter
   `docs/ki-vo-abschluss/` ablegen (einzelne Dateien höchstens 900.000 Bytes).
   Das öffentliche Repository enthält **keine** Secrets, personenbezogenen
   Rohdaten oder vertraulichen Anbieterantworten. Falls Originale nicht
   veröffentlicht werden dürfen, eine geprüfte Zusammenfassung mit Datum,
   Herkunft und nachprüfbarem Verweis/Hash der intern verwahrten Originale
   verwenden; diese müssen für die fachliche Prüfung tatsächlich existieren.
   Der Ordner ist Dokumentation, kein Hugo-Content. Jeder Dateihash bindet nur
   diese Dateien, nicht die Wahrheit einer Behauptung darin.

### 5.2 Belegmanifest und ausdrückliche Freigabe

Die Datei `docs/ki-vo-abschluss/abschluss.json` **erst nach wirklicher Prüfung**
anlegen. Das folgende Muster ist kein Beleg; alle Platzhalter müssen ersetzt,
alle verwendeten Systeme vollständig ergänzt und alle referenzierten Dateien
mit ihrem SHA-256 eingetragen werden. Die UTC-Zeitpunkte müssen in der Folge
Deploy-Ende → Live-Abnahme → Betreiberfreigabe liegen.

```json
{
  "frist_id": "ki-vo-kennzeichnung-bestand",
  "systeme": [{
    "name": "<Produkt>", "version": "<konkrete Version>",
    "anbieter": "<Anbieter>", "rolle": "betreiber",
    "inverkehrgebracht_am": "<YYYY-MM-DD>",
    "nachweis": {"datei": "docs/ki-vo-abschluss/anbieter.md", "sha256": "<SHA256>"}
  }],
  "bildinventar": {"datei": "docs/ki-vo-abschluss/bilder.md", "sha256": "<SHA256>"},
  "registerpruefung": {"datei": "docs/ki-vo-abschluss/register.md", "sha256": "<SHA256>"},
  "deploy": {"run_id": 1, "deployment_id": 1, "head_sha": "<vollständiger SHA>"},
  "live_abnahme": {
    "zeitpunkt": "<YYYY-MM-DDTHH:MM:SSZ>", "pruefer": "<Name>",
    "url": "https://franksfinanzcheck.de/",
    "kanaele": ["seite", "feed", "tonspur", "bild", "pinterest"],
    "nachweis": {"datei": "docs/ki-vo-abschluss/live.md", "sha256": "<SHA256>"}
  },
  "betreiberfreigabe": {
    "zeitpunkt": "<YYYY-MM-DDTHH:MM:SSZ>", "name": "<Name>",
    "github_login": "frank-hartung", "buendel_sha256": "<Bündel-SHA256>",
    "nachweis": {"datei": "docs/ki-vo-abschluss/freigabe.md", "sha256": "<SHA256>"}
  }
}
```

`rolle` ist je System `betreiber`, `anbieter` oder `beides`. Dateihashes mit
`sha256sum <Datei>` ermitteln. Der Bündel-Hash umfasst das kanonische JSON
**ohne** den Block `betreiberfreigabe` und lässt sich nach dem Ausfüllen aller
anderen Felder berechnen:

```bash
python3 - <<'PY'
import json
from pathlib import Path
from scripts.ki_frist_freigabe import buendel_sha256
beleg = json.loads(Path('docs/ki-vo-abschluss/abschluss.json').read_text(encoding='utf-8'))
print(buendel_sha256(beleg))
PY
```

Der Betreiber prüft die echten Unterlagen und Ergebnisse, erklärt seine
Freigabe **ausdrücklich** in der UTF-8-Datei `freigabe.md` und nennt darin
Bündel-Hash, GitHub-Konto `frank-hartung` und denselben UTC-Zeitpunkt wie im
Manifest. Deren Datei-SHA danach im Manifest eintragen. Ändert sich ein
Bündelfeld, muss die Freigabe neu geprüft und erteilt werden. Die
formale Hashprüfung kann die Echtheit der Unterlagen oder die fachliche
Beurteilung nicht feststellen.

### 5.3 Review und Workflow

Manifest und redigierte Nachweise geprüft nach `main` integrieren. Der
Docs-Ordner ist im bestehenden Deploy-Gate als Dokumentation ausgenommen;
sind zugleich Site-/KI-Pfade seit dem abgenommenen Deploy geändert oder läuft
noch ein regulärer **oder Notfall-Deploy**, blockiert der Abschluss. Beide
Workflows werden über alle Branches betrachtet: Der Notfall-Workflow checkt
auch bei Dispatch von einem anderen Ref `main` aus. Ein neueres Pages-
Deployment, unabhängig von dessen Ref, verdrängt die abgenommene Fassung.
Dann Auslieferung abwarten, bei Bedarf neu regulär deployen und live abnehmen
sowie Manifest und Freigabe aktualisieren. Der Vergleich ist bewusst
konservativ; der Deploy kann selbst Heilungscommits enthalten. Bei unklarem
Vergleich oder GitHub-Ausfall bleibt die Frist offen.

**Erst danach** startet der freigebende Repository-Inhaber `frank-hartung`
Actions → „Fristen-Check (Recht)“ auf `main`, ohne `nur_scan`, mit der
Eingabe `erledigt=ki-vo-kennzeichnung-bestand`. Die Beschränkung auf das
Inhaberkonto ist eine technische Betriebsvorgabe, keine Identitätsprüfung des
Unternehmens oder Rechtsberatung. Andere Fristen sind davon unabhängig.

Der erste Job prüft Belege und Identität und speichert nur eine **Vormerkung**.
Ein separater Testjob muss im selben Workflow-Versuch einschließlich seines
Testschritts grün sein. Der KI-Freigabejob prüft anschließend erneut die
Dokumente, den Deploy, wartende Deploys und Register. Code, Test, Kalender,
Register und Wachzustand müssen zum tatsächlich getesteten Dispatch-Stand,
zum Checkout **und** zum aktuellen `main` passen. Er prüft die Identität von
**#1028**, pusht den Erledigt-State und liest State und Belege wieder von
`main`. Unmittelbar vor dem Close kontrolliert er `main` und Deploys nochmals;
danach bestätigt ein Issue-Readback den Close. War #1028 bereits geschlossen,
meldet der Lauf dies ausdrücklich und schließt nicht ein zweites Mal; die
vollständigen Nachweisprüfungen sind trotzdem nötig.

**Wiederanlauf und Störungen:** Ein einzelnes `erledigt_am` ist kein Abschluss.
Der zweite State-Push kann vor dem abschließenden Issue-Readback bereits dieses
Feld enthalten. Bricht der Lauf dort ab, ist der rohe JSON-Wert daher bis zur
nächsten Auswertung **nicht als bestätigter Abschluss zu interpretieren**:
Der Fristen-Check prüft den vollständigen Workflow und verschiebt unbestätigte
Erledigungsfelder in `ki_abschluss_unbestaetigt`. Bei vorübergehendem
API-Ausfall kann er eine identische Quittung nach erfolgreicher erneuter
Prüfung und bestätigt geschlossenem Issue wiederherstellen; er schließt ein
Issue dabei nie automatisch. Wird #1028 nach einem bestätigten Abschluss
wieder geöffnet oder ist seine Identität bzw. sein Zustand nicht messbar,
quarantänisiert der nächste aktive Issue-Check die Erledigt-Felder und meldet
Handlungsbedarf. Andere Fristen dürfen #1028 auch bei fehlerhafter Zuordnung
nicht schließen oder kommentieren; ungültige Nummern und URL-Aliase werden
als Fehler gemeldet. Ein bewusst wieder geöffnetes Issue nicht automatisch
schließen; ein erneuter vollständiger Abschluss erfordert menschliche Prüfung.
Einen abgebrochenen Abschluss und den Issue-Zustand prüfen, ggf. Deployment,
Live-Abnahme und Betreiberfreigabe aktualisieren, dann den **vollständigen**
manuellen Fristen-Workflow erneut starten. Ein bloßer Wiederanlauf nur
fehlgeschlagener Jobs kann wegen der Bindung an die jeweilige
`run_attempt`-Nummer gesperrt sein. GitHub dokumentiert die steigende
[Versuchsnummer](https://docs.github.com/en/actions/reference/workflows-and-actions/variables#default-environment-variables)
und den [Job-Filter `latest`](https://docs.github.com/en/rest/actions/workflow-jobs#list-jobs-for-a-workflow-run).
Die API-Felder wurden zusätzlich lesend an einem [öffentlichen Lauf mit zwei
Versuchen](https://github.com/actions/runner/actions/runs/43082958818) geprüft.
Fehlende, unvollständige oder versuchsübergreifende Jobs blockieren; das ersetzt
keine Attestierung des Runners. Wird ein belegter Deploy-Lauf nachträglich nur
teilweise wiederholt, kann die spätere Prüfung vorsorglich unbestätigt werden.
Ein bereits geschlossenes Issue mit unbestätigter Quittung wird nicht blind
wieder geöffnet: der Lauf meldet einen Fehler zur menschlichen Klärung. Wird
#1028 ohne Abschluss oder Vormerkung
vorzeitig geschlossen, öffnet der Fristen-Check genau dieses identifizierte
Issue wieder; nicht messbare oder widersprüchliche Issue-Zustände werden rot
statt durch ein Ersatz-Issue kaschiert. Andere Fristen werden separat
verarbeitet und ihr State vor dem Fehler gesichert.

Fehlt der KI-Kalendereintrag oder sind Titel, Fälligkeit, Einmaligkeit,
30-Tage-Erinnerung oder Eskalationsstufen beschädigt, bleibt der 02.12.2026
sichtbar und der Abschluss gesperrt. Auch die Provenienz-Wache rechnet bei
fehlender, uneindeutiger oder verschobener Frist mit dem Schutzdatum, meldet
zugleich einen Werkzeugfehler und überschreibt den Wachzustand nicht. Eine
tatsächlich neue Rechtslage erfordert eine bewusst reviewte Änderung von
Kalender **und** gemeinsamem Schutzvertrag in `scripts/ki_provenienz.py`.
Ein `--dry-run` schreibt weder Report noch State und postet nichts.

Die GitHub-Readbacks und das Issue-Close sind nicht atomar; auch nach dem
letzten Fence kann ein paralleler Push oder Deploy dazwischen eintreten.
Insbesondere bleibt `notfall-deploy.yml` für dringende Rechts- und
Sicherheitskorrekturen ein bestehender **Ausnahmeweg ohne diese KI-Gates**.
Er kann später die abgenommene Fassung ersetzen; Abschluss und Gates sind
keine dauerhafte Sperre dieses Wegs. Nach einem solchen Deploy Provenienz und
alle relevanten Kanäle unverzüglich gesondert prüfen und Abweichungen
beheben. Der Ausgangs-SHA beweist nicht den Inhalt eines durch Heilungen oder
Rebase veränderten Build-Artefakts. Änderungen während der Abnahme vermeiden;
bei Zweifel Live-Abnahme und Freigabe erneut prüfen. Die Wache bleibt auch nach
einem Abschluss aktiv. Git-Review und menschliche Aufsicht sind nicht durch
die Formalkontrollen ersetzbar.

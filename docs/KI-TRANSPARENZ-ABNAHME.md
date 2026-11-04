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
```

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

## 4. Live-Abnahme nach Integration

1. Integritäts-Lock mit vollständiger Historie durch den Betreiber prüfen und
   nötige Freigabe der geschützten Generatoränderung dokumentieren. Erfolgreiches
   offizielles Pages-Deployment und ausgelieferte Revision prüfen; ein grüner
   lokaler Build oder `gh-pages` allein genügt nicht.
2. Eine bekannte KI-Textseite mit und eine ohne redaktionelle Freigabe im
   Browser samt Screenreader/ohne JavaScript prüfen: deutlicher Hinweis am
   Artikelanfang; keine falsche Freigabe. Eine nicht gekennzeichnete Seite
   gegen das tatsächliche Register und ihre Herkunft prüfen.
3. Für jedes tatsächlich deklarierte KI-Cover Einzelansicht, Listenansicht,
   Quelldatei und alle relevanten Social-/OG-Ausgaben prüfen. Original und
   live ausgelieferte Datei byteweise vergleichen; getrennt Signatur bzw.
   Wasserzeichen mit geeignetem Werkzeug prüfen. Keine Prüfung behaupten,
   wenn kein passendes KI-Cover vorliegt.
4. Ergebnis mit URLs, Zeit, Revision, Testdaten, Tool und offenen Abweichungen
   dokumentieren. Erst nach Betreiberfreigabe, Nachweisen und ggf. juristischer
   Prüfung den Workflow „Fristen-Check (Recht)“ mit
   `erledigt=ki-vo-kennzeichnung-bestand` ausführen.

# KI-VO: Tondatei, schema.org und Interaktions-Offenlegung (#1028)

**Datum:** 13.11.2026 · **Frist-ID:** `ki-vo-kennzeichnung-bestand` (02.12.2026)
**Ebene:** Technik + Vertrag · keine Rechtsberatung
**Vorakten:** `KI-VO-MASCHINENLESBAR-1028-KANALTREUE-DAUERWACHE-HIGHEND-2026-11-07.md`,
`KI-VO-MASCHINENLESBAR-1028-DAUERHEILUNG-HIGHEND-2026-11-05.md`
**Nachtrag im Report:** `RECHT-UPDATE-REPORT.md`, Eintrag 2026-11-13

## Befund

Die Vorakte vom 07.11.2026 schloss mit sieben Kanälen und einem grünen Gate.
Am 13.11.2026 wurde nicht der Bericht gelesen, sondern **jeder Weg
durchgegangen, auf dem ein Inhalt das Haus verlässt**. Drei Kanäle fehlten –
und zwar genau die, die eine Prüfung der Seite nie sieht:

1. **Die Tondatei.** 115 Seiten kennzeichnen die maschinelle Vorlese-Stimme
   sichtbar (Chip, `aria-describedby`, SR-Satz) und maschinenlesbar (Meta,
   scope, Feed). Die ausgelieferte MP3 enthielt **keine einzige**
   Herkunftsangabe. `ff_voice_audio.py` schrieb die Datei, `audio_coverage_check.py`
   zählte sie, `spam_guard` prüfte sie – keiner fragte, ob in ihr steht, dass
   eine Maschine spricht. Für Bilder war dieser Weg am 05.11.2026 geschlossen
   worden (`ki_bild_markierung.py`, XMP/IPTC), für Ton nie. Das ist der
   einzige Kanal, der die Seite **physisch verlässt**.
2. **Das JSON-LD.** `creditText` sagte, *dass* KI beteiligt war. Welcher Art
   das Titelbild ist (`trainedAlgorithmicMedia`), stand in der Bilddatei und im
   `<img>`-Attribut – aber nicht im schema.org-Markup.
3. **Der Assistent.** Der Worker schickte zu jeder Antwort `hinweis` und
   `ki: true` im JSON-Körper. Der Client las das Feld **nie**: `data.hinweis`
   kam in `static/premium/ki-assistent.js` nicht vor. Der Dialog begrüßte mit
   „Hallo! 👋 · Kostenlose Finanz-Fragen", als wäre ein Mensch am anderen Ende.

Punkt 3 wiegt rechtlich am schwersten, weil **Art. 50 Abs. 1 KI-VO seit
02.08.2026 ohne Übergangsfrist** gilt. Die Nachfrist bis 02.12.2026 betrifft
ausschließlich Abs. 2 (Markierung am Werk) und ausschließlich Systeme, die vor
dem 02.08.2026 in Verkehr kamen.

## Heilung

### Kanal 9 – Ton in der Datei (`scripts/ki_audio_markierung.py`, neu)

Schreibt die Herkunft in den Container, ohne ein Sample neu zu kodieren:

| Container | Angabe | Wo |
|---|---|---|
| MP3 | `TXXX:IPTC:DigitalSourceType` | ID3v2.3/v2.4, Version der Datei wird **erhalten** |
| MP3 | `TXXX:AISystemUsed`, `TXXX:Provenance`, `TXXX:Software` | ebenda, vor den fremden Frames |
| WAV | `ICMT` (Hinweis + Vokabularwert), `ISFT`, `IENG`, `ISBJ` | eigener `LIST/INFO`-Chunk am Dateiende |

Fünf Eigenschaften, jede einzeln geprüft:

1. **Kein Neukodieren.** Die Audiodaten sind vor und nach dem Schreiben
   byteweise gleich – inklusive des Null-Paddings, das `ffmpeg` in den ID3-Tag
   legt (wer es wegwirft, verschiebt den ersten MPEG-Frame).
2. **Fremdes bleibt fremd.** Der `TSSE`/`Lavf…`-Frame des Encoders, Titel,
   Künstler und jeder weitere Frame bleiben an ihrem Platz. Nur die vier
   eigenen Namen werden ersetzt.
3. **Widerspruch wird nicht überschrieben.** Steht bereits eine **andere**
   Erzeugungsart in der Datei, ist das Ergebnis `blockiert` – erst `--force`
   ersetzt sie. Dieselbe Regel wie beim Bildkanal.
4. **Bytegenau umkehrbar.** `--entfernen` stellt die Ausgangsdatei her, auch
   bei der ID3v2.4-Kopfzeile, die `ffmpeg` selbst schreibt (Syncsafe-Größen,
   Erhalt der Version).
5. **Ohne Beleg keine Behauptung.** Markiert wird nur, wenn
   `<stem>.track.json` die Spur als maschinell erzeugt belegt (`engine`), und
   nur, wenn die Angabe in der Datei zur Angabe im Beleg passt. Eine
   Abweichung ist ein Befund, keine stille Korrektur.

Verankert an drei Stellen, damit die Markierung nicht von einem zweiten Befehl
abhängt: `ff_voice_audio.py` schreibt sie direkt nach der Endkontrolle
(`setze_tonmarkierung`), `deploy.yml` schreibt und prüft sie am gebauten
Bestand, `ki_provenienz_gate.py` (M3) misst sie am ausgelieferten Baum.

### Kanal 8 – schema.org `digitalSourceType`

`layouts/_partials/schema_article.html` setzt am Cover-`ImageObject`
`digitalSourceType` = `https://schema.org/TrainedAlgorithmicMediaDigitalSource`
bzw. `…CompositeWithTrainedAlgorithmicMediaDigitalSource` – **nur** wenn
`cover.ki_pruefung.digital_source_type` einen der beiden IPTC-Werte trägt.
Kein Wert, kein Feld. An `ai_generated` gehängt wäre es eine Erfindung über die
Bildherkunft.

**Stand heute:** 0 von 115 Artikeln deklarieren eine Erzeugungsart ihres
Titelbilds. Das Feld steht deshalb **nirgends** – das ist der richtige Befund.
Nachgewiesen wurde der Kanal mit einer kontrollierten Probe (Frontmatter eines
Artikels mit `trainedAlgorithmicMedia`, Hugo-Build): genau **eine** Seite trug
die Angabe, keine andere; Probe danach zurückgenommen.

### Kanal 10 – `llms.txt`

`scripts/generate_llms_txt.py` erzeugt den Abschnitt „Woher diese Inhalte
kommen (KI-Kennzeichnung)": Text, Bild, Ton, Assistent, was diese Angaben
**nicht** sind (Betreiber-Erklärung, kein Herkunftsbeweis, keine
Anbieterpflicht) und die Bitte, die Kennzeichnung beim Zitieren mitzuführen.
Das ist der Kanal für KI-Antwortmaschinen – also genau die Zielgruppe, die
Art. 50 Abs. 2 im Blick hat.

### Kanal 11 – Interaktions-Offenlegung (Art. 50 Abs. 1)

| Ort | Was |
|---|---|
| `layouts/_partials/ki_assistent.html`, `layouts/shortcodes/ki_assistent.html` | Satz im Dialogkopf („Antworten erzeugt ein KI-System – kein Mensch."), Link auf `/impressum/#ki-hinweis` in der Fußzeile |
| `assets/css/extended/ki-assistent.css` | eigener Stil: `--primary` in voller Deckkraft, abgesetzt durch Linie – **nicht** `--secondary` + `opacity` wie die Fußzeile |
| `static/premium/ki-assistent.js` | zeigt `data.hinweis` aus der Antwort unter der Antwort (vorher: Feld existierte, wurde nie gelesen) |
| `cloudflare/ki-assistent/worker.js` | HTTP-Kopfzeile `ai-generated: true; …; ai-act=art-50-1` in `corsHeaders` – also auf **jedem** Antwortpfad, auch 4xx/429 |
| `scripts/ki_assistent_gate.py` | neue Regel **KA11** prüft alle vier Orte, inkl. Sabotageprobe |

**Fail-closed:** Die Offenlegung hängt am selben Schalter wie das Widget. Ist
kein Endpoint gesetzt, erscheint kein Dialog – und keine Offenlegung für etwas,
das es nicht gibt. Ist er gesetzt, erscheinen beide. Das Impressum behauptet
weder einen laufenden Chatbot noch dessen Abwesenheit; es beschreibt den
ausgelieferten Stand und nennt ausdrücklich, dass eine fehlende Schaltfläche
„derzeit nicht eingebunden" bedeutet. Die Formulierung bleibt in beiden
Zuständen wahr.

## Dauerhaft gesichert

| Wache | Prüft | Sabotageprobe |
|---|---|---|
| M3 (`ki_provenienz_gate.py`) | Herkunft in **jeder** ausgelieferten Tonspur, am Bauprodukt `public/audio/articles` | unmarkierte Spur → 1 Fund; nach `--write` → 0 Funde |
| M9 (`ki_provenienz_gate.py`) | `llms.txt` trägt den Kennzeichnungs-Abschnitt mit vier inhaltlichen Ankern, zeilenumbruch-tolerant, plus Drift gegen den Generator | Abschnitt entfernt → Fund; „Herkunftsbeweis" ersetzt → Fund |
| KA11 (`ki_assistent_gate.py`) | Offenlegung sichtbar (Partial + Shortcode), gestaltet, im Client angezeigt, im Worker als Kopfzeile | `data-ff-ki-chat-label` entfernt → erkannt |
| `node --test` (Worker) | Kopfzeile auf Erfolgs- **und** Fehlerpfad, `hinweis` im Körper | – |
| `test_ki_audio_markierung.py` | Rundlauf, Idempotenz, Fremdschutz, Bytegleichheit, `--entfernen`, Sidecar-Gate, Gate-Vertrag, Encoder-Proben | eigene Frames nicht aussortiert → 2 Tests rot; Padding verworfen → 1 Test rot |

Alle Sabotageproben wurden ausgeführt und danach zurückgesetzt. Eine Probe war
zunächst **blind** (sie zählte die UTF-16-kodierte Frame-Beschreibung mit
`latin-1` und fand immer 0); sie wurde korrigiert, danach schlug sie zu.

**Zwei Befunde aus den Sabotageproben, die den Code verbessert haben:**

* Der Marker verweigerte das Ersetzen einer **anderen** Erzeugungsart auch mit
  `--force` nicht korrekt – jetzt `blockiert` ohne, `ersetzt` mit `--force`.
* Die M9-Prüfung war zuerst eine Layout-Wache: Ein Satz, der über zwei Zeilen
  umbrochen war, galt als fehlend. Jetzt wird über normalisierte Leerzeichen
  verglichen (Inhalt statt Formatierung).

## Prüfung (Hugo 0.168.0 extended, PyYAML, Pillow, ffmpeg 9.0.2, mutagen)

| Messung | Ergebnis |
|---|---|
| `ki_provenienz_gate.py --gate` | **115/115** gebaute Seiten, 19 Abschnitte, 50 Feed-Items, 0 Tonspuren im Lauf, **0 Funde** |
| `--gate --source-only` | 19 Abschnitte, 0 Funde, Exit 0 |
| `--selftest` | **15** Szenarien grün (neu: M9 fehlend, M9 überzogen) |
| `ki_assistent_gate.py --selftest` | grün, inkl. KA11-Probe |
| `ki_assistent_gate.py` | 10 bereit, 1 Warnung (KA1: Endpoint nur via Shortcode – bewusst kein Default), 0 defekt |
| `node --test cloudflare/ki-assistent/test/worker.test.mjs` | **20/20** |
| `unittest test_ki_audio_markierung` | **16/16** (4 Encoder-Proben mit echtem `ffmpeg`) |
| `unittest` KI-Suiten (7 Module) | **44/44** mit Hugo im Pfad |
| `ki_audio_markierung.py --selftest` | Exit 0 |
| `ff_voice_audio.py --selftest` | 123/123 |
| `generate_llms_txt.py --check` | aktuell (nach Neuerzeugung) |
| `blustradius_register.py --check` | **88** Schritte erklärt (vorher 87) |
| `workflow_vertrag_wache.py --gate` | 103 Workflows, V1–V7 erfüllt |
| `trigger_wache.py --check` | 103 Workflows, 0 Befunde |
| `entity_marken_gate.py --gate` | 0 Fehler, 0 Warnungen |
| Hugo-Build | 115 Seiten, kein WARN/ERROR |

## Offen

Unverändert offen und **nicht** technisch heilbar (kein Punkt ist heilbar, ohne
dass ein Mensch eine Tatsache belegt):

1. **Anbieter-Inventar und schriftliche Bestätigung** zur Markierung nach
   Art. 50 Abs. 2 (Betreiber).
2. **Herkunft der Titelbilder.** Deshalb steht `digitalSourceType` im JSON-LD
   derzeit nirgends; der Kanal wartet auf Belege, er ist nicht lückenhaft.
3. **12 ungeklärte `menschlich`-Einträge** im Register (14.08.–03.09.2026).
4. **Live-Abnahme** nach `docs/KI-TRANSPARENZ-ABNAHME.md` §4, jetzt um vier
   Kanäle erweitert (Tondatei mit fremdem Leser, schema.org, `llms.txt`,
   Assistent in beiden Zuständen).
5. **Betreiberfreigabe** (`erledigt=ki-vo-kennzeichnung-bestand`). Issue #1028
   wird erst nach Merge, Deploy und Live-Abnahme geschlossen – nicht durch
   diesen Eintrag.

## Was diese Ebene nicht ist

Kein Herkunftsbeweis, kein Wasserzeichen, keine C2PA-Signatur und keine
Erfüllung der Anbieterpflicht. Ein grünes Gate heißt: Die Betreiberebene ist
vollständig und widerspruchsfrei **ausgeliefert**. Es heißt nicht: Die Herkunft
ist bewiesen. `ai_generated: false` erzeugt bewusst kein Signal – die
Abwesenheit einer Angabe ist keine Behauptung „rein menschlich".

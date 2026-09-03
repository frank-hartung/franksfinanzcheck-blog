# KURZFASSUNG-HIGHEND-REPORT — Kurzfassung auf Verlagshaus-Spitze (v4)

Datum: 03.09.2026 · Kerndateien: `static/premium/ff-reader.js` (v4), `layouts/_partials/reader_toolbar.html`,
`assets/css/extended/ff-reader.css`, Wachen: `scripts/summary_engine_check.js` (neu, 26 Prüfungen) und
`scripts/reader_toolbar_check.py` (erweitert).
Ziel: Die Funktion „Kurzfassung“ entspricht der **vollständigen Kurzfassung-Funktion von Verlagshäusern**
(Capital, WirtschaftsWoche, Die Zeit) – vollautomatisch, ohne Tracking, ohne Regler – und übertrifft deren
Niveau in der redaktionellen Struktur.

## 0. Was v4 neu macht (aufbauend auf v3)

| Bereich | v3 | v4 (Verlagshaus-Spitze) |
|---|---|---|
| Kurzantwort | `kurzantwort`/Description oder 1. Absatz | **Redaktionelle Kurzantwort-Wahl**: `kurzantwort` > Description > inhaltlich stärkste Einstiegspassage (Signal-Ranking, Szenen-Einstiege wie „Stell dir vor …“ werden ausgeschlossen) |
| Kernaussagen | H2-Titel + 1. Satz | **3–5 redaktionell gerankte Bullets** (ZEIT „Das Wichtigste in Kürze“): Zahlen-, Spar-, Warn-, Faustregel- und Tipp-Signale, dublettenfrei (Normalisierung + Überlappungs-Schutz), max. 2 je Abschnitt, in Lesereihenfolge, mit **Sprungmarke zum Abschnitt** |
| Zahlen | Satz-Schnipsel mit €/% | **Big-Number-Karten „Auf einen Blick“**: Wert (inkl. „bis zu“, „rund“, Bereiche, „pro/im Monat/Jahr“) + sauberes redaktionelles Label (hängende Verben/Präpositionen entfernt), 2 Zahlen je Satz, dublettenfrei, max. 6 |
| Inhaltsverzeichnis | – | **„In diesem Artikel“**: alle H2 mit Sprungmarke + Abschnitts-Teaser |
| Tabellen | – (nur Extraktion) | **„Tabellen & Übersichten im Fokus“**: Tabellen-Titel (Caption/Überschrift), Spaltenköpfe, erste Zeilen, Zeilenzahl, Sprungmarke zur Originaltabelle |
| Byline/Meta | Lesezeit · Wörter | **Verlagshaus-Byline**: Lesezeit · Wörter · Abschnitte · **Autor · Stand** (aus Frontmatter/`lastmod`) |
| Barrierefreiheit | `<dialog>` + Esc | **Fokus-Falle** (Tab-Zyklus), **Scroll-Sperre**, Fokus-Rückgabe an den Auslöser, Esc, `aria`-verdrahtet (WCAG 2.2 / BITV) |
| Satzsegmentierung | naive Splitter | **Abkürzungs- & zahlenfest** („z. B.“, „d. h.“, „ca.“, „Mio.“, 1.250,50 – kein Fehl-Split) |

## 1. Redaktionelle Extraktions-Engine (Chefredakteur-Standard)

- **Kernaussagen-Ranking (`signalScore`)**: konkrete Zahlen und Währungen/Prozente zählen doppelt,
  Spar-/Warn-/Tipp-/Faustregel-Vokabular (DE & EN getrennt) zählt, kurze Füllsätze und überlange
  Schachtelsätze werden abgewertet, 40–180 Zeichen gelten als ideal. Die Auswahl ist **divers** (max. 2
  je Abschnitt) und **dublettenfrei** (Normalisierung + Bigramm-/Wort-Überlappung > 60 % wird verworfen),
  die Reihenfolge folgt dem Dokument (Lesefluss).
- **Zahlen-Label (`figureFromMatch`)**: Der Wert wird als Einheit erkannt (€, %, kWh, Cent, Mbit/s,
  Monat/Jahr/Tag/Woche inkl. „im/pro/je/per Monat“), das Label aus dem Kontext davor/danach gebildet und
  von hängenden Verben/Präpositionen („kostet oft nur“, „liegt bei“, „spart …“) befreit. Regel-Pfeile
  („Bis 5 Jahre → Vollkasko“) bleiben bewusst bei den Kernaussagen und werden nicht als Zahl missdeutet.
- **Satzsegmentierung (`summarySentences`)**: 40+ Abkürzungen und Tausenderpunkte werden vor der Trennung
  maskiert – „Das kostet z. B. 1.250,50 Euro.“ bleibt **ein** Satz.
- **Kurzantwort (`pickShortAnswer`)**: nutzt die redaktionell gepflegte `kurzantwort` (28 von 29 Posts),
  sonst die Description, sonst die inhaltlich stärkste Passage (Signal-Score); dramaturgische
  Szenen-Einstiege werden nie als Antwort ausgegeben.

## 2. Bedienung wie ein Verlagshaus (vollständige Kurzfassung)

Ein Klick auf **„Kurzfassung“** öffnet einen barrierefreien Dialog mit:

1. **Kopf** – Eyebrow „Kurzfassung“, Artikel-Titel, Schließen-Knopf.
2. **Byline** – Lesezeit · Wörter · Abschnitte · Autor · Stand.
3. **💡 Das Wichtigste in 30 Sekunden** – hervorgehobene Kurzantwort (Signalgelb-Hero).
4. **📌 Die Kernaussagen** – nummerierte Bullets, je mit „Zum Abschnitt ↗“-Sprungmarke.
5. **💶 Auf einen Blick** – Big-Number-Karten (großer Wert + Label).
6. **🧭 In diesem Artikel** – interaktives Inhaltsverzeichnis mit Teaser.
7. **📊 Tabellen & Übersichten im Fokus** – kompakte Tabellen-Highlights mit „Zur Tabelle ↗“.
8. **Fußleiste** – „📋 Kurzfassung kopieren“ (sauber formatierter Klartext) + „Ganzen Artikel lesen →“.

- **Fokus-Falle**: Tab bleibt im Dialog (zyklisch), Esc schließt, der Fokus kehrt zum Auslöser zurück,
  der Seiten-Scroll wird während des Dialogs gesperrt (`lockScroll`).
- **Kopieren**: Klartext-Kurzfassung mit Titel, Quelle (URL), Byline, Kurzantwort, nummerierten
  Kernaussagen, Zahlen und Gliederung – kopierfähig in jede Redaktions-/Notiz-App.
- **DE & EN**: alle Labels zweisprachig, automatisch erkannt (wie beim Vorlesen).
- **Privacy-first**: alles läuft lokal im Browser, keine Netzwerkaufrufe, kein Tracking.

## 3. Robustheit & Kompatibilität

- Dokumenttreue DOM-Wanderung (`walkNodes`) statt fragiler Selektoren – verschachtelungssicher.
- Fallback ohne `dialog.showModal()` (Backdrop + `open`-Attribut) bleibt voll bedienbar.
- `data-ff-skip-read`-Blöcke werden von allen Extraktoren respektiert.
- Kurzantwort/Kernaussagen/Zahlen/TOC/Tabellen sind einzeln abgesichert: fehlt ein Baustein, zeigt der
  Dialog die übrigen (kein leerer Dialog, nur bei komplett leerem Artikel eine redaktionelle Meldung).
- `prefers-reduced-motion` respektiert (bestehende CSS-Regel), Dunkelmodus über CSS-Variablen
  (`--entry`, `--primary`, `--secondary`, `--ff-emerald`, `--ff-yellow`) ohne Sonderfälle.

## 4. Verifikation

| Prüfung | Ergebnis |
|---|---|
| `node --check static/premium/ff-reader.js` | Syntax OK |
| `node scripts/summary_engine_check.js` — Segmentierung, Signal-Ranking, Zahlen (Wert/Label), Kernaussagen (3–5, dublettenfrei, Sprungmarken), Inhaltsverzeichnis, Tabellen, Kurzantwort, Klartext, Byline, I18N | **26/26 grün** |
| `node scripts/reader_engine_check.js` (Vorlesen, Regressionsschutz) | **56/56 grün** |
| `python3 scripts/reader_toolbar_check.py` (A11y-/Highend-Wache, jetzt inkl. Kurzfassung-v4-Tokens + CSS-Klassen) | **alle Gates grün** |
| Real-Content-Test (3 echte Artikel, Markdown→Fake-DOM): Hausrat, DSL-Wechselbonus, Kfz-Vergleich | je 5 Kernaussagen, 6 Zahlen, 10–11 TOC-Einträge, Kurzantwort vorhanden – **solide Ausbeute, keine Crashes** |

Weiterhin keine UI-Änderung am Grundprinzip: kein Regler, keine Stimmen-/Themenwahl, kein
Tastatur-Hinweis – die Kurzfassung arbeitet vollautomatisch und redaktionell strukturiert.

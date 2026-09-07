# Vorlesen · Fehlerkorrektur: „einzelne Wörter werden englisch ausgesprochen"

**Auftrag:** 07.09.2026 · High-End / Profi-Agentur
**Betroffenes System:** FF Voice Studio (Vorlesen) — Studio-Tonspur **und** Browser-Engine
**Status:** ✅ behoben, dauerhaft abgesichert durch 9 Gate-Suiten (1.090+ Prüfungen)

---

## 1 · Der Befund (Warum wurden Wörter englisch?)

Die Vorlese-Funktion sprach bereits mit einem **männlichen, deutschen Nachrichtensprecher**
(Studio: `de-DE-ConradNeural`, Style *serious*; Browser: Conrad → Killian → Florian …)
und jede Äußerung trug bereits `lang = de-DE`. Trotzdem kippten einzelne Wörter
mitten im deutschen Satz auf die **englische Aussprache** — z. B.:

| Geschrieben | Falsch geklungen (Code-Switching) | Richtig (Nachrichtenfunk-Standard) |
|---|---|---|
| Service | „Sör-wiss" (englisches *service*) | **Sörwis** (deutsch) |
| Homeoffice | „Hoam-Offis" (englisches *home/office*) | **Homoffis** |
| Download | „Daun-loud" (englisches *download*) | **Daunloht** |
| Newsletter | „Njus-Letter" (englisches *letter*) | **Njusletter** |
| Live-Stream | „Leif-Strihm" mit englischem Vokal | **Leif Schtrihm** |
| Social Media | „Sou-schall Mi-di-a" | **Soschl Miedia** |

**Ursache:** Moderne mehrsprachige Neuronalstimmen (Edge/Microsoft **und** Google im
Browser) erkennen englisch *geschriebene* Wörter an der Buchstabenfolge und wechseln
**innerhalb des Satzes automatisch die Aussprache-Sprache** — das sogenannte
*Code-Switching*. Das Attribut `lang = de-DE` wirkt nur auf Stimmenwahl und Satzebene;
es **verhindert nicht die automatische Fremdsprachenerkennung der Stimme**.

---

## 2 · Die Lösung (High-End-Verfahren der Sprecherziehung)

Wie im deutschen Nachrichtenfunk mit Fremdwörtern verfahren wird: die Begriffe gehen
in **deutscher Lautschreibung auf das Manuskript**. Die Schreibung lenkt die Stimme
zuverlässig in das deutsche Lautsystem — **ohne** SSML (das die lokale Piper-Stimme
nicht kennt) und ohne sprachliche Code-Wechsel.

Ein **Germanisierungs-Glossar** überführt die Fach- und Markenbegriffe vor der
Synthese:

- **Studio-Tonspur (serverseitig):** `germanize_speech()` in `scripts/ff_voice_backends.py`
- **Browser-Engine (im Gerät):** `germanizeSpeech()` in `static/premium/ff-voice.js`
- **Beide Implementierungen sind wortgleich** und werden durch das
  Paritäts-Gate (`scripts/ff_voice_parity_check.py`) gegeneinander geprüft.

Das Glossar deckt den **echten Wortschatz des Blogs** ab (aus dem Content-Bestand
ermittelt): Technik & Internet (Provider, Router, Browser, Download/Upload, Update,
Cloud, Cookie, Cache, Mesh, Repeater …), Business & Finanzen (Service, Support,
Cashback, Broker, Trading, Leasing …), Sozial/Content (Newsletter, Podcast, Stream,
Social Media, Follower, Hashtag …), Marken/Plattformen (Instagram, YouTube, PayPal,
iPhone …) und mehr als **160 Begriffe inklusive Beugungsformen**.

**Intelligenz der Regelung:**

1. **Längste Muster zuerst** — „Newsletter" gewinnt gegen „News", „Homeoffice" gegen
   „Office".
2. **Automatische Beugung** — Plural/Genitiv-**-s** und schwache Endung **-n**
   („Providers" → „Proweiders", „Services" → „Sörwiss", „Apps" → „Äpps") werden
   automatisch abgeleitet; explizite Formen (z. B. „Cookies" → „Kuckis") haben Vorrang.
3. **Wortgrenzen schützen deutsche Wörter** — „Dienstleistung", „Check24", „Transfer"
   und „Hosting" (bereits Duden-deutsch) bleiben **unangetastet**.
4. **URLs, E-Mails und Datumsangaben sind geborgen** — sie werden vorher in
   Halte-Platzhalter gelegt und nie mitersetzt.

### Die Leseanzeige funktioniert weiterhin wortgenau

Die Stimme spricht „homoffis", markiert werden muss aber das Wort „Homeoffice" im
Artikeltext. Der **Wortuhr-Aligner** schlägt die Sprechschreibung über eine
automatisch aus dem Glossar abgeleitete Brücke (`FOREIGN_SPOKEN`) auf das rohe
Fremdwort zurück — auf beiden Tonpfaden identisch.

### Zusätzliche Härtung der Browser-Stimme

Die Äußerungssprache wird jetzt **an die tatsächlich gebundene deutsche Stimme
festgenagelt** und als kanonisches BCP-47 (`de-DE`, `de-AT`, `de-CH`) ausgegeben.
Damit kann die Engine auch auf Plattformen, bei denen allein die Stimme die
Ausgabesprache bestimmt, nicht mehr auf die System-Stimme zurückfallen.

---

## 3 · Der Premium-Nachrichtensprecher (erzwungen)

Die Stimme ist und bleibt **männlich, ausschließlich Deutsch**, ohne Umschalter:

- **Studio-Tonspur (Vorzugsweg):** `de-DE-ConradNeural` — Microsofts deutsche
  **Newsroom-Stimme** (Kategorie „News & Announcement"), Vortragsstil *serious*.
  Zweite Engine (lokal/offline): Piper `de_DE-thorsten-high`.
- **Browser-Engine (Fallback, sofort verfügbar):** Conrad → Killian → Florian →
  Thorsten → Klaus/Stefan …, gewichtet auf News-/Natural-/Online-Qualität; mit
  Veto gegen jede weibliche und jede fremdsprachige Stimme.
- Es gibt **keinen Sprachumschalter, kein Stimmen-Menü und keine englische Stimme**
  im System. Fremdsprachige Stimmen im Geräte-Katalog sind eine Test-Falle — die
  Regie darf sie unter keinen Umständen wählen.

Damit **alle bestehenden Tonspuren, in denen noch englisch ausgesprochene Wörter
stecken, automatisch neu vertont werden**, wurde die Rezept-Version auf
`ff-voice-2026.09.11` angehoben. Der nächste Deploy-Lauf (`ff_voice_audio.py`)
erkennt den geänderten Fingerabdruck und erzeugt jede Spur neu — danach spricht die
Studiospur durchgehend deutsch. Bis dahin greift automatisch die Browser-Stimme
(nach demselben Germanisierungs-Vertrag).

---

## 4 · Dauerhafte Absicherung (Robustheit auf Agentur-Niveau)

| Gate / Wache | Schützt vor |
|---|---|
| `ff_voice_parity_check.py` (384 Prüfungen) | Auseinanderlaufen von Tonspur und Browserstimme — inkl. **deutsche Aussprache aller Fremdwörter auf BEIDEN Wegen** und der Wortuhr-Brücke |
| `ff_voice_backends.py --selftest` (83) | Aussprache-Regeln, Glossar, Beugung, Stimmen-Kette |
| `ff_voice_audio.py --selftest` (105) | Block-Modell, Fingerabdruck, Stille-Erkennung, Wortuhr |
| `ff_voice_functional_test.mjs` (218) | Vorlesen + Kurzfassung im echten DOM (jsdom) |
| `ff_voice_tts_hardening_test.mjs` (57) | Stumme Engine, rasende Fortschrittsanzeige, verschlucktes `speak()` |
| `ff_voice_repair_test.mjs` (56) | Tonspur-Wache, Fallback, Lazy-Stimmbindung |
| `ff_voice_voice_test.js` (69) | **Stimmen-Regie: männlich, nur Deutsch** — fremdsprachige Kataloge als Falle |
| `ff_voice_toolbar_check.py` (118) | Layout, Barrierefreiheit, Workflow |
| CI `lesehilfen-gate.yml` (täglich 08:20 Uhr + bei jeder Änderung) | Blockiert Deploy bei Regression; Echt-Chromium-Test |

Zusätzlich gibt das Paritäts-Gate jetzt **hart vor**, dass das Glossar und seine
Verdrahtung in beiden Quellen existieren — ein reines Bekenntnis im Kommentar
genügt nicht.

---

## 5 · Geänderte Dateien

- `static/premium/ff-voice.js` — Germanisierungs-Glossar + Regeln, Beugung,
  Wortuhr-Brücke, kanonische `de-DE`-Stimmenbindung, Versions-Bump.
- `scripts/ff_voice_backends.py` — Germanisierungs-Glossar + Compiler,
  `germanize_speech()`, `germanize_spoken_cores()`, Rezept-Version `2026.09.11`,
  Selbsttest-Erweiterung.
- `scripts/ff_voice_audio.py` — Fremdwort-Erweiterung im Wortuhr-Aligner
  (`FOREIGN_SPOKEN`).
- `scripts/ff_voice_parity_check.py` — Fremdwort-Beweisbeispiele (Aussprache +
  Wortuhr) und harte Glossar-Verdrahtungs-Kontrollen.
- `scripts/ff_voice_tts_hardening_test.mjs` — Versions-Erwartung nachgezogen.

**Ergebnis:** Die Vorlese-Funktion spricht fremdgeschriebene Begriffe ab sofort so,
wie es im deutschen Hörfunk üblich ist — **durchgehend Deutsch, in der Stimme eines
professionellen Nachrichtensprechers**, auf allen Geräten und beiden Tonpfaden gleich.

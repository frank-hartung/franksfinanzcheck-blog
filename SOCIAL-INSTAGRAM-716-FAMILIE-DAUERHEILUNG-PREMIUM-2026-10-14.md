# Instagram-Winkel (#716-Familie) und Reserve-Verbrauch – Dauerheilung

**Stand:** 14.10.2026 · **Anlass:** zwei Folgeaufträge aus PR #747
(„Vorbestand – Daten, nicht Code“).

| Auftrag | Ergebnis |
|---|---|
| 1. `content-reserve.yml` soll die Reserve-Entwürfe vom 07./09.10. nachzertifizieren | **Nicht nötig, und gar nicht möglich:** Beide sind seit 14.10. 14:57 UTC **live** (Quote-Nachfüllung, `reserve_published: 2026-10-14`). Ihre Zeilen im Zertifikat waren Verbrauchsreste. Sie sind jetzt **ausgebucht**, ohne Messung und ohne verjüngte Frische. Das Werkzeug unterscheidet Verbrauch künftig von Drift. |
| 2. Instagram-Winkel für `2026-08-26-dns-server-wechseln-…` | **Behoben:** 6 von 6 Winkeln sendbar (vorher 0). Im Bestand ist jetzt jeder Artikel auf Instagram in allen 6 Winkeln sendbar, mit mindestens 4 verschiedenen Captions (vorher eine einzige pro Artikel). |

---

## 1 · Instagram: warum der Ratgeber in keinem Winkel sendbar war

Zwei Ursachen, die sich gegenseitig verstärkt haben:

1. **L7 hielt Fachkürzel für Geschrei.** Die Kurzantwort sagt (richtig):
   „DNS over HTTPS (DoH) oder DNS over TLS (DoT)“. L7 zählte jede
   Großbuchstabenfolge als geschrienes Wort und kam auf **13 % > 12 %**. Das
   ist dieselbe Fehlerklasse wie die beiden #716-Reparaturen vom 12.10.
   (Hashtag-Zahlen in L9, CamelCase-Tags in L7): Ein Falschurteil in einer
   fail-closed-Wache sperrt ausgerechnet die präzisesten Texte aus.
2. **Die Caption ignorierte den Winkel.** `_compose_visual` hat nur die
   Folien abhängig vom Winkel gebaut. Die gesendet wird aber nur die Caption,
   und die war für alle sechs Winkel Wort für Wort gleich. Ein einziges
   Falschurteil hat damit jeden Winkel zugleich getroffen. Das Nachrücken,
   das einen Kanal vor dem Verhungern schützt, lief ins Leere.

### Heilung

**Gate (L7): Fachkürzel brauchen einen Beleg, so wie Zahlen in L9.**
- Als Kürzel zählt, was der Haus-Kanon `tag_casing` (Akronyme, Marken,
  Einheiten) in Großbuchstaben führt **oder** was der Artikel selbst in
  Großbuchstaben schreibt (Titel, Kurzantwort, Beschreibung, Takeaways,
  Keywords, Tags, FAQ).
- Nie als Kürzel zählen Schreiwörter (GRATIS, JETZT, SOFORT …;
  erweiterbar über `meta.gate.schrei_woerter`), Versalwörter mit mehr als
  sechs Buchstaben und Wörter, die der Artikel normal schreibt („Tarif“ im
  Artikel macht „TARIF“ im Beitrag nicht zum Kürzel).
- Geschrei bleibt Geschrei: „DER BESTE DNS DEINES LEBENS“ wird weiter
  blockiert, auch wenn das Kürzel DNS belegt ist. Der Anteil steht jetzt als
  `shouting` in den Kennzahlen.

**Texter: Jeder Instagram-Winkel geht das Thema anders an** (`_visual_winkel`).

| Winkel | Erste Zeile (≤ 125 Zeichen, vor „mehr“) | Körper |
|---|---|---|
| nutzen | Aufhänger | Folgesätze der Kurzantwort |
| zahl | Folgesatz mit Zahl, sonst „Zahl – darum geht es bei …“ | Kontext |
| takeaway | Aufhänger | „Das Wichtigste in Kürze“ als Liste |
| frage | FAQ-Frage des Artikels | FAQ-Antwort |
| mythos | Korrektur aus dem Artikel („weder … noch“, „nicht automatisch“), sonst Pillar-Mythos | Korrektur und Folgesatz |
| karussell | Aufhänger | nummerierte Merkliste „Zum Speichern“ |

Fehlt einem Winkel sein Material, fällt er auf den Nutzen-Text zurück und
erfindet nichts. `karussell` verspricht keine Folien, weil der Adapter ein
Einzelbild sendet. Die Formel „Rechenwege“ steht nur unter Artikeln, die
tatsächlich rechnen. Unter dem DNS-Ratgeber heißt es jetzt „Den ganzen
Ratgeber findest du über den Link in der Bio.“

**Nebenbefunde derselben Prüfung, mitbehoben:**
- `extract_faq` hat **nie** eine Frage gefunden, weil DOTALL fehlte. Der
  Winkel `frage` fiel deshalb auf **jedem Kanal** auf den Titel zurück. Die
  Antwort reicht außerdem nicht mehr in die nächste Frage hinein, und ein
  bloßer Auftakt wie „Nicht zwingend.“ bekommt den begründenden Folgesatz.
- `sentences()` hat Daten zerschnitten („laufen vom 1.“). Ordnungszahlen vor
  Monat oder kleinem Wort und gängige Abkürzungen (z. B., ca., bzw.) sind
  kein Satzende mehr.
- Hashtags halten sich an den Kürzel-Kanon: `#DNSOverHTTPS`, `#DNSOverTLS`
  statt `#DNSOverHttps`/`#DNSOverTls`. Die lokale Liste hat weiter Vorrang,
  bestehende Tags ändern sich nicht.
- Die FAQ zählt als L9-Belegmaterial (sie ist wörtlicher Artikeltext).
  Erfundene Zahlen blockieren weiterhin.

### Wirkung im Bestand (alle Live-Artikel × alle Kanäle × alle Winkel, offline)

| Kanal | min. sendbare Winkel vorher → nachher | verschiedene Captions (min.) vorher → nachher |
|---|---|---|
| **instagram** | **0 → 6** (von 6) | **1 → 4** |
| bluesky | 1 → 5 | 6 → 6 |
| x | 2 → 4 | 5 → 5 |
| threads | 3 → 6 | 5 → 5 |
| mastodon | 5 → 8 | 7 → 7 |
| linkedin, facebook, pinterest, telegram, reddit | unverändert voll | unverändert |

### Dauerhafte Absicherung

- `TestKanaltreue716` (vorher rot) ist grün.
- **Neu:** `scripts/tests/test_social_instagram_winkel.py` (16 Tests):
  Eigenständigkeit der Winkel, keine erfundene Zahl, FAQ-/Mythos-Quelle, keine
  Folien-Versprechen, CTA-Wahrheit, Satzteiler, FAQ-Leser, Hashtag-Kanon.
  Dazu die **Frühwarnung**: je Kanal und Artikel mindestens 2 sendbare Winkel,
  auf Instagram mindestens 3 verschiedene sendbare Captions. Ein Beinahe-Ausfall
  wie Bluesky mit 1 Winkel wird damit rot, bevor ein Kanal verstummt.
- **Neu:** `TestL7Fachkuerzel` in `test_social_gate_l9.py` (9 Tests). Prüft
  beide Seiten des Vertrags: Kürzel mit Beleg passen, Geschrei,
  Schreiwörter, Versalwörter über sechs Buchstaben und normale Artikelwörter
  bleiben blockiert. Dazu der Vorfall-Artikel in allen 6 Winkeln.
- Eine Fixture angepasst (`TestNachruecken716`): Die Gift-Zahl stand dort in
  der FAQ. Weil die FAQ jetzt Belegmaterial ist, steht sie nur noch im
  Aufhänger. Die Absicht des Tests (eine nirgends belegte Zahl blockiert in
  jedem Winkel) bleibt erhalten und wird weiter geprüft.

---

## 2 · Reserve: „Nachzertifizierung“ für Artikel, die schon live sind

**Befund:** `reserve_recert.py --check` meldete beide Zeilen als
`verschwunden` mit dem Hinweis „zählen ohne Nachzertifizierung NICHT mehr zum
Bestand“. `reserve_artifacts.snapshot_findings` meldete „SHA-256 passt nicht
mehr zum Entwurf; Nachzertifizierung nötig“. Beide Meldungen zeigen in die
falsche Richtung: Die Entwürfe sind veröffentlicht. Die Bytes haben sich
geändert, weil die Veröffentlichung `draft: false` gesetzt hat. Eine
Reserve-Messung an einem Live-Artikel würde etwas belegen, das es nicht gibt.
So ist der Folgeauftrag in PR #747 entstanden.

**Heilung (`reserve_recert.py`):**
- Neue Befund-Art `veroeffentlicht` (`draft: false` + `reserve_published`).
  Sie gilt als **planmäßiger Verbrauch, nicht als Drift**: `--check` meldet
  Exit 0 mit Hinweis, und der Satz „NICHT mehr zum Bestand“ fällt dafür weg.
- `--fix` bucht `veroeffentlicht`/`verschwunden` **ohne Messkette** aus
  (`ausbuchen()`): Die Zeile fällt weg, die Zähler werden neu berechnet,
  `generated_at`, `measurement` und jedes `measured_at` bleiben unverändert.
  Die Provenienz steht unter `ausgebucht`. Die Invariante lautet: Eine
  Ausbuchung kann den Bestand nur kleiner rechnen (sonst Abbruch).
- Geänderte oder unzertifizierte Entwürfe brauchen weiter die vollständige
  Messkette (hugo + hunspell). Ohne sie gilt weiter Exit 3, und es wird
  nichts erfunden.

**Daten:** Lokal hat dieses Werkzeug die beiden Zeilen ausgebucht (11 → 9,
`generated_at` und die Messung unverändert). Noch vor dem Zusammenführen hat
der Reserve-Lauf 38616183448 auf `main` (18:35 UTC) dieselben zwei Zeilen
über den alten Pfad entfernt. Dafür brauchte er die vollständige Messkette,
obwohl gar nichts zu messen war. Beim Abgleich wurde deshalb die Fassung von
`main` übernommen; dieser PR ändert keine Zustandsdatei. Ergebnis ist
derselbe Bestand: 9 Zeilen, 9 gate-fertig, Ziel 6. `reserve_recert.py --check`
meldet keinen Drift, und `snapshot_findings` ist leer.

**Neu:** 8 Tests in `test_reserve_recert.py` (`VerbrauchIstKeinDrift`):
Unterscheidung von Verbrauch, Verschwinden und Änderung, bytegleiche Restzeilen,
keine verjüngte Frische, `--check` schreibt nie, Ausbuchung ohne Messkette,
Nachmessung ohne Messkette bleibt Exit 3.

---

## Nachweise

| Prüfung | Ergebnis |
|---|---|
| Gesamtsuite `unittest discover -s scripts/tests` (nach Abgleich mit `main`) | ✅ **3167 Tests, 0 Fehler** (12 übersprungen). Auf `main` vorher rot: `TestKanaltreue716` (instagram) |
| Fokus-Suiten (social × 3, reserve_recert, integrity_guard, reserve_artifacts) | ✅ 214 Tests grün |
| `governance_contract.py` | ✅ alle 36 Regeln |
| `measurement_chain.py --audit-workflows` | ✅ |
| `integrity_guard.py --check` | ✅ (kein versiegelter Kern berührt) |
| `social_preflight.py --selftest` · `reserve_recert.py --selftest` | ✅ |

## Bewusst nicht geändert

- Keine Schwelle bewegt: `max_shouting_ratio` bleibt bei 0,12, L9 bleibt
  streng.
- Kein versiegelter Kern (`tag_casing.py`, `reserve_artifacts.py`). Das TLS-
  Kürzel kommt für Hashtags aus der lokalen Liste des Texters und für L7 aus
  dem Artikelbeleg.
- Kein Workflow verändert und keiner aus dieser Umgebung angestoßen.
  `content-reserve.yml` (Stufe 0c, `--fix --refresh-stale`) bucht künftige
  Verbrauchsreste beim nächsten Lauf selbst aus.
- Nicht in diesem Auftrag enthalten: Auf **X** ist der Nutzen-Winkel bei
  6 Artikeln zu einem Fragment gekürzt („Beim Handytarif-Vergleich 2026
  zahlst …“), das L6 zu Recht ablehnt. Jeder dieser Artikel bleibt in
  mindestens 4 anderen Winkeln sendbar. Das Zeichenbudget des X-Texters ist
  ein eigener Fachkanal.

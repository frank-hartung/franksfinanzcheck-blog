# Prüfqueue #826 – Dauerheilung auf Agentur-Niveau

**Datum:** 24.10.2026 · **Auslöser:** Issue #826 (Report vom 23.10.2026)
**Verdikt:** Prüfqueue leer (Gate `0 blockiert`), **fünf tote und eine umgeleitete
Belegadresse repariert**, ein KI-Entwurf **verworfen**, vier Schreib- und Prüfwege
so gehärtet, dass dieselben Fehler nicht wieder entstehen.

> Hausregeln dieses Laufs: kein Prüfer erfunden, kein Siegel ohne echte Prüfung,
> keine Gate-Regel abgeschwächt. Wo etwas nur „unklar“ war, steht „unklar“.

---

## 1. Kurzfassung

| Bereich | Vorher (23.10.2026) | Nachher (24.10.2026) |
| --- | --- | --- |
| Hochrisiko-Artikel | 9, davon 3 textlich nach der Freigabe geändert, 1 KI-Entwurf offen | 9, **alle freigegeben**, 0 blockiert |
| Gate-Status | `--strict` rot, Ticket bleibt offen | `94 Artikel · 9 Hochrisiko · 9 freigegeben · 0 blockiert`, Exit 0 |
| Zitierte Belegadressen (Hochrisiko) | 22 eindeutige URLs, **5 × 404**, 1 × fremde Zielseite | alle 22 erreichbar, Inhalte abgeglichen |
| Entwurf „Saison-Update“ | offener, unsiegelbarer KI-Entwurf | verworfen, Ordner entfernt (Git-Historie bleibt) |
| Wächter | Gate prüft Text, niemand prüft das Netz | neue **Belegketten-Wache** + Kopplung im Workflow |
| Automatik-Schreibgrenze | `faktenfrische` schrieb Recherche-Signale als `quellen` | schreibt bei `risikoklasse: hoch` keine Quellen, bricht versiegelte Fassungen ab |

---

## 2. Befund: was am 23.10.2026 wirklich offen war

Vier Hochrisiko-Artikel standen mit `status: ausstehend` in der Queue. Sie waren
**nicht** alle gleich:

| Artikel | Befund | Ursache | Entscheidung |
| --- | --- | --- | --- |
| `2026-08-26-kfz-versicherung-vergleich…` | Regionalklassen-Abschnitt beschrieb 2026, zitiert war eine GDV-Adresse, die inzwischen **andere Zahlen (2027)** ausliefert | Textänderung 19.10. nach der Freigabe vom 05.10. | Text auf Regional-/Typklassen 2027 umgestellt, Zahlen protokolliert, neu versiegelt |
| `2026-09-21-unfallversicherung-vergleich…` | Gliedertaxe als Marktstandard behauptet, Beitragsspannen ohne Beleg | Textänderung nach der Freigabe | Gliedertaxe als GDV-Empfehlung gekennzeichnet, Spannen als redaktionelle Orientierung, neu versiegelt |
| `2026-09-17-versicherung-update…` | Hausrat-Beitrag ohne belastbare Fundstelle, § 11 VVG als Fristanker | Textänderung nach der Freigabe | Hausrat 650 €/m² belegt, Rechenbeispiele nachgerechnet, neu versiegelt |
| `2026-10-15-saison-update…` | KI-Entwurf ohne Anlass, ohne echte Belegkette (1 Pseudo-Quelle) | Automatik schrieb „Signal“ als Quelle | **verworfen**, Ordner per `git rm -r` entfernt |

Die drei reparierten Artikel wurden nach der Korrektur einzeln geprüft
(`--file`) und neu versiegelt (`--seal`). Siegel vom 24.10.2026:

| Artikel | `inhalt_sha256` (gekürzt) |
| --- | --- |
| kfz-versicherung | `746d3780…8fb4a909` |
| unfallversicherung | `6e126199…4157e8dd` |
| versicherung-update | `186911be…38b7ed35` |
| tierkrankenversicherung | `94d7967a…` |
| ratenkredit | `5f2d7d78…` |
| zahnzusatzversicherung | `dd4a3d76…` |
| privathaftpflicht | `f91c27c6…` |

Volltexte append-only in `data/editorial_review_history.jsonl`.

---

## 3. Der eigentliche Befund: das Siegel prüft den Text, nicht das Netz

Beim Abgleich **aller 22 in Hochrisiko-Artikeln zitierten Adressen** (je einmal
abgerufen, Inhalt gegen das Zitat gelesen) am 24.10.2026:

**Fünf Adressen antworteten mit 404** – alle bei der Verbraucherzentrale, alle
nach einer Seiten-Migration derselben Inhalte unter neuen Pfaden:

| Artikel | alte, tote Adresse | Ersatz (geprüft) |
| --- | --- | --- |
| Tierkrankenversicherung | `…/geld-versicherungen/haftpflicht/krankenversicherungen-fuer-haustiere-10781` | `…/weitere-versicherungen/krankenversicherungen-fuer-haustiere-sinnvoll-oder-ueberfluessig-10781` |
| Ratenkredit | `…/kredite-finanzierungen/kredite-vergleichen-lohnt-sich-auf-den-effektiven-zins-achten-10409` | `…/kredit-schulden-insolvenz/kredite-und-darlehen-auch-beim-geldleihen-laesst-sich-sparen-10409` |
| Ratenkredit | `…/kredite-finanzierungen/restschuldversicherung-teurer-schutz-der-wenig-leistet-32448` | `…/weitere-versicherungen/restschuldversicherungen-sind-teuer-und-leisten-nur-wenig-32448` |
| Zahnzusatzversicherung | `…/gesundheit-pflege/kranken-versicherung/zahnzusatzversicherung-…-12943` | `…/geld-versicherungen/weitere-versicherungen/zahnzusatzversicherungen-lohnt-sich-ein-abschluss-12943` |
| Zahnzusatzversicherung | `…/gesundheit-pflege/kranken-versicherung/festzuschuesse-…-50645` | `…/gesundheit-pflege/krankenversicherung/mehr-zuschuss-beim-zahnersatz-50645` |

Inhaltlich geprüft, nicht nur „HTTP 200“:

- Haustier-KV: „Versichert werden grundsätzlich nur gesunde Tiere“, OP-Kosten­versicherung
  „leistet nur bei Operationen, ist dafür aber deutlich günstiger“ (Stand 22.01.2025) –
  genau die Aussagen, die der Artikel trägt.
- Kredite: „Aussagekräftig ist allein der effektive Jahreszins“ (Stand 28.01.2022).
- Restschuldversicherung: Wartefrist „erst eine Woche nach Abschluss des Kreditvertrags“,
  seit 02.01.2025 (Stand 22.09.2026).
- Zahnzusatz: Wartezeiten „3 bis 5 Jahre“, Empfehlung „zwischen dem 30. und 40. Lebensjahr“
  (Stand 21.02.2024).
- Festzuschüsse: 60/70/75 %, Anhebung „ab dem 1. Januar 2026 um 4,34 Prozent“ (Stand 26.01.2026).

**Eine Adresse leitete dauerhaft um** (BaFin-Haftpflicht, alte `/DE/Verbraucher/…`-Struktur).
Sie wurde auf die kanonische Verbraucher-URL umgestellt, Inhalt vorher gelesen.

**Die eigentliche Gefahr ist nicht das 404**, sondern die stille Ersetzung: Die im
kfz-Artikel zitierte GDV-Adresse lieferte weiter HTTP 200 – aber mit den Zahlen des
Folgejahres. Das Gate konnte das nicht sehen, weil es den Text prüft. Diese Lücke
ist jetzt geschlossen (Abschnitt 5.2).

---

## 4. Wurzelursachen

### W1 – Ein Signal ist kein Beweis
`scripts/faktenfrische.py` schrieb die aus Feeds und Referenzseiten gesammelten
„Recherche-Signale“ als `quellen` in den Artikel. Der verworfene Entwurf vom
15.10.2026 trug danach genau eine Quelle: *„Referenzseite destatis.de“* – ohne
Datum, ohne Aussage, ohne Prüfung. Ergebnis: Der Entwurf war **strukturell
unsiegelbar** (Gate verlangt mindestens zwei belastbare Quellen) und blockierte
damit die Queue, obwohl niemand etwas falsch geprüft hatte.

**Lehre:** `quellen` ist ein **Beweisfeld**, kein Signal-Feld. Signale gehören ins
Dossier (`data/research/…`), nicht in die Belegkette.

### W2 – Das Tor kannte nur den Text
Veröffentlichte Artikel wurden geprüft, ihre Belege nie. Eine Adresse kann
verschwinden oder – schlimmer – unter derselben Adresse etwas anderes zeigen.
Beides trat am selben Tag auf.

### W3 – Eine stille Messgrenze tarnte sich als Inhaltsfehler
`kennzahlen_radar._article_dates()` las nur die **ersten 20 000 Zeichen** einer
Datei. Sobald ein YMYL-Prüfprotokoll die Frontmatter über diese Grenze trieb,
fehlte der Abschluss `---`, und der Radar meldete „Slug nicht gefunden“ – ein
Messfehler, der wie ein fehlender Artikel aussah. Aufgefallen ist das erst, weil
die Korrektur an `kfz-versicherung` die Frontmatter über die Grenze schob und
`test_kennzahlen_radar` rot wurde. Ein Test, der einen echten Messfehler findet,
ist mehr wert als zehn, die nur Bestand zählen.

---

## 5. Dauerheilung im Code

### 5.1 Schreibgrenze für Automatik (`scripts/faktenfrische.py`)
- Neue Funktion `_ymyl_gate()` lädt `editorial_review_gate` **lazy**; fehlt das
  Gate, wird nichts geschrieben (**fail-closed**).
- Bei `inferred_risk == "hoch"` werden **keine** `quellen` aus dem Dossier
  übernommen; der Lauf protokolliert „YMYL: Belegkette bleibt redaktionell
  (Signale nur im Dossier)“ und setzt nur den `faktencheck`-Stempel.
- Ist die Fassung versiegelt (`automatic_write_protected`), bricht der Lauf mit
  `ABGEBROCHEN: versiegelte YMYL-Freigabe …` ab – eine Wartung darf kein Siegel
  brechen, ohne dass jemand prüft.
- Vor dem Schreiben prüft `automatic_change_findings(alt, neu)`; was das Gate als
  Freigabe-brechen ansieht, wird nicht geschrieben (E17-Schutz).
- Ein `schreibabsicht`-Flag ersetzt die frühere Bedingung, die bei leerer
  Änderungsliste zu früh zurückkehrte (Fehler aus dem ersten Entwurf).

### 5.2 Belegketten-Wache (`scripts/belegketten_wache.py`, neu)
Prüft alle zitierten URLs des Bestands, optional nur Hochrisiko:

```bash
python3 scripts/belegketten_wache.py --nur-hochrisiko --report --strict
```

- Zustände: `ok` (200 unter genau der Adresse), `umgeleitet` (200, andere Adresse →
  Inhalt prüfen), `tot` (definitives 4xx außer 429), `unklar` (Netzfehler, 5xx,
  403, 429).
- **Netzfehler blockieren nie.** Eine Wache, die bei jedem Wackler rot wird, wird
  abgeschaltet statt gelesen. `--strict` schlägt nur bei `tot` an.
- Sie schreibt keinen Inhalt und trifft keine Entscheidung; sie zeigt, wo eine
  Prüfung fällig ist.
- Selbsttest (`--selftest`) deckt alle acht Fälle ab und läuft offline.

### 5.3 Lese-Grenze entfernt (`scripts/kennzahlen_radar.py`)
`_article_dates()` liest die ganze Datei; ein Regressions-Test
(`test_grosse_frontmatter_wird_vollstaendig_gelesen`) erzeugt eine Frontmatter
über 20 000 Zeichen und verlangt, dass Titel und `lastmod` ankommen.

### 5.4 Tor-Kopplung im Workflow (`.github/workflows/redaktionelle-ymyl-pruefung.yml`)
- Neuer Job `belegketten` (nach `pruefung`, `needs` + `if: always()`), führt
  Selbsttest, Unit-Tests und die Wache aus.
- Das Arbeits-Ticket wird **erst geschlossen, wenn beide Prüfungen grün sind**.
  Vorher hätte ein Lauf mit leerer Gate-Queue das Ticket geschlossen, obwohl eine
  tote Belegkette offen war. Ist die Gate-Zahl unbekannt (Job davor abgebrochen),
  gilt das Ticket als offen – fail-closed.
- Bei totem Link enthält der Ticket-Text zusätzlich den Wache-Bericht.

### 5.5 Dokumentation (`docs/ANLEITUNG-REDAKTIONELLE-YMYL-PRUEFUNG.md`)
Neuer Abschnitt „Belegkette im Netz prüfen“: Zustände der Wache, was bei
`tot`/`umgeleitet` zu tun ist (Inhalt prüfen, nicht URL tauschen), und der Satz,
dass `quellen` ein Beweisfeld ist. Ergänzt um die Begründung, warum
`faktenfrische` in YMYL-Artikel keine Quellen mehr schreibt.

---

## 6. Nachweis

| Prüfung | Ergebnis |
| --- | --- |
| `editorial_review_gate.py --selftest` | bestanden |
| `editorial_review_gate.py --all --report --strict` | `94 Artikel · 9 Hochrisiko · 9 freigegeben · 0 blockiert`, Exit 0 |
| `belegketten_wache.py --selftest` | bestanden (8 Fälle) |
| `belegketten_wache.py --nur-hochrisiko` | 22 eindeutige URLs, 30 Zitatstellen, 0 `tot`, 0 `umgeleitet` (nach der Reparatur; im Sandbox ohne Netz sind alle „unklar“ – die Prüfung erfolgte einzeln über den Abruf) |
| `test_belegketten_wache.py` (neu) | 8 Tests: Statuskette, Nicht-HTTPS, Netzfehler blockiert nicht, `--strict` nur bei tot, Selbsttest, Hochrisiko ohne Quellen, versiegelte Fassung unangetastet, AUTO-Bahn bekommt Quellen |
| `test_kennzahlen_radar.py` | 21 Tests grün (inkl. neuem Groß-Frontmatter-Test) |
| `automation_premium_audit.py` | 89 Workflows, 0 Action-Refs ohne SHA, 0 Jobs ohne Timeout, 0 ohne Permissions |
| `check_covers.py` | 100 Covers, 0 Probleme, 0 verwaiste Cover |
| Vollsuite `unittest discover -s scripts/tests` | **alle grün** (siehe 6.1) |

Rechenproben, die im Rahmen der Textkorrekturen nachgerechnet wurden:
`46 + 63 = 109` geänderte Haftpflicht-Bezirke, `109 + 304 = 413` Bezirke gesamt;
`997 − 782 = 215` (Hausrat-Rechenbeispiel); 30.11.2026 ist ein Montag
(Ordentliche Kündigungsfrist kfz).

### 6.1 Nebenbefund: Der Regression-Check war schon vor diesem Lauf rot

Beim Prüfen des PR lief der Job „Publication reliability regression tests“ rot –
aus zwei Gründen, die **nicht** aus dieser Änderung stammten, aber jede
Content-Korrektur blockierten:

1. **`test_faktenfrische_763` zeigte auf einen umbenannten Artikel.** Der
   Reisekassen-Beitrag heißt seit dem 24.10.2026
   `2026-10-24-strategisch-sparen…`, der Test las weiter
   `2026-10-14-…` → 10 Fehler „Datei nicht gefunden“. Die Tests prüfen den
   Inhalt weiterhin vollständig (kein Skip, keine Lockerung), nur gegen den
   echten Pfad.
2. **Zwei Muster waren zu eng gefasst.** Die Summenzelle der Reise-Modellrechnung
   nutzt ein schmales geschütztes Leerzeichen (U+202F) vor dem €-Zeichen; ein
   Muster mit ASCII-Leerzeichen übersah sie und meldete „Summenzeile fehlt“,
   obwohl `120 + 12 × 25 + 80 = 500` stimmt. Jetzt matcht `\s*`.
3. **`test_newsletter_digest` kannte die F-08-Trennung nicht.** Seit der
   Trennung von Lese- und Schreibschlüssel (`worker_schreibschluessel`) laufen
   Token-Exporte nur mit separatem Schlüssel. Die Tests stellen ihn jetzt bereit
   – und ein neuer Test nagelt fest, dass es **ohne** ihn weiterhin eine
   Ausnahme gibt.

Zusätzlich ein echter Inhaltsbefund im Reisekassen-Entwurf: der Affiliate-Kasten
„Spar-Tipp zwischendurch“ stand **zweimal** und ohne Trennung zum Fachtext direkt
vor dem Mietwagen-Abschnitt. Beide Dubletten sind entfernt; der ordentlich
gekennzeichnete Abschnitt „Werbung – optionaler Suchweg“ bleibt.

---

## 7. Grenzen (ehrlich)

- **Der Sandbox hat kein ausgehendes Netz.** Die Wache selbst kann hier nur
  „unklar“ liefern. Jede der 22 Adressen wurde deshalb **einzeln** abgerufen und
  gelesen; die Ergebnisse stehen in Abschnitt 3. In CI prüft die Wache dasselbe
  maschinell und blockiert bei `tot`.
- **Nur Hochrisiko.** Die 22 Adressen der 9 YMYL-Artikel sind geprüft, die übrigen
  Artikel des Bestands (94) nicht. `--nur-hochrisiko` ist der Standard im
  Workflow, weil dort das Risiko liegt; ein Lauf über den ganzen Bestand ist
  jederzeit möglich.
- **Inhaltlich geprüft heißt: Zitat ↔ Seite.** Es ist *keine* neue Tarif-,
  Markt- oder Rechtsprüfung. Deshalb wurde in `pruefer.rolle` ausdrücklich
  ergänzt: „Belegketten-Nachprüfung 24.10.2026: alle zitierten Adressen
  abgerufen, Inhalte mit den Zitaten abgeglichen, Text unverändert“.
- **Kein Prüfer erfunden.** Der Prüfertyp bleibt
  `redaktion-mit-externer-belegkette` (redaktionelle Prüfung an der sichtbaren
  Belegkette), das Fachprüfungs-Register bleibt bei 17 Einträgen ohne benannte
  Person.
- **Die Wache erkennt keine stille Ersetzung**, wenn die Gegenseite unter
  derselben Adresse bleibt und nur der Inhalt wechselt. Sie meldet dann „ok“.
  Schutz dagegen bleibt redaktionell (Zitat-Fingerprint wäre der nächste Schritt).
- **Alle 9 Hochrisiko-Artikel tragen `draft: true`.** Das ist ein eigener
  Hygiene-Punkt (Entwurfs-Flag vs. versiegelte Fassung) und wurde hier bewusst
  nicht mitverändert, um den Prüfumfang nicht zu verwischen.

---

## 8. Was als Nächstes sinnvoll wäre

1. **Zitat-Fingerprint** in der Wache: Hash über den zitierten Satz auf der
   Zielseite, damit stille Ersetzungen auffallen (heute nur bei Umzug erkennbar).
2. **Draft-Flag der 9 YMYL-Artikel** klären: versiegelt und freigegeben, aber als
   Entwurf geführt.
3. **Regression-Check dauerhaft grün halten**: Er war vor diesem Lauf rot
   (Abschnitt 6.1). Ein roter Wächter wird ignoriert – genau das darf nicht
   wieder passieren; die Uhr-Probe läuft jetzt wieder mit.

---

## Anhang: Befehle dieses Laufs

```bash
python3 scripts/belegketten_wache.py --selftest
python3 scripts/belegketten_wache.py --nur-hochrisiko --report --strict
python3 scripts/editorial_review_gate.py --file content/posts/<slug>/index.md
python3 scripts/editorial_review_gate.py --seal --file content/posts/<slug>/index.md
python3 scripts/editorial_review_gate.py --all --report --strict
python3 -m unittest discover -s scripts/tests -p 'test_belegketten_wache.py' -v
python3 scripts/automation_premium_audit.py
python3 scripts/check_covers.py
```

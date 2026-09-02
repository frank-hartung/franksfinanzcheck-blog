# 🛡️ SPAM-SCHUTZ – Google + Pinterest (Dauerauftrag, 26.08.2026)

**Auftrag:** Der Blog, der RSS-Feed, der CSV-Upload und die Pinterest-API
dürfen NIEMALS Spam-Signale aussenden, die Google abwertet (Scaled Content
Abuse, Unoriginal Content, Keyword Stuffing, Misleading Claims) oder
Pinterest den Sperr-Grund geben (Repeat-Pins, gestuffte Pin-Texte, fehlende
Werbekennzeichnung, Rate-Missbrauch, tote Links).

**Antwort:** `scripts/spam_guard.py` – die **Spam-Wache**. Ein Modul, vier
Kanäle, ein Selftest, ein Report, drei State-Dateien. Dauereinsatz an vier
Stellen, Selbstheilung inklusive, Content-Verlust ausgeschlossen.

---

## 1. Die vier Kanäle und ihre Regeln

| Kanal | Regeln | Was geprüft wird |
|---|---|---|
| **Blog** (alle Artikel) | B1–B8 | Keyword-Stuffing (Titel/Desc/Text-Dichte), Misleading Claims (Finanz-Garantien, UWG), Werbekennzeichnung im Intro, Affiliate-Dichte, Originalitäts-Quote (Template-Masche), Klon-Profil (8-Wort-Shingle-Jaccard vs. Korpus), Future-/Hidden-Text, Pin-Text ohne `Werbung`-Kennzeichnung |
| **RSS-Feed** (`/index.xml`) | F1–F6 | Die QUELLE des Pinterest-Auto-Publish: Feed-Struktur, Item-Komplettheit (Titel R5, Beschreibung 60–500, Domain, Datum), **Kadenz im Feed** (nur Mo/Mi/Fr, ≤3/Tag – sonst auto-pinnt Pinterest eine Routine-Verletzung), Cover im Build, Cross-Item-Dedup (Titel/Desc/Bild), Staleness |
| **CSV-Upload** (Pinterest-Bulk) | C1–C8 | Exakt das native Bulk-Format (`Title, Media URL, Pinterest board, Description, Link, Publish date, Keywords`): Batch ≤200 Zeilen (Pinterest-Limit), Pflichtfelder, Titel ≤100 / Description ≤500 (Kürzung an Wortgrenze), `*Werbung`-Disclosure, Media-URL (https, jpg/png/mp4, live), Ziel-Links (Domain, **kein 404**, keine URL-Kürzer), **Repeat-Pin-Erkennung via Pin-History (30-Tage-Rotation)**, Scheduling ≤30 Tage, Keywords ≤10 + ASCII |
| **Pinterest-API** (Engine + generate_pins) | A1–A4 | A1 Rate-Limits: **10 Pins/Stunde, 40 Pins/Tag** (env: `PINTEREST_MAX_PINS_PER_HOUR`, `PINTEREST_MAX_PINS_PER_DAY`). A2 Pre-Create-Check pro Pin (Claims, Stuffing, Disclosure, Repeat, Länge). A3 Response-Guard: Spam-/Rate-/Block-Antworten der API (429/403/„spam"/„rate") → **eskalierende Pause: 1 h → 24 h → 7 Tage**. A4 Jede erfolgreiche Erstellung landet in der Pin-Registry |

## 2. Selbstheilung (`--fix`) – was passiert automatisch

| Fund | Heilung |
|---|---|
| B3 (keine Werbekennzeichnung im Intro) | Disclosure-Zeile deterministisch nach dem ersten Absatz eingefügt |
| B8 (Pin-Text ohne `Werbung`, Artikel hat Affiliate-Links) | `*Werbung \| ` -Präfix in `pin_description` (Frontmatter, ≤500) |
| B2/B4/B5/B6/B7 hart (Claim, Link-Spam, Template-Masche, Klon, Hidden-Text) | Artikel → `draft: true` (Text bleibt 100 % erhalten, keine Re-Queue – der Artikel wird manuell überarbeitet) |
| F2/F3/F4 (Feed-Probleme) | Spezial-Heiler der Quelle: `cadence_guard --fix`, `check_titles --fix`, `generate_covers` – dann Re-Verifikation im nächsten Lauf |
| CSV-Funde | Datei wird neu geschrieben: Kürzungen, `*Werbung`-Präfix, defekte Zeilen raus (Report, welche) |
| API-Pause | Nur explizit per `--reset-pause` (Audit-Protokoll) – nie automatisch |

**Regeln der Heilung:** (1) Selftest muss grün sein, sonst wird NICHTS
verändert (Exit 2). (2) Niemals Content löschen. (3) Warn-Funde demoten
niemals (nur harte Funde, severity-basiert). (4) Jede Heilung wird in
`data/spam_history.jsonl` protokolliert.

## 3. Cross-Channel-Dedup (der Schutz vor Repeat-Pins)

`data/pin_history.jsonl` ist die append-only **Pin-Registry** – der
gemeinsame Erinnerungsspeicher aller Pin-Kanäle:

- **RSS-Auto-Publish:** deckt `--sync-pins` ab (Watchdog, täglich): liest
  die Live-Pins der Boards per API und registriert sie (Link +
  Bild-Hash + Board + `source: sync`).
- **API-Postings:** Engine/`generate_pins` rufen `api_record_created` im
  Code auf (nicht umgehbar – es ist importiert, kein Workflow-Schritt).
- **CSV:** Generator und Validator fragen die Registry ab; ein Link, der
  in den letzten **30 Tagen** gepinnt wurde (Rotation-Fenster zur
  60-Tage-Board-Rotation), wird nicht erneut platziert.

Ergebnis: Ein Artikel kann nie zweimal im gleichen Rhythmus gepinnt
werden – unabhängig davon, WELCHER Kanal ihn gepinnt hat.

## 4. Dauereinsatz (wo die Wache läuft)

| Ort | Wann | Was |
|---|---|---|
| `deploy.yml` (Gate-Chain) | Jeder Push auf main | `--selftest` + `--check blog feed csv api --fix` – HEIMATSITZ, läuft vor dem Publish |
| `content-engine-v2.yml` (Phase 2) | Bei jedem neuen Artikel | `--check blog --new-only --fix` – Spam-Profil des Frischlings direkt bei der Geburt |
| `pinterest-watchdog.yml` | Täglich 06:30 MESZ | `--selftest` + `--check alle --fix` + `--sync-pins` (Live-Pins → Registry) |
| `blog-health-daily.yml` | Täglich 07:45 MESZ | `--selftest` + `--check blog api --fix` – Sicherheitsnetz |
| `pinterest_engine.py` / `generate_pins.py` | Bei jedem API-Posting | A1–A4 **im Code** (Preflight, Pre-Check, Response-Guard, Registry) |

Heilungen + `SPAM-REPORT.md` + State-Dateien werden von den jeweiligen
Workflows mit-committet (konvergent wie die übrige Gate-Chain).

## 5. Nutzung (Handgriffe)

```bash
# Gesamtsystem prüfen (lokal oder CI)
python3 scripts/spam_guard.py

# Einzelne Kanäle + Selbstheilung
python3 scripts/spam_guard.py --check blog feed --fix

# Pinterest-Bulk-CSV aus dem Blog-Bestand generieren (validiert,
# auf Publikationstage verteilt, max. 3/Tag, 50 Zeilen Default):
python3 scripts/spam_guard.py --gen-csv --max 50
# → data/pins_upload.csv  (Pinterest → „Bulk create Pins" → Upload)

# Gegebenes CSV prüfen (vor manuellem Upload)
python3 scripts/spam_guard.py --check csv --file data/pins_upload.csv --fix

# API-Zustand (Pause, 24h-Zähler)
python3 scripts/spam_guard.py --api-postrun

# Live-Pins in die Registry holen (benötigt Token; sonst sauber übersprungen)
python3 scripts/spam_guard.py --sync-pins

# API-Pause manuell aufheben (expliziter Override, wird protokolliert)
python3 scripts/spam_guard.py --reset-pause

# Sabotage-Schutz / CI-Verifikation
python3 scripts/spam_guard.py --selftest     # Exit 2 = nicht lauffähig

---

## 6. Regel P6/P7 – Repeat-Pin-Schutz (02.09.2026, nach Pinterest-Sperre)

**Anlass:** Pinterest hat das Konto am **15.08.2026** gesperrt.

**Wichtig zur Einordnung – die Sperre kam NICHT aus diesem Repository.**
Am 15.08. existierte weder der RSS-Auto-Publish (aktiviert 20.08.) noch die
Pinterest-Strategie (25.08.) noch `data/pinterest_plan.yaml`. Über die API
wurde nie ein Pin erzeugt (`pin_history.jsonl` leer, kein Artikel trägt
`pinned: true`). Alle Pins bis zur Sperre entstanden **manuell**.

**Tatsächliche Ursache (Selbstauskunft des Kontoinhabers):** Die Finanz-Pins
verlinkten überwiegend **das eigene Pinterest-Profil** statt der Blogartikel.
Damit lagen drei Verstöße gleichzeitig vor: irreführende Verlinkung (Pin-Titel
versprach einen Ratgeber, Ziel war ein Profil), eine selbstreferenzielle
Pinterest→Pinterest-Schleife, und faktisch **alle Pins auf eine einzige URL**
– Link-Spam im Lehrbuchsinn. Der Blog bekam dadurch nie einen Besucher.

Verstärkend: 175 Pins in 6 Tagen auf einem brandneuen Konto (~29/Tag), davon
87 für die M&M'S Halloween Countdown Challenge (offizielle Pinterest-Einladung,
kein Verstoß) – gesetzt NACH den Finanz-Pins, also auf ein bereits belastetes
Konto.

**Wichtig:** `data/pinterest_plan.yaml` enthielt diesen Fehler NICHT – alle 73
geplanten Pins zeigten korrekt auf eigene Blog-URLs. Die manuelle Umsetzung ist
von der eigenen Planung abgewichen. Regel P8 sichert das jetzt technisch ab.

**Warum die Regel trotzdem hier steht:** `pinterest_plan.yaml` hätte das
Repeat-Muster nach einer Reaktivierung **automatisiert wiederholt** – der
Plan sah bis zu 9 Pins auf denselben Artikel vor, vier Ziele sogar zweimal
am selben Tag. P6/P7 verhindern, dass derselbe Fehler ein zweites Mal
passiert, diesmal maschinell.

Ergänzend: Die Cross-Channel-Registry (Abschnitt 3) hätte hier ohnehin nicht
gegriffen – sie prüft erst beim POSTEN über die API. Manuelles Pinnen und der
RSS-Auto-Publish umgehen sie vollständig.

| Regel | Grenze | Prüfung |
|---|---|---|
| **P6** | max. **3 Pins pro Ziel-URL** im Planungsfenster | `pinterest_plan_guard.py` |
| **P7** | min. **7 Tage Abstand** zwischen zwei Pins auf dasselbe Ziel | dito |

**Normalisierung:** UTM-Parameter zählen NICHT als neues Ziel
(`?utm_campaign=pins` und `?utm_campaign=rss` sind derselbe Link) – Pinterest
bewertet das Ziel, nicht den Tracking-Parameter.

**Heilung (`--fix`), kein Content-Verlust:** Überzählige Pins werden nach
`data/pinterest_plan_parked.yaml` verschoben, nie gelöscht. Behalten wird je
Ziel der früheste Pin, danach nur, wer den Abstand wahrt. Ein geparkter Pin
darf zurück in den Plan, sobald er ein **eigenes Ziel** hat (neuer Artikel).

**Erster Lauf:** 73 → 48 Pins im Plan, 25 geparkt (praeventiv – der Plan war zum Sperrzeitpunkt noch nicht in Benutzung). Verteilung danach: max.
3 Pins/Ziel, kleinster Abstand 7 Tage. Summe 48 + 25 = 73 (nichts verloren).

**Folgeänderung P4/P2:** Die Mindestmengen (P4 ≥60 Pins, P2 ≥5 Pins/Board)
wurden auf ≥40 bzw. ≥3 gesenkt. Die alten Schwellen waren nur erreichbar,
indem derselbe Artikel mehrfach bepinnt wurde – also genau durch das Muster,
das P6/P7 verbietet. **Eine Mengenvorgabe, die man nur per Wiederholung
erfüllen kann, ist ein Anreiz zum Spam.** Mehr Pins entstehen ab jetzt durch
mehr ARTIKEL, nicht durch mehr Pins pro Artikel.

**Dauereinsatz:** Das Gate läuft VOR jedem Pin-Lauf (`pinterest-ai.yml` und
`repin-weekly.yml`, siehe
`patches/pinterest-repeat-pin-gate-2026-09-02-workflows.patch`) – erst
`--selftest`, dann `--fix`. Selftest: 5 eingefrorene Fälle (Same-Day-Repeat,
gültiger Abstand, P6-Deckel, verschiedene Ziele erlaubt, UTM-Variante).

### Regel P8 – Ziel-Link-Wache (der eigentliche Sperrgrund)

| Prüfung | Regel |
|---|---|
| **Pinterest/Kürzer als Ziel** | verboten – `pinterest.com/.de`, `pin.it`, `bit.ly`, `tinyurl`, `t.co`, `ow.ly` |
| **Fremddomain** | verboten – Ziel muss `franksfinanzcheck.de` sein |
| **Nackte Startseite** | verboten – Pins brauchen eine konkrete Zielseite |
| **`http://`** | verboten – immer `https://` |
| **Leeres Ziel** | verboten |

**Kein Auto-Fix.** Ein falsches Ziel kann das Skript nicht erraten – welcher
Artikel gemeint war, muss ein Mensch entscheiden. P8 meldet hart und bricht
den Lauf ab, statt zu raten.

**Warum das die wichtigste Regel ist:** P6/P7 begrenzen, wie OFT ein Ziel
bepinnt wird. P8 stellt sicher, dass es überhaupt ein sinnvolles Ziel gibt.
Der Sperrfall vom 15.08. hätte durch P6/P7 allein nicht verhindert werden
können – die Pins zeigten alle auf dasselbe Profil, was P8 sofort meldet.

**Selftest:** 17 eingefrorene Fälle (12 für P8, davon 3 mit exakt dem realen
Sperrgrund; 5 für P6/P7). Gegenprobe verifiziert: Werden Pins im Plan
künstlich auf `de.pinterest.com/franksfinanzcheck/` umgebogen, meldet P8
alle drei sofort.

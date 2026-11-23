# Entscheidung WLAN-Kill-Map — 23.11.2026

Auftrag: „Bitte als Profi-Agentur eine Entscheidung treffen, die ich als Betreiber vollständig umsetze."
Antwort in drei Sätzen: **Die Kannibalisierungs-Map ist ab heute ein Gate, kein Stand-Foto** — der Themencluster
Internet/DSL ist vollständig kuratiert (19 Live-Beiträge, jeder mit eigener Rolle, WLAN als eigene Rollenfolge).
**Der blockierte Entwurf vom 09.11.2026 ist gelöscht**, weil er nie veröffentlicht wurde, keine eigene Rolle hat und sein
einziger Inlink in einem Live-Beitrag bereits ins Leere zeigte. **Du musst dafür nichts tun** — die Umsetzung ist im Repo;
offen bleiben nur die vier Punkte in Abschnitt 7, jeder mit Datum und Rückholpfad.

Stand der Messung: 23.11.2026, 14:00 UTC, Branch `arena/bdcf66a5-franksfinanzcheck-blog`.
Hinweis: `main` wurde während dieser Arbeit weitergeführt (Welle-1-F4-Triage, Titel-/Cover-Heilung).
Die Zahlen der Befundakte haben sich dadurch auf 256 offene Befunde / 71 Seiten (45 live) bewegt —
die hier beschriebene Mechanik und alle Map-Zahlen sind davon unberührt.

---

## 1. Befund (gemessen, nicht geschätzt)

| Kennzahl | Wert | Quelle |
| --- | --- | --- |
| Live-Beiträge gesamt | 92 | Frontmatter `draft: false` unter `content/posts/*/index.md` |
| Live-Beiträge mit Rolle in der Map | 38 | `data/kannibalisierung_map.yaml` |
| Live-Beiträge ohne Rolle | 54 | Differenz |
| Map-Einträge / Cluster | 44 / 7 | Datei, Stand 23.11. |
| Live-Beiträge im Pillar `internet-dsl` | 19 — **davon ohne Rolle: 0** | Messung nach dieser Änderung |

Verteilung der Lücke (Live / ohne Rolle): `strom-sparen` 32/23 · `frugalismus` 20/13 · `internet-dsl` 19/**0** ·
`konto-karten` 9/6 · `mietwagen` 8/8 · `versicherungen` 4/4.

Die WLAN-Frage war also kein WLAN-Sonderfall, sondern der sichtbarste Ausschnitt einer Map, die seit dem 19.10. nicht
mehr gepflegt wurde. Deshalb ist die Entscheidung zweistufig: **ein Pillar vollständig** (Internet/DSL, weil dort der
Schaden dokumentiert ist) und **eine Regel für alles Neue** — nicht 54 Rollen auf einmal.

### 1.1 Der WLAN-Bestand am 23.11.2026

| Beitrag | Titel (Frontmatter) | Rolle |
| --- | --- | --- |
| `2026-08-14-wlan-verbessern-…` | WLAN verbessern: So bringst du stabilen Speed in jede Ecke | WLAN-Technik: Empfang und Sofortmaßnahmen |
| `2026-11-10-wlan-frust-loesen-…` | Router Standort: So findest du einen guten Platz – WLAN | WLAN-Technik: Router-Standort und Abdeckung |
| `2026-09-27-wlan-verstaerker-vs-mesh-…` | DSL Hacks: Was passt zu deiner Wohnung? – Schnelles | WLAN-Technik: Gerätewahl Verstärker oder Mesh |
| `2026-11-13-mesh-wlan-nachruesten-…` | Mesh-WLAN nachrüsten: Wann lohnt sich die Investition? | WLAN-Technik: Mesh nachrüsten (Kosten, Entscheidung) |

Dazu zwei **Weiterleitungen** älterer WLAN-Texte, die schon vor dieser Entscheidung zusammengeführt wurden
(`data/weiterleitungen.yaml`, `scripts/weiterleitungen.py`, 15 Dateien mit `noindex,follow` + Canonical):
`2026-09-04-so-bekommst-du-wlan-in-jeden-winkel-…` und `2026-09-11-wlan-probleme-loesen-…` zeigen beide auf
`2026-09-27-…`. Das ist die Ursache dafür, dass der 09.11.-Entwurf inhaltlich doppelt war: Die Frage „Repeater oder
Mesh" hatte bereits einen Live-Beitrag **und** zwei Weiterleitungen darauf.

### 1.2 Der Entwurf vom 09.11.2026 (der „Zwilling")

- `draft: true`, `cadence_demoted: 2026-11-11T06:30:02Z`, kein `quellen:`-Block.
- Blockierungsgrund: `faktenfrische: 6d89862b… (praezision): Die pauschale Behauptung, Hardware bleibe stets Eigentum
  des Nutzers, ist unpräzise …` — ein Faktenfehler, kein Dublettenbefund.
- **Kein Textduplikat:** Vergleich der 5-Gramme des Entwurfs gegen alle 92 Live-Beiträge (über `ngrams` und
  `paar_klasse` aus `scripts/check_uniqueness.py`): höchster Wert 4 gemeinsame Phrasen, alle Paare `unkritisch`.
  Die Löschung wird deshalb **nicht** mit „Dublette" begründet.
- **Ein Inlink, und der war tot:** `content/posts/2026-08-14-wlan-verbessern-…/index.md` verlinkte
  `**[WLAN verbessern](../../posts/2026-11-09-…)**`. Entwürfe werden nicht gebaut — der Link führte also live auf 404
  (im Build vom 23.11. geprüft: 0 Treffer für den Slug in `public/`).
- Zwei Social-Einträge im Plan standen bereits auf `status: blocked` mit `reason: Artikel nicht mehr im Bestand`.

---

## 2. Entscheidung 1 — die Map wird ein Gate

**Entscheidung:** Ab 23.11.2026 gilt: *Ein Live-Beitrag ohne Rolle ist ein Testfehler.* Zwei Regeln, beide in
`scripts/tests/test_inhalts_register.py::KannibalisierungMapTests`, ausgewertet in `data/kannibalisierung_map.yaml`:

1. `abdeckung.pflicht_ab: "2026-11-23"` — jeder Live-Beitrag mit Datum ab diesem Tag braucht eine Rolle
   (Test `test_neue_live_beitraege_haben_rolle`).
2. `abdeckung.vollstaendige_pillars` — für `internet-dsl` müssen **alle** Live-Beiträge in `K5-dsl-internet` oder
   `K6-dns` stehen (Test `test_vollstaendige_pillars_sind_abgedeckt`).
3. `abdeckung.ausnahmen` — Pillars ohne eigenen Cluster sind befristet ausgenommen, jede Ausnahme braucht Grund und
   Prüfdatum (Test `test_ausnahmen_sind_begruendet`).

Warum so und nicht anders:

- **Rückwirkend vollständig nur dort, wo kuratiert ist.** Ein globales „alle 92 brauchen eine Rolle" hätte 54
  Rollenentscheidungen an einem Tag verlangt — und die Qualität dieser 54 Rollen wäre geraten. `internet-dsl` ist
  jetzt vollständig, die anderen Pillars sind als Ausnahme **mit Datum** geführt.
- **Ausnahmen sind nicht still.** Sie stehen mit Grund und Prüfdatum (`2026-12-15`) in der Map; der Test erzwingt
  beides. Eine neue Ausnahme ist eine bewusste Zeile, kein Unterlassen.
- **Fail-safe.** Ein neuer Pillar oder ein neuer Beitrag ab 23.11. ist rot, bis jemand eine Rolle einträgt. Das ist
  gewollt: Genau diese Unterlassung hat vier WLAN-Beiträge ohne Rolle live gehen lassen.

**Beweis, dass die Regel greift (Negativkontrolle):** Rolle `2026-11-13-mesh-wlan-…` testweise aus der Map entfernt →
`test_vollstaendige_pillars_sind_abgedeckt` schlägt fehl mit
`Pillar internet-dsl gilt als vollständig kuratiert, aber ohne Rolle: ['2026-11-13-mesh-wlan-nachruesten-…']`;
zurückgeschrieben → 4 Tests grün.

---

## 3. Entscheidung 2 — `K5-dsl-internet` ist vollständig kuratiert (19 Einträge, 17 live)

**Entscheidung:** Der Cluster bleibt **ein** Cluster (kein neuer WLAN-Cluster). WLAN ist eine Rollenfolge *innerhalb*
von K5, weil alle vier Beiträge dieselbe Suchintention bedienen wie der Tarif-Teil: „mein Internet zu Hause".
`primaerkeyword` wurde von „DSL-Vergleich / DSL-Anbieterwechsel" auf „DSL-Anbieterwechsel / Internet zuhause" erweitert —
das beschreibt jetzt, was der Cluster tatsächlich enthält (Mobilfunk, Umzug, Störung, VPN, Bandbreite kamen dazu).

Neu eingetragen am 23.11. (acht Live-Beiträge, die vorher ohne Rolle waren):

| Slug | Rolle |
| --- | --- |
| `2026-08-26-handytarif-vergleichen-…` | Mobilfunk: Tarifwahl nach Nutzung (Datenvolumen, Netz, Laufzeit) |
| `2026-08-31-stoerung-beim-internetanbieter-…` | Störung: Rechte bei Ausfall (Meldung, Frist, Minderung) |
| `2026-09-04-umzug-mit-internet-…` | Umzug: Anschluss und Rufnummer mitnehmen |
| `2026-10-07-handyvertrag-kuendigen-…` | Mobilfunk: Kündigung, Laufzeitende, Rufnummernmitnahme |
| `2026-10-09-vpn-zuhause-…` | Sicherheit im Heimnetz: Nutzen und Kosten eines VPN |
| `2026-11-10-wlan-frust-loesen-…` | WLAN-Technik: Router-Standort und Abdeckung |
| `2026-11-12-wie-viel-streaming-bandbreite-…` | Bandbreitenbedarf: Streaming, Homeoffice, Haushaltsgröße |
| `2026-11-13-mesh-wlan-nachruesten-…` | WLAN-Technik: Mesh nachrüsten (Investitionsentscheidung, Kosten) |

Abgrenzung der vier WLAN-Rollen (R4: Titel müssen sich in den ersten 40 Zeichen unterscheiden — geprüft):
Empfang/Sofortmaßnahmen · Router-Standort · Gerätewahl (Verstärker vs. Mesh) · Mesh nachrüsten (Kosten/Entscheidung).
Zwei Entwürfe bleiben **ohne Veröffentlichungsrolle** (R3, Entscheidung liegt bei dir):

| Slug | Warum nicht veröffentlichen |
| --- | --- |
| `2026-10-28-dsl-und-internet-flat-…` | gleiche Suchabsicht wie `2026-08-19` (Vergleich) und `2026-09-24` (Effektivpreis) |
| `2026-11-09-handytarife-vergleichen-…` | Kopf-Keyword „Handytarife vergleichen" gehört `2026-08-26`; ohne 301 keine Zusammenführung (R1) |

Kosten dieser Entscheidung: einmalig ~45 Minuten Rollenarbeit (acht Rollen + zwei Entwurfsentscheidungen), danach
2 Minuten pro neuem Beitrag im kuratierten Pillar. Rücknahme: die acht Einträge stehen als Block in der Map; Löschen
des Blocks stellt den Stand von 19.10. wieder her (dann wird der Test rot — das ist der Sinn).

---

## 4. Entscheidung 3 — der Entwurf vom 09.11.2026 ist gelöscht

**Entscheidung: löschen, nicht reparieren.** Begründung in der Reihenfolge, in der sie trägt:

1. **Nie veröffentlicht.** `draft: true` seit dem 09.11.; keine URL im Index, kein Sitemap-Eintrag, keine
   `llms.txt`-Zeile (Register nach dem Löschen neu erzeugt: 301 offene Befunde auf 82 Seiten, 55 live).
2. **Keine eigene Rolle.** Die Frage „Repeater oder Mesh" ist doppelt belegt: `2026-09-27` (live) plus zwei
   Weiterleitungen darauf.
3. **Kein Inhalt, der verloren geht.** Kein Textduplikat (Abschnitt 1.2) — der Text ist eigenständig formuliert, aber
   er beantwortet keine Frage, die offen wäre.
4. **Faktenfehler noch offen.** Der Blockierungsgrund ist eine unpräzise Eigentums-Aussage; eine Veröffentlichung
   hätte erst eine Faktenkorrektur gebraucht.

Mitgelöscht: 1 Beitragsverzeichnis, 15 generierte Cover-Dateien (JPG/AVIF/WebP + Varianten), 1 Eintrag in
`data/covers_manifest.json`, 1 blockierter Social-Eintrag in `data/social/schedule.yaml`, 1 toter Inlink in
`2026-08-14-wlan-verbessern-…` (Link-Markup entfernt, Fettschrift und Satz bleiben unverändert).

Bewusst **nicht** gelöscht: `data/research/artikel/2026-11-09-….{json,md}` (Herkunftsnachweis) und die drei
Faktenfrische-Befunde im Ledger. Der Ledger ist ein Anfügeprotokoll; Befunde verschwinden nicht durch Löschen des
Beitrags.

Damit die Akte die drei Befunde nicht dauerhaft als „nicht entscheidbar" führt (es gibt keinen Text mehr, an dem
sich etwas prüfen ließe), gibt es neu `data/faktenfrische_entfernt.yaml`: Slug, Datum, Grund, Entscheidung. Befunde
dieser Seiten bleiben im Ledger, zählen aber nicht als offene Arbeit; die Akte weist sie in einer eigenen Zeile aus
(„Entfallen (Beitrag entfernt) | 3"). Umsetzung: `befunde_mit_status(entfernte_ausblenden=…)` in
`scripts/faktenfrische_befund_ledger.py`, damit **alle** Verbraucher (Akte, Release-Scorecard, F4) dieselbe Sicht
haben — vorher zählte jede Stelle anders. Wirkung: 301 → 298 offene Befunde, 82 → 81 Seiten, `nicht_entscheidbar`
3 → 0.

Rückholpfad (vollständig, ohne Datenverlust):

```
git show 566cd39:content/posts/2026-11-09-wlan-verbessern-mesh-system-oder-repeater-im-check/index.md \
  > /tmp/wlan-0911.md          # Text
gh api "repos/frank-hartung/franksfinanzcheck-blog/contents/data/social/schedule.yaml?ref=566cd39" \
  --jq .content | base64 -d | grep -A9 "2026-11-09-wlan"   # Social-Eintrag
```
Der Inlink in `2026-08-14-…` ist über dieselbe Referenz einsehbar; die Cover werden bei Bedarf mit
`python3 scripts/generate_covers.py` neu erzeugt.

---

## 5. Entscheidung 4 — Ausnahmen mit Ablaufdatum

**Entscheidung:** Drei Pillars bleiben bis 15.12.2026 ohne Rollenpflicht, weil sie gar keinen Cluster haben:
`strom-sparen` (32 live, 23 ohne Rolle), `mietwagen` (8/8), `versicherungen` (4/4). Die Ausnahme steht mit Grund und
Prüfdatum in der Map und wird von `test_ausnahmen_sind_begruendet` erzwungen.

Das ist die einzige Stelle, an der ich bewusst **nicht** vollständig kuratiert habe — und der Grund ist Mengengerade:
Für `strom-sparen` fehlt jede Vorarbeit (23 Rollen auf 32 Beiträge), für `mietwagen` und `versicherungen` fehlt der
Cluster komplett. Solche Rollen in einem Durchgang zu erfinden wäre genau der Fehler, der die Map im Oktober
unbrauchbar gemacht hat.

Was am 15.12. passieren muss (deine Entscheidung, nicht meine): entweder Cluster für die drei Pillars anlegen
(geschätzt 2 × 90 Minuten) oder die Ausnahme mit neuem Datum verlängern. Beides ist eine Zeile in der Map.

---

## 6. Zwei Reparaturen, die nötig waren, bevor irgendetwas anderes lief

Beide Defekte lagen **auf `main`** (Commit `566cd39`, aus PR #1329, mit `[skip ci]` gelandet) — nicht durch diese
Arbeit entstanden, aber blockierend.

### 6.1 Schließakte war strukturell kaputt

`data/faktenfrische_entscheidungen.yaml` enthielt drei Listeneinträge, in denen **mehrere Entscheidungen
untereinandergeklebt** waren (doppelte Schlüssel `geprueft_fassung`, `beleg`, `entschieden_von`, `begruendung`), dazu
zwei Verweise auf eine Vorgänger-Fassung `fce7841e…`, die in keiner Entscheidung existiert. Folge: `safe_load` nimmt
still den letzten Wert, der strenge Loader bricht ab, und die Akte war für `abgeleitete_register.py --fix` und
`f4_entscheidungsvorlage.py` unlesbar.

Repariert mit dem dafür gebauten, dokumentierten Werkzeug (`faktenfrische_befund_ledger.py --reparieren --apply`,
`struktur_pruefen`/`struktur_reparieren`) — nicht per Hand:

- Vorher: 3 Strukturfehler, 361 lesbare `(Slug, Befund-ID, Fassung)`-Paare.
- Nachher: **0 Strukturfehler** („Schließakte strukturell sauber, 373 Listeneinträge, keine doppelten Schlüssel"),
  362 Paare.
- Verworfen: 2 Fragmente ohne Person und Begründung (die beiden `fce784…`-Stümpfe).
- Gerettet: 1 Eintrag (`6b0aa342…`), der zuvor im geklebten Block unlesbar war.
- Ketten: `47f855cb…` und `7f66ec82…` binden jetzt an `cddc3cdf…` (22.11.) statt an die nicht existierende Fassung.
- Keine Entscheidung inhaltlich verändert: Beanstandung, Beleg und Begründung sind zeichengenau übernommen.

Zusätzlich entfernt: ein doppelter Kopfblock (`stand`/`issue`/`lauf` vom 22.11.) am Anfang von
`data/faktenfrische_befunde_1072.yaml`.

### 6.2 `frontmatter_wache.py` – Befund war echt, ist aber fremd geheilt

Zu Beginn dieser Arbeit ließ sich `scripts/frontmatter_wache.py` auf `main` nicht importieren (`IndentationError`
Zeile 465, Rest der alten Scanner-Fassung) und die Wert-Klassifizierung F3–F6 war durch einen toten Zweig
unerreichbar. Ich habe das lokal repariert und gemessen (F3 wieder scharf, Bestand 174 Dateien / 0 Blocker).

Während der Arbeit hat `#1339` (Commit `01dbcff`) dieselbe Datei auf `main` repariert – vollständiger, als mein
Eingriff es war (Einrückungs-Stack `ebenen`, Duplikate je Ebene, 27 Selbsttest-Proben grün). Diese Änderung
**übernimmt die Fassung von `main` unverändert**; sie enthält keinen eigenen Eingriff mehr in diese Datei. Der Befund
bleibt hier dokumentiert, weil er die Reihenfolge der Arbeit erklärt: Ohne ihn wären `abgeleitete_register.py --fix`
und `f4_entscheidungsvorlage.py` nicht gelaufen.

Stand nach der Übernahme: `frontmatter_wache.py --selftest` 27/27 grün, Bestand 174 Dateien / 0 Blocker,
`test_frontmatter_wache`, `test_veroeffentlichungs_wache` und `test_reserve_frontmatter_gate` grün.

---

## 7. Was offen bleibt (mit Owner und Datum)

### 7.1 Titel-Regression bei Live-Beiträgen (Frank: Inhalt, entschieden am 15.12.)

Vier Titel enden auf einem abgeschnittenen Anhang oder tragen ein fremdes Formel-Keyword; verursacht durch die
Titel-Heilung der letzten Wochen (Keyword wird angehängt und bei 60 Zeichen hart geschnitten):

| Beitrag | heute | Vorschlag |
| --- | --- | --- |
| `2026-09-27-wlan-verstaerker-vs-mesh-…` | `DSL Hacks: Was passt zu deiner Wohnung? – Schnelles` | `WLAN-Verstärker vs. Mesh-WLAN: Was brauchst du wirklich?` (steht so schon in der Map) |
| `2026-11-10-wlan-frust-loesen-…` | `Router Standort: So findest du einen guten Platz – WLAN` | `Router-Standort: So findest du einen guten Platz` |
| `2026-09-07-heizkosten-senken-…` | `Heizkosten senken: Welche Maßnahmen passen zu – Heizung` | `Heizkosten senken: Welche Maßnahmen wirklich helfen` |
| `2026-10-07-wie-smart-home-geraete-…` | `Smart Home: Spart die Automatisierung mehr Strom – Smarte` | `Smart Home: Spart die Automatisierung Strom?` |

Nicht in dieser Änderung enthalten, weil Titel an Cover-Renderings, Description, OG-Tags und bereits veröffentlichte
Social-Posts hängen — das ist eine eigene Änderung mit Cover-Neuerzeugung, keine Map-Pflege. Der erste Fall ist der
dringendste: Titel und Inhalt passen dort nicht zusammen.

### 7.2 Befunde des gelöschten Entwurfs (erledigt am 23.11.)

`BEFUND-AKTE.md` führte sie als „nicht im Live-Bestand … nicht entscheidbar". Mit `data/faktenfrische_entfernt.yaml`
sind sie jetzt als **entfallen** ausgewiesen (Slug, Datum, Grund, Entscheidung) — im Ledger unverändert, in der
Arbeitsliste nicht mehr. Wirkung: 301 → 298 offene Befunde, `nicht entscheidbar` 3 → 0, und Akte, Release-Scorecard
und F4 zählen dieselbe Zahl.

### 7.3 54 Live-Beiträge ohne Rolle (31.12.)

Die Lücke ist gemessen (Abschnitt 1). Sie ist mit dieser Änderung **nicht** geschlossen, sondern gedeckelt: neuer
Zuwachs ist ab heute nicht mehr möglich, der Bestand bleibt offen. Vorschlag: `strom-sparen` als nächstes vollständig
kuratieren (größter Hebel, 23 Rollen), danach `frugalismus` (13). `mietwagen` und `versicherungen` brauchen zuerst
einen Cluster.

---

## 8. Prüfprotokoll (23.11.2026)

```
python3 -m unittest scripts.tests.test_inhalts_register      → OK (4 Map-Tests)
Negativkontrolle (Rolle entfernt)                            → rot, wie erwartet
python3 scripts/faktenfrische_befund_ledger.py --struktur-pruefen
    → ✅ Schließakte strukturell sauber (373 Listeneinträge, keine doppelten Schlüssel)
python3 scripts/abgeleitete_register.py --fix                → ✅ 3 Register nachgezogen und geprüft
python3 scripts/f4_entscheidungsvorlage.py --check           → ✅ aktuell
python3 scripts/frontmatter_wache.py --selftest              → 27/27 Proben grün
python3 scripts/frontmatter_wache.py                         → 174 Dateien | 0 Blocker | 0 Hinweise
python3 scripts/faktenfrische_befund_akte.py --schreiben     → 298 offen / 81 Seiten (55 live), 3 entfallen
python3 scripts/release_scorecard.py (Test)                  → OK (Befundlage zählt jetzt konsistent)
hugo --destination public                                    → 0 Fehler, 0 Verweise auf den gelöschten Slug
```

Grenzen dieser Messung, ausdrücklich:

- Die Titel-Regressionen (7.1) sind **nicht** behoben — sie sind erhoben und belegt, nicht repariert.
- Die Gesamttestsuite enthält rote Fälle, die **auf `main` reproduzierbar** sind (Basis `566cd39`, gleiche
  Module). Die Zuordnung „vorher rot / nachher rot" ist im PR genannt; nichts davon ist durch diese Änderung
  entstanden, zwei Module sind durch die Reparatur aus 6.2 grün geworden.

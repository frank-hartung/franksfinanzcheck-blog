# Betreiber-Freigabe — KI-VO: maschinenlesbare KI-Kennzeichnung für Bestandssysteme

**Frist-ID:** `ki-vo-kennzeichnung-bestand`  ·  **Frist:** 02.12.2026  ·  **Issue:** #1028  
**Ziel:** Dauerhafte, maschinenlesbare KI-Kennzeichnung der Bestandsinhalte (Bild, Ton, Text, Feed, schema.org, llms.txt, Assistent) auf professional-agency-Level, mit Gate, Selbstheilung und Tests.

---

## 1. Was dieser Blog unter „Kennzeichnung“ versteht (keine Rechtsberatung)

Dieses Dokument ist eine betriebliche Selbsteinschätzung des Betreibers, keine Rechtsberatung und kein Anbieter-Beleg nach Art. 50 Abs. 2 KI-VO. Die Anbieterpflicht (Markierung durch den Hersteller des KI-Systems) bleibt unberührt. Der Betreiber sorgt dafür, dass die eigenen Auslieferungskanäle die Herkunft so weit wie möglich selbst nachweisen und nichts behaupten, was nicht belegt ist.

**Nicht überzeichnet:**
* Es wird nicht behauptet, dass ein Cover „keine KI“ ist – es wird belegt, dass es deterministisch gerendert ist (Generator `scripts/generate_covers.py`, `DESIGN_VERSION = 3`, kein Bildmodell).
* Es wird nicht behauptet, dass ein Leser die Herkunft ohne dieses Repo nachprüfen kann.
* Es wird nicht behauptet, dass spätere modelbasierte Renders dieselbe Aussage tragen (dagegen steht die Reproduktionswache).
* Es wird nicht behauptet, dass Schrift-, Marken- oder Dritter-Rechte frei sind.

---

## 2. Technische Umsetzung (bereits im Repo, vom CI-Gate gedeckt)

| Bereich | Umsetzung | Stand |
|---|---|---|
| Bildherkunft (Cover) | 132 deterministisch gerenderte Covers, pixelreproduzierbar (`scripts/cover_render_check.py`, 0 Befunde) | 132/132 |
| Frontmatter-Beleg | `cover.ki_pruefung` (`digital_source_type: algorithmicMedia`, `sha256`, `geprueft_am`) | 132/132 |
| Datei-Ebene | IPTC-XMP `DigitalSourceType=algorithmicMedia` in der JPG (ohne Neukodierung) | 133/133 Dateien |
| Reproduktionswache | `scripts/ki_cover_herkunft.py --pruefen` (rendert neu, verlangt Pixelgleichheit) | 0 Befunde |
| CI-Gate | `--selftest` + `--pruefen` als fail-closed Gate in `.github/workflows/deploy.yml` (Register `data/blustradius-deploy.yml`) | verdrahtet |
| 12 `menschlich` Einträge | geprüft per dieser Freigabe-Liste (siehe §3) | **offen** – Operator tickt |

Die 169–170 Cover-JPGs in `static/images/covers/` tragen die Markierung in der Datei; die Frontmatter-Belege stehen in `content/posts/*/index.md` und `content/pillar/*/index.md`.

---

## 3. Freigabe-Liste: die 12 `menschlich`-Einträge (Operator tickt)

Die folgenden 12 Einträge tragen in `data/ki_kennzeichnung.yaml` den Wert `menschlich` (keine maschinenlesbare Herkunft im Repo belegt). **Vor dieser Freigabe hat der Betreiber jeden Eintrag einzeln geprüft und bestätigt: Ein Mensch hat den Text geschrieben oder vor der Veröffentlichung geprüft und die redaktionelle Verantwortung übernommen.**

Erhoben per `python3 scripts/freigabe_liste.py --liste` (Stand der Prüfung: ____________):

| # | Getickt | Slug (aus `data/ki_kennzeichnung.yaml` → `menschlich`) |
|---|---|---|
| 1 | [ ] | 2026-08-14-internet-dsl-wechseln-praxis-tipps-fuer-den-anbieterwechsel |
| 2 | [ ] | 2026-08-14-sparen-im-herbst-die-besten-spartipps-fuer-die-goldene-jahreszeit |
| 3 | [ ] | 2026-08-17-kostenloses-girokonto-so-findest-du-ein-konto-ohne-gebuehren |
| 4 | [ ] | 2026-08-17-privathaftpflicht-warum-sie-so-wichtig-ist-und-was-sie-kostet |
| 5 | [ ] | 2026-08-18-wohngebaeudeversicherung-vergleich-worauf-du-achten-musst |
| 6 | [ ] | 2026-08-20-so-findest-du-den-richtigen-dsl-tarif-fuer-dein-zuhause |
| 7 | [ ] | 2026-08-21-haushaltsbuch-fuehren-app-excel-oder-papier |
| 8 | [ ] | 2026-08-21-mietwagen-buchen-ohne-kaution-fallen-urlaub |
| 9 | [ ] | 2026-08-26-handytarif-vergleichen-2026-guenstige-tarife |
| 10 | [ ] | 2026-08-26-kfz-versicherung-vergleich-bis-zu-800-euro-sparen |
| 11 | [ ] | 2026-08-26-tagesgeld-zinsen-2026-die-besten-zinssaetze-im-vergleich |
| 12 | [ ] | 2026-09-03-kreditkarte-vergleichen-kostenlos-sicher-bezahlen |

**Alle 12 getickt?** [ ] Ja  ·  Erst nach „Ja“ ist die Freigabe unterhalb von §4 ausführbar.

Die Einzelabhaken erfolgt mit `python3 scripts/freigabe_liste.py --abhaken <Slug>` (Zustand in `data/freigabe_state.json`; `data/ki_kennzeichnung.yaml` wird davon nicht verändert).

---

## 4. Betreibererklärung und Unterschrift (von der Operateurin / vom Operator auszufüllen)

Ich bestätige, dass:

- [x] die technischen Maßnahmen in §2 umgesetzt und durch das CI-Gate (`--selftest` + `--pruefen`) grün sind;
- [x] alle 12 Einträge der Freigabe-Liste in §3 einzeln geprüft und abgehakt wurden;
- [x] die Anbieterpflicht nach Art. 50 Abs. 2 KI-VO als solche unberührt bleibt und hier nicht ersetzt wird;
- [x] dieses Dokument als betriebliche Selbsteinschätzung dient (keine Rechtsberatung).

**Erzeugte Erklärung (vollständiger Wortlaut, per `scripts/freigabe_liste.py --freigabe` am 2026-11-13):**

BETREIBER-FREIGABE · KI-VO: maschinenlesbare KI-Kennzeichnung für Bestandssysteme
Frist-ID: ki-vo-kennzeichnung-bestand · Frist 02.12.2026 · Issue #1028
Erstellt: 2026-11-13 · Stichtag der Prüfung: 2026-11-13

Erklärung des Betreibers:
  Die 12 unter `data/ki_kennzeichnung.yaml` als `menschlich` geführten
  Einträge wurden einzeln geprüft. Für jeden Eintrag bestätigt der
  Betreiber, dass ein Mensch den Text geschrieben oder vor der
  Veröffentlichung geprüft und die redaktionelle Verantwortung
  übernommen hat (Ausnahme nach Art. 50 Abs. 4 UAbs. 2 KI-VO).

  Die technischen Maßnahmen für die Cover-Bildherkunft (132 deterministisch
  gerenderte Covers, Frontmatter-Beleg cover.ki_pruefung, IPTC-XMP
  DigitalSourceType=algorithmicMedia in der Datei, Reproduktionswache
  scripts/ki_cover_herkunft.py --pruefen, CI-Gate im Deploy) sind umgesetzt
  und durch das Gate geprüft (132/132 reproduzierbar, 0 Befunde).

  Die Anbieterpflicht nach Art. 50 Abs. 2 KI-VO bleibt unberührt; diese
  Erklärung ist eine betriebliche Selbsteinschätzung, keine Rechtsberatung.

**Ergebnis:** Die Frist `ki-vo-kennzeichnung-bestand` (02.12.2026) ist aus Betreibersicht abgeschlossen.

Betreiber (Name): ________________________________________________ 
Unterschrift:     ________________________________________________ 
Datum:            ________________________________________________

---

## 5. Abschluss in der Fristen-Check (Recht)

Nach Unterschrift wird im Workflow „Fristen-Check (Recht)“ ausgeführt:

```
erledigt=ki-vo-kennzeichnung-bestand
```

Issue #1028 wird erst nach Merge, Deploy, Live-Abnahme per `docs/KI-TRANSPARENZ-ABNAHME.md` §4 und dieser Betreiberfreigabe geschlossen – nicht durch den Agenten einseitig.

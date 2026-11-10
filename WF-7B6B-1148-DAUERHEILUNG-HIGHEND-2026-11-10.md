# Vorgang WF-7B6B · #1148 – Dauerheilung (Quellenkette eines veröffentlichten Artikels)

**Datum:** 10.11.2026
**Meldung:** #1148 „🔧 Wartung · Lesbarkeit & Gestaltung · Vorgang WF-7B6B“ (Alert-Key `WF-7B6B`, Bereich *Lesbarkeit & Gestaltung*, Workflow *E2E-Tests (Playwright)*, Job *Playwright-Suite (Desktop + Mobile)*)
**Auslöser:** Geplanter Lauf **42823676289** auf `main` (Commit `8b173b07`, 10.11.2026, 14:20:47 UTC). Der Schritt „Metadaten-Wache – Quelle (Titel, Description, Belege)“ war rot. Die Meldung war seit 09.11. 14:43 offen.
**Basis:** `90aa12b` (`main`) · **Branch:** `arena/b162c6b1-franksfinanzcheck-blog`

---

## Kurzfassung

- **Ursache:** Der Artikel `content/posts/2026-11-05-waschmaschine-beladen-weniger-kosten-bei-jedem-waschgang/index.md` ist live (`draft: false`, `reserve_published: 2026-11-09`), hat aber **kein `quellen`** im Frontmatter. Die Metadaten-Wache meldet dafür M4. Das ist der einzige Befund im Bestand (127 Dateien).
- **Verschärfend:** Die Fachprüfung des Recherche-Dossiers (`data/research/artikel/2026-11-05-waschmaschine-beladen-weniger-kosten-bei-jedem-waschgang.md`, KI-Fachprüfung vom 05.11.) hatte die Kernzahlen als `luecke` markiert. Die verlinkte Referenzseite der Bundesnetzagentur belegt keine davon. Außerdem widersprach die **Kurzantwort** der **eigenen Modellrechnung** im Text: Die Kurzantwort nannte „bis zu 15 %“ und „rund 5 € pro Jahr“, die Modellrechnung ergibt 22 € pro Jahr (100 volle Ladungen 61 €, 200 halbe 83 €).
- **Sofortheilung (dieser Vorgang):**
  1. Zwei **geprüfte** Quellen in `quellen` eingetragen (Schema wie bei den übrigen Artikeln: `id`, `titel`, `url`, `herausgeber`, `datum`). Beide Seiten wurden am 10.11.2026 abgerufen und inhaltlich gegengelesen (Abschnitt 4).
  2. Die Kurzantwort auf die **Modellrechnung des Artikels** umgestellt. Die Zahlen stammen jetzt aus dem Textabschnitt, sind als Rechnung gekennzeichnet, und die unbelegten Prozent- und Euro-Angaben sind weg.
- **Dauerheilung der Klasse:** Die Metadaten-Wache bleibt hart, der Nachweis läuft über die bestehenden Gates (Abschnitt 5). Eine neue Sperre im Publish-Pfad wäre eine Policy-Änderung (C34) und liegt beim Inhaber (Abschnitt 6).

---

## 1. Zeitleiste (UTC)

| Zeit | Ereignis | Beleg |
|---|---|---|
| 05.11. 12:42 | Faktenfrische erzeugt Dossier. Die Fachprüfung markiert Kernzahlen als `luecke` (keine belegende Quelle) | `data/research/artikel/2026-11-05-waschmaschine-…md` |
| 09.11. 11:26 | Artikel mit `date: 2026-11-09T11:26:12Z`, `draft: false`, `reserve_published: 2026-11-09` | Frontmatter |
| 09.11. 14:43 | Erste Meldung zu M4 (Alert-Key WF-7B6B, offen seit diesem Zeitpunkt) | Issue #1148 |
| 10.11. 14:20 | Geplanter E2E-Lauf 42823676289 rot im Schritt „Metadaten-Wache – Quelle“ | Run-Meldung |
| 10.11. | Lokale Reproduktion: `scripts/metadaten_wache.py` → `M4 Keine Quelle im Frontmatter (quellen)`, Exit 1 | Abschnitt 5 |
| 10.11. | Heilung: Quellen eingetragen, Kurzantwort korrigiert, Wache Exit 0 | Abschnitt 3 |

Der Lauf-Log war von hier nicht abrufbar (`gh run view --log-failed`: EOF auf dem Log-Endpunkt). Die Ursache ist deshalb aus dem Repo-Stand reproduziert, nicht aus dem Log gelesen.

---

## 2. Ursache

Der Artikel stammt aus der Content-Engine. `scripts/engine_generate.py` schreibt das Frontmatter **ohne** `quellen`. Die Belegkette soll danach die Faktenfrische ergänzen (Docs: `docs/ANLEITUNG-FAKTENFRISCHE.md`: „Die Maschine schreibt `quellen` selbst“). Hier kam sie nicht zustande, der Artikel stand aber trotzdem auf `draft: false`.

Dass der Befund den Deploy nicht gestoppt hat, hat einen klaren Grund: Die Metadaten-Wache läuft im Deploy-Pfad **toleriert** (C34, Befund wird gemeldet, blockiert nicht). Der E2E-Lauf ist das harte Signal, und er ist kein Pflicht-Check für `main`. Die Scorecard stuft „Artikel ohne Belegkette“ für die Risikoklasse `standard` nur als Warnung (`Q2-quellen-vorhanden`) ein.

---

## 3. Heilung: was geändert wurde

| Datei | Änderung |
|---|---|
| `content/posts/2026-11-05-waschmaschine-beladen-weniger-kosten-bei-jedem-waschgang/index.md` | `quellen` mit zwei Einträgen eingefügt (Q1 Umweltbundesamt, Q2 Verbraucherzentrale Niedersachsen). `kurzantwort` neu gefasst: volle Trommel nach UBA, Modellrechnung 61 € / 83 € / 22 € pro Jahr, gekennzeichnet als Rechnung. Unbelegte Angaben („bis zu 15 %“, „0,5 kWh“, „5 Liter“, „rund 5 €“) entfernt. |
| `WF-7B6B-1148-DAUERHEILUNG-HIGHEND-2026-11-10.md` (neu) | dieser Bericht |

**Nicht geändert:** Titel, Description, Cover, `faktencheck`-Datum (`2026-11-05`), Fließtext, Tags, Offenlegung. Das `faktencheck`-Datum bleibt bewusst auf dem Stand der Fachprüfung. Eine neue Prüfung ist nicht erfolgt, und das Datum soll keine Prüfung behaupten, die es nicht gab.

**Entscheidungen im Detail:**

- **Keine erfundenen Quellen.** Jede Quelle wurde vor dem Eintrag abgerufen und gelesen. Die Referenz der Bundesnetzagentur aus dem Dossier wurde **nicht** übernommen, weil sie die Aussagen nicht belegt.
- **Rang und Herausgeber.** Umweltbundesamt (Bundesbehörde) und Verbraucherzentrale (anerkannte Verbraucherberatung) sind Primär- bzw. anerkannte Sekundärquellen.
- **Modellzahlen bleiben Modell.** Die 22 € beruhen auf Annahmen (0,9 kWh bzw. 0,6 kWh je Ladung, 0,40 €/kWh, 0,005 €/Liter). Diese stehen im Fließtext unter „Annahmen für die Modellrechnung“. Die Kurzantwort verweist darauf und behauptet keine Messung. Ob diese Annahmen für Leser zutreffen, ist eine Redaktionsfrage (Abschnitt 6).
- **Kein Eingriff in den Fließtext.** Der Fließtext wurde nicht umgeschrieben. Die Lesbarkeit ist eine eigene Aufgabe (Abschnitt 6), und sie sollte nicht als Nebeneffekt dieses Gate-Fixes passieren.

---

## 4. Belegprüfung (am 10.11.2026)

| Quelle | Abgerufen | Gelesene Aussage | Belegt im Artikel |
|---|---|---|---|
| Umweltbundesamt, „Klimabewusstes Wäschewaschen entlastet die Umwelt und spart Kosten“ (zuletzt aktualisiert 02.12.2024) | ja | Koch-/Buntwäsche voll beladen, „gerade noch eine Handbreit Luft“. Volle Trommel spart Energie, Wasser und Geld. Pflegeleicht zur Hälfte, Feinwäsche ein Viertel, Wolle ein Fünftel | Kurzantwort, Handbreit-Regel, Füllmengen |
| Verbraucherzentrale Niedersachsen, „Stromsparmythen – Zwischen Legende und Wirklichkeit“ (Stand 24.06.2026) | ja | „Zur Hälfte gefüllte Maschinen verbrauchen unnötig viel Waschmittel, Strom und Wasser.“ | Q2 in der Belegkette. Im Fließtext nicht eigens zitiert |

**Nicht belegt und nicht mehr behauptet:** „bis zu 15 % weniger Wasser und Energie“, „0,5 kWh und 5 Liter“, „rund 5 € pro Jahr bei 4 Waschgängen“. Außerdem stehen im Fließtext noch unbelegte Praxisaussagen zu Verschleiß („Lagerschaden … wirtschaftliches Aus“, Schäden durch Kleinteile). Sie sind als offene Punkte geführt (Abschnitt 6).

---

## 5. Beweis

| Prüfung | Ergebnis |
|---|---|
| `python3 scripts/metadaten_wache.py` **vor** der Heilung | ❌ Befunde: 1 – M4 „Keine Quelle im Frontmatter (quellen)“, Exit 1 (Reproduktion des Alarms) |
| `python3 scripts/metadaten_wache.py` **nach** der Heilung | ✅ Befunde: 0 · Selbsttest 13 Proben + Heiler-Proben grün |
| YAML-Parse des Frontmatters (PyYAML, `requirements-ci.txt`) | ✅ `quellen: [Q1, Q2]`, `faktencheck: 2026-11-05`, Kurzantwort lesbar |
| `python3 scripts/frontmatter_wache.py` | ✅ 156 Dateien · Blocker 0 · Tiefenprüfung YAML-Parser |
| `python3 scripts/tabellen_lesbarkeit_guard.py` | ✅ Exit 0 |
| `python3 -m unittest scripts.tests.test_metadaten_wache scripts.tests.test_keyword_optimizer scripts.tests.test_meta_optimizer scripts.tests.test_serp_limits` | ✅ 77 Tests |
| `hugo --destination /tmp/ff-public` (Hugo 0.169.0, Pin aus `requirements-hugo.txt`) | ✅ Exit 0 |
| Gerenderte Seite | ✅ Quellenbox mit beiden Links (Q1, Q2), neue Kurzantwort sichtbar |
| `python3 scripts/seo_cockpit.py --build /tmp/ff-public --fail-on description-length,description-breite,heading-order` | ✅ P1 0 · P2 0 |
| `python3 scripts/linktext_wache.py --public /tmp/ff-public` | ✅ 412 Seiten · 13.350 Links |
| `python3 scripts/h1_wache.py --public /tmp/ff-public` | ✅ jede Seite genau eine H1 |

**Nicht lokal bewiesen:** Der Alarm-Lauf selbst (Playwright-Suite). Den Nachweis liefert der nächste geplante Lauf auf `main` bzw. der PR-Lauf.

---

## 6. Offene Punkte (nicht Teil dieses Vorgangs)

1. **Publish-Pfad ohne Quellenpflicht (Governance, C34).** Die Engine erzeugt Entwürfe ohne `quellen`, und `draft: false` kann ohne Belegkette gesetzt werden. Eine harte Sperre im Publish-Gate wäre eine Änderung der dokumentierten C34-Entscheidung. Das entscheidet der Inhaber. Empfehlung: M4 als Pflicht-Check für Veröffentlichungen mit `draft: false` ab einem festen Stichtag, mit Vorlauf für bestehende Entwürfe.
2. **Fachprüfung des Artikels.** Die Verschleiß-Aussagen (Stoßdämpfer, Lagerschaden, Heizstäbe) sind unbelegt. Der Abschnitt „Rechnet man den geringeren Verschleiß und die Einsparung bei Waschmittel hinzu, wird der Hebel noch größer“ ist ebenfalls unbelegt und sollte gestrichen oder belegt werden. Die Modellannahmen (0,9/0,6 kWh, 50/35 Liter, 0,40 €/kWh, 0,005 €/Liter) sollten gegen eine Quelle geprüft werden. Dafür braucht es einen Menschen; Text entscheidet die Redaktion.
3. **Lesbarkeit und Gestaltung des Artikels.** Der Fließtext ist kurzsatzig und stellenweise holprig („Richtiges Waschmaschine beladen senkt deine Fixkosten“ in der Description), enthält Füllphrasen („Du handelst nach dem 4K-Prinzip“) und Wiederholungen. Eine Überarbeitung gehört in eine eigene Aufgabe mit Lesbarkeitsmessung (`scripts/readability_check.py`) und Redaktionsfreigabe. Sie wurde hier bewusst nicht als Nebeneffekt gemacht.
4. **Abschlussvermerk.** Der PR trägt `Closes #1148`. Den Vermerk schreibt `vorgangs-abschluss.yml` (Regel D2), nicht ein Agent von Hand.

---

## 7. Hinweis zur Vollsuite

Nicht ausgeführt: `python3 -m unittest discover -s scripts/tests` (Vollsuite). Der vorige Vorgang hatte dort vier Fehlschläge gefunden, die auch auf `origin/main` rot sind (Inhalts-Register, Versicherungs-Cluster). Dieser Vorgang ändert nur Frontmatter und Kurzantwort eines Artikels; die betroffenen Gates sind oben einzeln grün gelaufen.

# 🔧 Zwei Bestandsbefunde behoben – Ursachen, Belege, Nachmessung

**Datum:** 26.09.2026 · **Auslöser:** erster vollständiger Messlauf der
Design-Varianten-Werkbank (`DESIGN-VARIANTEN-WERKBANK-2026-09-26.md`).
Beide Befunde betrafen den **Bestand**, nicht die geprüfte Variante.

| Befund | Vorher | Nachher |
|---|---:|---:|
| DOM-Kinder (Maximum über alle 221 Seiten) | **58** | **49** |
| Lighthouse-LCP mobil (Startseite) | **3179 ms** | **1760 ms** |
| Lighthouse-Performance mobil | 0,93 | **0,99** |
| Gate-Urteil | 2 × P3 offen | **keine Befunde** |

---

## Befund 1 – DOM-Kinder 58: ein Konstruktionsfehler, kein Inhaltsproblem

### Diagnose

Die 58 Kinder waren **58 × `div.ff-content-chunk`** – reine Hüllen, kein
Inhalt. Erzeugt von `layouts/_partials/sectioned_content.html`, das lange
Ratgeber gruppiert, damit kein Element zu viele Kinder bekommt.

Die Historie dieses Partials erklärt den Fehler:

| Bauweise | Ergebnis am längsten Ratgeber (32 H2 + 25 H3) |
|---|---|
| nur an H2 geteilt | ein H2-Abschnitt sammelte bis zu 58 Blöcke |
| flach an H2 **und** H3 (21.09.2026) | 59 Chunks nebeneinander → wieder 58 Kinder |
| **zweistufig (26.09.2026)** | **33 Kinder, größte Gruppe 7** |

Die flache Teilung hat das Problem nur verschoben: Sie tauscht „ein Chunk
mit vielen Kindern" gegen „viele Chunks" – und weil alle Chunks
nebeneinander unter `.post-content` hängen, ist **die Zahl der Chunks
selbst** die neue Obergrenze. Nur eine zweistufige Gruppierung beschränkt
beide Dimensionen.

### Änderung

```
.post-content
  └── div.ff-content-section        (eine je H2-Abschnitt)
        └── div.ff-content-chunk    (H2-Block, danach je H3 einer)
```

Beide Ebenen sind `display: contents` – es entsteht **keine einzige**
zusätzliche Layout-Box. Zusätzlich werden leere Hüllen entfernt, die
entstehen, wenn ein Artikel direkt mit einer Überschrift beginnt.

### Beleg: pixelgleich, nicht „sollte gleich sein"

Vorher- und Nachher-Build wurden gegeneinander vermessen – jede sichtbare
Box nach Position, Größe und Reihenfolge:

```
✓ 1280px /                        278 Boxen, 6330 px hoch
✓ 1280px /posts/                  280 Boxen, 5933 px hoch
✓ 1280px /posts/…standby-kosten/  951 Boxen, 20649 px hoch
✓ 1280px /posts/…energiediebe/    914 Boxen, 16729 px hoch
✓  390px (dieselben vier Seiten)

4832 Element-Geometrien verglichen, 0 Abweichungen > 1 px
```

Kosten: **+12 DOM-Elemente** auf der schwersten Seite (1034 → 1046,
Frühwarnung 1100). Genau der Tausch, den das Budget belohnt – Kinder und
Tiefe sind die knappen Größen, die Gesamtzahl hat Luft.

### Nachmessung

```
✅ Kinder/Element: max. 49 (html > head) – Frühwarnung 54, Grenze 60
✅ Head-DOM:       max. 49              – Frühwarnung 52, Grenze 58
✅ Tiefe:          max. 13              – Frühwarnung 28, Grenze 32
✅ Elemente:       max. 1046            – Frühwarnung 1100, Grenze 1400
```

Der Chunker-Vertrag aus `scripts/layout_audit.py` hält: 1456 Überschriften
geprüft, alle auf Blockebene.

---

## Befund 2 – LCP 3179 ms: die Messumgebung war schuld, aber anders als vermutet

Dieser Befund hat **drei** Fehler nacheinander aufgedeckt. Zwei davon
waren meine.

### Fehler A – meine erste Einordnung war falsch

Ich hatte den Wert als „gedrosselte Sandbox, nicht belastbar" abgetan.
Vier Läufe widerlegen das:

| Lauf | benchmarkIndex | FCP | LCP |
|---|---:|---:|---:|
| 1 | 1779 | 1558 ms | 3038 ms |
| 2 | 2000 | 1549 ms | 2967 ms |
| 3 | 2212 | 1561 ms | 3154 ms |
| 4 | 1692 | 1524 ms | 3101 ms |

Die CPU-Güte schwankte um 31 %, der LCP nur um 187 ms. Der Wert war
**stabil und reproduzierbar** – also ein Strukturwert, keine Streuung.

### Fehler B – die Messung lief mobil, während die Konfiguration desktop sagte

`e2e/variant-metrics.mjs` übergab `settings: { preset: 'desktop' }` an die
Lighthouse-**Node-API**. Die kennt `preset` nicht – das ist ein
CLI-Begriff – und ignoriert es stillschweigend:

| Aufruf | formFactor | FCP | LCP | Perf |
|---|---|---:|---:|---:|
| `settings: { preset: 'desktop' }` | **mobile** | 1518 ms | 3166 ms | 0,92 |
| echtes Desktop-Config-Objekt | desktop | 369 ms | **622 ms** | **1,00** |
| echtes Mobile-Profil | mobile | 1556 ms | 3158 ms | 0,93 |

Gemessen wurde also mobil, während `lighthouserc.cjs` desktop deklarierte:
zwei Wahrheiten über dieselbe Zahl – genau das, was diese Werkbank
verhindern soll.

**Behoben:** Profile werden nur noch über echte Config-Objekte gesetzt.
Gemessen werden **beide** – mobil als maßgeblich (Google bewertet Core Web
Vitals überwiegend am mobilen Feld), desktop zum Vergleich. Jede Messung
schreibt ihre Bedingungen mit: `formFactor`, `cpu_faktor`, `netz_kbps`,
`benchmark_index`. `lighthouserc.cjs` misst jetzt dasselbe Profil.

### Fehler C – die eigentliche Ursache: der Test-Server komprimierte nicht

Das LCP-Element ist das erste Artikel-Cover, und es ist bereits optimal
konfiguriert – `lcp-discovery-insight` gibt volle Punktzahl:

```
fetchpriority=high applied                      ✓
Request is discoverable in initial document     ✓
LCP resources should not use loading=lazy       ✓
```

Die beobachtete Aufschlüsselung summiert sich auf **262 ms**
(TTFB 23 + Ladeverzögerung 51 + Laden 8 + Render 180). Der Widerspruch
zu 3179 ms löste sich beim Blick auf die Übertragung:

```
Dokument: transfer 190 547 B · resource 190 320 B   →  null Kompression
```

`e2e/server.mjs` lieferte Text unkomprimiert aus. **GitHub Pages tut das
nicht** – dort gehen HTML/CSS/JS/SVG/XML mit gzip bzw. brotli über die
Leitung. Auf Lighthouses simuliertem Mobilfunk (1638 kbps ≈ 205 KB/s)
waren das rund 0,7 s Ladezeit, die es in Produktion nie gab.

**Behoben:** Der Test-Server komprimiert jetzt dieselben Typen wie Pages –
weiterhin ohne jede Abhängigkeit (`node:zlib` ist eingebaut).

```
ohne Accept-Encoding: 190 320 B
mit gzip:              36 793 B   (−81 %)
mit brotli:            31 016 B   (−84 %)
```

### Nachmessung

| Profil | LCP vorher | LCP nachher | Performance |
|---|---:|---:|---:|
| **mobil** (maßgeblich) | 3179 ms | **1760 ms** | 0,93 → **0,99** |
| desktop | 674 ms | **573 ms** | 1,00 → 1,00 |

Budget 2500 ms mit Reserve eingehalten.

> **Tragweite über diese Aufgabe hinaus:** Die fehlende Kompression betraf
> **jede** Performance-Messung dieses Repos, nicht nur die Werkbank. Eine
> Messumgebung, die pessimistischer ist als die Wirklichkeit, erzeugt
> Befunde, die niemand beheben kann – und verdeckt die, die zählen.

---

## Regressionswächter

Jeder behobene Fehler hat jetzt einen Test:

| Zusage | Test |
|---|---|
| Gruppierung bleibt zweistufig (H3 öffnet keine äußere Ebene) | `scripts/tests/test_content_chunker.py::Gruppierung` |
| Beide Ebenen behalten `display: contents` | dito |
| Keine leeren Gruppierungshüllen im HTML | `…::BudgetImBuild` |
| Keine Seite über der Kinder-Frühwarnung | `…::BudgetImBuild` |
| Test-Server komprimiert wie Pages | `e2e/design-variante.spec.mjs` |
| Lighthouse-Profil steht in der Messdatei | `e2e/variant-metrics.mjs` (`formFactor` je Profil) |

**Testlauf:** 917 Python-Tests OK (15 übersprungen) · 5/5 Design-Varianten-Specs
grün · DOM-Audit alle vier Budgets grün · Chunker-Vertrag 1456 Überschriften
geprüft.

---

## Offen

* **Ungenutztes CSS:** Lighthouse meldet ~94 KiB der 129 KB Inline-CSS als
  auf der Startseite ungenutzt. Das ist kein toter Code – es ist
  überwiegend Artikel-CSS, das auf Artikelseiten gebraucht wird. Ein
  Aufteilen nach Seitentyp säße in `layouts/_partials/head.html`, und die
  Datei ist **KRITISCH-versiegelt** (`scripts/integrity_guard.py`):
  Änderungen dort sind eine menschliche Entscheidung mit Neusignatur, keine
  Agentenroutine. Nach der Kompressionskorrektur ist der Druck gering
  (LCP mobil 1760 ms bei Budget 2500 ms) – der Punkt gehört auf die Liste,
  nicht in diesen Commit.

# Werbe-Offenlegung auf Premium-Niveau – artikelgenau, sichtbar, dauerhaft

**Datum:** 28.09.2026 · **Auslöser:** `KONKURRENZANALYSE-ZEIT-ONLINE-2026-09-28.md`,
Zeile „Unabhängigkeit/Kommerz | ZEIT **5** | FF **4**" ·
**Auftrag:** „dauerhaft auf ZEIT-Niveau bzw. Premium-Level einer Profi-Agentur"

---

## 1. Der Befund, ehrlich gemessen

Die Analyse formulierte es freundlich: *„FF hat Affiliate-Governance;
Offenlegung sollte artikelgenau und noch sichtbarer sein."* Die Messung am
gebauten HTML war weniger freundlich:

| Messpunkt (Build vor der Änderung) | Wert |
|---|---|
| Seiten mit Partnerlinks | 48 |
| davon **ohne jeden** Hinweis | 0 |
| davon mit Offenlegung **vor** dem ersten Partnerlink | **21 (44 %)** |
| Abstand Offenlegung ↔ erster Partnerlink (Abbinder-Fall) | **20 000–40 000 Zeichen dahinter** |
| Aussage der Kennzeichnung | „**kann** Affiliate-Links enthalten" – Möglichkeitsform, pauschal, ohne Partner und ohne Zahl |

Drei Schwächen, die eine Bewertung von 4 statt 5 exakt beschreiben:

1. **Zu spät.** In mehr als der Hälfte der Artikel stand die Offenlegung unter
   dem Text – also nach dem Klick, den sie erklären soll.
2. **Zu unbestimmt.** „Kann enthalten" ist eine Formel, die für jeden Artikel
   gleich gilt und deshalb von niemandem gelesen wird.
3. **Nicht nachgewiesen.** Es gab keine Wache, die den Zustand hält. Er hätte
   beim nächsten Layout-Umbau lautlos verschwinden können.

---

## 2. Was jetzt gilt

### Sichtbar, oben, in eigenen Worten

Im Artikelkopf – direkt unter Titel und Prüfzeile, **vor** der ersten Zeile
Text – steht eine Kennzeichnung, die für jeden Artikel anders lautet.
Echtes Beispiel aus dem aktuellen Build (Gas-Preisgarantie):

> **Werbung · 2 Partnerlinks in diesem Artikel: CHECK24 (Gastarife).
> Provision nur bei Abschluss, für dich ohne Aufpreis.** ▸ Was das bedeutet

Aufgeklappt folgt die Aufschlüsselung je Partner („CHECK24 – Gastarife ·
2 Links"), der Satz zur Provision inklusive Netzwerk, was die Provision
**nicht** beeinflusst (Themenwahl, Empfehlung, Reihenfolge, Zahlen) – und der
Weg zur vollständigen Offenlegung unter `/transparenz/`.

Auf dem Ratgeber-Hub steht dieselbe Logik mit den Zahlen der Seite:

> **Werbung · 12 Partnerlinks auf dieser Seite: CHECK24 (Stromtarife, DSL- &
> Internettarife, Mietwagen), Tarifcheck (Privathaftpflicht) und C24 Bank
> (Girokonto, Tagesgeld).**

Und – der Teil, den Wettbewerber meist weglassen – **Artikel ohne
Partnerlinks sagen das ebenfalls**:

> **Werbefrei** · Keine Partnerlinks in diesem Artikel. Wir verdienen an
> diesem Text nichts.

Damit ist die Kennzeichnung kein Rechtshinweis mehr, sondern eine Information
mit Nachrichtenwert. Genau das unterscheidet Premium von Pflichterfüllung.

### Artikelgenau heißt: aus dem gebauten HTML hergeleitet

Gezählt wird, was wirklich gerendert wurde – nicht, was jemand im Frontmatter
behauptet. Eine Quelle (`data/affiliate_ziele.yaml`) versorgt drei Verbraucher
(Kopf-Kennzeichnung, Abbinder, Partnerregister auf `/transparenz/`).

### Messung nach der Änderung

| Messpunkt (Build nach der Änderung) | Wert |
|---|---|
| Geprüfte Seiten | **49** |
| Seiten mit Partnerlinks | **49** |
| davon Kennzeichnung **vor** dem ersten Partnerlink | **49 (100 %)** |
| Abstand Kennzeichnung → erster Partnerlink | **8 106 – 39 566 Zeichen davor** (Median 16 299) |
| Partnerlinks insgesamt / Spanne je Seite | 155 · 2 bis 12 |
| Abweichung genannte ↔ tatsächliche Partner/Anzahl | **0** |
| Registrierte Ziele auf `/transparenz/` | **20/20** |
| Artikel ohne Partnerlinks | tragen sichtbar „Werbefrei" (real gegengeprüft) |

Aus „44 % zu spät" wurde „100 % vorher" – und aus einer Pauschalformel eine
artikelgenaue Angabe.

---

## 3. Warum das dauerhaft ist (der eigentliche Auftrag)

Eine Einmal-Änderung an Templates hält genau bis zum nächsten Refactoring.
Deshalb hängt der Zustand an **fünf unabhängigen Nachweisen**:

| Ebene | Was sie beweist | Befund-Verhalten |
|---|---|---|
| `scripts/offenlegung_gate.py` (O1–O7) | Existenz, Position vor dem ersten Link, Zahl/Partner artikelgenau, Pflichtangaben, Sichtbarkeit, Widerspruchsfreiheit, Partnerregister – am **gebauten** HTML | fail-closed, Exit 1 |
| `scripts/publish_gate.py` **Gate 6** | Kein druckfrischer Artikel geht ohne saubere Kennzeichnung live | Hartstopp, Kandidat mit Grund abgelehnt |
| `scripts/bestand_gate.py` | Täglicher Bestandslauf (im `affiliate-integrity-daily`-Workflow) meldet Rückfälle | Befund, **keine** Heilung (C15) |
| `scripts/tests/test_offenlegung_gate.py` (36 Tests) | Verhalten je Vertrag, Robustheit gegen Minifizierung/Attributreihenfolge, Bauteil-Invarianten in den vier Layouts | rot im Unit-Lauf |
| `e2e/affiliate-guard.spec.mjs` | Browser-Wahrheit: sichtbar, ≥ 12 px, nicht transparent, geometrisch **über** dem ersten Partnerlink, `/transparenz/` erreichbar | rot in `npm run test:e2e` |

Dazu `governance_contract.py` (C6): Die Wache muss einen `--selftest` haben –
er sabotiert sie mit **13 Proben** (fehlende Kennzeichnung, falsche Zahl,
verschwiegener Partner, `display:none`, `hidden`, `font-size:0`,
`aria-hidden`, Widerspruch Kopf/Abbinder …) und verlangt, dass sie jede davon
erkennt. Eine Wache, die nicht beweisen kann, dass sie noch sehen kann, ist
nur ein grüner Haken.

### Bewusst **keine** Selbstheilung

Die Kennzeichnung entsteht im Layout, nicht im Artikeltext. Ein Befund heißt
deshalb immer: Template, CSS oder Partnerregister sind defekt. Ein „Heiler",
der am Kandidaten herumschreibt, würde genau diesen Defekt übertünchen. Die
Ausnahme ist in `scripts/reserve_healer_coverage.py` begründet hinterlegt –
und die Deckungs-Wache prüft, dass diese Begründung nicht still veraltet.

---

## 4. Geänderte und neue Dateien

**Neu**

| Datei | Zweck |
|---|---|
| `layouts/_partials/_funcs/affiliate_offenlegung.html` | SSOT: zählt Partnerlinks der gerenderten Seite, ordnet sie dem Register zu |
| `layouts/_partials/ff_offenlegung.html` | Sichtbares Bauteil (beide Varianten) inkl. Data-Attributen für Wache und E2E |
| `layouts/shortcodes/partnerliste.html` | Partnerregister-Tabelle, generiert aus `data/affiliate_ziele.yaml` |
| `content/transparenz/index.md` | Vollständige Offenlegungsseite (8 Abschnitte, Partnerliste, Geld-/Redaktionstrennung) |
| `scripts/offenlegung_gate.py` | Wache O1–O7, Selbsttest, JSON, Verlauf |
| `scripts/tests/test_offenlegung_gate.py` | 36 Regressionstests |
| `docs/ANLEITUNG-OFFENLEGUNG.md` | Runbuch: Befund → Handgriff, neuen Partner aufnehmen |

**Geändert:** `layouts/single.html`, `layouts/_default/single.html`,
`layouts/pillar/single.html`, `layouts/pillar/list.html` (Einbau im Kopf;
Pillar mit `extraKeys`, weil Template-CTAs nicht in `.Content` stehen),
`layouts/_partials/trust_box.html` (Abbinder aus demselben SSOT),
`layouts/_partials/footer.html` (Dauerlink „Transparenz & Werbung"),
`layouts/_partials/schema_article.html` (`publishingPrinciples` auf Article-
und Publisher-Ebene → maschinenlesbare Unabhängigkeitsangabe),
`assets/css/extended/z-premium-blog.css` (Block „WERBE-OFFENLEGUNG" inkl. Dark
Mode, Mobile, Reduced Motion), `scripts/publish_gate.py`,
`scripts/bestand_gate.py`, `scripts/governance_contract.py`,
`scripts/reserve_healer_coverage.py`, `package.json`,
`e2e/affiliate-guard.spec.mjs`, `content/methodik/index.md`.

---

## 5. Entscheidungen, die bewusst so getroffen wurden

* **Kein Menüeintrag für `/transparenz/`.** Die Hauptnavigation ist kuratiert;
  der Weg führt über die Kennzeichnung in jedem Artikel und den Footer – dort,
  wo die Frage tatsächlich entsteht.
* **Aufklappbar statt Textwand.** Die Kernaussage (Werbung, Anzahl, Partner,
  kein Aufpreis) steht immer sichtbar; Details liegen einen Klick entfernt.
  Kein Accordion-Trick: Der sichtbare Teil enthält bereits alles Pflichtige,
  und O5 verbietet jede Sichtbarkeits-Manipulation.
* **Der alte Satz im Abbinder bleibt.** Das Wort „Affiliate-Links" ist Teil des
  bestehenden A1-Vertrags von `affiliate_profi_check.py` – die neue
  Kennzeichnung ergänzt, sie ersetzt nicht.
* **Quotes optional beim Parsen.** `hugo --minify` schreibt
  `data-ff-offenlegung=mit-partnerlinks` ohne Anführungszeichen. Die Wache
  parst attribut-tolerant – die Lehre aus dem Vorfall „stille Blindheit"
  (01./02.09.2026), bei dem eine strikte Regex still nichts mehr fand.

---

## 6. Bewertung neu

| Dimension | ZEIT | FF vorher | FF jetzt |
|---|---|---|---|
| Unabhängigkeit/Kommerz | 5 | 4 | **5** |

Begründung für die 5: artikelgenaue Angabe **vor** dem ersten Werbelink auf
100 % der Seiten, namentliche Partner mit Produkt und Anzahl, aktive
„Werbefrei"-Aussage, vollständige Offenlegungsseite mit Partnerregister,
maschinenlesbare `publishingPrinciples` – und ein fail-closed Nachweis auf
fünf Ebenen, der den Zustand hält, statt ihn zu behaupten.

**Nicht behauptet wird:** dass damit die redaktionelle Unabhängigkeit *im
Prüfprozess* erreicht wäre. Das ist die Dimension „Menschliche
Zweitredaktion" (5 : 2) und bleibt offen.

# Anleitung: Artikelgenaue Werbe-Offenlegung (seit 28.09.2026)

**Kurzfassung:** Jeder Artikel sagt **oben**, **konkret** und **in eigenen
Worten**, wie er Geld verdient – mit der echten Zahl seiner Partnerlinks, den
echten Partnernamen und einem Weg zur vollständigen Offenlegung
(`/transparenz/`). Kein Mensch pflegt das von Hand: Das Layout leitet die
Angaben aus den tatsächlich gerenderten Links her, und die Wache
`scripts/offenlegung_gate.py` beweist es an jedem Build.

---

## 1. Warum es das gibt

Der Wettbewerbsvergleich mit ZEIT Online (28.09.2026) bewertete die Dimension
„Unabhängigkeit/Kommerz" mit **ZEIT 5 : FF 4**. Der Befund war nicht
„Kennzeichnung fehlt", sondern präziser – und unangenehmer:

* Die Offenlegung stand **pauschal** im Abbinder („kann Affiliate-Links
  enthalten") – eine Möglichkeitsform für etwas, das entweder stimmt oder nicht.
* Sie stand **unter** dem Text: gemessen 20 000–40 000 Zeichen HTML **nach** dem
  ersten Partnerlink. Nur **21 von 48** Seiten (44 %) kennzeichneten oberhalb
  des ersten Werbelinks.
* Sie war **unspezifisch**: kein Partnername, keine Anzahl, kein Bezug zum
  konkreten Artikel.

Wer erst nach dem Klick erfährt, dass der Klick Geld bringt, ist zu spät
informiert. Premium heißt hier: **vor** dem ersten Werbelink, **artikelgenau**,
**sichtbar** – und dauerhaft nachgewiesen.

---

## 2. Was ein Leser jetzt sieht

Im Artikelkopf, direkt unter Titel und Prüfzeile:

> **Werbung · 6 Partnerlinks** — Dieser Artikel enthält 6 Partnerlinks zu
> CHECK24 (Stromtarife, Gastarife) und Tarifcheck (Kfz-Versicherung).
> Provision nur bei Abschluss, für dich ohne Aufpreis. ▸ Was das für dich
> bedeutet

Aufgeklappt: welche Partner, welche Produkte, wie viele Links, warum es sie
gibt, was sie **nicht** beeinflussen – plus Link auf `/transparenz/`.

Artikel **ohne** Partnerlinks tragen denselben Platz mit umgekehrter Aussage:

> **Werbefrei** — Keine Partnerlinks in diesem Artikel. Wir verdienen an diesem
> Text nichts.

Das ist der eigentliche Gewinn: Die Kennzeichnung ist keine Floskel mehr,
sondern eine **Aussage, die von Artikel zu Artikel verschieden ist** – und
deshalb gelesen wird.

---

## 3. Wie es technisch entsteht (eine Quelle, drei Verbraucher)

```
data/affiliate_ziele.yaml            SSOT: /go/-Key → Partner, Produkt, Netzwerk
        │
        ▼
layouts/_partials/_funcs/affiliate_offenlegung.html     zählt + ordnet zu
        │            (liest die gerenderte Seite, nicht das Markdown)
        ├────────────► layouts/_partials/ff_offenlegung.html   Kopf-Kennzeichnung
        ├────────────► layouts/_partials/trust_box.html        Abbinder
        └────────────► layouts/shortcodes/partnerliste.html    /transparenz/
```

* **Gezählt wird, was wirklich im HTML steht** – `.Content` nach dem Rendern,
  inklusive Shortcode-CTAs. Kein Frontmatter-Flag, das jemand zu setzen
  vergisst.
* Template-CTAs, die **nicht** in `.Content` stehen (Pillar-Hub), reicht das
  Layout als `extraKeys` nach: `partial "ff_offenlegung.html" (dict "page" .
  "extraKeys" $ffGoKeys)`.
* Produktnamen werden gekürzt und dedupliziert, Partner alphabetisch
  zusammengefasst – aus 11 CHECK24-Links wird ein lesbarer Satz, keine Liste.

Eingehängt ist die Kennzeichnung in vier Layouts – **alle vier pflegen**
(Drift-Vorfall 26.09.2026: `layouts/single.html` gewinnt über
`layouts/_default/single.html`):

| Layout | Ort |
|---|---|
| `layouts/single.html` | im `<header>`, nach `ff_pruefzeile.html` |
| `layouts/_default/single.html` | ebenso |
| `layouts/pillar/single.html` | vor `</header>` |
| `layouts/pillar/list.html` | vor `</header>`, mit `extraKeys` |

---

## 4. Die Wache: `scripts/offenlegung_gate.py`

```bash
hugo --minify --destination public --cleanDestinationDir
python3 scripts/offenlegung_gate.py          # Bericht + Exit-Code
python3 scripts/offenlegung_gate.py --json --no-report   # Maschine
python3 scripts/offenlegung_gate.py --seite public/posts/<slug>/index.html
python3 scripts/offenlegung_gate.py --selftest           # 13 Sabotage-Proben
npm run offenlegung                           # Build + Prüfung in einem Schritt
npm run test:offenlegung                      # Selbsttest + 36 Unit-Tests
```

Sie prüft das **gebaute HTML** – nicht die Absicht im Template:

| Vertrag | Was er verlangt | Warum |
|---|---|---|
| **O1** | Jede Seite mit `/go/`-Link trägt eine Kennzeichnung | Kein stiller Ausfall bei neuen Layouts |
| **O2** | Die Kennzeichnung steht **vor** dem ersten Partnerlink | Information nach dem Klick ist keine |
| **O3** | Anzahl und Partner stimmen **artikelgenau** und stehen im **sichtbaren Text** | Ein Datenattribut liest kein Leser |
| **O4** | Pflichtangaben: Werbung, Provision, kein Aufpreis, Weg zur Offenlegung | Kennzeichnung ohne Folgen ist Deko |
| **O5** | Nicht versteckt: kein `hidden`, `display:none`, `font-size:0`, `aria-hidden` | Der klassische Weg, Transparenz zu „erfüllen" |
| **O6** | Kopf und Abbinder widersprechen sich nie („werbefrei" + Partnerlink) | Zwei Wahrheiten sind keine |
| **O7** | `/transparenz/` existiert und nennt **jeden** beworbenen Partner | Der Weg muss irgendwo ankommen |

**Fail-closed:** Ein Werkzeugfehler (Build fehlt, Register unlesbar) ist ein
Befund, kein stilles Grün. **Keine Selbstheilung:** Die Wache hat bewusst kein
`--fix`. Die Kennzeichnung erzeugt das Template – ein Befund heißt also
*Template, CSS oder Register sind kaputt*, und das repariert ein Mensch
(Kodex C15: „Beweisen ist nicht Heilen"). Genau so steht es als begründete
Ausnahme in `scripts/reserve_healer_coverage.py`.

**Artefakte:** `OFFENLEGUNG-REPORT.md` (Root, gitignored),
`.offenlegung_state.json` (Herzschlag/Idempotenz), `data/offenlegung_history.jsonl`
(Verlauf). Alle deploy-neutral.

---

## 5. Wo die Wache überall läuft

| Weg | Wirkung |
|---|---|
| `scripts/publish_gate.py` (Gate **6**) | Ein druckfrischer Artikel ohne saubere Kennzeichnung wird **nicht** veröffentlicht |
| `scripts/bestand_gate.py` | Täglicher Bestandslauf meldet Rückfälle im Altbestand (keine Heilung, nur Befund) |
| `scripts/governance_contract.py` (C6) | Verlangt den `--selftest` der Wache – eine Wache ohne Beweis zählt nicht |
| `scripts/tests/test_offenlegung_gate.py` | 36 Unit-Tests: Verhalten, Minifizierungs-Robustheit, Bauteil-Invarianten |
| `e2e/affiliate-guard.spec.mjs` | Browser-Wahrheit: sichtbar, ≥ 12 px, oberhalb des ersten Links, `/transparenz/` erreichbar |

Der tägliche Workflow `affiliate-integrity-daily.yml` baut ohnehin mit
`hugo --minify` und ruft `bestand_gate.py` – die Wache hängt damit ohne
Workflow-Änderung im Dauerbetrieb.

---

## 6. Befund kommt – was tun?

| Befund | Erste Handgriffe |
|---|---|
| **O1** „keine Kennzeichnung" | Layout prüfen: Steht `partial "ff_offenlegung.html"` noch im `<header>`? Neues Layout? → dort einhängen |
| **O2** „steht hinter dem ersten Link" | Ein CTA ist in den Kopf gerutscht (Hero/Prüfzeile) oder die Kennzeichnung nach unten – Reihenfolge im Layout wiederherstellen |
| **O3** „Anzahl/Partner weichen ab" | Meist ein neuer `/go/`-Key ohne Eintrag in `data/affiliate_ziele.yaml` → Key dort mit `partner`/`produkt`/`netz` ergänzen |
| **O4** „Pflichtangabe fehlt" | Jemand hat den Satz im Template gekürzt – Wortlaut in `ff_offenlegung.html` wiederherstellen |
| **O5** „unsichtbar gestellt" | CSS-Regel suchen (`.ff-offenlegung`), die `display`, `font-size` oder `opacity` kippt – P1, sofort |
| **O6** „Widerspruch Kopf/Abbinder" | Beide lesen denselben SSOT – ein Verbraucher wurde umgebaut. `trust_box.html` prüfen |
| **O7** „/transparenz/ nennt Partner nicht" | Neuer Partner im Register, Seite nicht nachgezogen → `{{< partnerliste >}}` rendert automatisch; prüfen, ob der Shortcode noch drinsteht |

---

## 7. Neuen Partner aufnehmen (der einzige Handgriff)

1. `data/affiliate_ziele.yaml` erweitern:
   ```yaml
   neuer-key:
     partner: "Name wie er dem Leser angezeigt wird"
     produkt: "Konkretes Angebot"
     netz: "awin"
   ```
2. `npm run offenlegung` – die Kennzeichnung in allen Artikeln, die den Key
   verlinken, der Abbinder und die Tabelle auf `/transparenz/` ziehen automatisch nach.
3. Nichts weiter. Kein Artikel-Markdown, keine zweite Liste, kein Copy-Paste.

> Der häufigste Fehler der Vergangenheit war die zweite Liste. Es gibt genau
> **eine** Wahrheit über Partner: `data/affiliate_ziele.yaml`.

# 🎯 Anleitung: Affiliate-Intent-Wache (kein Klick landet auf dem falschen Produkt)

**Auftrag Frank, 19.09.2026:** *„Ein Besucher mit konkreter Kaufabsicht darf
niemals auf einem anderen Produkt landen als der CTA versprochen hat."*

Der Auslöser: Sieben Live-Artikel bewarben über ihren prominentesten CTA ein
Produkt und lieferten ein anderes.

| Artikel | Anker versprach | Link lieferte |
|---|---|---|
| Kfz-Versicherung Vergleich | Kfz-Versicherung | `/go/haftpflicht/` (Privathaftpflicht) |
| Kostenloses Girokonto | Girokonto | `/go/kredit/` (Ratenkredit) |
| Kreditkarte vergleichen | Kreditkarte | `/go/reisekrankenversicherung/` |
| Mietwagen ohne Kautionsfallen (1. + letzter CTA) | Mietwagen | `/go/kfz-versicherung/` |
| Wohngebäudeversicherung Vergleich | Wohngebäude | `/go/hausrat/` |
| Flugtickets günstig buchen | Flugtickets | `/go/mietwagen/` (Pillar-Fallback) |
| Tagesgeld Zinsen | Tagesgeld-Vergleich | C24 Bank, ohne sie zu nennen |

Warum das monatelang durchging: Die Anker kamen aus einem generischen Pool
(„Jetzt Angebote vergleichen", „Tarifrechner starten"), gezogen über
`date.today().day`. **Ein Anker, der nichts verspricht, kann sich nicht
widersprechen** – er fiel durch jede Prüfung, während der Besucher auf einem
fremden Produkt landete. Deshalb prüft die Wache drei Dinge getrennt:
Anker ↔ Route, CTA ↔ Artikelthema, Name ↔ wirkliches Angebot – und bewacht
mit IW6 auch die **Quelle** (Generator-Vorlagen).

Zuständig: `scripts/affiliate_intent_guard.py` (Wache) und
`scripts/affiliate_intent_contract.py` (Angebots-Wahrheit).

---

## 1. Die eine Wahrheit: der Intent-Kontrakt

`scripts/affiliate_intent_contract.py` hält **20 Ziele**, **17 Nie-Paare**
(Artikelthema → Route, die es nie geben darf) und **24 Themen-Muster**
(Titel/Text → Route). Pro Ziel steht dort, was wirklich verkauft wird:

| Feld | Bedeutung |
|---|---|
| `partner`, `produkt`, `landing` | wer das Angebot liefert und was es ist |
| `anzeige` | Tooltip im Render-Hook (sichtbar für jeden Leser) |
| `gateway`, `weiter_zu` | Name und grammatisch fertige Phrase „Weiter {phrase}" auf der `/go/`-Seite |
| `anker` | ehrliche Ankertexte je Slot (top/mid/end/intext) |
| `abweichung` | Pflicht-/Verbots-Wörter, wenn der Route-Name lügt (siehe IW3) |
| `saetze` | ganze CTA-Sätze, wenn schon der Satz ein Angebot verspricht, das es nicht gibt |

Diese eine Datei versorgt: `data/affiliate_ziele.yaml` (Hugo-Tooltips),
`layouts/_default/_markup/render-link.html`,
`layouts/_partials/affiliate_anchor_attrs.html`, `layouts/pillar/list.html`,
`static/go/<route>/index.html` (20 Übergabeseiten), `affiliate_shield.py`,
`affiliate_marketer.py`, `affiliate_health.py` und die Wache selbst.
IW0 vergleicht alle diese Orte **Zeichen für Zeichen** – eine zweite Wahrheit
fällt sofort auf.

**Build-Regel (Vorfall 19.09.2026):** Kein Layout darf `hugo.Data` oder
`site.Data` anfassen. `data/` enthält auch Bot-Protokolle als `*.jsonl`
(u. a. `data/audit/`); ein einziger Zugriff lässt Hugo den **ganzen** Baum
parsen und der Build stirbt mit `failed to load data: … unmarshal of format
"" is not supported` – Seite baut nicht, kein Deploy, Qualitäts-Gate +
Playwright + Themenwelten rot. Die Zielnamen kommen deshalb über
`layouts/_partials/affiliate_ziele_data.html` (`os.ReadFile` +
`transform.Unmarshal`, `partialCached`), genau wie das Hausmuster
`themenwelten_data.html`. Dort muss das Format **explizit** gepinnt sein
(`transform.Unmarshal (dict "format" "yaml")`, Hugo ≥ 0.149): Ohne Pin rät
Hugo bei YAML mit `#`-Kommentarkopf TOML und der Build stirbt mit
`toml: expected '=' after key` – am 19.09.2026 beim Rendern von
`content/pillar/frugalismus/` genau so passiert. IW0 prüft beides:
`os.ReadFile` **und** den Format-Pin. IW0 prüft jedes Layout auf verbotene Zugriffe und
unterscheidet dabei Code von Kommentar; der Selbsttest beweist die Erkennung
mit einer Sabotage-Probe.

Vier Ziele weichen bewusst vom naheliegenden Namen ab (`abweichung`):
`allgemein`, `fluege`, `girokonto`, `tagesgeld`. Grund: Tagesgeld und
Girokonto sind Angebote der **C24 Bank** (kein Marktvergleich), und „Flüge"
ist der **CHECK24-Pauschalreise**-Vergleich – ein Flug-Deep-Link existiert im
Partnerprogramm nicht (`deep=fluege` endet E2E auf einer 404, geprüft
19.09.2026). Diese Ziele müssen das echte Angebot im Anker nennen.

## 2. Prüfen und heilen

```bash
# 0) Pflicht zuerst: Sehtest der Wache (Exit 2 = Detektor blind, fail-closed)
python3 scripts/affiliate_intent_guard.py --selftest

# 1) Bestand prüfen OHNE zu schreiben (Beweislauf)
python3 scripts/affiliate_intent_guard.py --dry-run

# 2) Bestand prüfen UND deterministisch heilen (täglich in CI)
python3 scripts/affiliate_intent_guard.py --fix

# 3) nur einen Artikel / nur neue Artikel
python3 scripts/affiliate_intent_guard.py --file content/posts/<slug>/index.md
python3 scripts/affiliate_intent_guard.py --fix --new-only

# 4) Kontrakt → Datendatei + Gateway-Seiten neu backen
python3 scripts/affiliate_intent_guard.py --bake
python3 scripts/affiliate_shield.py --fix
```

Exit-Codes: `0` grün · `1` redaktioneller Befund offen (blockiert) ·
`2` Werkzeugfehler (Beweis nicht möglich → es wird **nichts** veröffentlicht).

Beweisstücke: `AFFILIATE-INTENT-REPORT.md` (Tagesreport) ·
`.affiliate_intent_state.json` (Zustand/Herzschlag) ·
`data/affiliate_intent_history.jsonl` (Historie).

Die Heilung ist **deterministisch** (kein KI-Rewriting): Anker, Route und –
nur bei Abweichungs-Zielen – der ganze CTA-Satz kommen aus dem Kontrakt.
Sie ist byte-exakt (nur die kranke Zeile) und idempotent (zweiter Lauf
ändert nichts).

## 3. IW-Codes

| Code | Was geprüft wird |
|---|---|
| IW0 | Kontrakt, Register, Datendatei, Health-Kontrakt, Templates, Gateway-Seiten: eine Wahrheit – plus build-sicherer Datenpfad (kein `hugo.Data`/`site.Data` in Layouts) |
| IW1 | Nennt der Anker ein Produkt, liefert die Route genau dieses Produkt |
| IW2 | Top-/Mid-/End-CTA dient dem Artikelthema (oder ist durch den CTA-Kontext gedeckt) |
| IW2a | Route ist im Register `scripts/check24_links.yaml` eingetragen |
| IW3 | Routen mit Abweichung (C24 Bank, Pauschalreise statt Flug) benennen das echte Ziel |
| IW4 | Eingefrorene Nie-Paare (z. B. Kfz-Artikel → Haftpflicht) sind unmöglich |
| IW5 | Jede `/go/`-Seite nennt das echte Ziel, ist `noindex` und leitet exakt auf die Register-URL |
| IW6 | Die Engine-Vorlagen erzeugen für jede Route konforme CTAs (Quelle mitbewacht) |
| IW7 | Interne Lesetipps werden nicht zu Affiliate-Links entführt |
| IW8 | Kein Anker bleibt generisch – jeder nennt das Angebot |
| IW9 | Template- und Shortcode-CTAs (`tarifvergleich`, `einspartabelle`) gelten derselbe Kontrakt |

Blockierend sind IW1/IW2/IW2a/IW3/IW4/IW7/IW8/IW9 im Content; IW0/IW5/IW6
sind Struktur-Funde (Kontrakt/Register/Templates) und stoppen den Lauf
ebenfalls – sie bedeuten: die Wache selbst hat keine saubere Grundlage.

## 4. Was die Wache bewusst NICHT antastet

Eine Ehrlichkeits-Wache, die ehrliche Werbung killt, wird abgeschaltet –
deshalb sind diese Fälle ausdrücklich erlaubt:

- **Ehrliches Cross-Selling:** Im Mietwagen-Ratgeber darf ein
  Kreditkarten- oder Reisekranken-Angebot stehen, **wenn der Anker es selbst
  nennt**. Nur der generische Anker auf fremder Route ist ein harter Fund.
- **Prosa mit Partnernennung:** „Bei der [C24 Bank](/go/girokonto/) sind
  Kategorien integriert" ist Satzgrammatik, kein CTA – kein IW8-Fund.
- **Pillar- und Hub-Seiten:** dort gelten IW2/IW4 nicht (eine Säule führt
  bewusst in mehrere Themen).
- **Ehrlich benanntes Zweitangebot** im falschen Thema wird als *Hinweis*
  im Report gezeigt (Transparenz), blockiert aber weder CI noch Deploy.

## 5. Neue Route / neues Ziel anlegen

Reihenfolge ist Pflicht – jeder Schritt hat einen Prüfer:

1. **Partner-URL** in `scripts/check24_links.yaml` eintragen (Deep-Pfad aus
   dem Partnerprogramm, **nie geraten**). Siehe `ANLEITUNG-CHECK24-LINKS.md`.
2. **Kontrakt**: in `scripts/affiliate_intent_contract.py` ein `Ziel(...)`
   anlegen (`produkt`, `anzeige`, `gateway`, `weiter_zu`, `anker`, `netz`);
   bei Namens-Abweichung zusätzlich `Abweichung(pflicht=..., verbot=...,
   grund=...)`. Passende Themen-Muster in `THEMEN_REIHE` ergänzen und
   verbotene Kombinationen in `NIE_PAARE` einfrieren.
3. **Backen**: `python3 scripts/affiliate_intent_guard.py --bake` →
   `data/affiliate_ziele.yaml` + `static/go/<route>/index.html`.
4. **Health-Kontrakt** in `scripts/affiliate_health.py` ergänzen (sonst
   meldet IW0 eine Route ohne E2E-Prüfung).
5. **Templates**: Fallback-Dict in `render-link.html` und
   `affiliate_anchor_attrs.html` mit dem neuen Anzeigenamen ergänzen (die
   Zielnamen selbst kommen zur Build-Zeit aus
   `affiliate_ziele_data.html` – niemals `hugo.Data`/`site.Data`, siehe
   Build-Regel oben). Beide Dateien sind **integritätsgesperrt** → im selben
   Commit neu signieren: `python3 scripts/integrity_guard.py --set-current`.
6. **Beweis**: `--selftest` (Kontrakt + Wache), `--dry-run` (Bestand),
   `python3 -m unittest discover -s scripts/tests` (Regressionstests),
   `python3 scripts/affiliate_health.py --no-net`.

## 6. CI-Verdrahtung

**Publish-Gate (`scripts/publish_gate.py`, Gate #5):** Vor dem Deploy läuft
die Wache MIT Heilung über die Live-Kandidaten – ein druckfrischer Artikel
wird nicht wegen eines automatisch korrigierbaren Ankers verworfen. Was nach
der Heilung bleibt, ist redaktionell und **stoppt die Veröffentlichung**.
Bei Werkzeugfehler gilt fail-closed: nichts veröffentlichen, nichts
vernichten. Im `--dry-run` schreibt das Gate nichts (Beweislauf).

**Tägliche Wache** (Actions → „Affiliate-Integritäts-Wache (täglich)",
06:00 MESZ): `intent_selftest` (Sehtest) → `intent` (`--fix`, heilt und
committet) → Deploy nur, wenn wirklich geheilt UND der Nachweis gepusht
wurde. Bewertung des Laufs: Selbsttest-Fehler oder Exit 2 = **rot**
(Werkzeugfehler), Exit 1 = fachlicher Befund, Exit 0 = grün.

## 7. Eskalation: Name passt nicht zum Angebot

Wenn eine Route nicht das liefert, was ihr Name verspricht, gibt es genau
zwei saubere Wege – **niemals** einen stillen Produktwechsel:

1. **Ehrlich umbenennen**: `abweichung` + `saetze` + `weiter_zu` im Kontrakt
   so setzen, dass Anker, CTA-Satz und `/go/`-Seite das echte Angebot nennen
   (Beispiel Tagesgeld: „zum Tagesgeld der C24 Bank (CHECK24-Tochter)").
2. **Passendes Partnerprogramm besorgen**: neue Route mit echtem
   Vergleichs-Deep-Link (Beispiel Wohngebäude: Tarifcheck-Deep
   `wohngebaeudeversicherung`, E2E geprüft 19.09.2026 – die CHECK24-Deeps
   derselben Kategorie liefern 404).

Beides endet mit `--bake`, `--fix` und dem Testlauf aus Abschnitt 5.

## 8. Regressionstests

`scripts/tests/test_affiliate_intent_guard.py` – läuft in CI über
`python3 -m unittest discover -s scripts/tests` (kein pytest nötig) und
beweist: die sieben Live-Vorfälle werden erkannt, auf die richtige Route
geheilt und sind danach idempotent; ehrliches Cross-Selling, Prosa und
ehrliche Zweit-CTAs bleiben unverändert; Kontrakt ↔ Register ↔ Health ↔
Datendatei ↔ Templates ↔ Gateway-Seiten ↔ Generator decken sich; der ganze
Bestand ist intent-sauber; bei kaputtem Register meldet die Wache Exit 2.

Hintergrund: `AFFILIATE-INTENT-REPORT.md` · Register-Pflege:
`docs/ANLEITUNG-CHECK24-LINKS.md` · Link-Struktur:
`AFFILIATE-INTEGRITY-GATE-REPORT.md`.

---

## FAQ

**Darf ich einen Anker per Hand „schöner" formulieren?**
Ja, wenn er das Angebot der Route nennt. Generische Anker („Jetzt Angebote
vergleichen", „Tarifrechner starten", „Kostenlos vergleichen") heilt die
Wache zurück – sie waren der Grund des Vorfalls.

**Warum steht im Tagesgeld-Artikel „C24 Bank" statt „Vergleich"?**
Weil es dort keinen Marktvergleich gibt: Die Route führt zu einem Angebot
der C24 Bank. Ein Vergleichs-Versprechen wäre Werbung mit etwas, das der
Klick nicht hält.

**Kann die Wache einen Artikel kaputtmachen?**
Sie schreibt nur die kranke Zeile (byte-exakt) und ist idempotent. Bei
Werkzeugfehler (Exit 2) schreibt sie nichts und stoppt die Veröffentlichung
– fail-closed statt „grün schweigen".

**Was bedeutet Exit 1 ohne Heilung?**
Ein Befund, den kein Kontrakt-Eintrag abdeckt (meist Prosa mit einem
Vergleichs-Versprechen zu einem Einzelanbieter-Angebot). Redaktionell
entscheiden: Satz ehrlich formulieren oder Route mit passendem
Partnerprogramm ergänzen (Abschnitt 7).

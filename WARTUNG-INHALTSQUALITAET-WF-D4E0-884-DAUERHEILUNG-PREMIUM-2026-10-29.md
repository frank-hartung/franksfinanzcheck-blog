# 🏛️ WF-D4E0 (#884) – Forensische Kausalanalyse & Dauerheilung auf Agentur-Niveau

**Vorgang:** `WF-D4E0` · Issue **#884** (`🔧 Wartung · Inhaltsqualität · Vorgang WF-D4E0`)
**Workflow:** `.github/workflows/content-reserve.yml` (`Content-Reserve (täglicher Vorrat)`)
**Referenzlauf:** `40667750341` · Job `reserve` (`28.10.2026, 10:53:17`, `schedule`, Commit `3f67b54e`)
**Datum der Dauerheilung:** `2026-10-29`
**Alarmbild:** 26 von 28 Schritten grün – der Lauf endet am harten End-Gate
`Stock shortage must not look successful` mit **3/6** gate-fertigen Kandidaten (Pool 4).

---

## 1. Forensische Chronologie

`data/reserve-history.jsonl` und `data/reserve-readiness.json` zeigen kein
„Naturereignis“, sondern eine **sich selbst erhaltende Schleife**:

| Lauf (UTC) | Run | Klasse | Ready/Pool | Blocker im Zertifikat |
|---|---|---|---|---|
| `26.10. 09:43` | `40297687637` | `engpass` | 4/5 | `2026-10-26-flugvergleich-…` |
| `26.10. 15:27` | `40348621653` | `kette` | 2/5 | u. a. `2026-10-26-flugvergleich-…` |
| `27.10. 09:42` | `40479040838` | `engpass` | 5/6 | `2026-10-27-flugvergleich-…` |
| `28.10. 10:27` | `40667750341` | `engpass` | 5/6 → **3/6** | `2026-10-28-flugvergleich-…` |

Es ist **derselbe Artikel**, der jede Nacht neu datiert wird (die
Veredelung hebt Pool-Kandidaten auf „heute“) – und jede Nacht am selben,
scheinbar unerklärlichen Fund scheitert:

```
⛔ 2026-10-28-flugvergleich-im-winter-so-findest-du-echte-billigfluege
   Score 0.958 – Textverständnis-Gate nicht bestanden:
   R13-DATUM-PUNKT: Politur-Ruine „23 Dezember“ – Überrest eines
   automatisierten Politur-Laufs, manuell reparieren
```

Der Widerspruch, der die Fehlersuche zwei Tage lang in die Irre führte: In
der **Datei auf der Platte** steht die Ruine **nicht**. Ein Scan der
Originalbytes über die Muster-SSOT `sprachkern.POLITUR_RUINEN` findet
`0` Treffer:

```bash
python3 - <<'EOF'
import sys; sys.path.insert(0,'scripts'); import sprachkern
t = open('content/posts/2026-10-28-flugvergleich-im-winter-so-findest-du-echte-billigfluege/index.md', encoding='utf-8').read()
print(sprachkern.politur_ruine_funde(t))      # → []
EOF
```

Der Fund galt deshalb als „Geisterbefund“; die naheliegenden Antworten
(Modellfehler der Wache, API-Ausfall, Gate-Lockerung) waren alle falsch.

---

## 2. Root-Cause 1: Der R5-Absatz-Splitter **baut** den Blocker, den er beheben soll

`scripts/r5_absatz_splitter.py` schützt den Ordinalpunkt, indem es ihn
**löscht** – und teilt anschließend genau den gelöschten Text:

```python
# split_para(), Stand bis 28.10.2026
p = re.sub(r'(\b\d{1,2})\.\s+([A-ZÄÖÜ][a-zäöüß]{2,}\b)', r'\1 \2', p)   # „23. Dezember“ → „23 Dezember“
...
a, b = p[:cut], p[cut:]        # die Teilung wird aus DEM Text gebaut
return a.rstrip() + "\n\n" + b.lstrip()
```

Reproduktion am echten Kandidaten:

```bash
python3 - <<'EOF'
import sys; sys.path.insert(0,'scripts')
import r5_absatz_splitter as r5, publikations_vertrag as pv
p = 'content/posts/2026-10-28-flugvergleich-im-winter-so-findest-du-echte-billigfluege/index.md'
t = open(p, encoding='utf-8').read()
neu, n, _ = r5.heal_text(t)
print(n, pv.verstoesse_kurz(pv.pruefe('x', t, neu)))
EOF
# → 11  V2 Textverständnis: die Änderung führt den harten Fund R13-DATUM-PUNKT ein …
```

Damit schließt sich ein Kreis, in dem **jede Stufe die Arbeit der anderen
vernichtet**:

1. **Stufe 2** (`reserve_finisher.run_chain`) ruft `r5_absatz_splitter.py
   --apply` auf → der Splitter schreibt die R13-Ruine.
2. Der **Schritt-Vertrag** (`_step_guard_enforce` → `_kandidat_regressionen`
   → `publikations_vertrag.pruefe`, Regel **V2**) erkennt „neuer harter
   Fund“, rollt die Datei **bytegenau zurück**. Ergebnis: Der Artikel bleibt
   ungeteilt – der Split ist weg, die R5-Hartfunde bleiben.
3. **Stufe 3** (Zertifizierung) heilt vor dem Gate **nach**: `accept_candidate
   → preheal_candidate → r5.heal_text` – **ohne** Schritt-Vertrag. Jetzt
   entsteht die Ruine im Messbild.
4. Das Publish-Gate lehnt **korrekt** ab (`R13-DATUM-PUNKT` ist seit #482
   hart). `certify_one` schreibt im `finally` die Originalbytes zurück.
5. Die Nacht darauf: derselbe Ablauf, derselbe Befund, derselbe Blocker.

Der Vorrat konnte so nie über 5/6 (am 28.10. dann 3/6) hinauskommen: Der
Kandidat war fertig (Qualität **0,958**, Flesch 66,2, alle übrigen Tore grün)
und wurde von einem Werkzeug blockiert, dessen einzige Aufgabe es ist, ihn
**fertig** zu machen.

### 2.1 Dauerheilung (nicht Symptom, sondern Klasse)

1. **Maske statt Löschung** (`r5_absatz_splitter.datum_maskieren()`):
   Der Ordinalpunkt wird für die Satzzählung durch `\x01` ersetzt (kein
   Satzzeichen, kein Whitespace) und nach der Teilung **bytegenau**
   zurückgeschrieben – inklusive schmalem geschütztem Leerzeichen
   (`U+202F`), das in den Artikeln real vorkommt. Beide Pfade
   (`split_para()` und `paras_with_many_sents()`) nutzen dieselbe Funktion;
   es gibt keine zweite Datums-Erkennung mehr.
2. **Letztlinie gegen die ganze Familie**: `split_body_text()` vergleicht vor
   dem Zurückgeben die Ruinen-Mengen (Alt gegen Neu, SSOT
   `sprachkern.POLITUR_RUINEN`). Führt die Teilung **irgendeine** Ruine ein –
   auch eine, die es heute noch nicht gibt –, werden die Originalbytes
   zurückgegeben, `splits = 0` gemeldet und der Grund als Warnung geführt
   (**fail-closed**). Die konkrete Datums-Klasse ist damit unerzeugbar, die
   Zusage gilt aber für jede künftige Muster-Änderung.

---

## 3. Root-Cause 2: Die Vorheilung schrieb ohne Tor – der Schaden blieb unsichtbar

`publication_release.preheal_candidate()` ist der **einzige Schreiber** der
Zertifizierung, der nicht durch `publikations_vertrag.pruefe` ging. Genau
deshalb hat niemand den Fund aus Abschnitt 2 je gesehen: Das Gate lehnte ab,
die Bytes wurden zurückgestellt, das Zertifikat nannte einen Fund, den die
Datei nie hatte – und `certify_one` prüfte die Abweichung nur im **grünen**
Fall (`if ready and index.read_bytes() != proof_bytes`).

**Heilung (zwei Seiten):**

* `preheal_candidate()` prüft jede geplante Änderung jetzt gegen den
  Publikations-Vertrag. Bei einem Verstoß (oder wenn der Vertrag nicht
  messbar ist – Regel **V3**, fail-closed) werden die **Originalbytes**
  zurückgeschrieben und der Grund gemeldet:
  `🛡 …: R5-Vorheilung verworfen – V2 Textverständnis: …`
* `reserve_readiness.certify_one()` sagt im **roten** Fall zusätzlich, dass
  die Messfassung durch die Vorheilung verändert und danach zurückgestellt
  wurde. Die Diagnose unterscheidet ab jetzt „Datei ist kaputt“ von
  „Werkzeug hat die Messfassung verändert“ – der Unterschied, der diese
  Fehlersuche zwei Tage gekostet hat.

---

## 4. Root-Cause 3: RS5 galt an der Geburt als „unheilbar“ – vier Themen je Nacht verbrannt

`engine_generate._reserve_vorstufe_ok()` lässt Rohtexte in die Reserve-Werkbank,
wenn **nur** Klassen fehlen, für die die Kette einen belegten Heiler hat.
Erlaubt waren „Länge“ und „Keyword“. **RS5** (Zahlen ohne Satzbeleg) war
ausgenommen – obwohl `redaktions_standard.py --fix` (deterministische
Kennzeichnung als Modell-/Beispielwert + KI-Heilung unter
Publikations-Vertrag) in der Kette läuft und einen **grünen
Wirkungsnachweis** besitzt (`reserve_healer_coverage.WIRKUNGS_PROBEN`,
`RS5 2 → 0, Fixpunkt bestätigt`, Vertrag C25).

Realfolge am 28.10.2026 – vier frische Themen wurden verworfen, weil die
**Kombination** aus heilbaren Klassen als unbehandelbar galt:

| Thema | Befund | Klasse |
|---|---|---|
| „Weihnachtsgeld klug einsetzen …“ | `RS5: 6 Zahlenbehauptungen` | heilbar |
| „Strom-Nachzahlung vermeiden …“ | `RS5: 6 Zahlenbehauptungen` | heilbar |
| „Router-Sicherheit … in 15 Minuten“ | `RS5: 2 Zahlenbehauptungen` | heilbar |
| „… mit einem Budget-App …“ | `nur 858 Wörter` + RS5 | heilbar |

**Heilung:** RS5 ist die **dritte** belegte Heilerklasse
(`heilbar.append("Zahlenbeleg")`). Die Annahme wird nicht behauptet, sondern
bei **jedem** Gebrauch gegen die beiden Quellen geprüft:
`reserve_finisher.HEALER_CHAIN` **und** `reserve_healer_coverage.WIRKUNGS_PROBEN`.
Fällt eine der beiden Zusagen weg (z. B. der Wirkungsnachweis), bleibt RS5
an der Geburt hart (`_rs5_heilung_belegt()` → `False`). Die harten Klassen
bleiben unangetastet: Struktur/FAQ, Floskeln und RS1 („Das Wichtigste in
Kürze“, nur KI-heilbar) verwerfen weiterhin sofort.

---

## 5. Root-Cause 4: Ein stiller Fahnenverlust (LECK)

Der am 28.10. um `15:04Z` redaktionell zurückgezogene Heizöl-Artikel
(`2026-10-24-heizoel-preise-…`, Begründung im Frontmatter: saisonale
Preisprognosen ohne belastbare Quellenkette) lag als Entwurf **ohne**
`reserve: true` im Repo, während `data/reserve-custody.json` ihn als
Pool-Kandidaten führte. Der End-Gate meldete das korrekt als
`LECK … Heilung: python3 scripts/reserve_custody.py --heal`.

Der Entwurf entstand um `15:04Z` – also **nach** dem Reserve-Lauf des Tages
(`10:53Z`); die Stufe 0b des nächsten Laufs (`reserve_custody.py --heal`)
hätte die Fahne automatisch zurückgeholt. Diese Heilung wurde hier
vorgezogen, damit der Zustand nicht bis zur nächsten Nacht als „LECK“ in
der Diagnose steht.

**Heilung:** `python3 scripts/reserve_custody.py --heal` – belegte
Wiederherstellung der Fahne (Ledger-Eintrag vorhanden, Artikel bleibt
`draft: true`, kein Inhalt angefasst). Pool: **4 → 5**. Ein stiller Schwund
bleibt damit auch künftig ein Befund statt einer stillen Lücke.

---

## 6. Durchgeführte Dauerheilung (Dateien)

| Datei | Änderung |
|---|---|
| `scripts/r5_absatz_splitter.py` | `datum_maskieren()` / `datum_wiederherstellen()` (verlustfreie Maske, `U+202F`-fest); beide Pfade umgestellt; **Fail-closed-Gegenprobe** gegen `sprachkern.POLITUR_RUINEN` in `split_body_text()`; 2 neue Selbsttest-Blöcke (Ordinaldatum bytegenau, Ruinen-Gegenprobe, Masken-Verlustfreiheit). |
| `scripts/publication_release.py` | `preheal_candidate()` prüft jede geplante Änderung gegen `publikations_vertrag.pruefe`; bei Verstoß oder Messausfall (V3) bytegenaue Rücknahme + Meldung. |
| `scripts/reserve_readiness.py` | `certify_one()` dokumentiert auch im roten Fall, wenn die Gate-Vorheilung die Messfassung verändert und zurückgestellt hat. |
| `scripts/engine_generate.py` | `_reserve_vorstufe_ok()` nimmt RS5 als belegte Klasse (`Zahlenbeleg`) an; `_rs5_heilung_belegt()` prüft Kette **und** Wirkungsnachweis (fail-closed). |
| `scripts/tests/test_reserve_pipeline.py` | `WfD4e0Issue884Tests` (4 Fälle) + `test_vorstufe_nimmt_rs5_zahlenbeleg_an` (inkl. Nachweis-Wegfall und Gegenprobe). |
| `.github/workflows/content-reserve.yml` | Kopf-Dokumentation der Reparatur (4 Befunde, Kausalkette, Verweis hierher). |
| `content/posts/2026-10-28-flugvergleich-…/index.md` | R5-Teilung **sicher** angewendet (11 Absätze; Datum bytegenau erhalten) – der Zustand, den Stufe 2 künftig selbst herstellt. |
| `content/posts/2026-10-24-heizoel-…/index.md` | `reserve: true` belegt wiederhergestellt (Custody-Heilung). |
| `data/reserve-custody.json` | Ledger-Fortschreibung der Heilung (append-only-Charakter, keine Löschung). |

---

## 7. Verifikation

| Prüfung | Befehl | Ergebnis |
|---|---|---|
| R5-Selbsttest (inkl. neuer Datums-/Ruinen-Proben) | `python3 scripts/r5_absatz_splitter.py --selftest` | ✅ grün |
| Neue Regressionstests | `python3 -m unittest scripts.tests.test_reserve_pipeline.WfD4e0Issue884Tests` | ✅ 4 Tests |
| Vorstufen-Vertrag (RS5) | `… .WfD4e0Issue821Tests` | ✅ inkl. Nachweis-Wegfall (fail-closed) |
| Reserve-Pipeline + Auslieferung | `python3 -m unittest scripts.tests.test_reserve_pipeline scripts.tests.test_publication_reliability` | ✅ **193 Tests OK** |
| Publikations-Vertrag | `python3 scripts/publikations_vertrag.py --selftest` | ✅ V1/V2/V3 + Vorfallprobe |
| Heiler-Deckung + Vorratsschutz | `reserve_healer_coverage.py --selftest` / `--vorratsschutz` | ✅ grün |
| Politur-Ruinen-Wirkungsprobe | `python3 scripts/politur_ruine_heiler.py --wirkungsprobe` | ✅ 3 → 0, Fixpunkt |
| RS-Wirkungsprobe | `python3 scripts/redaktions_standard.py --wirkungsprobe` | ✅ RS5 2 → 0, Fixpunkt |
| Bestands-Wächter | `python3 scripts/reserve_custody.py --selftest` | ✅ grün (Fahne zurück, Inhalt unberührt) |
| Der geheilte Kandidat | Ruinen-Scan · `reserve_quality_findings` · `publish_gate.textverstaendnis_failures` · `r5.hard_r5_findings` | ✅ jeweils **0 Funde** (2.030 Wörter, Datum bytegenau) |
| End-Gate-Diagnose | `python3 scripts/reserve_gate.py` | ✅ LECK verschwunden, BLOCKER-Klasse „Werkzeug“ weg; Es fehlen nur noch die zwei Nachschub-Kandidaten |
| Engine-Kapazität | `python3 scripts/engine_capacity.py` | ✅ 65 freie AUTO-Themen (Vorlauf 32,5 Tage) |
| Artefakte | `artefakt_waechter.py` · `reserve_artifacts.py --check` | ✅ 515 Artefakte · Snapshot vollständig |
| Wachen | `url_substring_guard` · `clear_text_logging_guard` · `fm_boundary_guard --check` · `check_covers` | ✅ 1.118 / 580 / 136 Dateien · 106 Covers, 0 Probleme |
| Governance | `python3 scripts/governance_contract.py` | ✅ **42/42 Regeln** |
| Integritäts-Siegel | `python3 scripts/integrity_guard.py --gate` | ✅ 50 Kerndateien (gemessen auf `HEAD 2e4c7ae`). Nach dem Rebase auf `main` (`76efccb`) meldet das Gate `scripts/internal_linker.py` als **fremd und unversiegelt** – Folge von #940 (`9bb3e86`), das eine gesperrte Kerndatei ohne neue Signatur änderte. Dieser Vorgang fasst den gesperrten Kern nicht an und signiert fremde Änderungen nicht mit (C15); der Fall gehört zu #826/#940. |
| Workflow-Audit | `python3 scripts/automation_premium_audit.py --strict` | ✅ rc 0 |
| Selbsttests aller Wachen (der CI-Schritt, der im roten Lauf grün war) | `python3 scripts/selftest_runner.py` | ✅ **245 Wachen · 490 Uhr-Proben** (`+97` und `+1461` Tage vorgestellte Uhr) · 198,8 s · alles grün |
| Vollsuite | `python3 -m unittest discover -s scripts/tests` | **4.249 Tests**, 6 Fehlschläge – **alle sechs vorbestehend** (Baseline-Gegenprobe in einem `git worktree` auf `HEAD 2e4c7ae`: identische 6 Fehlschläge, 0 durch diese Heilung verursacht) |

**Baseline-Befund (nicht Teil von #884, aber ehrlich benannt):** Die sechs
roten Tests sind Drift außerhalb des Reserve-Vorrats –
`fachpruefung_register.yaml` veraltet, sieben Artikel ohne artikelgenaue
Abbildungs-Unterschrift, ein `LCP`-Manifest-Eintrag, ein Entwurf, der aus
einem Versicherungs-Pillar verlinkt ist, und eine News-Kopfzeile ohne die
geforderte destatis-Zahl. Sie blockieren den Reserve-Lauf nicht (dessen
Stufe 0 misst Wachen-Selbsttests, nicht die Unit-Suite), gehören aber in
einen eigenen Vorgang – sie sind mit dieser Heilung **nicht** entstanden
und werden hier nicht stillschweigend mitrepariert.

**Ehrliche Grenze dieser Sitzung:** Im Arbeits-Container fehlen `hugo` und
`hunspell` (Download nur aus dem gesperrten Release-Host möglich). Eine
**neue Zertifizierung** (`reserve_readiness.py` → Hugo-Render-Beweis) ist
deshalb lokal nicht ausführbar; sie läuft im nächsten Nachtlauf der
Produktionslinie auf demselben Code. Belegt ist hier alles, was ohne diese
beiden Werkzeuge beweisbar ist – inklusive der Ursache selbst.

---

## 8. Erwarteter Lauf nach dieser Heilung

1. **Stufe 2** teilt die verbleibenden langen Absätze, ohne eine Ruine zu
   erzeugen → der Schritt-Vertrag rollt nicht mehr zurück (vorher: jede
   Nacht).
2. **Stufe 3** zertifiziert `2026-10-28-flugvergleich-…` mit denselben Bytes,
   die auf der Platte liegen (keine In-Flight-Heilung mehr nötig) →
   **4/6**.
3. **Stufe 1/4** dürfen die RS5-Kandidaten jetzt in die Werkbank geben; die
   Kette heilt Zahlenbeleg und Länge, die Zertifizierung entscheidet
   unverändert hart → Ziel **6/6**.
4. Sollte ein Kandidat dennoch scheitern, nennt das Zertifikat künftig immer
   den Fund **der Datei** – nicht den einer zurückgestellten Heilfassung.

## 9. Was strukturell verhindert ist

* Eine Absatz-Teilung kann **keine** Politur-Ruine mehr einführen
  (Maskierung + Fail-closed-Gegenprobe) – unabhängig davon, welche Muster
  künftig in `sprachkern.POLITUR_RUINEN` stehen.
* Ein Werkzeug der Zertifizierung kann den Kandidaten **nicht mehr
  unbemerkt** verändern (Publikations-Vertrag in der Vorheilung, Diagnose im
  roten Fall).
* Ein heilbarer Geburtsbefund mit belegtem Heiler kann den Nachschub nicht
  mehr **allein** blockieren – der Beweis wird bei jedem Gebrauch gegen
  Kette und Wirkungsnachweis geprüft.
* Ein stiller Fahnenverlust bleibt ein **Befund** (Custody-Ledger), kein
  Schwund.

# Themen haben zwei Bahnen – und der Vorrat läuft aus

> Wörtlich aus `CLAUDE.md` übernommen am 01.11.2026 (Skill-Umbau). Kein Satz wurde umformuliert, gekürzt oder erfunden; die Überschriften sind eine Ebene tiefer gehängt. Änderungen hier sind Änderungen am Regelwerk – sie brauchen denselben Nachweis wie vorher: Selbsttest der betroffenen Wache, dann Commit.

### Themen haben zwei Bahnen (seit 02.10.2026, Issue #521)

Am 02.10.2026 lief die Engine, schrieb vier Artikel und veröffentlichte
**null**. Nicht die Produktion war kaputt, sondern die Buchhaltung darüber.

- **AUTO vs. FACHFREIGABE:** YMYL-Themen (Versicherung, Rente, Kredit –
  46 von 187) können per Vertrag nie ohne menschliche Freigabe live gehen.
  Die Disposition war dafür blind, gab sie an die Automatik und verbuchte
  den unveröffentlichbaren Entwurf als Erfolg: Slot weg, Thema 180 Tage
  gesperrt, LIVE-Zähler unverändert. **Nur `engine_capacity.nur_auto()`
  beantwortet „schaffen wir das Tagesziel?“.**
- **Die Bahn ersetzt nie ein Gate.** Sie ist asymmetrisch konservativ: Ein
  bekanntes `hoch`-Thema kommt nicht in die Quote; ein als `auto`
  eingestuftes Thema, dessen Artikel sich doch als YMYL erweist, läuft
  weiterhin ins fail-closed `editorial_review_gate`.
- **Eine Klassifikation, nicht zwei:** `engine_capacity` ruft
  `editorial_review_gate.classify_text()`. Die Risikomuster nie kopieren –
  ein Test verbietet es.
- **Die Bahnen gelten für jeden Produzenten, nicht nur für die Engine
  (13.10.2026, Issue #734).** Der News-Writer der KI-Redaktion kannte sie
  nicht: Er zog den Aufhänger „versicherung“ und legte einen Hochrisiko-
  Entwurf ohne Prüfgerüst und ohne Quelle in die Prüfqueue (E03), dazu mit
  dem Titel eines Entwurfs vom 17.09. Seitdem prüft
  `ki_shared.fachfreigabe_pruefen()` vor jeder Generierung und
  `ki_shared.build_frontmatter()` an der Schreibgrenze: YMYL nur mit
  `--fachfreigabe` **und** offenem WIP-Limit, immer mit Gerüst
  (`status: ausstehend`, nie `freigegeben`). Übersprungene Aufhänger bleiben
  unverbraucht im Pool, Titel-Dubletten werden übersprungen, und
  `ki_redaktion.py --promote` nimmt Hochrisiko ohne gültige Freigabe nicht
  an. **Ein neuer Writer baut sein Frontmatter über
  `ki_shared.build_frontmatter` – nie daneben**, und kein `except Exception`
  darf `FachfreigabeErforderlich` schlucken. Pin:
  `scripts/tests/test_ki_redaktion_fachfreigabe.py`; Bericht:
  `YMYL-PRUEFQUEUE-734-DAUERHEILUNG-PREMIUM-2026-10-13.md`.
- **Ein Maß für „frei“:** `engine_capacity.lage()` zählt ausschließlich über
  `reserve_topics.disponieren`. Vorher maß der Pre-Flight mit einer laxen
  60-%-Token-Regel (`157 frei`), während der Disponent **3** fand. Nie eine
  zweite Zählregel einführen.
- **Pre-Flight bricht bei Engpass NICHT ab** (`::warning::` statt Exit 1):
  Re-Queue und Reserve-Veröffentlichung brauchen keine neuen Themen. Ein
  leerer Pool heilt nicht dadurch, dass die Engine stillsteht.
- **`merke(ok=True, "produziert: …")` ist keine Garantie, dass es den
  Artikel gibt.** `reserve_topics.abgleich()` (läuft im Pre-Flight) prüft
  gegen den Bestand und löst Phantom-Sperren – am 02.10. waren das **47 von
  63** Einträgen; freie AUTO-Themen 3 → 37. Der Abgleich hebt nur den
  *Cooldown* auf, nie den Dubletten-Schutz.
  ⚠️ **Slug-Falle:** Das Ledger speichert ohne Datumspräfix, auf der Platte
  liegt `<datum>-<slug>` (ggf. mit `-N`). Immer über `_bestands_slugs()`
  normalisieren – die naive Prüfung meldet 51/63 Einträge falsch als
  Phantom und entsperrt den halben Pool.
- Bedienung: `npm run engine:kapazitaet`, `npm run engine:abgleich`.
  Anleitung: `docs/ANLEITUNG-ENGINE-KAPAZITAET.md`.

### Der Vorrat endet nicht, er läuft aus (Themennachschub, C44, seit #821, 25.10.2026)

Vom 19.10. bis 25.10.2026 fiel der Reserve-Vorrat von 6 auf 1 gate-fertige
Kandidaten. Jede Nacht wurde derselbe Schritt rot, und jede Nacht stand im
Ticket nur der Vorrat. Die Ursache war messbar banal – und drei Wochen
unsichtbar: **In der AUTO-Bahn war kein Thema mehr frei.**

- **Zwei Ursachen, nicht eine.** (a) `reserve_topics.FUELLWOERTER` kannte
  „guenstig“, aber nicht „guenstige(n)“, nicht „tarife“, „anbieter“,
  „welche“ oder die Jahreszeiten. Ein einziges Artikel-Wort sperrte damit
  ganze Themenfamilien (Top-Blocker „guenstige“: 15 Themen); 154 von 202
  galten als „belegt“. (b) Die übrigen 21 waren sämtlich YMYL-Hochrisiko –
  frei, aber per Vertrag nie automatisch veröffentlichbar.
  → Nach der Reparatur: 0 → 19 freie AUTO-Themen, plus 36 neue, geprüfte
  AUTO-Themen in `data/topics.yaml` (Stand 25.10.: **55 frei = 27,5
  Produktionstage**).
- **Ein Füllwort ist keine Sachgrenze.** Ergänzt wird nur, was im Titel
  nichts unterscheidet (Beugungen gelisteter Wörter, Rollen-Nomen wie
  *Tarif/Anbieter/Wechsel*, Jahreszeiten, Fragewörter). Produkte und
  Sachthemen bleiben Leitbegriffe: „Stromfresser“, „Kreditkarte“,
  „Reiseversicherung“ und „Gasrechnung“ kollidieren weiterhin. Eine
  bequeme Füllwort-Liste würde die Dublettenprüfung entwerten; ein Test
  verbietet genau das.
- **Stück ist keine Zeit.** „55 Themen“ plant niemand, „27,5
  Produktionstage“ schon. `scripts/themen_nachschub_waechter.py` rechnet
  den Vorrat über `engine_capacity.lage()` (→ `reserve_topics.disponieren`,
  also mit dem Maß des Disponenten – **keine zweite Zählregel**) in Tage um
  und vergleicht ihn mit dem Mindestvorlauf (`THEMEN_HORIZON_TAGE`,
  Default 14). Exit 1 unter dem Horizont; `--warn-only` berichtet nur.
- **Der Befund nennt die Bahn.** `reserve_gate.diagnose()` unterscheidet
  jetzt „AUTO-Bahn leer“ (mit der Zahl der Fachfreigabe-Themen), „beide
  Bahnen leer“ (mit belegt/Cooldown) und „Vorlauf knapp“. Der alte Satz
  „alles thematisch belegt oder im Cooldown“ war am 25.10. nachweislich
  falsch und schickte die Reparatur zu Cooldowns, Dubletten und API-Keys.
  Die Ursache steht zusätzlich in der Gate-Meldung, die im Ticket landet.
- **Der Lauf misst vor der Kette.** `.github/workflows/content-reserve.yml`
  ruft die Wache als eigenen Schritt VOR Runde 0 auf – bewusst ohne
  `continue-on-error` (ein Befund an die Redaktion gehört in den Lauf),
  aber keine der folgenden Stufen hängt an ihrem Ergebnis: Heilung und
  Nachzertifizierung des Bestands laufen weiter.
- **Nachschub ist Redaktionsarbeit.** Neue Themen brauchen Titel, drei
  Keywords, ein `/go/`-Ziel mit passendem Angebot und eine Kollisionsprüfung
  gegen Bestand + Pool. Keine Versicherungs-, Kredit-, Renten- oder
  Baufi-Themen – die gehören in die Fachfreigabe-Bahn und kosten dort einen
  Prüfplatz, keinen Automatik-Slot.
- Bedienung: `npm run engine:nachschub` · `npm run test:themen:nachschub`.
  Vertrag: C44. Bericht:
  `WARTUNG-INHALTSQUALITAET-WF-D4E0-821-DAUERHEILUNG-PREMIUM-2026-10-25.md`.

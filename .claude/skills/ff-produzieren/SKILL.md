---
name: ff-produzieren
description: "Benutzen, sobald der Bestand an Artikeln selbst das Thema ist: Content-Engine, Entwurf, Reserve-Pool, Themenplan, Slot verpasst, Quote 1/2 LIVE, Faktencheck-Fälligkeit, Quelle/Belegkette, Dubletten und Sieben-Wort-Phrasen, YMYL-Fachfreigabe, Heiler der auf Artikel losgelassen wird, 'warum wurde nichts veröffentlicht', 'der Pool ist leer', Pin-/Keyword-Nachschub. Dieser Skill enthält die Produktionsverträge: zwei Bahnen, Messlatte, Übernahme, Heiler-Pflicht, Zahlenbeleg und Schreibvertrag. Nicht für die Sprache des Textes (ff-marke-text), nicht für Deploy-Reihenfolge (ff-ausliefern)."
metadata:
  version: 1.0.0
  besitz: repo-eigen – kein Eintrag in skills-lock.json, nie von `npx skills update` anfassen
  quelltext: CLAUDE.md-Kernregeln, wörtliche Details in references/
---

# Produzieren, ohne die Buchhaltung zu betrügen

Der teuerste Fehler dieser Kette war nie ein kaputter Generator, sondern eine
**Veröffentlichungs-Buchhaltung, die einen nicht veröffentlichbaren Entwurf als
Erfolg verbuchte** (#521) oder eine Zahl las, die sie nicht gemessen hatte
(#653, #821). Alles hier ist wörtlich aus `CLAUDE.md` übernommen.

## Wann dieser Skill zählt

- Ein Lauf produziert, aber es geht nichts live – oder umgekehrt.
- Du willst ein Thema in den Pool, einen Entwurf übernehmen oder löschen.
- Ein Kandidat fällt durch `RS1–RS6`, `RD1/RD2`, Flesch, `publish_gate`.
- Ein Heiler soll auf Artikel losgelassen werden (Zahlen, Politur, Faustregeln).
- Ein Befund nennt eine Zahl, die der Text so nicht enthält.

## Die harten Kernregeln

1. **Themen haben zwei Bahnen.** YMYL (Versicherung, Rente, Kredit) kann nie
   automatisch live gehen. Auf die Frage „schaffen wir das Tagesziel?“ antwortet
   **nur** `engine_capacity.nur_auto()`. Die Bahn ersetzt nie ein Gate.
2. **Eine Klassifikation, nicht zwei:** `engine_capacity` ruft
   `editorial_review_gate.classify_text()`. Risikomuster kopieren verbietet ein
   Test. **Ein neuer Schreiber** baut sein Frontmatter über
   `ki_shared.build_frontmatter` – nie daneben.
3. **Wer schreibt, misst vor dem Schreiben** (C41): jede Bahn ruft
   `scripts/lesbarkeit_schreiber.py` **vor** `write_post` und gibt den Status
   durch. Eine Bahn, die den Aufruf umgeht, ist selbst der Befund.
4. **Ein harter Blocker braucht einen Heiler** (C29), sonst wird der Melder zum
   Dauerläufer (C37). Wo bewusst nicht geheilt wird, bleibt der Kandidat als
   Hold erhalten und die Begründung steht im Register
   (`reserve_healer_coverage.AUSNAHMEN`).
5. **Eine Messlatte, ein Besitzer:** Ziel und Alarmschwelle rechnet
   `scripts/reserve_economy.py`. Niemals ein Ziel aus `data/reserve-readiness.json`
   lesen – dessen `target` ist Protokoll, nie Vorgabe.
6. **Löschen braucht einen Beweis:** unheilbare Klasse **und** zwei Läufe Beleg
   **und** Karenz. Eine Übernahme ohne Begründung im Intake-Ledger ist ein
   Testfehler.
7. **Eine Quelle, zwei Ausspielwege:** eine factageprüfte Quelle erscheint
   gleichzeitig in `ff_quellen_box.html` und im `citation`/`sdDatePublished` des
   Article-JSON-LD. Nie einen der beiden separat pflegen.
8. **Messen ist nicht Raten.** `check_uniqueness`, `faktenfrische.faelligkeit`
   und die Publish-Gate-Collector sind dieselben Messungen wie in Audit und
   Scorecard (C19). Ein Heiler darf keinen Satz schreiben, den er woanders
   schon hingeschrieben hat (#766).

## Katalog

| Deine Frage | Antwort im Detail |
|---|---|
| Warum geht nichts live, obwohl die Engine läuft? | `references/themen-und-bahnen.md` (#521, C44) |
| Welche Quelle darf in welchen Artikel, wann ist Fälligkeit, wie heilt man Zahlen? | `references/faktenfrische.md` (#821) |
| Pool leer, Blocker rot, Kurz-Kandidat, Ruinen-Rest? | `references/reserve.md` (#393, #594, C29, #529) |
| Slot von GitHub nicht gestartet, Issue fälschlich geschlossen? | `references/aussteuerung.md` (#601, #608, C23) |
| Titel-Zwilling, geteilte Phrasen, Gate grün und Audit rot? | `references/einzigartigkeit.md` (#714, #766) |
| Shortcode sprengt den Build, Frontmatter mit doppeltem Schlüssel? | `references/schreibvertrag.md` (F7/C32, #482) |

## Kommando-Notausgang

```bash
npm run engine:kapazitaet            # Lage der Bahnen, gemessen wie der Disponent misst
npm run engine:abgleich              # Phantom-Sperren gegen den Bestand lösen
npm run engine:deficit               # Zustand des Kanals engine-deficit (Trockenlauf)
npm run faktenfrische:deckung        # Bedarf gegen Angebot
python3 scripts/reserve_intake.py --md              # jede Übernahme und Ablehnung mit Grund
python3 scripts/politur_ruine_heiler.py --wirkungsprobe
```

## Nicht zuständig für

- **Wie ein Satz klingt, Rechtschreibung, Snippet-Länge** → `ff-marke-text`
- **Ob der Deploy durchläuft** → `ff-ausliefern`
- **Recherche-Zugänge, Modellrouten, Kosten** → `ff-ki-automation`

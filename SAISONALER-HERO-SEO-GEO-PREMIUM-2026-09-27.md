# Saisonaler Startseiten-Hero – SEO/GEO-Premium

**Umsetzung:** 27.09.2026
**Ablösung:** Der statische Willkommenstext aus `hugo.toml` ist vollständig entfernt. Es gibt keine `homeInfoParams.Title`- oder `Content`-Werte und keine alte Willkommenstext-Automation mehr.

## Was Besucher jetzt sehen

Die Startseite zeigt einen **saisonalen Hero** aus `data/saisons.yaml`:

- genau **eine H1** mit saisonaler Suchintention,
- einen **Antwort-zuerst-Lead**, der mit „FranksFinanzcheck“ beginnt und ohne Seitenkontext verständlich ist,
- einen klaren Saisonhinweis, drei messbare Einstiege und die vorhandenen Vertrauenssignale,
- den Saison-Fokus mit passenden Live-Ratgebern weiter unten.

Für den aktuellen Herbst lautet der Einstieg nicht mehr „Willkommen“, sondern führt direkt in die Aufgabe: Strom, Gas und Versicherung rechtzeitig vergleichen. Die vier Saison-Basistexte decken Herbst, Winter, Frühling und Sommer ab; der Wechsel erfolgt datumsbasiert ohne Template-Eingriff.

## SEO, GEO und Design

| Ebene | Vertrag |
|---|---|
| **SEO** | Die H1 benennt Saison und Suchintention (Sparen, Vergleichen oder Fixkosten). Meta-Title, Canonical, Description und Schema bleiben unverändert und werden vom Design-Gate geschützt. |
| **GEO** | Der Lead startet mit der Entity, nennt Saison, mindestens drei Kernthemen und den konkreten Nutzwert. So bleibt er für Antwortsysteme als einzelne Passage lesbar – ohne Ranking- oder Zitiergarantie. |
| **Premium-Layout** | Die freigegebene Variante `v-hero-premium` bleibt aktiv: editoriales Grid auf Desktop, kompakter Trust-Block, klare CTA-Hierarchie, Dark Mode, Fokuszustände und geschützte mobile LCP-Reihenfolge. |
| **Messbarkeit** | Alle Hero-CTAs behalten `cta_click`-Events. Der Saison-Fokus ist separat messbar. |
| **A11y/CWV** | Keine zusätzlichen Requests oder Skripte im Hero; genau eine H1, Dark-Mode-Varianten, reduzierte Bewegung und die vorhandenen Budgets bleiben Pflicht. |

## Automatische Kette: Agent Reach → Claude → Gates

Der Workflow **„Saisonaler Hero-Refresh (Agent Reach + Claude)“** läuft täglich um 05:15 UTC sowie manuell.

1. **Agent Reach** recherchiert lesend mit dem separaten, kuratierten Plan `data/agent_reach/saisonaler_hero.yaml` und schreibt einen tagesfrischen Brief nach `data/research/saisonal/`.
2. **Claude Sonnet 5** wird ausschließlich über die vorhandene kostenlose Puter.js-Brücke verwendet (`PUTER_AUTH_TOKEN`, keine Anthropic-API, kein Modell-Fallback). Claude poliert nur `hero_title` und `hero_lead` in Franks Stil.
3. **Faktenbremse:** Recherche-Treffer werden nicht als Tatsachen in den Text kopiert. Claude erhält nur bereits erlaubte Saison-Themen. Zahlen, Preise, Prozente, Fristen, Quellen, URLs und neue Anbieter sind im Kandidaten verboten.
4. **Verifikation vor dem Schreiben:** Entity-first, drei Kernkategorien, Saison, du-Ansprache, keine Floskeln, keine Faktenmarker und Neuheit gegenüber den letzten fünf Versionen.
5. **Saison-Gate + Hugo:** `saisonale_startseite_guard.py` prüft Quelle, Ton, GEO-Vertrag, Kontrast, CSS-Parität und den fertigen Build. Die Produktionswache bestätigt zusätzlich `v-hero-premium`.

Der Lauf ändert weder CSS noch Templates noch die Design-Freigabe. Automatischer Textwechsel und automatischer Designwechsel sind bewusst getrennt: Layoutänderungen bleiben menschen- und messpflichtig.


## Merge-/Wochen-Guard-Korrektur vom 27.09.2026

Nach der Ablösung des statischen Willkommenstexts darf die alte Wochen-Rotation nicht mehr als Fallback-Pool zurückschreiben. Der freigegebene Herbst-Hero ist deshalb als Basisstand in `data/saisonaler_hero_state.json` und `data/saisonaler_hero_history.jsonl` markiert; `scripts/saisonaler_hero_refresh.py --check` meldet damit „aktuell“ statt sofort neu zu rotieren.

Zusätzlich endet `data/willkommenstext_history.jsonl` jetzt auf einem Decommission-/Saison-Hero-Merge-Eintrag. Die Startseiten-Wache prüft diese Stilllegung: `homeInfoParams`, `scripts/willkommenstext_guard.py`, `.github/workflows/willkommenstext-refresh.yml` und neue `fallback`/`ai:*`-Einträge am Ende der Legacy-Historie sind wieder harte Funde.

## Fail-closed statt Schein-Automation

Fehlt der Agent-Reach-Brief, `PUTER_AUTH_TOKEN`, die Puter-Brücke oder besteht ein Kandidat die Verifikation nicht, schreibt die Automation **nichts**. Die geprüfte saisonale Basis bleibt sichtbar; der Workflow erstellt eine deduplizierte Issue. Damit wird kein unbestätigter KI-Text als Premium-Optimierung ausgegeben.

## Lokale Prüfung

```bash
python3 scripts/saisonaler_hero_refresh.py --selftest
python3 scripts/saisonaler_hero_refresh.py --check
# Bei Merge-/Konfliktentscheid den aktuellen Saison-Hero als Basis bestätigen:
python3 scripts/saisonaler_hero_refresh.py --set-current --reason "Merge-Entscheid bestätigt"
python3 scripts/saisonale_startseite_guard.py --source-only
hugo --minify
python3 scripts/saisonale_startseite_guard.py --public public
python3 scripts/design_variant_gate.py --produktionswache
```

Für eine echte Claude-Politur muss vorher ein Brief für den heutigen UTC-Tag unter `data/research/saisonal/` vorliegen und `PUTER_AUTH_TOKEN` gesetzt sein:

```bash
python3 scripts/agent_reach_research.py \
  --plan data/agent_reach/saisonaler_hero.yaml \
  --out-dir data/research/saisonal
PUTER_AUTH_TOKEN=… python3 scripts/saisonaler_hero_refresh.py --fix
```

Die Nachweise liegen versioniert in `data/saisonaler_hero_state.json`, `data/saisonaler_hero_history.jsonl` und im zugehörigen Agent-Reach-Brief. Der Laufreport ist bewusst nur ein CI-Artefakt.

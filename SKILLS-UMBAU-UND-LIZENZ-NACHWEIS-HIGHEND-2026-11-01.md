# Skills-Umbau: Kernbudget, sechs ff-Skills, Lizenznachweis (Highend, 01.11.2026)

> Status: umgesetzt und nachgewiesen. Wahrheitsort für den Betriebsablauf ist
> `docs/ANLEITUNG-SKILLS.md`; diese Datei hält Vorgang, Zahlen und Entscheidungen fest.

## Ausgangslage (gemessen, nicht geschätzt)

| Befund | Wert am 01.11.2026 |
|---|---|
| `CLAUDE.md` | 2.532 Zeilen · 161.706 Bytes (157,9 KB) · ~39.700 Tokens |
| Ladezeitpunkt | bei **jedem** Agenten-Start, unabhängig vom Auftrag |
| Abschnitte im Leitfaden | 67 (`##`-Ebenen, Code-Zäune mitgezählt) |
| Installierte Skills | 18 in `.claude/skills/`, **in Git versioniert**: 191 Dateien, 5,6 MB |
| Immer geladene Skill-Beschreibungen | ~3.335 Tokens (18 × Name + Beschreibung) |
| Vendored Skills ohne Lizenztext | 16 von 18 (nur `frontend-design`, `webapp-testing` trugen `LICENSE.txt`) |
| installierter Skill ohne auffindbare Herkunft | `web-design-guidelines` (Upstream ohne Lizenzangabe) |

Der Leitfaden war damit kein Dokument, sondern eine Steuer: Jeder Auftrag
bezahlte 40k Tokens für Backup-Fristen und Snippet-Pixel, die er brauchte oder
nicht. Gleichzeitig war die eigentliche Idee – Skills als Bedarfs-Wissen –
schon vorhanden und wurde nur für Fremd-Content benutzt.

## Entscheidungen

1. **Kein zweiter Schwung Fremd-Skills.** `anthropics/skills` bietet 19 Skills,
   davon sind zwei bereits installiert. Eine Vollinstallation hätte ~1.500
   Tokens Dauerlast und fünf weitere Abhängigkeiten pro Repo bedeutet, ohne ein
   einziges Gate dieses Blogs abzudecken. Die 17 unpassenden (Slack-GIF,
   Canvas, Theme-Factory, pptx …) sind Beispiele, keine Werkzeuge.
2. **Umbau des eigenen Regelwerks in dasselbe Format.** Progressive Disclosure
   ist genau dafür erfunden: 63 von 67 Abschnitten wandern in sechs repo-eigene
   Skills, der Kern behält, was jeden Auftrag angeht.
3. **Wörtlich, nicht nacherzählt.** Die Verschiebung erfolgte maschinell pro
   Abschnitt; kein Satz wurde umformuliert, gekürzt oder erfunden. Eine
   Unit-Sperre (`test_wörtliche_übernahme_kein_umgeschrieben`) vergleicht jede
   Überschrift in `references/` gegen den früheren Kern.
4. **Vertrag statt Hoffnung.** Eine neue Wache `scripts/skills_vertrag.py`
   (K1–K7) hält Budget, Erreichbarkeit, Herkunft, Lizenz und Befehle; sie steht
   im vertraglichen Minimum (`GUARDS`, C6) und läuft deshalb mit dem
   Qualitäts-Gate auf jeden Push und jede PR – **ohne** eine Workflow-Datei
   anzufassen (Kern-Regel 3).

## Umsetzung

```
CLAUDE.md                     2.532 → 237 Zeilen (17,4 KB) · −89 % Vorladelast
.claude/skills/ff-pruefen/     SKILL.md + 4 references  (Prüfkatalog, Wachen, Artefakte, Erzeuger)
.claude/skills/ff-ausliefern/  SKILL.md + 4 references  (CI, Blockaden, Alarme, Bestand/Backup/Merge)
.claude/skills/ff-produzieren/ SKILL.md + 7 references  (Bahnen, Faktenfrische, Reserve, Aussteuerung,
                                                         Einzigartigkeit, Schreibvertrag)
.claude/skills/ff-marke-text/  SKILL.md + 5 references  (Markenfläche, Sprache, Metadaten/SERP/Tags,
                                                         Kennzeichnung, Verbreitung)
.claude/skills/ff-oberflaeche/ SKILL.md + 2 references  (Robustheit, Werkzeuge/Header)
.claude/skills/ff-ki-automation/ SKILL.md + 4 references (Transportweg/Kostensperre, Werkbank/Recherche,
                                                         Suchradar, Schaltwerk)
data/skill_lizenzen.json      Herkunft + Lizenz je Skill, Ausnahme mit Frist
scripts/skills_vertrag.py     K1–K7, --selftest mit 13 Fällen
scripts/tests/test_skills_vertrag.py   31 Unit-Tests
docs/ANLEITUNG-SKILLS.md      Runbook (Ablage, Gründung, Fremd-Skill, Nachweis)
```

Kern-Geblieben (wörtlich): Repository-Satz, die sechs **Sicherheitsregeln**, der
**UI-/Design-Abschnitt** mit Skill-Tabelle, **Keine Fremdmessung**, **Wichtige
Konventionen**. Die Nummerierung der beiden Pflichtlisten ist erhalten, weil
`scripts/mini_toc_premium_guard.py` auf „CLAUDE.md §4“ und
`.github/workflows/seo-paritaet.yml` auf „Regel 4“ verweist – K7 löst solche
Verweise jetzt prüfend auf statt sie zu überleben.

Lizenznachweis: 14 Lizenztexte ergänzt (12 × MIT aus `coreyhaines31/marketingskills`,
MIT für `design-taste-frontend` und `agent-reach`) plus Apache-2.0 `LICENSE.txt`
**und** `NOTICE.md` für `impeccable` (§4(d) verlangt die Weitergabe einer
vorhandenen NOTICE). 17 von 18 vendored Skills sind damit sauber ausgewiesen.

## Nebenbefunde, die die neue Wache sofort gefunden hat

* `npm run faktenfrische:deckung` wurde im Leitfaden seit #912 befohlen,
  existierte aber nie in `package.json` – ein Schritt ohne Erzeuger in der
  Report-Klasse #806. Neu: `faktenfrische:deckung` und `faktenfrische:wache`
  (beide auf `scripts/faktenfrische_kapazitaet.py`).
* Eine verlinkte Detaildatei (`design-vertrag.md`) war ohne Sinn gedoppelt –
  die fünf Basissätze stehen wörtlich im Kern; K3/K5 erzwangen die eine Fassung.

## Nachweis (lokal, 01.11.2026)

```
python3 scripts/skills_vertrag.py --selftest      ✅ 13 eingefrorene Fälle
python3 -m unittest scripts.tests.test_skills_vertrag   ✅ Ran 31 tests, OK
python3 scripts/skills_vertrag.py                 ✅ 24 Skills, 0 Befunde, 0 Warnungen
python3 scripts/skript_syntax_wache.py            ✅ grün (623 Dateien)
python3 scripts/wachen_vertrag.py                 ✅ 370 Skripte, 0 Funde
python3 scripts/redos_guard.py                    ✅ 634 Python-Dateien, 0 Funde
python3 scripts/fremdmessung_sperre.py            ✅ keine Spur
python3 scripts/manifest_guard.py                 ✅ GRÜN (13 Manifeste)
python3 scripts/report_hygiene.py --check         ✅ Root sortenrein
python3 scripts/governance_contract.py --quick    ✅ 43 Regeln, beide Richtungen
```

## Nebenbefund aus der Abnahme (nicht verursacht, aber belegt)

`python3 scripts/redaktions_standard.py --selftest` ist auf `main` **rot**
(Exit 2, Fall `Vertrag-gute-aenderung-still`) – nachgewiesen in einem frischen
Worktree auf dem Ausgangscommit `51e0270`, also unabhängig von diesem Umbau.

Warum das hier steht: Die Wache steht im vertraglichen Minimum (`GUARDS`, C6).
Der volle Vertragslauf führt den Selbsttest aus – damit ist der Qualitäts-Gate
auf jedem Push rot, ohne dass ein Gate etwas am Blog gefunden hätte. Das ist die
Klasse „ein Befund, der die Arbeit blockiert, statt sie zu beschreiben“.

**Nicht geheilt, mit Grund:** `scripts/redaktions_standard.py` ist KRITISCH
versiegelt (`data/integrity_lock.json`, 50 Dateien) und `.gitattributes` setzt
`merge=binary` auf alle signierten Skripte. Eine Änderung daran verlangt die
menschliche Neu-Signatur (`integrity_guard.py --set-current`), die kein Agent
ersetzt. Der Befund gehört in den nächsten Siegel-Termin – nicht in einen
Unterdrückungs-Kommentar.

Zwei Hinweise für die Heilung, gemessen am Fall:
* Der Fixture-Text und sein „gutes“ Gegenstück unterscheiden sich in Länge und
  Wortwahl (`Kurzer Satz hier.` → `Kurzer Satz steht hier.`); der Vertrag meldet
  einen Grund, wo der Fall Stille erwartet. Das ist entweder eine zu enge
  Tolerz im Fall oder eine zu scharfe Regel im Detektor – beides entscheidbar,
  aber nur mit dem Original-Vorgang WF-54C4/#607 im Blick.
* `test_selbsttest_der_redaktions_wache_laeuft` in
  `scripts/tests/test_wachen_vertrag.py` ist die Sperre, die diesen Zustand
  seit #783 fernhält – sie schlägt korrekt an. Die Wache ist also nicht
  vergessen, sie ist erweislich kaputt.

## Offene Punkte (bewusst nicht entschieden)

1. **`web-design-guidelines` ohne Lizenz.** Upstream `vercel-labs/agent-skills`
   führt weder LICENSE noch `license`-Feld. Die Ausnahme im Register trägt Grund,
   Entscheidung und Frist **31.12.2026**. Optionen: Lizenz erfragen, eigener
   Haus-Leitfaden (die tragenden Regeln stehen bereits in `DESIGN.md` und
   `ff-oberflaeche`), oder entfernen. Ein Agent entscheidet das nicht.
2. **Siegel.** `scripts/skills_vertrag.py` ist **nicht** in
   `data/integrity_lock.json` versiegelt, und `data/skill_lizenzen.json` hat
   keinen `merge=binary`-Eintrag in `.gitattributes`. Beides ist eine
   Inhaber-Handlung beim nächsten Siegel-Termin (`integrity_guard.py
   --set-current` verlangt die menschliche Unterschrift).
3. **Kein eigener CI-Job.** Die Wache läuft über C6 im Qualitäts-Gate. Ein
   eigener Schritt wäre deutlicher, berührt aber `.github/workflows/**`
   (Kern-Regel 3) und braucht einen ausdrücklichen Auftrag.
4. **Zwei Wartungsfragen fürs nächste Quartal:** Ob `npx skills update` mit
   repo-eigenen Ordnern im `.claude/skills/`-Baum sauber umgeht (K4 verbietet
   wenigstens den Lock-Eintrag), und ob die 228 Root-Berichte in dieselbe
   Struktur umziehen – dieser Umbau hat gezeigt, dass Verschieben ohne
   Inhaltsumbruch billiger ist als Aufräumen durch Löschen.

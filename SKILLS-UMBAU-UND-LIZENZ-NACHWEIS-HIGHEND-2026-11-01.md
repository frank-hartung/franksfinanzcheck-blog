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

## Offene Punkte (bewusst nicht entschieden — am selben Tag geschlossen, siehe letzter Abschnitt)

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

## Zweiter Schwung: die vier offenen Punkte, umgesetzt (01.11.2026)

Auftrag: keiner der vier Punkte darf als Fußnote enden. Stand nach diesem
Abschnitt: 1, 3 und 4 sind erledigt, 2 ist vorbereitet und bleibt ein
Menschenakt – mit Kommando, Reihenfolge und Grund.

### 1 · Vercel-Lizenzfrage: geschlossen, nicht verlängert

Entfernt über den Werkzeugweg, nicht durch Löschen im Ordner:

```bash
npx -y skills@1.7.4 remove web-design-guidelines -y
```

Der CLI nimmt damit exakt das, wofür er den Eintrag je geschrieben hat: die
Skill-Datei und ihren `skills-lock.json`-Eintrag (`a6a44d54…`). Ohne `-y` steht
er an einer Ja/Nein-Frage und tut nichts – im Automatenlauf ein grüner Schritt
ohne Wirkung, deshalb gehört der Schalter in jede Doku.

Was der Skill tat, liegt jetzt hausgemacht:
`.claude/skills/ff-oberflaeche/references/web-richtlinien.md`, 24 Punkte in sechs
Gruppen (Struktur, Wahrnehmbarkeit, Bewegung/Zeit, Zeiger/Tastatur, Text im
Interface, Kopf/Ressourcen). Jeder Punkt ist entweder an einem bestehenden Gate
beweisbar (Kontrast, A11y, Werkzeuge, Kopf, Variante) oder im Review mit Datei
und Zeile zu benennen – die Liste ist bewusst keine Geschmacks-Erweiterung,
sondern die Summe dessen, was dieses Repo schon messen kann. Kern-Tabelle und
`DESIGN.md`-Kopf zeigen seither dorthin. Im Register steht der Fall unter
`erledigte_faelle` (Grund, Heilung, Datum), die Ausnahme selbst ist weg:
**18 Fremd-Skills, 18 Lizenztexte, 0 Ausnahmen.**

Nebenbefund mit Wert: `npx skills` hat den Lock-Eintrag **an der richtigen Stelle**
ausgetauscht (alphabetisch, Format erhalten) – der Lock ist also nicht nur
schreibbar, sondern round-trip-fähig. `computedHash` ist dabei **nicht** die
SHA-256 von `SKILL.md` (an `frontend-design` und `webapp-testing` nachgerechnet);
ein von Hand gesetzter Hash sähe gültig aus und wäre es nie. Seit diesem Tag
steht das in `docs/ANLEITUNG-SKILLS.md` und `.gitattributes` trägt
`merge=binary` für beide Register – dieselbe Klasse wie der kaputte
Merge-Schnitt des Siegels (#346), nur hier mit Herkunftsangaben statt Hashes.

### 2 · Siegel: K8 meldet den Stand, die Unterschrift bleibt beim Betreiber

Nagelt man `scripts/skills_vertrag.py` und `data/skill_lizenzen.json` nicht ins
Schloss, entscheidet jeder Schreibende über Lizenzen und Kernbudget, ohne dass
es laut wird. Neu geprüft wird das in **K8**, und zwar immer als **Warnung mit
Schlusszeile** – nie als Befund:

```text
[K8] scripts/skills_vertrag.py – steht weder in KRITISCH/FEST noch im Siegel – …
```

Der Verzicht auf Exit 1 ist keine Feigheit, sondern die Lehre aus #316: Ein HARD
STOP auf eine ungezeichnete Datei traf am 19.09.2026 die Content-Engine im
ersten Schritt, während der eigentliche Fehler eine vergessene Signatur war. Ein
Gate, das Produktion geiselt, um eine Formalität beizubringen, verliert die
Debatte in der ersten Woche.

Warum hier **nicht** signiert wurde: `npm run test:redaktion` ist rot (Fall
„Vertrag-gute-aenderung-still“, auf frischem Auschecken von `51e0270`
reproduziert, also vorbestehend), und `scripts/redaktions_standard.py` ist
FEST-versiegelt. Eine Signatur auf diesem Stand würde den Defekt waschen – das
Schloss erklärt dann einen Zustand für gut, dessen eigener Selbsttest Nein sagt.
Der Auftrag mit Reihenfolge, Kommandos und der Audit-Tabelle steht in
`docs/SICHERHEIT-BETRIEB-RUNBOOK.md` § G1–G3. Vorgesehen ist außerdem:
`--add=` akzeptiert einen Pfad nur, wenn er in `KRITISCH` oder `FEST` steht
(Zeile ~1810 der Wache) – die Klassenerweiterung gehört deshalb in denselben
Commit wie die Zeichnung, sonst steht jedes PR-Gate rot.

### 3 · Eigener Schritt im Gate

`.github/workflows/link-check.yml` hat seit heute einen eigenen Schritt vor dem
Hugo-Bau-Vertrag:

```yaml
- name: Skill-Vertrag (Kernbudget, Router, Herkunft, Lizenz, Siegelstand)
```

Er fährt Prüfung, Selbsttest und Regressionstests. Der Trigger brauchte keine
Änderung (der Workflow läuft auf push/PR/Plan ohne `paths:`-Filter), und der
vorhandene Schritt „Gate-Fehlschlag melden“ verwendet `failure()` – ein Fall
dieses Schrittes meldet sich also von selbst, mit dem gefallenen Schritt im Text,
was „Reihenfolge statt Raterei“ (C14) heißt. `governance_contract.py --quick`
prüft nach wie vor 43 Regeln in beide Richtungen und steht auf Grün, die
Wache stand bereits vorher in `GUARDS` (C6).

### 4 · Zwei Anlagen, die Prüfung bestanden – eine abgelehnt

**`skill-creator` (anthropics/skills, Apache-2.0) aufgenommen**: 256 KB, 18
Dateien, `LICENSE.txt` liegt bei und ist **bytegleich** mit dem von
`webapp-testing` (11.345 B reines Apache-2.0, keine Zusatzklausel). Vorher am
Kratz-Baum geprüft: Syntaxwache 623 grün, REDOS 643 Dateien 0 Funde (+9),
Wachen-Vertrag 370/0, Fremdmessung-Sperre still – und **K6 meldete sofort den
fehlenden Register-Eintrag**. Genau dafür ist die Wache da: eine neue Anlage kann
nicht ohne Herkunftsnachweis hineinschlüpfen.

**`xlsx` (dasselbe Haus) abgelehnt – mit Messung statt Bauch.** 63 Dateien,
1.102.893 Bytes, und eine `LICENSE.txt` über 1.467 Bytes, die exakt das
verbietet, was ein Vendor-Ordner ist: „may not extract these materials from the
Services or retain copies of these materials outside the Services … create
derivative works … distribute“. Dasselbe Blatt bei `pdf` und `docx`. Und selbst
ohne das: im Repo liegt keine Tabellenkalkulation – die beiden .xlsx/.pdf-Dateien
wurden am 31.08.2026 daraus entfernt („gehören in Notion/Drive, nicht ins
Git-Repo“, `docs/CLEANUP-REPORT-2026-08-31.md`).

Die Lizenzmischung in diesem Haus war der Anlass, **K6 nachzuschärfen**: `MIT`
und `Apache-2.0` sind nachprüfbare Freigaben, jeder andere Wert braucht
Ausnahme mit Grund, Entscheidung und Frist – das Repo-Zeichen eines Upstreams
sagt nichts über seinen Ordner. Dabei fiel die zweite Lücke auf: Die Ausnahme
beendete den Prüfschritt bisher mit `continue`, und hat damit den Lizenztext
gleich mit erledigt. Jetzt endet der Block nur bei „unbekannt“ (wo es per Definition
nichts zu kopieren gibt); bei einer bekannten Sonderlizenz bleibt die
Volltextpflicht. Zwei Tests, ein Selbsttest-Fall.

### Nachweis

| Prüfung | Ergebnis |
|---|---|
| `python3 scripts/skills_vertrag.py` | 24 Skills · 0 Befunde · 2 Warnungen (K8, erwarteter Siegelhinweis) |
| `python3 scripts/skills_vertrag.py --selftest` | ✅ 17 Fälle (vorher 13) |
| `python3 -m unittest scripts.tests.test_skills_vertrag` | ✅ 33 Tests (vorher 31) |
| `governance_contract.py --quick` | ✅ 43 Regeln, in beide Richtungen |
| `skript_syntax_wache.py` · `wachen_vertrag.py` · `redos_guard.py` | ✅ 623 · 370/0 · 643/0 |
| `fremdmessung_sperre.py` | ✅ keine Spur, auch nicht in den neuen Skill-Ordnern |
| `report_hygiene.py --check` | ✅ Root sortenrein |
| `design_handoff.py --check` | ✅ nach Generatorlauf (Kopfzeile in `DESIGN.md` hatte der Manifest-Hash erwartet – geheilt mit `python3 scripts/design_handoff.py`, ein Hash in `design/handoff/handoff-manifest.json`, 8 weitere Artefakte bytegleich) |
| Kern und Skills | `CLAUDE.md` 239 Zeilen / 17,5 KB (Budget 420 / 32 KB) · `ff-oberflaeche` 87 Zeilen (Budget 200) |
| `content/` | unverändert, kein Artikel angefasst |

### Was bleibt

Zeichnen (Betreiber, § G). `hugo` steht in dieser Sandbox nicht zur Verfügung,
der Bau bleibt damit ungeprüft – er wird auch im Gate gebaut, und keiner der
geänderten Pfade liegt im Hugo-Eingabebaum (`.claude/`, `CLAUDE.md`,
`skills-lock.json`, `data/skill_lizenzen.json` werden nicht gerendert).
`scripts/redaktions_standard.py` bleibt der vorbestehende Defekt, dessen Heilung
die Signatur voraussetzt, nicht umgekehrt. Und die Quartalsfrage aus Punkt 4
(228 Root-Berichte in dieselbe Struktur) ist unbeantwortet – dieser Umbau hat
nur gezeigt, dass Verschieben billiger ist als Aufräumen durch Löschen.

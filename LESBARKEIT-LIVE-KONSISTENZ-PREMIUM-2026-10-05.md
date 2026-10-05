# Lesbarkeit & Live-Konsistenz – Premium-Instandsetzung vom 05.10.2026

Grundlage: Governance-Report **#585** („Redaktionelle & technische
Handlungsfelder", Fingerprint `5a5b9df06cc5`, ROT).

Gemeldet waren zwei Befunde. Behoben sind **drei** Dinge: die beiden Befunde –
und die Ursache, warum der redaktionelle Befund überhaupt entstehen konnte. Der
Report ist der Nachweis dafür, dass hier nicht Symptome weggeschrieben wurden,
sondern die Kette repariert ist.

---

## 1. Befund A – Lesbarkeit des Bestands

**Meldung:** Ø Flesch der Live-Artikel **61,3** (Ziel ≥ 62,0), **9 Artikel**
unter dem Boden von 55,0. `readability_check.py --gate-bestand` → Exit 1.

### Warum das passiert ist

Der entscheidende Satz steht nicht in der Lesbarkeits-Wache, sondern im
Publish-Tor. `publish_gate.readability_failures()` blockierte einen neuen
Artikel **ausschließlich** über den zusammengesetzten Score (`< 75`). Dieser
Score ist ein Mittel aus sechs Teilnoten; ein Flesch-Wert von 47 kostet darin
lediglich 20 Punkte. Ergebnis: Ein Text mit Flesch 47,4 kam mit 80/100 durch das
Tor, ging live – und die Bestands-Wache durfte hinterher melden, was sie nicht
mehr verhindern durfte.

Eine Wache ohne zugehöriges Tor ist ein Protokoll. Genau das war der Zustand.

### Was getan wurde

**(a) Der Bestand wurde redaktionell instandgesetzt – alle 9 Artikel.**
Keine Schwellen-Kosmetik, keine Textkürzung: Jeder Artikel wurde in einfaches
Deutsch umgeschrieben. Nominalstil zu Verben, Komposita zu Alltagswörtern,
Sätze von ~13 auf 8–10 Wörter, Absätze auf höchstens drei Sätze. Tabellen,
Listen, Links, CTAs, Affiliate-Hinweise und alle `/go/…`-Anker blieben
unangetastet; NBSP vor `€`/`%` und geschützte Bindestriche sind erhalten.

| Artikel | Flesch vorher | Flesch nachher |
|---|---:|---:|
| `2026-09-30-last-minute-urlaub-…` | 47,4 | **77,6** |
| `2026-10-02-weihnachten-budget-planen-…` | 50,3 | **79,3** |
| `2026-08-10-sicher-heizen-…-preisgarantie-gas` | 50,4 | **76,3** |
| `2026-08-14-gasrechnung-senken-…` | 52,4 | **79,5** |
| `2026-10-05-budget-app-2026-…` | 52,7 | **73,6** |
| `2026-08-17-kostenloses-girokonto-…` | 53,5 | **76,2** |
| `2026-10-02-preiswert-surfen-…-dsl-anschluss` | 53,7 | **77,6** |
| `2026-08-26-tagesgeld-zinsen-2026-…` | 53,8 | **76,8** |
| `2026-10-05-oekostrom-anbieter-wechseln-…` | 54,1 | **74,7** |

Zwei Artikel wären durch die Vereinfachung unter den Längen-Boden von 10 000
Zeichen gefallen (einfaches Deutsch spart ~10–15 % Zeichen). Statt Füllmaterial
bekamen sie echten Mehrwert: eine Anschluss-Vergleichstabelle und einen
Störungs-Abschnitt (`preiswert-surfen`), eine Kostentabelle und die
Drittel-Regel (`weihnachten-budget-planen`). `check_length.py`: 40 Artikel,
**0 zu kurz, 0 zu lang**.

**(b) Das Tor wurde geschlossen (die eigentliche Reparatur).**
`publish_gate.readability_failures()` prüft ab sofort zusätzlich die
Flesch-Schwelle und zwar über die **importierte** SSOT
`readability_check.NEW_FLESCH_MIN` (60,0) – keine kopierte Zahl, keine zweite
Wahrheit. 60 statt 55 ist bewusst gewählt: Ein neuer Artikel soll den
Durchschnitt heben, nicht nur den Boden streifen. Der Collector bleibt
fail-closed (Prüfer nicht importierbar/auswertbar → blockiert).

Wirkung sofort messbar: Von 22 Entwürfen blockiert das Tor jetzt **8**, die den
Bestand erneut nach unten gezogen hätten (siehe Abschnitt 4). 14 bleiben
veröffentlichungsfähig – die Reserve läuft weiter.

### Ergebnis

```
✅ Bestands-Gate OK – 40 Live-Artikel, Ø Flesch 66,9, kein Live-Artikel unter Floor 55
```

Ø **66,9** statt 61,3 (Ziel ≥ 62,0), Boden-Verstöße **0** statt 9.

---

## 2. Befund B – Live-Konsistenz (Cloudflare/CDN)

**Meldung:** „2 Money-URL(s) fehlen live in der Sitemap" und
„`/posts/…/` liefert live HTTP 404" → ROT.

### Warum das passiert ist

Beide beanstandeten URLs trugen das Veröffentlichungsdatum **desselben Tages**,
an dem die Wache lief. Zwischen `git push` und ausgelieferter Seite liegen
zwangsläufig Hugo-Build, Pages-Deploy und CDN-Invalidierung. Die Wache maß also
nicht Drift, sondern die Laufzeit der Auslieferung – und meldete die Physik als
Fehler. Verschärfend: Die Seiten-Probe wählte ausdrücklich den **neuesten**
Artikel aus dem Build, also mit höchster Wahrscheinlichkeit genau den, der
gerade erst deployt wurde. Die Wache war so gebaut, dass sie sich selbst rot
machte.

Dauer-Rot ohne Handlungsmöglichkeit ist Alarm-Müdigkeit – der teuerste Fehler
in einem Betrieb mit 30+ Automatisierungen (#206-Policy).

### Was getan wurde

Ein **endliches Deploy-Fenster** in `scripts/live_policy_guard.py`:

- `GRACE_MIN` (Vorgabe 90 min, über `LIVE_POLICY_GRACE_MIN` einstellbar).
- `published_at()` liest den spätesten Zeitstempel aus dem Frontmatter
  (`date` / `reserve_published` / `lastmod`) – deterministisch und ohne
  Netz- oder Git-Abhängigkeit. Keine Datei, kein Fenster: unbekannte URLs
  gelten als alt, die Prüfung bleibt also **fail-closed**.
- Fehlende Money-URL **innerhalb** des Fensters → Hinweis `deploy_hysterese`
  (benannt, sichtbar, kein Issue). **Außerhalb** → unverändert ROT.
- Gleiches für den HTTP-Status einer Seite.
- Die Seiten-Probe nimmt jetzt den jüngsten Artikel, der das Fenster bereits
  **verlassen** hat. Nur wenn es keinen gibt, bleibt der frische – dann greift
  die Hysterese.
- `deploy_hysterese` steht in `governance_gate.INFO_AMBER`: nie ein Issue. Die
  Eskalation steckt im Fenster selbst – nach 90 Minuten meldet dieselbe Wache
  denselben Sachverhalt als `sitemap_drift` / `page_drift` in ROT.

Ein eigener Code war nötig, weil die Hinweise sonst unter `sitemap_drift`
gelaufen wären – also unter dem Namen genau des Fehlers, den sie ausschließen.

---

## 3. Regressionsschutz (damit es dauerhaft bleibt)

| Ort | Schutz |
|---|---|
| `live_policy_guard.py --selftest` | **9 Fälle** statt 5. Neu: frischer Artikel fehlt live → kein ROT, benannter Hinweis, Probe weicht auf den reifen Artikel aus (Fall 6); derselbe Stand nach Fensterablauf → ROT (Fall 7); 404 der einzigen, frischen Seite weich / nach Ablauf hart (Fall 8); Fenster-Arithmetik gegen echtes Frontmatter inkl. „unbekannte URL bekommt kein Fenster" (Fall 9). Das Fenster wird im Test injiziert – der Selbsttest ist datumsunabhängig. |
| `governance_contract.py` → **C20** | Neuer Vertragspunkt „Lesbarkeits-Tor & Deploy-Hysterese": das Publish-Tor muss `NEW_FLESCH_MIN` prüfen **und** aus `readability_check` importieren (eigene Definition = Verstoß); `AVG_TARGET` ≥ 62, `NEW_FLESCH_MIN` ≥ 60, `FLOOR_MIN` ≤ 55 dürfen nicht aufgeweicht werden; das Deploy-Fenster muss existieren, über `LIVE_POLICY_GRACE_MIN` einstellbar und ≤ 180 min sein; `deploy_hysterese` muss als INFO_AMBER eingestuft sein. Gegengeprüft: jede dieser Manipulationen erzeugt im Test einen Befund. |
| `readability_check.py --selftest` | Unverändert grün – verteidigt die Schwellen weiterhin gegen Absenken. |
| `publish_gate` | Fail-closed-Pfad unverändert; die neue Bedingung sammelt Gründe additiv, der Score-Grund bleibt erhalten. |

---

## 4. Offene redaktionelle Nachliste (bewusst, nicht blockierend)

Diese **8 Entwürfe** werden vom geschärften Tor blockiert, bis sie in einfaches
Deutsch gebracht sind. Sie sind nicht live und gefährden den Bestand nicht – das
Tor tut hier genau seine Arbeit:

| Entwurf | Flesch |
|---|---:|
| `digital-banking-vorteile-moderner-online-konten-nutzen` | 48,3 |
| `dein-haus-sicher-schuetzen-das-neue-vorsorge-update-2026` | 50,0 |
| `bankgebuehren-sparen-so-halbierst-du-deine-kosten` | 51,0 |
| `konto-wechseln-2026-so-sparst-du-gebuehren-ohne-stress` | 52,8 |
| `e-auto-ladekosten-so-drueckst-du-deine-ausgaben-massiv` | 53,1 |
| `strom-und-gas-teure-fehler-beim-vergleichen-vermeiden` | 54,4 |
| `die-50-30-20-regel-einfach-erklaert` | 55,2 |
| `privathaftpflicht-warum-sie-so-wichtig-ist-und-was-sie-kostet` | 55,5 |

Das Rezept steht fest und ist neunmal erprobt: kurze Aussagesätze (8–10 Wörter),
höchstens drei Sätze je Absatz, Komposita und Nominalstil in Verben auflösen,
Anglizismen ersetzen, Satzanfänge variieren.

---

## 5. Nachweislauf

```
python3 scripts/readability_check.py --gate-bestand   → Exit 0 · Ø 66,9 · 0 unter Floor
python3 scripts/readability_check.py --selftest       → OK
python3 scripts/live_policy_guard.py --selftest       → 9 Fälle grün
python3 scripts/check_length.py                       → 40 Artikel · 0 zu kurz · 0 zu lang
python3 scripts/textverstaendnis_guard.py --json      → 97 Hinweise (vorher 99), 0 harte Verstöße
python3 scripts/governance_contract.py                → C20 grün
```

Hinweis zur Umgebung: In dieser Werkbank fehlen `hugo` und `PyYAML`, deshalb
melden `C6`/`C19` umgebungsbedingte Fehler (Build-Rumpf, `release_scorecard.yaml`).
Diese Befunde bestanden vor der Instandsetzung und sind von ihr unberührt; die
Live-Wache wurde deshalb über ihren gemockten Selbsttest verifiziert.

---

## 6. Die Lehre

Beide Befunde hatten dieselbe Bauart: **Eine Wache meldete etwas, das ein
anderer Teil der Kette hätte verhindern – oder gar nicht erst als Fehler werten
– müssen.** Einmal fehlte das Tor vor der Wache, einmal fehlte der Wache der
Begriff von Zeit. Deshalb ist die Reparatur nicht der Textumbau und nicht die
Ausnahme, sondern C20: Lesbarkeit ist ein Tor, kein Protokoll – und
Auslieferungszeit ist keine Drift.

# ⚠️→✅ Bot-Watchdog „Automatisierung braucht Eingriff" – dauerhaft behoben (#462)

**Stand:** 2026-09-30 · **Besitzer:** Content-Automatisierung (Maschine)
**Auslöser:** Issue #462 · **Niveau:** Profi-Agentur (Ursache, Prävention, Backstop, Test)

---

## 1. Was das Ticket wirklich meldete

Zwei Befunde standen im Automations-Ticket – beide als „Maschine heilt das",
beide ohne Heiler. Genau diese Lücke macht ein Ticket zum Dauergast:

| Befund | Scheinbare Ursache | Echte Ursache |
|---|---|---|
| **Content-Reserve niedrig** (1 von 6 gate-fertig, Blocker „Zertifikat passt nicht mehr zum Entwurf") | zu wenig Content | **Nachweis-Engpass**: alle 3 zertifizierten Kandidaten waren nach der Zertifizierung von Heiler-Läufen angefasst worden |
| **Pinterest-Report veraltet** (Quellfingerabdruck passt nicht) | Report nicht erzeugt | **Messlatte zu breit**: der Fingerabdruck hashte ALLE Artikel-Bytes – der Morgen-Artikel (08:10 UTC) entwertete den 04:30-Report, jeden Tag, per Konstruktion |

Nachgemessen im Repo-Stand vom 30.09.: **alle acht** Reserve-Entwürfe wichen
vom Zertifikat ab, der Pinterest-Abdruck wich ebenfalls ab. Der Bestand war
also nicht leer – er war **unbelegt**.

Das ist dieselbe Fehlerklasse wie #272 (ein Meldeweg für alles) und #393
(Alarmschwelle = Ziel): Ein Zustand, den das Ticket meldet, aber niemand
heilen kann, kommt jeden Tag zurück und trainiert das Team darauf, den Melder
zu ignorieren.

---

## 2. Die Lösung in vier Schichten

### Schicht 1 – Nachzertifizierung als eigenständiges Werkzeug
**Neu: `scripts/reserve_recert.py`**

* erkennt Drift billig und ohne Hugo (sha256 je Entwurf) und unterscheidet
  `geaendert` / `verschwunden` / `unzertifiziert`,
* **nennt den Verursacher** (letzter Commit auf dem Entwurf) – ein Befund ohne
  Besitzer ist Rauschen,
* misst mit `--fix` **nur die betroffenen** Kandidaten am echten Gate neu
  (`reserve_readiness.certify_one` – exakt die Messvorschrift des Nachtlaufs,
  dafür herausgelöst; zwei Messvorschriften für dieselbe Reife wären die
  nächste „zweite Wahrheit"),
* schreibt Provenienz ins Zertifikat (`recert.renewed`), damit ein Teil-Lauf
  nie wie ein Volllauf aussieht.

### Schicht 2 – Zwei Sicherungen gegen erfundene Ergebnisse
Eine Nachzertifizierung kann Bestand **vernichten**. Deshalb fail-closed:

1. **Messkette wird bewiesen** (`gate_verfuegbar`): Hugo *und* eine lauffähige
   Rechtschreib-Kette. Hintergrund: `quality_score` wertet eine nicht
   startbare Rechtschreibprüfung als `spelling = 0.5` („unbekannt"). Bei
   Gewicht 0.20 drückt das jeden Artikel unter die 0.85-Schwelle. Im ersten
   Probelauf dieser Reparatur (Sandbox ohne `hunspell`) hätte das **acht
   gesunde Kandidaten** abgewertet – ein Werkzeugmangel, der wie ein
   Qualitätseinbruch aussieht. Jetzt: Exit 3, **keine Schreibaktion**.
2. **Abwertungs-Bremse**: Werden mehr als die Hälfte der zertifizierten
   Kandidaten abgewertet und nennen **alle** dieselbe schwächste Teilnote,
   bricht der Lauf ab (bewusst erzwingbar mit `RESERVE_RECERT_FORCE=1`).
   Das fängt auch die Werkzeuglücken ab, die wir noch nicht kennen.

### Schicht 3 – Prävention an der Quelle, Backstop im Melder
* **Prävention:** `content-engine-v2.yml` zieht das Zertifikat direkt nach der
  Veredelungs-/Freigabe-Phase nach (dort steht die komplette Messkette schon).
  Wer Entwürfe anfasst, erneuert ihren Nachweis.
* **Backstop:** `bot-watchdog.yml` heilt beide Befunde im selben Lauf
  (installiert Hugo + hunspell, `reserve_recert.py --fix`, vollwertiger
  Pinterest-Lauf mit Hugo-Build) und **misst danach neu**, bevor geroutet
  wird – ein Ticket für ein bereits gelöstes Problem ist derselbe
  Vertrauensverlust wie ein übersehener Fehler.

### Schicht 4 – Befunde, deren nächster Schritt zur Ursache passt
`bot_watchdog.reserve_finding()` trennt jetzt:

* **„Reserve-Zertifikat veraltet (Heiler-Drift)"** → Nachzertifizieren
  (Sekunden), *nur wenn* der gedriftete Bestand die Alarmschwelle rechnerisch
  trägt,
* **„Content-Reserve niedrig"** → produzieren (`content-reserve.yml`).

Und der Pinterest-Fingerabdruck deckt nur noch den **pin-relevanten**
Quellenstand ab (Frontmatter + Affiliate-Gateways pro Artikel, Layouts,
Pin-Assets, Skripte – Report-Schema 3). Eine Stilpolitur entwertet den
Nachweis nicht mehr; ein neues Pin-Feld oder ein neuer Gateway-Link sehr wohl.

---

## 3. Sofort-Wirkung in diesem Commit

* `PINTEREST-REPORT.md` neu erzeugt (Schema 3, 62 Artikel, 0 Probleme) →
  Befund „Pinterest-Report veraltet" ist **weg** (lokal verifiziert:
  `check_pinterest_report_freshness() == (True, 'Report aktuell zum Quellenstand')`).
* Das Reserve-Zertifikat wurde **bewusst nicht** lokal überschrieben: in der
  Sandbox fehlt `hunspell`, die Sicherung hat korrekt abgebrochen. Die
  Nachzertifizierung läuft mit vollständiger Messkette im nächsten
  Bot-Watchdog- bzw. Content-Engine-Lauf (oder sofort über
  *Actions → Bot-Watchdog → Run workflow*).

## 4. Regressionsschutz

| Test | Nagelt fest |
|---|---|
| `scripts/tests/test_reserve_recert.py` (10) | Drift-Erkennung inkl. Verursacher, „nur Betroffene messen", Altlasten fallen raus, fehlende Messkette blockiert, Massenabwertung mit einem Muster wird gestoppt, echter Qualitätseinbruch bleibt erlaubt |
| `scripts/tests/test_bot_watchdog_routing.py` (+3) | Drift → Nachzertifizierung, echter Engpass → Produktionslinie, Drift ohne tragfähigen Bestand bleibt Produktionsbefund |
| `scripts/tests/test_pinterest_check.py` (+1) | Prosa-Politur entwertet den Report nicht, Pin-Felder und Gateways schon |
| `scripts/reserve_recert.py --selftest` | Sabotageschutz vor jeder Fix-Aktion (im Workflow verdrahtet) |

## 5. Betriebsanleitung

```bash
python3 scripts/reserve_recert.py --check   # Drift melden (Exit 1)
python3 scripts/reserve_recert.py --fix     # Drift nachzertifizieren
python3 scripts/pinterest_check.py --fix    # Pinterest-Report erneuern
```

Exit-Codes von `reserve_recert.py`: `0` sauber · `1` Drift offen ·
`2` Zertifikat fehlt (Volllauf nötig) · `3` Messkette unvollständig,
**nichts geschrieben**.

# Layout-Automatisierung #900 – Dauerheilung auf Agentur-Niveau

**Stand:** 30.10.2026 · **Vorgang:** Meldung
[#900](https://github.com/frank-hartung/franksfinanzcheck-blog/issues/900)
„⚠ Layout-Automatisierung: Probleme gefunden" · **Basis:** `main` @ `57a4361`
· **Beleglauf vor Ort:** Hugo 0.168.0 extended, `hugo --minify`, 380 Seiten

---

## 1. Was die Meldung behauptet hat – und was wahr war

Meldung #900 entstand am 26.10.2026 aus dem Lauf
[40336062251](https://github.com/frank-hartung/franksfinanzcheck-blog/actions/runs/40336062251).
Sie sagte:

> **Statisches Audit:** Exit 1 · **Browser-Audit:** Exit 1
> Statisches Audit: `_Kein Report erzeugt._`
> Browser: `404 http://127.0.0.1:8099/ · kein <title> · kein <h1>`

Davon war **kein einziger Satz ein Layout-Befund**. Der Bau war gestorben
(unquotierter Doppelpunkt im Frontmatter einer Inhaltsdatei), `public/` enthielt
nur Bruchstücke. Drei Instanzen haben das nacheinander falsch erzählt:

1. **Der Workflow** erfand Zahlen: `STATIC_EXIT ?? '1'` machte aus „nicht
   gelaufen" ein „kritische Befunde". → geheilt in WF-9FD5 / #901 (26.10.).
2. **Das statische Audit** war über 0 Seiten **grün** („0 Links kaputt, alle
   OK"). Es prüfte nur, ob das *Verzeichnis* existiert.
3. **Der Browser-Audit** lud die 404-Seite und meldete sie als
   Layout-Katastrophe („kein `<title>`, kein `<h1>`") – eine Fehldiagnose über
   das falsche Objekt. „Kein Chrome" und „kein Bau" teilten sich außerdem den
   Exit-Code 2, den der Workflow als *grün* wertet.

Dazu kamen zwei Dauerstörungen, die den Blick auf echte Befunde verstellten:
77 Alt-Text-Fehlalarme in **jedem** Wochenlauf und eine Meldung, die nach ihrer
Heilung offen blieb.

Die Reparatur vom 29.10.2026 (PR #937) hat `open()`-Leichen beseitigt und den
Zustand dokumentiert – aber keinen der fünf Punkte oben. #900 blieb deshalb
offen, und zwar zu Recht.

---

## 2. Die fünf Ursachen und ihre Heilung

### 2.1 Grün ohne Messung → **rot ohne Bau**

`scripts/layout_audit.py` prüft jetzt **vor** jeder Einzelprüfung, ob
überhaupt etwas zu messen ist: Verzeichnis, Startseite, Mindestumfang
(≥ 20 Seiten, ≥ 1 Artikel). Fehlt etwas, ist das ein **kritischer Befund**
(Exit 1) mit Klartext und Zahlen – und es wird *keine* Einzelprüfung „OK"
gemeldet, die in Wahrheit nichts geprüft hat.

```
$ LAYOUT_BASE_DIR=/tmp/leer python3 scripts/layout_audit.py
## ❌ Kritisch
Messbarkeit: der Bau ist unvollständig – es wurde NICHTS belastbar geprüft.
  - index.html fehlt – der Bau hat keine Startseite.
  - nur 0 HTML-Seiten gefunden (Mindestumfang für eine Messung: 20).
  - keine Artikel-Seite unter posts/ gefunden …
Exit: 1
```

### 2.2 Fehldiagnose im Browser-Audit → **Werkzeugfehler, fail-closed**

`scripts/layout_browser_check.js` hat eine Vorprüfung vor dem Start und
**vier getrennte Exit-Codes**:

| Code | Bedeutung | Wirkung im Workflow |
|---|---|---|
| 0 | grün (ggf. Frühwarnungen) | grün |
| 1 | harte Befunde auf geprüften Seiten | **rot** |
| 2 | weich übersprungen (kein Chrome/kein puppeteer-core) | grün, mit Ansage |
| 3 | **Werkzeugfehler** – kein messbarer Bau, Server nicht startbar | **rot (fail-closed)** |

Vorher gab es kein 3. Ein leerer Bau war entweder „Befund" (falsch) oder
„übersprungen" (grün). Zusätzlich: Der Audit nimmt jetzt einen **freien Port**
(Standard 0) statt fest 8099; eine Portkollision war früher ein Werkzeugfehler
mitten im Lauf.

```
$ LAYOUT_BASE=/tmp/leer node scripts/layout_browser_check.js
Werkzeugfehler: …/index.html fehlt (kein Bau) – der Browser-Audit hat NICHTS
gemessen (Exit 3, fail-closed).                                   → Exit 3

$ LAYOUT_BASE=public node scripts/layout_browser_check.js
CHROME_PATH nicht gesetzt – Browser-Audit übersprungen (Exit 2 …)  → Exit 2
```

### 2.3 77 Alt-Text-Fehlalarme → **Attribut-Scanner statt Regex**

`hugo --minify` schreibt `alt=""` als bloßes `alt`. Das ist gültiges HTML mit
**leerem** Wert – so parst es jeder Browser. Die Prüfung suchte `alt=` und
meldete deshalb 77 dekorative Kartenbilder
(`_partials/extend_post_content.html`: `alt="" aria-hidden="true"`) als „Bild
ohne alt-Attribut".

Neu: `tag_attributes()` liest Attribute wie ein Parser und unterscheidet
**fehlt** von **leer**. Ergebnis am echten Bau:

| | vorher | nachher |
|---|---|---|
| Alt-Text-Warnungen im Report | **77** | **0** |
| geprüfte Bilder im Artikel-Inhalt | (Zahl stand nicht im Report – nur die Befunde) | 266 |

Echte Befunde bleiben echt: fehlendes `alt`, leeres `alt` ohne
`aria-hidden`/`role=presentation`, generische Alt-Texte (`hero-1200`) – alle
drei sind weiter Testfälle.

### 2.4 Alarm ohne Schließpfad → **Push-Lauf auf `main`**

Geheilt wird über einen Pull Request. Der PR-Lauf darf keine Issues pflegen,
der Wochenlauf kommt erst Montag. #900 stand deshalb über den Merge von PR #937
hinaus offen – genau der Dauer-Alarm, den der Workflow abschaffen soll
(Regel #272).

Jetzt löst ein **Merge auf `main`** denselben Audit aus – mit **identischer
Pfadliste** wie der PR-Trigger (per Test erzwungen). Die Auto-Heilung
(committet und pusht) läuft bei `push` **nicht**: kein Selbst-Anstoßen, kein
Schreiben im Namen eines Merges. Damit schließt sich die Meldung dort, wo sie
entsteht.

### 2.5 `open()`-Zusage aus PR #937 war unvollständig

Drei Aufrufe (Covers, Frontmatter, Auto-Fix) lasen weiterhin ohne
`with`-Kontext. Jetzt gilt die Zusage für die ganze Datei – nachprüfbar:
`grep -n "open(" scripts/layout_audit.py | grep -v "with open"` → leer.

---

## 3. Beweise (ausgeführt, nicht behauptet)

| Beweis | Befehl | Ergebnis |
|---|---|---|
| Echter Produktionsbau | `hugo --minify --cleanDestinationDir` | Exit 0 · 113 Seiten, 17 Paginatoren, 2615 statische Dateien |
| Statisches Audit am echten Bau | `python3 scripts/layout_audit.py` | **Exit 0** · 14× OK, **0 Warnungen** |
| Zahlen des Laufs | `LAYOUT-REPORT.md` | 3662 Links (0 kaputt) · 266 Bilder (0 ohne Alt) · 72 Artikel-Schema · 401 hreflang-Seiten · 380 Seiten DOM-vermessen · max. Kinder 50 / Head 50 / Tiefe 14 / 1058 Elemente · 2015 Überschriften im Chunker-Vertrag |
| Leerer Bau | `LAYOUT_BASE_DIR=/tmp/leer python3 scripts/layout_audit.py` | **Exit 1**, Report mit 3 Ursachen (vorher Exit 0) |
| Browser ohne Bau | `LAYOUT_BASE=/tmp/leer node scripts/layout_browser_check.js` | **Exit 3**, Klartext (vorher Befund/grün) |
| Browser ohne Chrome | `LAYOUT_BASE=public node scripts/layout_browser_check.js` | **Exit 2**, Ansage (unverändert weich) |
| Severity-Vertrag | `node scripts/layout_browser_check.js --selftest` | 13 Fälle grün |
| ReDoS-Vertrag | `python3 -m unittest scripts.tests.test_redos_security` | 14 Tests grün; 40 000-Zeichen-Tag in 0,012 s geparst |
| Neue Regressionstests | `python3 -m unittest scripts.tests.test_layout_audit_bau_basis` | **16 Tests grün** |
| Workflow-/Lebenszyklus-Verträge | `python3 -m unittest scripts.tests.test_layout_ai_bauausfall` | **13 Tests grün** (5 neu) |
| Gesamtes Unit-Test-Netz | `python3 -m unittest discover -s scripts/tests` | 4537 Tests, 22 Fehlschläge – **alle außerhalb dieses Vorgangs** (u. a. `alert-on-failure.yml`-Syntax aus #955, package.json-Doppelschlüssel, Content-/Snapshot-Drift); in Bearbeitung: PR #956 |

---

## 4. Geänderte Dateien

| Datei | Änderung |
|---|---|
| `scripts/layout_audit.py` | Messbarkeits-Vorprüfung (rot statt leer-grün), Attribut-Scanner für Alt-Texte, restliche `open()` auf `with` |
| `scripts/layout_browser_check.js` | Vorprüfung + Exit 3, freier Port, klare Trennung „übersprungen" vs. „Werkzeugfehler", Puppeteer erst nach der Vorprüfung |
| `.github/workflows/layout-ai.yml` | `push` auf `main` mit identischer Pfadliste (Schließpfad), Auto-Heilung nur bei `schedule`/`dispatch`, Exit-3-Ansage, keine feste Portnummer |
| `scripts/tests/test_layout_audit_bau_basis.py` | **neu**: 16 Regressionstests (Bau-Basis, Minifier-Attribute, Browser-Vorprüfung – letztere führt das Skript aus) |
| `scripts/tests/test_layout_ai_bauausfall.py` | 5 neue Lebenszyklus-Verträge (Push-Trigger, Pfadgleichheit, kein Schreiben im Push-Lauf, Issue-Pflege, Reihenfolge) |
| `docs/LAYOUT-AUTOMATISIERUNG.md` | Ursachen-Tabelle, Exit-Code-Vertrag, Stand |
| dieser Bericht | Nachweis und Übergabe |

---

## 5. Was bewusst nicht geändert wurde

* **Browser-Audit bleibt weich, wenn Chrome fehlt.** Ein Umgebungsmangel ist
  kein Layout-Befund; das statische DOM-Budget vermisst weiterhin *jede* Seite.
  Der Unterschied ist jetzt nur ehrlich benannt (Exit 2 statt grün-ohne-Ansage).
* **Kein Push-Trigger für Deploy- oder Inhalts-Commits.** Die Pfadliste ist eng
  (Layout, CSS, Audit-Skripte, dieser Workflow). Sonst würde jeder Deploy den
  Audit starten – der Grund, warum der Trigger 2026 bewusst fehlte.
* **Keine Anhebung der DOM-Budgets.** Die Messwerte liegen mit 50/50/14/1058
  deutlich unter Frühwarnung und Lighthouse-Grenze (54/52/28/1100 bzw.
  60/58/32/1400). Ein Budget, das man anhebt, prüft nichts mehr.
* **Fremde Baustellen** (`alert-on-failure.yml`, `package.json`): eigene
  Vorgänge (PR #956), hier nur als Vorzustand benannt – nicht mitgeheilt.

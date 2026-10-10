# Code-Scanning-Alert #83 – „Incomplete URL substring sanitization“ · Dauerheilung auf Agentur-Niveau, 10.10.2026

**Ausgangslage:** Alert #83 (`py/incomplete-url-substring-sanitization` / `js/incomplete-url-substring-sanitization`) stand offen, obwohl genau diese beiden Regeln seit dem 04.10.2026 als „begründete Ausnahme“ in der Unterdrückungs-Whitelist von `.github/workflows/codeql.yml` standen. Das ist die Pointe dieses Falls: **Die Unterdrückung hat den Fund nicht beseitigt, sondern nur die eine von zwei Sichten blind gemacht.** Das parallel laufende GitHub-Default-Setup kennt weder `paths-ignore` noch `# codeql[...]`-Kommentare – es meldete weiter, während das eigene Gate „0 Funde“ sagte. · **Ergebnis:** Alle Fundstellen konstruktiv im Code geheilt (**kein Dismiss, keine Inline-Unterdrückung, keine Ausnahme**), die Whitelist **ersatzlos gestrichen**, und drei neue, voneinander unabhängige Wachen frieren den Zustand ein: eine Host-Wahrheit (`scripts/url_host.py`), eine upload-unabhängige URL-Wache über Python + JavaScript + HTML (`scripts/url_substring_guard.py`, **697 Dateien**) und ein Sicherheitsvertrag mit **14 Tests** (`scripts/tests/test_url_substring_security.py`).

> Dieser Bericht ist der Wahrheitsort für Alert #83. Vorgeschichte: `CODE-SCANNING-HEILUNG-PREMIUM-2026-10-04.md` (Gesamtstrategie), `CODE-SCANNING-ALERT-78-DAUERHEILUNG-PREMIUM-2026-10-05.md` (Diff-Blindheit, Namensvertrag), `CODE-SCANNING-ALERT-80-PREMIUM-2026-10-05.md` (SARIF-unabhängige Klartext-Wache). Was hier steht, gilt bis ein neuer datierter Abschnitt es ablöst.

---

## 1 · Was die Regel wirklich prüft – und warum sie recht hat

Eine URL ist **keine Zeichenkette mit Bedeutung**, sondern eine strukturierte Adresse. Wer sie mit `in`, `startswith`, `endsWith` oder `includes` beurteilt, prüft Text statt Herkunft. Jede dieser Prüfungen hat eine offene Flanke:

| Prüfung im Code | Was der Autor meinte | Was durchkommt |
|---|---|---|
| `"https://franksfinanzcheck.de" in text` | „Link auf unseren Blog“ | `https://franksfinanzcheck.de.angreifer.example/` |
| `"api.pinterest.com" in text` | „Skript spricht mit der Pinterest-API“ | Eine bloße **Erwähnung** in einem Kommentar – und umgekehrt: `https://fake-api.pinterest.com/v5` gilt als echt |
| `origin.endsWith(".pages.dev")` | „Vorschau-Deployment“ | `https://angreifer.example/?x=.pages.dev`, `http://boese.pages.dev` (kein TLS), `https://xyz.pages.dev.angreifer.example` |
| `"example.com" in pfad` | „kein fremder Host im Pfad“ | `https://127.0.0.1/…`, `https://nutzer@angreifer.example/…` |

Die CodeQL-Queries wurden für diese Heilung **im Original gelesen**, nicht aus dem Gedächtnis nachgebaut (`github/codeql`, Pfade `python/ql/src/Security/CWE-020/` und `javascript/ql/src/Security/CWE-020/`). Kern der Python-Query:

```
looksLikeUrl(StringLiteral s):
    text.regexpMatch("(?i)([a-z]*:?//)?\\.?([a-z0-9-]+\\.)+(com|org|edu|gov|uk|net|io)(:[0-9]+)?/?")
 or text.regexpMatch("(?i)https?://([a-z0-9-]+\\.)+([a-z]+)(:[0-9]+)?/?")

incomplete_sanitization: looksLikeUrl(url) und
    Compare mit `In`  |  x.startswith(url)  |  x.endswith(url)   (mit zwei Ausnahme-Regexen)
```

Zwei Details, die in der Praxis über falsche Sicherheit entscheiden und deshalb hier festgehalten sind:

1. **`regexpMatch` ist voll-ankernd.** Nur das ganze Literal zählt, nicht ein Teil davon.
2. **`getACommonTld()` kennt nur `com|org|edu|gov|uk|net|io`.** Ein `.de`-Host ist für die erste Regel **kein** Treffer – `"franksfinanzcheck.de"` allein löst nichts aus, `"https://franksfinanzcheck.de"` sehr wohl (zweite Regel). Wer das nicht weiß, baut Positivproben, die nie anschlagen, und hält seine Wache für scharf.

---

## 2 · Warum der Alert trotz „grünem“ Gate offen blieb

### Ursache A – die Unterdrückungs-Whitelist (die eigentliche Wurzel)

In `.github/workflows/codeql.yml` filterte ein Schritt vor Upload **und** Gate alle Ergebnisse heraus, die eine `suppressions`-Angabe trugen und auf dieser Liste standen:

```bash
ERLAUBT='py/incomplete-url-substring-sanitization
js/incomplete-url-substring-sanitization'
```

Das ist eine Wache, die sich selbst die Augen zuhält. Drei Konsequenzen, alle eingetreten:

* **Zwei Sichten, ein Repository.** Die Security-Tab wird vom Default-Setup gespeist. Es wertet `# codeql[...]`-Kommentare **nicht** als Unterdrückung und hielt den Alert offen – sichtbar für jeden Besucher der Security-Tab, unsichtbar für das Gate.
* **Unbegrenzte Laufzeit.** Eine Whitelist hat kein Ablaufdatum. Aus „wir heilen das nächste Woche“ wird ein Dauerzustand, den niemand mehr in Frage stellt.
* **Kollateraler Blindflug.** CodeQL wertet ein **nacktes** `# noqa` oder `# lgtm` als Unterdrückung **jedes** Alerts dieser Zeile. Die Whitelist hätte solche Funde mitentsorgt, sobald jemand ein `# noqa` setzt.

**Heilung:** Die Whitelist ist gestrichen. Der Schritt heißt jetzt **„Unterdrückungen sind selbst ein Befund (Upload & Gate)“** und filtert nichts mehr: Jedes SARIF-Ergebnis mit `suppressions` erzeugt eine `::error`-Annotation an der Codezeile und lässt den Job scheitern.

**Vorprüfung, damit diese Verschärfung nicht blind zuschlägt** – die Suppression-Logik stammt aus `python/ql/src/AlertSuppression.ql`, Regex `(?i)\s*noqa\s*([^:].*)?`. Ein qualifiziertes `# noqa: E731` ist also **keine** CodeQL-Unterdrückung, ein nacktes `# noqa` schon. Repository-Stand heute: **0** nackte `# noqa`, **0** `# lgtm`, **0** verbliebene `# codeql[...]`-Unterdrückungen. Die harte Sperre kann also niemanden überraschen, der sauber arbeitet.

### Ursache B – die Fundstellen waren echt, nicht „false positive“

Alle drei Python-Fundstellen hielten der Prüfung stand: Jede war eine Zeichenketten-Prüfung auf einer Adresse, jede hatte eine benennbare Umgehung (Tabelle in Abschnitt 1). Es gab nichts zu rechtfertigen – nur zu heilen.

### Ursache C – eine Fundstelle war für jede Analyse unsichtbar

`scripts/tests/test_offline_import.py` war seit `ac903015` **syntaktisch kaputt** (unparsebar). Damit war die darin schlummernde Prüfung `"example.com" in p` für jede AST-basierte Wache **und für CodeQLs Extraktor** schlicht nicht vorhanden. Sie tauchte erst auf, als die Datei im Zuge dieser Lieferung repariert wurde – und wurde im selben Lauf von der neuen Wache gemeldet. Genau dafür ist Fail-closed da: **Eine Datei, die nicht gelesen werden kann, ist nicht „sauber“, sondern unbekannt.** (Siehe Abschnitt 5, Probe `test_nicht_analysierbarer_code_ist_fail_closed`.)

---

## 3 · Die Fundstellen – Befund, Ursache, Heilung

### A · `scripts/affiliate_marketer.py` (Selbsttest der Gateway-Normalisierung)

```python
# vorher
if n3 != 1 or "https://franksfinanzcheck.de" in t3 \
# nachher (Zeile 336)
if n3 != 1 or hat_link_auf_host(t3, BLOG_HOST, mit_subdomains=True) \
```

Der Selbsttest sichert zu, dass absolute Blog-Links zu relativen `/go/`-Gateways normalisiert werden (nur relative Gateways bekommen `rel="sponsored"`). Die Teilstring-Suche hätte `https://franksfinanzcheck.de.angreifer.example/go/strom/` als „eigener Blog“ durchgewinkt. Jetzt werden die Links des Textes ausgelesen und ihr **Host** verglichen – inklusive Subdomain-Grenze. Der eigene Host steht einmal als `BLOG_HOST` im Modul, statt dreimal als Literal.

### B · `scripts/governance_contract.py`, Regel C10 (Token-Broker-Pflicht)

```python
# vorher (zweimal, mit Inline-Unterdrückung)
if "api.pinterest.com" in text and not ...
# nachher (Zeile 691)
spricht_mit_api = ruft_host_an(text, PINTEREST_API_HOST)
```

Hier war die Zeichenketten-Prüfung **doppelt falsch**: zu lasch (jeder Host, der die Zeichenkette enthält) und zu streng (jede Erwähnung in Kommentar, Dokumentation oder Fixture machte ein Skript zum „API-Verbraucher ohne Token-Broker“). Die Regel lärmte, und Lärm erzieht zum Wegsehen. `ruft_host_an()` wertet den Quelltext per **AST** aus und urteilt nur über echte URL-**Literale** – Prosa zählt nicht, `https://fake-api.pinterest.com/v5` zählt nicht, `https://api.pinterest.com/v5/pins` zählt.

Verworfene Alternativen, bewusst dokumentiert: (a) `TOKEN_BROKER_EXEMPT` erweitern – das wäre eine Ausnahme statt einer Heilung; (b) eine Transport-Marker-Regex (`requests.`, `urlopen`, …) – sie traf `url_host.py` selbst und hätte die nächste Lärmquelle geschaffen.

### C · `scripts/tests/test_offline_import.py` (Datenschutz-Zusicherung)

```python
# vorher
self.assertNotIn("/", pfade[0])                      # wirkungslos: Pfade BEGINNEN mit "/"
self.assertFalse(any("example.com" in p for p in pfade))
# nachher (Zeile 166)
verseucht = [p for p in pfade if "@" in p or IPV4.match(p.strip("/"))]
self.assertEqual(verseucht, [])
```

Von den zwei Zusicherungen war eine wirkungslos und eine unvollständig: Sie prüfte auf **einen** Beispielhost statt auf die **Eigenschaft** „hier steht ein Host oder eine Kennung, wo ein Pfad stehen muss“. Jetzt wird die Eigenschaft geprüft (Benutzer-Kennung via `@`, IPv4-Adresse) – und die Zusicherung nennt im Fehlerfall den konkreten Übeltäter.

### D · `cloudflare/ki-assistent/worker.js` – dieselbe Fehlerklasse, die keine Query meldet

Der Worker entschied seine **CORS-Freigabe** über `origin.endsWith(".pages.dev")` – die gefährlichste der vier Stellen, weil hier eine **Sicherheitsentscheidung zur Laufzeit** daran hängt.

**Wichtige Präzisierung, damit niemand sich auf das Werkzeug verlässt:** CodeQL meldet dieses Muster **nicht** – und diese Wache ebenfalls nicht. Die JS-Query nimmt `EndsWith`-Ziele aus, die wie ein Domain-Suffix aussehen (`"(?i)\\.([a-z0-9-]+)(\\.[a-z0-9-]+)+"`), weil Suffix-Prüfungen auf Hostnamen meistens legitim sind. Hier war die Prüfung aber nicht auf einem **Hostnamen**, sondern auf der **ganzen Herkunftszeichenkette** – und damit falsch. Genau für solche Fälle gibt es Regel **KA10**: Eine semantische Hausregel schlägt dort zu, wo eine generische Query bewusst schweigt. Wer nur auf grüne Scanner wartet, findet diese Klasse nie.

```js
const VORSCHAU_HOSTS = ["pages.dev", "e2b.app"];

function vorschauHost(origin) {
  let url;
  try { url = new URL(String(origin)); } catch { return false; }   // keine gültige Herkunft → keine Freigabe
  if (url.protocol !== "https:") return false;
  const host = url.hostname.toLowerCase();
  return VORSCHAU_HOSTS.some((basis) => host.endsWith("." + basis));
}

const isAllowed = allowed.includes(origin) || vorschauHost(origin);
```

Bewusste Verhaltensänderungen: `http://…pages.dev` ist **nicht mehr** erlaubt (eine Vorschau ohne TLS ist keine vertrauenswürdige Herkunft), und der Apex `pages.dev` selbst ebenfalls nicht (er gehört nicht uns). Die Produktions-Herkunft wird weiterhin **exakt** verglichen (`Array.includes`), `Vary: Origin` bleibt gesetzt.

---

## 4 · Die Wachen – drei Schichten, die sich nicht gegenseitig stützen

### Schicht 1 · `scripts/url_host.py` (342 Zeilen) – eine einzige Host-Wahrheit

Keine Wache und kein Produktionsskript baut mehr eigene Host-Logik. Das Modul kapselt sie:

| Funktion | Zusage |
|---|---|
| `host_von(url)` | Host einer URL, kleingeschrieben, ohne Port/Benutzer |
| `ist_host(url, host)` | exakte Gleichheit |
| `ist_host_oder_subdomain(url, basis)` | Punkt-Grenze, nie Zeichenketten-Ende |
| `nennt_host(text, host)` | nur echte Links im Text, keine Prosa |
| `ruft_host_an(quelltext, host)` | **AST**: nur URL-Literale im Code, keine Kommentare |
| `absolute_links(text)` / `hat_link_auf_host(…)` | Linkauslese für Markdown + HTML |

`python3 scripts/url_host.py --selftest` → **42 Proben** (Host-Exaktheit, Subdomain-Grenze, Namensgrenze, Linkauslese), darunter die Umgehungen aus Abschnitt 1.

### Schicht 2 · `scripts/url_substring_guard.py` (1 039 Zeilen) – die upload-unabhängige Wache

Sie ist **nicht** von CodeQL, vom SARIF-Upload oder von der Alert-API abhängig – die Lehre aus #78/#80, hier zum dritten Mal bestätigt:

* **Python** über `ast` (Vergleiche, `startswith`/`endswith`, auch Tupel-Argumente) plus `tokenize` für Unterdrückungskommentare.
* **JavaScript und TypeScript** über einen **echten Lexer** (nicht Regex): `.includes/.startsWith/.endsWith/.indexOf/.lastIndexOf/.search`, dazu die `slice`/`substring`/`substr`-Idiome beidseitig. Reine Textsuche hätte an Kommentaren, Template-Strings und Regex-Literalen versagt. `.ts/.tsx/.mts/.cts` sind mit drin, weil CodeQLs JS-Extraktor sie ebenfalls liest.
* **HTML** mit eingebetteten `<script>`-Blöcken; Hugo- und HTML-Kommentare werden vorher positionstreu neutralisiert.
* **Fail-closed:** Nicht lexbarer Quelltext ist ein **Fehler** (Exit 2), kein „sauber“. Ausnahme nur für `*.min.js`/`*.umd.js`.
* **Bewusst schärfer als CodeQL:** `not in` zählt mit, `.de`-Hosts zählen mit, `indexOf`-Idiome ohne Vergleichskontext zählen mit – **und jede Unterdrückung ist selbst ein Befund.**
* **Scope-Lücken sind ein Fehler, kein „grün“.** Taucht eine Endung auf, die CodeQL liest und diese Wache (noch) nicht – `.vue`, `.hbs`, `.ejs`, `.njk`, `.svelte`, `.astro` –, meldet `scopeluecken()` sie und der Lauf endet mit Exit 2. Der erste Vue-Baustein erzwingt damit die Erweiterung der Wache, statt still an ihr vorbeizulaufen.

`--selftest` → **20 Positivproben, 16 Gegenproben, 23 Musterproben, 2 Fail-closed-Proben, 2 Scope-Proben.** Repository-Lauf → **697 Dateien, 0 Funde, Exit 0.** Schnittstelle: `--json`, `--quiet`, Exit 0/1/2.

### Schicht 3 · `scripts/ki_assistent_gate.py`, Regel **KA10** – „CORS-Freigabe host-genau“

Die Wache aus Schicht 2 sieht den Worker (er liegt im Scope), aber KA10 sichert zusätzlich die **positive** Zusage, die keine Textsuche leisten kann: Der Worker muss die Herkunft **parsen**.

```python
CORS_ZEICHENKETTE = re.compile(
    r"origin[^;\n]{0,40}\.\s*(endsWith|startsWith|includes|indexOf|search|match)\s*\(",
    re.IGNORECASE)
# geprüft wird der KOMMENTARFREIE Token-Strom; zusätzlich Pflicht:
#   re.search(r"new\s+URL\s*\(", code) und "vorschauHost" in code
```

Geprüft wird auf dem **kommentarfreien** Token-Strom (über den Lexer aus Schicht 2) – sonst würde die Begründung der Heilung, die die kranke Zeile zitiert, die eigene Regel auslösen. `--selftest` baut dafür einen sabotierten Worker in einem Temporärverzeichnis (die echte Datei wird nie angefasst) **und** prüft gegen, dass der echte Worker passiert.

---

## 5 · Der Dauerschutz: `scripts/tests/test_url_substring_security.py` (17 Tests)

Fünf Ebenen, damit kein einzelner Rückschritt unbemerkt bleibt:

| Klasse | Was eingefroren wird |
|---|---|
| `WacheIstScharf` (5) | Eigenprüfung beider Module; **Rückfall-Probe**: die zwei historischen Fundstellen werden wortgleich in ein Temporärverzeichnis geschrieben und müssen gemeldet werden („Hätte diese Wache Alert #83 gefunden?“); Unterdrückungskommentar = Befund; kaputter Code = Exit 2 |
| `ScopeHatKeineBlindenFlecken` (3) | TypeScript wird wirklich gelesen; eine `.vue`-Datei wird als Scope-Lücke gemeldet; das Repository hat heute keine ungelesene Endung |
| `BestandIstFrei` (1) | Repository-Lauf: 0 Funde, **0 Analysefehler**, Exit 0, Mindest-Dateizahl (damit niemand die Wache durch eine geschrumpfte Dateiauswahl „grün“ macht) |
| `HeilungBleibtBestehen` (3) | Die geheilten Zeilen A/B inhaltlich; die Umgehungstabelle aus Abschnitt 1 als ausführbare Zusicherung |
| `BetriebsvertragCI` (3) | `ERLAUBT=` darf **nicht** zurückkommen; der Job `url-wache` muss die vier Prüfbefehle enthalten; beide Regeln bleiben security-relevant |
| `WorkerHerkunftIstHostGenau` (2) | Worker parst die Herkunft; KA10 existiert und ist scharf |

Zwei Tests prüfen bewusst den **kommentarfreien** Quelltext (`tokenize` für Python, der JS-Lexer für den Worker): Die Begründung einer Heilung zitiert die kranke Zeile – ein Kommentar darf einen Vertragstest weder bestehen lassen noch brechen.

Dazu `cloudflare/ki-assistent/test/worker.test.mjs` (**7 Tests**, `node --test`): exakte Produktions-Herkunft, `Vary: Origin`, echte Vorschau-Subdomains, **sechs Umgehungsversuche** (`?x=.pages.dev`, Pfad-Anhang, `boesepages.dev`, `pages.dev.angreifer.example`, `…pages.dev@angreifer.example`, `http://`), Rückfall-Origin für fremde/leere Herkünfte, mehrfaches `ALLOWED_ORIGIN`.

---

## 6 · Verankerung im Betrieb

**CI** – `.github/workflows/codeql.yml`, neuer Job `url-wache` (Vorbild: `klartext-wache` aus #80), bewusst **ohne** Abhängigkeit vom SARIF-Upload:

```yaml
- run: python3 scripts/url_host.py --selftest
       python3 scripts/url_substring_guard.py --selftest
- run: python3 scripts/url_substring_guard.py
- run: python3 -m unittest scripts.tests.test_url_substring_security -v
- run: python3 scripts/ki_assistent_gate.py --selftest
       node --test cloudflare/ki-assistent/test/worker.test.mjs
```

**Lokal** – neue npm-Skripte, damit niemand erst in der CI erfährt, was er gebaut hat:

| Skript | Zweck |
|---|---|
| `npm run url:wache` | Repository prüfen |
| `npm run url:wache:json` | maschinenlesbarer Bericht |
| `npm run url:wache:check` | nur die Eigenprüfungen |
| `npm run test:urlwache` | Eigenprüfung + Bestand + Vertrag (14 Tests) |
| `npm run test:ki` | **erweitert** um `node --test cloudflare/ki-assistent/test/worker.test.mjs` |

**Selbsttest-Runner** – `python3 scripts/selftest_runner.py` findet die beiden neuen `--selftest`-Flags automatisch: **184 Wachen** (vorher 155), jede zusätzlich unter einer um 97 und 1 461 Tage vorgestellten Uhr.

---

## 7 · Verifikation (vollständige Matrix, alles am 10.10.2026 gelaufen)

| Prüfung | Ergebnis |
|---|---|
| `python3 scripts/url_host.py --selftest` | ✅ 42 Proben |
| `python3 scripts/url_substring_guard.py --selftest` | ✅ 20 / 16 / 23 / 2 / 2 Proben |
| `python3 scripts/url_substring_guard.py` (Repository) | ✅ **697 Dateien, 0 Funde, Exit 0** |
| `python3 -m unittest scripts.tests.test_url_substring_security` | ✅ **17 Tests** |
| `node --test cloudflare/ki-assistent/test/worker.test.mjs` | ✅ **7/7** |
| `python3 scripts/ki_assistent_gate.py --selftest` | ✅ 4 Sabotage-Proben + Gegenprobe |
| `python3 scripts/ki_assistent_gate.py` | ✅ 9 bereit, 1 Warnung (KA1, vorbestehend), **0 defekt** |
| `python3 -m unittest scripts.tests.test_offline_import` | ✅ 15 Tests (Datei war upstream kaputt) |
| `python3 scripts/governance_contract.py --selftest` / `--quick` | ✅ C1–C35 / 33 Regeln |
| `python3 scripts/clear_text_logging_guard.py --selftest` + Lauf | ✅ 438 Dateien, 0 Funde (#78/#80 unberührt) |
| `python3 -m unittest scripts.tests.test_clear_text_logging_security` | ✅ 11 Tests |
| `python3 -m unittest scripts.tests.test_zugangs_namensvertrag` | ✅ 21 Tests |
| `npm run test:mess` | ✅ 63 Tests |
| `python3 scripts/selftest_runner.py` | ✅ **184 Wachen, 368 Uhr-Proben** |
| `python3 scripts/integrity_guard.py --gate` | ✅ 49 Kerndateien signiert (Lock mitgezeichnet) |
| `python3 scripts/actions_version_guard.py --gate` | ✅ keine Action-Versions-Drift |
| `python3 scripts/artefakt_waechter.py` | ✅ 391 Artefakte strukturell heil |
| **CI auf dem PR** | ✅ `URL-Wache`, `Klartext-Wache`, `Integritäts-Siegel`, `Regelwerk`, `gate`, `regression`, `CodeQL (python)`, `CodeQL (javascript)` |
| Repository-Grep | ✅ 0 `# noqa` nackt, 0 `# lgtm`, 0 `# codeql[...]` |


### Der Beweis auf `main` – der Zweig, den die Security-Tab zeigt (Lauf `38079000771`)

Nach dem Merge von PR #696 (Squash `0a37cdc3`) lief die Analyse auf `main`:

```
CodeQL (python):     success   ·  python.sarif:     0 Funde (0 unterdrückt), 43 Regeln
CodeQL (javascript): success   ·  javascript.sarif: 0 Funde (0 unterdrückt), 87 Regeln
URL-Wache:           success   ·  Eigenprüfung · Bestand · Vertrag · CORS-Vertrag
Klartext-Wache:      success
```

**Zwei Dinge wurden damit zugleich grün.** Die beiden `main`-Läufe davor (`ac903015` um 17:57, `ab47c76a` um 16:21) waren **rot** – und zwar nicht an CodeQL, sondern an der **Klartext-Wache mit Exit 2**: Deren Fail-closed-Regel schlug an, weil `scripts/tests/test_offline_import.py` seit `ac903015` nicht parsebar war. Dieselbe kaputte Datei, die Fundstelle C vor jeder Analyse versteckt hat, hielt also auch die Wache aus Alert #78/#80 in Dauerrot. Mit ihrer Reparatur ist beides erledigt – ein Beleg dafür, dass „unlesbar“ nie als „sauber“ durchgehen darf.

### Der Beweis aus der echten Analyse (PR #696, Lauf `38077159639`)

Die entscheidende Zahl steht nicht in einem lokalen Skript, sondern in der SARIF der GitHub-Analyse — **ohne jede Whitelist**:

```
sarif-results/python.sarif:     0 Funde (0 unterdrückt), 43 Regeln mit Metadaten
sarif-results/javascript.sarif: 0 Funde (0 unterdrückt), 87 Regeln mit Metadaten
```

Beide Klammern zählen: **0 Funde** heißt, die Klasse ist weg; **0 unterdrückt** heißt, sie ist nicht versteckt. Vorher war die erste Zahl nur deshalb klein, weil die zweite ungeprüft blieb.

Der Weg dorthin war instruktiv: Der **erste** Lauf ohne Whitelist meldete `1 Security-Fundstelle` — `py/bad-tag-filter` in der URL-Wache selbst (Abschnitt 8, Punkt 4). Geheilt, erneut analysiert, seitdem 0. Ein Gate, das beim ersten scharfen Lauf nichts findet, hat meistens nur nicht hingesehen.

---

## 8 · Nebenbefunde, die bei dieser Arbeit anfielen

1. **`scripts/tests/test_offline_import.py` war seit `ac903015` unparsebar.** Repariert statt per Ausschlussliste umgangen – sonst wäre Fundstelle C für immer unsichtbar geblieben. Lehre: Eine Wache, die unlesbare Dateien überspringt, erzeugt genau die blinden Flecken, gegen die sie antritt.
2. **Regel C10 war erwähnungsbasiert** und produzierte Falschmeldungen (jede Doku-Nennung machte ein Skript zum API-Verbraucher). Mit `ruft_host_an()` urteilt sie jetzt über den AST. Nebeneffekt: weniger Lärm, mehr Autorität.
3. **Die URL-Wache löste anfangs sich selbst aus** – ihre Musterprobe enthielt einen echten Partnerhost und verstieß damit gegen C10. Jetzt steht dort `https://api.beispiel.com/v5/pins`. Lehre: Proben gehören auf Beispiel-Hosts.
4. **Die Wache hat sich selbst einen Fund eingebrockt – und ihn bestanden.** Der erste CodeQL-Lauf ohne Whitelist meldete `py/bad-tag-filter` in `scripts/url_substring_guard.py:602`: Das Endtag-Muster `</script\s*>` übersieht, was Browser sehr wohl als Ende lesen (`</script foo="bar">`, `</script\t\n bar>`, `</script/>`). Für die Wache wäre das ein **Fail-open** gewesen – ein nicht beendeter Skriptblock, in dem sie den Code nicht mehr findet. Geheilt zu `</script\b[^>]*>` (ein `\b` hält `</scriptfoo>` weiterhin draußen), vier Endtag-Varianten als Probe eingefroren. **Das ist der Beweis, dass die Abschaffung der Whitelist wirkt:** Der Fund war eine Zeile in dem Werkzeug, das Funde verhindern soll – mit Whitelist-Denken wäre genau hier die Versuchung zum Unterdrücken am größten gewesen.
5. **`scripts/revenue_funnel.py` hatte eine Zeitbombe** (`_month_age("2030-01")` als „Zukunfts-Monat“): Unter der 1 461-Tage-Uhrprobe des Runners war das ein **Vergangenheits**-Monat, der Selbsttest ging datumsabhängig rot. Auf dem Basis-Commit `b38fe54` reproduzierbar, also **vorbestehend** – mitgeheilt (relative Fixture, 10 Jahre voraus), weil eine rote Wache in der Lieferung niemandem nützt.

---

## 9 · Runbook für den nächsten Fund dieser Klasse

1. **Nie unterdrücken.** Eine Unterdrückung wirkt höchstens in einer von zwei Sichten und hat kein Ablaufdatum. Seit heute bricht sie den Lauf.
2. **URL parsen, Host vergleichen** – `scripts/url_host.py` benutzen, keine eigene Logik bauen.
3. **Subdomain?** `ist_host_oder_subdomain()` (Punkt-Grenze), niemals `endsWith`.
4. **Prüft der Code Quelltext?** `ruft_host_an()` statt `in` – Erwähnung ≠ Aufruf.
5. **Eigenschaft prüfen, nicht Beispiel.** „Enthält dieser Pfad einen Host?“ schlägt „Enthält dieser Pfad `example.com`?“.
6. **Danach:** `npm run test:urlwache` (lokal) – und die Rückfall-Probe im Sicherheitsvertrag um das neue Muster ergänzen.

---

## 10 · Offene Betreiber-Handlung (unverändert aus #78/#80, nur per Klick möglich)

Solange das **GitHub-Default-Setup** aktiv ist, speist es die Security-Tab und lehnt das SARIF der eigenen Wache ab. Genau diese Doppelsicht hat Alert #83 erzeugt.

1. **Settings → Advanced Security → Code Security → CodeQL analysis → Disable CodeQL** (die Seite hieß früher „Code security and analysis“).
2. **Security → Code scanning → Tool status/Affected branches → `main`** – stale Konfiguration des Default-Setups löschen.

Bis dahin ist das **Gate des jeweiligen Laufs** maßgeblich, ergänzt um die drei upload-unabhängigen Wachen (`klartext-wache`, `url-wache`, `ki-assistent`). Diese laufen unabhängig davon, ob die Security-Tab jemals wieder die richtigen Zahlen zeigt – das ist der eigentliche Sinn dieser Architektur.

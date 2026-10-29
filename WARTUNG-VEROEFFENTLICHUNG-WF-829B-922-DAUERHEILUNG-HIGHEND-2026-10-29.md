# Wartung · Veröffentlichung · Vorgang WF-829B (#922) — Highend-Dauerheilung

**Auftrag:** `Wartung · Veröffentlichung · Vorgang WF-829B #922 Bitte dauerhaft auf Highend-Level einer Profi-Agentur beheben.`
**Datum:** 29.10.2026 · **Branch:** `arena/0dc8309e-franksfinanzcheck-blog` · **Basis:** `2e4c7ae`, zusammengeführt mit `main` @ `76efccb` (enthält den Environment-Policy-Gate aus #935)
**Workflow:** `.github/workflows/worker-deploy.yml` („Cloudflare-Worker deployen“)
**Meldung:** [Issue #922](https://github.com/frank-hartung/franksfinanzcheck-blog/issues/922) · Vorgangscode `WF-829B`

---

## 1. Forensischer Ist-Befund

### 1.1 Was gemessen wurde (nicht zitiert, sondern abgefragt)

Der gemeldete Lauf ist [`40569123622`](https://github.com/frank-hartung/franksfinanzcheck-blog/actions/runs/40569123622)
(Push `0b6a1a27` auf `main`, 27.10.2026 19:26:24 UTC). Die Job- und Checks-API nennt
für **beide** Deploy-Jobs dasselbe Bild — und es ist kein Zufall, sondern eine
Zeitangabe:

| Job | Schritt 5 | Schritt 6 (rot) | Dauer Schritt 6 |
|---|---|---|---|
| `Deploy newsletter-worker` (122418462813) | Worker-Tests ✅ | Produktive Ressource auflösen ❌ | 19:26:56 → 19:26:56 (**< 1 s**) |
| `Deploy klick-zaehler` (122418462861) | Worker-Tests ✅ | Produktive Ressource auflösen ❌ | 19:26:56 → 19:26:56 (**< 1 s**) |

Die Annotationen des roten Schritts (Checks-API, wörtlich):

```text
newsletter-worker: Produktionsressource nicht eindeutig aufgelöst – Deploy bleibt
fail-closed. CF_WORKERS_DEPLOY_TOKEN fehlt im Environment cloudflare-produktion;
die bestehende Worker-Bindung kann nicht gelesen werden.

klick-zaehler: Produktionsressource nicht eindeutig aufgelöst – Deploy bleibt
fail-closed. CF_WORKERS_DEPLOY_TOKEN fehlt im Environment cloudflare-produktion;
die bestehende Worker-Bindung kann nicht gelesen werden.
```

Der Lauf brach also **vor** Wrangler ab, in unter einer Sekunde, ohne Netzverkehr:
`worker_ressourcen._token_und_konto()` prüft zuerst den Token, findet ihn leer und
wirft. **Das ist gewollt** (fail-closed; der stille Nicht-Deploy vom 24.10.2026 ist
der Gegenbeweis) — und es ist trotzdem nicht in Ordnung, wie es aussieht.

### 1.2 Drei Defekte hinter einer richtigen Entscheidung

Fail-closed war die richtige Entscheidung. Zu heilen war die **Form** und der
**Ort** der Auskunft:

**U1 — Kurzschluss-Diagnose: ein Feld pro Freigabe-Runde.**
`worker_ressourcen.py` bricht beim **ersten** fehlenden Baustein ab. Das ist für
einen Deploy richtig (ohne Token gibt es nichts zu tun), für einen Menschen vor
dem Dashboard falsch: Der Token wird hinterlegt, der nächste Lauf ist rot, weil
die Konto-ID fehlt, dann das Leserecht, dann die Bindung. Jedes Feld kostet eine
eigene Environment-Freigabe (Required reviewer) — für eine Frage, die in **einem**
Netzaufruf beantwortbar ist. Der Beweis, dass dieser Zustand real war, ist der
Befund selbst: Die Annotation nennt genau **ein** Feld, obwohl niemand weiß, ob
`CLOUDFLARE_ACCOUNT_ID` überhaupt existiert — die Prüfung erreicht die Zeile nie.

**U2 — Der Zugang war nur über den Fehler prüfbar.**
Im Repository existierte bis heute kein Weg, den produktiven Deploy-Zugang zu
prüfen, ohne einen Deploy zu wagen. Die Sicherheits-Wache prüft den *Worker*
(Header, Betriebsbild, `/healthz`), aber nicht den *Deploy-Zugang*; der
Deploy-Workflow wird von `paths`-Filtern ausgelöst, nicht von einer Frage. Wer
„fehlt der Zugang noch?“ wissen wollte, musste einen Deploy-Anlauf und eine
Environment-Freigabe verbrauchen — und bekam dann U1 zu sehen.

**U3 — Der Meldeweg hätte sich beim Umzug verloren (vor dem Ausliefern entdeckt).**
Das Fehler-Alerting erkennt den Zugangsbefund bis heute **am Schrittnamen**
`Produktive Ressource auflösen` (`workerZugangFailed` in
`.github/workflows/alert-on-failure.yml`). Eine Vorprüfung *vor* diesem Schritt
hätte den roten Lauf in die Klasse `worker-deploy` („Deploy-Fehler, Live-Nachweis“)
verschoben — also genau den Befund von #922 ohne seinen Rat geliefert. Diese
Kopplung ist im Neubau mitgewandert und zusätzlich durch drei
Verhaltens-Simulationen geprüft (Abschnitt 3.5).

**Was ausdrücklich NICHT die Ursache ist:** ein Code-Fehler im Resolver, ein
abgelaufener Token, ein Fehler im Workflow oder ein Cloudflare-Ausfall. Der Zugang
selbst fehlt. Diese Heilung kann ihn nicht erzeugen — sie kann nur dafür sorgen,
dass er in **einem** Schritt vollständig, präzise und ohne Deploy-Versuch
behebbar ist, und dass die Lücke nicht wieder unsichtbar wird.

---

## 2. Was in dieser Umgebung möglich ist — und was nicht

Hier existiert **kein** produktiver Cloudflare-Zugang, kein Environment-Secret
und kein Dashboard. Eine Änderung an `cloudflare-produktion` ist von hier aus
nicht möglich; sie ist eine Inhaber-Aufgabe (Runbook A4). Ein „grüner“ Behelf —
etwa den Deploy-Job überspringen, die Matrix leeren oder den Befund zu einer
Warnung herabstufen — wäre eine Fälschung des Nachweises und würde genau den
Vorfall vom 24.10.2026 wiederholen.

**Vorgang #922 bleibt deshalb offen.** Diese Stufe behauptet kein Grün; siehe
Abschnitt 5 für den Abschlussvertrag.

---

## 3. Dauerhafte technische Heilung

### 3.1 H-A · `scripts/worker_zugang.py` — Sammelbefund statt Kurzschluss

Ein neues, rein lesendes Werkzeug mit **einer** Aufgabe: den Deploy-Zugang
vollständig beschreiben, ohne ihn zu benutzen.

| Zusage | Umsetzung |
|---|---|
| **Sammeln statt kurzschließen** | `pruefen()` erhebt *alle* Befunde und bricht nirgends ab: Token vorhanden? Konto-ID vorhanden und 32-Hex? Token aktiv (`GET /user/tokens/verify`)? Leserecht (`Workers Scripts: Read`)? Worker vorhanden (404)? Bindung `ABO` / `DB` eindeutig? Netz/429/5xx? |
| **Klassen statt Fließtext** | `OK`, `FEHLT`, `FORMAT`, `UNGUELTIG`, `RECHT`, `UNBEKANNT`, `BINDUNG`, `NETZ`, `OFFEN` — jede mit **einer** festen Maßnahme. Aus einer Klasse wird ein Rat, nicht aus einer Vermutung. |
| **`OFFEN` ist kein Beleg** | Ist der Token nicht da, sind Token-Gültigkeit und Bindungen *nicht prüfbar*. Das steht dann auch so da — nicht als „in Ordnung“. `urteil()` wertet `OFFEN` niemals als grün. |
| **Keine Werte im Text** | Befunde entstehen aus festen Vorlagen (nur Klassennamen und HTTP-Status werden eingesetzt); zusätzlich maskiert `_maskiere()` Token, Konto-ID und Ressourcen-IDs vor jeder Ausgabe — Log, `--json`, Dossier, Annotation. |
| **Nur zwei Endpunktformen** | `GET /client/v4/user/tokens/verify` und `GET /client/v4/accounts/<konto>/workers/scripts/<worker>/settings`. Kein Wrangler, kein Anlegen, kein Ändern, kein Löschen, keine Weiterleitung (Bearer wird nie weitergereicht). |
| **Vorrang der Repository-Variable** | Ist `KV_NAMESPACE_ID_ABO` / `D1_DATABASE_ID` gültig gesetzt, ist die Bindung dieses Workers keine Voraussetzung — exakt die Reihenfolge von `worker_ressourcen.py`. Eine *ungültige* Variable wird gemeldet und **nicht** durch eine geratene Ressource ersetzt. |

CLI: `--pruefen [--worker X] [--md PFAD|-] [--json] [--selftest]`.
Exit `0` = alle Voraussetzungen belegt, `1` = Befund (fail-closed), `2` =
Werkzeugfehler (nie als Zugangsbefund ausgegeben). Der Selbsttest prüft zehn
Sabotagefälle offline, ohne Netz.

### 3.2 H-B · Der Deploy prüft sich selbst — bevor er es versucht

In `.github/workflows/worker-deploy.yml` steht die Prüfung **vor** der Auflösung:

```yaml
- name: Selbsttest Deploy-Zugang (ohne Netz)            # Code-Regression ≠ Zugang
- name: Zugang prüfen (alle Befunde auf einmal, lesend) # Dossier + je Befund 1 Annotation
- name: Produktive Ressource auflösen (…)               # unverändert: Autorität für die IDs
- name: Konfiguration vorbereiten …
- name: Deploy
```

Der Resolver bleibt die einzige Autorität für die IDs, die Reihenfolge bleibt
(Prüfung → Auflösung → Vorbereitung → Deploy; per Test festgehalten). Der
Environment-Policy-Gate aus #935 (`production-policy`, liest nur
Environment-Metadaten, ohne Cloudflare-Secrets) bleibt unverändert **davor** —
die Zugangsprüfung ersetzt ihn nicht, sie ergänzt ihn um die Cloudflare-Seite
(Token, Konto, Bindung). Neu ist,
dass ein fehlendes Feld **sofort alle** fehlenden Felder nennt und das Dossier in
die Job-Zusammenfassung schreibt. `scripts/worker_zugang.py` und
`scripts/github_kommando.py` stehen jetzt auch in `DEPLOY_DATEIEN` und im
`paths`-Filter: Ändert sich die Prüfung, muss der nächste Lauf beweisen, dass sie
den Deploy noch trägt.

### 3.3 H-C · „Deploy-Zugang prüfen“ (WF-537F) — der Knopf, den es nicht gab

Ein eigener Workflow (`.github/workflows/worker-zugang-pruefen.yml`,
`workflow_dispatch`, Environment `cloudflare-produktion`, nur `main`) mit
derselben Prüfung über **beide** automatischen Worker. Er deployt nicht, er
ändert nichts, er braucht kein Wrangler — und er ist **überwacht**: Der Name steht
in der Wacht-Liste des Fehler-Alertings, weil ein stiller Kanal genau die Klasse
ist, die #922 erzeugt hat. Sein Vorgangscode ist `WF-537F`, Bereich
*Veröffentlichung*; der Titel ist markenneutral wie alle Meldungen dieses Repos.

### 3.4 H-D · Der Rat bleibt am Befund (U3)

In `.github/workflows/alert-on-failure.yml`:

- `workerZugangFailed` erkennt jetzt **drei** Schritte (`Zugang prüfen (alle
  Befunde…`, den alten `Produktive Ressource auflösen` **und** den
  Environment-Gate `Produktions-Environment absichern` aus #935) — der Umzug
  einer Prüfung darf ihren Meldeweg nicht verlieren, und der neue Gate darf ihn
  nicht erben, ohne ihn zu nennen.
- `istZugangsPruefung` / `zugangsPruefungFailed` ordnen den neuen Workflow
  derselben Runbook-Klasse `worker-deploy-zugang` zu.
- Der Rat selbst nennt jetzt den Prüfknopf, das Dossier und die Selbsttests; ein
  roter Selbsttest bleibt in der bestehenden Klasse `selbsttest`
  (Code-Regression, **nicht** Zugangsproblem) — es gibt weiterhin **genau einen**
  Klassennamen pro Rat, sonst bliebe der alte Rat in offenen Meldungen stehen.

### 3.5 H-E · Dokumentation und Verträge

- `docs/SICHERHEIT-BETRIEB-RUNBOOK.md`: A4 (Zugang prüfen ohne Deploy) und D2
  (Zugangs-Diagnose vor dem Deploy, Klassen und Grenzen).
- `docs/ANLEITUNG-NEWSLETTER-EIGENBETRIEB.md`: derselbe Knopf im Setup-Weg.
- `scripts/tests/test_worker_zugang.py`: 43 Verträge (siehe 4.1).
- `scripts/tests/sim/alert_scoping_sim.mjs`: **drei** neue Verhaltens-Szenarien
  (Vorprüfung im Deploy rot → Einrichtungs-Rat; eigener Prüf-Workflow rot →
  derselbe Rat unter eigener Identität; roter Selbsttest → Selbsttest-Rat).
- `scripts/ki_transportweg.py`: enge T6-Ausnahme für den neuen Leser, mit
  Gegenprobe im Testmodul (nur `api.cloudflare.com`, nur zwei Endpunktformen,
  kein Modellverkehr).
- `package.json` (`test:sicherheit`), `sicherheits-wache.yml` (`paths` **beide**
  Listen, Selbsttest im Betriebs-Wachen-Job), `alert-on-failure.yml` (Wacht-Liste).

---

## 4. Verifikation

### 4.1 Der Kernbeweis: zwei fehlende Felder in **einem** Lauf

```text
$ python3 scripts/worker_zugang.py --pruefen
❌ [FEHLT] CF_WORKERS_DEPLOY_TOKEN: … nicht lesbar.
❌ [FEHLT] CLOUDFLARE_ACCOUNT_ID: … nicht lesbar.
❌ [OFFEN] Token-Gültigkeit: Nicht prüfbar, solange CF_WORKERS_DEPLOY_TOKEN fehlt.
❌ [OFFEN] newsletter-worker · Ressource: … Nicht prüfbar …
❌ [OFFEN] klick-zaehler · Ressource: … Nicht prüfbar …
❌ 5 Befund(e) · Klassen: FEHLT, OFFEN. Der Deploy bleibt fail-closed;
   nichts wurde angelegt oder geändert.
   → Exit 1
```

Vorher (Run `40569123622`) nannte derselbe Zustand **ein** Feld. Das Dossier, das
der Lauf jetzt schreibt, listet „Was zu tun ist“ mit den zwei echten Aufgaben und
trennt sauber ab, was danach automatisch nachgeprüft wird („Diese Punkte sind
heute ausdrücklich NICHT bestätigt“).

### 4.2 Grün, ohne Netz — und die Grenzen mitgeprüft

| Prüfung | Ergebnis |
|---|---|
| `python3 scripts/worker_zugang.py --selftest` | ✅ 10 Sabotagefälle (Sammelbefund, Klassen, Maskierung, Endpunktgrenzen) |
| `python3 -m unittest scripts.tests.test_worker_zugang` | ✅ **43 Tests** (inkl. keiner Wert in Log/JSON/Dossier, eine Annotation je Befund, `OFFEN` nie grün, eine Annotation **nicht** für `OFFEN`, T6-Gegenprobe, Workflow-Verdrahtung) |
| `python3 -m unittest scripts.tests.test_alert_scoping` | ✅ 27 Tests, **inkl. der drei neuen Simulationen** gegen das echte `alert-on-failure.yml` |
| `npm run test:sicherheit` | ✅ Exit 0 |
| `python3 scripts/trigger_wache.py --check` | ✅ 96 Workflows, 0 Befunde |
| `python3 scripts/wachen_vertrag.py` | ✅ 352 Skripte, 0 Funde |
| `python3 scripts/skript_syntax_wache.py --check` | ✅ 572 Dateien |
| `python3 scripts/alert_issue_identity.py --selftest` | ✅ 65 Workflows, 65 eindeutige Codes |
| `python3 scripts/actions_version_guard.py` | ✅ keine Drift |
| `python3 scripts/manifest_guard.py` | ✅ grün |
| `python3 scripts/worker_deploy_vorbereiten.py --selftest` | ✅ |
| vollständiger Python-Vertragslauf (`unittest discover`, 4312 Tests) | ✅ alle neuen/berührten Verträge grün; **11 Fehlschläge + 1 Fehler, die identisch auf `origin/main` @ `76efccb` fehlschlagen** (Bestands-/Siegel-Themen: `test_affiliate_*`, `test_alt_text_vorschlaege`, `test_belegketten_wache`, `test_frontmatter_duplikate`, `test_integrity_guard`, `test_inhalts_register` ×3, `test_lcp_image_optimizer`, `test_versicherungs_cluster_verlinkung`, `test_faktenfrische_823`) — in einem eigenen Worktree auf `main` gegengeprüft, nicht von diesem Vorgang |

**Warum `test_ki_transportweg` hier auftaucht:** Der repo-weite T6-Vertrag verbietet
direkte Anbieter-Endpunkte in jedem Skript. Der neue Leser spricht
`api.cloudflare.com` — kein Modell. Er ist deshalb als enge Ausnahme eingetragen
**und** durch einen Gegentest auf genau zwei Endpunktformen festgenagelt. Ohne
diesen Schritt wäre der T6-Vertrag gebrochen (dreimal rot) — der Vertrag hat
funktioniert.

---

## 5. Was offen bleibt — Inhaber-Aufgabe, ein Durchgang

Der Abschluss ist **nicht** im Repository zu erledigen. Reihenfolge (Runbook A4/D2):

1. **Zugang prüfen, ohne zu deployen:** Actions → **„Deploy-Zugang prüfen“** →
   *Run workflow* (`main`) → Freigabe im Environment `cloudflare-produktion`.
   Der Lauf liest nur und nennt **alle** offenen Punkte plus Dossier. (Lokal,
   ohne Netz: `python3 scripts/worker_zugang.py --pruefen`.)
2. **Werte setzen:** GitHub → Settings → Environments → `cloudflare-produktion` →
   *Environment secrets*: `CF_WORKERS_DEPLOY_TOKEN` (Vorlage „Edit Cloudflare
   Workers“: Workers Scripts **Read** *und* **Edit**, D1 *Edit* für den
   Klick-Zähler, begrenzt auf dieses Konto) und `CLOUDFLARE_ACCOUNT_ID`
   (32 Hexzeichen). Required reviewer und Branch-Beschränkung auf `main` bleiben.
3. **Ausrollen:** Actions → „Cloudflare-Worker deployen“ → *Run workflow* (`main`).
   Danach meldet derselbe Lauf den neuen `bau`-Stempel gegen `/healthz` nach.

**Abschlussvertrag:** #922 schließt sich **automatisch** mit dem ersten
vollständig grünen Deploy-Lauf auf `main` (Job-Beweis über
`scripts/alert_resolve_gate.py`: beide genannten Jobs müssen im auflösenden Lauf
vorhanden und grün sein). Ein grüner Plan, ein grüner Prüf-Workflow oder ein
grüner Push ohne Deploy-Job schließen die Meldung ausdrücklich **nicht** — die
Zugangsprüfung bestätigt den Zugang, nicht den Deploy.

---

## 6. Grenzen dieser Heilung (bewusst benannt)

- Sie erzeugt **keinen** Zugang und legt **keine** Ressource an. Fehlt der Token,
  bleibt der Deploy rot — nur in einem Satz, der alles nennt.
- Sie beweist **nicht**, dass der Worker läuft. Dafür stehen die Sicherheits-Wache,
  `/healthz` und der `bau`-Stempel (dieses Werkzeug liest keinen Healthcheck).
- `OFFEN` ist keine Entwarnung. Wer `OFFEN` als grün liest, hat #922 nur
  umformuliert.
- Der Prüf-Workflow braucht dieselbe Environment-Freigabe wie der Deploy. Das ist
  Absicht: Produktionszugänge werden von einem benannten Menschen freigegeben,
  nicht von einer Automatik.

---

*Erstellt im Zuge der Dauerheilung von WF-829B (#922). Vorgänger dieses Vorgangs:
`WARTUNG-BETRIEBSPFLEGE-WF-E813-815-HIGHEND-2026-10-2*.md` (Aufbau der
Deploy-Kette, Resolver, fail-closed), `WARTUNG-BACKUP-WF-9E5A-HIGHEND-2026-10-2*.md`
(Einrichtungs-Diagnose als Vorbild für dieses Dossier).*

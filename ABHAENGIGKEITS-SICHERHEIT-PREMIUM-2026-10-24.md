# 58 offene Schwachstellen, 0 belegbare Fundstellen · Dauerheilung, 24.10.2026

**Ausgangslage:** GitHub meldete auf `main` **58 offene Schwachstellen**
(7 kritisch · 30 hoch · 18 mäßig · 3 niedrig). Eine vollständige Prüfung des
ausgelieferten Bestands gegen **dieselbe Advisory-Datenbank, die Dependabot
benutzt**, ergab am selben Tag **0 Treffer** bei 292 Abfragen (272
npm-Versionen, 16 pip-Pins, 5 Range-Untergrenzen; 0 Fehler).

Das ist kein Widerspruch, den man wegklickt. Es sind zwei getrennte Fehler:
**eine Auflösung, die niemand erneuert** (U1) und **eine Stimme, die fehlt**
(U2). Beide sind hier dauerhaft geschlossen — mit Wache, Vertragstests und
CI-Gate, nicht mit Dismiss.

> Dieser Bericht ist der Wahrheitsort für den Vorgang vom 24.10.2026.
> Vorgeschichte: `CODE-SCANNING-ALERT-83-DAUERHEILUNG-PREMIUM-2026-10-10.md`
> (dieselbe Denkweise für Code-Scanning), `SICHERHEITSAUDIT-PREMIUM-2026-10-14.md`
> (Findings F-01…F-10), `docs/SICHERHEIT-BETRIEB-RUNBOOK.md` Abschnitt E
> (Betriebsanleitung dieser Heilung).

---

## 1 · Der Befund, der keiner war — und warum das gefährlicher ist als ein offener Alert

58 Alarme, 7 davon kritisch, und keine einzige betroffene Version im Bestand.
Drei Erklärungen sind denkbar, zwei davon sind belegt:

| Hypothese | Prüfung | Ergebnis |
|---|---|---|
| Die Versionen sind noch verwundbar | 292 Abfragen `affects=<paket>@<version>` gegen die Advisory-API | **0 Treffer, 0 Fehler** |
| Die Alarme sind veraltet und werden nie neu bewertet | Analyse der Manifeste, die Dependabot liest | **belegt** (U1) |
| Niemand prüft den Bestand unabhängig | Suche nach einer Gegenprobe im Repo | **belegt** (U2) |

### U1 · Auflösungs-Ambiguität: der Alert überlebt seine eigene Heilung

`requirements-ci.in`, `requirements-werkbank.txt` und
`requirements-agent-reach.txt` nannten Versionen als **Bereich** (`>=`, ohne
Pin). Dependabot löst eine solche Anforderung **einmal** auf und hält das
Ergebnis fest. Ändert sich danach nur `requirements-ci.txt` — die
hashgesperrte Auslieferungsdatei —, sieht Dependabot **keinen Anlass**, die
Auflösung zu erneuern. Der Alarm zeigt weiter auf die alte, inzwischen
geheilte Version.

Das erklärt genau das Muster: Der Bestand ist sauber, die Anzeige nicht.
Eine Heilung, die nur die Auslieferung korrigiert, ist damit **nicht
dauerhaft** — sie wartet auf den nächsten Redakteur, der den Bereich wieder
aufmacht.

### U2 · Keine Gegenprobe: die Alarmtabelle ist ein Cache, kein Beweis

Im Repo gab es bis heute keine Stimme, die den **ausgelieferten Bestand**
selbst gegen die Advisory-Datenbank prüft. Der Sicherheitsstatus hing allein
an GitHubs Anzeige — einem Cache, der von Auflösungszeitpunkten abhängt, die
niemand im Repo sieht.

---

## 2 · Was geändert wurde

| Datei | Änderung | Wirkt gegen |
|---|---|---|
| `requirements-ci.in` | 9 Anforderungen von „nackter Name" auf `==<version>` (identisch mit dem Hash-Lock), Kopfkommentar erklärt die Regel | U1 |
| `requirements-werkbank.txt` | `crawl4ai==0.9.5`, `composio==0.30.0`, `PyYAML==6.0.3` | U1 |
| `requirements-agent-reach.txt` | `yt-dlp==2026.10.21`, `feedparser==6.0.14` | U1 |
| `cloudflare/ki-assistent/package-lock.json` | **neu** — 92 Pakete, `lockfileVersion: 3`; die aufgelösten Versionen sind ab jetzt nachweisbar | U2 |
| `cloudflare/ki-assistent/package.json` | `overrides: { "undici": "7.30.1" }` | konkreter Fund (siehe §3) |
| `scripts/abhaengigkeits_wache.py` | **neu** — Offline-Strukturprüfung (A1–A6) + Online-Advisory-Audit | U1 + U2 |
| `scripts/tests/test_abhaengigkeits_wache.py` | **neu** — 33 Verträge inkl. Sabotage- und Gegenproben | Regression |
| `.github/workflows/sicherheits-wache.yml` | Job **Abhängigkeiten**; Audit im Tageslauf, `--check` bei jedem Push | Dauerbetrieb |
| `package.json` | `deps:check`, `deps:audit`, `test:deps`; `test:sicherheit` ruft die Wache mit auf | Bedienbarkeit |
| `SECURITY.md`, `CLAUDE.md`, Runbook E | Vertrag, Agentenregel, Betriebsanleitung | Wissen |

**Nicht** geändert: `requirements-ci.txt`. Die Datei ist die hashgesperrte
Installationsgrundlage von rund 90 Workflows (`--require-hashes`); sie wird
nur gemeinsam mit einer echten Versionsänderung angefasst. Genau deshalb
prüft Regel A2 die **Gleichheit** von Quelle und Auslieferung, statt eine
Seite zu bevorzugen.

---

## 3 · Der Fund, den erst die Wache sichtbar machte

Die fehlende Lockfile in `cloudflare/ki-assistent` war als Warnung (A3)
geführt. Nach dem Erzeugen der Lockfile lief der Audit sofort rot:

```
undici@7.29.1 · HIGH   · GHSA-xjj6-f33q-929c · Fix 6.29.1
undici@7.29.1 · MEDIUM · GHSA-4qv8-2p9j-2685 · Fix 6.29.1
undici@7.29.1 · MEDIUM · GHSA-f72v-6w45-q472 · Fix 7.30.1
```

Drei echte Schwachstellen, die vorher **nicht prüfbar** waren, weil es keine
aufgelösten Versionen gab. Die Heilung ist nicht neu erfunden: Die beiden
Nachbar-Worker (`cloudflare/klick-zaehler`, `tools/wrangler`) tragen längst
`overrides: { "undici": "7.30.1" }`. Diese Datei tut jetzt dasselbe — und
`npm audit` meldet danach `found 0 vulnerabilities`.

Das ist der Beweis, dass die Wache nicht nur grün kann: Sie hat innerhalb
einer Minute einen Befund produziert, den 58 offene GitHub-Alarme nicht
sichtbar gemacht hatten.

---

## 4 · Die Wache: sechs Regeln, zwei Betriebsarten, drei Exit-Codes

### Offline (`--check`) — deterministisch, ohne Netz, in Sekunden

| Regel | Prüft | Schwere |
|---|---|---|
| **A1** | Jede Anforderung in `requirements*.txt` ist ein exakter Pin (`==`). Bereiche, `*`, nackte Namen sind Fehler. | Fehler |
| **A2** | `requirements-ci.in` und `requirements-ci.txt` nennen dieselbe Version (Quelle ↔ Hash-Lock). | Fehler |
| **A3** | Jedes `package.json` mit Abhängigkeiten hat eine Lockfile. | Warnung |
| **A4** | Jede Action hängt an einer Commit-SHA **und** trägt einen Versionskommentar. | Fehler / Warnung |
| **A5** | Kein bewegliches Container-Tag (`:latest`, fehlender Tag). | Fehler |
| **A6** | Kein Paket mit zwei verschiedenen Versionen in derselben Datei. | Fehler |

Diese Prüfung ist **falsch-negativ-frei für das, was sie prüft**: Sie
beurteilt Syntax und Herkunft, nie das Netz. Sie kann deshalb nicht wegen
eines API-Ausfalls grün werden.

### Online (`--audit`) — dieselbe Datenbank wie Dependabot

Für jede ausgelieferte Version (`name@version`, serverseitig geprüft) geht
eine Abfrage an `api.github.com/advisories` mit `affects=`. Das Ergebnis nennt
Paket, Version, Schweregrad, GHSA, `first_patched_version` und die
**Herkunftsdatei**. Budget: 900 Abfragen, Token-Pflicht (`GITHUB_TOKEN`).

### Exit-Codes sind Klassen, keine Stimmungen

| Exit | Bedeutung | Reaktion |
|---|---|---|
| **0** | sauber | – |
| **1** | Befund | auf `first_patched_version` pinnen, PR, erneut messen |
| **2** | Störung (Netz, Rate-Limit, fehlendes Token, Werkzeugfehler) | **rot**, nicht grün. Wiederholen. Ungeprüft ist nicht sauber (Vertrag C34) |

---

## 5 · Regression: 33 Verträge, die nicht nur grün können

`scripts/tests/test_abhaengigkeits_wache.py` hält drei Zusagen fest:

1. **Jede Regel feuert.** Für A1–A6 gibt es einen vergifteten Baum, in dem
   genau die zuständige Regel anschlägt — inklusive Schweregrad.
2. **Keine Regel feuert ohne Anlass.** Ein sauberer Baum bleibt grün; eine
   leere Advisory-Quelle erzeugt keinen Treffer; ein Bereich wird nicht
   auditiert; ein Treffer ohne Fix bleibt als Befund stehen.
3. **Der Bestand bleibt sauber.** `test_check_auf_repo_ist_gruen` prüft bei
   jedem Lauf den echten Repo-Baum. Fällt jemand auf einen Range zurück, wird
   dieser Test rot — nicht erst der Alert in der Security-Tab.

Dazu kommen Parser-Verträge (Hash-Fortsetzungen, Extras, Marker, URLs,
`-r`-Includes, Wildcard-Pins, Scopes in Lockfiles, SHA- vs. Tag-Referenzen)
und ein **Workflow-Vertrag**: Der CI-Job muss die Wache wirklich aufrufen,
sonst schlägt der Test fehl. Eine Wache, die niemand startet, ist Dokumentation.

**Nachweis des Selbsttests (Sabotage-Schutz):** `--selftest` baut Bäume im
temporären Verzeichnis, vergiftet sie gezielt und verlangt, dass genau die
zuständige Regel feuert — plus drei Gegenproben (sauberer Baum bleibt grün,
leere Quelle erzeugt keinen Treffer, immer-treffende Quelle wird gemeldet).

---

## 6 · Dauerbetrieb in CI

`.github/workflows/sicherheits-wache.yml`, Job **Abhängigkeiten (Pins offline ·
Audit online)**:

- **Bei jedem Push und PR** (Pfadfilter auf Requirements, Lockfiles,
  Workflows, Dependabot-Konfiguration): `--selftest` → `--check` →
  Vertragstests. Kein Token, kein Netz, keine Ausrede.
- **Im Tageslauf (06:05 UTC) und auf Zuruf**: `--audit --report … --json`
  gegen die Advisory-API, mit `GITHUB_TOKEN`. Exit 1 und 2 werden als
  getrennte Fehlerannotationen sichtbar; der Bericht landet in der
  Step-Summary.

Damit gilt: Ein neuer Range oder eine neue Lockfile ohne Override ist
**spätestens beim nächsten Push** rot — nicht erst, wenn ein Mensch die
Security-Tab öffnet.

---

## 7 · Beweisführung (nachfahrbar)

```bash
python3 scripts/abhaengigkeits_wache.py --selftest     # ✅ 5 Parser, 6 Regeln, 3 Gegenproben
python3 scripts/abhaengigkeits_wache.py --check        # ✅ 0 Fehler, 0 Warnungen
python3 scripts/abhaengigkeits_wache.py --audit        # ✅ 312 Versionen, 0 Treffer
python3 -m unittest scripts.tests.test_abhaengigkeits_wache   # ✅ 33 Tests
cd cloudflare/ki-assistent && npm audit --package-lock-only    # ✅ 0 vulnerabilities
```

Messwerte dieses Laufs:

| Messung | Vorher | Nachher |
|---|---|---|
| Struktur-Befunde (`--check`) | 5 Fehler + 1 Warnung | **0 / 0** |
| Advisory-Treffer (`--audit`) | 0 (Bestand), aber 3 in der neuen Lockfile | **0** bei 312 Versionen |
| Lockfile `ki-assistent` | fehlt | 92 Pakete, `undici` 7.30.1 |
| Range-Anforderungen in Requirements | 5 | **0** |

Zusätzlich grün: `npm run test:sicherheit` (jetzt inklusive Wache),
`manifest_guard.py` (13 Manifeste, 0 Warnungen), `wachen_vertrag.py`
(322 Skripte, 0 Funde), `url_substring_guard.py` (893 Dateien).

---

### 7.1 · Was sich nicht messen ließ — und wie damit umgegangen wird

Die Alarm-Endpunkte von GitHub sind mit den hier verfügbaren Tokens **nicht
lesbar** (HTTP 403 für `dependabot/alerts` und `secret-scanning/alerts`, auch
mit dem `GITHUB_TOKEN` eines eigens dafür gebauten Diagnose-Laufs). Lesbar war
`code-scanning/alerts` — und dort stand **0**.

Damit gilt für die 58: Sie stammen aus der **Dependabot-Anzeige**, nicht aus
dem Code-Scanning. Ihre Zahl ist ein Cache-Wert, den nur GitHub selbst
fortschreibt. Deshalb wird hier nicht behauptet „die 58 sind weg", sondern
das, was belegbar ist:

> Jede ausgelieferte Version (312) ist gegen dieselbe Advisory-Datenbank
> geprüft und sauber; jede Anforderung ist gepinnt; jede Lockfile existiert;
> jede künftige Abweichung ist rot.

Sobald GitHub den Bestand neu bewertet, verschwinden die Alarme ohne Dismiss,
weil ihre Versionen nicht mehr vorkommen. Bleibt einer stehen, nennt die
Wache beim nächsten Lauf die Herkunft — dann ist es kein Cache-Problem mehr,
sondern ein Befund.

## 8 · Grenzen — was hier ausdrücklich nicht behauptet wird

- **Kein Dismiss.** Es wurde kein GitHub-Alert „not affected" oder
  „won't fix" geschlossen. Die Alarme verschwinden, weil die von ihnen
  genannten Versionen im Bestand nicht mehr vorkommen.
- **Keine Container-Inhalte.** A5 prüft nur, ob ein Image-Tag fest ist —
  nicht, was im Image steckt. `python:3.14-slim` bleibt ein bewegliches Tag
  und ist als solches bekannt, nicht geheilt.
- **Kein Ersatz für Dependabot.** Dependabot öffnet Update-PRs; die Wache
  prüft, was tatsächlich ausgeliefert wird.
- **Nur Repo-Bestand.** Was ein Dienst zur Laufzeit nachlädt, sieht die
  Wache nicht.

---

## 9 · Was beim nächsten Alert zu tun ist

1. `npm run deps:audit` laufen lassen. Exit 0 = der Bestand ist sauber.
2. Nennt der Alarm eine Version, die im Bestand **nicht mehr** vorkommt:
   schließen — mit dieser Messung als Begründung, nicht mit einem Gefühl.
3. Nennt der Alarm eine Version, die noch vorkommt: Die Wache zeigt die
   Herkunftsdatei. Auf `first_patched_version` pinnen, `--check` und
   `--audit` erneut, dann PR.
4. Kommt derselbe Alert wieder, war die Ursache nicht die Version, sondern
   die Auflösung: Range in einer Requirements-Datei (A1) oder Manifest ohne
   Lockfile (A3).

Vollständige Betriebsanleitung: `docs/SICHERHEIT-BETRIEB-RUNBOOK.md`, Abschnitt E.

---

## 10 · Nachtrag: was nach dem Merge gemessen wurde (24.10.2026, 15:30 UTC)

- **#848 ist gemergt.** Die Pins, die Lockfile, die Wache und das CI-Gate
  stehen auf `main`; der Job *Abhängigkeiten (Pins offline · Audit online)*
  läuft dort bei jedem Push und im Tageslauf.
- **Code-Scanning: 0 offene Alarme.** Mit dem Repository-Token gemessen
  (`code-scanning/alerts`) — die 58 stammen also nicht aus dieser Quelle.
- **Dependabot- und Secret-Scanning-Endpunkte: 403.** Weder das Agenten-Token
  noch das `GITHUB_TOKEN` eines eigens gebauten Diagnose-Laufs dürfen sie
  lesen. Die Alarmliste ist damit **nicht maschinell prüfbar** — nur die
  Anzeige im Repository.
- **Der Zähler stand nach dem Merge weiter auf 58** (7/30/18/3). Das ist
  erwartbar, wenn die Alarme an eine **früher aufgelöste** Fassung der
  Requirements gebunden sind (U1): Sie fallen erst, wenn Dependabot die
  Manifeste neu auflöst. Es ist **nicht** so, dass die Heilung nichts bewirkt
  hat — der Bestand war schon vorher sauber; geändert hat sich, dass er es
  bleibt und dass es nachweisbar ist.

**Der Satz, der hier stehen darf:** Jede ausgelieferte Version ist gegen
dieselbe Advisory-Datenbank geprüft und sauber; jede Anforderung ist gepinnt;
jede Lockfile existiert; jede Abweichung ist ab jetzt rot.

**Der Satz, der hier nicht stehen darf:** „Die 58 sind weg." Das kann erst
behauptet werden, wenn die Anzeige fällt oder die Liste einzeln abgeglichen
ist. Wer sie abgleichen will: Security → Dependabot → *Export as CSV*; die
Wache nennt zu jedem Paket die Herkunftsdatei und den Fix.

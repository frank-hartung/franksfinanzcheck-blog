# Anleitung: Manifest-Wache (package.json & Lockfile)

**Vorgang:** WF-7B6B · Meldung #654 · Stand 08.10.2026
**Code:** `scripts/manifest_guard.py` · **Tests:** `scripts/tests/test_manifest_guard.py`
**Vorgangsbericht:** `WF-7B6B-654-DAUERHEILUNG-PREMIUM-2026-10-08.md`

---

## 1. Wozu die Wache da ist

Am 08.10.2026 hat ein Merge (#647) eine `package.json` mit **ungültigem JSON**
auf `main` zurückgelassen: ein fehlendes Komma zwischen zwei Blöcken, der
Schlüssel `pagefind` doppelt, `lighthouse` doppelt. Folgen:

- Der E2E-Lauf auf `main` brach im Schritt *Abhängigkeiten installieren*
  (`npm ci`) ab – **in Sekunde 1**.
- Von 10:41 bis 12:50 UTC scheiterte **jeder Produktions-Deploy** im Schritt
  *Suchindex bauen (Pagefind)*, der ebenfalls `npm ci` ausführt.
- Die automatische Meldung (#654) riet zu „API-Key abgelaufen“ oder
  „GitHub-Ausfall“. Die Ursache stand in Zeile 181 der Datei.

Die Wache prüft Manifest und Lockfile **vor** dem Install und nennt Datei,
Zeile und Ursache. Im GitHub-Lauf erscheint der Befund als Annotation direkt
an der betroffenen Zeile.

---

## 2. Was geprüft wird

Jedes Verzeichnis mit `package.json` (Wurzel, `tools/ff-voice-browser`,
`tools/ff-voice-qa`, `newsletter-worker`) wird als Paar geprüft.

| Code | Prüfung | Schwere |
|---|---|---|
| **K1** | Git-Konfliktmarker (`<<<<<<<`, `=======`, `>>>>>>>`) in der Datei | Fehler |
| **J1** | Die Datei ist gültiges JSON – mit Zeile, Spalte und Ursache in Klartext | Fehler |
| **J2** | Doppelter Schlüssel im selben Objekt. JSON erlaubt ihn, npm nimmt still den letzten Wert | Fehler |
| **F1** | Abhängigkeitsblöcke und `scripts` sind Objekte aus Name und Text | Fehler |
| **D1** | Ein Paket steht in `dependencies` **und** `devDependencies` (npm toleriert es, typisches Merge-Rest) | Warnung |
| **L1** | Lockfile-Format: `lockfileVersion` 2 oder 3, Feld `packages`, Wurzel-Eintrag `packages[""]` | Fehler |
| **L2** | Wurzel-Sync: `packages[""]` trägt exakt die Deklarationen des Manifests. Daran scheitert `npm ci` mit „nicht synchron“ | Fehler |
| **L3** | Jede deklarierte Abhängigkeit hat einen Eintrag `node_modules/<name>` im Lock | Fehler |
| **L4** | Exakt gepinnte Versionen (`1.2.3`) stimmen mit dem Lock überein | Fehler |
| **P1** | Lock ohne Manifest: Fehler. Manifest ohne Lock: Warnung (ausgenommen: `newsletter-worker`, siehe unten) | Fehler / Warnung |

**Bewusst nicht geprüft:** Versions-Ranges wie `^30.1.2`. Ob ein Range zum
Lock passt, entscheidet `npm ci` selbst. Die Wache sagt nur vorher, woran es
liegt, sie ersetzt npm nicht.

**Begründete Ausnahme:** `newsletter-worker/package.json` hat bewusst kein
Lockfile. Es ist ein Cloudflare-Worker, der über `wrangler` gebaut wird und in
keinem Workflow per `npm ci` installiert wird (geprüft am 08.10.2026). Die
Ausnahme gilt nur für diesen Pfad (`OHNE_LOCKFILE_ERLAUBT`) und ist im
Selbsttest abgesichert.

---

## 3. Bedienung

```bash
npm run manifest:check                          # Arbeitsbaum prüfen (Exit 1 bei Befund)
npm run test:manifest                           # Selbsttest + Unit-Tests
python3 scripts/manifest_guard.py --selftest    # nur die Sabotageproben
python3 scripts/manifest_guard.py --json        # Maschinenausgabe
python3 scripts/manifest_guard.py --ref <sha>   # Stand eines Commits prüfen (Vorfall nachspielen)
```

**Exit-Codes:** `0` grün (Warnungen zulässig) · `1` Befund, `npm ci` würde
scheitern · `2` Werkzeugfehler (Selbsttest rot, Ref nicht lesbar).

Beispiel für den Vorfall (Commit `dcc3138553`, Merge #647):

```
❌ FEHLER [J1] package.json Zeile 181, Spalte 5: kein gültiges JSON: Expecting ',' delimiter
      → Fehlendes Komma zwischen zwei Einträgen. Typisch für einen Merge, der zwei Blöcke nebeneinander legt – `git log -p -- <datei>` zeigt den Moment.
ERGEBNIS: ROT – 1 Befund(e), 0 Warnung(en). npm ci würde hier abbrechen (Exit 1).
```

---

## 4. Wo die Wache läuft

Vor **jedem** `npm ci` oder `npm install` im Repo, jeweils als eigener Schritt
`Manifest-Wache` oder `Manifest-Schutz`:

| Workflow | Job | Hinweis |
|---|---|---|
| `deploy.yml` | `deploy` | direkt nach dem Merge-Marker-Schutz, vor jedem Gate und vor dem Build (fail-closed) |
| `e2e.yml` | `e2e` | direkt nach dem Checkout, vor Hugo und `npm ci` |
| `design-varianten.yml` | `werkbank` | vor dem Install |
| `lesehilfen-gate.yml` | `lesehilfen` | vor den beiden Install-Schritten |
| `robustheit.yml` | `robustheit` | **vor** dem Install mit `|| npm install`-Ausweichweg – der würde ein defektes Lockfile still reparieren |
| `themenwelten-gate.yml` | `navigation` | vor `npm ci --prefix tools/ff-voice-browser` |
| `werkbank.yml` | `werkbank` | vor dem Browser-Install |

Der Test `VerdrahtungTests` in `test_manifest_guard.py` prüft das bei jedem
Lauf der Unit-Tests: Ein neuer Workflow mit `npm ci` ohne vorgeschaltete Wache
wird rot.

---

## 5. Wenn der Alarm kommt

Schlägt ein Install- oder Manifest-Schritt fehl, nennt die Meldung nicht mehr
den API-Key, sondern diese Reihenfolge:

1. **Im Log des roten Schritts** stehen Datei, Zeile und Ursache. Die Wache
   zeigt außerdem denselben Befund als Annotation an der Zeile im PR.
2. **Lokal prüfen:** `npm run manifest:check`.
3. **Ursache beheben:**
   - **J1 (Syntax, z. B. fehlendes Komma):** Stelle korrigieren. Bei einem
     Merge zeigt `git log -p -- package.json`, welcher Commit sie eingeführt hat.
   - **K1 (Konfliktmarker):** Merge vollständig auflösen, die Marker entfernen.
   - **J2 (doppelter Schlüssel):** den falschen Eintrag löschen. Welcher Wert
     richtig ist, ergibt sich aus der letzten guten Fassung.
   - **L2, L3, L4 (Lock nicht synchron):** Lock neu erzeugen, dann beide Dateien
     zusammen committen:
     ```bash
     npm install --package-lock-only --ignore-scripts
     git diff -- package-lock.json      # Änderungen prüfen
     npm run test:manifest
     ```
     Den Lock niemals von Hand auf einen Pin setzen. Der Pin gehört in
     `package.json`, der Lock folgt.
   - **L1 (Format):** Lock mit npm 10 neu erzeugen (siehe oben).
4. **Erst danach** einen Registry- oder GitHub-Ausfall prüfen
   (<https://www.githubstatus.com>) und den Lauf neu starten.

Die Meldung schließt sich automatisch, sobald der beobachtete Workflow auf
`main` wieder grün läuft.

---

## 6. Grenzen

- **Kein Ersatz für `npm ci`.** Die Wache prüft Struktur und Sync, nicht
  Versions-Ranges und nicht die Registry.
- **Kein Merge-Schutz.** Die Wache blockiert einen Merge nur, wenn der Check
  im Branch-Schutz als Pflicht-Check hinterlegt ist. Das ist eine
  Admin-Entscheidung (Governance-Regel C15). Auf diesem Repo ist derzeit
  kein Pflicht-Check gesetzt. PR #647 wurde 17 Sekunden nach dem roten
  E2E-Lauf gemergt.
- **Nicht für Umgebungen ohne Git-Historie gedacht.** `--ref` braucht ein
  Git-Repo.

---

## 7. Erweitern

Eine neue Prüfung bekommt:

1. eine Regel mit eigenem Code (K/J/F/D/L/P) und Hinweistext,
2. einen Sabotage-Fall in `_probe_werte()` (mit `"rein": True`, wenn sie allein
   feuern muss),
3. einen Unit-Test in `scripts/tests/test_manifest_guard.py`,
4. einen Eintrag in diesem Runbook.

Eine neue Ausnahme (`OHNE_LOCKFILE_ERLAUBT`) braucht eine Begründung im Code
und einen Eintrag in Abschnitt 2 dieses Runbooks.

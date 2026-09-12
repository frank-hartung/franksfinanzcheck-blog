# Reparatur Issue #220 – Affiliate-Integritäts-Wache (täglich)

**Datum:** 08.09.2026 · **Status:** behoben · **Klasse:** Ursachenreparatur (Betriebslücke, nicht Content)

---

## 1. Kurzfassung für Frank

Die Affiliate-Links waren **nicht kaputt**. Die Wache ist am **Hugo-Build** gestorben, **bevor** sie einen einzigen Link anfassen konnte.

* Run `34204720578` (08.09.2026, 10:28 MESZ): 13 Sekunden, dann rot.
* Schritt „Hugo-Build“ fehlgeschlagen.
* Gate, Heilung, Report, Deploy-Trigger und fachliches Issue: **alle übersprungen**.
* Das zentrale Alerting hat daraus Issue #220 gebaut – mit der Standard-Vermutung „API-Key abgelaufen“. Die trifft hier nicht zu. Diese Wache braucht keinen KI-Key.

Drei Reparaturen: Hugo darf nicht mehr mit einem Schuss die Wache töten, das Gate läuft trotzdem, und ein Werkzeugfehler hinterlässt ein ehrliches fachliches Issue statt eines Phantom-Alarms.

---

## 2. Beweislage

| Fakt | Wert |
|---|---|
| Workflow | Affiliate-Integritäts-Wache (täglich) |
| Run | [34204720578](https://github.com/frank-hartung/franksfinanzcheck-blog/actions/runs/34204720578) |
| Commit | `1f418192` |
| Job-Dauer | 08:28:56–08:29:09 UTC (**13 s**) |
| Hugo installieren | success |
| Hugo-Build | **failure** |
| Gate / Commit / Deploy / Issue | **skipped** |
| Vortage (7 schedule-Läufe) | alle **success** (17–31 s) |
| Letzter grüner Report im Repo | 07.09.2026, 31 Live-Artikel, 0 Funde |

Der Render-Beweis AI4 braucht ein gebautes `public/`. Deshalb steht `hugo --minify` vor dem Gate. Genau diese eine Zeile war ein Single Point of Failure.

---

## 3. Ursachenkette

```
hugo --minify  (ein Versuch, kein Log, kein Extended-Check)
        └─> Schritt rot
                └─> alle Folgeschritte skipped
                        └─> Gate kommt nicht zum eigenen Rebuild
                                └─> kein fachliches Issue, kein Artefakt
                                        └─> Alerting öffnet #220
                                            („API-Key abgelaufen“)
```

Zusätzlich fehlten im **Live-YAML** Teile des Premium-Ausbaus vom 02.09. (Selftest-Stage, idempotente Issue-Pflege, Deploy nur bei `healed+pushed`, Diagnose-Artefakt). `actions: write` war schon da – der Rest nicht. Deshalb blieb ein Hugo-Flake stumm und unheilbar.

---

## 4. Die Reparaturen

### R1 – Hugo-Extended nachweisen, sonst selbst laden

PaperMod braucht die Extended-Binary (TOCSS/Libsass). Liefert die Install-Action still die Standard-Binary, stirbt `hugo --minify` in Sekunden – passend zum 13-Sekunden-Run. Jetzt: Version prüfen, bei Bedarf Extended direkt von GitHub Releases holen.

### R2 – Hugo-Build 3×, Log, halbfertiges `public/` löschen

Drei Versuche mit Pause. Bei endgültigem Fehlschlag wird `public/` entfernt, damit das Gate nicht gegen ein unvollständiges Artefakt „aktuell“ beweist.

### R3 – Gate läuft trotzdem

`continue-on-error` am Hugo-Schritt. Das Gate hat `ensure_build()` und baut selbst – jetzt mit **drei Versuchen** (`rebuild_hugo`). Ein Runner-Blip im Vor-Build darf die Integritätsprüfung nicht mehr ausfallen lassen.

### R4 – Premium-Betrieb nachziehen

* Detektor-Selbsttest vor jeder Prüfung (fail-closed)
* Deploy nur bei echter Heilung **und** erfolgreichem Push (nicht mehr über `GEHEILT` aus `git_sync.sh`, das auch bei „nichts zu pushen“ greift)
* Ein fachliches Issue pro Schadenslage, bei Grün automatisch zu, inkl. Hugo-Log
* Artefakt 14 Tage bei Rot
* Job-Timeout 20 Minuten
* Inhaltsschaden → fachliches Issue, Lauf betrieblich grün (kein Doppelalarm)
* Unheilbarer Werkzeugfehler nach allen Wiederholungen → Lauf rot (Alerting bleibt ehrlich)

---

## 5. Absicherung

| Prüfung | Ergebnis |
|---|---|
| `python3 scripts/affiliate_integrity_gate.py --selftest` | bestanden, inkl. neuem Fall „kein Hugo-Binary = klarer Werkzeugfehler“ |
| YAML der Wache | gültig |
| Vorher: ein Hugo-Exit skipped die ganze Wache | nachher: bis zu 6 Build-Versuche (3 Workflow + 3 Gate), danach ehrlicher Werkzeugfehler |

**Nicht angetastet:** CTA-Vorlagen, Registry `check24_links.yaml`, Render-Hook, Shortcode-Partial, fail-closed gegenüber `publish_gate.py`, Konvergenz von Report/Zustand (kein täglicher Leer-Commit).

---

## 6. Erwartete Wirkung

| Kennzahl | vorher | nachher |
|---|---|---|
| Hugo-Flake → Wache tot | ja | nein (Retry + Gate-Rebuild) |
| Diagnose im Issue | „API-Key?“ | Hugo-Log + Exit-Code + Selftest |
| Issue-Flut bei gleichem Schaden | möglich | ein Issue, auto-close bei Grün |
| Deploy ohne Heilung | möglich (`GEHEILT`) | nur `healed && pushed` |
| Echte kaputte CTAs | würden nie geprüft, wenn Hugo stirbt | werden geprüft und geheilt |

Nach dem Merge einmal **Actions → Affiliate-Integritäts-Wache (täglich) → Run workflow**. Erwartet: Selftest ✅ → Hugo ✅ → Gate 🟢 → „keine Änderungen“ → Lauf grün. Issue #220 schließt das zentrale Alerting dann selbst.

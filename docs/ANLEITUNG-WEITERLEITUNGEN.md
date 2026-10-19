# Anleitung: Weiterleitungen für verschobene Beiträge

Stand: 19.10.2026 · Gilt für: `data/weiterleitungen.yaml`, `data/url_entfallen.yaml`, `scripts/weiterleitungen.py`, `scripts/url_wache.py`, `scripts/index_hygiene_gate.py` (Teil H9)

## 1. Warum es das gibt

117 Beiträge waren veröffentlicht und sind heute nicht mehr erreichbar. Die Ursachen sind Datums-Korrekturen beim Ordnernamen, Dubletten mit Suffix `(1)` und ersetzte Beiträge. Ohne Weiterleitung gehen Besucher und Suchmaschinen-Signale verloren.

Die Hugo-Aliase sind absichtlich abgeschaltet (`hugo.toml`: `disableAliases = true`). Deshalb liegen die Weiterleitungen als eigene Seiten unter `static/` und entstehen aus einer einzigen Quelle.

**Grenze, bitte kennen:** GitHub Pages kann keine echten HTTP-301 setzen. Die erzeugte Seite ist eine Meta-Refresh-Seite (0 Sekunden, `canonical`, `noindex,follow`). Ein echter 301 entsteht nur über den Cloudflare-Proxy. Siehe Abschnitt 6.

## 2. Die Quelle der Wahrheit

`data/weiterleitungen.yaml` enthält je Eintrag:

| Feld | Bedeutung |
|---|---|
| `von` | Alt-URL, Format `/posts/<slug>/` |
| `nach` | Ziel, `/posts/<slug>/` oder `/pillar/<key>/` |
| `regel` | `A`, `B` oder `C` (siehe Abschnitt 3) |
| `grund` | Begründung in Klartext. Bei Teilüberschneidung steht das ausdrücklich dabei. |

`data/url_entfallen.yaml` enthält URLs, die **bewusst 404** bleiben (Regel D und E).

Nicht von Hand in `static/` ändern. Dort liegt nur das Ergebnis.

## 3. Regeln

| Regel | Wann | Ziel |
|---|---|---|
| **A** | Ordner umbenannt (Datumskorrektur) oder Dublette `(1)` mit gleichem Titel | Der exakte Nachfolger. Der Slug-Rest nach Datum und `(1)` muss identisch sein, das prüft der Generator. |
| **B** | Gleiches Thema, gleiche Suchabsicht | Ein Live-Beitrag, manuell gewählt und im Grund begründet |
| **C** | Kein gleichwertiger Beitrag live | Die **Pillar-Seite** des Themas. Niemals die Startseite. |
| **D** | Kein Themenbezug, kein Pillar passt | Bewusst 404 (`url_entfallen.yaml`) |
| **E** | Tag-Archive `/tags/…/` | Bewusst 404. Entscheidung „Index-Hygiene“ vom 29.09.2026. Tag-Archive sind noindex, nicht in der Sitemap und haben keine externen Links. |

Harte Regeln, die der Generator erzwingt:

- Ziele sind **live** (`draft: false`). Entwürfe sind als Ziel verboten.
- **Keine Ketten:** Ein Ziel darf nicht selbst Quelle einer Weiterleitung sein.
- **Keine Schleifen:** Ziel gleich Quelle ist verboten.
- Eine Quelle darf **nicht live** sein. Sonst überdeckt die Weiterleitung eine Live-Seite.
- Regel C verlangt ein Pillar-Ziel, Regel A und B verlangen ein Beitrags-Ziel.

## 4. Befehle

```bash
python3 scripts/weiterleitungen.py --check      # Quelle validieren (Ziele live, keine Ketten, Regeln)
python3 scripts/weiterleitungen.py --build      # static/<von>/index.html erzeugen, veraltete eigene Seiten entfernen
python3 scripts/weiterleitungen.py --verify     # erzeugte Seiten gegen die Quelle prüfen (schreibt nichts)
python3 scripts/weiterleitungen.py --proxy-check # Cloudflare-Proxy per cf-ray prüfen (braucht Internet)
python3 scripts/url_wache.py                    # verschwundene Live-URLs melden (exit 1 bei Befund)
python3 scripts/url_wache.py --snapshot         # Snapshot neu schreiben, nur nach bewusster Änderung
python3 scripts/weiterleitungen.py --selftest   # Selbsttest
npm run weiterleitungen:check                   # check + verify + Wache in einem Lauf
npm run test:weiterleitungen                    # Selbsttests + Unit-Tests
```

`npm run` ruft `python3` auf. PyYAML muss dafür im Python installiert sein. Lokal wird das Projekt-Venv genutzt (`/tmp/gv/bin/python`).

## 5. Ablauf bei einer neuen Umbenennung oder Löschung

1. Die Wache meldet: `BEFUND … Live-URL verschwunden ohne Weiterleitung`. Dazu gibt es einen Vorschlag über den datumsbereinigten Slug. Der Vorschlag ist nur ein Hinweis.
2. Eine Person entscheidet die Regel:
   - exakter Nachfolger → Regel A
   - gleiches Thema, passender Beitrag → Regel B, Grund schreiben
   - sonst Pillar → Regel C
   - sonst bewusst 404 → Regel D, Grund schreiben
3. Eintrag in die passende Datei schreiben.
4. `python3 scripts/weiterleitungen.py --build`
5. `python3 scripts/url_wache.py --snapshot` (erst nach Prüfung, dass die Änderung gewollt ist)
6. `npm run test:weiterleitungen`, dann committen.

Der Snapshot ist kein Freibrief. Er hält fest, welche URLs live sind. Ein Snapshot-Update ohne vorherige Prüfung der Befunde verbirgt Verluste.

## 6. Cloudflare-Proxy (echte 301)

Aktuell zeigt `franksfinanzcheck.de` ohne Proxy direkt auf GitHub Pages. Ein echter 301 braucht den Proxy.

Vorgehen, wenn der Proxy aktiv ist:

1. `python3 scripts/weiterleitungen.py --proxy-check` (auf deinem Rechner, braucht Internet). Ausgabe `aktiv` heißt: Antwort trägt `cf-ray`. `unbekannt` heißt: Anfrage gescheitert, das ist kein Beleg für „inaktiv“. Die Sandbox kann diese Prüfung nicht ausführen.
2. Nur bei `aktiv`: `python3 scripts/weiterleitungen.py --cloudflare`. Erzeugt `cloudflare/redirects/bulk-redirects.csv`. Ohne nachgewiesen aktiven Proxy verweigert der Befehl die Ausgabe.
3. CSV-Format (laut Cloudflare-Doku, ohne Kopfzeile): `<Quelle>,<Ziel>,301,FALSE,FALSE,FALSE,FALSE`. Die Quelle hat kein `https://`, das Ziel schon.
4. CSV im Dashboard unter *Bulk Redirects* importieren. Der Upload ist **eine Außenwirkung**, deshalb macht ihn die Redaktion, nicht die Sandbox.
5. Nach dem Import eine Stichprobe mit `curl -I` prüfen: `301` und `location`.

Die Datenschutz-Folgen des Proxys stehen in `docs/SICHERHEIT-BETRIEB-RUNBOOK.md` (Punkt B7). Vor der Aktivierung prüfen.

## 7. Durchsetzung

| Stelle | Was sie prüft | Wann |
|---|---|---|
| `scripts/index_hygiene_gate.py` (H9) | Jede Weiterleitungsseite hat ein Ziel, das im Build existiert, indexierbar ist, keine Kette und keine Schleife bildet | Im Deploy nach dem Build (`deploy.yml`). Harter Fund stoppt den Deploy. |
| Gate H5 | Weiterleitungsseiten zählen nicht in das Verhältnis indexierbar : nicht indexierbar | Im Deploy |
| `scripts/tests/test_weiterleitungen.py` | Quelle grün, Seiten stimmen, Snapshot aktuell | Lokal über `npm run test:weiterleitungen`. In der CI läuft dieser Test **nicht** automatisch (die Workflows führen `unittest` nur für benannte Module aus). |

Die Quellprüfung `--check` läuft in der CI nicht. Eine Aufnahme in `deploy.yml` ist eine Workflow-Änderung und braucht einen ausdrücklichen Auftrag (CLAUDE.md).

## 8. Bekannte Grenzen

- Ohne Cloudflare-Proxy ist die Weiterleitung eine Meta-Refresh-Seite. Google behandelt sie als Weiterleitung, aber die Signalübertragung ist schwächer als bei einem echten 301.
- Der Snapshot umfasst alle Live-URLs aus `content/`. Änderungen an `layouts/` oder `static/` erscheinen nicht darin.
- Die Zuordnung der 114 Ziele beruht auf Titel, Thema und Stichproben. Nicht jeder Text wurde einzeln gelesen. Jeder Eintrag hat eine Begründung. Vor dem Cloudflare-Import (Abschnitt 6) sollte die Redaktion die Regel-B-Einträge gegenlesen.

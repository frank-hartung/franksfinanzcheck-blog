# Externe SEO-Daten mit claude-seo (GSC, CrUX, Drift)

Stand: 10.10.2026 · Werkzeug: `AgriciDaniel/claude-seo` v2.4.2

**Abgrenzung – bitte vorher lesen.** Diese Anleitung ergänzt das
[lokale SEO-Cockpit](ANLEITUNG-SEO-COCKPIT.md), sie ersetzt es nicht.
Der Unterschied ist der Blickwinkel:

| | SEO-Cockpit (`npm run seo:audit`) | claude-seo |
|---|---|---|
| Datenquelle | lokaler Hugo-Build (`public/`) | Live-URLs + Google-APIs |
| Kosten | keine | Google-API-Kontingente beachten; keine Drittanbieter-Abos nötig |
| Zugangsdaten | keine | API-Key, optional OAuth |
| Beantwortet | „Ist der Build technisch sauber?" | „Was sieht und misst Google wirklich?" |

Euer Cockpit ist auf der On-Page-Seite bereits weiter als dieses Werkzeug
(Article-JSON-LD mit E-E-A-T-Knoten, `citation`-Belegkette, `llms.txt` mit
Content-Signals). Der Zusatznutzen liegt **ausschließlich bei Felddaten**,
die aus einem statischen Build nicht hervorgehen können.

---

## 1. Voraussetzungen

Die Installation liegt **global** unter `~/.claude/skills/seo/`, nicht im
Projekt. Die Projekt-Skills in `.claude/skills/` bleiben unberührt; beide
werden gleichzeitig geladen.

```bash
# Installationsstatus prüfen
~/.claude/skills/seo/scripts/claude-seo doctor
#   Runtime: ready · Install mode: manual · Python: 3.11 · Chromium: not installed

# Welche Zugänge fehlen?
~/.claude/skills/seo/.venv/bin/python ~/.claude/skills/seo/scripts/google_auth.py --check
```

Pfade, die dieses Werkzeug benutzt:

| Zweck | Pfad |
|---|---|
| Konfiguration | `~/.config/claude-seo/google-api.json` |
| Drift-Datenbank | `~/.cache/claude-seo/drift/baselines.db` |
| Python-Runtime (venv) | `~/.claude/skills/seo/.venv/bin/python` |

**Keine Zugangsdaten jemals im Repository ablegen.** Alles liegt unterhalb
von `~/.config/` bzw. `~/.cache/`, also außerhalb von Git.

---

## 2. Schritt 1 – API-Key für PageSpeed und CrUX

Das ist der **einzige Schritt mit echtem Neuwert und ohne OAuth**: ein
API-Key, der nur zwei lesende APIs freigibt. Er liefert
Core-Web-Vitals-**Felddaten** echter Nutzer aus den rollierenden
CrUX-Erhebungen – euer lokales Cockpit misst dagegen keine echten
Nutzerbedingungen.

1. <https://console.cloud.google.com> öffnen, Projekt wählen oder anlegen.
2. **APIs & Services → Bibliothek**, freischalten:
   - **PageSpeed Insights API**
   - **Chrome UX Report API**
3. **APIs & Services → Anmeldedaten → Anmeldedaten erstellen → API-Schlüssel**.
4. Den Schlüssel **einschränken** auf genau diese beiden APIs. Ohne
   Einschränkung ist ein abgegriffener Schlüssel für beliebige
   Google-APIs nutzbar.

Den Schlüssel nicht in Chat, Git oder die Shell-History schreiben. Sicher
lokal in die Konfiguration übernehmen und einen vorhandenen GSC-Eintrag
dabei erhalten:

```bash
mkdir -p ~/.config/claude-seo
chmod 700 ~/.config/claude-seo

python3 - <<'PY'
import getpass, json, os, tempfile
from pathlib import Path

path = Path.home() / ".config/claude-seo/google-api.json"
try:
    config = json.loads(path.read_text())
except (FileNotFoundError, json.JSONDecodeError):
    config = {}
config["api_key"] = getpass.getpass("Google API-Key (Eingabe bleibt unsichtbar): ")
path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".google-api.", suffix=".tmp")
os.chmod(tmp, 0o600)
with os.fdopen(fd, "w") as handle:
    json.dump(config, handle, indent=2)
os.replace(tmp, path)
os.chmod(path, 0o600)
print(f"Gespeichert: {path} (Modus 600)")
PY

# Prüfen – nur Status ausgeben, niemals den Schlüssel posten
~/.claude/skills/seo/.venv/bin/python ~/.claude/skills/seo/scripts/google_auth.py --check psi
~/.claude/skills/seo/.venv/bin/python ~/.claude/skills/seo/scripts/google_auth.py --tier
```

Alternativ ohne Datei, wenn der Schlüssel nur in einer Shell-Sitzung
gebraucht wird: `export GOOGLE_API_KEY=...`

---

## 3. Schritt 2 – CrUX-Felddaten über die sechs Pillar-Seiten

Die Pillar-Ratgeber tragen thematisch das meiste Gewicht, deshalb ist das
der richtige Startpunkt. (Es sind **sechs** Ratgeber, nicht sieben –
`content/pillar/_index.md` ist die Übersichtsseite.)

```bash
SEO=~/.claude/skills/seo/.venv/bin/python
S=~/.claude/skills/seo/scripts

for p in strom-sparen internet-dsl versicherungen konto-karten mietwagen frugalismus; do
  echo "── pillar/$p"
  "$SEO" "$S/crux_history.py" "https://franksfinanzcheck.de/pillar/$p/" \
         --form-factor PHONE --json
done
```

Für eine Einzelmessung inklusive Lighthouse-Laborwerten:

```bash
"$SEO" "$S/pagespeed_check.py" "https://franksfinanzcheck.de/pillar/strom-sparen/" \
       --strategy mobile --json
```

`--strategy` kennt `mobile`, `desktop`, `both` (Vorgabe `both`).
`--form-factor` kennt `PHONE`, `DESKTOP`, `TABLET`.

> **Erwartungshaltung:** CrUX liefert für Seiten mit wenig Verkehr unter
> Umständen keine Daten. Fehlende Werte sind dann keine Fehlermeldung,
> sondern ein Datenmengen-Thema.

---

## 4. Schritt 3 – Drift-Baseline setzen

Die Baseline hält Titel, Meta-Tags, Canonical, Überschriften, JSON-LD,
OG-Tags und – sofern ein API-Key gesetzt ist – die Core Web Vitals als
„bekannt gut" in SQLite fest. Spätere Läufe zeigen Abweichungen.

```bash
SEO=~/.claude/skills/seo/.venv/bin/python
S=~/.claude/skills/seo/scripts

# Baseline anlegen (einmalig)
for p in strom-sparen internet-dsl versicherungen konto-karten mietwagen frugalismus; do
  "$SEO" "$S/drift_baseline.py" "https://franksfinanzcheck.de/pillar/$p/"
done

# Wöchentlicher Vergleich
for p in strom-sparen internet-dsl versicherungen konto-karten mietwagen frugalismus; do
  "$SEO" "$S/drift_compare.py" "https://franksfinanzcheck.de/pillar/$p/" --json
done
```

- `--skip-cwv` lässt die Core-Web-Vitals-Messung weg (schneller, kein
  API-Key nötig) – sinnvoll, wenn Schritt 1 noch nicht erledigt ist.
- `--baseline-id` vergleicht gegen eine bestimmte ältere Baseline.
- Die Datenbank liegt unter `~/.cache/claude-seo/drift/baselines.db`.
  Umstellbar über `export CLAUDE_SEO_DATA_DIR=...` (muss ein eigenes
  Unterverzeichnis sein, nicht `$HOME` selbst).

---

## 5. Schritt 4 – Search Console: bewusste Entscheidung

⚠️ **Hier gibt es eine Vorentscheidung in diesem Repository.**
[ANLEITUNG-GOOGLE-SEARCH-CONSOLE.md](ANLEITUNG-GOOGLE-SEARCH-CONSOLE.md)
beschreibt den **manuellen Weg**: Leistungsbericht als CSV exportieren und
lokal ins SEO-Cockpit importieren – ausdrücklich *„keine Search-Console-API,
kein Google-Cloud-Projekt, keine Zugangsdaten … Es wird nichts hochgeladen."*

Der API-Weg automatisiert diesen Export, ändert aber die Risikolage:

| | Manueller CSV-Import (bisher) | API-Zugang (claude-seo) |
|---|---|---|
| Aufwand | jedes Mal von Hand | einmalig einrichten, dann automatisch |
| Zugangsdaten | keine | OAuth-Token bzw. Dienstkonto auf der Festplatte |
| Google-Cloud-Projekt | nicht nötig | nötig |
| Angriffsfläche | keine | Token-Diebstahl möglich (Leserechte) |
| Datenaktualität | Stichtag des Exports | täglich abrufbar |

**Für den von dir gewünschten ersten Schritt nehmen wir jetzt OAuth.**
Damit bleibt die Search-Console-Nutzung an deinem Google-Konto hängen; das
Tool liest danach nur mit dem für seine GSC-Aufrufe verwendeten
`webmasters.readonly`-Bereich. Die interaktive Einwilligung wird trotzdem vom
Tool mit mehreren Bereichen angefordert – siehe den Sicherheitshinweis unten.

### 5a. OAuth-Client einmalig anlegen

1. In <https://console.cloud.google.com> ein Projekt wählen oder anlegen und
   **Search Console API** aktivieren.
2. Unter **APIs & Services → OAuth-Zustimmungsbildschirm** die App einrichten.
   Bei einer externen Test-App deine eigene Google-Adresse als **Testnutzer**
   hinzufügen; die App muss für diesen Zweck nicht veröffentlicht werden.
3. Unter **Anmeldedaten → Anmeldedaten erstellen → OAuth-Client-ID** den
   Anwendungstyp **Desktop-App** wählen und die JSON-Datei herunterladen.
4. Die Datei außerhalb des Repositories ablegen, z. B.
   `~/.config/claude-seo/client_secret.json`, und lokal schützen:

```bash
mkdir -p ~/.config/claude-seo
mv ~/Downloads/client_secret_*.json ~/.config/claude-seo/client_secret.json
chmod 600 ~/.config/claude-seo/client_secret.json
```

Das Google-Konto muss in der Search Console bereits Zugriff auf die
Property haben. **Die JSON-Datei, die OAuth-URL und der Autorisierungscode
gehören nicht in den Chat.**

### 5b. OAuth ausführen

Der lokale Rücksprung des Tools ist `http://localhost:8085`. Den Befehl
auf derselben Maschine ausführen, auf der der Browser läuft – nicht in einer
entfernten Sandbox, wenn deren `localhost` nicht dein Browser-Rechner ist:

```bash
SEO=~/.claude/skills/seo/.venv/bin/python
S=~/.claude/skills/seo/scripts
"$SEO" "$S/google_auth.py" --auth \
       --creds ~/.config/claude-seo/client_secret.json
```

Der Browser öffnet die Google-Einwilligung. Nach „Zulassen" wird das Token
unter `~/.config/claude-seo/oauth-token.json` mit Modus 600 gespeichert; der
Pfad zur Client-Datei wird für spätere Erneuerungen in
`google-api.json` hinterlegt.

> **Berechtigungshinweis zu claude-seo v2.4.2:** Der eingebaute
> `--auth`-Flow fordert technisch die Bereiche `indexing`, `webmasters` und
> `analytics.readonly` an, obwohl die GSC-Abfragen in diesem Runbook nur
> `webmasters.readonly` verwenden. Das ist eine Eigenschaft des installierten
> Tools, nicht eine Notwendigkeit der Search-Analytics-Abfrage. Wenn du diese
> zusätzlichen Einwilligungen nicht geben möchtest, brich den Flow ab und
> nutze stattdessen die untenstehende Dienstkonto-Variante oder ADC mit einem
> gezielt gesetzten Read-only-Scope.

Danach lokal prüfen:

```bash
"$SEO" "$S/google_auth.py" --check gsc
"$SEO" "$S/google_auth.py" --tier
```

`--auth` speichert noch nicht automatisch die bevorzugte Property. Für die
erste Abfrage deshalb die Property explizit angeben; den exakten Wert zuerst
mit `sites` ausgeben lassen.

### 5c. Dienstkonto als engere Alternative

Wenn die zusätzlichen OAuth-Bereiche nicht akzeptabel sind oder die Abfrage
später unbeaufsichtigt laufen soll, ist ein Dienstkonto mit GSC-Leserechten
engmaschiger:

1. Cloud-Projekt öffnen, **Google Search Console API** freischalten.
2. **IAM → Dienstkonten → Dienstkonto erstellen**, JSON-Schlüssel herunterladen.
3. Schlüssel **außerhalb** des Repos ablegen, z. B. `~/.config/claude-seo/gsc-service-account.json`,
   Rechte `chmod 600`.
4. In der Search Console: **Einstellungen → Nutzer und Berechtigungen →
   Nutzer hinzufügen**, die `client_email` aus dem JSON eintragen. Für reine
   Abfragen reicht die niedrigste passende Leseberechtigung.
5. Die Konfiguration ergänzen (vorhandene Felder, etwa `api_key`, erhalten):

```bash
python3 - <<'PY'
import json, os
from pathlib import Path
path = Path.home() / ".config/claude-seo/google-api.json"
try:
    config = json.loads(path.read_text())
except (FileNotFoundError, json.JSONDecodeError):
    config = {}
config.update({
    "service_account_path": str(Path.home() / ".config/claude-seo/gsc-service-account.json"),
    "default_property": "sc-domain:franksfinanzcheck.de",
})
path.write_text(json.dumps(config, indent=2) + "\n")
os.chmod(path, 0o600)
PY
```

`default_property`: `sc-domain:franksfinanzcheck.de` für die
Domain-Property, `https://franksfinanzcheck.de/` für eine
URL-Präfix-Property. Den tatsächlichen Property-Typ ohne Raten mit `sites`
prüfen.

### Abfragen

```bash
# Verfügbare Properties
"$SEO" "$S/gsc_query.py" sites

# Suchanfragen und Seiten, 28 Tage
"$SEO" "$S/gsc_query.py" query -p sc-domain:franksfinanzcheck.de \
       --days 28 --dimensions query,page --limit 1000 --json

# Nur Seiten, mobiler Traffic, Deutschland
"$SEO" "$S/gsc_query.py" query -p sc-domain:franksfinanzcheck.de \
       --dimensions page --device mobile --country DEU --json

# Indexierungsstatus einer einzelnen URL (Property-Wert anpassen)
"$SEO" "$S/gsc_inspect.py" "https://franksfinanzcheck.de/pillar/strom-sparen/" \
       --site-url sc-domain:franksfinanzcheck.de --json
```

Werte aus `--country` folgen ISO 3166-1 **alpha-3**, also `DEU` nicht `DE`.
GSC-Daten sind um etwa zwei bis drei Tage verzögert; aus einem einzelnen
Tag lässt sich kein Trend ableiten.

---

## 6. Bekannte Grenzen

- **Chromium fehlt.** Ohne Chromium funktionieren alle gerenderten
  Prüfungen nicht (Seiten, die JavaScript zum Aufbau brauchen). Nachziehen
  mit `~/.claude/skills/seo/scripts/claude-seo setup` – der Download von
  `cdn.playwright.dev` muss dafür erreichbar sein.
- **Netzwerk abhängig.** Alle Verfahren hier rufen Live-URLs oder
  Google-APIs auf. In eingeschränkten Umgebungen (z. B. dieser Sandbox,
  die nur github.com, npm und PyPI freigibt) laufen sie ins Leere. Auf der
  eigenen Maschine funktionieren sie.
- **Keine Inhaltsänderung durch diese Einrichtung.** Zugangsdaten und
  Drift-Daten liegen unter `~/.config/claude-seo/` bzw.
  `~/.cache/claude-seo/`; die unten genannten Befehle ändern keine
  Templates oder Markdown-Dateien im Blog. Andere claude-seo-Audits können
  je nach Aufruf eigene Reports am angegebenen Ausgabeort erzeugen – deren
  Schreibziel vorher prüfen.

## 7. Bewusst nicht genutzt

Folgende mitgelieferte Teil-Skills passen nicht zu diesem Blog und werden
**nicht** eingerichtet: `seo-ecommerce` (kein Shop), `seo-hreflang`
(einsprachig), `seo-local` und `seo-maps` (kein Standortgeschäft),
`seo-programmatic` (die vorhandene Content-Engine leistet das bereits)
sowie alle kostenpflichtigen Erweiterungen (`seo-ahrefs`, `seo-dataforseo`,
`seo-firecrawl`, `seo-profound`, `seo-seranking`, `seo-matomo`).
`seo-bing` ist kostenlos und wäre ein späterer, kleiner Zusatz – die
Sitemap liegt in den Bing Webmaster Tools bereits bereit.

## 8. Namensähnlichkeit – Verwechslungsgefahr

| Befehl | Bedeutung |
|---|---|
| `npm run seo:audit` | **euer** lokales SEO-Cockpit, Gratis, Build-basiert |
| `npm run seo:check` | dasselbe, Exit 1 bei technischen P1-Funden |
| `/seo audit <url>` | claude-seo, Live-Prüfung, braucht Netz |

Beide bleiben parallel in Betrieb. Vor automatisierten Änderungen gilt
weiterhin: **main deployt auf Produktion.**

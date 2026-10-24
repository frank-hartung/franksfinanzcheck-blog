# Anleitung: Search Console per Dienstkonto automatisieren

Stand: 12.10.2026 · Gilt für `scripts/gsc_import.py` (lesen) und
`scripts/gsc_indexierung.py` (Indexierung anfragen) · ersetzt den Satz „ohne API“ in
[ANLEITUNG-GOOGLE-SEARCH-CONSOLE.md](ANLEITUNG-GOOGLE-SEARCH-CONSOLE.md).

**Was du bekommst:**

1. Täglich aktualisierte, aggregierte Klick- und Impressionszahlen im Repo (`data/gsc/`).
2. Seit 12.10.2026 zusätzlich die **aktive Indexierungs-Anfrage** über die URL Inspection API –
   derselbe Knopf wie „Indexierung beantragen“ in der Oberfläche, nur maschinell.

Die Search Console und ihre API sind kostenlos. Es gibt keine Anmeldung einer Person, keine Cookies
und kein Hochladen von CSV-Dateien.

**Zwei Zugänge, zwei Rechte, ein Dienstkonto.** Der Lese-Import braucht den Scope
`webmasters.readonly` und die Berechtigungsstufe „Eingeschränkt“. Eine Indexierungs-Anfrage ist ein
Schreibvorgang: Sie braucht den Scope `webmasters` und die Stufe **„Vollständig“ (Owner)**. Beide
Scopes sind in den Skripten getrennt hinterlegt – der Lese-Import kann niemals versehentlich mit
Schreibrechten laufen. Was das Dienstkonto **nicht** bekommt: Zugriff auf dein Google-Konto, auf
andere Properties oder auf irgendetwas außerhalb der Search Console.

---

## Schritt 1 – Google-Cloud-Projekt anlegen

1. [console.cloud.google.com](https://console.cloud.google.com) öffnen, mit deinem Google-Konto anmelden.
2. Oben links das Projektmenü → **Neues Projekt** → Name `franksfinanzcheck-gsc` → **Erstellen**.
3. Sicherstellen, dass dieses Projekt oben ausgewählt ist.

## Schritt 2 – Search Console API aktivieren

1. Menü → **APIs & Dienste → Bibliothek**.
2. Nach `Google Search Console API` suchen → öffnen → **Aktivieren**.

## Schritt 3 – Dienstkonto anlegen

1. Menü → **IAM & Verwaltung → Dienstkonten → Dienstkonto erstellen**.
2. Name: `gsc-leser`. Beschreibung: „Search-Console-Daten lesen und Indexierung anfragen für
   franksfinanzcheck.de“. Ein zweites Dienstkonto ist nicht nötig – dieselbe Identität bekommt in
   Schritt 5 die passende Stufe, und die beiden Scopes trennen die Skripte selbst.
3. **Keine Projektrollen vergeben.** Der Zugriff auf die Search Console wird in Schritt 5 erteilt.
4. **Fertig.** Die E-Mail-Adresse des Dienstkontos notieren, sie hat die Form
   `gsc-leser@franksfinanzcheck-gsc.iam.gserviceaccount.com`.

## Schritt 4 – JSON-Schlüssel erzeugen

1. Das eben angelegte Dienstkonto öffnen → Reiter **Schlüssel → Schlüssel hinzufügen → Neuen Schlüssel erstellen**.
2. Typ **JSON** → **Erstellen**. Die Datei wird heruntergeladen.

> **Geheimnis.** Diese Datei ist ein Passwort. Sie gehört **nicht** ins Repo, nicht in einen Chat und nicht in
> E-Mails. Ablage nur in den GitHub-Secrets (Schritt 6) und lokal außerhalb des Repos (z. B. `~/.config/ff/gsc.json`,
> Rechte `600`). Die Datei danach löschen oder sicher verwahren. Bei Verdacht auf Abfluss den Schlüssel sofort
> im Dienstkonto unter **Schlüssel → Löschen** entfernen und einen neuen anlegen.

## Schritt 5 – Dienstkonto in der Search Console freischalten

1. [search.google.com/search-console](https://search.google.com/search-console) öffnen, die Property
   `franksfinanzcheck.de` auswählen (Domain-Property oder URL-Präfix, siehe
   [Search-Console-Anleitung](ANLEITUNG-GOOGLE-SEARCH-CONSOLE.md), Abschnitt 1).
2. Zahnrad **Einstellungen → Nutzer und Berechtigungen → Nutzer hinzufügen**.
3. E-Mail des Dienstkontos aus Schritt 3 eintragen.
4. Berechtigung wählen → **Hinzufügen**.

| Stufe | Lese-Import (`gsc_import.py`) | Indexierungs-Anfrage (`gsc_indexierung.py`) |
|---|---|---|
| **Eingeschränkt** | ✅ reicht | ❌ 403 – Google lehnt jede Anfrage ab |
| **Vollständig** (Owner) | ✅ reicht ebenfalls | ✅ nötig |

**Empfehlung: „Vollständig“.** Ohne diese Stufe läuft der tägliche GSC-Tageslauf zwar grün, der
Schritt „Indexierung anfragen“ meldet aber dauerhaft `keine_berechtigung` – die Site wäre dann
weiter im Zustand „Sitemap hinlegen und warten“, also genau da, wo sie vor dem 12.10.2026 war.

Ohne diesen Schritt antwortet die API mit „403 – keine Berechtigung“, obwohl alles andere stimmt.
`gsc_indexierung.py` prüft die Stufe **vor** der ersten Anfrage und benennt sie im Befund, damit
eine fehlende Berechtigung nie als „kein Zugriff“ durchgeht.

## Schritt 6 – Zugang im Repo-Umfeld hinterlegen

**Lokal** (für Tests):

```bash
export GSC_SITE_URL="sc-domain:franksfinanzcheck.de"    # oder "https://franksfinanzcheck.de/"
export GSC_SERVICE_ACCOUNT_FILE="$HOME/.config/ff/gsc.json"
```

**GitHub** (für den täglichen Lauf): Repo → **Settings → Secrets and variables → Actions**:

| Name | Inhalt |
|---|---|
| `GSC_SERVICE_ACCOUNT_JSON` | kompletter Inhalt der JSON-Datei aus Schritt 4 |
| `GSC_SITE_URL` | `sc-domain:franksfinanzcheck.de` (als *Variable*, nicht als Secret) |

Das Anlegen dieser Werte machst **du** selbst. Der Agent legt keine Geheimnisse an.

## Schritt 7 – Einrichtung prüfen

```bash
python3 scripts/gsc_import.py --sites
```

Erwartete Ausgabe:

```
Sichtbare Properties:
  - sc-domain:franksfinanzcheck.de  (siteOwner)
✅ Einrichtung in Ordnung.
```

`siteOwner` = Stufe „Vollständig“ (Indexierungs-Anfragen funktionieren).
`siteRestrictedUser` = Stufe „Eingeschränkt“ (nur der Lese-Import funktioniert) – dann Schritt 5
wiederholen und die Stufe anheben.

Fehlermeldungen und ihre Ursache:

| Meldung | Ursache | Abhilfe |
|---|---|---|
| `Token-Abruf fehlgeschlagen: invalid_grant` | Uhrzeit des Rechners oder Schlüssel falsch | Uhr synchronisieren, Schlüsselinhalt prüfen |
| `keine Property` / leere Liste | Dienstkonto nicht in Schritt 5 eingetragen | Schritt 5 prüfen; nach dem Eintragen kann es einige Minuten dauern |
| `GSC_SITE_URL ... ist nicht darunter` | Property-Name weicht ab | Exakt den angezeigten Namen verwenden (Domain: `sc-domain:` davor, URL-Präfix mit `https://` und `/`) |
| `Search-Console-API: ... has not been used ... or it is disabled` | API nicht aktiviert | Schritt 2 |

## Schritt 8 – Erstbefüllung und Dauerbetrieb

```bash
python3 scripts/gsc_import.py --backfill        # einmalig: letzte 480 Tage (Google liefert maximal 16 Monate)
python3 scripts/gsc_import.py                   # danach täglich: letzte 90 Tage, überschreibt nur diese Tage

python3 scripts/gsc_indexierung.py --live --plan      # welche Seiten wären heute fällig?
python3 scripts/gsc_indexierung.py --live --dry-run   # Zugang + Berechtigungsstufe prüfen, nichts senden
python3 scripts/gsc_indexierung.py --live             # Indexierung anfragen
```

Beim **ersten** Indexierungs-Lauf sind alle 74 indexierbaren Seiten fällig – sie passen in ein
Tageskontingent von 200. Danach greift die Wiedervorlage: eine indexierte Seite wird nach 28 Tagen
erneut angefragt, eine noch nicht indexierte nach 7, und jede Seite sofort, wenn sich ihr `lastmod`
geändert hat. Unveränderte URLs täglich einzureichen ist genau das, wovor Google in den Richtlinien
warnt – das Kontingent-Gedächtnis (`data/gsc_indexierung_state.json`) verhindert es.

Dateien in `data/gsc/`:

- `tagesdaten.jsonl` – eine Zeile je Tag (Klicks, Impressionen, CTR, Position). **Wächst dauerhaft.**
  Das ist der wichtige Punkt: Google hält nur 16 Monate. Was einmal im Repo steht, bleibt erhalten.
- `top_seiten_28t.json`, `top_suchbegriffe_28t.json` – Top 500 der letzten 28 Tage.
- `meta.json` – Stand, Zeitraum, Status, Hinweis auf Datenschutz.

**Zeitverzögerung:** Google liefert finale Zahlen mit etwa 2–3 Tagen Verzögerung. Der Import endet deshalb
drei Tage vor heute. Aus einem einzelnen Tag kein Trend ableiten.

## Datenschutz

- Gespeichert werden nur Summen je Tag, Seite oder Suchbegriff. Keine Nutzerkennungen, keine IP-Adressen.
- Die Search Console zeigt Suchanfragen aggregiert; seltene Suchanfragen fehlen oder sind anonymisiert.
  Das ist Googles Datenbasis, nicht unsere Erhebung.
- Der Lese-Import schreibt keine Daten zurück zu Google.
- Die Indexierungs-Anfrage übermittelt ausschließlich öffentliche Seiten-URLs dieser Property –
  also Adressen, die ohnehin in der Sitemap stehen. Keine Inhalte, keine Personenbezüge.
- Im Zustand (`data/gsc_indexierung_state.json`) stehen URL, Zeitstempel und die von Google
  gemeldete Abdeckung. Kein Token, kein Schlüsselmaterial – der Selbsttest prüft das ausdrücklich.

## Täglicher Lauf per GitHub Actions (seit 12.10.2026 aktiv)

`.github/workflows/gsc-import.yml` läuft täglich um 05:17 UTC (≈ 07:17 Berlin) und verbindet beide
Hälften: Leistungsdaten holen **und** Indexierung anfragen. Dazu prüft er vorher live, was Google
tatsächlich sieht (`gsc_verifikations_guard.py --nur-live`) – Besitznachweis, robots.txt, Sitemap,
Canonical.

Ohne die Secrets aus Schritt 6 endet der Lauf mit Status `nicht_konfiguriert` und bleibt grün: Ein
noch nicht eingerichtetes Dienstkonto ist ein Zustand, kein Defekt. Verschwiegen wird er nicht – er
steht in der Lauf-Zusammenfassung.

Zwei Wege, bewusst getrennt:

- **Zustand** (`data/gsc_indexierung_state.json`, `.indexnow_submitted.json`) wird direkt auf `main`
  gesichert. Ohne ihn weiß der nächste Lauf nicht, was er schon angefragt hat, und verbrennt das
  Tageskontingent. Beide Pfade stehen in der `STATE_ONLY`-Negativliste des Deploy-Gates: Dieses
  Lebenszeichen löst keinen Livegang aus.
- **Leistungsdaten** (`data/gsc/`) gehen als PR. Das sind Kennzahlen, die du liest und einordnest;
  ein automatischer Merge würde unbemerkt Zahlen in den Bestand schreiben, die niemand geprüft hat.

Die frühere Vorlage unter `docs/workflow-vorlagen/gsc-import.yml` ist damit überholt und entfernt:
Eine Vorlage neben dem scharfen Workflow ist eine zweite Wahrheit über denselben Ablauf.

## Indexierungs-API: Abgrenzung und Grenzen

Die URL Inspection API ist **nicht** die „Google Indexing API“. Diese gilt ausschließlich für Seiten
mit `JobPosting`- oder `BroadcastEvent`-Schema; sie für einen Ratgeber-Blog zu benutzen wäre ein
Richtlinienverstoß und würde die Property riskieren. Die URL Inspection API ist für eine normale
Website der einzige offizielle maschinelle Weg – sie fragt den Indexierungsstatus ab und bittet um
erneutes Crawlen.

| Grenze | Wert | Wie das Skript damit umgeht |
|---|---|---|
| Anfragen je Property und Tag | 200 | Kontingent-Gedächtnis, 5 Anfragen Sicherheitsabstand, Wiedervorlage-Fristen |
| Anfragen je Minute | 600 | 0,2 s Abstand zwischen zwei Anfragen (20× darunter) |
| Berechtigung | „Vollständig“ (Owner) | Vorcheck über die Property-Liste, bevor die erste Anfrage rausgeht |
| HTTP 429 | Kontingent erschöpft | Lauf bricht ab, statt die übrige Queue weiter zu traktieren |
| HTTP 403 | Berechtigung zu niedrig | Status `keine_berechtigung` mit der konkreten Abhilfe |

Eine Anfrage ist **kein** Indexierungsversprechen. Google entscheidet weiterhin selbst; die API
macht aus „irgendwann“ ein „geprüft, mit Begründung“.

## Selbsttest (ohne Zugang, ohne Netz)

```bash
python3 scripts/gsc_import.py --selftest
```

Prüft: echte RS256-Signatur mit `openssl` (Gegenprobe mit `openssl dgst -verify`), Paginierung, Merge
der Tage, Geheimnisschutz in `meta.json`, Status „nicht konfiguriert“.

## Wenn ein Artefakt kaputt ist: die Wache und ihr Heilweg (24.10.2026)

Am 21.10.2026 hat Git drei Dateien aus `data/gsc/` **als Text** zusammengeführt.
Danach trug `meta.json` vier `stand`-Schlüssel in einem Objekt, und in den
Top-Listen standen zwei Läufe ohne Trennkomma hintereinander. Vier Tage lang war
das `Integritäts-Siegel` für **jeden** Pull-Request rot – die Annotation nannte
nur `.github#30 – Process completed with exit code 1`.

### 1. Messen

```bash
python3 scripts/gsc_artefakte_guard.py --check
```

Vier Prüfungen, alle hart:

| Prüfung | Frage |
|---|---|
| **G1** | Ist `meta.json` vollständig und plausibel (Pflichtfelder, `stand` als ISO-UTC, `zeitraum.von <= bis`, `status` bekannt)? |
| **G2** | Tragen beide Top-Listen genau die Schlüssel des Erzeugers, Zahlen in gültigen Bereichen – und ist jeder Suchbegriff/jede Seite **nur einmal** enthalten? |
| **G3** | Ist jede Ledger-Zeile gültig und läuft das Datum **streng aufsteigend ohne Doppel**? |
| **G4** | Passt der Kopf zu den Zahlen (`zeitraum.bis` nicht hinter dem letzten Tag, `tage_gesamt` nicht über der Zahl der gemessenen Tage)? |

G2/G3/G4 sind der Grund, warum diese Wache existiert: Zwei **gültige** Top-Listen
hintereinander sind weiterhin gültiges JSON. Nur die Bedeutung ist kaputt.

Der Selbsttest (`--selftest`, 20 Fälle) sabotiert jede dieser Klassen in einem
temporären Baum und beweist, dass die Wache anschlägt – auch, dass sie **nicht**
anschlägt, wenn wirklich alles in Ordnung ist (C15: ein Prüf-Aufruf heilt nie).

### 2. Heilen – nur mit Beleg

```bash
# a) jede Datei für sich: jüngster Stand im Git, der die volle Prüfung besteht
python3 scripts/gsc_artefakte_guard.py --heal

# b) besser: EIN Lauf = EINE Messung, alle Kopfdaten aus demselben Commit
python3 scripts/gsc_artefakte_guard.py --heal --rev <sha>
```

Was die Heilung **nie** tut:

- Sie rekonstruiert nichts. Ein zusammengesetztes Artefakt lässt sich nicht
  zurückrechnen, ohne Zahlen zu erfinden; ohne belegbaren Stand bleibt der Fund
  stehen (Exit 1).
- Sie rollt den **Tagesledger nie zurück**. `tagesdaten.jsonl` ist append-only:
  Jeder Tag ist eine eigene Messung, die durch einen Merge nicht falsch wird.
- Sie schreibt kein Teilstück. Besteht eine der drei Kopfdaten im gewählten
  Commit die Prüfung nicht, wird **keine** geschrieben – ein halber Gesamtstand
  wäre schlimmer als der Befund.
- Sie schreibt nicht, ohne danach erneut zu prüfen („signiert, ohne zu messen“
  ist im Repo keine Option).

### 3. Verhindern – die drei Schichten

| Schicht | Wo | Wirkung |
|---|---|---|
| **Struktur** | `.gitattributes`: `data/gsc/*.json merge=binary` | Git kann die Dateien nicht mehr als Text zusammensetzen; bei parallelen Änderungen bleibt **ein** vollständiger Stand. Der Ledger (`*.jsonl merge=union`) ist bewusst ausgenommen – Tage sind unabhängige Messungen. |
| **Bedeutung** | `scripts/gsc_artefakte_guard.py` in `integrity-lock.yml` und in `gsc-import.yml` **vor** jedem Commit | Kein kaputtes Artefakt verlässt den schreibenden Lauf; jeder PR prüft den Bestand zusätzlich zur Syntax. |
| **Herkunft** | `--heal --rev`, `scripts/tests/test_gsc_artefakte.py` | Die Reparatur ist belegbar, und `regression` prüft die echten Dateien bei jeder Änderung unter `data/gsc/**`. |

Der alte Befund bleibt nachlesbar:
`GSC-DATEN-INTEGRITAET-HIGHEND-2026-10-24.md` (Ursache, Belege, Grenzen).

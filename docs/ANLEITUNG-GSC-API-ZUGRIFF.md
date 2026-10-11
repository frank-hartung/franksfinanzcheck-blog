# Anleitung: Search Console per Dienstkonto automatisiert auslesen

Stand: 11.10.2026 · Gilt für `scripts/gsc_import.py` · ersetzt den Satz „ohne API“ in
[ANLEITUNG-GOOGLE-SEARCH-CONSOLE.md](ANLEITUNG-GOOGLE-SEARCH-CONSOLE.md).

**Was du bekommst:** Täglich aktualisierte, aggregierte Klick- und Impressionszahlen im Repo
(`data/gsc/`). Die Search Console und ihre API sind kostenlos. Es gibt keine Anmeldung einer Person,
keine Cookies und kein Hochladen von CSV-Dateien.

**Was du nicht bekommst:** Keine Schreibrechte. Das Dienstkonto liest nur.

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
2. Name: `gsc-leser`. Beschreibung: „Liest Search-Console-Daten für franksfinanzcheck.de (nur lesen)“.
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
4. Berechtigung **Eingeschränkt** wählen (reicht zum Lesen; „Vollständig“ ist nicht nötig) → **Hinzufügen**.

Ohne diesen Schritt antwortet die API mit „403 – keine Berechtigung“, obwohl alles andere stimmt.

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
  - sc-domain:franksfinanzcheck.de  (siteRestrictedUser)
✅ Einrichtung in Ordnung.
```

Fehlermeldungen und ihre Ursache:

| Meldung | Ursache | Abhilfe |
|---|---|---|
| `Token-Abruf fehlgeschlagen: invalid_grant` | Uhrzeit des Rechners oder Schlüssel falsch | Uhr synchronisieren, Schlüsselinhalt prüfen |
| `keine Property` / leere Liste | Dienstkonto nicht in Schritt 5 eingetragen | Schritt 5 prüfen; nach dem Eintragen kann es einige Minuten dauern |
| `GSC_SITE_URL ... ist nicht darunter` | Property-Name weicht ab | Exakt den angezeigten Namen verwenden (Domain: `sc-domain:` davor, URL-Präfix mit `https://` und `/`) |
| `Search-Console-API: ... has not been used ... or it is disabled` | API nicht aktiviert | Schritt 2 |

## Schritt 8 – Erstbefüllung und Dauerbetrieb

```bash
python3 scripts/gsc_import.py --backfill    # einmalig: letzte 480 Tage (Google liefert maximal 16 Monate)
python3 scripts/gsc_import.py               # danach täglich: letzte 90 Tage, überschreibt nur diese Tage
```

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
- Der Import schreibt keine Daten zurück zu Google.

## Ausblick: täglicher Lauf per GitHub Actions

Die Workflow-Vorlage liegt unter [`docs/workflow-vorlagen/gsc-import.yml`](workflow-vorlagen/gsc-import.yml).
Sie wird **nicht** automatisch aktiv. Umsetzung per Pull Request, nach deiner Freigabe.

## Selbsttest (ohne Zugang, ohne Netz)

```bash
python3 scripts/gsc_import.py --selftest
```

Prüft: echte RS256-Signatur mit `openssl` (Gegenprobe mit `openssl dgst -verify`), Paginierung, Merge
der Tage, Geheimnisschutz in `meta.json`, Status „nicht konfiguriert“.

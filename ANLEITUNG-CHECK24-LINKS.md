# 🔗 Anleitung: Deine persönlichen CHECK24-Links in allen Artikeln einsetzen

Deine Artikel verlinken aktuell direkt auf die CHECK24-Kategorieseiten – **ohne deine persönliche Partner-ID bekommst du keine Provision**. Mit diesem Skript stellst du alle Artikel in 3 Minuten um.

---

## So funktioniert es

Ein kleines Skript (`scripts/set_check24_links.py`) ersetzt alle Standard-Check24-Links durch **deine persönlichen Links**. Du musst nur einmal eine Liste mit deinen Links anlegen.

## Schritt 1 – Deine persönlichen CHECK24-Links sammeln

Hole dir im CHECK24-Partnerportal (bzw. im Affiliate-Netzwerk, über das du angemeldet bist) deine persönlichen Partnerlinks – einen pro Kategorie:

- Strom, Gas, DSL, Girokonto, Kredit, Kfz-Versicherung, Reisen, Mietwagen, Flüge
- plus einen allgemeinen Link für Artikel ohne feste Kategorie (Frugalismus, 50-30-20, finanzielle Freiheit)

> Deine Links sehen z. B. so aus: `https://www.check24.de/strom/?partner=DEINE-ID` – Hauptsache, es sind **deine** Links mit deiner Partner-ID.

## Schritt 2 – Konfigurationsdatei anlegen (~2 Min.)

```bash
cp scripts/check24_links.example.yaml scripts/check24_links.yaml
```

Öffne `scripts/check24_links.yaml` und ersetze bei **jeder** Zeile den Platzhalter `DEIN-LINK` durch deinen persönlichen Link:

```yaml
links:
  allgemein: "https://www.check24.de/?partner=DEINE-ID"
  strom: "https://www.check24.de/strom/?partner=DEINE-ID"
  gas: "https://www.check24.de/gas/?partner=DEINE-ID"
  # … usw.
```

> 🔒 **Wichtig:** Die Datei `scripts/check24_links.yaml` steht in `.gitignore` – deine Partner-ID wird also **nie** ins Repository committet. Nur die Beispiel-Vorlage wird mitcommittet.

## Schritt 3 – Vorschau (ändert nichts)

```bash
python3 scripts/set_check24_links.py --dry-run
```

Du siehst, wie viele Links pro Artikel ersetzt würden und ob alle Kategorien abgedeckt sind.

## Schritt 4 – Ersetzen (ein Befehl)

```bash
# Alle Artikel umstellen:
python3 scripts/set_check24_links.py

# Zusätzlich den Themenpool umstellen (damit künftige Bot-Artikel direkt deine Links enthalten):
python3 scripts/set_check24_links.py --topics
```

## Schritt 5 – Prüfen & hochladen

```bash
# Kontrolle: Wie viele persönliche Links sind drin? (sollte ~19 sein)
grep -rch "partner=DEINE-ID" content/posts/ | paste -sd+ | bc

# Alles committen und pushen (GitHub Pages baut automatisch neu):
git add -A
git commit -m "affiliate: persönliche CHECK24-Links in allen Artikeln eingesetzt"
git push
```

---

## 🤖 Damit auch der BOT deine Links nutzt

Der Bot erzeugt täglich neue Artikel-Entwürfe. Damit die **auch** deine persönlichen Links enthalten, gibt es zwei Wege:

**Weg 1 – Themenpool (empfohlen):**
Einfach `python3 scripts/set_check24_links.py --topics` ausführen (Schritt 4). Dann nutzt der Bot automatisch deine Links aus `data/topics.yaml` (`affiliate_url`-Einträge).

**Weg 2 – Repository-Variable (für Artikel ohne Kategorie):**
GitHub → Repo → **Settings → Secrets and variables → Actions → Variables → New repository variable**
- Name: `AFFILIATE_URL`
- Wert: dein allgemeiner persönlicher CHECK24-Link

> **Reihenfolge im Bot:** pro Thema gilt `affiliate_url` aus `topics.yaml` → sonst `AFFILIATE_URL` (Variable) → sonst Standard-Link.

---

## ❓ Häufige Fragen

**Muss ich das nach jedem neuen Artikel wiederholen?**
Nein – wenn du den Themenpool (`--topics`) umgestellt hast, enthalten neue Bot-Artikel automatisch deine Links. Nur selbst geschriebene Artikel musst du ggf. manuell anpassen.

**Kann ich das Skript bedenkenlos mehrfach ausführen?**
Ja. Es ist idempotent: Bereits ersetzte Links werden erkannt und nicht doppelt ersetzt (zweiter Lauf meldet „0 ersetzt").

**Wie teste ich, ob die Links funktionieren?**
Link in einem privaten Browserfenster öffnen: Er muss auf CHECK24 weiterleiten und in der Adressleiste deine Partner-ID enthalten. Den ersten Test-Kauf am besten mit einem kleinen Betrag machen.

**Was, wenn ich meine Links später ändere?**
Einfach in `scripts/check24_links.yaml` die neuen Links eintragen und Schritt 4 erneut ausführen.

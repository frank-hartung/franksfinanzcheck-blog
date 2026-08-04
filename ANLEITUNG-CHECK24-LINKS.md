# 🔗 Anleitung: Deine persönlichen CHECK24-Links – mit nur einer Partner-ID

Deine Artikel verlinken aktuell direkt auf die CHECK24-Kategorieseiten – **ohne deine persönliche Partner-ID bekommst du keine Provision**. Ein kleines Skript setzt deine Partnerlinks in **allen** Artikeln automatisch ein. Du brauchst nur **eine** Zahl: deine CHECK24-Partner-ID.

---

## Schritt 1 – Partner-ID finden (einmalig)

Deine CHECK24-Partner-ID ist die **Ziffernfolge** in deinem persönlichen Empfehlungslink aus dem CHECK24-Partnerprogramm:

```
https://www.check24.de/?pi=123456789
                          └──┬───┘
                     DEINE Partner-ID
```

> **Falls dein Link ein anderes Format hat** (z. B. `?partner=…` statt `?pi=…`): Das Skript erkennt das automatisch, wenn du ihm **einen** Beispiel-Link gibst (siehe Schritt 2, Variante B).

## Schritt 2 – Links einsetzen (ein Befehl)

**Variante A – nur die ID (Standard):**
```bash
# Vorschau (ändert nichts):
python3 scripts/set_check24_links.py --id 123456789 --dry-run

# Alle Artikel ersetzen:
python3 scripts/set_check24_links.py --id 123456789
```

**Variante B – Beispiel-Link (falls dein Format anders ist):**
```bash
python3 scripts/set_check24_links.py --beispiel "https://www.check24.de/?pi=123456789"
```
Das Skript erkennt Parameter und ID aus diesem einen Link und baut daraus automatisch alle Kategorien-Links (Strom, Gas, DSL, Girokonto, Kredit, Kfz, Reisen, Mietwagen, Flüge + allgemein).

**ID dauerhaft speichern (danach reicht ein Aufruf ohne Argumente):**
```bash
python3 scripts/set_check24_links.py --id 123456789 --save
python3 scripts/set_check24_links.py          # nutzt die gespeicherte ID
```

## Schritt 3 – Auch den Bot versorgen (empfohlen)

```bash
python3 scripts/set_check24_links.py --id 123456789 --topics
```
Damit werden auch die Links im Themenpool (`data/topics.yaml`) ersetzt – **alle künftigen Bot-Artikel enthalten automatisch deine Partnerlinks**.

## Schritt 4 – Prüfen & hochladen

```bash
# Kontrolle: Wie viele persönliche Links sind drin? (sollte ~19 sein)
grep -rc "pi=123456789" content/posts/ | grep -v ":0" | wc -l

# Alles committen und pushen (GitHub Pages baut automatisch neu):
git add -A
git commit -m "affiliate: persönliche CHECK24-Links in allen Artikeln eingesetzt"
git push
```

---

## ℹ️ So funktioniert das Skript

- Ersetzt alle Standard-Links (`https://www.check24.de/strom/` usw.) durch deine persönlichen Links (`https://www.check24.de/strom/?pi=DEINE_ID`)
- **Idempotent:** Beim zweiten Aufruf passiert nichts („0 ersetzt") – keine doppelten Parameter
- **Sicher:** Deine ID wird in `scripts/check24_id.txt` gespeichert, die in `.gitignore` steht – sie wird **nie** ins Repository committet
- **Kontrolle:** Am Ende meldet das Skript, falls ein Link übrig geblieben ist
- `--dry-run` zeigt vorab alles an, ohne etwas zu ändern

## ❓ Häufige Fragen

**Muss ich das nach jedem neuen Artikel wiederholen?**
Nein – wenn du einmal `--topics` ausgeführt hast, enthalten künftige Bot-Artikel automatisch deine Links.

**Wie teste ich, ob die Links funktionieren?**
Link in einem privaten Browserfenster öffnen: Er muss auf CHECK24 weiterleiten und `?pi=DEINE_ID` in der Adressleiste enthalten. Den ersten Test-Kauf am besten mit einem kleinen Betrag machen.

**Kann ich das Skript bedenkenlos mehrfach ausführen?**
Ja – bereits ersetzte Links werden erkannt und übersprungen.

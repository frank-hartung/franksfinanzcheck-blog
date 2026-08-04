# 🔗 Anleitung: Awin-Links in allen Artikeln auf einmal einsetzen

Deine Artikel verlinken aktuell direkt auf `check24.de` – **ohne deine Partner-ID bekommst du keine Provision**. Mit dieser Anleitung stellst du alle Artikel in 5 Minuten um.

---

## Schritt 1 – Awin-Links erzeugen (einmalig, ~10 Min.)

1. Melde dich im [Awin-Konto](https://www.awin.com/) an
2. Suche den Advertiser **CHECK24** → öffne das Partnerprogramm
3. Gehe auf **„Links" / „Deep Links"** und erzeuge **pro Kategorie einen Link** (Strom, Gas, DSL, Girokonto, Kredit, Kfz, Reisen, Mietwagen, Flüge)
4. Ein Awin-Link sieht so aus:
   `https://www.awin1.com/cread.php?awinmid=1234567&p=https%3A%2F%2Fwww.check24.de%2Fstrom%2F`
   (Die Zahl nach `awinmid=` ist deine persönliche Partner-ID)

> 💡 Alternativ: CHECK24 stellt Partnern auch einen eigenen Link-Generator im Partnerportal zur Verfügung – die Links dort funktionieren genauso.

## Schritt 2 – Mapping-Datei ausfüllen (~2 Min.)

```bash
cp scripts/affiliate_links.example.yaml scripts/affiliate_links.yaml
```

Öffne `scripts/affiliate_links.yaml` und ersetze bei **jeder** Zeile `DEINE_AWIN_ID` durch deine echte ID. Die Datei enthält bereits alle 10 Kategorien, die im Blog vorkommen:

| Alte URL (im Artikel) | Kommt vor in |
|---|---|
| `check24.de/strom/` | Stromfresser, Stromwechsel |
| `check24.de/gas/` | Gastarife, Heizperiode |
| `check24.de/dsl/` | DSL-Flat, WLAN, DNS |
| `check24.de/girokonto/` | Girokonto, Notgroschen |
| `check24.de/kredit/` | Ratenkredit |
| `check24.de/kfz-versicherung/` | Kfz-Artikel |
| `check24.de/reisen/` | Last Minute, Urlaubskasse |
| `check24.de/mietwagen/` | Mietwagen-Artikel |
| `check24.de/fluege/` | Flüge-Artikel |
| `check24.de/` (allgemein) | Frugalismus, 50-30-20, finanzielle Freiheit |

## Schritt 3 – Vorschau anzeigen (nichts wird geändert)

```bash
python3 scripts/replace_affiliate_links.py --dry-run
```

Du siehst, wie viele Links pro Artikel ersetzt würden und ob alle abgedeckt sind.

## Schritt 4 – Ersetzen (ein Befehl)

```bash
python3 scripts/replace_affiliate_links.py
```

Falls du auch den **Themenpool** (für künftige Bot-Artikel) umstellen willst:

```bash
python3 scripts/replace_affiliate_links.py --topics
```

## Schritt 5 – Prüfen & hochladen

```bash
# Kontrolle: keine direkten check24-Links mehr (außerhalb von awin1.com-Links)
grep -rn "check24.de" content/posts/ | grep -v awin1.com

# Alles committen und pushen (GitHub Pages baut automatisch neu)
git add -A
git commit -m "affiliate: Awin-Links in allen Artikeln eingesetzt"
git push
```

---

## 🤖 Damit auch der BOT künftig deine Links nutzt

Der Bot erzeugt ab jetzt täglich neue Artikel-Entwürfe. Damit die **auch** direkt deine Awin-Links enthalten, gibt es zwei Wege:

**Option A – Repository-Variable (für generische Artikel):**
GitHub → Repo → **Settings → Secrets and variables → Actions → Variables → New repository variable**
- Name: `AFFILIATE_URL`
- Wert: dein allgemeiner Awin-Link (z. B. auf `check24.de/`)

**Option B – Themenpool (empfohlen, pro Kategorie genau):**
In `data/topics.yaml` stehen bei vielen Themen `affiliate_url:`-Einträge mit direkten check24-Links. Einfach `scripts/replace_affiliate_links.py --topics` ausführen (Schritt 4) – dann nutzt der Bot automatisch die Awin-Links.

> **Reihenfolge im Bot:** pro Thema gilt `affiliate_url` aus `topics.yaml` → sonst `AFFILIATE_URL` (Variable) → sonst Platzhalter.

---

## ❓ Häufige Fragen

**Muss ich das nach jedem neuen Artikel wiederholen?**
Nein – wenn du den Themenpool (Option B) umgestellt hast, nutzen neue Bot-Artikel automatisch deine Links. Nur selbst geschriebene Artikel musst du ggf. manuell anpassen.

**Wie teste ich, ob die Links funktionieren?**
Link in einem privaten Browserfenster öffnen: Er muss auf CHECK24 weiterleiten und in der Adressleiste deine `awinmid` enthalten. Den ersten Test-Kauf am besten mit einem kleinen Betrag machen.

**Was, wenn ich meine Partner-ID später ändere?**
Einfach in `scripts/affiliate_links.yaml` die neue ID eintragen und Schritt 4 erneut ausführen – die Ersetzung funktioniert auch rückwärts (Awin-Link → neuer Awin-Link).

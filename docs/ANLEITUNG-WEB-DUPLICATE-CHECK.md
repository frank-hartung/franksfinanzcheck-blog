# ANLEITUNG: Web-Duplikat-Suche einrichten (optional, kostenlos)

`scripts/web_uniqueness_guard.py` kann jeden Artikel per Exakt-Phrasen-Suche
gegen das gesamte Web prüfen (Profi-Level-Duplikat-Check, wie es auch
kostenpflichtige Tools wie Copyscape im Kern tun). Ohne Einrichtung läuft
das Skript sauber weiter – nur dieser eine Baustein wird übersprungen (die
technische Duplicate-Content-Prüfung der eigenen Website und die
Indexierungs-Prüfung laufen immer, ganz ohne API-Key).

**Kosten:** kostenlos bis 100 Suchanfragen/Tag (Google Programmable Search
Engine). Bei ~10 Artikeln × 2 Phrasen pro Wochenlauf werden davon nur ein
Bruchteil verbraucht.

## Schritt 1: Programmable Search Engine anlegen (~2 Minuten)

1. Gehe zu [programmablesearchengine.google.com](https://programmablesearchengine.google.com/)
2. **Neue Suchmaschine erstellen**
3. Bei „Durchsuchen" **„Das gesamte Web durchsuchen"** aktivieren (wichtig –
   sonst wird nur eine bestimmte Website durchsucht)
4. Suchmaschine erstellen → in den Einstellungen die **Suchmaschinen-ID**
   (Feld „cx") kopieren

## Schritt 2: Custom Search API aktivieren + Key erzeugen (~2 Minuten)

1. Gehe zu [console.cloud.google.com/apis/library/customsearch.googleapis.com](https://console.cloud.google.com/apis/library/customsearch.googleapis.com)
2. Falls nötig, ein (kostenloses) Google-Cloud-Projekt anlegen
3. **API aktivieren**
4. Unter *APIs & Dienste → Anmeldedaten* → **API-Schlüssel erstellen**

## Schritt 3: In GitHub hinterlegen

Repo → *Settings → Secrets and variables → Actions*:

| Typ | Name | Wert |
|---|---|---|
| Secret | `GOOGLE_CSE_API_KEY` | dein API-Schlüssel aus Schritt 2 |
| Variable | `GOOGLE_CSE_CX` | deine Suchmaschinen-ID aus Schritt 1 |

**Fertig.** Der nächste Lauf von `web_uniqueness_guard.py` nutzt automatisch
den Web-Duplikat-Check.

## Wie es funktioniert

- Aus jedem veröffentlichten Artikel werden 2 unverwechselbare ~12-Wort-
  Phrasen entnommen (keine Standardsätze/CTA-Boxen).
- Jede Phrase wird als Exakt-Zitat (`"..."`) über die Google-Suche
  abgefragt.
- Taucht ein Treffer auf einer **fremden** Domain auf (nicht
  franksfinanzcheck.de), wird das gemeldet.
- Ergebnisse werden 3 Wochen zwischengespeichert (`data/web_uniqueness_cache.json`),
  damit dasselbe Freikontingent nicht unnötig verbraucht wird.

## Lokale Tests

```bash
export GOOGLE_CSE_API_KEY=dein_key
export GOOGLE_CSE_CX=deine_cx_id
python3 scripts/web_uniqueness_guard.py --dry-run
```

## FAQ

- **Was, wenn ich das Kontingent überschreite?** Die Google-API antwortet
  dann mit einem Fehler pro Anfrage – das Skript protokolliert das im
  Cache und bricht nicht ab, versucht es beim nächsten Lauf erneut.
- **Findet das Skript wirklich alle Kopien?** Nein – es ist eine
  stichprobenartige Prüfung (2 Phrasen pro Artikel), kein vollständiger
  Volltextabgleich wie bei kostenpflichtigen Profi-Tools. Für die meisten
  Blogs ist das aber ein realistischer, kostenloser Kompromiss.

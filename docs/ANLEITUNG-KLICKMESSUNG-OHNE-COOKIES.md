# Anleitung: Klickmessung ohne Cookies (Eigenbetrieb)

> **Stand 14.10.2026 (Sicherheitsaudit M-13): Messung AUS.** `stats.franksfinanzcheck.de` existiert nicht, deshalb senden die `/go/`-Seiten keinen Beacon mehr. Einschalten erst, wenn der Worker läuft: (1) Worker deployen und Custom Domain `stats.` anlegen, (2) in `data/klickmessung.yaml` `aktiv: true` setzen, (3) `python3 -c "import sys; sys.path.insert(0,'scripts'); import affiliate_shield as a; a.generate_go_pages(a.load_registry())"` ausführen und committen. Datenschutzerklärung und `click_chain_guard` folgen dem Schalter automatisch.

Stand: 11.10.2026 · Status: **vorbereitet, nicht live.** Die Einführung braucht deine Freigabe,
eine Datenschutz-Prüfung (siehe Abschnitt 7) und die Anpassung der Datenschutzerklärung.

Dieses Dokument beschreibt die Messung der Partnerklicks ohne Fremdanbieter. Eine Reichweitenmessung durch
einen Drittanbieter gibt es auf dem Blog nicht mehr (abgeschaltet am 11.10.2026).

---

## 1. Was gemessen wird – und was nicht

| | Wird gemessen | Wird **nicht** gemessen |
|---|---|---|
| Ereignis | Aufruf einer `/go/<key>/`-Übergabeseite | Bestätigung beim Partner, Abschluss, Umsatz |
| Zuordnung | Gateway-Schlüssel (z. B. `strom`), Artikel-Slug aus `subid` | Person, Gerät, Browser, Herkunft |
| Speicherung | **Tagessumme** je Schlüssel und Artikel in D1 | Einzelklicks, Zeitstempel, IP, User-Agent, Referrer |
| Gerät | nichts wird auf dem Gerät gespeichert | Cookies, localStorage, Fingerabdruck |
| Einwilligung | DNT und GPC werden respektiert: dann keine Zählung | – |

**Wichtig für die Auswertung:** Gezählt wird der Aufruf der Übergabeseite. Ob der Partner den Klick
annimmt, zeigt diese Messung nicht. Zahlen daher nicht als „Abschlüsse“ bezeichnen.

## 2. Architektur

```
Artikel ─► /go/<key>/?subid=<artikel> ─► Beacon (navigator.sendBeacon, im Generator scripts/affiliate_shield.py)
                                              │  POST https://stats.franksfinanzcheck.de/e   (JSON, 1 Zeile)
                                              ▼
                              Cloudflare Worker "klick-zaehler"  (cloudflare/klick-zaehler/worker.js)
                                  · Origin-Allowlist · DNT/GPC · Kill-Switch KLICKS_AUS · Schlüssel-Prüfung
                                              │  INSERT … ON CONFLICT DO UPDATE  (ein Zähler je Tag/Schlüssel/Artikel)
                                              ▼
                              Cloudflare D1 "ff-klicks", Tabelle klicks (PK: tag, go_key, artikel)
                                              │  täglich (GitHub Actions, Vorlage)
                                              ▼
                              scripts/klick_import.py ─► data/klicks_eigen.json ─► scripts/click_attribution.py
```

- Der Beacon-Code liegt **im Generator**. Die HTML-Dateien unter `static/go/` werden erzeugt, nicht von
  Hand bearbeitet.
- Die Weiterleitung zum Partner läuft unabhängig von der Zählung. Schlägt der Beacon fehl, merkt der
  Besucher nichts.
- Die Domain `stats.franksfinanzcheck.de` ist eine eigene Subdomain über eine Custom Domain des Workers.
  Die GitHub-Pages-Einträge für Apex und `www` bleiben unverändert (siehe
  [DNS-CLOUDFLARE-GITHUB-PAGES.md](DNS-CLOUDFLARE-GITHUB-PAGES.md)).

## 3. Einrichtung (einmalig, von dir)

Voraussetzung: Cloudflare-Konto, die Domain liegt bei Cloudflare-DNS (laut Repo-Doku der Fall).

**3.1 Wrangler anmelden**

```bash
cd cloudflare/klick-zaehler
npx wrangler login
```

**3.2 D1-Datenbank anlegen**

```bash
npx wrangler d1 create ff-klicks
```

Die ausgegebene `database_id` in `cloudflare/klick-zaehler/wrangler.toml` eintragen (ersetzt `EINTRAGEN-NACH-wrangler-d1-create`).
Die ID ist kein Geheimnis, sie gehört ins Repo. Der Zugriff ist durch das Token geschützt. Das ist eine Änderung über einen Pull Request, nicht direkt auf `main`.

**3.3 Schema anlegen**

```bash
npx wrangler d1 execute ff-klicks --remote --file=schema.sql
```

**3.4 Worker deployen**

```bash
npx wrangler deploy
```

Die Route `stats.franksfinanzcheck.de` wird als Custom Domain eingerichtet.

**3.5 Funktionstest**

```bash
curl -i https://stats.franksfinanzcheck.de/healthz
# erwartet: HTTP/2 200, Body "ok"

curl -i -X POST https://stats.franksfinanzcheck.de/e \
  -H 'Origin: https://franksfinanzcheck.de' -H 'Content-Type: text/plain' \
  --data '{"k":"strom","s":"testlauf-bitte-loeschen"}'
# erwartet: HTTP/2 204

curl -i -X POST https://stats.franksfinanzcheck.de/e \
  -H 'Origin: https://evil.example' -H 'Content-Type: text/plain' --data '{"k":"strom"}'
# erwartet: HTTP/2 403 (fremde Herkunft wird abgewiesen)
```

Den Testklick danach löschen:

```bash
npx wrangler d1 execute ff-klicks --remote --command "DELETE FROM klicks WHERE artikel='testlauf-bitte-loeschen'"
```

**3.6 Rate-Limit (empfohlen)** – im Cloudflare-Dashboard unter *Security → WAF → Rate limiting rules*:
Pfad `/e`, z. B. 120 Anfragen pro Minute und Client. Cloudflare nutzt dafür intern die IP. Diese Regel
speichert sie nicht im Repo. Im Datenschutz-Entwurf (Abschnitt 7) erwähnen.

**3.7 GitHub-Secrets für den Import** (nur Lesezugriff):

| Name | Inhalt |
|---|---|
| `CLOUDFLARE_ACCOUNT_ID` | Account-ID aus dem Dashboard (rechte Seitenleiste) |
| `CLOUDFLARE_API_TOKEN` | Token mit **nur** *Account › D1 › Read* |

Die Datenbank-ID steht in `wrangler.toml` (Abschnitt 3.2), nicht mehr als Secret. Der Import ruft D1 über `wrangler d1 execute --remote --json` auf (Wrangler ist devDependency des Workers, `npm ci` in `cloudflare/klick-zaehler`).

Token anlegen: Dashboard → *My Profile → API Tokens → Create Custom Token*. Nur das Recht „D1 Read“.
Die Werte legst du selbst an. Der Agent legt keine Geheimnisse an.

**3.8 Lokaler Import-Check**

```bash
(cd cloudflare/klick-zaehler && npm ci)
export CLOUDFLARE_ACCOUNT_ID=… CLOUDFLARE_API_TOKEN=…
python3 scripts/klick_import.py --tage 30
```

Ohne Zugangsdaten oder mit noch eingetragenem Platzhalter in `wrangler.toml` endet der Import mit Status `nicht_konfiguriert` und Exit 0. Das ist kein Fehler. Schlägt der Abruf fehl (z. B. Token-Recht), steht der Grund im Status `fehler`; das Token wird dabei nicht ausgegeben.

## 4. Betrieb

**Täglicher Import:** `scripts/klick_import.py` schreibt `data/klicks_eigen.json` (Format von
`click_attribution.py`) und `data/klicks_eigen.meta.json`. `click_attribution.py` nutzt diese Datei bevorzugt,
sobald sie Daten enthält.

**Drift-Check:** Die Schlüsselliste im Worker (`gateway-keys.mjs`) entspricht der Registry
`scripts/check24_links.yaml`. Nach jeder Änderung an der Registry ausführen:

```bash
python3 scripts/klick_import.py --bake-keys     # Liste neu erzeugen
python3 scripts/klick_import.py --pruefe-keys   # Exit 1 bei Abweichung
cd cloudflare/klick-zaehler && npm test
```

**Tests:**

```bash
python3 scripts/klick_import.py --selftest
python3 scripts/click_attribution.py --selftest
cd cloudflare/klick-zaehler && npm test
```

## 5. Kill-Switch (Notschalter)

Es gibt drei Stufen. Die Seiten funktionieren in allen drei Fällen weiter.

1. **Sofort, ohne Deploy:** Im Dashboard die Custom Domain `stats.franksfinanzcheck.de` vom Worker lösen.
   Der Beacon schlägt dann still fehl.
2. **Per Konfiguration:** `KLICKS_AUS = "1"` in `wrangler.toml` setzen und `npx wrangler deploy`. Dann
   zählt der Worker nichts mehr (204 ohne Speicherung).
3. **Dauerhaft:** Beacon-Zeilen aus dem Generator entfernen (`scripts/affiliate_shield.py`), dann
   `static/go/` neu erzeugen. Das ist ein Pull Request.

Hinweis: Eine Dashboard-Variable wird beim nächsten `wrangler deploy` aus `wrangler.toml` überschrieben.
Für einen dauerhaften Stopp deshalb Stufe 1 oder 3 wählen.

## 6. Grenzen (Kosten und Limits)

- Cloudflare Workers Free: 100.000 Anfragen pro Tag. D1 Free: 100.000 Schreibvorgänge pro Tag, 5 GB.
  Die Werte stammen aus der Anbieter-Dokumentation und sind vor dem Livegang auf der Preisseite
  erneut zu prüfen.
- Überschreitung führt zu Fehlern, nicht zu Abrechnung. Die Zählung bricht dann für den Rest des Tages
  ab. Die Seiten laufen weiter.
- Bei heutigem Umfang (42 Artikel, Partnerlinks) liegt die Last weit unter den Grenzen.
- Der Umzug auf einen bezahlten Tarif ist möglich, wenn die Zahlen es rechtfertigen.

## 7. Datenschutz – Prüfpunkte und Textvorschlag (Entwurf)

**Vor Livegang durch eine Rechtsberatung zu prüfen:**

1. Rechtsgrundlage für die Zählung (z. B. berechtigtes Interesse nach Art. 6 Abs. 1 lit. f DSGVO) und
   die Abwägung dazu.
2. Ob der Zugriff auf Endgeräteinformationen nach TDDDG § 25 eine Einwilligung braucht. Der Beacon
   speichert nichts auf dem Gerät. Ob das für die Einordnung genügt, ist juristisch zu bestätigen.
3. Auftragsverarbeitung mit Cloudflare und Drittlandübermittlung (Standardvertragsklauseln) prüfen.
4. Die Datenschutzerklärung und ggf. den Generator (siehe
   [CHECKLISTE-DATENSCHUTZ-GENERATOR.md](CHECKLISTE-DATENSCHUTZ-GENERATOR.md)) anpassen.

**Textvorschlag für die Datenschutzerklärung (Entwurf, nicht veröffentlicht):**

> **Zählung von Partnerlinks.** Wenn du auf einen Partnerlink klickst, zählen wir den Aufruf unserer
> Übergabeseite anonym. Wir erfassen dabei nur Tagessummen je Partnerangebot und Artikel. Es wird kein
> Cookie gesetzt und nichts auf deinem Gerät gespeichert. Wir speichern weder deine IP-Adresse noch eine
> Kennung. Die Anfrage wird technisch über Cloudflare, Inc. ausgeliefert; Cloudflare verarbeitet dafür
> die übliche Verbindungsinformation als Auftragsverarbeiter. Wenn dein Browser „Do Not Track“ oder
> „Global Privacy Control“ meldet, zählen wir nicht. Rechtsgrundlage: berechtigtes Interesse an einer
> anonymen Erfolgsmessung unserer Angebote (Art. 6 Abs. 1 lit. f DSGVO). *[Rechtsprüfung ausstehend]*

## 8. Abnahme-Checkliste vor dem Livegang

- [ ] Rechtsprüfung (Abschnitt 7) abgeschlossen, Datenschutzerklärung angepasst
- [ ] D1 angelegt, `database_id` per PR eingetragen, Schema eingespielt
- [ ] Worker deployt, `/healthz` = 200, Testklick = 204, fremde Herkunft = 403, Testzeile gelöscht
- [ ] Löschlauf aktiv: Cron-Trigger `17 3 * * *` (wrangler.toml, Abschnitt `[triggers]`) im Dashboard unter Worker → Trigger sichtbar; Löschfrist 13 Monate, Stichtag = gleicher Kalendertag vor 13 Monaten (Europe/Berlin)
- [ ] Rate-Limit-Regel gesetzt
- [ ] GitHub-Secrets (3.7) angelegt
- [ ] Erster `klick_import.py --tage 30` gegen die echte D1 gelaufen (Status `ok`). Falls Wrangler mit „D1 Read“ 403 meldet, braucht das Token zusätzlich „D1 Edit“. Dann Recht anpassen und dokumentieren.
- [ ] `npm test` und beide Selbsttests grün
- [ ] Beacon-PR gemerged, `static/go/` neu erzeugt, Gates grün (`affiliate_integrity_gate.py`)
- [ ] Erster Import mit echten Daten, `click_attribution.py` zeigt Quelle `data/klicks_eigen.json`

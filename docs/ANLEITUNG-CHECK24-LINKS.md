# 🔗 Anleitung: CHECK24- & Tarifcheck-Links (zentrale Pflege)

Die Affiliate-Links dieses Blogs liegen **zentral** in
`scripts/check24_links.yaml`. Alle Artikel verlinken über das eigene
Gateway `https://franksfinanzcheck.de/go/<kategorie>/` – Artikel selbst
bleiben sauber und unabhängig von PID/Deep-Änderungen.

**Wichtig:** Die frühere Anleitung mit `scripts/set_check24_links.py` ist
**nicht mehr gültig** (das Skript existiert nicht mehr). Änderungen nimmt
man heute ausschließlich in `scripts/check24_links.yaml` vor.

---

## 1. Partner-Pfad prüfen / aktualisieren

Öffne `scripts/check24_links.yaml` und passe die Werte an:

```yaml
strom: "https://a.check24.net/misc/click.php?pid=80968&aid=18&deep=stromanbieter-wechseln&cat=1&utm_source=franksfinanzcheck&utm_medium=affiliate&utm_campaign=strom"
```

- **CHECK24:** `.../misc/click.php?pid=<PID>&aid=<AID>&deep=<kategorie>`
- **Tarifcheck:** `.../click.php?partner_id=<PID>&ad_id=15&deep=<kategorie>`
- Tracker, die die UTM-Parameter nicht akzeptieren, werden von der
  Wochenwache automatisch auf den bekannten Zustand zurückgeheilt.

**Merkregel:** `pid=80968`/`partner_id=47086` kommen aus deinem
Partner-Dashboard. Deep-Pfade aus dem Partnerprogramm (PDF) verwenden –
**niemals** Kategorien erraten.

## 2. Gateway (/go/) neu generieren

```bash
python3 scripts/affiliate_shield.py --fix
```

- erzeugt/aktualisiert alle `static/go/<kategorie>/index.html`
- jedes Gateway hat `noindex,nofollow,noarchive`
- der Bot-Wächter `affiliate_health.py` prüft E2E, dass jede Route auf
  die richtige Kategorie und die richtige PID zeigt.

## 3. Bestehende Artikel abgleichen (falls nötig)

```bash
python3 scripts/affiliate_link_check.py --fix
python3 scripts/affiliate_profi_check.py --fix
```

- `affiliate_link_check.py` ersetzt generische CTAs durch passende
  Deep-Links und prüft Kategorie/PID.
- `affiliate_profi_check.py` stellt Offenlegung, E-E-A-T, Trust-Box und
  CTA-Slots sicher.

## 4. Neue Bot-Artikel

Der Content-Bot liest die Kategorie-Zuordnung ebenfalls aus
`data/pinterest_plan.yaml` (`check24_kategorie`) und rückt sie vor dem
Speichern in das `/go/`-Gateway um. Ein Ändern von
`scripts/check24_links.yaml` wirkt also sofort auf alle **neuen** Artikel;
für Bestand reicht Schritt 2 + 3.

## 5. Verifizieren

```bash
# 0) Pflicht zuerst: Sehtest der Wache (Exit 2 = Detektor blind, fail-closed)
python3 scripts/affiliate_integrity_gate.py --selftest

# 1) Jede im Blog verwendete /go/-Route muss im Register stehen,
#    jeder Link muss im gebauten HTML erscheinen (AI1-AI5, heilt sofort)
python3 scripts/affiliate_integrity_gate.py

# 2) E2E-Kette (Redirect-Ziel, Kategorie, PID, Gateway-Drift)
python3 scripts/affiliate_health.py --no-net
```

Die Integritäts-Wache läuft zusätzlich **täglich automatisch**
(Actions → „Affiliate-Integritäts-Wache (täglich)", 06:00 MESZ) und beweist:

| Prüfung | Beweis |
|---|---|
| AI1 | vollständiger Markdown-Link in jeder CTA-Zeile (kein Dangling) |
| AI2 | nur registrierte `/go/<key>/`, keine rohen Partner-URLs im Content |
| AI3 | kein verstümmelter Text an der CTA |
| AI4 | jeder Link steht **schlüsselgenau** im gebauten HTML – mit `rel="sponsored"` und Klick-Attribution |
| AI5 | jede `/go/<key>/`-Seite leitet `noindex` auf exakt die registrierte Partner-URL weiter |

Exit-Codes: `0` grün · `1` Inhaltsschaden offen · `2` Werkzeugfehler
(Beweis nicht möglich → es wird **nichts** veröffentlicht).
Shortcode-CTAs (`tarifvergleich`, `einspartabelle`) laufen über
`layouts/_partials/affiliate_anchor_attrs.html` – dort gilt derselbe Vertrag.
Hintergrund: `AFFILIATE-INTEGRITY-GATE-REPORT.md` · Tagesreport:
`AFFILIATE-INTEGRITY-REPORT.md`.

Test im Browser: `https://franksfinanzcheck.de/go/strom/` sollte auf
Check24 mit deiner PID weiterleiten und die Seite
`https://franksfinanzcheck.de/go/strom/` selbst darf **keinen** Index
bekommen (Quelle: `robots.txt` + `<meta name="robots" content="noindex,...">`).

---

## FAQ

**Ändert sich der Link pro Kategorie?**
Ja – jede Kategorie hat einen eigenen `deep`-Pfad. Der Blog verwendet pro
Thema genau die passende Kategorie statt eines generischen Portals.

**Muss ich Artikel-Handarbeit machen?**
Nein. Die Artikel verlinken nur `/go/<kategorie>/` und bleiben damit
vollständig unabhängig von PID/Deep-Änderungen.

**Wie testet man einen Link?**
Link in einem privaten Browserfenster öffnen: Er muss auf die richtige
Check24-Kategorie mit deiner PID weiterleiten. Ersten Test-Kauf am besten
mit kleinem Betrag.

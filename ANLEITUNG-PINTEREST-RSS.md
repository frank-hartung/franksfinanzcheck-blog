# 📌 ANLEITUNG: Blogartikel per RSS automatisch an Pinterest senden

**Ziel:** Neue Blogartikel erscheinen automatisch als Pins auf Pinterest –
ohne manuelles Pinnen, über Pinterests eigene „Auto-publish"-Funktion.

**Stand:** 20.08.2026 · Feed-URL: `https://franksfinanzcheck.de/index.xml`

---

## 1. Was wurde technisch geändert?

RSS war am 10.08.2026 deaktiviert (`disableKinds = ["RSS"]`). Für die
Pinterest-Automatisierung wurde es wieder aktiviert – **Pinterest-freundlich**:

| Änderung | Wirkung |
|---|---|
| `hugo.toml` → `disableKinds` entfernt | RSS wird wieder erzeugt |
| `hugo.toml` → `[outputs]` | nur der **Home-Feed** `/index.xml` (keine Sektions-Feeds) |
| `hugo.toml` → `[services.rss] limit = 50` | Feed enthält bis zu 50 Artikel |
| `layouts/_default/rss.xml` (neu) | Pinterest-optimiertes Template |

**Das neue Feed-Template liefert pro Artikel:**
- `<title>` → Pin-Titel
- `<description>` → Pin-Beschreibung (deine Meta-Description)
- `<enclosure>` + `<media:content>` + `<media:thumbnail>` → **Cover-Bild**
  (2:3, 1000×1500 – exakt das Pinterest-Format)
- nur **Blog-Artikel** (Section `posts`) – keine Rechts-/Pillar-Seiten

> Pinterest unterstützt **RSS 2.\*** und **RSS 1.\*** – **kein Atom**. Hugos
> RSS ist 2.0 → kompatibel.

---

## 2. Dateien ins Repo laden

1. `hugo.toml` → **ersetzen** (Repo-Wurzel)
2. `layouts/_default/rss.xml` → **neu anlegen** im Ordner `layouts/_default/`
   (Ordner existiert bereits; falls nicht: anlegen)

Nach dem Push baut der Deploy automatisch → Feed liegt dann unter:
`https://franksfinanzcheck.de/index.xml`

**Kontrolle:** Im Browser `https://franksfinanzcheck.de/index.xml` öffnen →
es erscheint die XML-Liste aller Artikel.

---

## 3. Pinterest: Auto-publish einrichten (native, kostenlos)

**Voraussetzungen:**
- Pinterest-**Business-Konto**
- Deine Website ist bei Pinterest **verifiziert (claimed)**:
  Settings → „Claimed accounts"/„Verifizierte Website" → `franksfinanzcheck.de`

**Schritte:**
1. Pinterest öffnen → **Menü (oben rechts)** → **Settings**
2. Links: **„Create Pins in bulk"** (Pins in großen Mengen erstellen)
3. Unter **„Auto-publish"** → **„Connect RSS feed"**
4. Feed-URL einfügen: `https://franksfinanzcheck.de/index.xml`
5. Unter **„Save Pins to"** das gewünschte **Board** wählen
6. **Save**

**Verhalten (laut Pinterest):**
- Neue Artikel im Feed → innerhalb von **24 h** automatisch gepinnt
- Beim ersten Verbinden werden die **vorhandenen** Artikel gepinnt
  (älteste zuerst, Limit **200 Pins/Tag** – bei dir aktuell 10 → kein Problem)
- Jeder Artikel braucht einen Link auf deine **claimed** Domain → erfüllt ✅

---

## 4. Alternativen (Third-Party, falls du mehr Kontrolle willst)

| Tool | Vorteil | Hinweis |
|---|---|---|
| **Publer** | RSS-Auto-Posting, günstig ($12/Monat), Bulk + Recycling | gut für „Budget-Mehrfachposting" |
| **Buffer** | einfachste Queue, $6/Kanal | solide, aber ohne Recycling |
| **Zapier / Make** | flexible Logik (z. B. erst Prüfen, dann pinnen) | ab Free-Plan alle 15 Min |

Alle lesen denselben Feed `https://franksfinanzcheck.de/index.xml`.

---

## 5. ⚠️ Wichtig: Doppel-Pins vermeiden!

Dein Blog hat **bereits** zwei Pinterest-Automatisierungen:
- `pinterest-ai.yml` → `pinterest_engine.py --auto` (2× täglich)
- `repin-weekly.yml` → `generate_pins.py` (montags)

Wenn du **zusätzlich** den RSS-Auto-publish aktivierst, wird jeder neue Artikel
**mehrfach** gepinnt (API + RSS). Deshalb: **genau einen** Weg wählen.

| Variante | Empfehlung |
|---|---|
| **A – RSS-only** (einfach & robust, first-party) | RSS-Auto-publish aktivieren + API-Auto-Posting abschalten (Workflows deaktivieren oder alle Artikel auf `pinned: true` setzen) |
| **B – API-only** (hat Pin-Text-Optimierung, Hashtags, Rotation) | bestehende Automatisierung behalten, RSS **nur als Feed** nutzen (kein Auto-publish verbinden) |

**Profi-Empfehlung:** Variante **A**. Pinterests native Funktion ist
wartungsarm (kein Token-Refresh, keine Skripte) – heute hatten wir ja gesehen,
wie anfällig die eigene Pinterest-API-Kette sein kann.

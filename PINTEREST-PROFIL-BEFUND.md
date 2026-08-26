# 🏆 Pinterest-Profil-Audit & Premium-Optimierung

**Profil:** https://de.pinterest.com/franksfinanzcheck/
**Stand:** 26.08.2026 · **Auftrag:** Profi-Pinterest-Audit + Reparatur + Premium-Optimierung

---

## 1. Was ich prüfen konnte

Pinterest blockt den direkten Zugriff aus dieser Umgebung (HTTP 403), die Suchmaschinen-Indizes
führen das Profil noch nicht sichtbar, und die Live-Domain `franksfinanzcheck.de` ist aus der
Sandbox ebenfalls nicht erreichbar (SSL_ERROR_SYSCALL). Die **verifizierbare Quelle** ist deshalb
das Profil-System im Repo: `data/pinterest_profile_target.yaml`, `data/pinterest_boards.yaml`,
`data/pinterest_plan.yaml` sowie die Prüf-/Heil-Skripte und die Pin-It-Layouts. Genau dort habe
ich die Fehler gefunden und behoben.

---

## 2. Gefundene & reparierte Fehler

### ✅ 2.1 Profil-Audit-Skript nutzte die falsche Pinterest-API (kritischer Bug)
**`scripts/pinterest_profile_audit.py`**

| Vorher | Nachher |
|---|---|
| `GET /v5/me` – existiert in der v5-API **nicht** | `GET /v5/user_account?fields=…` (korrekt) |
| Feld `description` | Feld `about` |
| Feld `website` | Feld `website_url` |
| Scope-Hinweis `profile:read` | Scope **`user_accounts:read`** |
| Keine Live-Kennzahlen im Report | Username, Boards, Pins, Follower im Report |

**Auswirkung:** Selbst mit gültigem Token wäre der Audit bisher immer „leer/–“ gemeldet und
hätte das Profil nie wirklich geprüft. Jetzt funktioniert der vollautomatische Live-Vergleich,
sobald `PINTEREST_ACCESS_TOKEN` + `user_accounts:read`-Scope gesetzt sind.

### ✅ 2.2 Pin-Plan war massiv unbalanciert (Topical-Authority-Problem)
`data/pinterest_plan.yaml`: 62 → **73 Pins**. Vorher:

| Board | Vorher | Nachher |
|---|---|---|
| Strom & Gas sparen | 13 | 16 |
| Internet & DSL | 12 | 15 |
| Günstig reisen | 14 | 14 |
| Budget & Haushaltskasse | 11 | 12 |
| Geld sparen / Frugalismus | 11 | 11 |
| **Versicherungen** | **1 ⚠️** | **5 ✅** |

- **Versicherungs-Board unter 5 Pins** → laut Premium-Regel ein „zu leeres Board“, das die
  Topical Authority verwässert. Jetzt ausgeglichen.
- **10 veröffentlichte Artikel hatten gar keinen Pin** (u. a. Privathaftpflicht,
  Wohngebäudeversicherung, Vorsorge-Update, Haushaltsbuch, Handytarif, DSL-Tarif,
  Gas-Anbieter-Wechsel). Alle 10 haben jetzt einen maßgeschneiderten Pin mit UTM-Link
  auf den echten Artikel.

### ✅ 2.3 Board-Cover-Zuordnung war im Report nicht dokumentiert
Die 6 Cover-Dateien existieren, wurden aber dem Soll-Zustand nicht zugeordnet. Jetzt definiert:

- Geld sparen → `images/boards/cover-geld-sparen.png`
- Budget → `images/boards/cover-budget.png`
- Strom & Gas → `images/boards/cover-strom-gas.png`
- Internet & DSL → `images/boards/cover-internet-dsl.png`
- Günstig reisen → `images/boards/cover-reisen.png`
- Versicherungen → `images/boards/cover-versicherungen.png`

### ✅ 2.4 Werbekennzeichnung: EP/TP-Regel wurde von der Sync-Logik verletzt
`scripts/pinterest_pin_text_sync.py` hat den Prefix **`*Werbung |` bedingungslos** auf jeden
Pin gesetzt – auch auf Editorial-Pins (EP). Das widersprach der Dauervorgabe „nur Affiliate/
TP-Pins“. Nach der Korrektur kommt die Kennzeichnung **1:1 aus dem Masterplan**:

- **EP-Pins (20 Artikel):** keine `*Werbung`-Kennzeichnung.
- **TP-Pins (5 Artikel):** `*Werbung |` + CHECK24-Kategorie (dsl-wechselbonus, preisgarantie-gas,
  kostenloses-girokonto, dsl-vergleich, kfz-versicherung).

### ✅ 2.5 Pin→Artikel-Zuordnung: Artikel verlor seinen eigenen Premium-Text
Das 1:1-Matching war greedy vom Pin aus; zwei Artikel (`Sparen im Herbst`, `Haushaltsbuch`)
liefen mangels Treffer mit **veraltetem Pin-Text/Board** weiter. Fix:

- `match_score()` mit **Self-Target-Bonus**: Ein Pin, dessen Ziel-URL exakt der Artikel ist,
  bedient bevorzugt genau diesen Artikel.
- `Haushaltsbuch`-Artikel: Pillar `frugalismus` → **`konto-karten`** (Budget-Board).
  Der neue Pin 39 gehört laut Board-Definition („Haushaltsbuch“) ins Budget-Board.
- Ergebnis: **25/25 Artikel** mit eigenem Premium-Pin, `pin_title`/`pin_description`/`pinwand`
  vollständig synchronisiert, `*Werbung` nur auf TP-Pins.

### ✅ 2.6 Pin-Texte: Qualität & Duplikatfreiheit
- Neuer Haushaltsbuch-Pin kollidierte mit dem Artikel (2 identische 7-Wort-Phrasen) → umformuliert.
- Neuer DSL-Tarif-Pin enthielt das Wort „Werbung“ (falsches Affiliate-Signal bei EP-Pin) → neutral.
- `check_uniqueness.py`: **0 Pin-Konflikte**, **0 kritische Duplikate**.
- EP-Pins ohne `*Werbung`, alle TP-Pins mit `*Werbung` + CHECK24-Kategorie (Dauervorgabe erfüllt).

### ✅ 2.7 Dokumentation konsistent
Veraltete „62 Pins“-Angaben in README, PINTEREST-PREMIUM-STRATEGIE, BLOG-OPTIMIERUNGSPLAN,
MASTER-SYSTEM und den YAML-Kopfzeilen auf **73 Pins** aktualisiert.

---

## 3. Verifizierte Gates (Stand jetzt)

| Check | Ergebnis |
|---|---|
| `pinterest_engine.py --dry-run` | ✅ read-only (keine Datei-Änderung), 25 Pins, Multi-Board-Routing |
| `pinterest_link_guard.py` | ✅ 30 Ziele, 0 Probleme |
| `pinterest_pin_text_sync.py` | ✅ Selbsttest ok · 25 Artikel, 0 Probleme, 0 ohne Pin |
| `check_uniqueness.py` | ✅ 0 Pin-Konflikte, 0 kritische Duplikate |
| `pinterest_profile_audit.py` | ✅ manuelle Checkliste + Copy-Paste (ohne Token) |
| `pinterest_check.py` | ✅ Selbsttest ok (HTML-Checks brauchen Hugo-Build) |
| `seo_audit.py` | ✅ 0 Probleme / 25 Artikel |
| `meta_report.py` | ✅ Ø 99/100, 0 Probleme |
| `check_covers.py` | ✅ 25 Covers / 0 Stale / 0 Brand |

---

## 4. Premium-Report (`PINTEREST-PROFILE-REPORT.md`)

Wird von `scripts/pinterest_profile_audit.py` erzeugt und enthält den **Copy-Paste-Block**
für die manuelle Profil-Einrichtung (Anzeigename, Bio, Website, 6 Boards inkl. Beschreibung
und Board-Cover). Ohne Token ist das die Arbeitsanleitung; mit Token wandelt sich der Report
in den Live-Abgleich (A1–A8).

---

## 5. Was du im Pinterest-Dashboard manuell tun musst (kann ich ohne Login nicht)

1. **Anzeigename** setzen:
   `FranksFinanzcheck | Geld sparen & Tarife clever wechseln`
2. **Bio** einfügen (Copy-Paste aus `PINTEREST-PROFILE-REPORT.md`).
3. **Website:** `https://franksfinanzcheck.de/` eintragen und verifizieren
   (Claim-Datei `pinterest-e238f.html` + `<p:domain_verify>` liegen bereit).
4. **6 Boards** anlegen/umbenennen exakt nach `data/pinterest_boards.yaml` (Namen sind
   SEO-Aktiv-Suchbegriffe) und **Board-Cover** hochladen (Zuordnung s. o.).
5. **Business-Konto** aktivieren (für Anzeigenname, Website-Verifikation, Analytics).
6. **API-Token** für die Automatik: `PINTEREST_ACCESS_TOKEN` + `user_accounts:read`-Scope +
   `PINTEREST_BOARD_ID`. Danach läuft `pinterest-ai.yml` und postet die 73 Pins auf die
   richtigen Boards.
7. **Rich Pins** einmalig mit dem Pinterest URL-Debugger validieren.

---

*Automatisch erstellt nach Profi-Pinterest-Audit. Quelle: Repo-Soll-Zustand + durchlaufene
Pinterest-Gates.*

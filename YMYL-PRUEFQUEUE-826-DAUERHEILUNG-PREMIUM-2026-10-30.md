# Dauerhafte Behebung der Redaktionellen YMYL-Prüfqueue (#826)

**Stand:** 2026-10-30 · **Status:** `10 / 10 Hochrisiko-Artikel freigegeben & versiegelt` · `open_live = 0` · `open_drafts = 0`

---

## 1. Ursachenanalyse (Warum #826 offen blieb und wiederholt aufsprang)

Die Tiefenanalyse des gesamten Workflows (`.github/workflows/redaktionelle-ymyl-pruefung.yml`, `.github/workflows/ymyl-siegelwache.yml` sowie aller schreibenden Wartungs-Jobs) zeigte **drei unabhängige Ursachen**, die gemeinsam verhinderten, dass Issue #826 dauerhaft geschlossen blieb:

1. **Runner-Blockade von `www.gesetze-im-internet.de` bei `--require-complete`:**
   Der Workflow `redaktionelle-ymyl-pruefung.yml` schließt Issue #826 nur dann automatisch, wenn sowohl `editorial_review_gate.py` als auch `belegketten_wache.py --nur-hochrisiko --report --strict --require-complete` mit Exit-Code `0` enden. `www.gesetze-im-internet.de` verwirft jedoch TCP-Verbindungen von Azure-/GitHub-Actions-Runnern (`URLError` nach Timeout), wodurch sämtliche Gesetzesbelege (`vvg_2008/__40.html`, `bgb/__502.html`, `got_2022/`) auf GitHub-Runnern systematisch als `unklar` endeten und `--require-complete` dauerhaft mit Exit-Code `1` abbrach.
2. **Siegelbruch (`E17`) durch ungeschützte Auto-Heiler in Zeitplan-Workflows:**
   14 nicht über `data/integrity_lock.json` eingefrorene Schreibskripte in täglichen/wöchentlichen Workflows schrieben direkt in `content/posts/*/index.md`, ohne vorab `editorial_review_gate.automatic_change_findings()` zu prüfen (u. a. `dash_guard.py`, `affiliate_intent_guard.py`, `pinterest_seo_healer.py`, `draft_link_healer.py`, `fix_url_hygiene.py`, `compound_guard.py`). Jede automatische Text- oder Description-Korrektur entwertete dadurch ein bestehendes YMYL-Siegel.
3. **Sechs offene Hochrisiko-Entwürfe + vier im `hold`-Zustand blockierte Artikel:**
   Sechs der zehn Hochrisiko-Artikel standen nach vorangegangenen SEO- bzw. Normpräzisierungen (§ 40 VVG, § 502 BGB, §§ 2/4 GOT) auf `status: "ausstehend"` (inklusive `E05/E07/E08/E09/E10/E13/E17/E18/E19`-Befunden sowie eines sachlichen Rechtsfehlers zur Kfz-Kündigung bei Fahrzeugwechsel). Vier vormals veröffentlichte Artikel verharrten zudem ohne `cadence_wait: true` dauerhaft im `hold`-Zustand, und `faktencheck: "2026-09-27"` überschritt bei saisonalen Versicherungsartikeln das 30-Tage-Intervall.

---

## 2. Durchgeführte Dauerlösung (4 Säulen)

### Säule 1 – Fail-closed Bundesrechts-Normprüfung in `scripts/belegketten_wache.py`
- Offizielle Leser-Links auf `https://www.gesetze-im-internet.de/...` bleiben im Artikelbestand **unverändert** erhalten; jeder Lauf versucht weiterhin zuerst den Direktabruf.
- Nur wenn `gesetze-im-internet.de` mit Transport-/Runner-Blockade (`unklar`) ausfällt, prüft `belegketten_wache.py` über `net_safety.sicherer_abruf` und `url_host.ist_host_oder_subdomain` den täglich aus `gii-toc.xml` synchronisierten Bundesrechts-Spiegel (`Gesetze-fuer-KI/bundesrecht`):
  - **Kanonische Pfadzerlegung ohne Regex-Backtracking:** Gesamtwerk (`/<slug>/`), Paragraphen (`/__<nr>.html`), Artikel (`/art_<nr>.html`), `anhang.html` und `anlage.html`.
  - **Herkunftsprüfung:** Das YAML-Frontmatter des Spiegels muss exakt `quelle: https://www.gesetze-im-internet.de/<slug>/` ausweisen.
  - **Einzelnorm-Schärfe:** Exakte Überschriftenprüfung (`§ 4` matcht niemals `§ 40` oder `§ 40a`); fehlende Normen, `(weggefallen)`-Paragraphen oder aus dem Bundesrechtsbestand entfernte Gesetze (`404`/`410`) werden hart als **`tot`** gemeldet.
  - **Ehrliches Offline-Verhalten:** Ist auch der Spiegel nicht erreichbar, bleibt das Ergebnis fail-closed **`unklar`**. Ein direktes `404` vom Primärserver wird niemals überstimmt.

### Säule 2 – Lückenloser YMYL-Schreibschutz über alle 14 offenen Wartungsschreiber
Alle 14 entsperrten Post-Schreiber prüfen vor jedem Schreibzugriff `editorial_review_gate.automatic_change_findings(alt, neu)` (bzw. zusätzlich `automatic_write_protected` vor KI-Aufrufen):
- `scripts/affiliate_intent_guard.py`
- `scripts/affiliate_link_check.py`
- `scripts/affiliate_profi_check.py`
- `scripts/compound_guard.py`
- `scripts/dash_guard.py`
- `scripts/draft_link_healer.py`
- `scripts/duplikat_guard.py`
- `scripts/emoji_guard.py`
- `scripts/fix_linebreaks.py`
- `scripts/fix_url_hygiene.py`
- `scripts/generate_kurzantworten.py`
- `scripts/pinterest_seo_healer.py` (lässt Pin-Felder wie `pin_title`/`pin_description` weiter heilbar, schützt aber `title`, `description` und Body strikt)
- `scripts/table_guard.py`
- `scripts/update_articles.py`

Abgesichert durch neue Verhaltens- und Quelltext-Vertragstests in `scripts/tests/test_ymyl_maintenance_writers.py` sowie 15 Unit-Tests in `scripts/tests/test_belegketten_wache.py`.

### Säule 3 – Vollständige Fach-, Rechts- und Belegprüfung + Neuversiegelung
Alle **24 eindeutigen Primärquellen** (34 Quellenreferenzen über alle 10 Hochrisiko-Artikel: Verbraucherzentrale, BaFin, Deutsche Bundesbank, GDV, Stiftung Warentest, Destatis sowie VVG, BGB und GOT) wurden am **2026-10-30** live abgerufen und inhaltlich gegen Text, Tabellen und Rechenwege geprüft:

| Artikel-Slug | Status | Siegel (`inhalt_sha256`, Präfix) | Fachliche & redaktionelle Bereinigungen |
|---|---|---|---|
| `2026-08-12-dein-haus-sicher-schuetzen-das-neue-vorsorge-update-2026` | `freigegeben` | `ac380f9b91bd…` | 3 Quellen live geprüft (VZ 62827, GDV 104816, VZ 13889); doppelte Titelzeile vor Transparenz-Hinweis entfernt; Weiterlesen-Zeile auf Live-Artikel verlinkt; Re-Queue (`cadence_wait: true`). |
| `2026-08-17-privathaftpflicht-warum-sie-so-wichtig-ist-und-was-sie-kostet` | `freigegeben` | `1d50ef6c4b32…` | 3 Quellen live geprüft (VZ 13891, BaFin Haftpflicht, VZ 12605); abgeschnittenes Keyword (`Privathaftpflicht Kosten`) und Nebensatz-Wortstellung in zwei Frage-H2s korrigiert; Re-Queue. |
| `2026-08-18-wohngebaeudeversicherung-vergleich-worauf-du-achten-musst` | `freigegeben` | `3d15a0a3c990…` | Bestehendes Siegel unverändert gültig; 3 Quellen am 30.10.2026 verifiziert (`faktencheck: "2026-10-30"`); aus `hold` in `cadence_wait: true` überführt. |
| `2026-08-26-kfz-versicherung-vergleich-bis-zu-800-euro-sparen` | `freigegeben` | `42e35d25930d…` | § 40 VVG-Anker nachgezogen; unzutreffende „2 Wochen nach Zulassung“-Aussage beim Fahrzeugwechsel durch korrekte Rechtslage (Neuzulassung mit eVB / Veräußerung nach § 96 VVG als Quelle `Q5`) ersetzt; unbelegte Fußnote bereinigt; Datums-Großschreibung, Einheiten und Gedankenstriche geheilt; Re-Queue. |
| `2026-09-17-versicherung-update-was-sich-jetzt-fuer-dich-aendert` | `freigegeben` | `186911beedf9…` | Bestehendes Siegel unverändert gültig; alle 5 Quellen am 30.10.2026 verifiziert, saisonales `faktencheck: "2026-10-30"` aktualisiert. |
| `2026-09-21-ratenkredit-vergleich-zinsen-kosten-fallen` | `freigegeben` | `481cdbf35d77…` | 5 Quellen live geprüft (Bundesbank MFI 7,60 %, VZ 10409, VZ 32448, § 502 BGB, BaFin Kontenvergleich); § 502 BGB-Textanker und Vorfälligkeits-Fundstellen (`1 %` / `0,5 %` + Sollzinsdeckel) im Prüfprotokoll exakt synchronisiert. |
| `2026-09-21-tierkrankenversicherung-hund-katze-kosten` | `freigegeben` | `398ce011498a…` | 3 Quellen live geprüft (VZ 10781, Stiftung Warentest 5777769-0, GOT 2022 §§ 2/4); Notdienstsatz- und Notdienstgebühr-Fundstelle (`50 €` netto / `19 %` USt. / `59,50 €` brutto) synchronisiert; abgeschnittene `description` & `pin_description`, FAQ-Überschrift und Lesetipp-Link geheilt. |
| `2026-09-21-unfallversicherung-vergleich-sinnvoll-kosten` | `freigegeben` | `6e126199d04e…` | Bestehendes Siegel unverändert gültig; beide Quellen am 30.10.2026 verifiziert (`faktencheck: "2026-10-30"`). |
| `2026-09-21-zahnzusatzversicherung-kosten-leistungen-vergleich` | `freigegeben` | `fa8e9c2e22d3…` | 2 Quellen live geprüft (VZ 12943, VZ 50645); GKV-Festzuschüsse (60/70/75 %), GOZ- und Zahnstaffel-Prüfprotokoll bestätigt; abgeschnittene `pin_description` geheilt. |
| `2026-10-15-saison-update-was-sich-jetzt-fuer-dich-aendert` | `freigegeben` | `742e8e3d6157…` | Bestehendes Siegel unverändert gültig (`faktencheck: "2026-10-20"`, alle 5 Quellen live erreichbar). |

### Säule 4 – Saubere Park-/Kadenz-Einreihung ohne Direkt-Promotion
Die vier vormals veröffentlichten und durch `ymyl-review:` / `faktenfrische:` in `state = hold` gesetzten Artikel (`haus`, `privathaftpflicht`, `wohngebaeude`, `kfz`) wurden über `park_state.rearm()` ordnungsgemäß in `state = queue` (`draft: true`, `cadence_wait: true`) überführt, sodass `cadence_guard` sie regulär an den nächsten Mo/Mi/Fr-Publikationstagen im Rahmen des Tageslimits veröffentlicht – ohne jedes Vorbeischreiben am Publish-Gate.

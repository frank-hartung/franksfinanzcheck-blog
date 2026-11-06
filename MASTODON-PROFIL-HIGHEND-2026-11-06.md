# 🐘 Mastodon-Profil Highend-Update – vollständig auf die Mo/Mi/Fr-Publikationsroutine ausgerichtet

**Datum:** 06.11.2026 · **Auftrag:** Frank · **Level:** Profi-Agentur · **Live-Sync:** ja, vollständig (via `Actions → Mastodon-Profil-Sync`)
**Branch:** `arena/02a91216-franksfinanzcheck-blog` · **Live-Profil:** https://mastodon.social/@FranksFinanzcheck

---

## 1 · Auftrag & Ausgangslage

> „Bitte Mastodon-Profil vollständig an die Veröffentlichungsroutine Montag/Mittwoch/Freitag anpassen auf Highend-Level einer Profi-Agentur.“ (Frank, 06.11.2026)

**Ausgangslage (Befund der Analyse, kein Live-Abruf nötig – der Repo-Bestand ist die Quelle):**

| Ebene | Ist (bis 06.11.2026) | Problem |
|---|---|---|
| Bio im Profil-Sync | 470 Z., ohne Rhythmus-Angabe | Publikationsroutine nirgends ablesbar – verschenkte Konsistenz zum Blog |
| Bio im Wachstumsplan (Doku) | deckungsgleich mit Sync, aber ohne Routine | Kopf und Code driften vom Playbook-Anspruch ab |
| Testvertrag | „Mo/Mi/Fr“ war **verbotener** Claim (`test_positionierung_ohne_veraltete_claims`) | Dauervorgabe wurde fälschlich wie ein volatiler Zähler-Claim behandelt |
| Autopilot-Taktung (`data/social/channels.yaml`) | **täglich** (`days: [0,1,2,3,4,5,6]`, 4 Slots, 2/Tag) | Drift weg von der Blog-Dauervorgabe Mo/Mi/Fr (`docs/CADENCE-REPORT.md` Regel 2) |
| 14-Tage-Plan (`data/social/schedule.yaml`) | 4 Mastodon-Posten auf Nicht-Publikationstagen (2 × Sa 07.11., Sa 14.11., Do 19.11.) | würde die neue Routine bereits ab dem nächsten Wochenende unterlaufen |
| Kalender (`data/social/kalender/`, `static/kalender/`) | Sendetage „täglich“ | widersprach dem Playbook-Anschein nach außen |

**Warum das eine Dauervorgabe ist – und kein volatiler Claim:** „Montag/Mittwoch/Freitag, 2–3 Artikel“ steht seit 19.08.2026 als **fixe** DAUERVORGABE in `docs/CADENCE-REPORT.md` (Regel 2, ohne dynamische Anpassung, technisch erzwungen durch `cadence_guard.py` + Deploy-Gate). Was veraltet, sind Sparsummen („1.800 €“), Artikelzähler („25+“) und Gegenwartsversprechen („antworte persönlich“) – die bleiben bewusst verboten.

---

## 2 · Was geändert wurde (vollständig, alle Ebenen)

### 2.1 Profil-Texte (`scripts/mastodon_profile_sync.py`)

**Neue Bio – 498/500 Zeichen** (Mastodon-Rendering: mehrzeilig, Absätze):

> Ich bin Frank Hartung. Ich helfe dir, Fixkosten nachvollziehbar zu prüfen – mit Rechnungen und Checklisten statt Wechsel-Druck.
>
> Strom & Gas · Internet · Versicherungen · Konto · Budget · Mobilität
>
> **Neue Ratgeber: Mo/Mi/Fr – 2–3 pro Publikationstag.**
>
> Mein 4K-Kompass: Kosten sehen, Konditionen rechnen, Kündigungsfenster sichern, Kurs halten.
>
> KI-unterstützte Ratgeber · Affiliate-Links (Werbung) · Keine individuelle Finanzberatung.
>
> Welche Fixkosten prüfst du als Nächstes? #Fixkosten #GeldSparen

- **Anzeigename** unverändert: `Frank | FranksFinanzcheck` (25/40) – persönlicher Absender + Marke, ohne Sparversprechen.
- **Felder** unverändert (max. 4/4): Fixkosten-Cockpit → `/cockpit/`, Ratgeber → `/pillar/`, Über Frank → `/ueber/`, Transparenz → `/transparenz/`. Keine Kurz-/Partnerlinks.
- **`discoverable: true` / `indexable: true`**, Bot-Flag unverändert (kein Wachstumstrick).
- **Header-/Avatar-Alt-Texte** unverändert (beschreiben das Motiv; a11y-korrekt, kein Rhythmus-Versprechen in Alt-Text).
- Report-Baustein (`MASTODON-PROFILE-REPORT.md`) enthält jetzt zusätzlich die **Veröffentlichungsroutine**-Zeile und eine Einordnung („kein Uhrzeit-Versprechen für Einzelbeiträge“).
- Trockenlauf-Ausgabe prüft neu: `Publikationsroutine Mo/Mi/Fr (Dauervorgabe): OK`.

**Agentur-Detail Bio:** Die Routine-Zeile ist der einzige Rhythmus-Hinweis – bewusst ohne Uhrzeiten („MESZ“/„07:30“): Uhrzeiten veralten bei Zeitumstellung und Slot-Vergleichen; der Wachstumsplan testet 07:30–20:00 abwechselnd. Der Test verbietet `MESZ`/`Uhr` in der Bio.

### 2.2 Autopilot-Taktung (`data/social/channels.yaml`)

```yaml
cadence:
  # UMSTELLUNG 2026-11-06 (Frank / Agentur): nur Mo/Mi/Fr …
  days: [0, 2, 4]                # vorher [0,1,2,3,4,5,6]
  times: ["07:30", "11:30", "17:30", "20:00"]   # bewusst unverändert
  max_per_day: 2                                # bewusst unverändert
```

Uhrzeiten bleiben, weil die Routine die **Wochentage** betrifft (DAUERVORGABE), nicht die Uhrzeit – und weil der 14-Tage-Plan bereits Slots im 07:30/11:30-Raster hält. `max_per_day: 2` bleibt am Wachstumsplan-Limit („maximal zwei automatische Mastodon-Posts/Tag“).

### 2.3 14-Tage-Plan (`data/social/schedule.yaml`) – 4 Posten verschoben, keiner verloren

| Posten (Artikel) | vorher geplant | jetzt |
|---|---|---|
| mehr-freiheit-durch-verzicht (frugalismus, vergleich) | Sa 07.11. 11:30 | `blocked` – Rückstellung vermerkt |
| preisgarantie-gas (strom-sparen, frage) | Sa 07.11. 17:30 | `blocked` – Rückstellung vermerkt |
| wohngebaeudeversicherung-vergleich (versicherungen, mythos) | Sa 14.11. 17:30 | `blocked` – Rückstellung vermerkt |
| kreditkarte-vergleichen (konto-karten, thread) | Do 19.11. 07:30 | `blocked` – Rückstellung vermerkt |

`blocked` ist der vorgesehene Rückstellstatus des Autopiloten (Kalender-Symbol 🚫). Die Slugs sind damit nicht mehr im Plan belegt → der nächste Plan-Roll plant die Artikel automatisch auf Mo/Mi/Fr ein. Alle Mo/Mi/Fr-Posten dieses Fensters (Fr 06.11. 2 Launch-Posts, Mo 09.11. 2×, Mi 11.11., Mo 16.11. 2×) bleiben unverändert. Der Tagesgesamt-Deckel (12/Tag über alle Kanäle) wird an keinem bewegten Tag gerissen.

### 2.4 Veröffentlichungskalender neu gebaut

`python3 scripts/social_calendar.py --build` (25 Dateien). Mastodon zeigt jetzt **„Sendetage: Mo, Mi, Fr · Uhrzeiten: 07:30, 11:30, 17:30, 20:00 · max. 2/Tag“**; UEBERSICHT/README/`static/kalender/index.html` synchronisiert; die anderen Kanal-Kalender wurden dabei auf den aktuellen (über Nacht vom Autopiloten gerollten) Planstand synchronisiert.

### 2.5 Tests (`scripts/tests/test_mastodon_profile_sync.py`)

- `test_positionierung_ohne_veraltete_claims`: `Mo/Mi/Fr` ist **kein** verbotener Claim mehr, sondern gefordert (`assertIn`). Verboten bleiben `1.800`, `25+`, `antworte persönlich`.
- Neu: `test_bio_nennt_publikationsroutine_als_dauervorgabe` – fordert `Mo/Mi/Fr` + `Publikationstag`, verbietet `MESZ`/`Uhr`, deckelt 500 Zeichen.
- Alle 8 Profil-Tests bestanden. Gesamtsuite: **Ran 96 tests – 1 pre-existing Failure** (`test_jeder_kanal_hat_mindestens_einen_sendbaren_winkel`, reddit-Winkel für `2026-10-28-oekostrom-…`), **auf der unmodifizierten Basis `ec3ecdd` reproduziert** → kein Regressions durch diese Änderung.

### 2.6 Doku synchronisiert

- `docs/MASTODON-WACHSTUMSPLAN.md`: Stand, Bio (498 Z.), Blog↔Rhythmus-Befund (Dauervorgabe statt „ungeeigneter Rhythmus“), Redaktionsroutine Mo/Mi/Fr, Nachtrag 06.11.2026.
- `docs/ANLEITUNG-SOCIAL-MEDIA.md`: Premium-Profil-Tabelle (Bio 498 Z.), neuer Block „Veröffentlichungsroutine Mo/Mi/Fr (Stand 06.11.2026)“.
- `docs/ANLEITUNG-SOCIAL-AUTOPILOT.md`: Kanal-Tabelle – Mastodon-Taktung jetzt **Mo/Mi/Fr, 2/Tag**.

---

## 3 · Verifikation (offline, 06.11.2026)

| Prüfung | Ergebnis |
|---|---|
| `python3 -m unittest scripts.tests.test_mastodon_profile_sync` | **8/8 OK** |
| `python3 -m unittest …test_social_perf_feedback …test_social_autopilot` | 96 Tests, 1 Failure = **pre-existing auf Base `ec3ecdd`** (reddit, siehe 2.5) – keine Regression durch diese Änderung |
| `scripts/social_calendar.py --selftest` | ✅ bestanden |
| `scripts/social_studio.py --selftest` | ✅ bestanden (Kapazität, Limits, Gate, Duplikat-Schutz, Planung, Standby-Regel) |
| `scripts/social_perf_feedback.py --selftest` | ✅ bestanden |
| `scripts/mastodon_profile_sync.py --dry-run` | ✅ Anzeige korrekt (498 Z., Felder 4/4, Checks grün, kein Versand) |
| `git diff --check` | Nur Generator-Artefakte: `.ics` (CRLF, RFC-5545-Pflicht) + Kalender-`.md` (Markdown-Harte-Umbrüche = zwei Leerzeichen, 34× bereits im Bestand) – kein manuell getippter Whitespace; kein CI-Gate nutzt `--check` |

---

## 4 · Live-Rollout (vollständig, wie beauftragt)

Ausführung über den bestehenden Workflow (nutzt `MASTODON_ACCESS_TOKEN`, Scope `write:accounts`):

1. `Actions → Mastodon-Profil-Sync → Run workflow` (dry_run=true) – Vorschau, kein Versand.
2. Danach `dry_run=false` – echter PATCH `/api/v1/accounts/update_credentials`.
3. Bestätigung erst mit API-Antwort + Report-Artefakt (`mastodon-profile-report-<run_id>`, 90 Tage Retention); der lokale Report ist bewusst nicht versioniert.

**Nach dem Live-Lauf prüfen (30 Minuten später):** Bio-Zeile sichtbar? Felder verifiziert (grüner Haken = nur Link-Kontrolle)? Mobilansicht/Banner-Zuschnitt? `rel="me"` im `<head>` unverändert?

**Durchgeführter Rollout & Nachweis (06.11.2026):**

- Dry-Run: `Actions → Mastodon-Profil-Sync` run `42214662111` – alle Steps grün.
- Live: run `42214731405` – alle Steps grün, inkl. `Mastodon-Profil aktualisieren` (PATCH) und `Profil-Report als Artefakt sichern`.
- Öffentlicher Gegencheck auf `https://mastodon.social/@FranksFinanzcheck` (06.11.2026): Bio mit der Zeile „Neue Ratgeber: Mo/Mi/Fr – 2–3 pro Publikationstag.“ sichtbar, 4 Profilfelder gesetzt, Banner/Avatar unverändert, Bot-Kennzeichnung („Automated“) erhalten, 104 Posts.
- Hinweis: Job-Logs und das Report-Artefakt konnten aus dieser Sandbox nicht geladen werden (Netzwerk-Restriktion); der Nachweis erfolgte über den öffentlichen Profil-Endpunkt. Der Artefakt-Download bleibt via `gh run download 42214731405 --name mastodon-profile-report-42214731405` möglich.

---

## 5 · Grenzen & Ehrlichkeit

- Der Sync setzt Profil-Metadaten und Bilder – **keine** Reichweite, keine Impressions-Garantie. Profil-Verifizierung bestätigt den Besitz der Domain-Links, keine Finanzqualifikation.
- Off-Day-Posten im Plan wurden **nicht gelöscht, sondern zurückgestellt**; sie kehren beim nächsten Plan-Roll zurück. Ein Volltext-Neuversenden/Löschen+Wiederholen findet bewusst nicht statt.
- Kein Live-Abruf vor dem Rollout; alle Live-Zahlen (Follower, Reactions) bleiben separate Nachweise nach dem Sync.
- Die Routine-Zeile ist eine Dauervorgabe, kein Uhrzeit- oder Reichweitenversprechen; der Blog garantiert Mo/Mi/Fr technisch (Kadenz-Gate), Mastodon-Veröffentlichungen folgen demselben Raster.

## 6 · Rollback

`git revert <merge-commit>` (oder die Datei `scripts/mastodon_profile_sync.py` auf den Stand vor 06.11.2026 zurücksetzen) → `Actions → Mastodon-Profil-Sync` erneut ausführen. Der Plan-Stand (4 `blocked`-Posten) kann unverändert bleiben – er ist unabhängig reversibel (`status: planned` + Datum wiederherstellen).

## 7 · Nächste Hebel (nicht Teil dieses Auftrags)

- 30-Tage-Messung nach Wachstumsplan § 6 (48h-/7-Tage-Fenster, Boosts/Antworten als Primärsignale).
- Zwei bis drei echte Gespräche pro Publikationstag (15–20 Min.) – menschlich, nicht delegierbar.
- Nach 6+ vergleichbaren Beiträgen: Hashtag-/Uhrzeit-Entscheidung anhand eigener Zahlen.

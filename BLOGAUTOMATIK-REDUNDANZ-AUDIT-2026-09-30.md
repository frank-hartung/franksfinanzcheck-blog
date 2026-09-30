# 🔍 Blogautomatik-Redundanz-Audit – Premium-Agentur-Befund

**Datum:** 30.09.2026 · **Auftrag:** „Prüfe ausführlich und umfangreich meine
gesamte Blogautomatik auf Premium-Level einer Profi-Agentur. Finde heraus,
welche Blogautomatik sich überschneidet bzw. überflüssig ist und nehme die
entsprechende Optimierung auf Premium-Level einer Profi-Agentur vor."

---

## 1. Befund in einem Satz

Die Automatik ist im Kern auf Agentur-Niveau gebaut — aber nach 6 Wochen
Wachstum waren **4 Automatiken echte Duplikate** (eine lief byte-identisch
dreifach pro Woche), **14 produktionskritische Läufe liefen ohne
Fehlalarm-Beobachtung**, der Uptime-Monitor verbrannte **ein Viertel des
gesamten Laufkontingents** für eine statische Site, und vier Cron-Kollisionen
produzierten genau die Rebase-Konfliktklasse, die das Repo schon zweimal
teuer getroffen hat — alles heute behoben, mit 1.115 grünen Tests als Beweis.

## 2. Methodik & Prüfungsumfang

Geprüft wurden **vollständig**: alle 68 Workflow-Dateien (Trigger, Cron-Plan,
Schritt-Ketten, Aufruf-Scope `--new-only` vs. Bestand), die Skript-Verdrahtung
(250 Skripte, Gegenüberstellung welches Skript in welchem Workflow mit
welchem Scope läuft), der komplette Wochenkalender (Laufzahl je Wochentag
und Minute), die Governance-Verträge C1–C18 (`governance_contract.py`), die
Watch-Listen (Fehler-Alerting, Deploy-Catchup), die Wachen-Tests
(`selftest_runner`, 121 Wachen × 2 Uhr-Proben) sowie die Verifikationskette
(1.115 Unit-Tests, YAML-Wache für Workflows).

**Kennzahl vor der Optimierung:** ~1.287 geplante Workflow-Läufe pro Woche
(dazu Push-/workflow_run-getriggerte Läufe). Größte Treiber: Uptime-Monitor
672, Deploy-Catchup 168, Newsletter-Lifecycle 168, Social-Autopilot 56,
Revenue-Import 28, Dialog-Autopilot 21.

## 3. Was Profi-Niveau hat und UNANGETASTET blieb

Diese Muster sind bewusste Verteidigungstiefe („drei Netze"), KEINE
Redundanz — jede einzelne hat einen dokumentierten Vorfall als Entstehungsgrund:

| Muster | Warum es so bleibt |
|---|---|
| Newsletter: Worker-Taktgeber + GitHub-Cron + Kadenz-Wache | 23./25.09.: GitHub verwarf Crons still (5–5,5 h). Ein Netz am selben Haken ist kein Netz. |
| Deploy-Catchup: stündlicher Backstop + workflow_run-Schnellpfad | GITHUB_TOKEN-Commits triggern keine Folge-Workflows; #433-Driftklasse. |
| Affiliate: Integrität täglich (Render-Ebene) + Health wöchentlich (E2E-Redirect-Ketten) | Zwei Schadensklassen aus dem Vorfall 14.08. (8 beschädigte Live-CTAs). |
| Bot-Watchdog: bedingte Pinterest-Nachmessung (nur bei WARN/FAIL) | Nachmessung nach Selbstheilung — sonst meldet das Routing einen schon reparierten Zustand (#272). |
| Backup: brand_surface_guard `--only releases` nach jedem Lauf | Doppelboden, direkt nachdem der Lauf selbst hätte eine öffentliche Spur legen können. |
| Premium-Governance: Montags-Umami/Awin-Import trotz Revenue-Import | Nachweis-Prinzip: Das Wochen-Gate beweist die Pipeline, statt den 4×/täglichen Läufen zu vertrauen (gleiche Doktrin wie der Alerting-Herzschlag). |
| Content-Engine: Guards `--new-only` (Geburt) · Blog-Health: Bestand täglich · Deploy/Kadenz: Release-Gates | Sauber getrennte Scopes — genau dieses Muster habe ich für die Deduplizierung unten zum Vorbild genommen. |
| Mastodon-SEO 2×/Tag Mo/Mi/Fr | Drift-Wache über Live-Toots (PUT-Heilung), nicht Posten — komplementär zum Autopilot. |
| Agent-Reach (Mo-Briefs) vs. Hero-Refresh (täglich, 21-Tage-Rotation) | Verschiedene Produkte: Wochen-Briefs vs. Startseiten-Saison-Signale; der Hero-Lauf spart sich Claude-Aufrufe selbst. |
| Design-Varianten (Mo 06:45) vs. Layout-AI (Mo 07:00) | Verschiedene Jobs: Varianten-Labor/Messung vs. Layout-Annotate/DOM-Audit. |
| Tolerierte Kleinst-Redundanz: `fix_linebreaks`/`fix_spaces` laufen in der Engine (3×/Wo) und seo-weekly (1×/Wo) über den Bestand | Deterministische, idempotente Text-Normalisierer; Teil der Geburtskette — Eingriffskosten > Nutzen. |

## 4. Gefundene Überschneidungen (die Redundanz-Matrix)

### 4.1 Echte Duplikate — heute behoben 🔴→🟢

| # | Überschneidung | Befund | Maßnahme |
|---|---|---|---|
| **D1** | **Redaktions-Politur ⊂ Hemingway-Lesbarkeitscheck** | Die Mo 03:45-Wache lief exakt die Offline-Kette (`grammar_check --fix` + `sprachglatt --fix` über ALLE Artikel), die der Hemingway-Workflow seit 30.09. in **jedem** Lauf (Mo/Mi/Fr 04:50) als Schritt 1 ausführt. Montags lief derselbe Bestands-Fix zweimal binnen 65 Minuten. | Cron entfernt, Workflow bleibt als **manueller Notlauf**; der Hemingway-Check ergänzt die Offline-Kette um einen kostenlosen, lokalen Lesbarkeitsreport. |
| **D2** | **SEO-Weekly duplizierte die Sprachkette** | Mittwochs liefen `grammar_check --fix` und `sprachglatt --fix` über den Gesamtbestand — 3 h 10 min **nachdem** der Hemingway-Workflow (Mi 04:50) exakt dasselbe getan hatte. | Beide Schritte entfernt; SSOT Bestands-Sprachkette = Hemingway-Workflow. hunspell-Rechtschreib-Check bleibt (lief nur dort im Vollbestand). |
| **D3** | **SEO-Weekly duplizierte die Tageswache (R2–R8)** | Textverständnis-Audit + R8-Anker-Heilung liefen wöchentlich identisch zur **täglichen** Blog-Gesundheitswache. | Aus SEO-Weekly entfernt; SSOT = blog-health-daily (täglich). |
| **D4** | **SEO-Weekly duplizierte die Keyword-Heilung** | `keyword_optimizer --fix` + `keyword_gate --fix` liefen wöchentlich, obwohl die Tageswache sie seit Premium #303 täglich heilt. | Fix-Läufe entfernt; der Wochenschritt behält seine echte Arbeit: KI-LSI-Vorschläge (`--ai --apply`) + reines Prüfgate (ohne `--fix`) für den Issue-Trigger. |
| **D5** | **Uptime-Monitor */15** | 672 Läufe/Woche = **52 % aller geplanten Läufe** für 3 statische URLs. Der repo-eigene Incident-Nachweis (25.09.) zeigt, dass GitHub unter Last ohnehin nur 6 von 96 Läufen auslöste — das 15-Minuten-Versprechen war faktisch nie einhaltbar. | `*/30` — halbiert die Scheduler-Last bei gleicher realer Erkennungsqualität. |
| **D6** | **Revenue-Import 4×/Tag** | Dokumentierter Bedarf ist *Tages*frische („Klicks und Stornos kommen täglich herein"); kein einziger Verbraucher im Repo liest die Daten intraday (Scorecard/Funnel wöchentlich, Kennzahlen-Radar liest Research-Briefs). | 2×/Tag (06:10 + 18:10 MESZ) — halbiert die Umami-API-Last, Morgen- und Abendbericht bleiben. |

### 4.2 Betriebslücken, die bei der Prüfung auffielen — heute geschlossen 🔴→🟢

| # | Lücke | Folge | Maßnahme |
|---|---|---|---|
| **L1** | **14 geplante Produktions-Workflows standen NICHT in der Fehler-Alerting-Wacht-Liste** — darunter Social-Autopilot (8×/Tag), Revenue-Import, Newsletter-Lifecycle, Faktenfrische, ZEIT-Rechtschreibung, Kennzahlen-Radar, Marken-Oberfläche, Agent-Reach, Dialog-Autopilot, Shorts-Schmiede, Social-Preflight, Design-Varianten, E2E-Tests. (Historischer Grund: alle jünger als der letzte Wacht-Listen-Stand; bewusst fehlt nur der Alerting-Herzschlag selbst.) | Ein stiller Rotlauf dieser Workflows hätte **kein Issue, keine Mail** erzeugt — exakt die Blindheitsklasse (#206 „stille Blindheit"), gegen die das Alerting gebaut wurde. | Alle 14 + der Redaktions-Politur-Notlauf in die Wacht-Liste aufgenommen (jetzt 57 beobachtete Workflows; Herzschlag zählt sie automatisch mit, Tests asserten ≥ 35 — grün). |
| **L2** | **Deploy-Catchup-Schnellpfad kannte 5 content-committende Workflows nicht** (Hemingway-Lesbarkeitscheck, ZEIT-Rechtschreibung, Redaktions-Standard Bestand, Faktenfrische, Redaktions-Politur) | Deren GITHUB_TOKEN-Commits triggern keinen Deploy — die Fixes lagen bis zu 55 Min. brach, bis der stündliche Backstop sie holte. | Alle 5 in den Schnellpfad aufgenommen: Content-Heilungen sind jetzt Minuten nach Commit live. |
| **L3** | **Toter Issue-Trigger im Keyword-Schritt (SEO-Weekly)** | `exit ${PIPESTATUS[0]}` nach einem reinen `cat` liefert immer 0 — das „Issue bei kritischen Keyword-Scores" (Premium-Lücke zu 09.09.) konnte **nie** feuern. Schein-Sicherheit der schlimmsten Sorte. | Exit-Code des Gates wird jetzt sauber gefangen (`gate_rc=${PIPESTATUS[0]}`); der Trigger lebt. |
| **L4** | **Cron-Kollisionen** (jeweils dieselbe Minute): Di/Fr 04:30 Newsletter + Pinterest-Watchdog + KI-Redaktion (drei Content-Committer!) · Mo/Mi/Fr 04:50 Herzschlag + Hemingway-Check · Di 04:20 Kennzahlen-Radar + Marken-Oberfläche · Mo 05:15 Premium-Governance + Hero-Refresh (beide mit Hugo-Build) | Erhöht genau die parallele-Bot-Commit-Klasse, an der schon #295 (Rebase-Konflikt auf `data/reserve-readiness.json`) und der 25.09.-Scheduler-Zusammenbruch gemessen wurden. | Entzerrt: KI-Redaktion → 04:53, Herzschlag → 04:47, Kennzahlen-Radar → 04:24, Hero-Refresh → 05:27. Alle dokumentierten Reihenfolge-Verträge bleiben eingehalten (jeweils in den Kommentaren begründet). |
| **L5** | **Aktiver Workflow mit Temporär-Name** `fristen-check-2026-08-30-workflow-ready.yml` | Der Ready-to-Paste-Name stammte aus der Zeit, in der Agent-Token keine Workflow-Pfade pushen durften; das Rename war schon am 31.08. als Auftrag erkannt (docs/CLEANUP-REPORT), konnte aber nie ausgeführt werden. | Zu `fristen-check.yml` umbenannt (Watch-Listen matchen auf den Namen „Fristen-Check (Recht)", unverändert). |
| **L6** | **Veraltete Doppelkopie** `workflow-ready/zeit-rechtschreibung.yml` | Kopier-Vorlage nach Aktivierung vom 28.09. = Drift-Risiko bei jeder künftigen Änderung der aktiven Datei. | Ordner entfernt; SSOT = aktiver Workflow. 5 Dokumentationsstellen (CLAUDE.md, Anleitung, ZEIT-Report) nachgezogen. |

## 5. Die Redundanz-Matrix im Detail (Skript × Workflow × Scope)

Vor der Optimierung liefen über den **Gesamtbestand** (nicht `--new-only`):

| Skript (Vollbestand-Fix) | Vorher | Nachher | SSOT |
|---|---|---|---|
| `grammar_check --fix` | 4–5×/Wo (Politur Mo · Hemingway-Check Mo/Mi/Fr · SEO Mi · ZEIT-Fallback Mo) + Engine (neu) | 3×/Wo (Hemingway-Check Mo/Mi/Fr) + ZEIT-Fallback (Mo) + Engine (neu) | Hemingway-Lesbarkeitscheck |
| `sprachglatt --fix` | 4×/Wo (Politur Mo · Hemingway-Check Mo/Mi/Fr · SEO Mi) + Engine (neu) | 3×/Wo (Hemingway-Check) + Engine (neu) | Hemingway-Lesbarkeitscheck |
| `textverstaendnis_guard` + `fix_r8_anker --fix` | 8×/Wo (Blog-Health täglich + SEO wöchentlich) | 7×/Wo (Blog-Health täglich) | Blog-Gesundheitswache |
| `keyword_optimizer --fix` / `keyword_gate --fix` | 8×/Wo (Blog-Health täglich + SEO wöchentlich) | 7×/Wo (Blog-Health täglich); SEO prüft nur noch (Gate ohne Fix) | Blog-Gesundheitswache (#303) |
| Umami/Awin-Import | 29×/Wo (Revenue 28 + Governance 1) | 15×/Wo (Revenue 14 + Governance-Verifikation 1) | Revenue-Import (Daten) · Governance (Nachweis) |

Nicht angetastet (bewusste Verteidigungstiefe, siehe § 3): `cadence_guard` (7 Workflows, aber 4 verschiedene Rollen: Geburt/Backstop/Monitor/Gate), `check_covers` (Release-Gates vs. Bestandshygiene), `fix_url_hygiene`, `draft_link_healer`, `submit_indexnow`, `pinterest_seo_healer` (Bestand vs. `--new-only`).

## 6. Was bewusst NICHT geändert wurde (Agentur-Urteil)

1. **Premium-Governance-Umami-Import** blieb trotz Überschneidung mit dem
   Revenue-Import: Das Wochen-Gate muss die Pipeline **beweisen** (C3-Vertrag
   zählt die Gate-Kennungen), nicht den 2×/täglichen Läufen vertrauen —
   dieselbe Doktrin wie der Alerting-Herzschlag. Die Kadenzhalbbierung beim
   Revenue-Import löst die Redundanz an der richtigen Stelle.
2. **Newsletter-Lifecycle stündlich** blieb: zweites Netz unter dem
   Cloudflare-Worker-Taktgeber, ehrlich billig (Kurzlauf ohne Posten), und
   E-Mail-Verzögerung bei Double-Opt-In ist Umsatzrelevant.
3. **Deploy-Catchup stündlich** blieb: Backstop-Charakter, ~15 s pro Lauf.
4. **Ki-Redaktion (Mo–Fr)** blieb: eigener Auftrag (Entwurfs-Track mit
   manueller Freigabe), kein Konkurrent zur Engine (Auto-Publish-Track).
5. **Manuelle Notlauf-Workflows** (repin-weekly, social-ai, pinterest-ai,
   mastodon-manual-post, redaktions-politur ab heute): kosten keinen Plan-
   Slot, haben dokumentierten Zweck als Handwerkzeug.
6. **Keine Änderung an Dauervorgaben**: Kadenz Mo/Mi/Fr 2–3 Artikel,
   AUTO_PUBLISH-Logik, Kosten-Deckel 0 €, Skript-Verhalten — die Optimierung
   betraf ausschließlich Verdrahtung, Zeitpläne und Watch-Listen.

## 7. Verifizierung (alles grün, in dieser Reihenfolge gelaufen)

| Prüfung | Ergebnis |
|---|---|
| Workflow-YAML-Wache (Parse, doppelte Schlüssel, Step-Namen, Skript-Existenz) | ✅ 6/6 |
| Governance-Vertrag C1–C18 (quick + voll) | ✅ erfüllt |
| Alerting-Tests (Herzschlag-Parsing, Scoping, Wacht-Listen-Vertrag) | ✅ 35/35 |
| Deploy-Catchup-Vertragstests | ✅ inklusive |
| **Gesamte Unit-Suite** | ✅ **1.115 Tests, 0 Fehler** (22 netzbedingt geskippt) |
| Wachen-Selbsttests (121 Wachen, jeweils 2 vorgestellte Uhren) | ✅ grün |
| Report-Hygiene (Root sortenrein) | ✅ grün |
| Push-Test Workflow-Pfade (Agent-Token mit workflows-Scope) | ✅ möglich — Basis für L5/L6 |

## 8. Kenndaten Vorher → Nachher

| Kennzahl | Vorher | Nachher |
|---|---|---|
| Geplante Workflow-Läufe/Woche | ~1.287 | **~936 (−27 %)** |
| Uptime-Monitor-Läufe/Woche | 672 | 336 |
| Umami-API-Vollzüge/Woche | 29 | 15 |
| Vollbestands-Grammatik/Glätte-Fixläufe/Woche | 4–5 | 3 |
| Ohne Fehlalarm-Beobachtung laufende geplante Workflows | 14 | **0** (bewusst nur der Herzschlag selbst) |
| Content-Commits mit verspätetem Deploy (Schnellpfad-Lücke) | 5 Workflows | 0 |
| Cron-Minuten-Doppelbelegungen (Nachtband 02–07 UTC) | 4 | 0 |
| Funktionsfähige Issue-Trigger (Keyword-Gate) | 0 (still tot) | 1 |

## 9. Was nur Frank tun kann (unverändert gültig)

Die Restliste aus dem Automatisierungs-Fahrplan vom 29.09. bleibt bestehen
(Pinterest-Domain-Freigabe → Restart-Workflow, Bluesky/Telegram-Secrets,
GSC-Verifizierung, CHECK24-Testklick-SOP). Neu aus diesem Audit: **nichts** —
alle Maßnahmen dieses Berichts wirken nach dem Merge automatisch mit dem
nächsten Cron-Fenster.

---

_Erstellt in der Arena-Session „Blogautomatik-Redundanz-Audit" am 30.09.2026.
Alle Änderungen kommen per PR auf `main` — Workflow-Renames und Zeitplan-
änderungen greifen mit dem nächsten geplanten Lauf nach dem Merge._

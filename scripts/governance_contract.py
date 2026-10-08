#!/usr/bin/env python3
"""
GOVERNANCE-KONTRAKT – die Checks, damit #206 nie wiederkehrt.

Ein Governance-Report, der jede Woche dasselbe „Problem" meldet, das keines ist,
ist kein Messinstrument, sondern Lärm. Und Lärm ist im Betrieb teurer als der
Fehler selbst: echte rote Befunde gehen in der Gewohnheit unter (Alarm-Müdigkeit).
Deshalb werden die Regeln, die den Dauer-Alarm erzeugt haben, jetzt als
**materieller Vertrag** im Repo gespeichert und vor jedem Merge geprüft.

Geprüft werden ausschließlich Im-Repo-Artefakte (Workflows, Reports, Manifeste) –
ohne Netzwerk, ohne API, determinisch. Läuft lokal, im Premium-Governance-Lauf
(Preflight) und im Qualitäts-Gate (bei jedem Push/PR auf main).

  C1  Reihenfolge       – Scorecard (Sicht) MUSS nach den Messschritten laufen
  C2  Bau-Grundlage     – Hugo-Build darf kein `|| true` schlucken; Scheingrün
                          ohne gemessenen Build ist verboten
  C3  Messkette komplett– jeder Gate-Schritt wird aus dem Workflow gefüttert
  C4  Issue-Policy       – kein Issue ohne Gate-Entscheidung, kein Duplikat
                          (update statt create), schließen bei Grün
  C5  Nachweis-Provenienz– `--record-success` nur mit `--proof-by`, nie im
                          Governance-Lauf selbst (kein Selbst-Waschen), nur für
                          registrierte Secrets
  C6  Selbsttests grün   – alle Governance-Wachen haben `--selftest` und bestehen
  C7  Datenkonsistenz    – Manifest ↔ Report ↔ Scorecard müssen dieselbe Ampel
                          zeigen (oder die Scorecard kennzeichnet STALE/nicht
                          gemessen ausdrücklich)
  C8  Commit-Hygiene     – `git add` im Workflow darf nur versionierbare Pfade
                          nennen (Sonst: harter Abbruch, vgl. #205)
  C9  Secret-Leak-Schutz – Report-Dateien dürfen kein Token-Material enthalten
  C10 Token-Broker      – jedes Pinterest-Skript holt seinen Token beim zentralen
                          Broker; kein Skript baut sich eine eigene Reihenfolge
                          (sonst prüft die Wache einen anderen Token als der Bot
                          benutzt – Kernbefund #206)
  C11 Token-Lebenszyklus– es gibt einen täglichen Erneuerungslauf, der den
                          rotierten Refresh-Token sichert und sich selbst heilt
                          (ein 30-Tage-Secret von Hand ist kein Betrieb)
  C13 Nachweis-Echtheit – ein Pinterest-Nachweis läuft immer mit Live-Probe
                          (`--verify`), nur die Token-Wache rotiert proaktiv
                          (PINTEREST_TOKEN_WACHE=1), und die Autorisierung
                          fordert die echten v5-Scopes (#219)
  C12 Label-Garantie    – jeder Workflow, der ein Issue mit Label erzeugt, legt
                          das Label vorher an; sonst scheitert der Melder am
                          Melden (Ursache des roten Laufs in #209)
  C14 Alarm-Routing     – jeder Befund hat einen Besitzer (Maschine/Mensch),
                          einen Kanal und einen Schließpfad. Menschliche Befunde
                          dürfen kein Automations-Ticket öffnen oder offen halten
                          (sonst Dauer-Alarm ohne Ausweg, #272)
  C15 Beweis-Trockenlauf – ein Prüf-Aufruf heilt nicht: Nacktheiler brauchen
                     einen trockenen `--selftest`, Kettenleiter dürfen `--fix`
                     im Selbsttest nicht weitergeben
  C16 Wache-Herzschlag  – ein Lebenszeichen ist kein Befund: die Affiliate-
                     Integritäts-Wache erneuert ihren Zeitstempel bei jedem Lauf
                     (Beweis im Gate-Selbsttest), ihre Frische wird per Herzschlag
                     ODER fehlerfreiem Lauf belegt, und der Lebenszeichen-Pfad ist
                     deploy-irrelevant (#281)
  C17 Pinterest-Duplikate – pin_title/pin_description sind über alle Artikel
                     einzigartig; der Duplicate-Guard läuft in Watchdog und
                     Content-Engine (#305)
  C19 Release-Scorecard – die SSOT der Produktionswahrheit: jede harte
                     Publish-Gate-Familie ist als blockierend deklariert,
                     die Engine misst über die Publish-Gate-Collectoren
                     (keine zweite Messregel) und siegelt die geprüfte
                     Version (Befund 10, 03.10.2026)
  C18 Pflicht-Check     – der Anzeigename des PR-Gates (`Integritäts-Siegel`) ist
                     der Vertrag mit dem Branch-Schutz: Konstante = Workflow =
                     Ruleset. Kein `paths`-Filter, kein `if:` am Job, kein
                     `continue-on-error` am Gate-Schritt, nur Leserechte – und die
                     Live-Wache `pflichtcheck_guard.py` prüft im Gate selbst, ob
                     der Branch-Schutz den Check wirklich verlangt (19.09.2026).
                     Ist der Vertrag nachweislich NICHT erfüllbar (Regeländerung
                     bleibt Admin-Aufgabe), darf er weder verschwiegen noch zum
                     Dauer-Alarm werden: `PFLICHT_CHECK_DAUERZUSTAND` legt ihn als
                     festgestellten, befristeten Zustand ab – die Wache meldet ihn
                     als BEKANNT statt als Vorfall, jeder andere Befund bleibt rot
                     (20.09.2026)

Exit-Codes: 0 = Vertrag erfüllt · 1 = Verletzung(en) · 2 = Selbsttest/Fehler

Nutzung:
  python3 scripts/governance_contract.py            # prüfen
  python3 scripts/governance_contract.py --md docs/GOVERNANCE-KONTRAKT.md
  python3 scripts/governance_contract.py --quick    # ohne Selbsttest-Läufe (schnell)
  python3 scripts/governance_contract.py --python .venv/bin/python   # lokale Abweichung
  python3 scripts/governance_contract.py --selftest
"""
import datetime
import glob
import json
import os
import re
import subprocess
import sys
from pathlib import Path

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))

GOV_WORKFLOW = os.path.join(BLOG_DIR, ".github", "workflows", "premium-governance.yml")
WORKFLOWS_DIR = os.path.join(BLOG_DIR, ".github", "workflows")
# Mindestmenge der Wachen, die der Vertrag prüft (C6: jede mit `--selftest`).
# schema_seo_gate.py + generate_pwa_icons.py sind der 11.09.2026 dazugekommen:
# das doppelte `| jsonify` in schema_article.html hatte die Article-Schema aller
# Live-Artikel unbrauchbar gemacht, und die Site registrierte einen Service
# Worker ohne Manifest. Beide Fehler waren im Build unsichtbar – jede Korrektur
# ohne Wache hier wäre eine Leihgabe.
GUARDS = [# Kostensperre (03.10.2026): Schreibschutz vor den zwei
          # Geldflaechen ausserhalb der Textkette. Gehoert ins
          # Regelwerk, weil eine Wache, die niemand verlangt,
          # irgendwann niemand mehr ausfuehrt.
          "kostensperre.py",
          # Hugo-Build-Vertrag (03.10.2026): Ohne diese Wache broeckelt die
          # gemeinsame Fehlerausgabe zurueck in `> /dev/null`, `|| true` und
          # `--quiet` – genau die Lage, die am 02.10.2026 Stunden kostete.
          "hugo_build_vertrag.py",
          "editorial_scorecard.py", "cwv_guard.py", "secrets_age_guard.py",
          "decay_radar.py", "governance_gate.py", "readability_check.py",
          # Lesbarkeits-Heiler (07.10.2026, WACHE-609): Er ist der Heiler
          # der zweiten Haelfte des Lesbarkeits-Tors (Flesch >= 60 als
          # Publish-Kriterium, #585) und beweist seine Wirkung als
          # Maschinenvertrag (`--wirkungsprobe`). Eine Wache, die niemand
          # verlangt, fuehrt irgendwann niemand aus - deshalb steht sein
          # Selbsttest hier im vertraglichen Minimum (C6).
          "lesbarkeit_heiler.py",
          # Politur-Heiler (07.10.2026, BOT-WATCHDOG #614): Er heilt die
          # Maschinen-Reste, fuer die es bis dahin KEINEN Heiler gab (R7-Intro-
          # Formel, R11/R13 Zahlen-Datums-Ruinen, R14-Marker, R15-PHrasen-Doppel,
          # R16-Prompt-Echo) - genau die Funde, die das Zertifikat als „manuell
          # reparieren" auswies und die das Tor T2 des Lesbarkeits-Heilers
          # deshalb JEDE KI-Heilung verwerfen liessen. Er laeuft in der Kette
          # VOR dem Lesbarkeits-Heiler und beweist seine Wirkung als
          # Maschinenvertrag (`--wirkungsprobe`, Governance C25). Eine Wache,
          # die niemand verlangt, fuehrt irgendwann niemand aus - deshalb steht
          # sein Selbsttest hier im vertraglichen Minimum (C6).
          "politur_heiler.py",
          # Politur-Ruinen-Heiler (07.10.2026, WF-D4E0/#612, aus main): das
          # schmale, deterministische Werkzeug fuer R11/R13/R14. Beide Heiler
          # sind Absicht: der schmale heilt seine drei Klassen ohne KI-Zutun,
          # der breite deckt die uebrige Familie (R7/R15/R16) und wirkt als
          # Auffangnetz. Beide mit Wirkungsprobe (C25) und Selbsttest (C6).
          "politur_ruine_heiler.py",
          # Satz-Heiler (07.10.2026, BOT-WATCHDOG #614): Der Lesbarkeits-
          # Heiler kann die Schwelle (< 60) mit Stufe A nicht erreichen und
          # mit Stufe B (Ganztext) nicht schreiben - die Klasse war damit
          # unheilbar gebaut, und genau sie hielt den Reserve-Vorrat bei 2/6.
          # Der Satz-Heiler gibt der KI nur Sätze ohne Zahlen/Markup und
          # laesst das Ganztext-Tor T1-T4 unveraendert entscheiden; seine
          # Wirkung ist Maschinenvertrag (`--wirkungsprobe`, C25). Damit gilt
          # auch fuer ihn: eine Wache, die niemand verlangt, fuehrt irgendwann
          # niemand aus - Selbsttest ins vertragliche Minimum (C6).
          "satz_heiler.py",
          # Publikations-Vertrag (07.10.2026, WF-54C4/#607): Die KI-Heilung
          # pruefte nur Struktur und schrieb am 05.10.2026 einen Text mit
          # Flesch 44,3 + „In diesem Beitrag…“ in den Bestand; der Alarm kam
          # erst vom Deploy-Lauf. Diese Wache haelt den Vertrag selbst,
          # damit die Schreib-Seite nie ohne pruefbare Schwelle heilt.
          "publikations_vertrag.py",
          "umami_clicks.py", "click_attribution.py", "awin_provisions.py",
          # Umsatz-Messkette (19.09.2026): Views-Nenner, Awin-API-Import,
          # Wochen-Trichter und Ketten-Guard sind Wachen wie alle anderen –
          # ohne sie wäre „unbekannt“ wieder eine Fußnote statt ein Befund.
          "umami_views.py", "awin_fetch.py", "revenue_funnel.py",
          "click_chain_guard.py",
          "pinterest_perf_feedback.py", "pinterest_token.py", "pinterest_auth.py",
          "schema_seo_gate.py", "generate_pwa_icons.py", "report_hygiene.py",
          "live_policy_guard.py", "draft_triage.py", "check_uniqueness.py",
          "audio_coverage_check.py", "newsletter_digest.py",
          # Newsletter-Studio (22.09.2026, 0 €): das Design-System leitet jede
          # Mail-Farbe aus dem Build-CSS her, die Vor-Versand-Wache misst 20
          # Regeln nach. Beides sind Wachen wie die andren – ohne sie wäre
          # „Marke geprüft“ wieder eine Behauptung in einer Anleitung.
          "newsletter_studio.py", "newsletter_qa.py",
          # Social-Autopilot: der fail-closed Selbsttest der Kanallogik
          "social_studio.py",
          # Alarm-Routing (#272): Besitz, Kadenz, Schließpfad
          "alert_router.py",
          # Wache-Herzschlag (#281): der Selbsttest friert ein, dass ein
          # zweiter Lauf mit gleichem Befund den Zeitstempel ERNEUERT
          "affiliate_integrity_gate.py",
          # Intent-Wache (19.09.2026, Auftrag Frank: „Ein Besucher mit
          # konkreter Kaufabsicht darf niemals auf einem anderen Produkt
          # landen"): IW0–IW9 auf Anker↔Route, CTA↔Artikelthema und
          # Name↔wirkliches Angebot. Der Selbsttest friert die sieben
          # Live-Funde ein (Erkennung, Heilung, Idempotenz) UND den
          # Datenpfad der Templates – hugo.Data/site.Data im Layout lässt
          # Hugo den ganzen data/-Baum inklusive *.jsonl parsen und den
          # Build sterben. Der Kontrakt ist die Datendatei dahinter und
          # selbsttestet Angebotstreue, Nie-Paare und Themen-Muster.
          "affiliate_intent_guard.py", "affiliate_intent_contract.py",
          # Uhr-Zwang + Selbsttest-Runner (18.09.2026, Run 35312783057): der
          # draft_triage-Selbsttest war an einem Tag grün und sechs Tage später
          # rot, weil seine Fixtures von der echten Wanduhr, die Erwartung aber
          # von einem eingefrorenen Testdatum abhingen. Beide Wachen zusammen
          # machen „läuft an jedem Kalendertag" beweisbar statt gehofft.
          "selftest_clock.py", "selftest_runner.py",
          # Folge-Reparatur des Gate-Vorfalls (18.09.2026, Folge-Befund 2 des
          # Vorfall-Berichts): Beweis und Visite des Doktors sind jetzt
          # getrennt – sein --selftest ist ein reiner Logik-Beweis (kein
          # Bericht, kein data/*.jsonl, keine Kette) und gehört damit ins
          # vertragliche Minimum statt in die Runner-Ausnahme.
          "blog_doctor.py",
          # Folge-Reparatur des Gate-Vorfalls (18.09.2026, Folge-Befund 4 /
          # Befund E): Der Herzschlag zählt die workflow_run-Zustellung des
          # Fehler-Alertings täglich nach (~35 % der Ereignisse kamen
          # 08.–18.09. nie an). Eine Wache, die Zählung nur dokumentiert,
          # statt sie zu verlangen, ist keine Wache – also ins Minimum.
          "alerting_heartbeat.py",
          # Newsletter-Kadenz-Wache (23.09.2026): Der planmäßige
          # Newsletter-Daily-Cron blieb an einem Werktag STILL aus – kein Lauf,
          # kein Rotton, keine Meldung (GitHub verwirft schedule-Ereignisse
          # unter Last). Eine Wache, die den verpassten Lauf nicht einmal
          # verlangen kann, wäre Dekoration: ihr --selftest friert die
          # Entscheidungslogik ein (Ruhetag, Fenstergrenze, Vorfall-Erkennung,
          # kein Auto-Retry nach rotem Lauf) und gehört ins Minimum.
          "newsletter_cadence.py",
          # Zustandskanal der Tagesquote (07.10.2026, WF-1F8C #608): Die
          # Quote ist ein Zustand, kein Arbeitsauftrag. Am 05.10. endete der
          # Tag 1/2, das Fach-Issue #601 wurde per Reparatur-Merge
          # geschlossen, der Ruhetag am 06.10. wurde übersprungen – und der
          # nachgelieferte Montags-Slot meldete ehrlich rot, während das
          # zentrale Fehler-Alerting fail-open ein generisches Wartungs-Issue
          # mit API-Key-Runbook anlegte (#608). Der Selbsttest dieser Wache
          # stellt den Vorfall nach (Ruhetag gemessen, rot Geschlossenes
          # wieder geöffnet, ehrlich geschlossen) und gehört ins Minimum.
          "engine_issue.py",
          # H1-Wache (07.10.2026, WF-A11Y #623): „Genau eine H1 pro Seite“
          # ist die unsichtbarste Barrierefreiheits-Regel im Haus – sie
          # bricht nur, wenn jemand eine `# …`-Zeile in einen Fließtext
          # tippt, und sie trifft genau die Leser, die sich nicht
          # beschweren können (Screenreader, Inhaltsverzeichnis,
          # KI-Antworten). Ihr Selbsttest friert Quell-, Layout- und
          # Build-Regel mit Sabotageproben ein und läuft im Minimum (C6).
          "h1_wache.py",
          # Slot-Wache der Content-Linie (05.10.2026, #601): Dieselbe
          # Fehlerklasse wie oben, nur am Herzstück – GitHubs Scheduler
          # startete 4 von 7 planmäßigen Slots nie, der Tag endete 1/2 LIVE,
          # und kein einziger Lauf war rot. Die Wache parst den Soll-Plan aus
          # den Workflow-Dateien (keine zweite Handliste), holt verpasste
          # Slots per Dispatch nach und meldet das Defizit, wenn nichts mehr
          # nachholbar ist. Ihr --selftest stellt den Vorfall nach und
          # gehört ins vertragliche Minimum.
          "slot_wache.py",
          # Zustellbarkeits-Wache (23.09.2026, Lauf #21): Der Versand war
          # dreifach verriegelt, die Kette davor ungeprüft. Ein Lauf meldete
          # „Absender-Problem“ für eine Cloudflare-Signaturblockage vor der API,
          # und die Freischalt-Checkliste schrieb eine SPF-Erweiterung vor, die
          # auf Brevos geteiltem Weg an der Zustellung nichts ändert (DKIM trägt,
          # SPF alignt nie). Die Wache misst Zone UND Konto und sagt zu jedem
          # Befund den exakten Klickweg – ihr --selftest friert die
          # Unterscheidung ein (Kante vs. Anbieter, Messlücke vs. Fund,
          # p=reject nur mit belegtem Domain-DKIM) und gehört ins Minimum.
          "newsletter_zustellbarkeit.py",
          # Werbe-Offenlegung (28.09.2026, Wettbewerbsvergleich ZEIT Online,
          # Dimension „Unabhängigkeit/Kommerz"): Die Kennzeichnung entsteht im
          # Template – also stirbt sie auch dort, lautlos, bei der nächsten
          # Layout-Änderung. Die Wache prüft O1–O7 am gebauten HTML (Existenz,
          # Position vor dem ersten Partnerlink, Zahl/Partner artikelgenau,
          # Pflichtangaben, Sichtbarkeit, Widerspruchsfreiheit, Partnerregister).
          # Ihr --selftest friert 13 Sabotage-Proben ein und gehört ins Minimum.
          "offenlegung_gate.py",
          # Bewertungsraster (03.10.2026, Audit-Befund 8 „Monetarisierung und
          # Vertrauen sauberer austarieren"): Die öffentliche Seite „So
          # entstehen unsere Vergleiche" beantwortet die sieben Audit-Fragen
          # aus drei Quellen (kuratierte Grundsätze, gebackenes Routen-
          # Register, versionierte Methodik). Die Wache prüft V1–V8 am
          # gebauten HTML – Register-Sync in beide Richtungen, Zieltyp-
          # Ehrlichkeit (Einzelangebot nie als „Marktvergleich"), die
          # wörtliche Provisions-Antwort „nein" und die Wegweiser-Kette.
          # Ihr --selftest friert 13 Sabotage-Proben ein und gehört ins
          # Minimum: Ein Raster ohne Wache veraltet in die Unwahrheit.
          "vergleichsgrundsaetze_gate.py",
          # YMYL-Freigabe (02.10.2026): Ein Score ist keine Fachprüfung.
          # Die Wache verlangt Prüfer, Belegkette, Zahlenprotokoll, Termine
          # und bindet jede Freigabe per Hash an exakt eine Textfassung.
          "editorial_review_gate.py",
          # Folge-Reparatur des Gate-Vorfalls (18.09.2026, Folge-Befund 5):
          # Die Frontmatter-Schlussgrenze war in 13 Dateien (9 live) an den
          # ersten Absatz geklebt (`---Text`). Hugo rendert das, aber
          # zeilenweise lesende Wachen werden blind (park_state.set_field
          # liefert still False, compound_guard zählt 0 statt 1) – und eine
          # Live-Seite trug das Prompt-Gerüst „TITEL:/ARTIKEL:". Der Selbsttest
          # der Wache hält Kleber-Erkennung, Naht-Treue, Gerüst-Entfernung und
          # Idempotenz fest; sie heilt über die Naht-SSOT in post_utils.
          "fm_boundary_guard.py",
          # Folge-Reparatur zu Issue #316 (19.09.2026): Der Integritäts-Lock
          # stand auf HARD STOP, weil PR #315 sechs gesperrte Dateien ohne
          # Neu-Signatur gemergt hatte – die Content-Engine starb im ersten
          # Schritt. Der Guard beweist jetzt in seinem `--selftest` an einem
          # echten Mini-Repo: Klassifikation (committet vs. Laufzeit-Mutation),
          # Signatur-Regel (nur FEST + versioniert + == HEAD) und Konvergenz
          # der Heilung. Als Wache im Minimum läuft dieser Beweis in jedem
          # Gate-Durchgang mit – inklusive Uhr-Proben und C15.
          "integrity_guard.py",
          # Pflicht-Check-Vertrag (19.09.2026, Nachtrag zu #316): Das PR-Gate
          # meldete sich als Check „lock" (Job-ID ohne Anzeigename) und wurde
          # unter diesem Namen in ein Ruleset eingetragen, das keinen
          # Ziel-Branch hatte – ein Häkchen, das nichts schützt. Die Wache
          # vergleicht im Gate selbst, ob der Branch-Schutz genau den Check
          # verlangt, der da gerade läuft; ihr Selbsttest beweist die Logik an
          # Kunst-Rulesets ohne Netz (C18).
          "pflichtcheck_guard.py",
          # Reserve-Linie (26.09.2026, #387 – „Content-Reserve rot, obwohl
          # der Content da war"): Drei stille Lecks leerten den Vorrat
          # gleichzeitig. Ein fremder Commit nahm zwei zertifizierten
          # Kandidaten die `reserve`-Fahne (Bestands-Wächter heilt das und
          # führt Buch), und der Nachschub griff sechsmal dasselbe Thema,
          # weil er immer das ERSTE freie nahm (Disposition rotiert jetzt
          # mit Gedächtnis und Cooldown). Beide sind Wachen mit
          # Entscheidungslogik – ohne Selbsttest im Minimum wäre die
          # Reparatur wieder nur eine Zusage.
          "reserve_custody.py", "reserve_topics.py",
          # Messlatte der Reserve (26.09.2026, #393 – „Bot-Watchdog:
          # Automatisierung braucht Eingriff\"): Zielbestand und Alarmschwelle
          # standen an drei Orten, und die entscheidende Kopie lag IM
          # geprüften Zertifikat. Ein magerer Lauf schrieb `target: 4`, der
          # harte End-Gate bestätigte „✅ 4/4" und die Konvergenz reichte die
          # abgesenkte Latte an ihre Kindprozesse weiter, die sie
          # zurückschrieben – eine Ratsche, die das Produktionsziel dauerhaft
          # aussperrte. Weil zugleich Alarmschwelle == Ziel war, öffnete sich
          # das Ticket nach jeder Veröffentlichung neu. Der SSOT rechnet die
          # Schwelle jetzt aus dem Ziel (Invariante 1 ≤ Alarm < Ziel); ohne
          # Selbsttest im Minimum wäre genau diese Invariante wieder nur eine
          # Behauptung.
          "reserve_economy.py",
          # Deploy-Drift-Wache (28.09.2026, #433 – „Deploy-Drift: #431 auf main,
          # aber nicht live“): Prüft Parität zwischen main und gh-pages.
          # Schützt vor Queue-Verdrängung und Skip-Deploy-Täuschung.
          "deploy_drift_guard.py",
          # Release-Scorecard (03.10.2026, Befund 10 „Der Produktionsprozess
          # ist sehr komplex“): EINE sichtbare Produktionswahrheit – acht
          # Dimensionen pro Artikel, gemessen über die Publish-Gate-
          # Collectoren (keine zweite Messregel), versiegelt gegen die
          # veröffentlichte Version. Ihr --selftest friert SSOT-Form,
          # Gate-Deckung, Ausnahmen-Protokoll und Siegel-Bindung ein.
          "release_scorecard.py",
          # Auslieferungs-Melder (07.10.2026, WF-54C4/#610): Am 05.10.2026
          # lieferte der Blog 1/2 Artikel öffentlich; der Kanal dazu hätte
          # JEDEN späteren grünen Beleg als Abschluss akzeptiert – der
          # Fehltag wäre still verschwunden. Seit der Reparatur schließt er
          # nur mit einem Beleg DESSELBEN Tages und verbucht einen
          # vergangenen Fehltag als Quittung („verbucht, nicht behoben“).
          # Ohne Selbsttest im vertraglichen Minimum wäre genau dieser
          # Schließpfad wieder eine unbewachte Zeile.
          "publication_incident.py",
          # Artefakt-Wächter (08.10.2026, WF-D4E0 #653): Sechs Nächte
          # hintereinander meldete der harte End-Gate „0/6 gate-fertig“,
          # obwohl der Vorrat voll war – `data/reserve-readiness.json` war
          # durch ein Merge-Artefakt strukturell kaputt und niemand las es.
          # Ein Maschinen-Artefakt, das niemand gegenliest, ist eine
          # Behauptung: Die Wache prüft alle ~390 JSON/JSONL/YAML/Front-
          # matter-Artefakte des Korpus auf Syntax, doppelte Schlüssel,
          # Zeilenform und Konfliktmarker. Ihr --selftest friert jede
          # Klasse mit Sabotage- und Negativproben ein, ihre
          # --wirkungsprobe die Selbstheilung samt Idempotenz – ohne
          # beides im Minimum wäre die Reparatur wieder nur eine Zusage.
          "artefakt_waechter.py"]
          # Manifest-Wache (WF-7B6B / #654, 08.10.2026): Ein Merge-Rest in
          # package.json (ungültiges JSON) hat den E2E-Lauf und danach zwei
          # Stunden lang jeden Produktions-Deploy rot gemacht – `npm ci` brach
          # in Sekunde 1 ab. Die Wache prüft Manifest und Lockfile vor dem
          # Install. Eine Wache, die niemand verlangt, führt niemand aus –
          # deshalb steht ihr Selbsttest im vertraglichen Minimum (C6).
          "manifest_guard.py"]

# Skripte, die mit der Pinterest-API sprechen, müssen ihren Token vom Broker
# holen. Ausnahmen: der Broker selbst und die Krypto-/OAuth-Schicht darunter.
TOKEN_BROKER = "pinterest_token"

# Kanal der maschinell behebbaren Befunde (Alarm-Routing, C14).
GENERIC_LABEL = "bot-watchdog"
TOKEN_BROKER_EXEMPT = {"pinterest_token.py", "pinterest_auth.py"}
TOKEN_WORKFLOW = "pinterest-token.yml"

# Reihenfolge-Vertrag: diese Schritte sind Messungen, die vor der Sicht liegen müssen
MEASURE_STEPS = ("decay", "cwv", "secrets", "lesbarkeit", "pinperf", "clicks", "awin",
                 "live-policy", "umami-views", "awin-fetch", "revenue-funnel",
                 "click-chain")
VIEW_STEP = "scorecard"


def _read(path):
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


# --------------------------------------------------------------- Schritt-Modell

def step_blocks(workflow_text):
    """YAML grob in `name:`-Schritte zerlegen (der Workflow ist bot-geschrieben,
    deshalb bewusst einfach gehalten – ein voller YAML-Parser wäre hier fragiler)."""
    blocks = []
    cur_name, cur = None, []
    for line in workflow_text.splitlines():
        m = re.match(r"^\s*-\s+name:\s*(.+?)\s*$", line)
        if m:
            if cur_name is not None:
                blocks.append((cur_name, "\n".join(cur)))
            cur_name, cur = m.group(1).strip().strip("'\""), []
            continue
        if cur_name is not None:
            cur.append(line)
    if cur_name is not None:
        blocks.append((cur_name, "\n".join(cur)))
    return blocks


STEP_SIGNATURES = {
    "decay":     (r"--emit\s+decay\b", r"decay_radar\.py"),
    "lesbarkeit": (r"--emit\s+lesbarkeit\b", r"readability_check\.py"),
    "cwv":       (r"--emit\s+cwv\b", r"cwv_guard\.py"),
    "secrets":   (r"--emit\s+secrets\b", r"secrets_age_guard\.py"),
    "pinperf":   (r"--emit\s+pinperf\b", r"pinterest_perf_feedback\.py"),
    "clicks":    (r"--emit\s+clicks\b", r"click_attribution\.py"),
    # (?!-) : `--emit awin\b` würde sonst auch `--emit awin-fetch` „sehen“ –
    # zwei Messschritte, eine Signatur = falsche Reihenfolge-Indizes.
    "awin":      (r"--emit\s+awin\b(?!-)", r"awin_provisions\.py"),
    "live-policy": (r"--emit\s+live-policy\b", r"live_policy_guard\.py"),
    # Umsatz-Messkette: eigene Signaturen, damit die Reihenfolge (Messung vor
    # Sicht) auch für Views-Nenner, API-Abruf, Trichter und Ketten-Guard gilt.
    "umami-views": (r"--emit\s+umami-views\b", r"umami_views\.py"),
    "awin-fetch":  (r"--emit\s+awin-fetch\b", r"awin_fetch\.py"),
    "revenue-funnel": (r"--emit\s+revenue-funnel\b", r"revenue_funnel\.py"),
    "click-chain": (r"--emit\s+click-chain\b", r"click_chain_guard\.py"),
    "scorecard": (r"--emit\s+scorecard\b", r"editorial_scorecard\.py"),
}


def step_index(workflow_text, only=None):
    """Position (Index) der Schritte, die eine Kennzahl messen bzw. bündeln."""
    pos = {}
    for i, (_name, body) in enumerate(step_blocks(workflow_text)):
        if "--selftest" in body:
            continue          # Preflight-Selbsttests sind keine Messläufe
        for step, pats in STEP_SIGNATURES.items():
            if only and step not in only:
                continue
            if any(re.search(pat, body) for pat in pats):
                pos.setdefault(step, i)
    return pos


def c1_ordering(workflow_text):
    """C1: Die Sicht (Scorecard) darf nie vor ihren Messungen laufen."""
    out = []
    idx = step_index(workflow_text)
    if VIEW_STEP not in idx:
        out.append(("C1", "Kein Scorecard-Schritt (scripts/editorial_scorecard.py) im "
                          "Governance-Workflow gefunden."))
        return out
    for step in MEASURE_STEPS:
        if step in idx and idx[step] > idx[VIEW_STEP]:
            out.append(("C1", f"`{step}` (Messung, Schritt {idx[step]}) läuft NACH der "
                              f"Scorecard (Schritt {idx[VIEW_STEP]}) – die Scorecard "
                              "zeigt damit Werte des Vorlaufs. Genau der #206-Fehler: "
                              "AMBER in der Sicht, GREEN im Wächter, -7 Punkte Grund "
                              "in einem Lauf, das nichts mit Performance zu tun hat."))
    return out


def c2_build_not_swallowed(workflow_text):
    out = []
    for name, body in step_blocks(workflow_text):
        if "hugo" not in (name + body).lower():
            continue
        if re.search(r"hugo[^\n]*\|\|\s*true", body):
            out.append(("C2", f"Bau-Schritt „{name}“ verschluckt Hugo-Fehler mit `|| true` "
                              "– ein fehlgeschlagener Build wäre unsichtbar und die "
                              "Performance-Messung würde auf einem leeren/alten Baum grün."))
        if "governance_gate.py --emit build" not in body and "--require-green" not in body:
            if "hugo --minify" in body:
                out.append(("C2", "Hugo-Build meldet sein Ergebnis nicht an das "
                                  "Governance-Gate (`--emit build --require-green`)."))
    return out


def c3_measure_chain_complete(workflow_text, gate_text):
    out = []
    steps = re.findall(r'^\s{4}"([a-z_]+)":\s*\{', gate_text, re.M)
    if not steps:
        steps = re.findall(r'^\s+"([a-z_]+)":\s*\{"', gate_text, re.M)
    for step in steps:
        if step in ("scorecard",):
            continue
        if not re.search(rf"--emit\s+{step}\b", workflow_text):
            out.append(("C3", f"Gate-Kennung `{step}` wird im Governance-Workflow nie "
                              "übermittelt – dieser Befund taucht in keiner Entscheidung auf."))
    return out


def c4_issue_policy(workflow_text):
    out = []
    low = workflow_text
    if "governance_gate.py --decide" not in low:
        out.append(("C4", "Der Workflow entscheidet nicht über `governance_gate.py --decide` "
                          "– damit hängt das Issue an rohen Exit-Codes (Ursache des "
                          "Wochen-Duplikat-Issues #206)."))
    if re.search(r"issues\.create\(", low) and "--decide" not in low:
        out.append(("C4", "Issue-Erzeugung ohne Gate-Entscheidung (creates Duplikate)."))
    if "issues.create(" in low.replace(" ", "") and "gh issue list" not in low \
            and "issues.listForRepo" not in low:
        out.append(("C4", "Issue-Erzeugung ohne Duplikat-Prüfung (listForRepo / gh issue list)."))
    if "governance" in low and "close" not in low.lower():
        out.append(("C4", "Kein Selbstheilungs-Pfad: ein Governance-Issue wird nie "
                          "geschlossen, wenn alles grün ist (action=close fehlt)."))
    return out


def c5_record_provenance(workflow_texts, wachen_quelltext):
    """Nachweis-Provenienz: workflow_texts = dict pfad -> Text.

    `wachen_quelltext` ist der QUELLTEXT von scripts/secrets_age_guard.py,
    daraus werden ausschließlich die registrierten Variablen-NAMEN gelesen –
    niemals Werte (Namensvertrag, Code-Scanning-Alert #78).
    """
    out = []
    known = set(re.findall(r'^\s{4}"([A-Z0-9_]+)":\s*\{', wachen_quelltext, re.M))
    for path, raw_text in workflow_texts.items():
        rel = os.path.basename(path)
        # Shell-Zeilenfortsetzung ( \ + Umbruch ) zusammenziehen, sonst übersieht
        # die Regel ein --proof-by in der Folgezeile.
        text = re.sub(r"\\\s*\n\s*", " ", raw_text)
        for m in re.finditer(r"--record-success\s+([A-Z0-9_]+)([^\n]*)", text):
            var, rest = m.group(1), m.group(2)
            if known and var not in known:
                out.append(("C5", f"{rel}: `--record-success {var}` – Secret nicht in "
                                  "`secrets_age_guard.SECRETS` registriert."))
            if "--proof-by" not in rest:
                out.append(("C5", f"{rel}: Nachweis für `{var}` ohne `--proof-by` – "
                                  "ohne Herkunft ist der Eintrag nicht beweisbar und "
                                  "kann nicht auf Plausibilität geprüft werden."))
        if rel == "premium-governance.yml" and "--record-success" in text:
            out.append(("C5", "premium-governance.yml vermerkt Secret-Erfolg, obwohl der "
                              "Lauf die Secrets nicht benutzt (Selbst-Waschen). "
                              "Stattdessen: `secrets_age_guard.py --verify`."))
        if rel == "premium-governance.yml" and "secrets_age_guard.py" in text \
                and "--verify" not in text:
            out.append(("C5", "premium-governance.yml prüft Secrets ohne Live-Probe "
                              "(`--verify`) – vorhanden ist nicht gleich funktioniert."))
    return out


def c6_selftests(python_bin="python3", quick=False):
    out = []
    if quick:
        for name in GUARDS:
            src = _read(os.path.join(BLOG_DIR, "scripts", name))
            if "--selftest" not in src:
                out.append(("C6", f"scripts/{name} hat keinen `--selftest`."))
        return out
    for name in GUARDS:
        path = os.path.join(BLOG_DIR, "scripts", name)
        if not os.path.exists(path):
            out.append(("C6", f"scripts/{name} fehlt."))
            continue
        try:
            r = subprocess.run([python_bin, path, "--selftest"], cwd=BLOG_DIR,
                               capture_output=True, text=True, timeout=600)
            if r.returncode != 0:
                tail = (r.stdout or r.stderr or "").strip().splitlines()
                last = tail[-1][:160] if tail else "kein Output"
                out.append(("C6", f"scripts/{name} --selftest Exit {r.returncode}: {last}"))
        except (OSError, subprocess.TimeoutExpired) as exc:
            out.append(("C6", f"scripts/{name} --selftest nicht ausführbar: {exc.__class__.__name__}"))
    return out


def c7_data_consistency(report_texts, manifest):
    out = []
    cwv_report = report_texts.get("CWV-REPORT.md", "")
    verdict_report = None
    m = re.search(r"Gesamt-Ampel:\s*\*\*(GREEN|AMBER|RED)\*\*", cwv_report)
    if m:
        verdict_report = m.group(1)
    verdict_manifest = manifest.get("verdict")
    if verdict_report and verdict_manifest and verdict_report != verdict_manifest:
        out.append(("C7", f"CWV-Report sagt {verdict_report}, Manifest {verdict_manifest} – "
                          "zwei Wahrheiten an einem Tag."))
    date_report = None
    m = re.search(r"\*\*Stand:\*\*\s*(\d{4}-\d{2}-\d{2})", cwv_report)
    if m:
        date_report = m.group(1)
    if date_report and manifest.get("generated") and date_report != manifest["generated"]:
        out.append(("C7", f"CWV-Report (Stand {date_report}) und Manifest "
                          f"({manifest.get('generated')}) sind nicht derselbe Lauf – "
                          "die Scorecard liest einen gemischten Stand."))
    scorecard = report_texts.get("EDITORIAL-SCORECARD.md", "")
    if scorecard and verdict_manifest:
        m = re.search(r"Core-Web-Vitals\s*\|\s*([^|]+?)\s*\|", scorecard)
        if m:
            cell = m.group(1)
            allowed = [verdict_manifest] if manifest.get("build_measured", True) else []
            allowed += ["STALE", "nicht gemessen", "nur static/", "UNKNOWN"]
            if not any(a.split(" (")[0] in cell for a in allowed if a):
                out.append(("C7", f"Scorecard-Zeile „Core-Web-Vitals = {cell}"
                                  f"“ passt nicht zum Manifest ({verdict_manifest}, "
                                  "build_measured="
                                  f"{manifest.get('build_measured')}) – die Sicht zeigt "
                                  "einen Stand, den niemand gemessen hat."))
    return out


def add_tokens(workflow_text):
    """Alle Pfade, die ein Workflow mit `git add` staged (für die Hygiene-Regel)."""
    toks = []
    for line in workflow_text.splitlines():
        m = re.match(r"^\s*git add\s+(?!--)(.+)$", line)
        if not m:
            continue
        for raw in re.split(r"[;|]{1,2}", m.group(1)):
            for tok in raw.split():
                tok = re.sub(r"(\s*2>?/?dev/null.*|\s*>\s*/dev/null.*)$", "", tok).strip("'\"")
                if not tok or tok.startswith("-") or "$" in tok or "*" in tok:
                    continue
                toks.append(tok)
    return sorted(set(toks))


def c8_commit_hygiene(workflow_text, ignored_untracked):
    """C8: `git add` auf eine ignorierte, unversionierte Datei bricht den Lauf unter
    `set -e` hart ab – genau die Ursache von #205. Versionierte Dateien (Reports)
    dürfen das, sie sind .gitignore-technisch frei."""
    out = []
    for tok in add_tokens(workflow_text):
        if tok in ignored_untracked:
            out.append(("C8", f"`git add {tok}` – Datei ist .gitignore-ignoriert UND nicht "
                              "versioniert: der Add bricht den Lauf hart ab (vgl. #205). "
                              "Als CI-Artefakt sichern statt committen."))
    return out


LEAK_CHECK_PATTERNS = [
    (r"\bpina_[A-Za-z0-9]{20,}", "Pinterest Access-Token im Klartext"),
    (r"\bpinr_[A-Za-z0-9]{20,}", "Pinterest Refresh-Token im Klartext"),
    (r"\bAIza[0-9A-Za-z_\-]{30,}", "Google/Gemini-API-Key im Klartext"),
    (r"\bgsk_[A-Za-z0-9]{20,}", "Groq-API-Key im Klartext"),
    (r"\bghp_[A-Za-z0-9]{30,}", "GitHub-PAT im Klartext"),
    (r"eyJ[A-Za-z0-9_\-]{20,}\.eyJ", "JWT (Mastodon/OAuth) im Klartext"),
]


def c10_token_broker(script_texts):
    """C10: EINE Token-Wahrheit für den ganzen Pinterest-Betrieb.

    Der teuerste Teil von #206 war nicht der abgelaufene Token, sondern dass
    sechs Skripte sechs verschiedene Reihenfolgen benutzten: Die Wache prüfte
    das Env-Secret, der Bot arbeitete mit dem Auto-Refresh-Speicher. Ein grüner
    Report konnte einen toten Kanal bedeuten – und ein roter einen gesunden.
    """
    out = []
    for name, text in sorted(script_texts.items()):
        if name in TOKEN_BROKER_EXEMPT:
            continue
        if "api.pinterest.com" not in text and "PINTEREST_ACCESS_TOKEN" not in text:
            continue
        uses_broker = TOKEN_BROKER in text
        # Direktzugriff auf das Env-Secret als TOKEN-QUELLE (nicht bloß erwähnt)
        direct = re.search(r"os\.environ(?:\.get\(\s*)?\[?[\"']PINTEREST_ACCESS_TOKEN", text)
        if not uses_broker and direct:
            out.append(("C10", f"scripts/{name}: holt den Pinterest-Token direkt aus dem "
                               "Env statt über `pinterest_token.get_token()` – damit prüft "
                               "die Wache einen anderen Token als der Bot benutzt (#206)."))
        # Hinweis: „… in text“ durchsucht den QUELLTEXT eines Scripts nach der
        # Pinterest-API-Host-Erwähnung (Governance-Regel C10) – das ist
        # Code-Suche, keine URL-Validierung.  # codeql[py/incomplete-url-substring-sanitization]
        if not uses_broker and "api.pinterest.com" in text and not direct:
            out.append(("C10", f"scripts/{name}: spricht mit der Pinterest-API, kennt aber "
                               "den Token-Broker `pinterest_token` nicht – Failover und "
                               "Auto-Erneuerung greifen dort nicht."))
    return out


def c11_token_lifecycle(workflow_texts, root=None):
    """C11: Der Zugang muss sich selbst erneuern – täglich, nachweisbar."""
    out = []
    path = next((p for p in workflow_texts if os.path.basename(p) == TOKEN_WORKFLOW), None)
    if not path:
        out.append(("C11", f"Kein Erneuerungslauf `.github/workflows/{TOKEN_WORKFLOW}` – "
                           "ein Pinterest-Token von Hand stirbt planmäßig nach 30 Tagen "
                           "(genau der Dauerbefund aus #206)."))
        return out
    text = workflow_texts[path]
    if "schedule:" not in text or "cron:" not in text:
        out.append(("C11", f"{TOKEN_WORKFLOW}: kein Zeitplan – eine Erneuerung, die nur "
                           "von Hand läuft, ist keine Erneuerung."))
    if "pinterest_token.py --refresh" not in text:
        out.append(("C11", f"{TOKEN_WORKFLOW}: erneuert den Zugang nicht über "
                           "`pinterest_token.py --refresh`."))
    if "data/pinterest_tokens.enc" not in text:
        out.append(("C11", f"{TOKEN_WORKFLOW}: sichert den rotierten Refresh-Token nicht "
                           "(`data/pinterest_tokens.enc`) – nach 60 Tagen ist der Kanal "
                           "trotz Automatik tot."))
    if "issue close" not in text:
        out.append(("C11", f"{TOKEN_WORKFLOW}: kein Selbstheilungs-Pfad – ein erledigter "
                           "Befund muss sein Issue selbst schließen."))
    if "--selftest" not in text:
        out.append(("C11", f"{TOKEN_WORKFLOW}: fasst Tokens ohne vorherigen Selbsttest an "
                           "(Sabotage-Schutz fehlt)."))
    return out


def c12_label_guarantee(workflow_texts):
    """C12: Ein Melder, der am Melden scheitert, ist schlimmer als kein Melder.

    `gh issue create --label X` schlägt mit HTTP 422 fehl, wenn X im Repository
    nicht existiert. Genau das hat den Pinterest-Watchdog am 07.09.2026 rot
    laufen lassen (#209) – und das Fehler-Alerting öffnete daraufhin ein Issue
    über das Issue, das nicht geschrieben werden konnte.
    """
    out = []
    for path, raw in sorted(workflow_texts.items()):
        rel = os.path.basename(path)
        # Kommentarzeilen raus: In den Kommentaren stehen Beispielbefehle (auch
        # dieser Regel), die sonst als echte Issue-Erzeugung gezählt würden.
        raw = "\n".join(l for l in raw.splitlines()
                         if not l.lstrip().startswith("#"))
        text = re.sub(r"\\\s*\n\s*", " ", raw)          # Zeilenfortsetzungen
        labels = set()
        for m in re.finditer(r"gh issue create[^\n]*", text):
            labels |= {l.strip("\"'`,;") for l in re.findall(r"--label\s+(\S+)", m.group(0))}
        for m in re.finditer(r"labels:\s*\[([^\]]*)\]", text):
            labels |= {l.strip().strip("\"'") for l in m.group(1).split(",") if l.strip()}
        for label in sorted(l for l in labels if l):
            # `--label "$GOV_LABEL"` und `--label governance` sollen beide
            # zum passenden `gh label create` finden – deshalb der nackte Kern.
            var = label.strip('${} "\'')
            pattern = r'gh label create\s+["\']?\$?\{?' + re.escape(var)
            created = (re.search(pattern, text)
                       or re.search(r"issues\.createLabel", text))
            if not created:
                out.append(("C12", f"{rel}: erzeugt Issues mit Label `{label}`, legt es aber "
                                   "nie an (`gh label create … --force`). Fehlt das Label im "
                                   "Repo, scheitert die Meldung mit HTTP 422 (#209)."))
    return out


def c13_proof_integrity(workflow_texts, auth_text=""):
    """C13: Ein Nachweis ohne Probe ist eine Behauptung (#219, 08.09.2026).

    Drei Workflows riefen `secrets_age_guard.py --verify-only PINTEREST_ACCESS_TOKEN`
    OHNE `--verify` auf – es lief nie eine Live-Probe, und das Lagebild stand
    monatelang auf `unverified`. Dazu: Nur die Token-Wache darf den Refresh-
    Token proaktiv rotieren (sonst Kollision), und die Autorisierungs-URL muss
    die echten v5-Scopes anfordern (`read_ads` gibt es nicht; ohne
    `user_accounts:read` antwortet die Broker-Probe /v5/user_account mit 403).
    """
    out = []
    for path, raw in sorted(workflow_texts.items()):
        rel = os.path.basename(path)
        text = "\n".join(l for l in raw.splitlines() if not l.lstrip().startswith("#"))
        text = re.sub(r"\\\s*\n\s*", " ", text)
        for m in re.finditer(r"secrets_age_guard\.py([^\n]*)--verify-only\s+PINTEREST_ACCESS_TOKEN", text):
            if not re.search(r"(^|\s)--verify(\s|$)", m.group(1) + " "):
                out.append(("C13", f"{rel}: prüft den Pinterest-Nachweis mit `--verify-only`, "
                                   "aber ohne `--verify` – es läuft keine Live-Probe, die Wache "
                                   "bleibt `unverified` (#219)."))
        if rel == TOKEN_WORKFLOW and "PINTEREST_TOKEN_WACHE" not in text:
            out.append(("C13", f"{rel}: setzt `PINTEREST_TOKEN_WACHE` nicht – der Broker rotiert "
                               "dann nie proaktiv, der Access-Token stirbt am 30. Tag."))
        if rel != TOKEN_WORKFLOW and re.search(r"PINTEREST_TOKEN_WACHE:\s*[\"']?(1|true|yes|ja)", text):
            out.append(("C13", f"{rel}: gibt sich als Token-Wache aus – zwei Rotierer entwerten "
                               "sich gegenseitig den Refresh-Token."))
    if auth_text:
        m = re.search(r"^DEFAULT_SCOPES\s*=\s*[\"']([^\"']+)[\"']", auth_text, re.M)
        scopes = set(m.group(1).replace(" ", ",").split(",")) if m else set()
        if not m:
            out.append(("C13", "scripts/pinterest_auth.py: keine `DEFAULT_SCOPES` – die "
                               "Autorisierungs-URL ist nicht prüfbar."))
        else:
            bad = [sc for sc in scopes if not re.fullmatch(r"[a-z_]+:(read|write)(_secret)?", sc)]
            if bad:
                out.append(("C13", "scripts/pinterest_auth.py: ungültige v5-Scopes "
                                   f"{sorted(bad)} – Pinterest bricht die Autorisierung ab."))
            for need in ("pins:write", "boards:read", "user_accounts:read"):
                if need not in scopes:
                    out.append(("C13", f"scripts/pinterest_auth.py: Scope `{need}` fehlt – "
                                       + ("die Broker-Probe /v5/user_account liefert 403."
                                          if need == "user_accounts:read"
                                          else "ohne ihn kann der Bot nicht pinnen.")))
    return out


def c9_leak_wache(texts):
    """C9: Findet Zugangs-Material im Klartext in Reports und data/*.json.

    Rückgabe sind ausschließlich BEFUNDE (Dateiname + Muster-Label) – nie der
    gefundene Wert selbst. Die Funktion hieß bis 05.10.2026 `c9_secret_leak`;
    allein dieser Name machte ihren Rückgabewert für CodeQL
    (`SensitiveFunctionCall`) zu „sensiblen Daten“ und damit jede Ausgabe des
    Vertragsberichts zum Klartext-Logging-Befund (Alert #78). Siehe
    CODE-SCANNING-ALERT-78-DAUERHEILUNG-PREMIUM-2026-10-05.md.
    """
    out = []
    for name, text in texts.items():
        for pattern, label in LEAK_CHECK_PATTERNS:
            if re.search(pattern, text):
                out.append(("C9", f"{name}: {label} – Report/Ausgabe dichtet etwas nicht ab."))
    return out


# ------------------------------------------------------------------ Ausführung

def c14_alarm_routing(wflows, script_texts, root=BLOG_DIR):
    """C14: Jeder Alarm hat einen Besitzer, eine Kadenz und einen Schließpfad.

    Auslöser (#272, 12.09.2026): Der Bot-Watchdog kannte nur EINEN Meldeweg.
    Ein Befund, den ausschließlich ein Mensch heilen kann (totes Pinterest-
    Token → OAuth im Browser), lief als „Problem mit der Content-
    Automatisierung" durchs Haus – und weil der automatische Schließpfad
    „grün melden" voraussetzte, das Grün aber am Menschen hing, konnte das
    Ticket NIE zugehen: #251 → #272 → täglich ein neues Gesicht. Ein Melder
    ohne Besitz und ohne Schließpfad ist ein Dauerläufer, kein Melder.

    Geprüft wird dreierlei: der Router existiert und verhält sich richtig,
    der Watchdog meldet ausschließlich über ihn, und menschliche Befunde
    kommen niemals in den Automations-Kanal.
    """
    out = []
    router = script_texts.get("alert_router.py", "")
    watchdog = script_texts.get("bot_watchdog.py", "")
    rel = "bot-watchdog.yml"
    raw = ""
    for path, text in wflows.items():
        if os.path.basename(path) == rel:
            raw = text
    text = "\n".join(l for l in raw.splitlines() if not l.lstrip().startswith("#"))

    # a) Der Router existiert und trägt die vier tragenden Teile.
    if not router.strip():
        out.append(("C14", "scripts/alert_router.py fehlt – ohne ihn gibt es keinen "
                           "Besitzer, keine Kadenz und keinen Schließpfad (#272)."))
    else:
        for needle in ("def plan_generic(", "def plan_channels(", "def tier_for_age(",
                       "class Finding"):
            if needle not in router:
                out.append(("C14", f"scripts/alert_router.py: `{needle}` fehlt – die "
                                   "Router-Logik ist nicht vollständig prüfbar."))

    # b) Der Watchdog meldet über den Router – nicht mit eigenem gh-Aufruf.
    if raw:
        if "--route" not in text:
            out.append(("C14", f"{rel}: kein `bot_watchdog.py --route` – die Meldung läuft "
                               "am Alarm-Router vorbei (Rückfall in den Dauer-Alarm)."))
        if re.search(r"gh issue create", text) and GENERIC_LABEL in text:
            out.append(("C14", f"{rel}: erzeugt Issues mit eigenem `gh issue create` im "
                               f"Kanal `{GENERIC_LABEL}` – Besitz und Kadenz liegen damit "
                               "wieder im YAML statt im Router (#272-Regression)."))

    # c) Verhalten: Besitzer-Trennung + kein Ticket für Mensch-Befunde.
    if watchdog.strip():
        try:
            sys.path.insert(0, os.path.join(root, "scripts"))
            import alert_router as ar
            import bot_watchdog as bw
            mensch = bw._f("pinterest-token", "Token tot", owner="human",
                           channel="pinterest-token")
            maschine = bw._f("cadence", "Kadenz", severity="P1", owner="auto")
            m, h = bw.split_findings([mensch, maschine])
            if len(m) != 1 or len(h) != 1:
                out.append(("C14", "scripts/bot_watchdog.py: split_findings trennt "
                                   "Maschinen- und Menschen-Befunde nicht sauber."))
            decision = ar.plan_generic([mensch], None,
                                       datetime.datetime.now(datetime.timezone.utc))
            if decision.action != "none":
                out.append(("C14", "scripts/bot_watchdog.py: ein menschlicher Befund öffnet "
                                   "das Automations-Ticket – genau die Sackgasse aus #272."))
            offen = ar.IssueRef(number=1,
                                created_at=datetime.datetime.now(datetime.timezone.utc)
                                - datetime.timedelta(days=3))
            if ar.plan_generic([mensch], offen,
                               datetime.datetime.now(datetime.timezone.utc)).action != "close":
                out.append(("C14", "scripts/bot_watchdog.py: ein offenes Automations-Ticket "
                                   "ohne maschinellen Befund wird nicht geschlossen – "
                                   "Schließpfad fehlt (#272)."))
        except Exception as exc:  # Import/Logikfehler sind ein Befund, kein Absturz
            out.append(("C14", f"Alarm-Routing nicht prüfbar: "
                               f"{exc.__class__.__name__}: {exc}"))
    return out



# Wer den Bestand bei JEDEM Aufruf umschreibt (kein Heil-Flag noetig), und wer als
# Laeufer --fix an Kinder weitergibt. Die Listen sind Ergebnis des Audits vom
# 15.09.2026 (alle 165 Skripte nackt und mit --selftest in einer Arbeitskopie,
# gezaehlt nur content/, layouts/, assets/, static/) – bei neuen Workflow-Heilern
# greift Klausel (b) automatisch, die Listen muessen nur bei Befund nachziehen.
HEILER_NACKT = ["fix_spaces.py"]
KETTEN_LEITER = ["blog_doctor.py"]
RE_C15_SCHREIBT = re.compile(r"""open\([^)\n]{0,90}["']w["']|\.write_text\(""")
RE_C15_BEWEIS = re.compile(r"""["']--selftest["']""")
RE_C15_TROCKEN = re.compile(r"""(?m)^\s*(?:dry|dry_run|DRY|DRY_RUN)\s*=[^\n]*"""
                            r"""(?:--selftest|--check|trocken\()|def\s+trocken\(""")
RE_C15_FIX_WEITER = re.compile(r"""kinder_args|child_args|append\(["']--fix["']\)""")


def c15_proof_not_healing(script_texts, wflows):
    """C15: Beweisen ist nicht Heilen.

    Ausloeser (15.09.2026, ohne Ticket – Selbstfund beim Haerten der Kette): Ein
    Prueflauf, der nebenbei heilt, veraendert die Messgroesse, die er pruefen will,
    und sein Ergebnis haengt von der Aufrufreihenfolge ab. Zwei Faelle im Haus:
      * `blog_doctor.py --selftest` leitete DRY nur aus `--dry-run` ab, `kinder_args()`
        zog `--fix` nur im Dry-Run ab – der Selbsttest heilte die ganze Kette und
        legte 13 Artikel um, die der Bericht als „unangetastet" ausgab.
      * `fix_spaces.py` kannte keinen Beweispfad: jedes unbekannte Flag (auch
        `--selftest`) las es als Heilauftrag – 4 Artikel, 8 Korrekturen.
    Der Satz „schreibt bei unbekanntem Flag" wurde empirisch erhoben, nicht statisch
    klassifiziert: eine statische Heil-Schalter-Zaehlung meldete 72 „riskante"
    Skripte, real war es eines (im Haus hetieren --fix, --apply, --live, args.fix und
    „--fix in argv" gleichermassen). Die drei Klauseln sind deshalb eng und beweisbar;
    die Laufzeit-Kopie bleibt der Grundwahrheits-Beweis.
    """
    out = []
    for name in HEILER_NACKT:
        src = script_texts.get(name, "")
        if not src:
            out.append(("C15", f"scripts/{name}: fehlt – die Nacktheiler-Liste muss nach "
                              f"dem nächsten Audit neu gelesen werden."))
            continue
        if not RE_C15_SCHREIBT.search(src):
            out.append(("C15", f"scripts/{name} steht als Nacktheiler, schreibt aber nichts "
                              f"mehr – Liste prüfen."))
            continue
        if not RE_C15_BEWEIS.search(src):
            out.append(("C15", f"scripts/{name} schreibt den Bestand bei jedem Aufruf und hat "
                              f"keinen `--selftest`: Prüfen und Heilen sind nicht zu "
                              f"unterscheiden."))
        elif not RE_C15_TROCKEN.search(src):
            out.append(("C15", f"scripts/{name}: `--selftest` ist nicht als Trockenlauf "
                              f"geführt – der Beweislauf heilt, was er prüfen soll."))
    for pfad, text in sorted(wflows.items()):
        for zeile in text.splitlines():
            code = zeile.strip()
            if code.startswith("#"):
                continue
            m = re.search(r"""scripts/(fix_[a-z0-9_]+\.py)\b""", code)
            if not m:
                continue
            nach = code[code.index(m.group(1)) + len(m.group(1)):].split("||")[0].split("&&")[0]
            if "--" in nach:
                continue                    # Aufruf mit Schalter – keine Nack-Heilung
            name = m.group(1)
            src = script_texts.get(name, "")
            if not src or not RE_C15_SCHREIBT.search(src):
                continue
            if not RE_C15_BEWEIS.search(src):
                out.append(("C15", f"{pfad}: ruft scripts/{name} ohne Schalter auf (heilt "
                                   f"dabei), und das Skript weist keinen `--selftest` aus – "
                                   f"ein Kontrollauftrag ist hier nicht möglich."))
    for name in KETTEN_LEITER:
        src = script_texts.get(name, "")
        if src and RE_C15_FIX_WEITER.search(src) and not RE_C15_TROCKEN.search(src):
            out.append(("C15", f"scripts/{name} gibt `--fix` an seine Kinder weiter, ohne "
                              f"`--selftest` als Trockenlauf zu führen – der Selbsttest "
                              f"heilt die Kette."))
    return out


# --- C16: Wache-Herzschlag (Lebenszeichen != Befund, Ursache #281) ----------
# Auslöser (15.09.2026, Ticket #281): Der Bot-Watchdog meldete „Integritäts-Wache
# schweigt: State 64 h alt" – obwohl die Wache jeden Tag fehlerfrei lief. Das
# Gate schrieb seinen Zustand „konvergent" (nur bei geändertem Befund), der
# Zeitstempel fror an ruhigen Tagen ein, und genau dieser Zeitstempel war die
# Frische-Prüfung. Ein Befund-Zeitstempel beweist keinen Lauf.
# Die Regel prüft beide teuren Fehlerrichtungen: ein Lebenszeichen darf keinen
# Deploy auslösen (Queue-Belastung, Audit F1), ein Site-Pfad darf nie als
# deploy-irrelevant durchrutschen (unveröffentlichter Artikel).
RE_C16_LAUFEVIDENZ = re.compile(r"""workflow_run_evidence\(""")
RE_C16_ESKALATION = re.compile(r"""AFFILIATE_STATE_ESCALATE_HOURS\s*=""")
RE_C16_STATE_ONLY = re.compile(r"""STATE_ONLY='([^']+)'""")
C16_LEBENSZEICHEN = (".affiliate_integrity_state.json", "AFFILIATE-INTEGRITY-REPORT.md")
C16_SITE_PFADE = ("content/posts/2026-09-15-beispiel/index.md",
                  "layouts/_default/baseof.html", "assets/css/extended/custom.css",
                  "static/images/cover.jpg", "hugo.toml")


def c16_heartbeat(deploy_text, script_texts):
    """C16: Ein Lebenszeichen ist kein Inhalt – ein Befund kein Lebenszeichen.

    Drei Klauseln, jede mit einer echten Fehlerrichtung aus #281:
      (a) Der Watchdog belegt die Frische AUCH über fehlerfreie Läufe
          (`workflow_run_evidence`) und kennt eine Eskalationsgrenze fuer den
          Fall, dass der Nachweis dauerhaft nicht im Repo landet.
      (b) Der Lebenszeichen-Pfad ist in der Deploy-Negativliste, und die
          Negativliste laesst keinen Site-Pfad durch (beide Richtungen).
      (c) Der Herzschlag-Beweis laeuft in der Governance mit: `affiliate_
          integrity_gate.py` steht in GUARDS, sein `--selftest` friert ein,
          dass ein zweiter Lauf mit gleichem Befund den Zeitstempel erneuert.
    """
    out = []
    watchdog = script_texts.get("bot_watchdog.py", "")
    if not watchdog:
        out.append(("C16", "scripts/bot_watchdog.py fehlt – die Frische der Affiliate-"
                           "Wache ist nicht prüfbar."))
    else:
        if not RE_C16_LAUFEVIDENZ.search(watchdog):
            out.append(("C16", "scripts/bot_watchdog.py: keine Lauf-Evidenz "
                               "(`workflow_run_evidence`) – die Frische der Wache hinge "
                               "wieder allein an einem Zeitstempel (#281)."))
        if not RE_C16_ESKALATION.search(watchdog):
            out.append(("C16", "scripts/bot_watchdog.py: keine Eskalationsgrenze fuer den "
                               "Herzschlag (`AFFILIATE_STATE_ESCALATE_HOURS`) – ein "
                               "dauerhaft fehlender Nachweis bliebe unsichtbar."))
    m = RE_C16_STATE_ONLY.search(deploy_text or "")
    if not m:
        out.append(("C16", "deploy.yml: STATE_ONLY-Negativliste fehlt – ein Lebenszeichen "
                           "würde einen vollen Deploy (inkl. Vertonung) auslösen."))
    else:
        try:
            rx = re.compile(m.group(1))
        except re.error as exc:
            out.append(("C16", f"deploy.yml: STATE_ONLY-Muster ist kein gültiger Ausdruck ({exc})."))
            rx = None
        if rx is not None:
            for pfad in C16_LEBENSZEICHEN:
                if not rx.match(pfad):
                    out.append(("C16", f"deploy.yml: `{pfad}` gilt als deploy-relevant – ein "
                                       f"Lebenszeichen darf keinen Livegang auslösen (#281)."))
            for pfad in C16_SITE_PFADE:
                if rx.match(pfad):
                    out.append(("C16", f"deploy.yml: `{pfad}` gilt als deploy-irrelevant – ein "
                                       f"Site-Pfad darf nie still übersprungen werden."))
    if "affiliate_integrity_gate.py" not in GUARDS:
        out.append(("C16", "scripts/affiliate_integrity_gate.py steht nicht in GUARDS – der "
                           "Herzschlag-Selbsttest (C6) läuft in keiner Governance-Prüfung."))
    return out


def c17_pinterest_duplicate_guard(script_texts, wflows, root=BLOG_DIR):
    """C17: Pinterest-Duplikate (P4) sind ein Spam-Signal – der Guard muss existieren
    und in den relevanten Workflows laufen (Watchdog + Content-Engine).

    Hintergrund #305: Zwei Artikel mit identischer pin_description führten zum
    Issue "Pinterest-Check: Probleme gefunden". Der Guard heilt Duplikate
    deterministisch und ist idempotent. Ohne ihn kehrt das Spam-Risiko zurück.
    """
    out = []
    guard_path = os.path.join(root, "scripts", "pinterest_duplicate_guard.py")
    if not os.path.exists(guard_path):
        out.append(("C17", "scripts/pinterest_duplicate_guard.py fehlt – kein Schutz gegen DUPLIKAT-Description (P4) (#305)."))
        return out
    guard_text = script_texts.get("pinterest_duplicate_guard.py", "")
    if "_unique_desc" not in guard_text or "_unique_title" not in guard_text:
        out.append(("C17", "pinterest_duplicate_guard.py: Unique-Generator fehlt – Duplikate würden nicht geheilt."))
    # Workflows prüfen
    watchdog = ""
    for p, txt in wflows.items():
        if "pinterest-watchdog" in p:
            watchdog = txt
            break
    if watchdog and "pinterest_duplicate_guard" not in watchdog:
        out.append(("C17", "pinterest-watchdog.yml: ruft pinterest_duplicate_guard nicht auf – Duplikate würden erst spät erkannt (#305)."))
    engine = ""
    for p, txt in wflows.items():
        if "content-engine-v2" in p:
            engine = txt
            break
    if engine and "pinterest_duplicate_guard" not in engine:
        out.append(("C17", "content-engine-v2.yml: ruft pinterest_duplicate_guard nicht auf – neue Artikel könnten mit Duplikat live gehen (#305)."))
    return out


# --- C19: Release-Scorecard – die SSOT der Produktionswahrheit -------------
RELEASE_SSOT = os.path.join("data", "release_scorecard.yaml")
RELEASE_ENGINE = "release_scorecard.py"


def c19_release_ssot(script_texts, root=BLOG_DIR):
    """C19: Die Produktionswahrheit ist deklariert, deckungsgleich und versiegelt.

    Auslöser (03.10.2026, Audit-Befund 10 „Der Produktionsprozess ist sehr
    komplex“): Das Repo hat viele Gates, Reports, Zustandsdateien und Wachen –
    aber niemand konnte auf einen Blick sagen, welche Checks veröffentlichen
    blockieren, welche nur warnen, wer bei fachlichen Konflikten entscheidet
    und ob die VERÖFFENTLICHTE Version wirklich die geprüfte ist. Die Antwort
    ist die Release-Scorecard (scripts/release_scorecard.py) mit ihrer
    deklarativen SSOT (data/release_scorecard.yaml).

    Dieser Vertrag verhindert die drei Arten, wie eine solche Wahrheit
    still verrotet:
      a) SSOT fehlt/unvollständig → die Sicht erfindet ihre eigene Wahrheit.
      b) Eine harte Publish-Gate-Familie ist nicht (mehr) als blockierend
         deklariert → die Scorecard verschweigt live blockierende Gates
         (Scheingrün in Reinform, vgl. die „Wache, die eine Blockade nur
         versprach“, 02.10.2026).
      c) Die Engine misst nicht (mehr) über die Publish-Gate-Collectoren →
         zwei Messregeln, zwei Ampeln (Lektion „Themen haben zwei Bahnen“).
    """
    out = []
    engine = script_texts.get(RELEASE_ENGINE, "")
    if not engine.strip():
        out.append((f"C19", f"scripts/{RELEASE_ENGINE} fehlt – die Produktions-"
                             "wahrheit (Befund 10) hat keine Engine."))
        return out
    ssot_pfad = os.path.join(root, RELEASE_SSOT)
    if not os.path.isfile(ssot_pfad):
        out.append((f"C19", f"{RELEASE_SSOT} fehlt – ohne deklarierte Wahrheit "
                             "(blockiert/warnt, Besitz, Eskalation) ist die "
                             "Scorecard eine Sicht, die lügt."))
        return out

    sys.path.insert(0, os.path.join(root, "scripts"))
    try:
        import release_scorecard as rs  # noqa: PLC0415
    except Exception as exc:  # noqa: BLE001 – Importfehler ist ein Befund
        out.append((f"C19", f"scripts/{RELEASE_ENGINE} nicht importierbar: {exc}"))
        return out

    try:
        ssot = rs.ssot_laden(Path(ssot_pfad))
    except Exception as exc:  # noqa: BLE001 – Konfigurationsfehler ist ein Befund
        out.append((f"C19", f"{RELEASE_SSOT} unzulässig: {exc}"))
        ssot = None
    if ssot is not None:
        fehler = rs.ssot_pruefen(ssot)
        for f in fehler:
            out.append((f"C19", f"{RELEASE_SSOT}: {f}"))
        # Frage 3–6 brauchen einen Ort mit Antworten, nicht nur Checks.
        for block in ("eskalation", "falschpositive", "freigabeprozess", "siegel"):
            if block not in ssot:
                out.append((f"C19", f"{RELEASE_SSOT}: Block `{block}` fehlt – die "
                                    "Antworten auf die sechs Fragen der "
                                    "Produktionswahrheit müssen deklariert sein."))
        # Ausnahmen: Pflichtfelder + nicht ausnehmbare Checks (Frage 4).
        heute = datetime.date.today()
        try:
            rs.ausnahmen_aufbereiten(ssot, heute)
        except rs.KonfigurationsFehler as exc:
            out.append((f"C19", f"{RELEASE_SSOT}: unzulässige Ausnahme – {exc}"))

    # c) Die Engine muss über die Publish-Gate-Collectoren messen (Quelltext-
    #    Vertrag, gespiegelt in scripts/tests/test_release_scorecard.py).
    #    Editorial-Familie: erlaubt ist auch der Direktaufruf der Messfunktion
    #    `editorial_review_gate.evaluate_path` – genau das ruft die Collector-
    #    Funktion des Publish-Gates intern auf (keine zweite Messregel).
    for collector in ("check_length_failures", "seo_audit_failures",
                      "affiliate_profi_failures", "affiliate_integrity_failures",
                      "affiliate_intent_failures", "offenlegung_failures",
                      "title_integrity_failures", "keyword_failures",
                      "readability_failures", "textverstaendnis_failures"):
        if f"publish_gate.{collector}" not in engine and f".{collector}(" not in engine:
            out.append((f"C19", f"scripts/{RELEASE_ENGINE}: misst nicht über "
                                f"`publish_gate.{collector}` – eine zweite "
                                "Messregel wäre eine zweite Ampel."))
            break
    editorial_ueber_collector = "publish_gate.editorial_review_failures" in engine
    editorial_ueber_messfunktion = ("editorial_review_gate" in engine
                                    and "evaluate_path(" in engine)
    if not (editorial_ueber_collector or editorial_ueber_messfunktion):
        out.append((f"C19", f"scripts/{RELEASE_ENGINE}: misst nicht über "
                            "`publish_gate.editorial_review_failures` oder "
                            "`editorial_review_gate.evaluate_path` – eine zweite "
                            "Messregel wäre eine zweite Ampel."))
    if "DRY_RUN = True" not in engine:
        out.append((f"C19", f"scripts/{RELEASE_ENGINE}: erzwingt keinen Beweislauf "
                            "(publish_gate.DRY_RUN = True fehlt) – die Scorecard "
                            "dürfte nebenbei heilen (C15-Verstoß)."))
    if RELEASE_ENGINE not in GUARDS:
        out.append((f"C19", f"scripts/{RELEASE_ENGINE} steht nicht in GUARDS – ihr "
                            "Selbsttest läuft nicht im vertraglichen Minimum (C6)."))
    return out


# --- C20: Lesbarkeits-Vertrag + Deploy-Hysterese (Governance-Report #585) ---
# Auslöser (05.10.2026, #585): Zwei Befunde, eine gemeinsame Bauart – eine Wache
# meldete etwas, das ein anderer Teil der Kette hätte verhindern bzw. gar nicht
# erst als Fehler werten dürfen.
#   · Lesbarkeit: 9 Live-Artikel lagen unter dem Bestands-Floor (55), der Ø unter
#     dem Ziel (62). Möglich war das, weil das Publish-Tor NUR den zusammen-
#     gesetzten Score (< 75) prüfte. Ein Flesch von 47 kostet dort 20 Punkte –
#     zu wenig, um zu blocken. Die Bestands-Wache durfte also hinterher melden,
#     was das Tor vorher durchgelassen hat. Eine Wache ohne Tor ist ein Protokoll.
#   · Live-Konsistenz: Die Live-Wache lief im selben Lauf, in dem veröffentlicht
#     wurde, und wertete die Laufzeit von Build + Pages-Deploy + CDN als Drift.
#     Dauer-Rot ohne Handlung ist Alarm-Müdigkeit.
# Beide Reparaturen sind strukturell und müssen strukturell verteidigt werden:
# das Tor darf die Flesch-Schwelle nicht wieder verlieren, die Schwelle muss die
# importierte SSOT bleiben (nie eine Kopie), das Deploy-Fenster muss endlich und
# konfigurierbar sein, und sein Hinweis-Code darf nie ein Issue erzeugen.
def c20_lesbarkeit_und_hysterese(script_texts, gate_text):
    out = []
    pg = script_texts.get("publish_gate.py", "")
    rc = script_texts.get("readability_check.py", "")
    lp = script_texts.get("live_policy_guard.py", "")
    if not pg or not rc or not lp:
        out.append(("C20", "publish_gate.py / readability_check.py / "
                           "live_policy_guard.py nicht lesbar – der Vertrag ist "
                           "nicht prüfbar."))
        return out

    # a) Das Publish-Tor prüft die Flesch-Schwelle, nicht nur den Score.
    start = pg.find("def readability_failures(")
    ende = pg.find("\ndef ", start + 1) if start >= 0 else -1
    block = pg[start:ende] if start >= 0 and ende > start else ""
    if not block:
        out.append(("C20", "scripts/publish_gate.py: `readability_failures` fehlt – "
                           "ohne Collector gibt es kein Lesbarkeits-Tor (#585)."))
    else:
        if "NEW_FLESCH_MIN" not in block:
            out.append(("C20", "scripts/publish_gate.py: `readability_failures` prüft "
                               "`NEW_FLESCH_MIN` nicht – ein Artikel mit Flesch 47 "
                               "käme wieder durch das Tor und zöge den Bestand unter "
                               "das Ziel (#585)."))
        if "from readability_check import" not in block:
            out.append(("C20", "scripts/publish_gate.py: `readability_failures` "
                               "importiert die Schwelle nicht aus `readability_check` – "
                               "eine kopierte Zahl ist eine zweite Wahrheit (#585)."))
        if re.search(r"NEW_FLESCH_MIN\s*=", block):
            out.append(("C20", "scripts/publish_gate.py: definiert `NEW_FLESCH_MIN` "
                               "selbst – die Schwelle gehört in readability_check (SSOT)."))

    # b) Die Schwellen der SSOT bleiben, wo sie sind (Absenken = Sabotage).
    for name, mindest in (("AVG_TARGET", 62.0), ("NEW_FLESCH_MIN", 60.0)):
        m = re.search(rf"(?m)^{name}\s*=\s*([0-9.]+)", rc)
        if not m:
            out.append(("C20", f"scripts/readability_check.py: `{name}` fehlt – die "
                               "Lesbarkeits-SSOT ist nicht mehr auffindbar."))
        elif float(m.group(1)) < mindest:
            out.append(("C20", f"scripts/readability_check.py: `{name}` = {m.group(1)} "
                               f"liegt unter dem vertraglichen Mindestwert {mindest:g} – "
                               "ein abgesenktes Ziel heilt nichts, es misst nur anders."))
    m = re.search(r"(?m)^FLOOR_MIN\s*=\s*([0-9.]+)", rc)
    if not m:
        out.append(("C20", "scripts/readability_check.py: `FLOOR_MIN` fehlt."))
    elif float(m.group(1)) > 55.0:
        out.append(("C20", f"scripts/readability_check.py: `FLOOR_MIN` = {m.group(1)} "
                           "wurde angehoben – der Bestands-Boden darf nicht weicher "
                           "werden als 55."))

    # c) Das Deploy-Fenster ist endlich, konfigurierbar und läuft ab.
    if "GRACE_MIN" not in lp:
        out.append(("C20", "scripts/live_policy_guard.py: kein Deploy-Fenster "
                           "(`GRACE_MIN`) – die Wache wertet die Auslieferungszeit "
                           "wieder als Drift (#585)."))
    else:
        if "LIVE_POLICY_GRACE_MIN" not in lp:
            out.append(("C20", "scripts/live_policy_guard.py: das Deploy-Fenster ist "
                               "nicht über `LIVE_POLICY_GRACE_MIN` einstellbar."))
        m = re.search(r'LIVE_POLICY_GRACE_MIN["\']?,\s*["\']([0-9.]+)["\']', lp)
        if m and float(m.group(1)) > 180:
            out.append(("C20", f"scripts/live_policy_guard.py: Deploy-Fenster "
                               f"{m.group(1)} min ist zu groß – ein Fenster, das länger "
                               "offen steht als ein Deploy dauert, verdeckt echte Drift."))
    if "HYSTERESE_CODE" not in lp:
        out.append(("C20", "scripts/live_policy_guard.py: Hysterese-Hinweise tragen "
                           "keinen eigenen Code – sie liefen unter dem Namen des "
                           "Fehlers, den sie gerade ausschließen."))
    if "deploy_hysterese" not in gate_text:
        out.append(("C20", "scripts/governance_gate.py: `deploy_hysterese` steht nicht "
                           "in der Ledger-Policy – ein Hinweis ohne Einstufung wird "
                           "entweder zum Issue oder zum blinden Fleck (#585)."))
    elif "INFO_AMBER" in gate_text:
        info = gate_text[gate_text.find("INFO_AMBER"):]
        info = info[:info.find("}") + 1]
        if "deploy_hysterese" not in info:
            out.append(("C20", "scripts/governance_gate.py: `deploy_hysterese` ist "
                               "nicht als INFO_AMBER eingestuft – die Deploy-Laufzeit "
                               "würde wieder ein Issue erzeugen."))
    return out

# --- C21: Maschinell eingefügte Sätze (Nachtrag zu #585, 05.10.2026) ---
# Auslöser: Die Keyword-Heilung schrieb „Mit dem richtigen Vorgehen lässt sich
# die gasrechnung senken um bis zu 15 % senken." in einen Live-Artikel – das
# Keyword gebeugt, kleingeschrieben und das Verb doppelt. Niemand hat es
# gesehen: Die Lesbarkeits-Wache misst Satz- und Wortlängen, keine Grammatik,
# und der Artikel stand mit Flesch 79 glänzend da. Eine Maschine, die Sätze in
# fremde Texte schreibt, kennt die Wortart des eingesetzten Keywords nicht –
# deshalb darf sie es NIE in eine Satzgrammatik einpassen (`.lower()`,
# Deklination, feste Schablonen mit Verb). Erlaubt ist nur die Apposition nach
# Doppelpunkt, und was trotzdem durchrutscht, fängt R17 im Verständnis-Guard.
def c21_maschinensaetze(script_texts):
    out = []
    ko = script_texts.get("keyword_optimizer.py", "")
    tg = script_texts.get("textverstaendnis_guard.py", "")
    pg = script_texts.get("publish_gate.py", "")
    if not ko or not tg or not pg:
        out.append(("C21", "keyword_optimizer.py / textverstaendnis_guard.py / "
                           "publish_gate.py nicht lesbar – der Vertrag ist nicht prüfbar."))
        return out
    start = ko.find("def heal_density(")
    ende = ko.find("\ndef ", start + 1) if start >= 0 else -1
    block = ko[start:ende] if start >= 0 and ende > start else ""
    if not block:
        out.append(("C21", "scripts/keyword_optimizer.py: `heal_density` fehlt."))
    else:
        if re.search(r"main_kw\.lower\(\)", block):
            out.append(("C21", "scripts/keyword_optimizer.py: `heal_density` beugt das "
                               "Keyword mit `.lower()` – deutsche Substantive werden "
                               "kleingeschrieben eingesetzt (#585-Nachtrag)."))
        if "dichte_saetze" not in block:
            out.append(("C21", "scripts/keyword_optimizer.py: `heal_density` benutzt die "
                               "geprüfte Satz-SSOT `dichte_saetze` nicht – freie "
                               "Schablonen im Heiler sind grammatisch ungedeckt."))
        if "in body" not in block:
            out.append(("C21", "scripts/keyword_optimizer.py: `heal_density` prüft nicht "
                               "auf bereits vorhandene Sätze – die Heilung wäre nicht "
                               "idempotent."))
    for schablone in re.findall(r'"([^"]*\{kw\}[^"]*)"', ko):
        # Erlaubt ist genau eine Form: vollständiger Satz, Doppelpunkt,
        # Keyword, Punkt. Alles andere stellt Wörter NACH das Keyword – und
        # genau dort entstand die Ruine („… {kw} um bis zu 15 % senken.").
        if ":" not in schablone.split("{kw}")[0] or not schablone.rstrip().endswith("{kw}."):
            out.append(("C21", f"scripts/keyword_optimizer.py: Schablone „{schablone}“ "
                               "setzt das Keyword mitten in die Satzgrammatik – erlaubt "
                               "ist nur die Apposition nach Doppelpunkt am Satzende."))
    if "R17-KEYWORD-KASUS" not in tg or "R17-KEYWORD-DOPPEL" not in tg:
        out.append(("C21", "scripts/textverstaendnis_guard.py: R17 (Keyword-Ruinen) "
                           "fehlt – kleingeschriebene Keyword-Substantive und doppelte "
                           "Verben blieben unsichtbar."))
    if "R17-KEYWORD-KASUS" not in pg or "R17-KEYWORD-DOPPEL" not in pg:
        out.append(("C21", "scripts/publish_gate.py: R17 steht nicht unter den harten "
                           "Regeln – eine Keyword-Ruine könnte erneut live gehen."))
    return out

# --- C22: Publikations-Vertrag auf der SCHREIB-Seite (WF-54C4/#607, 07.10.2026) ---
# Auslöser: Die KI-Heilung prüfte die STRUKTUR ihrer Änderung (Links, H2-Anzahl,
# Länge, Trennlinien) – aber nicht die Regeln, die über die Veröffentlichung
# entscheiden. Am 05.10.2026 um 22:20 UTC schrieb sie den Live-Artikel
# `2026-09-10-energie-update-…` von Flesch 68,7 auf 44,3 und fügte „In diesem
# Beitrag erfährst du …“ ein. Der nächste Deploy-Lauf (22:27 UTC) blockierte
# korrekt – Exit 1, roter Produktionsalarm WF-54C4, abgebrochener Deploy.
# Die Lehre aus #585 war „eine Wache ohne Tor ist ein Protokoll“; hier ist die
# Umkehrung: Ein Schreiber ohne Tor ist ein Blocker-Produzent. Der Vertrag V1–V3
# (scripts/publikations_vertrag.py) sitzt deshalb zwischen KI und Schreiben:
#   V1 Lesbarkeit  – importierte SSOT `readability_check.NEW_FLESCH_MIN`,
#                    keine zweite Zahl.
#   V2 Verständnis – nur NEUE harte Funde, Regelliste importiert aus
#                    `publish_gate.HARTE_REGELN` (dieselbe wie am Gate).
#   V3 Messbarkeit – nicht messbar heißt verworfen (fail-closed).
# Was hier bewacht wird, ist der Weg, nicht das Ergebnis: Wer den Aufruf
# entfernt, das Urteil weichzeichnet oder die Schwellen kopiert, verliert die
# Heilung, ohne dass ein Test rot würde – genau die Lücke, die #607 möglich
# machte.
def c22_publikations_vertrag(script_texts, root=BLOG_DIR):
    out = []
    vertrag = script_texts.get("publikations_vertrag.py", "")
    schreiber = script_texts.get("redaktions_standard.py", "")
    pg = script_texts.get("publish_gate.py", "")
    if not vertrag or not schreiber or not pg:
        out.append(("C22", "publikations_vertrag.py / redaktions_standard.py / "
                           "publish_gate.py nicht lesbar – der Vertrag ist nicht prüfbar."))
        return out

    # a) Der Selbsttest der Wache läuft im vertraglichen Minimum (C6).
    if "publikations_vertrag.py" not in GUARDS:
        out.append(("C22", "scripts/publikations_vertrag.py steht nicht in GUARDS – "
                           "sein Sabotage-Selbsttest liefe nicht in C6, und eine Wache, "
                           "die niemand verlangt, läuft irgendwann niemand mehr."))

    # b) Der Schreiber kennt den Vertrag und wendet ihn VOR dem Schreiben an.
    if "from publikations_vertrag import" not in schreiber:
        out.append(("C22", "scripts/redaktions_standard.py importiert den "
                           "Publikations-Vertrag nicht – die KI-Heilung schriebe wie am "
                           "05.10.2026 ungeprüft in Live-Artikel (#607)."))
    start = schreiber.find("def heal_article_ai(")
    ende = schreiber.find("\ndef ", start + 1) if start >= 0 else -1
    block = schreiber[start:ende] if start >= 0 and ende > start else ""
    if not block:
        out.append(("C22", "scripts/redaktions_standard.py: `heal_article_ai` fehlt – "
                           "ohne diese Funktion ist die KI-Strecke nicht prüfbar."))
    else:
        if "_vertrag_gruende(" not in block:
            out.append(("C22", "scripts/redaktions_standard.py: `heal_article_ai` ruft "
                               "`_vertrag_gruende` nicht auf – die KI-Änderung ginge ohne "
                               "Flesch-/R7-Prüfung in die Datei."))
        if "return None" not in block:
            out.append(("C22", "scripts/redaktions_standard.py: `heal_article_ai` verwirft "
                               "bei Verstoß nicht (kein `return None`) – der Vertrag wäre "
                               "eine Empfehlung statt einer Wache."))
    start = schreiber.find("def _vertrag_gruende(")
    ende = schreiber.find("\ndef ", start + 1) if start >= 0 else -1
    block = schreiber[start:ende] if start >= 0 and ende > start else ""
    if not block:
        out.append(("C22", "scripts/redaktions_standard.py: `_vertrag_gruende` fehlt – "
                           "die Vertragsprüfung ist nicht verdrahtet."))
    else:
        if "_vertrag_pruefe is None" not in block:
            out.append(("C22", "scripts/redaktions_standard.py: `_vertrag_gruende` kennt "
                               "den Fall „Vertrag nicht verfügbar“ nicht – ohne Import "
                               "wäre die Heilung stillschweigend freigegeben (fail-open)."))
        if "join_article(a[\"fm\"], neu_body)" not in block:
            out.append(("C22", "scripts/redaktions_standard.py: `_vertrag_gruende` misst "
                               "nicht den kanonischen Rohtext (`join_article(a[\"fm\"], "
                               "neu_body)`) – gemessen würde etwas anderes als das "
                               "Geschriebene."))

    # c) Der Vertrag selbst: Schwellen importiert, nicht kopiert; neue Funde nur
    #    als Differenz; Unmessbarkeit ein Verstoß.
    if "def pruefe(" not in vertrag:
        out.append(("C22", "scripts/publikations_vertrag.py: `pruefe(` fehlt."))
    if "readability_check.NEW_FLESCH_MIN" not in vertrag:
        out.append(("C22", "scripts/publikations_vertrag.py: benutzt nicht die importierte "
                           "Schwelle `readability_check.NEW_FLESCH_MIN` – eine zweite Zahl "
                           "wäre ein zweiter Maßstab (#585)."))
    if re.search(r"(?m)^NEW_FLESCH_MIN\s*=", vertrag):
        out.append(("C22", "scripts/publikations_vertrag.py: definiert `NEW_FLESCH_MIN` "
                           "selbst – die Schwelle gehört in readability_check (SSOT)."))
    if "parse_article" not in vertrag:
        out.append(("C22", "scripts/publikations_vertrag.py: nutzt nicht "
                           "`readability_check.parse_article` – eine Messung erst nach dem "
                           "Schreiben verhindert keinen Blocker."))
    if "publish_gate.HARTE_REGELN" not in vertrag:
        out.append(("C22", "scripts/publikations_vertrag.py: prüft das Textverständnis nicht "
                           "gegen die importierte Regelliste `publish_gate.HARTE_REGELN` – "
                           "Schreiber und Gate könnten verschiedene Regeln kennen (#607)."))
    if "check_article" not in vertrag:
        out.append(("C22", "scripts/publikations_vertrag.py: ruft den Verständnis-Detektor "
                           "`textverstaendnis_guard.check_article` nicht auf."))
    if "V3" not in vertrag:
        out.append(("C22", "scripts/publikations_vertrag.py: kein V3-Fall – „nicht "
                           "gemessen“ könnte als „freigegeben“ durchgehen (fail-open)."))

    # d) Die Gate-Seite bleibt die eine Quelle der harten Regeln.
    if not re.search(r"(?m)^HARTE_REGELN\s*=", pg):
        out.append(("C22", "scripts/publish_gate.py: `HARTE_REGELN` steht nicht auf "
                           "Modulebene – Schreiber und Gate hätten je eine eigene Liste."))
    start = pg.find("def textverstaendnis_failures(")
    ende = pg.find("\ndef ", start + 1) if start >= 0 else -1
    block = pg[start:ende] if start >= 0 and ende > start else ""
    if not block:
        out.append(("C22", "scripts/publish_gate.py: `textverstaendnis_failures` fehlt."))
    elif "HARTE_REGELN" not in block:
        out.append(("C22", "scripts/publish_gate.py: `textverstaendnis_failures` nutzt "
                           "nicht die SSOT `HARTE_REGELN` – die Blockade des Gates und die "
                           "Prüfung des Schreibers liefen auseinander."))

    # e) Der reale Vorfall bleibt als Beweismittel eingefroren (kein Nachbau).
    sim_dir = os.path.join(root, "scripts", "tests", "sim", "wf54c4")
    if "wf54c4" not in vertrag:
        out.append(("C22", "scripts/publikations_vertrag.py: die eingefrorene Vorfallprobe "
                           "WF-54C4 wird nicht mehr geladen."))
    for name in ("vorher.md", "nachher.md"):
        pfad = os.path.join(sim_dir, name)
        if not os.path.exists(pfad) or os.path.getsize(pfad) < 500:
            out.append(("C22", f"Vorfall-Material fehlt oder ist unbrauchbar: "
                               f"scripts/tests/sim/wf54c4/{name} – ohne den echten Text "
                               f"prüft der Vertrag nur gegen Nachbauten."))
    return out

# --- C18: Pflicht-Check-Vertrag (der Name im Branch-Schutz ist ein Vertrag) ---
# Auslöser (19.09.2026, Nachtrag zu #316 / PR #317): Das neue PR-Gate
# integrity-lock.yml meldete sich bei GitHub als Check „lock" – die Job-ID, weil
# der Job keinen Anzeigenamen trug. Unter genau diesem Namen wurde es als
# Pflicht-Check in ein Ruleset eingetragen … das keinen Ziel-Branch hatte
# (`include: []`): ein aktives Häkchen, das nichts schützte. Ein Pflicht-Check
# ist ein Vertrag zwischen Workflow-Datei und Repository-Einstellung, den keine
# Seite allein einhalten kann. Drei Fehlerrichtungen, alle still:
#   · Job umbenannt, Ruleset nicht: jeder PR wartet auf einen Check, der nie
#     berichtet („Expected") – main ist eingefroren.
#   · `paths`/`paths-ignore` am Trigger: für PRs ohne Treffer startet der
#     Workflow gar nicht – dasselbe Einfrieren, nur seltener und darum schwerer
#     zu finden (GitHub-Doku „Handling skipped but required checks").
#   · `if:` am Job oder `continue-on-error` am Gate-Schritt: ein übersprungener
#     bzw. verschluckter Pflicht-Check gilt GitHub als BESTANDEN – Scheingrün.
# Der Vertrag friert den Anzeigenamen deshalb als Konstante ein (eine Quelle für
# Workflow, Doku und die Live-Wache pflichtcheck_guard.py) und verlangt die Form,
# in der ein Pflicht-Check zuverlässig berichtet. Umbenennen bleibt möglich –
# aber nur bewusst: Konstante, Workflow und Ruleset im selben Atemzug
# (Runbook: docs/PFLICHT-CHECK-RUNBOOK.md).
PFLICHT_CHECK_WORKFLOW = "integrity-lock.yml"
PFLICHT_CHECK_NAME = "Integritäts-Siegel"
PFLICHT_CHECK_BRANCH = "main"
PFLICHT_CHECK_WACHE = "pflichtcheck_guard.py"
RE_PFLICHT_CHECK_SCHRITT = re.compile(r"integrity_guard\.py\s+--gate\b")

# --------------------------------------------------------------------------- #
#  DAUERZUSTAND – der dokumentierte Fall „Vertrag verletzt, aber nicht heilbar"
# --------------------------------------------------------------------------- #
# Was hier steht, ist kein Freispruch, sondern ein Protokoll. Der Pflicht-Check
# `Integritäts-Siegel` ist auf diesem Repo ohne Admin-Eingriff nicht erfüllbar:
# Rulesets darf nach C15 nur ein Mensch ändern, und kein Bot-Token dieses Hauses
# hat `administration:write`. Die Wache meldete deshalb seit 19.09. 23:09 UTC in
# JEDEM PR rot – und dieses Rot war nachweislich folgenlos: PR #327 wurde am
# 20.09.2026 um 15:43 UTC gemergt, obwohl der Check mit `FAILURE` endete
# (kein Pflicht-Check ⇒ keine Merge-Blockade). Ein Befund, der jede Woche
# dasselbe „Problem" meldet, das niemand im Repo heilen kann, ist kein
# Messinstrument, sondern Lärm (die Lehre aus #206/#272) – und Lärm ist teurer
# als der Fehler, weil echte rote Kreuze in der Gewohnheit untergehen.
#
# Option B statt Option A: Der Befund wird NICHT grün gewaschen. Die Wache läuft
# weiter, prüft weiter und zeigt das rote Kreuz im Log und in der Step-Summary –
# nur eingeordnet als BEKANNT (dokumentierter, befristeter Dauerzustand) statt
# als Vorfall. Die Erklärung gilt exakt für den festgestellten Befund auf dem
# festgestellten Zweig und nur bis `pruefung_bis`; danach – und bei jeder
# Abweichung davon – meldet die Wache wieder hart (Exit 1, ::error::). `--strict`
# stellt den alten Zähler für Admin-Sitzungen und Nachprüfungen wieder her.
PFLICHT_CHECK_DAUERZUSTAND = {
    "zweck": "Pflicht-Check `Integritäts-Siegel` wird von `main` nicht verlangt und "
             "kann im Repo nicht eingetragen werden: Rulesets ändern ist Admin-Aufgabe (C15).",
    "check": PFLICHT_CHECK_NAME,
    "branch": PFLICHT_CHECK_BRANCH,
    "urteil_erwartet": "UNGESCHUETZT",
    "festgestellt": "2026-09-19",          # erster roter Vertragsschritt (19.09. 23:09:30 UTC)
    "dokumentiert": "2026-09-20",          # Entscheidung Frank: Zustand ablegen statt Alarm drehen
    "pruefung_bis": "2026-12-31",          # danach meldet die Wache wieder als Vorfall
    "belege": {
        "branch-schutz": "GET /repos/frank-hartung/franksfinanzcheck-blog/rules/branches/main "
                         "(20.09.2026) → 4 Einträge, je `deletion` + `non_fast_forward` aus den "
                         "Rulesets #23710849 und #23705980; kein `required_status_checks`, "
                         "keine `pull_request`-Regel",
        "keine-admin-rechte": "GET /repos/frank-hartung/franksfinanzcheck-blog → "
                              "permissions {admin:false, maintain:false, pull:false, push:false, "
                              "triage:false} – kein administration:write, PUT auf ein Ruleset "
                              "ist dem Bot verwehrt",
        "kein-merge-blocker": "PR #327 ist am 20.09.2026 15:43 UTC trotz Check-Konclusion "
                               "FAILURE gemergt (Merge-Commit 4b91938, Run 35520108131) – das "
                               "rote Kreuz hält nachweislich keinen Merge auf",
        "harter-stopp": "Schritte 4 und 5 desselben Laufs sind grün "
                        "(`integrity_guard.py --gate`: 43 Kerndateien == signierter Stand) – "
                        "der Sabotage-Schutz läuft und meldet Drift, er blockiert nur nicht",
    },
    "runbook": "docs/PFLICHT-CHECK-RUNBOOK.md",
    "runbook_abschnitt": "Dauerzustand – dokumentiert statt Dauer-Alarm (20.09.2026, Option B)",
}
# Schlüssel, die die Erklärung vollständig machen (C18 prüft gegen diese Liste).
DAUERZUSTAND_SCHLUESSEL = ("zweck", "check", "branch", "urteil_erwartet", "festgestellt",
                           "dokumentiert", "pruefung_bis", "belege", "runbook",
                           "runbook_abschnitt")
# Urteile, die als Dauerzustand dokumentierbar sind. `NICHT_PRUEFBAR` fehlt
# bewusst: „kann nicht prüfen" ist kein Zustand, den man absegnen könnte.
DAUERZUSTAND_URTEILE = ("UNGESCHUETZT", "FEHLT", "FALSCHE_QUELLE", "PR_SCOPING_FEHLT")


def _yaml_bloecke(text, kopf_re, einzug):
    """[(Kopf-Match, Blocktext)] aller Blöcke, deren Kopfzeile mit genau `einzug`
    Leerzeichen eingerückt ist und auf `kopf_re` passt. Der Block reicht bis zur
    nächsten Nicht-Kommentar-Zeile mit Einrückung <= `einzug`.

    Bewusst kein YAML-Parser (Haus-Regel des Vertrags: stdlib, deterministisch,
    keine Abhängigkeit, die im Gate fehlen könnte). Die Workflows sind
    bot-geschrieben und einheitlich eingerückt – die Selbsttests halten die Form
    fest, die hier erkannt wird.
    """
    zeilen = text.splitlines()
    out, i = [], 0
    while i < len(zeilen):
        m = re.match(r"^( *)([^\s#].*)$", zeilen[i])
        if m and len(m.group(1)) == einzug:
            km = kopf_re.match(m.group(2).rstrip())
            if km:
                j = i + 1
                while j < len(zeilen):
                    m2 = re.match(r"^( *)(\S.*)$", zeilen[j])
                    if m2 and len(m2.group(1)) <= einzug and not m2.group(2).startswith("#"):
                        break
                    j += 1
                out.append((km, "\n".join(zeilen[i + 1:j])))
                i = j
                continue
        i += 1
    return out


def pflichtcheck_profil(text):
    """Was GitHub aus dieser Workflow-Datei macht – die Teile, die für einen
    Pflicht-Check zählen: PR-Trigger (Zweige, Pfadfilter), Schreibrechte,
    Jobs mit Anzeigename, `if:` und Schritten."""
    profil = {"pr_trigger": False, "pr_branches": [], "pr_pfadfilter": False,
              "schreibrechte": [], "jobs": []}
    for _m, on_body in _yaml_bloecke(text, re.compile(r"^[\"']?on[\"']?:\s*$"), 0):
        for _pm, pr_body in _yaml_bloecke(on_body, re.compile(r"^pull_request(_target)?:\s*$"), 2):
            profil["pr_trigger"] = True
            for bm, br_body in _yaml_bloecke(pr_body, re.compile(r"^branches:\s*(.*)$"), 4):
                inline = bm.group(1).strip()
                if inline.startswith("["):
                    profil["pr_branches"] += [b.strip().strip("'\"") for b in
                                              inline.strip("[]").split(",") if b.strip()]
                profil["pr_branches"] += [lm.group(1).strip("'\"") for lm in
                                          re.finditer(r"^\s*-\s*(.+?)\s*$", br_body, re.M)]
            if re.search(r"^ {4}paths(-ignore)?:", pr_body, re.M):
                profil["pr_pfadfilter"] = True
        # `on:\n  pull_request:` ohne Unterblock (Kurzform) zählt ebenfalls als Trigger
        if re.search(r"^ {2}pull_request(_target)?:\s*(\{\}|~|null)?\s*$", on_body, re.M):
            profil["pr_trigger"] = True
    for _m, perm_body in _yaml_bloecke(text, re.compile(r"^permissions:\s*$"), 0):
        profil["schreibrechte"] = re.findall(r"^ {2}([\w-]+):\s*write\s*$", perm_body, re.M)
    for _m, jobs_body in _yaml_bloecke(text, re.compile(r"^jobs:\s*$"), 0):
        for jm, job_body in _yaml_bloecke(jobs_body, re.compile(r"^([A-Za-z_][\w-]*):\s*$"), 2):
            nm = re.search(r"^ {4}name:\s*(.+?)\s*$", job_body, re.M)
            profil["jobs"].append({
                "id": jm.group(1),
                "name": nm.group(1).strip().strip("'\"") if nm else None,
                "if": bool(re.search(r"^ {4}if:", job_body, re.M)),
                "steps": step_blocks(job_body),
            })
    return profil


def pflichtcheck_name_aus_workflow(text):
    """Der Check-Name, den GitHub für den Gate-Job meldet (Anzeigename, sonst
    Job-ID) – gelesen aus der Workflow-Datei, nicht aus einer Kopie. Leer, wenn
    kein Job den Gate-Schritt trägt."""
    for job in pflichtcheck_profil(text)["jobs"]:
        if any(RE_PFLICHT_CHECK_SCHRITT.search(body) for _n, body in job["steps"]):
            return job["name"] or job["id"]
    return ""


# --- C23: Zustandskanal (WF-1F8C #608, 07.10.2026) --------------------------
# Auslöser: Der 05.10.2026 endete mit 1/2 LIVE. Das Fach-Issue #601 existierte
# korrekt, wurde aber um 21:21 durch den Reparatur-Merge #603 geschlossen
# („Closes #601“) – der gemessene Tag blieb rot. Am 06.10. (Dienstag) übersprang
# `engine_issue.py` den Tag vollständig („Kein Publikationstag“); der um 00:55
# UTC nachgelieferte Montags-Slot der Kadenz-Endkontrolle meldete ehrlich rot
# („TAGESDEFIZIT – Fachmeldung engine-deficit ist zuständig“) – und das zentrale
# Fehler-Alerting fand keinen offenen, frischen Fachkanal. Es musste fail-open
# das generische Wartungs-Issue #608 mit API-Key-Runbook anlegen.
# Der Fehler war keine Alarmregel, sondern eine Besitzfrage: Eine QUOTE ist ein
# Zustand, kein Arbeitsauftrag. Ein Arbeitsauftrag endet mit einem Merge – ein
# Zustand nur durch eine neue MESSUNG. Diese Regel friert den Kanal ein:
#   * Besitzer = die Messung selbst (engine_issue.py), tägliche Kadenz
#   * gemessen wird der jüngste Publikationstag (SSOT cadence_guard) – auch
#     an Ruhetagen, denn ein Ruhetag vergisst keinen offenen Zustand
#   * Schließpfad = nur die eigene Messung (Ziel erreicht, mit ehrlichem
#     Vermerk, dass ein Fehltag NICHT nachgeholt wird)
#   * Reopen = wer den Kanal rot schließt, findet ihn beim nächsten Lauf offen
def c23_zustandskanal(script_texts, wflows, root=BLOG_DIR):
    out = []

    def _wf(name: str) -> str:
        for path, text in (wflows or {}).items():
            if os.path.basename(path) == name:
                return text
        return ""

    ei = script_texts.get("engine_issue.py", "")
    cg = script_texts.get("cadence_guard.py", "")
    pc = script_texts.get("publication_check.py", "")
    if not ei or not cg or not pc:
        out.append(("C23", "engine_issue.py / cadence_guard.py / "
                           "publication_check.py nicht lesbar – der Zustandskanal "
                           "ist nicht prüfbar."))
        return out

    # a) Der Selbsttest der Wache läuft im vertraglichen Minimum (C6).
    if "engine_issue.py" not in GUARDS:
        out.append(("C23", "scripts/engine_issue.py steht nicht in GUARDS – sein "
                           "Selbsttest liefe nicht in C6, und eine Wache, die niemand "
                           "verlangt, führt irgendwann niemand mehr aus."))

    # b) EIN Kalender: der jüngste Publikationstag kommt aus der SSOT.
    if "def letzter_publikationstag(" not in cg:
        out.append(("C23", "scripts/cadence_guard.py: `letzter_publikationstag` fehlt – "
                           "ohne die eine Kalenderquelle baut sich jeder Melder seinen "
                           "eigenen Tag (#608)."))
    if "cg.letzter_publikationstag(" not in ei:
        out.append(("C23", "scripts/engine_issue.py misst nicht über "
                           "`cadence_guard.letzter_publikationstag` – ein zweiter "
                           "Kalender im Melder ist die Ursache #608."))
    if "cg.letzter_publikationstag(" not in pc:
        out.append(("C23", "scripts/publication_check.py hat wieder eine eigene "
                           "Kalenderlogik – drei Melder, drei Tage (#608)."))

    # c) Kein Ruhetag-Sprung: Ein Zustand gilt auch am Dienstag.
    if "Kein Publikationstag – Defizit-Wache übersprungen" in ei:
        out.append(("C23", "scripts/engine_issue.py überspringt Ruhetage wieder "
                           "(„Kein Publikationstag“) – genau dann fehlte der Fachkanal "
                           "am 06.10.2026 (#608)."))
    if re.search(r"if\s+\w+\.weekday\(\)\s+not\s+in\s+cg\.PUBLICATION_DAYS", ei):
        out.append(("C23", "scripts/engine_issue.py kehrt an Ruhetagen vorzeitig "
                           "zurück – der Zustandskanal bliebe unbesetzt."))

    # d) Besitz: Der Kanal wird belegt und, falls rot geschlossen, wieder geöffnet.
    if 'gh("issue", "reopen"' not in ei:
        out.append(("C23", "scripts/engine_issue.py kennt kein Wiederöffnen – ein "
                           "Zustand, den ein Merge schließt, bliebe geschlossen (#608)."))
    if "wieder_oeffnen" not in ei:
        out.append(("C23", "scripts/engine_issue.py: die Entscheidung "
                           "`wieder_oeffnen` fehlt – ohne sie entsteht am nächsten roten "
                           "Lauf wieder ein generisches Wartungs-Issue."))
    if ei.count('gh("issue", "close"') != 1:
        out.append(("C23", "scripts/engine_issue.py schließt an mehr als einer Stelle "
                           "(oder gar nicht) – der Schließpfad muss die eigene Messung "
                           "sein, sonst schließt ihn am Ende ein Merge."))
    if "def schluss_kommentar(" not in ei or "nachgeholt" not in ei:
        out.append(("C23", "scripts/engine_issue.py: der Schließvermerk spricht die "
                           "Nicht-Nachholbarkeit nicht aus – dann behauptet der "
                           "Abschluss Fortschritt, den es nicht gibt."))

    # e) Identität bleibt Marker + Label: daran hängt die Stummschaltung des
    #    zentralen Fehler-Alertings (Meldung #602). Wer den Marker ändert, macht
    #    die Dedupe blind – und erzeugt wieder generische Doppelmeldungen.
    if 'MARKER = "<!-- engine-deficit-id: tagesdefizit -->"' not in ei:
        out.append(("C23", "scripts/engine_issue.py: der Marker "
                           "`<!-- engine-deficit-id: tagesdefizit -->` fehlt oder ist "
                           "verändert – die Fachkanal-Dedupe des Fehler-Alertings "
                           "greift nicht mehr."))
    if 'LABEL = "engine-deficit"' not in ei:
        out.append(("C23", "scripts/engine_issue.py: das Label `engine-deficit` fehlt "
                           "oder ist verändert – das Alerting findet den Fachkanal nicht."))

    # f) Kadenz: JEDEN Tag ein Beleg – an Ruhetagen von der Produktions-Wache.
    pw = _wf("produktions-wache.yml")
    if "engine_issue.py --deficit" not in pw:
        out.append(("C23", "produktions-wache.yml belegt den Quoten-Fachkanal nicht – "
                           "an Ruhetagen (Di/Do/Sa/So) bliebe er unbesetzt, und genau "
                           "dort entstand #608."))
    if not re.search(r'cron:\s*"0 20 \* \* \*"', pw):
        out.append(("C23", "produktions-wache.yml hat keinen täglichen Takt mehr – "
                           "der Zustandskanal braucht einen Beleg an jedem Kalendertag."))
    if "env.LEVEL != 'WARTEND'" not in pw:
        out.append(("C23", "produktions-wache.yml kennt die WARTEND-Frist nicht mehr – "
                           "in den Fallback-Slots (14:10/17:40) darf kein Defizit "
                           "gemeldet werden, die Slots laufen noch."))
    ke = _wf("kadenz-endkontrolle.yml")
    pos_beleg = ke.find("engine_issue.py --deficit")
    pos_messung = ke.find("publication_check.py")
    if pos_beleg < 0:
        out.append(("C23", "kadenz-endkontrolle.yml ruft die Defizit-Wache nicht mehr "
                           "auf – der rote TAGESDEFIZIT-Schritt hätte keinen Fachkanal."))
    elif 0 <= pos_messung < pos_beleg:
        out.append(("C23", "kadenz-endkontrolle.yml misst die Quote VOR dem Beleg des "
                           "Fachkanals – das Alerting liest nach dem Lauf und fände "
                           "einen veralteten Kanal (fail-open, #608)."))
    return out


def c18_pflicht_check(wflows):
    """C18: Der Pflicht-Check heißt, wie der Branch-Schutz ihn verlangt – und er
    berichtet in jeder Lage (kein Pfadfilter, kein `if:`, kein Verschlucken)."""
    out = []
    wf = PFLICHT_CHECK_WORKFLOW
    path = next((p for p in wflows if os.path.basename(p) == wf), None)
    if not path:
        out.append(("C18", f"`.github/workflows/{wf}` fehlt – der Pflicht-Check "
                           f"`{PFLICHT_CHECK_NAME}` würde nie berichten, jeder PR auf "
                           f"`{PFLICHT_CHECK_BRANCH}` bliebe auf „Expected“ stehen."))
        return out
    text = wflows[path]
    p = pflichtcheck_profil(text)
    if not p["pr_trigger"]:
        out.append(("C18", f"{wf}: kein `pull_request`-Trigger – ein Pflicht-Check, der "
                           f"bei Pull Requests nicht startet, friert den Merge ein."))
    elif p["pr_branches"] and PFLICHT_CHECK_BRANCH not in p["pr_branches"]:
        out.append(("C18", f"{wf}: `pull_request.branches` nennt `{PFLICHT_CHECK_BRANCH}` "
                           f"nicht ({', '.join(p['pr_branches'])}) – auf dem geschützten "
                           f"Zweig berichtet der Check nie."))
    if p["pr_pfadfilter"]:
        out.append(("C18", f"{wf}: `paths`/`paths-ignore` am PR-Trigger – ein Pflicht-Check "
                           f"darf nicht vom geänderten Pfad abhängen: für PRs ohne Treffer "
                           f"startet er nicht, und GitHub wartet ewig auf ihn („Expected“)."))
    if p["schreibrechte"]:
        out.append(("C18", f"{wf}: Schreibrechte ({', '.join(p['schreibrechte'])}: write) – "
                           f"das Gate ist read-only; ein Pflicht-Check mit Schreibrecht "
                           f"ist eine Angriffsfläche in jedem fremden PR."))
    traeger = [j for j in p["jobs"] if (j["name"] or j["id"]) == PFLICHT_CHECK_NAME]
    if not traeger:
        namen = ", ".join(f"`{j['name'] or j['id']}`" for j in p["jobs"]) or "keine Jobs"
        out.append(("C18", f"{wf}: kein Job meldet sich als `{PFLICHT_CHECK_NAME}` (gefunden: "
                           f"{namen}) – das Ruleset verlangt genau diesen Namen. Umbenennen "
                           f"heißt: PFLICHT_CHECK_NAME, Workflow und Ruleset im selben "
                           f"Atemzug (docs/PFLICHT-CHECK-RUNBOOK.md)."))
        return out
    for job in traeger:
        if job["if"]:
            out.append(("C18", f"{wf}: Job `{PFLICHT_CHECK_NAME}` trägt eine `if:`-Bedingung – "
                               f"ein übersprungener Pflicht-Check gilt GitHub als bestanden "
                               f"(Scheingrün)."))
        gate_steps = [(n, b) for n, b in job["steps"] if RE_PFLICHT_CHECK_SCHRITT.search(b)]
        if not gate_steps:
            out.append(("C18", f"{wf}: Job `{PFLICHT_CHECK_NAME}` ruft `integrity_guard.py "
                               f"--gate` nicht auf – ein Pflicht-Check ohne Prüfung ist ein "
                               f"grünes Häkchen ohne Inhalt."))
        for name, body in gate_steps:
            if re.search(r"continue-on-error:\s*true", body):
                out.append(("C18", f"{wf}: Schritt „{name}“ läuft mit `continue-on-error` – "
                                   f"ein rotes Gate würde grün gemeldet."))
        if not any(PFLICHT_CHECK_WACHE in b for _n, b in job["steps"]):
            out.append(("C18", f"{wf}: Job `{PFLICHT_CHECK_NAME}` ruft `{PFLICHT_CHECK_WACHE}` "
                               f"nicht auf – ob der Branch-Schutz diesen Check wirklich "
                               f"verlangt, prüft dann niemand (ein Ruleset ohne Ziel-Branch "
                               f"schützt nichts; Befund vom 19.09.2026)."))
    if PFLICHT_CHECK_WACHE not in GUARDS:
        out.append(("C18", f"scripts/{PFLICHT_CHECK_WACHE} steht nicht in GUARDS – ihr "
                           f"Selbsttest (C6) läuft in keiner Governance-Prüfung."))
    return out


def _iso_datum(wert):
    """Datum aus ISO-Zeichenkette oder None (bewusst kein Vergleich mit der Wanduhr)."""
    try:
        return datetime.date.fromisoformat(str(wert or "").strip())
    except ValueError:
        return None


def c18_dauerzustand(zustand, wache_text="", runbook_text=""):
    """C18-Zusatz: Eine dokumentierte Dauerzustand-Erklärung ist kohärent, verdrahtet
    und beweisbar – oder sie ist ein roter Befund.

    Eine Erklärung, die ihren Zweck verfehlt, ist schlimmer als keine: Sie verwandelt
    ein rotes Kreuz in ein grünes Gewissen. Also wird geprüft, was im Repo steht und
    was daraus folgt (alles deterministisch, ohne Netz, ohne Blick auf die Wanduhr):

      · vollständig   – alle Schlüssel sind gesetzt, die Belege sind welche (nicht
                        „war schon immer so")
      · eine Wahrheit – `check`/`branch`/`urteil_erwartet` stimmen mit den
                        Vertragskonstanten und den Urteilen der Wache überein
      · Datengrundlage – festgestellt ≤ dokumentiert ≤ Frist, alle drei als ISO-Datum
      · nicht tot     – die Wache liest die Erklärung (`PFLICHT_CHECK_DAUERZUSTAND`)
                        und kennt ihren harten Modus `--strict`
      · auffindbar    – das Runbook existiert und führt den benannten Abschnitt

    Die FRIST selbst ist hier ausdrücklich kein Befund: Der Vergleich mit der
    Wanduhr kippte sonst den Selbsttest unter der Uhr-Probe (C6, #310-Klasse) und
    ein Governance-Lauf würde drei Monate später anders entscheiden als heute.
    Abgelaufen wird im Live-Pfad gemeldet – dort, wo die echte Uhr steht.
    """
    out = []
    if not isinstance(zustand, dict) or not zustand:
        return out
    for feld in DAUERZUSTAND_SCHLUESSEL:
        wert = zustand.get(feld)
        if isinstance(wert, dict):
            if not wert:
                out.append(("C18", f"PFLICHT_CHECK_DAUERZUSTAND.{feld} ist leer – eine "
                                   f"Dauerzustand-Erklärung ohne Inhalt entschuldigt nichts."))
        elif not str(wert or "").strip():
            out.append(("C18", f"PFLICHT_CHECK_DAUERZUSTAND.{feld} fehlt – die Erklärung "
                               f"muss zweck, belege und Frist nennen."))
    if str(zustand.get("check") or "") != PFLICHT_CHECK_NAME:
        out.append(("C18", f"PFLICHT_CHECK_DAUERZUSTAND.check ist `{zustand.get('check')}`, "
                           f"Vertrag aber `{PFLICHT_CHECK_NAME}` – die Erklärung würde einen "
                           f"anderen Check freisprechen."))
    if str(zustand.get("branch") or "") != PFLICHT_CHECK_BRANCH:
        out.append(("C18", f"PFLICHT_CHECK_DAUERZUSTAND.branch ist `{zustand.get('branch')}`, "
                           f"geschützt werden soll `{PFLICHT_CHECK_BRANCH}`."))
    if str(zustand.get("urteil_erwartet") or "") not in DAUERZUSTAND_URTEILE:
        out.append(("C18", f"PFLICHT_CHECK_DAUERZUSTAND.urteil_erwartet "
                           f"`{zustand.get('urteil_erwartet')}` ist kein Urteil der Wache "
                           f"({', '.join(DAUERZUSTAND_URTEILE)}) – die Erklärung griffe ins Leere."))
    daten = {f: _iso_datum(zustand.get(f)) for f in ("festgestellt", "dokumentiert", "pruefung_bis")}
    for feld, wert in daten.items():
        if wert is None:
            out.append(("C18", f"PFLICHT_CHECK_DAUERZUSTAND.{feld} ist kein ISO-Datum "
                               f"(`{zustand.get(feld)}`) – Fristen müssen maschinenlesbar sein."))
    if all(daten.values()) and not (daten["festgestellt"] <= daten["dokumentiert"] <= daten["pruefung_bis"]):
        out.append(("C18", "PFLICHT_CHECK_DAUERZUSTAND: festgestellt ≤ dokumentiert ≤ "
                           "pruefung_bis ist verletzt – eine Erklärung, die vor ihrem eigenen "
                           "Befund datiert ist, ist keine."))
    belege = zustand.get("belege") if isinstance(zustand.get("belege"), dict) else {}
    for titel, text in belege.items():
        if len(str(text or "").strip()) < 20:
            out.append(("C18", f"PFLICHT_CHECK_DAUERZUSTAND.belege[„{titel}“] ist keine Evidenz "
                               f"(zu kurz) – ein Dauerzustand wird belegt, nicht behauptet."))
    if belege and not re.search(r"#\d+", " ".join(str(t) for t in belege.values())):
        out.append(("C18", "PFLICHT_CHECK_DAUERZUSTAND.belege nennen kein Issue und keine PR-Nummer "
                           "– woran soll man die Prüfung in sechs Monaten nachmessen können?"))
    if wache_text:
        if "PFLICHT_CHECK_DAUERZUSTAND" not in wache_text:
            out.append(("C18", f"scripts/{PFLICHT_CHECK_WACHE} liest `PFLICHT_CHECK_DAUERZUSTAND` "
                               f"nicht – die Erklärung ist totes Konfigurationsstück und der "
                               f"Befund bliebe ein Dauer-Vorfall."))
        if "--strict" not in wache_text:
            out.append(("C18", f"scripts/{PFLICHT_CHECK_WACHE} kennt keinen `--strict`-Modus – ohne "
                               f"harten Schalter für Admin-Sitzungen wäre das Weichzeichnen "
                               f"unwiderruflich (Scheingrün auf Dauer)."))
    runbook = str(zustand.get("runbook") or "")
    if runbook_text:
        if str(zustand.get("runbook_abschnitt") or "") not in runbook_text:
            out.append(("C18", f"{runbook}: Abschnitt „{zustand.get('runbook_abschnitt')}“ fehlt – "
                               f"die Wache verweist auf eine Anleitung, die es nicht gibt."))
    return out


def run_all(python_bin="python3", quick=False, root=BLOG_DIR):
    gov = _read(os.path.join(root, ".github", "workflows", "premium-governance.yml"))
    gate = _read(os.path.join(root, "scripts", "governance_gate.py"))
    # Quelltext der Secrets-Wache – Grundlage für C5 (registrierte NAMEN).
    wachen_quelltext = _read(os.path.join(root, "scripts", "secrets_age_guard.py"))
    wflows = {}
    for path in sorted(glob.glob(os.path.join(root, ".github", "workflows", "*.yml"))):
        wflows[path] = _read(path)
    manifest = {}
    mpath = os.path.join(root, "data", "cwv_manifest.json")
    try:
        with open(mpath, encoding="utf-8") as f:
            manifest = json.load(f)
    except (OSError, json.JSONDecodeError):
        manifest = {}
    report_texts = {}
    for name in ("CWV-REPORT.md", "EDITORIAL-SCORECARD.md", "SECRETS-REPORT.md"):
        report_texts[name] = _read(os.path.join(root, name))
    # Welche der gestagten Pfade sind ignoriert UND unversioniert? (die Kombination
    # ist das Problem – Versioniertes darf git add trotz Ignore-Muster.)
    candidates = sorted({t for text in wflows.values() for t in add_tokens(text)})
    ignored = set()
    if candidates:
        try:
            r = subprocess.run(["git", "check-ignore", "--stdin"], cwd=root,
                               input="\n".join(candidates), capture_output=True,
                               text=True, timeout=60)
            ignored = {l.strip() for l in r.stdout.splitlines() if l.strip()}
            if ignored:
                t = subprocess.run(["git", "ls-files", "--", *sorted(ignored)], cwd=root,
                                   capture_output=True, text=True, timeout=60)
                tracked = {l.strip() for l in t.stdout.splitlines() if l.strip()}
                ignored -= tracked
        except (OSError, subprocess.TimeoutExpired):
            ignored = set()
    checks = []
    checks += c1_ordering(gov)
    checks += c2_build_not_swallowed(gov)
    checks += c3_measure_chain_complete(gov, gate)
    checks += c4_issue_policy(gov)
    checks += c5_record_provenance(wflows, wachen_quelltext)
    checks += c6_selftests(python_bin=python_bin, quick=quick)
    checks += c7_data_consistency(report_texts, manifest)
    checks += c8_commit_hygiene(gov, ignored)
    leak_texts = dict(report_texts)
    for path in glob.glob(os.path.join(root, "data", "*.json")):
        if os.path.getsize(path) < 400_000:
            leak_texts[os.path.relpath(path, root)] = _read(path)
    checks += c9_leak_wache(leak_texts)
    script_texts = {}
    for path in sorted(glob.glob(os.path.join(root, "scripts", "*.py"))):
        script_texts[os.path.basename(path)] = _read(path)
    checks += c10_token_broker(script_texts)
    checks += c11_token_lifecycle(wflows, root=root)
    checks += c12_label_guarantee(wflows)
    checks += c13_proof_integrity(wflows, auth_text=script_texts.get("pinterest_auth.py", ""))
    checks += c14_alarm_routing(wflows, script_texts, root=root)
    checks += c15_proof_not_healing(script_texts, wflows)
    deploy_yml = _read(os.path.join(root, ".github", "workflows", "deploy.yml"))
    checks += c16_heartbeat(deploy_yml, script_texts)
    checks += c17_pinterest_duplicate_guard(script_texts, wflows, root=root)
    checks += c18_pflicht_check(wflows)
    dauerz = PFLICHT_CHECK_DAUERZUSTAND or {}
    runbook_pfad = str(dauerz.get("runbook") or "")
    checks += c18_dauerzustand(dauerz, script_texts.get(PFLICHT_CHECK_WACHE, ""),
                               _read(os.path.join(root, runbook_pfad)) if runbook_pfad else "")
    checks += c19_release_ssot(script_texts, root=root)
    checks += c20_lesbarkeit_und_hysterese(script_texts, gate)
    checks += c21_maschinensaetze(script_texts)
    checks += c22_publikations_vertrag(script_texts, root=root)
    checks += c23_zustandskanal(script_texts, wflows, root=root)
    checks += c25_deckung_wirkung(script_texts, root=root,
                                  python_bin=python_bin)
    checks += c26_beleg_je_tag(script_texts, wflows, root=root)
    checks += c27_ledger_isolation(script_texts, wflows, root=root)
    checks += c28_klassen_routing(script_texts, wflows, root=root)
    checks += c29_geburts_tor(script_texts, wflows, root=root,
                              python_bin=python_bin)
    checks += c30_eine_h1(script_texts, wflows, root=root,
                          python_bin=python_bin)
    checks += c32_doppelte_schluessel(
        script_texts, wflows, root=root, python_bin=python_bin)
    checks += c33_artefakt_waechter(script_texts, wflows, root=root,
                                    python_bin=python_bin)
    return checks


# --- C33: Maschinen-Artefakte werden gegengelesen (WF-D4E0 #653) ------------
# ---------------------------------------------------------------------------
# Haus-Nummern: C24 ist die C24 Bank, C31 der Robustheits-Vertrag
# (robustheits_gate.py) – C33 ist darum die nächste freie Nummer.
# ---------------------------------------------------------------------------
# Auslöser: Sechs Nächte hintereinander meldete der harte End-Gate der
# Content-Reserve „🛑 RESERVE-ENGPAß: nur 0/6 Kandidaten gate-fertig“, und
# in keiner dieser Nächte war der Vorrat leer. `data/reserve-readiness.json`
# lag nach einem Merge als strukturell kaputtes JSON in main (zwei Stände
# desselben Artefakts verschmolzen) und `data/reserve-quarantine.json`
# gleich mit. Niemand las die Artefakte gegen – der End-Gate las daraus eine
# „0“, und eine fehlgeschlagene Messung sah aus wie ein leerer Lagerbestand.
# Die Folge war teurer als der Defekt: sechs Nächte Reparatur in die falsche
# Richtung (KI-Keys, Themenmangel, Produktion), während die Ursache ein
# halbes Artefakt war.
#
# Was der Vertrag verlangt:
#   a) Eine Wache, die den Artefakt-Korpus prüft (Klassen A1–A6),
#   b) fail-closed: sie rekonstruiert kein unlesbares Artefakt,
#   c) Verdrahtung am PR-Pfad (ein kaputtes Artefakt darf nicht nach main)
#      UND am Reserve-Lauf, letzteres NACH den heilenden Stufen,
#   d) Ursachenklassen am End-Gate: „nicht gemessen“ ≠ „zu wenig Vorrat“,
#   e) Siegel und Regressionstest – ein Vertrag ohne Test ist Prosa.
C33_KLASSEN = ("A1", "A2", "A3", "A4", "A5", "A6")
C33_PFLICHT_WF = ("integrity-lock.yml", "content-reserve.yml")


def c33_artefakt_waechter(script_texts, wflows, root=BLOG_DIR,
                          python_bin=None):
    out = []
    wache = script_texts.get("artefakt_waechter.py", "")
    gate = script_texts.get("reserve_gate.py", "")
    readiness = script_texts.get("reserve_readiness.py", "")
    kerndateien = _read(os.path.join(root, "scripts", "integrity_guard.py"))
    test = os.path.join(root, "scripts", "tests", "test_artefakt_waechter.py")

    dateien: dict[str, str] = {}
    for pfad, text in (wflows or {}).items():
        dateien[os.path.basename(str(pfad))] = text

    if not wache:
        out.append(("C33", "scripts/artefakt_waechter.py fehlt – ohne die "
                           "Wache ist „unsere Maschinen-Artefakte sind "
                           "heil“ eine Behauptung, kein Zustand (#653, "
                           "fail-closed)."))
        return out

    # a) Erkennung aller sechs Klassen. Eine Wache, die nur JSON prüft,
    #    übersieht genau die Hälfte: A6 (Frontmatter) ist die Klasse, an
    #    der Hugo beim Bauen stirbt, und A4 (Konfliktmarker) die, die ein
    #    Merge hinterlässt.
    for klasse in C33_KLASSEN:
        if klasse not in wache:
            out.append(("C33", f"scripts/artefakt_waechter.py: Klasse {klasse} "
                               "fehlt – eine Wache, die eine Klasse nicht "
                               "kennt, meldet für sie Grün (#653)."))

    # b) Selbsttest und Wirkungsprobe: eine Wache, deren Behauptungen
    #    niemand nachstellt, ist Dekoration (C25-Logik, sinngemäß).
    for flagge, feld, sinn in (("--selftest", "args.selftest",
                                "der Beweis der Erkennung"),
                               ("--wirkungsprobe", "args.wirkungsprobe",
                                "der Beweis der Heilung"),
                               ("--heal", "args.heal",
                                "die Selbstheilung")):
        if flagge not in wache:
            out.append(("C33", f"scripts/artefakt_waechter.py: {flagge} fehlt "
                               f"– ohne {sinn} bleibt die Wache eine Zusage."))
        elif feld not in wache:
            out.append(("C33", f"scripts/artefakt_waechter.py: {flagge} ist "
                               "nicht ausgewertet – eine Flagge, die niemand "
                               "liest, ist Papier (#653)."))

    # c) FAIL-CLOSED: Ein nicht mehr lesbares Artefakt zu rekonstruieren
    #    hieße, Inhalt zu erfinden. Die Wache darf nur A2 heilen (doppelte
    #    Schlüssel: der letzte Eintrag gewinnt, mit Gegenprobe).
    if "heile(" in wache and "A1" not in wache.split("def heile(")[-1][:900]:
        if "nicht mehr lesbar" not in wache and "rekonstru" not in wache.lower():
            out.append(("C33", "scripts/artefakt_waechter.py: die Heilung "
                               "begründet nicht, warum sie unlesbare "
                               "Artefakte auslässt – rekonstruierter Inhalt "
                               "wäre erfunden (#653, fail-closed)."))

    # d) C6: Ohne Selbsttest im vertraglichen Minimum führt die Wache
    #    irgendwann niemand aus (Befund C).
    if "artefakt_waechter.py" not in GUARDS:
        out.append(("C33", "scripts/artefakt_waechter.py steht nicht in "
                           "governance_contract.GUARDS – ohne den Zwang zum "
                           "Selbsttest im Minimum verstummt die Wache "
                           "(C6, #653)."))

    # e) Verdrahtung: der PR-Pfad UND der Reserve-Lauf.
    for name in C33_PFLICHT_WF:
        text = dateien.get(name, "")
        if not text:
            out.append(("C33", f".github/workflows/{name} fehlt – das "
                               "Artefakt-Siegel hat keinen Ort, an dem es "
                               "verlangt wird (#653)."))
        elif "scripts/artefakt_waechter.py" not in text:
            out.append(("C33", f".github/workflows/{name} ruft den "
                               "Artefakt-Wächter nicht – ein strukturell "
                               "kaputtes Maschinen-Artefakt bliebe "
                               "unbemerkt (#653)."))

    # f) REIHENFOLGE im Reserve-Lauf: ERST heilen (Stufe 3 schreibt das
    #    Zertifikat neu), DANN urteilen. Ein am Lauf-Anfang platzierter
    #    Wächter würde die Stufe abschalten, die seinen eigenen Fund heilt
    #    – genau das war der Fehler der übersprungenen Stufen 1–3.
    reserve = dateien.get("content-reserve.yml", "")
    if reserve and "scripts/artefakt_waechter.py" in reserve:
        i_wache = reserve.rindex("scripts/artefakt_waechter.py")
        i_stufe3 = reserve.find("scripts/reserve_readiness.py")
        if i_stufe3 < 0 or i_wache < i_stufe3:
            out.append(("C33", "content-reserve.yml: der Artefakt-Wächter "
                               "steht VOR der Zertifizierung – er würde die "
                               "Stufe überspringen, die seinen Fund heilt "
                               "(#653). Reihenfolge: heilen, dann urteilen."))
        if "artefakt_waechter.py --selftest" not in reserve:
            out.append(("C33", "content-reserve.yml: der Selbsttest des "
                               "Artefakt-Wächters läuft nicht mit – eine "
                               "Wache, die ihren eigenen Beweis nicht führt, "
                               "kann still erblinden (#653)."))
        if "if: ${{ !cancelled() }}" not in reserve:
            out.append(("C33", "content-reserve.yml: dem Artefakt-Schritt "
                               "fehlt `!cancelled()` – als harter Fehler "
                               "würde er den Lauf abbrechen, statt den "
                               "Befund zu sichern (#653)."))

    # g) Stufe 3 (Zertifizierung) muss IMMER laufen. Sie schreibt das
    #    Artefakt, aus dem der End-Gate urteilt – wird sie übersprungen,
    #    liest er den Stand der VORNACHT und gibt ihn als diese Nacht aus.
    if reserve:
        # Der Stufen-Block wird am Schritt-NAMEN gesucht, nicht am bloßen
        # Vorkommen von „Stufe 3“: Der Name steht im Kommentar einer ANDEREN
        # Stufe und hätte die Prüfung sonst auf den falschen Block gelenkt
        # (die Regel fände eine Bedingung, die sie gar nicht meint).
        treffer = re.search(
            r"^      - name:[^\n]*Stufe 3[^\n]*\n(.*?)(?=^      - name:|\Z)",
            reserve, re.S | re.M)
        if not treffer:
            out.append(("C33", "content-reserve.yml: Stufe 3 "
                               "(Zertifizierung) fehlt – ohne sie gibt es "
                               "keine Messung, nur ein altes Artefakt "
                               "(#653)."))
        else:
            block = treffer.group(1)
            if "steps.wachen.conclusion" in block:
                out.append(("C33", "content-reserve.yml: Stufe 3 hängt am "
                                   "Wachen-Selbsttest – die Messung wird "
                                   "dann übersprungen und der End-Gate liest "
                                   "den Stand der VORNACHT als diese Nacht "
                                   "(#653)."))
            elif "!cancelled()" not in block:
                out.append(("C33", "content-reserve.yml: Stufe 3 hat keine "
                                   "eigene Lauf-Bedingung – eine übersprungene "
                                   "Messung darf nie als Vorrats-Urteil "
                                   "aussehen (#653)."))

    # h) Ursachenklassen am End-Gate: „nicht gemessen“ darf nicht als
    #    „zu wenig Vorrat“ gemeldet werden. Genau diese Verwechslung hat
    #    #653 sechs Nächte lang die Reparatur in die falsche Richtung
    #    geschickt.
    if not gate:
        out.append(("C33", "scripts/reserve_gate.py fehlt – ohne ihn gibt es "
                           "keinen Ort, an dem eine Messung von einem "
                           "Vorrats-Urteil zu unterscheiden wäre (#653)."))
    else:
        for marke, sinn in (("def zertifikat_lage(", "die Klasse des Zertifikats"),
                            ("KLASSE_ARTEFAKT", "die Klasse „nicht gemessen“"),
                            ("KLASSE_KETTE", "die Klasse „Kette übersprungen“"),
                            ("def ketten_lage(", "die Lage der Kette")):
            if marke not in gate:
                out.append(("C33", f"scripts/reserve_gate.py: {marke} fehlt – "
                                   f"ohne {sinn} sieht eine fehlgeschlagene "
                                   "Messung wieder wie ein leerer Vorrat aus "
                                   "(#653)."))
        if "RESERVE_STUFE3_STATUS" not in gate:
            out.append(("C33", "scripts/reserve_gate.py liest die Ketten-Lage "
                               "nicht aus der Umgebung – ohne sie kann der "
                               "Lauf nicht wissen, dass seine Messung "
                               "übersprungen wurde (#653)."))

    # i) Der Schreiber prüft, was er geschrieben hat: atomar und mit
    #    Gegenprobe. Ein Zertifikat ist danach entweder alt oder neu, nie
    #    halb – und ein halbes hätte niemand bemerkt (#653).
    if not readiness:
        out.append(("C33", "scripts/reserve_readiness.py fehlt – ohne den "
                           "Schreiber gibt es kein Zertifikat (#653)."))
    else:
        for marke, sinn in (("def schreibe_zertifikat(",
                             "das atomische Schreiben"),
                            ("os.replace(", "der unteilbare Tausch"),
                            ("object_pairs_hook",
                             "die Gegenprobe auf doppelte Schlüssel")):
            if marke not in readiness:
                out.append(("C33", f"scripts/reserve_readiness.py: {marke} "
                                   f"fehlt – ohne {sinn} kann ein halbes "
                                   "Artefakt im Repo stehen (#653)."))

    # j) Siegel und Regressionstest: eine Wache, die man löschen darf,
    #    ohne dass irgendwo etwas rot wird, ist eine Empfehlung.
    if "artefakt_waechter.py" not in kerndateien:
        out.append(("C33", "scripts/artefakt_waechter.py steht nicht unter "
                           "dem Integritäts-Siegel – als ungesiegelte Datei "
                           "könnte die Wache still verändert werden (#653)."))
    if not os.path.exists(test):
        out.append(("C33", "scripts/tests/test_artefakt_waechter.py fehlt – "
                           "ohne Regressionstest ist dieser Vertrag Prosa "
                           "(#653)."))
    return out


# --- C25: Deckung heißt Wirkung (WACHE-609, 07.10.2026)
# Der Code ist bewusst NICHT C24: „C24“ bezeichnet im Haus die
# C24 Bank (Affiliate-Anker/Tooltips). Eine Governance-Regel „C24“
# wäre in Logs und Greps nicht mehr von der Marke zu unterscheiden.
# ---------------------------------------------------------------------------
# Auslöser: `readability_failures` galt als gedeckt, weil `profi_polish.py`
# in der Heiler-Kette der Reserve stand – und der Vorrat stand trotzdem bei
# 2/6, sieben Kandidaten allein an der Lesbarkeit geparkt (Flesch 53,1–59,9);
# der Publikationstag endete 1/2 (Produktions-Wache, P2, Issue #609).
# Ein Name in der Kette ist eine Behauptung – die Wache beweist sie:
#   * Regeln mit Zahlen-Versprechen (PROBEN_PFLICHT) brauchen mindestens
#     einen Heiler mit Wirkungsprobe,
#   * der Heiler muss in `reserve_finisher.HEALER_CHAIN` wirklich laufen,
#   * die Schwelle muss importiert sein (keine zweite Zahl, Lehre #585),
#   * und die Probe muss JETZT grün laufen (Exit 0) – auf diesem Baum.
def c25_deckung_wirkung(script_texts, root=BLOG_DIR, python_bin=None):
    out = []
    rhc = script_texts.get("reserve_healer_coverage.py", "")
    rf = script_texts.get("reserve_finisher.py", "")
    heiler = script_texts.get("lesbarkeit_heiler.py", "")
    if not rhc or not rf or not heiler:
        out.append(("C25", "reserve_healer_coverage.py / reserve_finisher.py / "
                           "lesbarkeit_heiler.py nicht lesbar – die Wirkungs-"
                           "Deckung ist nicht prüfbar."))
        return out
    if "WIRKUNGS_PROBEN" not in rhc or "def wirkungsdeckung(" not in rhc:
        out.append(("C25", "scripts/reserve_healer_coverage.py: Wirkungsproben "
                           "fehlen – eine Deckung ohne Wirkung ist Papier (#609)."))
    if "PROBEN_PFLICHT" not in rhc or "readability_failures" not in rhc:
        out.append(("C25", "scripts/reserve_healer_coverage.py: die Pflicht-Regeln "
                           "mit Zahlen-Versprechen fehlen (readability_failures)."))
    if "lesbarkeit_heiler.py" not in rhc:
        out.append(("C25", "scripts/reserve_healer_coverage.py nennt den "
                           "Lesbarkeits-Heiler nicht – das Tor gälte wieder als "
                           "gedeckt, ohne dass es jemand bewegt (#609)."))
    if '("lesbarkeit_heiler.py"' not in rf:
        out.append(("C25", "reserve_finisher.HEALER_CHAIN fährt den Lesbarkeits-"
                           "Heiler nicht – die Reserve bliebe bei Flesch < 60 "
                           "strukturell unerreichbar (#609)."))
    if "NEW_FLESCH_MIN" not in heiler:
        out.append(("C25", "scripts/lesbarkeit_heiler.py importiert die Schwelle "
                           "`readability_check.NEW_FLESCH_MIN` nicht – zweite "
                           "Wahrheit (#585)."))
    if re.search(r"NEW_FLESCH_MIN\s*=\s*[0-9]", heiler):
        out.append(("C25", "scripts/lesbarkeit_heiler.py definiert die Flesch-"
                           "Schwelle selbst – die importierte SSOT ist die eine "
                           "Wahrheit (#585)."))
    if "--wirkungsprobe" not in heiler or "def wirkungsprobe(" not in heiler:
        out.append(("C25", "scripts/lesbarkeit_heiler.py: `--wirkungsprobe` fehlt "
                           "– ein Heiler ohne Probe kann seine Wirkung nicht belegen."))
    # Der scharfe Teil: die Probe muss JETZT grün sein (Exit 0).
    bin_ = python_bin or sys.executable or "python3"
    try:
        lauf = subprocess.run(
            [bin_, os.path.join(root, "scripts", "lesbarkeit_heiler.py"),
             "--wirkungsprobe"],
            cwd=root, capture_output=True, text=True, timeout=180)
    except (OSError, subprocess.TimeoutExpired) as exc:
        out.append(("C25", f"Wirkungsprobe nicht ausführbar "
                           f"({exc.__class__.__name__}) – fail-closed."))
        return out
    if lauf.returncode != 0:
        zeilen = ((lauf.stdout or "") + (lauf.stderr or "")).strip().splitlines()
        out.append(("C25", "Wirkungsprobe ROT: "
                           + (zeilen[-1][:160] if zeilen
                              else f"Exit {lauf.returncode}")))
    return out


# --- C26: Ein Beleg gehört seinem Tag (WF-54C4 #610, 07.10.2026) -----------
# Auslöser: `publication_check.py` schrieb seinen Beleg bei JEDEM Lauf in
# dieselbe Datei `tmp/publication-receipt.json`, und `publication_incident.py`
# schloss das offene Issue bei JEDEM grünen Lauf. Die SLO misst aber immer den
# JÜNGSTEN Publikationstag: Das Ticket über den 05.10.2026 (Source und öffentlich
# je 1/2) wäre am 07.10. mit dem Beleg des 07.10. geschlossen worden – der
# Fehltag wäre nie verbucht worden, und der Beweis wäre mit der Datei
# überschrieben. Dazu die zweite Hälfte derselben Nacht: Ein Reserve-Artikel,
# vom späten Gate auf `draft: true` zurückgestuft, trug noch
# `reserve_published` – die Signatur, mit der Sichtung und Janitor ihn als
# „Rückläufer“ lasen (der Inhalt lebe live) und sofort löschten. Er war nie
# öffentlich: Der Tag verlor Auslieferung UND Material. Diese Regel hält
# fest, dass ein Beleg seinem Tag gehört und ein Löschgrund einen Beweis
# braucht.
def c26_beleg_je_tag(script_texts, wflows, root=BLOG_DIR):
    out = []

    def _wf(name: str) -> str:
        for path, text in (wflows or {}).items():
            if os.path.basename(path) == name:
                return text
        return ""

    pi = script_texts.get("publication_incident.py", "")
    pc = script_texts.get("publication_check.py", "")
    pr_ = script_texts.get("publication_release.py", "")
    rp = script_texts.get("reserve_pool.py", "")
    rc = script_texts.get("reserve_custody.py", "")
    rj = script_texts.get("reserve_janitor.py", "")
    fehlend = [name for name, text in (
        ("publication_incident.py", pi), ("publication_check.py", pc),
        ("publication_release.py", pr_), ("reserve_pool.py", rp),
        ("reserve_custody.py", rc), ("reserve_janitor.py", rj)) if not text]
    if fehlend:
        out.append(("C26", f"{', '.join(fehlend)} nicht lesbar – der "
                           "Tages-Beleg ist nicht prüfbar."))
        return out

    # a) Der Melder ist selbst eine Wache: sein Schließpfad läuft im Selbsttest.
    if "publication_incident.py" not in GUARDS:
        out.append(("C26", "scripts/publication_incident.py steht nicht in "
                           "GUARDS – sein Schließpfad liefe in keinem "
                           "Selbsttest mit."))

    # b) Schließen ausschließlich über die Tages-Entscheidung (fail-closed).
    m = re.search(r"if\s+urteil\s+in\s*\(([^)]*)\)\s*:", pi)
    if not m or "'schliessen'" not in m.group(1) or "'quittung'" not in m.group(1):
        out.append(("C26", "publication_incident.py schließt nicht "
                           "ausschließlich über die Tages-Entscheidung "
                           "(schliessen|quittung) – ein grüner Fremdtag würde "
                           "den Fehltag still schließen (#610)."))
    if "receipt_ok" not in pi:
        out.append(("C26", "publication_incident.py prüft `receipt_ok` nicht – "
                           "ein roter Beleg könnte abschließen."))
    if "Quittung" not in pi or "verbucht, nicht behoben" not in pi:
        out.append(("C26", "publication_incident.py verbucht einen vergangenen "
                           "Fehltag nicht ausdrücklich als Quittung – der "
                           "Abschluss wäre eine Beschönigung statt einer "
                           "Buchung (#610)."))
    if "Gemessener Tag" not in pi or "tag_aus_body" not in pi:
        out.append(("C26", "publication_incident.py führt den gemessenen Tag "
                           "nicht im Issue-Body – die Akte verliert ihren Tag "
                           "(#610)."))

    # c) publication_check: tagesgenauer Beleg UND versionierte Historie.
    if "publication-receipt-" not in pc or "def beleg_schreiben(" not in pc:
        out.append(("C26", "publication_check.py schreibt keinen tagesgenauen "
                           "Beleg (`publication-receipt-<tag>`) – der Beweis "
                           "wird bei jedem Lauf überschrieben (#610)."))
    if "publication-delivery-history" not in pc:
        out.append(("C26", "publication_check.py führt keine versionierte "
                           "Auslieferungs-Historie – ein Fehltag wäre nach "
                           "dem nächsten Lauf nicht mehr nachweisbar (#610)."))
    if "beleg_schreiben(" not in pc.replace("def beleg_schreiben(", ""):
        out.append(("C26", "publication_check.py benutzt `beleg_schreiben` "
                           "nicht – der Tagesbeleg wäre toter Code."))

    # d) Konvergenz der Nachfüllung: nicht aufhören, solange Material da ist.
    if "def refill_until_min(" not in pr_ or pr_.count("refill_until_min(") < 3:
        out.append(("C26", "publication_release.py füllt nicht konvergent nach "
                           "(`refill_until_min` an den Aufrufstellen) – ein "
                           "später Gate-Verwurf beendete den Tag wieder bei "
                           "1/2 (#610)."))
    if ("def sichere_verworfene_nachschuebe(" not in pr_ or
            "sichere_verworfene_nachschuebe(" not in
            pr_.replace("def sichere_verworfene_nachschuebe(", "")):
        out.append(("C26", "publication_release.py holt verworfenen Nachschub "
                           "nicht zurück (`sichere_verworfene_nachschuebe`) – "
                           "Material ginge mit der Zurückstufung verloren "
                           "(#610)."))

    # e) Nachweis-Pflicht beim Rückläufer (Löschen braucht einen Beweis).
    if "def live_zwilling(" not in rp or "def zurueck_in_den_pool(" not in rp:
        out.append(("C26", "reserve_pool.py hat keinen LIVE-Nachweis und "
                           "keinen Rückweg (`live_zwilling` / "
                           "`zurueck_in_den_pool`) – „Rückläufer“ bliebe eine "
                           "Behauptung (#610)."))
    if "ruecklaeufer_ohne_nachweis" not in rc:
        out.append(("C26", "reserve_custody.py meldet `reserve_published` + "
                           "draft ohne LIVE-Nachweis nicht als eigenen Zustand "
                           "– der Janitor würde nicht ausgelieferten Nachschub "
                           "als Rückläufer vernichten (#610)."))
    if "zurueck_in_den_pool(" not in rj:
        out.append(("C26", "reserve_janitor.py holt nachweis-losen Nachschub "
                           "nicht zurück (`zurueck_in_den_pool`) – Löschen "
                           "ohne Beweis (#610)."))

    # f) Der Auslieferungs-Workflow bewahrt den Tagesbeleg und meldet auf
    #    beiden Pfaden (rot = öffnen/aktualisieren, grün = abschließen).
    pd = _wf("publication-delivery.yml")
    if not pd:
        out.append(("C26", "publication-delivery.yml nicht lesbar – die "
                           "Auslieferungs-Beweiskette ist nicht prüfbar."))
    else:
        if "publication-receipt*.json" not in pd:
            out.append(("C26", "publication-delivery.yml lädt den tagesgenauen "
                               "Beleg nicht als Artefakt hoch – die "
                               "Beweiskette endet mit dem Lauf (#610)."))
        if pd.count("publication_incident.py") < 2:
            out.append(("C26", "publication-delivery.yml ruft den Melder nicht "
                               "auf beiden Pfaden (öffnen und abschließen) – "
                               "der Kanal wäre halb verdrahtet."))
    return out


RE_C27_LOGEVENT = re.compile(r"def\s+log_event\s*\(.*?(?=\ndef\s)", re.S)


def c27_ledger_isolation(script_texts, wflows, root=BLOG_DIR):
    """C27: Beweisen ist nicht Fabrizieren.

    Ausloeser (07.10.2026, Nebenbefund zu #610 – Selbstfund beim Siegeln der
    Auslieferungs-Heilung): Drei Unit-Tests schrieben echte Zeilen in
    `data/audit/*.jsonl`, ein versioniertes, von history_guard H6 als
    append-only bewachtes Beweis-Ledger. Die teuerste Zeile war ein
    gate-Entscheid fuer den Fixture-Artikel `2026-09-07-r5-live`, committet am
    03.10.2026: Das Buch behauptete einen am Gate verworfenen Live-Artikel,
    den es nie gab. Vier weitere Zeilen bescheinigten GROQ_API_KEY einen
    Erfolg `via content-engine-v2`, obwohl in CI ausschliesslich
    pinterest-ai.yml und pinterest-token.yml `--record-success` aufrufen – und
    zwar nur fuer PINTEREST_TOKEN_KEY.

    Die Regel ist die Schwester von C15: Dort darf ein Beweislauf nicht heilen,
    was er prueft; hier darf er nicht behaupten, was nie geschah. Geprueft wird
    der Engpass (audit_log), die Sandbox (repo_isolation), die Beobachtung
    (Regressionstest) und die empirische Leitplanke im Qualitaets-Gate.
    """
    out = []

    def _wf(name: str) -> str:
        for path, text in (wflows or {}).items():
            if os.path.basename(path) == name:
                return text
        return ""

    al = script_texts.get("audit_log.py", "")
    ri = script_texts.get("repo_isolation.py", "")
    if not al:
        out.append(("C27", "scripts/audit_log.py nicht lesbar – der Engpass des "
                           "Beweis-Ledgers ist nicht prüfbar."))
        return out

    # a) Der Engpass trägt den Vertrag – in der UMGEBUNG, nicht im Prozess.
    #    Leckstelle 1 entsteht in einem Kindprozess (publish_gate ruft
    #    affiliate_profi_check.py); ein Monkeypatch erreicht das Kind nicht.
    if "FFC_AUDIT_DIR" not in al:
        out.append(("C27", "audit_log.py kennt FFC_AUDIT_DIR nicht: Die Umlenkung "
                           "erreicht Kindprozesse nicht (publish_gate → "
                           "affiliate_profi_check.py) – ein Testlauf schreibt "
                           "weiter echte Zeilen ins Beweis-Ledger."))
    if "FFC_AUDIT_DISABLE" not in al:
        out.append(("C27", "audit_log.py kennt FFC_AUDIT_DISABLE nicht – es gibt "
                           "keinen harten No-Op für Läufe, die überhaupt nichts "
                           "protokollieren dürfen."))
    for funktion in ("audit_verzeichnis", "audit_abgeschaltet"):
        if not re.search(rf"def\s+{funktion}\s*\(", al):
            out.append(("C27", f"audit_log.py stellt `{funktion}()` nicht bereit – "
                               "Schreib- und Lesepfad könnten auseinanderlaufen "
                               "(ein umgelenkter Lauf läse das echte Buch)."))
    m = RE_C27_LOGEVENT.search(al)
    koerper = m.group(0) if m else ""
    if not koerper:
        out.append(("C27", "audit_log.py: `log_event()` nicht auffindbar – der "
                           "einzige Schreibpfad ins Ledger ist nicht prüfbar."))
    else:
        if "audit_abgeschaltet()" not in koerper:
            out.append(("C27", "log_event() prüft die Stummschaltung nicht – "
                               "FFC_AUDIT_DISABLE wäre wirkungslos."))
        if "audit_verzeichnis()" not in koerper:
            out.append(("C27", "log_event() schreibt nicht über audit_verzeichnis() "
                               "– FFC_AUDIT_DIR wäre wirkungslos."))
    # Gegenrichtung (Schein-Sicherheit): Ohne Schalter MUSS das Ledger scharf
    # bleiben. Ein Engpass, der im Betrieb stumm ist, vernichtet Beweise statt
    # sie zu fabrizieren – und wäre der teurere der beiden Fehler.
    if "return ziel or AUDIT_DIR" not in al.replace("  ", " "):
        out.append(("C27", "audit_verzeichnis() fällt nicht auf data/audit zurück – "
                           "im Betrieb würde das Beweis-Ledger still abgeschaltet."))

    # b) Die Sandbox für Testläufe.
    if not ri:
        out.append(("C27", "scripts/repo_isolation.py fehlt – ohne Sandbox müssen "
                           "Tests das Ledger von Hand schützen, und genau das ist "
                           "am 07.10.2026 dreimal nicht passiert."))
    else:
        for baustein in ("ledger_sandbox", "beweis_ledger_unangetastet",
                         "fingerabdruck", "ledger_abweichung"):
            if not re.search(rf"def\s+{baustein}\s*\(", ri):
                out.append(("C27", f"repo_isolation.py stellt `{baustein}()` nicht "
                                   f"bereit – die Sandbox ist unvollständig."))
        if "FFC_AUDIT_DIR" in ri and "AUDIT_DIR_ENV" not in ri:
            out.append(("C27", "repo_isolation.py schreibt den Variablennamen fest, "
                               "statt audit_log.AUDIT_DIR_ENV zu benutzen – eine "
                               "Umbenennung im Engpass bliebe unbemerkt."))

    # c) Beobachtung: Der Vertrag braucht einen Regressionstest.
    regress = _read(os.path.join(root, "scripts", "tests",
                                 "test_audit_ledger_isolation.py"))
    if not regress:
        out.append(("C27", "scripts/tests/test_audit_ledger_isolation.py fehlt – "
                           "der Ledger-Vertrag wäre unbeobachtet und könnte "
                           "stillschweigend verrotten."))
    elif "erbt_sich_in_den_subprozess" not in regress:
        out.append(("C27", "test_audit_ledger_isolation.py prüft die Vererbung in "
                           "den Kindprozess nicht – genau dort entstand die "
                           "erste Leckstelle."))

    # d) Empirische Leitplanke im Qualitäts-Gate: unberührtes Ledger nach dem
    #    Suite-Lauf. Statische Regeln allein genügen nicht (Vorbild C15: „wurde
    #    empirisch erhoben, nicht statisch klassifiziert").
    wf = _wf("publication-reliability-tests.yml")
    if not wf:
        out.append(("C27", "publication-reliability-tests.yml nicht lesbar – die "
                           "empirische Ledger-Leitplanke ist nicht prüfbar."))
    elif "git status --porcelain -- data/audit" not in wf:
        out.append(("C27", "publication-reliability-tests.yml prüft nicht, ob "
                           "data/audit/ nach dem Suite-Lauf unberührt ist – ein "
                           "künftiger Test könnte wieder Beweise fabrizieren, "
                           "ohne dass ein Lauf rot wird."))
    return out


# --- C28: Die Klasse geht dem Kanal vor (WF-7C1F #611, 07.10.2026) --------
# Auslöser: Der öffentliche Nachweis („Publication Delivery“) lief am
# 05./06.10.2026 zweimal rot, weil die QUELLE den gemessenen Montag (05.10.)
# nur mit 1/2 LIVE trug. Der Beleg sagte das selbst: `source: 1`,
# `delivered: 1`, `errors: []` – die Auslieferung war vollständig. Der
# Sammel-Schritt „Missing public delivery is a failed run“ nannte keine
# Ursache, also legte das zentrale Fehler-Alerting das generische
# Wartungs-Issue #611 mit API-Key-/Transient-Runbook an, obwohl der Fachkanal
# `engine-deficit` (#602/#608) für genau diesen Zustand existiert. Es ist
# dieselbe Klasse wie #602 – nur beim zweiten Melder derselben Sache.
#
# Die Regel hält fest: Die Auslieferungs-SLO trägt eine KLASSE (`ok`,
# `quelle_unter`, `quelle_ueber`, `auslieferung`, `unbekannt`), der Workflow
# antwortet der Klasse mit einem eigenen, ehrlichen roten Schritt, und nur das
# Bestandsdefizit ruft den Defizit-Fachkanal – mit Frischebeweis VOR dem roten
# Exit, weil das Alerting nur einen offenen UND frisch belegten Kanal als
# Zuständigkeit akzeptiert.
def c28_klassen_routing(script_texts, wflows, root=BLOG_DIR):
    out = []

    def _wf(name: str) -> str:
        for path, text in (wflows or {}).items():
            if os.path.basename(path) == name:
                return text
        return ""

    def _schritte(text: str):
        """(Name, Block) je benanntem Workflow-Schritt – grob, aber stabil."""
        bloecke, name, block = [], None, []
        for zeile in text.splitlines():
            if zeile.lstrip().startswith("- name:"):
                if name:
                    bloecke.append((name, "\n".join(block)))
                name = zeile.split("- name:", 1)[1].strip()
                block = [zeile]
            elif name is not None:
                block.append(zeile)
        if name:
            bloecke.append((name, "\n".join(block)))
        return bloecke

    pc = script_texts.get("publication_check.py", "")
    pd = _wf("publication-delivery.yml")
    af = _wf("alert-on-failure.yml")
    if not pc or not pd:
        out.append(("C28", "publication_check.py / publication-delivery.yml nicht "
                           "lesbar – die Klasse des Auslieferungs-Nachweises ist "
                           "nicht prüfbar."))
        return out

    # a) Die Klasse selbst: vollständig, rein, `ok` zuerst, im Beleg und in der
    #    Historie – sonst endet der Lauf wieder in einem Sammel-Boolean.
    for konst in ("KLASSE_QUELLE_UNTER", "KLASSE_QUELLE_UEBER",
                  "KLASSE_AUSLIEFERUNG", "KLASSE_UNBEKANNT"):
        if konst not in pc:
            out.append(("C28", f"publication_check.py kennt `{konst}` nicht – "
                               "die Klasse des Belegs ist unvollständig (#611)."))
    if not re.search(r"def\s+klasse\s*\(\s*result\s*\)", pc):
        out.append(("C28", "publication_check.py hat keine reine `klasse(result)` "
                           "– ohne sie endet der Lauf wieder in einem "
                           "Sammel-Boolean (#611)."))
    if "result.get('ok')" not in pc:
        out.append(("C28", "publication_check.py prüft `ok` nicht ZUERST – ein "
                           "bestätigter Tag trüge dann eine Defizitklasse."))
    if "result['klasse'] = klasse(result)" not in pc:
        out.append(("C28", "publication_check.py schreibt die Klasse nicht in den "
                           "Beleg (`check()` → `result['klasse']`) – der Workflow "
                           "hätte nichts zu lesen (#611)."))
    if "klasse_aus_beleg" not in pc:
        out.append(("C28", "publication_check.py hat keinen Lesepfad "
                           "`klasse_aus_beleg` – ein fehlender Beleg bliebe "
                           "unbemerkt statt fail-closed laut."))
    if "'klasse':" not in pc:
        out.append(("C28", "publication_check.py schreibt die Klasse nicht in die "
                           "versionierte Historie – ein roter Tag wäre später "
                           "keinem Besitzer zuzuordnen."))

    # b) Der Workflow antwortet der Klasse – kein Sammel-Boolean, kein stiller
    #    unbekannter Beleg.
    if "Missing public delivery is a failed run" in pd:
        out.append(("C28", "publication-delivery.yml endet wieder im Sammel-"
                           "Schritt „Missing public delivery is a failed run“ – "
                           "genau so entstand #611 (Ursache unbenannt)."))
    if "publication_check.py --klasse" not in pd:
        out.append(("C28", "publication-delivery.yml liest die Klasse nicht "
                           "(`publication_check.py --klasse`) – der rote Schritt "
                           "kann den Besitzer nicht nennen (#611)."))
    if "unbekannt" not in pd:
        out.append(("C28", "publication-delivery.yml kennt den unbekannten Beleg "
                           "nicht – ein fehlender Nachweis bliebe still statt "
                           "fail-closed laut."))

    # c) Jede Klasse hat ihren eigenen, ehrlichen roten Schritt – und nur das
    #    Bestandsdefizit ruft den Defizit-Fachkanal (Schrittname = Zuordnung).
    bloecke = _schritte(pd)
    fach = [(n, b) for n, b in bloecke
            if "TAGESDEFIZIT" in n and "engine-deficit" in n]
    if not fach:
        out.append(("C28", "publication-delivery.yml hat keinen Schritt, den das "
                           "zentrale Fehler-Alerting dem Fachkanal zuordnet – die "
                           "Kennwörter „TAGESDEFIZIT“ + „engine-deficit“ im "
                           "Schrittnamen fehlen (#602-Regel)."))
    else:
        name, block = fach[0]
        if "engine_issue.py --deficit" not in block:
            out.append(("C28", f"der Schritt „{name}“ belegt den Fachkanal nicht "
                               "(`engine_issue.py --deficit`) – ohne Frischebeweis "
                               "meldet das Alerting fail-open generisch."))
        elif block.find("engine_issue.py --deficit") > block.find("exit 1"):
            out.append(("C28", f"der Schritt „{name}“ belegt den Fachkanal erst "
                               "NACH dem roten Exit – der Frischebeweis käme zu "
                               "spät (#602)."))
        if "exit 1" not in block:
            out.append(("C28", f"der Schritt „{name}“ endet nicht rot – ein "
                               "Bestandsdefizit darf nicht als grün durchgehen."))
        if "quelle_unter" not in block:
            out.append(("C28", f"der Fachkanal-Schritt „{name}“ gilt nicht "
                               "ausschließlich dem Bestandsdefizit "
                               "(`quelle_unter`)."))
    for klasse in ("quelle_unter", "quelle_ueber", "auslieferung"):
        if klasse not in pd:
            out.append(("C28", f"publication-delivery.yml antwortet der Klasse "
                               f"`{klasse}` nicht – der rote Lauf nennt die "
                               "Ursache nicht (#611)."))
    weitere = [n for n, b in bloecke if "TAGESDEFIZIT" in n
               and "engine-deficit" in n and "exit 1" in b
               and n != (fach[0][0] if fach else "")]
    if weitere:
        out.append(("C28", "weitere rote Schritte tragen die Fachkanal-Kennwörter "
                           f"({', '.join(weitere)}) – die Stummschaltung wäre "
                           "nicht mehr klasse-scharf."))

    # d) Die Zuordnung ist beidseitig eingefroren: Das Alerting sucht genau
    #    diese Kennwörter in den fehlgeschlagenen Schrittnamen.
    if af:
        if "'TAGESDEFIZIT'" not in af or "'engine-deficit'" not in af:
            out.append(("C28", "alert-on-failure.yml hat die Fachkanal-Regel "
                               "(„TAGESDEFIZIT“ + „engine-deficit“ in den "
                               "fehlgeschlagenen Schrittnamen) verloren – die "
                               "Stummschaltung des generischen Issues greift "
                               "nicht mehr."))
        if '"Publication Delivery (öffentlicher Nachweis)"' not in af:
            out.append(("C28", "alert-on-failure.yml beobachtet „Publication "
                               "Delivery (öffentlicher Nachweis)“ nicht mehr – "
                               "ein roter Nachweis bliebe unbemerkt."))
    return out


# --- C29: Der Schreiber prüft, was über ihn entscheidet (WF-D4E0 #612, 07.10.2026)
# Auslöser: Die Content-Reserve lief N acht für Nacht rot, weil der Vorrat
# unter dem Ziel stand (`ready 2/6`, #612). Die Wurzel lag nicht in der
# Zertifizierung – die hat korrekt abgelehnt – sondern in der GEBURT: Das
# „Profi-Gate“ (`generate_drafts.profi_quality_ok`) prüfte Länge, Module,
# Keywords und Struktur, aber NICHT die Lesbarkeit, obwohl Flesch ≥ 60 seit
# #585 ein hartes Publish-Kriterium ist. Kandidaten wurden mit Flesch 53–60
# geboren, fielen geschlossen durch die Zertifizierung und banden danach
# Heiler-/KI-Zeit; blieb die Heilung aus, nahm die Quarantäne den Kandidaten
# aus dem Pool (#513, #609, #612).
#
# Die zweite Hälfte desselben Befunds: Der Retry war blind. `try_generate`
# sammelte die Ablehnungsgründe, gab sie aber nie an den nächsten Versuch
# weiter – dreimal derselbe Fehler mit dreimal derselben Wahrscheinlichkeit.
#
# Die dritte: Der Trend-Beweis war strukturell blind. `reserve_gate` schrieb
# die Chronik-Zeile NACH dem einzigen Commit-Schritt des Laufs; jeder rote
# Lauf verlor sie wieder. Der letzte CI-Eintrag stammte vom 02.10., alle
# späteren Zeilen waren lokale Reparaturläufe – genau die Nächte fehlten, die
# man später erklären will.
#
# Diese Regel hält die drei Lektionen fest und prüft sie am echten Baum:
#   * `profi_quality_ok` misst die Lesbarkeit über die IMPORTIERTE SSOT
#     (`readability_check.NEW_FLESCH_MIN`) – keine zweite Zahl (#585),
#   * `generate_article_text` kennt Korrektur-Hinweise, und `try_generate`
#     gibt die Befunde des Vorversuchs weiter (Retry mit Gedächtnis),
#   * die Chronik wird VOR dem Sicherungs-Commit geschrieben und ist je Lauf
#     idempotent,
#   * der Politur-Ruinen-Heiler (#612) hält die harte R11/R13/R14-Familie in
#     der Reserve-Kette heilbar und beweist seine Wirkung JETZT (Exit 0).
RE_C29_QUALITY_FN = re.compile(r"def\s+profi_quality_ok\s*\(.*?(?=\ndef\s)", re.S)


def c29_geburts_tor(script_texts, wflows, root=BLOG_DIR, python_bin=None):
    out = []
    gd = script_texts.get("generate_drafts.py", "")
    eg = script_texts.get("engine_generate.py", "")
    rg = script_texts.get("reserve_gate.py", "")
    heiler = script_texts.get("politur_ruine_heiler.py", "")
    kette = script_texts.get("reserve_finisher.py", "")
    deckung = script_texts.get("reserve_healer_coverage.py", "")
    if not gd or not eg or not rg:
        out.append(("C29", "generate_drafts.py / engine_generate.py / "
                           "reserve_gate.py nicht lesbar – das Geburts-Tor ist "
                           "nicht prüfbar (fail-closed)."))
        return out

    # a) Die Geburt misst die Regel, die über die Veröffentlichung entscheidet.
    if "lesbarkeits_befund" not in gd:
        out.append(("C29", "generate_drafts.py misst die Lesbarkeit nicht am "
                           "Geburts-Gate – Kandidaten entstehen wieder unter der "
                           "Publish-Schwelle und die Zertifizierung lehnt sie "
                           "geschlossen ab (#612)."))
    else:
        koerper = RE_C29_QUALITY_FN.search(gd)
        if not koerper or "lesbarkeits_befund(body)" not in koerper.group(0):
            out.append(("C29", "`profi_quality_ok` ruft die Lesbarkeits-Messung "
                               "nicht auf – eine Funktion ohne Aufruf ist "
                               "Papier (#612)."))
    if "NEW_FLESCH_MIN" not in gd:
        out.append(("C29", "generate_drafts.py liest die Schwelle nicht aus der "
                           "SSOT `readability_check.NEW_FLESCH_MIN` (#585)."))
    if re.search(r"NEW_FLESCH_MIN\s*=\s*[0-9]", gd):
        out.append(("C29", "generate_drafts.py definiert die Flesch-Schwelle "
                           "selbst – zweite Wahrheit (#585)."))

    # b) Der Retry hat ein Gedächtnis.
    if "KORREKTUR-AUFTRAG" not in gd or "hinweise" not in gd:
        out.append(("C29", "`generate_article_text` kennt keinen "
                           "Korrektur-Auftrag – der nächste Versuch würfelt "
                           "denselben Fehler blind neu (#612)."))
    if "hinweise=" not in eg:
        out.append(("C29", "`engine_generate.try_generate` gibt die Befunde des "
                           "Vorversuchs nicht an den Schreiber weiter (#612)."))

    # c) Die Chronik gehört VOR den Sicherungs-Commit.
    if "--chronik" not in rg or "chronik_schreiben(" not in rg:
        out.append(("C29", "reserve_gate.py kennt den Chronik-Modus nicht – der "
                           "Trend-Beweis ginge wieder verloren (#612)."))
    yml = wflows.get(os.path.join(root, ".github", "workflows",
                                  "content-reserve.yml"), "")
    if not yml:
        out.append(("C29", "content-reserve.yml nicht lesbar – die "
                           "Chronik-Reihenfolge ist nicht prüfbar."))
    else:
        if "reserve_gate.py --chronik" not in yml:
            out.append(("C29", "content-reserve.yml schreibt die Reserve-Chronik "
                               "nicht VOR dem Commit – rote Läufe verlören ihre "
                               "Zeile (der letzte CI-Eintrag stammte vom "
                               "02.10., #612)."))
        else:
            pos_chronik = yml.find("reserve_gate.py --chronik")
            pos_commit = yml.find("Entwürfe, Zertifikate und Reporte sichern")
            if pos_commit != -1 and pos_chronik > pos_commit:
                out.append(("C29", "die Chronik steht in content-reserve.yml NACH "
                                   "dem Sicherungs-Commit – genau die Reihenfolge, "
                                   "die den Trend-Beweis rot machte (#612)."))

    # d) Der Ruinen-Heiler: in der Kette, in der Deckung, Wirkung JETZT.
    if not heiler:
        out.append(("C29", "scripts/politur_ruine_heiler.py fehlt – R11/R13/R14 "
                           "wären wieder ein harter Blocker ohne Heiler (#612)."))
    else:
        if '("politur_ruine_heiler.py"' not in kette:
            out.append(("C29", "reserve_finisher.HEALER_CHAIN fährt den "
                               "Politur-Ruinen-Heiler nicht – ein fertiger "
                               "Kandidat bliebe an einem „SATZ: “-Rest hängen "
                               "(#612)."))
        if "politur_ruine_heiler.py" not in deckung:
            out.append(("C29", "reserve_healer_coverage.py nennt den "
                               "Politur-Ruinen-Heiler nicht – die Familie gälte "
                               "wieder als gedeckt, ohne dass jemand sie heilt."))
        bin_ = python_bin or sys.executable or "python3"
        try:
            lauf = subprocess.run(
                [bin_, os.path.join(root, "scripts", "politur_ruine_heiler.py"),
                 "--wirkungsprobe"], cwd=root, capture_output=True, text=True,
                timeout=180)
        except (OSError, subprocess.TimeoutExpired) as exc:
            out.append(("C29", f"Wirkungsprobe des Ruinen-Heilers nicht "
                               f"ausführbar ({exc.__class__.__name__}) – "
                               f"fail-closed."))
            return out
        if lauf.returncode != 0:
            zeilen = ((lauf.stdout or "") + (lauf.stderr or "")).strip().splitlines()
            out.append(("C29", "Wirkungsprobe des Ruinen-Heilers ROT: "
                               + (zeilen[-1][:160] if zeilen
                                  else f"Exit {lauf.returncode}")))
    return out


# --- C30: Eine Seite hat genau eine H1 (WF-A11Y #623, 07.10.2026) -----------
#
# DER BEFUND: Am 07.10.2026 meldete das wöchentliche Audit auf /presse/ und
# /studien/ je ZWEI H1. Ursache: Beide Markdown-Dokumente trugen im
# FLIESSTEXT eine eigene `# …`-Zeile, obwohl jedes Layout die H1 bereits
# aus dem Titel setzt. Für Screenreader, Inhaltsverzeichnisse und
# KI-Antworten kippt damit die Gliederung (WCAG 1.3.1 / 2.4.6).
#
# DER EIGENTLICHE SCHADEN war größer als die Meldung und lag in zwei
# Blindstellen, die dieser Vertrag schließt:
#   1. STICHPROBE: Das Audit prüfte 20 von 107 gebauten Seiten. Die dritte
#      Doppel-H1 (/studien/fixkosten-index-2026-q4/) stand im selben Build
#      und blieb unsichtbar. Wer ein Fünftel misst, würfelt.
#   2. TOTER ZWEIG: Die Einzelansicht lag ZWEIMAL im Repo
#      (_default/single.html und single.html), gepflegt „deckungsgleich“,
#      mit dem Vermerk „layouts/single.html gewinnt die Template-Auflösung“.
#      Ein Baustein-Marker im gebauten HTML bewies das Gegenteil: Hugo
#      löst `_default/single.html` ZUERST auf. Die Kopie war der Zweig, der
#      ins Leere lief – jede künftige Heilung dort wäre versandet.
#
# Was der Vertrag verlangt: EIN Baustein trägt die H1 und ehrt `heading:`
# (eine eigene Schirmzeile, ohne dass der Fließtext eine zweite H1
# liefert). Die Wache prüft Quelle UND Build – und das Audit prüft ALLE
# Seiten, keine Stichprobe. Geheilt wird nie automatisch: Eine H1 zu
# löschen hieße, einen redaktionellen Satz zu vernichten.
#
# STUFE 2 (08.10.2026, „verifizieren & nachhärten“): Die Nachprüfung fand
# drei Ränder, die Stufe 1 nicht sah – und einen echten, LIVE Befund:
#   A) MARKDOWN-WAHRHEIT: Eine reine `#`-Suche übersah eingerückte ATX-H1
#      (bis drei Leerzeichen), Setext-H1 (`=====`) und rohes `<h1 …>`
#      (hugo.toml: `unsafe = true`). Alle drei rendert Goldmark als H1 –
#      die Quellprüfung wäre still geblieben, der Build hätte es getragen.
#   B) DIE AUSNAHME, DIE EINEN BEFUND VERDECKTE: `page/N/` war pauschal als
#      „Blätter-Redirect ohne Inhalt“ ausgenommen. Mit
#      `[pagination] disableAliases = true` (29.09.2026) gibt es diese
#      Redirects nicht mehr: /page/2/ … /page/5/ sind echte, verlinkte
#      Seiten – und trugen GAR KEINE H1. Der Befund war für die Wache
#      unsichtbar, weil die Ausnahme ihn deckte.
#   C) LAYOUT-INVENTAR: S2 kannte vier Dateien. Neun Dateien rendern H1.
#      Jetzt gilt ein fail-closed Inventar (H1_QUELLEN + SEITENARTEN) plus
#      Parität der eigenen Einzelansichten (pillar/, werkzeuge/).
# Der Vertrag prüft deshalb zusätzlich: Inventar und Seitenarten-Tabelle
# existieren und passen zusammen, der Startseiten-Blätterkopf hängt an
# seinem Marker, die Einzelansichten mit eigener Vorlage ehren `heading:`,
# und die Ausnahmen decken KEINE Blätterseite mehr (Wirkungsprobe – eine
# Textsuche wäre hier unzuverlässig, weil die Datei die alte Ausnahme
# dokumentiert).
RE_C30_H1 = re.compile(r"<h1(?=[\s>])")


def c30_eine_h1(script_texts, wflows, root=BLOG_DIR, python_bin=None):
    out = []
    wache = script_texts.get("h1_wache.py", "")
    audit = script_texts.get("a11y_audit.py", "")
    baustein = _read(os.path.join(root, "layouts", "_partials",
                                  "artikel_einzeln.html"))
    single_default = _read(os.path.join(root, "layouts", "_default", "single.html"))
    single_wurzel = _read(os.path.join(root, "layouts", "single.html"))
    liste = _read(os.path.join(root, "layouts", "_default", "list.html"))
    deploy = ""
    e2e = ""
    for pfad, text in (wflows or {}).items():
        name = os.path.basename(str(pfad))
        if name == "deploy.yml":
            deploy = text
        elif name == "e2e.yml":
            e2e = text
    paket = _read(os.path.join(root, "package.json"))
    tests = os.path.join(root, "scripts", "tests", "test_h1_wache.py")
    a11y_tests = os.path.join(root, "scripts", "tests", "test_a11y_audit.py")

    if not wache:
        out.append(("C30", "scripts/h1_wache.py fehlt – ohne Wache ist „genau "
                           "eine H1 pro Seite“ eine Behauptung, kein Zustand "
                           "(#623, fail-closed)."))
    else:
        # a) Quelle UND Build: nur eine Seite der Wahrheit zu prüfen, ist
        #    genau die Halbheit, die #623 teuer machte. Geprüft wird nicht
        #    die ERWÄHNUNG der Flagge (eine Doku-Zeile genügt sonst als
        #    Alibi), sondern Registrierung UND Auswertung – eine Flagge,
        #    die niemand liest, ist Papier.
        for flagge, feld, sinn in (("--source-only", "args.source_only",
                                    "Quellprüfung ohne Build"),
                                   ("--public", "args.public",
                                    "Prüfung der gebauten Seiten"),
                                   ("--selftest", "args.selftest",
                                    "Sabotageproben der Wache")):
            if f'"{flagge}"' not in wache or feld not in wache:
                out.append(("C30", f"scripts/h1_wache.py registriert `{flagge}` "
                                   f"nicht oder wertet sie nicht aus ({sinn}) – "
                                   f"eine Wache ohne diesen Pfad lässt die "
                                   f"Hälfte des Befunds wieder durch (#623)."))
        if "archetypes" not in wache:
            out.append(("C30", "scripts/h1_wache.py prüft die Archetypen nicht – "
                               "eine H1 in einer Vorlage vererbt sich an jeden "
                               "neuen Artikel (#623)."))
        if "class _H1TextParser(HTMLParser)" not in wache:
            out.append(("C30", "scripts/h1_wache.py verwendet keinen HTML-aware Parser – "
                               "Skriptstrings, Kommentare oder Entities könnten den "
                               "H1-Befund verfälschen."))
        if "--fix" in wache:
            out.append(("C30", "scripts/h1_wache.py bietet ein `--fix` an: Eine H1 "
                               "automatisch zu löschen vernichtet einen "
                               "redaktionellen Satz. Die Wache meldet den "
                               "Handgriff, sie führt ihn nicht aus (#623)."))
        # a2) Die Ausnahmen-Registry selbst: Sie darf keine Blätterseite
        #     decken. Geprüft wird der Registry-Block (b2 misst zusätzlich das
        #     Verhalten) – die Prosa daneben ist ausdrücklich erlaubt, denn
        #     sie erklärt die alte, falsche Ausnahme.
        block = re.search(r"AUSNAHMEN_H1[^\n=]*=\s*\((?P<body>.*?)\n\)", wache, re.S)
        if block is None:
            out.append(("C30", "scripts/h1_wache.py: AUSNAHMEN_H1 ist nicht als "
                               "begründete Registry erkennbar (fail-closed)."))
        elif re.search(r"page/", block.group("body")):
            out.append(("C30", "Die Ausnahmen der H1-Wache decken wieder "
                               "Blätterseiten (page/N/) – genau diese "
                               "Pauschalausnahme verdeckte, dass /page/2/ … "
                               "gar keine H1 trugen (#623, Stufe 2)."))
        # a3) Stufe 2: die Markdown-Wahrheit, das Inventar und der
        #     Startseiten-Blätterkopf sind Eigenschaften der Wache selbst.
        for marke, sinn in (
                ("SETEXT_UNTERSTRICH", "Setext-H1 (`Text` + `=====`)"),
                ("markdown_roh_html_h1", "rohes `<h1 …>` im Markdown (`unsafe = true`)"),
                ("H1_QUELLEN", "Inventar aller H1-Quellen im Layout-Baum"),
                ("SEITENARTEN", "Seitenarten-Tabelle (keine Seite ohne H1-Quelle)"),
                ("H1_BLAETTERKOPF", "Startseiten-Blätterkopf (/page/N/ braucht eine H1)"),
        ):
            if marke not in wache:
                out.append(("C30", f"Der H1-Wache fehlt {sinn} ({marke}) – Stufe 1 "
                                   f"war an genau diesem Rand blind; ohne die "
                                   f"Prüfung entsteht der Befund wieder unsichtbar "
                                   f"(#623, 08.10.2026)."))
        # b) Wirkungsprobe: der Selbsttest der Wache muss JETZT grün sein.
        bin_ = python_bin or sys.executable or "python3"
        try:
            lauf = subprocess.run(
                [bin_, os.path.join(root, "scripts", "h1_wache.py"), "--selftest"],
                cwd=root, capture_output=True, text=True, timeout=180)
        except (OSError, subprocess.TimeoutExpired) as exc:
            out.append(("C30", f"Wirkungsprobe der H1-Wache nicht ausführbar "
                               f"({exc.__class__.__name__}) – fail-closed."))
        else:
            if lauf.returncode != 0:
                zeilen = ((lauf.stdout or "") + (lauf.stderr or "")).strip().splitlines()
                out.append(("C30", "Wirkungsprobe der H1-Wache ROT: "
                            + (zeilen[-1][:160] if zeilen
                               else f"Exit {lauf.returncode}")))
        # b2) Wirkungsprobe der Ausnahmen (Stufe 2): Eine Blätterseite darf
        #     NICHT ausgenommen sein – genau diese Pauschalausnahme verdeckte,
        #     dass /page/2/ … gar keine H1 trugen. Textsuche wäre hier
        #     unzuverlässig, weil die Wache die alte Ausnahme dokumentiert;
        #     gemessen wird deshalb das Verhalten.
        probe = (
            "import sys;sys.path.insert(0,'scripts');import h1_wache as w;"
            "print('|'.join([w.ausnahme_grund('page/2/index.html'),"
            "w.ausnahme_grund('posts/page/3/index.html'),"
            "w.ausnahme_grund('google123.html'),"
            "w.ausnahme_grund('pinterest-oauth/index.html')]))")
        try:
            mess = subprocess.run([bin_, "-c", probe], cwd=root,
                                  capture_output=True, text=True, timeout=60)
        except (OSError, subprocess.TimeoutExpired) as exc:
            out.append(("C30", f"Ausnahmen der H1-Wache nicht messbar "
                               f"({exc.__class__.__name__}) – fail-closed."))
        else:
            felder = (mess.stdout or "").strip().split("|")
            if len(felder) < 4 or mess.returncode != 0:
                out.append(("C30", "Ausnahmen der H1-Wache nicht messbar "
                                   "(Probe ohne Ergebnis) – fail-closed."))
            else:
                if felder[0] or felder[1]:
                    out.append(("C30", "Die H1-Wache nimmt Blätterseiten "
                                       "(page/N/) wieder pauschal aus – diese "
                                       "Ausnahme verdeckte bis 08.10.2026, dass "
                                       "/page/2/ … gar keine H1 trugen (#623)."))
                if not felder[2] or not felder[3]:
                    out.append(("C30", "Die begründeten Ausnahmen "
                                       "(Verifikationsdateien, Pinterest-Redirect) "
                                       "fehlen – das Gate würde Dateien prüfen, "
                                       "die nie ein Layout sehen."))

    # c) EIN Baustein, EINE H1 – und beide Zweige zeigen auf ihn.
    if not baustein.strip():
        out.append(("C30", "layouts/_partials/artikel_einzeln.html fehlt – damit "
                           "liegt die Einzelansicht wieder in zwei Kopien, von "
                           "denen eine nie rendert (toter Zweig, #623)."))
    else:
        if len(RE_C30_H1.findall(baustein)) != 1:
            out.append(("C30", "layouts/_partials/artikel_einzeln.html rendert nicht "
                               "genau eine H1 – jede weitere ist eine Doppel-H1 "
                               "(#623)."))
        if ".Params.heading" not in baustein:
            out.append(("C30", "layouts/_partials/artikel_einzeln.html ehrt "
                               "`.Params.heading` nicht – eine eigene Schirmzeile "
                               "ließe sich nur über eine `# …`-Zeile im Fließtext "
                               "setzen, also über die zweite H1 aus #623."))
    for name, text in (("_default/single.html", single_default),
                       ("single.html", single_wurzel)):
        if not text.strip():
            out.append(("C30", f"layouts/{name} ist leer – die Einzelansicht würde "
                               "nicht rendern."))
        elif 'partial "artikel_einzeln.html"' not in text:
            out.append(("C30", f"layouts/{name} bindet den gemeinsamen Baustein "
                               "nicht ein – eine zweite Kopie der Einzelansicht "
                               "wäre wieder ein Zweig, der ins Leere läuft "
                               "(#623)."))
    if ".Params.heading" not in liste:
        out.append(("C30", "layouts/_default/list.html ehrt `.Params.heading` nicht "
                           "– Abschnittsseiten bräuchten für eine Schirmzeile "
                           "wieder eine H1 im Fließtext (#623)."))
    # c2) Parität der Einzelansichten mit eigener Vorlage (Stufe 2): Auch
    #     Themenwelt- und Werkzeug-Seiten rendern ihre H1 selbst. Ohne
    #     `heading:`-Ehrung wäre die dokumentierte Heilung dort wirkungslos.
    for rel in ("pillar/single.html", "werkzeuge/single.html"):
        text = _read(os.path.join(root, "layouts", rel))
        if not text.strip():
            out.append(("C30", f"layouts/{rel} ist leer – die Einzelansicht "
                               "würde nicht rendern."))
        elif ".Params.heading" not in text:
            out.append(("C30", f"layouts/{rel} ehrt `.Params.heading` nicht – "
                               "die dokumentierte Schirmzeile wäre auf dieser "
                               "Seite wirkungslos, und die nächste eigene "
                               "Überschrift landete wieder als zweite H1 im "
                               "Fließtext (#623)."))
    # c3) Startseiten-Blätterkopf: /page/N/ ab Seite 2 ist eine echte Seite
    #     und braucht eine H1. Der Marker bindet die Prüfung an den Zweig.
    if "H1-BLÄTTERKOPF" not in liste:
        out.append(("C30", "layouts/_default/list.html trägt den Marker "
                           "„H1-BLÄTTERKOPF“ nicht – die Startseiten-Blätter "
                           "/page/2/ … stehen dann wieder ohne jede H1 da "
                           "(Befund vom 08.10.2026, #623)."))

    # d) Das Audit darf keine Stichprobe mehr sein: 20 von 107 Seiten sahen
    #    die dritte Doppel-H1 nicht.
    if not audit:
        out.append(("C30", "scripts/a11y_audit.py nicht lesbar – ohne das Audit ist "
                           "die H1-Regel nur zur Hälfte belegt (#623)."))
    else:
        if re.search(r"\[\s*20\s*\]|STICHPROBE\s*=|files\[:\s*\d+\s*\]", audit):
            out.append(("C30", "scripts/a11y_audit.py prüft wieder nur eine "
                               "STICHPROBE – genau die Blindstelle, die die dritte "
                               "Doppel-H1 am 07.10.2026 verdeckt hat (#623)."))
        if ("from h1_wache import AUSNAHMEN_SEITE" not in audit
                or "h1_der_seite" not in audit or "h1_ist_gefuellt" not in audit):
            out.append(("C30", "scripts/a11y_audit.py bezieht Ausnahme-Registry und "
                               "HTML-aware H1-Erkennung nicht direkt aus der H1-Wache – "
                               "zwei Wahrheiten könnten auseinanderlaufen."))
        if ("AUSNAHMEN = (" in audit or "SKIP_PATTERNS" in audit
                or 'if "assets" in root' in audit):
            out.append(("C30", "scripts/a11y_audit.py enthält wieder eine lokale "
                               "Ersatz-Ausnahmeliste oder einen undokumentierten "
                               "Datei-/Verzeichnisfilter; das Audit muss fail-closed "
                               "und vollständig bleiben."))
        if ("_require_h1_contract" not in audit or "public/ fehlt" not in audit
                or "return 2" not in audit):
            out.append(("C30", "scripts/a11y_audit.py meldet eine fehlende H1-Wache "
                               "oder einen fehlenden Build nicht fail-closed."))

    # e) Verdrahtung: geprüft wird erst, wenn der Deploy es verlangt.
    if deploy:
        if "scripts/h1_wache.py --source-only" not in deploy:
            out.append(("C30", "deploy.yml ruft die H1-Wache nicht VOR dem Build – "
                               "die Quelle käme ungeprüft in den Build (#623)."))
        if "scripts/h1_wache.py --public public" not in deploy:
            out.append(("C30", "deploy.yml prüft die gebauten Seiten nicht – die "
                               "Doppel-H1 stünde wieder live, bevor jemand sie "
                               "sieht (#623)."))
        if "scripts.tests.test_a11y_audit" not in deploy:
            out.append(("C30", "deploy.yml führt die Fail-closed-/Vollständigkeits-Regressionen "
                               "des A11y-Audits nicht vor dem Build aus."))
    else:
        out.append(("C30", "deploy.yml nicht lesbar – die Verdrahtung der H1-Wache "
                           "ist nicht prüfbar."))
    e2e_pfade = (
        "scripts/h1_wache.py",
        "scripts/a11y_audit.py",
        "scripts/tests/test_h1_wache.py",
        "scripts/tests/test_a11y_audit.py",
    )
    if not e2e:
        out.append(("C30", "e2e.yml nicht lesbar – Änderungen an H1-Wache/Audit "
                           "lösen keine Browser-Regression aus."))
    else:
        for pfad in e2e_pfade:
            if f'"{pfad}"' not in e2e:
                out.append(("C30", f"e2e.yml-Pfadfilter fehlt `{pfad}` – Änderungen "
                                   "an der H1-Wache könnten ohne Browser-Regression "
                                   "durchrutschen."))
        # Im Pull Request wird gebaut: dort muss die gebaute Wahrheit auch
        # gemessen werden (Stufe 2) – sonst fällt ein Blätter-Befund wie der
        # vom 08.10.2026 erst nach dem Merge auf.
        if "scripts/h1_wache.py --public public" not in e2e:
            out.append(("C30", "e2e.yml prüft die GEBAUTEN Seiten nicht – im "
                               "Pull Request bliebe die gebaute Wahrheit "
                               "ungemessen (#623, Stufe 2)."))
    if paket and '"h1:check"' not in paket:
        out.append(("C30", "package.json kennt `h1:check` nicht – eine Wache, die "
                           "man lokal nicht rufen kann, wartet auf den nächsten "
                           "Montag (#623)."))
    if paket and ('"test:h1"' not in paket or "scripts.tests.test_a11y_audit" not in paket):
        out.append(("C30", "package.json bündelt die H1-Wache nicht mit den "
                           "Regressionstests des A11y-Audits."))
    if not os.path.isfile(tests):
        out.append(("C30", "scripts/tests/test_h1_wache.py fehlt – ohne "
                           "Regressionstest fällt die nächste Doppel-H1 erst im "
                           "wöchentlichen Audit auf (#623)."))
    if not os.path.isfile(a11y_tests):
        out.append(("C30", "scripts/tests/test_a11y_audit.py fehlt – Vollständigkeit, "
                           "eine einzige Ausnahmenquelle und fail-closed sind nicht "
                           "dauerhaft belegt."))
    return out


# --- C32: Doppelte Mapping-Schluessel sind eine Bau-Ursache (WF-54C4 #643) ---
# Am 08.10.2026 starb der Produktions-Build an fuenf Reserve-Artikeln, die aus
# einem Merge je zwei `tags:`-Zeilen trugen. go-yaml bricht dort HART ab
# (`mapping key "tags" already defined`), PyYAML liest dieselbe Datei still
# (letzter Wert gewinnt) – ALLE bisherigen Gates waren gruen. Die Wache heilt
# jetzt VOR dem Build (ohne die Klasse nachtraeglich zu entschaerfen), und
# jeder FM-Schreiber endet mit genau einem Feld. Diese Regel prueft nicht die
# Absicht, sondern die Verdrahtung UND die lebende Wirkung.
# Haus-Nummern: C31 ist der Robustheits-Vertrag (robustheits_gate.py), C24 die
# C24 Bank – beide sind keine Regeln dieses Vertrags. C32 ist darum frei.
def c32_doppelte_schluessel(script_texts, wflows, root=BLOG_DIR, python_bin=None):
    out = []
    wache = script_texts.get("fm_boundary_guard.py", "")
    schreiber = script_texts.get("post_utils.py", "")
    tag = script_texts.get("tag_governance.py", "")
    kw = script_texts.get("keyword_optimizer.py", "")
    pin = script_texts.get("pinterest_pin_text_sync.py", "")
    deploy = ""
    rel = ""
    for pfad, text in (wflows or {}).items():
        name = os.path.basename(str(pfad))
        if name == "deploy.yml":
            deploy = text
        elif name == "publication-reliability-tests.yml":
            rel = text

    # a) Die Wache: Klasse vorhanden, VOR dem Parser-Kurzschluss geprueft,
    #    in beiden Modus-Pfaden verdrahtet, mit Index-Blob-Pfad (--staged).
    if not wache:
        out.append(("C32", "scripts/fm_boundary_guard.py fehlt – ohne die Wache "
                           "ist „kein doppelter Mapping-Schluessel“ eine "
                           "Behauptung, keine Pruefung (#643, fail-closed)."))
    else:
        for marke, sinn in (
                ("def doppelte_schluessel(", "Erkennung der Klasse F7"),
                ("def heile_doppelte(", "verlustfreie Heilung (Listen vereinigt, "
                                        "sonst gilt der letzte Wert)"),
                ("doppel_funde", "Meldung der Funde im Prueflauf"),
                ("doppel_heilungen", "Beleg jeder Heilung (Report-Pflicht)"),
                ("def staged_content(", "Pruefung der GESTAGETEN Blobs (--staged)"),
                ("--wirkungsprobe", "Fixture-Beweis der Wirkung")):
            if marke not in wache:
                out.append(("C32", f"scripts/fm_boundary_guard.py kennt {sinn} "
                                   f"nicht (`{marke}`) – genau diese Haelfte von "
                                   f"#643 koennte unbemerkt zurueckkehren."))
        idx_f7 = wache.find("doppel = doppelte_schluessel(fm_lines)")
        idx_ok = wache.find("if not doppel and _yaml is not None and parse_ok(")
        if idx_f7 == -1:
            out.append(("C32", "scripts/fm_boundary_guard.py ruft die F7-Erkennung "
                               "nicht mit den Frontmatter-Zeilen auf – PyYAML "
                               "akzeptiert doppelte Schluessel, nur der Zeilenscan "
                               "sieht sie (#643)."))
        elif idx_ok == -1 or idx_f7 > idx_ok:
            out.append(("C32", "scripts/fm_boundary_guard.py laesst den "
                               "Parser-Kurzschluss VOR der F7-Erkennung greifen – "
                               "dann bleibt genau der Fall unsichtbar, der den "
                               "Build am 08.10.2026 getoetet hat (#643)."))
        if "python3 scripts/fm_boundary_guard.py" not in wache:
            out.append(("C32", "scripts/fm_boundary_guard.py nennt seinen Aufruf "
                               "nicht – Charta und Kommando sollen nicht "
                               "auseinanderlaufen."))

    # b) Die Verdrahtung: heilen VOR dem Build, pruefen im PR (fail-closed).
    if not deploy:
        out.append(("C32", "deploy.yml nicht lesbar – die Reihenfolge "
                           "(Heilen vor dem Build) ist nicht pruefbar."))
    else:
        if "scripts/fm_boundary_guard.py --fix" not in deploy:
            out.append(("C32", "deploy.yml ruft `fm_boundary_guard.py --fix` nicht "
                               "– ein doppelter Schluessel stuerzt den Build ab, "
                               "statt vorher geheilt zu werden (#643)."))
        if "scripts/fm_boundary_guard.py --selftest" not in deploy:
            out.append(("C32", "deploy.yml prueft die Wache nicht selbst – eine "
                               "tote Wache vor dem Build faellt niemandem auf "
                               "(#643)."))
        idx_fix = deploy.find("scripts/fm_boundary_guard.py --fix")
        idx_bau = deploy.find("./.github/actions/hugo-build")
        if idx_fix != -1 and idx_bau != -1 and idx_fix > idx_bau:
            out.append(("C32", "deploy.yml heilt die FM-Grenzen erst NACH dem "
                               "Build-Schritt – genau die Reihenfolge, an der "
                               "der Deploy am 08.10.2026 gestorben ist (#643)."))
    if not rel:
        out.append(("C32", "publication-reliability-tests.yml nicht lesbar – der "
                           "PR-Pfad (fail-closed ohne --fix) ist nicht pruefbar."))
    elif "scripts/fm_boundary_guard.py --check" not in rel:
        out.append(("C32", "publication-reliability-tests.yml ruft "
                           "`fm_boundary_guard.py --check` nicht – ein PR koennte "
                           "doppelte Schluessel unbemerkt nach main tragen (#643)."))

    # c) Die Schreiber-Schlussregel: EINE Regel, kein zweiter Schluessel.
    if "def doppel_freies_feld(" not in schreiber:
        out.append(("C32", "scripts/post_utils.py kennt die gemeinsame "
                           "Schreiber-Schlussregel `doppel_freies_feld` nicht – "
                           "ein Heiler mit `count=1` liesse die zweite Zeile "
                           "stehen und wuerde die Falle nur unsichtbar machen "
                           "(#643)."))
    for name, text in (("keyword_optimizer.py", kw),
                       ("tag_governance.py", tag),
                       ("pinterest_pin_text_sync.py", pin)):
        if text and "doppel_freies_feld" not in text:
            out.append(("C32", f"scripts/{name} schreibt Top-Level-Felder ohne "
                               f"`doppel_freies_feld` – der naechste Schreibvorgang "
                               f"koennte einen zweiten Schluessel hinterlassen "
                               f"(#643)."))

    # d) Lebende Wirkung: Selbsttest UND Fixture-Beweis muessen JETZT gruen sein.
    bin_ = python_bin or sys.executable or "python3"
    for flagge, sinn in (("--selftest", "Sabotageproben der Wache"),
                         ("--wirkungsprobe", "Fixture-Beweis der F7-Wirkung")):
        if not wache:
            break
        try:
            lauf = subprocess.run(
                [bin_, os.path.join(root, "scripts", "fm_boundary_guard.py"), flagge],
                cwd=root, capture_output=True, text=True, timeout=180)
        except (OSError, subprocess.TimeoutExpired) as exc:
            out.append(("C32", f"{sinn} nicht ausfuehrbar "
                               f"({exc.__class__.__name__}) – fail-closed."))
        else:
            if lauf.returncode != 0:
                zeilen = ((lauf.stdout or "") + (lauf.stderr or "")).strip().splitlines()
                out.append(("C32", f"{sinn} ROT: "
                                   + (zeilen[-1][:160] if zeilen
                                      else f"Exit {lauf.returncode}")))
    return out


RULE_TEXT = {
    "C32": "Doppelte Mapping-Schluessel sind eine Bau-Ursache: go-yaml bricht "
           "bei einem wiederholten Schluessel HART ab (`mapping key \"…\" "
           "already defined`), PyYAML liest dieselbe Datei still weiter (letzter "
           "Wert gewinnt). Genau daran starben am 08.10.2026 fuenf Reserve-"
           "Artikel aus einem Merge (WF-54C4 #643): FM-Grenze, Taxonomie und "
           "alle PyYAML-Gates waren gruen, der Deploy starb im Bauschritt. Die "
           "Wache (scripts/fm_boundary_guard.py, F7) erkennt die Klasse im "
           "Zeilenscan VOR dem Parser-Kurzschluss, heilt verlustfrei VOR dem "
           "Build (Listen werden vereinigt, sonst gilt die YAML-Leseregel: der "
           "letzte Wert bleibt, das fruehere Vorkommen faellt mit Beleg weg) und "
           "prueft die gestageten Blobs im PR. Jeder FM-Schreiber endet ueber "
           "`post_utils.doppel_freies_feld` mit GENAU EINEM Top-Level-Feld – "
           "ein Heiler mit `count=1` wuerde die Falle sonst nur unsichtbar "
           "machen.",
    "C30": "Eine Seite hat genau eine H1: Die Schirmzeile gehoert dem Layout, "
           "nie dem Markdown-Fliesstext – wer eine eigene braucht, setzt sie "
           "als `heading:` ins Frontmatter. Eine Wache (scripts/h1_wache.py) "
           "prueft Quelle (content/ + archetypes/, inklusive "
           "Template-Verdrahtung) UND Build (jede gebaute Seite), und das "
           "Barrierefreiheits-Audit prueft ALLE Seiten statt einer "
           "Stichprobe. Er nutzt denselben HTML-aware Parser und dasselbe "
           "Ausnahmenregister; ohne Wache oder Build ist das Ergebnis "
           "fail-closed statt eines falschen Gruens. Geheilt wird nie automatisch: Eine H1 zu loeschen "
           "hiesze, einen redaktionellen Satz zu vernichten. Am 07.10.2026 "
           "trugen /presse/ und /studien/ je zwei H1 – und weil das Audit "
           "nur 20 von 107 Seiten sah, blieb die dritte "
           "(/studien/fixkosten-index-2026-q4/) im selben Build unsichtbar. "
           "Dahinter lag der eigentliche Schaden: Die Einzelansicht lag "
           "zweimal im Repo (_default/single.html und single.html) mit dem "
           "Vermerk, layouts/single.html gewinne die Template-Aufloesung. "
           "Ein Baustein-Marker im gebauten HTML bewies das Gegenteil – die "
           "Kopie war der tote Zweig, in dem jede kuenftige Heilung "
           "versandet waere (#623). "
           "STUFE 2 (08.10.2026, verifizieren & nachhaerten) schliesst drei "
           "Raender, die Stufe 1 nicht sah: (1) Die Quellpruefung kennt jetzt "
           "die ECHTE Markdown-Wahrheit – eingerueckte ATX-H1 (bis drei "
           "Leerzeichen), Setext-H1 (`Text` + `=====`) und rohes `<h1 …>` "
           "(`unsafe = true` in hugo.toml). (2) Die Ausnahmen der Wache decken "
           "KEINE Blaetterseiten mehr: `page/N/` galt pauschal als "
           "Blätter-Redirect ohne Inhalt, obwohl es seit "
           "`[pagination] disableAliases = true` keine solchen Redirects mehr "
           "gibt – die Startseiten-Blaetter /page/2/ … trugen real GAR KEINE "
           "H1, und die Ausnahme machte sie unsichtbar. Eine Ausnahme, die "
           "einen Befund deckt, ist ein Versteck. (3) S2 prueft nicht mehr "
           "vier Dateien, sondern ein fail-closed Inventar aller H1-Quellen "
           "(H1_QUELLEN) samt Seitenarten-Tabelle (SEITENARTEN), bindet den "
           "Startseiten-Blaetterkopf an seinen Marker und verlangt Paritaet "
           "der Einzelansichten mit eigener Vorlage (pillar/, werkzeuge/) bei "
           "`heading:`. Der Pull Request misst die gebaute Wahrheit jetzt "
           "ebenfalls (e2e.yml, direkt nach dem Hugo-Build).",
    "C1": "Die Sicht (Chefredakteur-Scorecard) läuft nach allen Messungen – sonst "
          "zeigt sie Werte des Vorlaufs als aktuellen Befund (#206).",
    "C2": "Der Hugo-Build darf keinen Fehler mit `|| true` verschlucken und meldet sein "
          "Ergebnis an das Gate – eine nicht ausgeführte Messung ist kein Grün.",
    "C3": "Jede Gate-Kennung wird aus einem Workflow befüllt – ein Schritt, den "
          "niemals jemand meldet, kann auch niemand reparieren.",
    "C4": "Issues entstehen aus der Gate-Entscheidung (`--decide`), Duplikate sind "
          "verboten (aktualisieren statt neu öffnen), und eine meldungsfreie Lage "
          "schließt das Issue.",
    "C5": "Secret-Nachweise tragen ihre Herkunft (`--proof-by`) und kommen aus dem "
          "Workflow, der das Secret benutzt; die Governance prüft live (`--verify`) "
          "statt sich selbst zu beglaubigen.",
    "C6": "Jede Wache hat einen `--selftest`, und alle bestehen – eine kaputte Wache "
          "liefert falsche Sicherheit.",
    "C7": "Manifest, Report und Scorecard zeigen dieselbe Ampel (oder die Scorecard "
          "kennzeichnet STALE/nicht gemessen ausdrücklich).",
    "C8": "`git add` im Workflow nennt nur versionierbare Pfade – ignorierte, "
          "unversionierte Dateien brechen den Lauf hart ab (#205).",
    "C9": "Reports und `data/*.json` enthalten kein Secret-Material (Pinterest/Groq/"
          "Gemini/GitHub/JWT-Muster).",
    "C10": "Alle Pinterest-Skripte holen ihren Token über den Broker "
           "`scripts/pinterest_token.py` – eine Reihenfolge, ein Failover, und die "
           "Wache prüft denselben Token, mit dem der Bot arbeitet (#206).",
    "C11": "Es gibt einen täglichen Erneuerungslauf (`pinterest-token.yml`), der den "
           "rotierten Refresh-Token sichert, sich selbst testet und sein Issue bei "
           "Heilung schließt – ein Handbetriebs-Secret stirbt sonst alle 30 Tage.",
    "C12": "Jeder Workflow, der Issues mit Label erzeugt, legt das Label vorher an – "
           "sonst scheitert die Meldung mit HTTP 422 und der Melder wird selbst zum "
           "Zwischenfall (#209).",
    "C13": "Ein Pinterest-Nachweis läuft immer mit Live-Probe (`--verify`), nur die "
           "Token-Wache rotiert den Refresh-Token proaktiv, und die Autorisierung "
           "fordert die echten v5-Scopes – sonst steht `unverified` im Cockpit, während "
           "niemand gemessen hat (#219).",
    "C14": "Jeder Alarm hat einen Besitzer (Maschine oder Mensch), einen Kanal und "
           "einen Schließpfad: menschliche Befunde öffnen kein Automations-Ticket und "
           "halten keins offen – sonst wird der Melder zum Dauerläufer (#272).",
    "C16": "Ein Lebenszeichen ist kein Befund: die Affiliate-Integritäts-Wache erneuert "
           "ihren Zeitstempel bei jedem Lauf (Beweis im Gate-Selbsttest), ihre Frische wird "
           "per Herzschlag ODER fehlerfreiem Lauf belegt, und der Lebenszeichen-Pfad ist "
           "deploy-irrelevant – ein ruhiger Tag darf weder einen Fehlalarm noch eine "
           "Veröffentlichung auslösen (#281).",
    "C15": "Beweisen ist nicht Heilen: wer den Site-Bestand bei jedem Aufruf umschreibt, "
           "muss einen trockenen Beweispfad haben, und ein Kettenleiter darf `--fix` im "
           "eigenen Selbsttest nicht weitergeben – ein Prüflauf, der nebenbei heilt, "
           "verändert die Messgröße, die er prüfen will (15.09.2026).",
    "C17": "Pinterest-Duplikate (P4) sind Spam: pin_title und pin_description müssen "
           "über alle Artikel hinweg einzigartig sein – der Duplicate-Guard heilt "
           "deterministisch, läuft in Watchdog und Content-Engine und verhindert "
           "Repeat-Pin-Spam (#305).",
    "C18": "Der Pflicht-Check heißt, wie der Branch-Schutz ihn verlangt: Der Anzeigename "
           "des PR-Gates (`Integritäts-Siegel`) ist als Konstante eingefroren und muss "
           "Workflow und Ruleset gleichermaßen entsprechen; das Gate läuft bei jedem PR "
           "auf `main` ohne Pfadfilter, ohne `if:` am Job, ohne `continue-on-error` und "
           "nur mit Leserechten, und die Live-Wache `pflichtcheck_guard.py` prüft im "
           "Gate selbst, ob der Branch-Schutz den Check wirklich verlangt – ein "
           "umbenannter Job friert `main` ein, ein Ruleset ohne Ziel-Branch schützt "
           "nichts (19.09.2026). Ist der Vertrag nachweislich nicht erfüllbar, legt "
           "`PFLICHT_CHECK_DAUERZUSTAND` ihn als befristeten Dauerzustand ab: Die Wache "
           "meldet genau diesen Befund als BEKANNT statt als Vorfall, jeder andere bleibt "
           "rot, und `--strict` zieht auch den bekannten Befund wieder auf Exit 1 "
           "(20.09.2026).",
    "C20": "Lesbarkeit ist ein Tor, kein Protokoll, und Auslieferungszeit ist keine "
           "Drift: Das Publish-Gate blockiert jeden neuen Artikel unter der "
           "importierten SSOT-Schwelle `readability_check.NEW_FLESCH_MIN`, die "
           "Schwellen AVG_TARGET/NEW_FLESCH_MIN/FLOOR_MIN dürfen nicht aufgeweicht "
           "werden, und die Live-Wache trennt über ein endliches, konfigurierbares "
           "Deploy-Fenster (`LIVE_POLICY_GRACE_MIN`) den frisch deployten Artikel "
           "(`deploy_hysterese`, INFO, nie ein Issue) von echter Drift (ROT) – sonst "
           "meldet eine Wache hinterher, was ein offenes Tor durchgelassen hat, und "
           "eine andere meldet wöchentlich die Physik (#585).",
    "C21": "Eine Maschine, die Sätze in fremde Texte schreibt, kennt die Wortart des "
           "eingesetzten Keywords nicht: Die Keyword-Heilung beugt das Keyword nie "
           "(`.lower()`/Deklination verboten), benutzt ausschließlich die geprüfte "
           "Satz-SSOT `dichte_saetze` mit Apposition nach Doppelpunkt, ist idempotent – "
           "und was trotzdem entsteht, fangen R17-KEYWORD-KASUS/-DOPPEL im "
           "Verständnis-Guard und im Publish-Gate ab. Die Lesbarkeitsnote sieht solche "
           "Ruinen nicht, sie misst Satzlängen, keine Grammatik (Nachtrag #585).",
    "C22": "Ein Schreiber ohne Tor ist ein Blocker-Produzent: Bevor die KI-Heilung "
           "einen Artikel ändert, prüft der Publikations-Vertrag die GEPLANTE Fassung "
           "gegen die Regeln, die über die Veröffentlichung entscheiden – V1 Flesch "
           "nicht unter die importierte SSOT-Schwelle `readability_check.NEW_FLESCH_MIN` "
           "bei gleichzeitiger Verschlechterung, V2 keine NEUEN harten "
           "Verständnis-Funde gegen die importierte Regelliste `publish_gate."
           "HARTE_REGELN` (Altlasten bleiben unangetastet), V3 nicht messbar = "
           "verworfen (fail-closed). Am 05.10.2026 hatte die KI-Heilung den Live-"
           "Artikel `2026-09-10-energie-update-…` auf Flesch 44,3 mit „In diesem "
           "Beitrag …“ umgeschrieben; ihre Struktur-Prüfung sah nichts, blockiert hat "
           "erst der nächste Deploy-Lauf – Exit 1, Produktionsalarm WF-54C4, "
           "abgebrochene Auslieferung (#607).",
    "C25": "Eine Deckung ohne Wirkung ist Papier: Fuer Regeln mit Zahlen-"
           "Versprechen (die Lesbarkeit ist das erste: Flesch >= "
           "`readability_check.NEW_FLESCH_MIN` als Publish-Kriterium, #585) "
           "verlangt die Deckungs-Wache der Reserve nicht nur einen Namen in "
           "`reserve_finisher.HEALER_CHAIN`, sondern eine GRUENE "
           "Wirkungsprobe des genannten Heilers – `--wirkungsprobe`, Exit 0, "
           "ohne Netz und ohne Kontingent. Am 07.10.2026 stand der Vorrat bei "
           "2/6, sieben Kandidaten allein an Flesch 53,1–59,9 geparkt, "
           "waehrend `profi_polish.py` die Regel formal deckte; der Tag "
           "endete 1/2 (Produktions-Wache P2, #609).",
    "C23": "Eine Quote ist ein Zustand, kein Arbeitsauftrag: Das Fach-Issue "
           "`engine-deficit` gehört seiner Messung (`scripts/engine_issue.py`) – "
           "Besitzer, tägliche Kadenz, Schließpfad. Gemessen wird der jüngste "
           "Publikationstag (`cadence_guard.letzter_publikationstag`, EINE "
           "Kalenderquelle für Defizit-Wache, Produktions-Wache und "
           "Auslieferungs-SLO) – auch an Ruhetagen, denn ein Ruhetag vergisst "
           "keinen offenen Zustand. Geschlossen wird nur durch die eigene "
           "Messung (Ziel erreicht), und der Vermerk sagt ausdrücklich, dass ein "
           "Fehltag NICHT nachgeholt wird (kein Nachtragen von Inhalten). Wer "
           "den Kanal rot schließt – Merge, Hand, Missverständnis –, findet ihn "
           "beim nächsten Lauf wieder offen. Am 05./06.10.2026 war #601 nach "
           "einem Reparatur-Merge zu, der Ruhetag wurde übersprungen, und das "
           "zentrale Fehler-Alerting musste fail-open das generische "
           "Wartungs-Issue #608 mit API-Key-Runbook anlegen (#608).",
    "C26": "Ein Beleg gehört seinem Tag: Die Auslieferungs-SLO schreibt einen "
           "tagesgenauen Beleg und eine versionierte Historie, und der Melder "
           "schließt nur mit einem Nachweis DESSELBEN Tages – ein vergangener "
           "Fehltag wird als Quittung verbucht („verbucht, nicht behoben“), nie "
           "beschönigt. Dazu die zweite Lehre derselben Nacht: Ein Rückläufer "
           "braucht einen LIVE-Beweis. Ein zurückgestufter Reserve-Artikel ohne "
           "Zwilling ist nicht ausgelieferter Nachschub – er kehrt in den Vorrat "
           "zurück, statt als „Kopie“ vernichtet zu werden, und die Endabnahme "
           "füllt konvergent nach, bis das Mindestziel steht oder das Material "
           "ehrlich erschöpft ist (#610).",
    "C29": "Ein Schreiber prüft, was über ihn entscheidet: Das Geburts-Gate "
           "der Content-Engine (`generate_drafts.profi_quality_ok`) misst die "
           "Lesbarkeit gegen die importierte SSOT "
           "`readability_check.NEW_FLESCH_MIN` – ein Text, den die "
           "Zertifizierung nachweislich ablehnt, darf gar nicht erst als "
           "Rohtext entstehen (Flesch >= 60 ist hartes Publish-Kriterium, "
           "#585). Der Retry hat ein Gedächtnis: `try_generate` gibt die "
           "Befunde des Vorversuchs als Korrektur-Auftrag an den Schreiber. "
           "Der Trend-Beweis gehört vor den Commit: Die Reserve-Chronik wird "
           "VOR dem Sicherungs-Commit geschrieben (`reserve_gate.py --chronik`, "
           "idempotent je Lauf) – bis zum 07.10.2026 verlor jeder rote Lauf "
           "genau die Zeile, die seine Nacht erklärt hätte. Und ein harter "
           "Blocker hat einen Heiler: R11/R13/R14 (Politur-Ruinen, #482) "
           "heilt `politur_ruine_heiler.py` beweisbar (Tor T1-T4) in Reserve- "
           "und Live-Kette; sonst blieb ein fertiger Kandidat an einem "
           "„SATZ: “-Rest hängen und der Vorrat fiel unter das Ziel "
           "(WF-D4E0, #612).",
    "C27": "Beweisen ist nicht Fabrizieren: `data/audit/*.jsonl` ist ein "
           "versioniertes, append-only bewachtes Beweis-Ledger (history_guard "
           "H6) – jede Zeile behauptet einen echten Betriebsvorgang. Ein "
           "Testlauf schreibt deshalb in einen Sandkasten: `audit_log` lenkt "
           "über FFC_AUDIT_DIR um und schaltet über FFC_AUDIT_DISABLE stumm, "
           "beides in der UMGEBUNG, weil die Wachen einander als Subprozesse "
           "aufrufen (publish_gate → affiliate_profi_check.py) und ein "
           "Monkeypatch im Testprozess das Kind nicht erreicht. Schwester von "
           "C15: Dort darf ein Beweislauf nicht heilen, was er prüft – hier "
           "darf er nicht behaupten, was nie geschah. Am 03.10.2026 stand ein "
           "gate-Entscheid für den Fixture-Artikel `2026-09-07-r5-live` im "
           "Buch: ein verworfener Live-Artikel, den es nie gab (Nebenbefund zu "
           "#610, 07.10.2026).",
    "C19": "Die Produktionswahrheit ist eine deklarierte, deckungsgleiche Sicht: "
           "data/release_scorecard.yaml erklärt jede harte Publish-Gate-Familie "
           "als blockierend (und jeden reinen Hinweis als Warnung), dokumentiert "
           "Eskalation, Falsch-Positiv-Protokoll, Freigabeprozess und Siegel – "
           "und scripts/release_scorecard.py misst ausschließlich über die "
           "Publish-Gate-Collectoren, als Beweislauf ohne Heilung, mit "
           "versiegeltem Versionsnachweis. Wer eine blockierende Prüfung zur "
           "Warnung herabstuft oder eine zweite Messregel einzieht, macht die "
           "Scorecard zur Lüge (Befund 10, 03.10.2026).",
    "C28": "Die Klasse geht dem Kanal vor: Der öffentliche Nachweis trägt eine "
           "Klasse (`ok` · `quelle_unter` · `quelle_ueber` · `auslieferung` · "
           "`unbekannt`) – der Bestand wird gegen das Tagesband geprüft, und "
           "`ok` steht zuerst, damit ein bestätigter Tag nie eine "
           "Defizitklasse trägt. Der Workflow antwortet der Klasse mit einem "
           "eigenen, ehrlichen roten Schritt; nur das Bestandsdefizit belegt "
           "den Fachkanal `engine-deficit` – mit Frischebeweis VOR dem roten "
           "Exit und mit beiden Kennwörtern im Schrittnamen, an denen das "
           "zentrale Fehler-Alerting seine Stummschaltung festmacht. "
           "Überschuss und Auslieferungsdefizit bleiben laut (Kadenz-Gate "
           "bzw. P1-Kanal), ein fehlender Beleg ist fail-closed laut. Am "
           "05./06.10.2026 fiel der Nachweis rot, weil die Quelle den "
           "gemessenen Montag nur mit 1/2 trug – der unbenannte Sammel-Schritt "
           "erzeugte das generische Wartungs-Issue #611 mit API-Key-Runbook, "
           "obwohl der Fachkanal existierte.",
    "C33": "Maschinen-Artefakte werden gegengelesen, bevor sie bewertet werden: "
           "data/**/*.json, *.jsonl, *.yaml und das Frontmatter aller Inhalte "
           "müssen parsebar, schlüsseleindeutig und frei von Konfliktmarkern "
           "sein – `artefakt_waechter.py` prüft das als Wache im vertraglichen "
           "Minimum, am PR-Pfad hart und im Reserve-Lauf NACH der Stufe, die "
           "das Zertifikat neu schreibt (erst heilen, dann urteilen). Wer das "
           "Zertifikat schreibt, schreibt es atomar und liest es gegen. Wer es "
           "liest, unterscheidet eine fehlgeschlagene Messung von einem leeren "
           "Vorrat: Am 08.10.2026 meldete der harte End-Gate sechs Nächte lang "
           "\u201e0/6 gate-fertig\u201c, weil ein Merge zwei Zertifikatsstände "
           "verschmolzen hatte – die Reparatur lief sechs Nächte in die falsche "
           "Richtung (WF-D4E0, #653).",
}

LABEL = {"C1": "Reihenfolge", "C2": "Bau-Grundlage", "C3": "Messkette",
         "C4": "Issue-Policy", "C5": "Nachweis-Provenienz", "C6": "Selbsttests",
         "C7": "Datenkonsistenz", "C8": "Commit-Hygiene", "C9": "Secret-Leak-Schutz",
         "C10": "Token-Broker", "C11": "Token-Lebenszyklus", "C12": "Label-Garantie",
         "C13": "Nachweis-Echtheit", "C14": "Alarm-Routing",
         "C15": "Beweis-Trockenlauf", "C16": "Wache-Herzschlag",
         "C17": "Pinterest-Duplikate", "C18": "Pflicht-Check",
         "C19": "Release-Scorecard",
         "C20": "Lesbarkeits-Tor & Deploy-Hysterese",
         "C21": "Maschinensätze",
         "C22": "Publikations-Vertrag der Schreib-Seite",
         "C23": "Zustandskanal (Besitz, Kadenz, Schließpfad)",
         "C25": "Deckung heißt Wirkung (Wirkungsprobe der Zahlen-Heiler)",
         "C26": "Ein Beleg gehört seinem Tag (Tages-Nachweis & Nachweis-Pflicht)",
         "C27": "Beweis-Ledger-Isolation (ein Testlauf fabriziert keine Beweise)",
         "C28": "Die Klasse geht dem Kanal vor (Melder-Routing der "
                "Auslieferungs-SLO)",
         "C29": "Der Schreiber prüft, was über ihn entscheidet (Geburts-Tor, "
                "Retry-Gedächtnis, Chronik-Reihenfolge, Ruinen-Heiler)",
         "C32": "Doppelte Mapping-Schluessel (Hugo-Abbruch, verdeckt fuer "
                "PyYAML) – erkennen vor dem Kurzschluss, heilen vor dem Build",
         "C30": "Eine Seite hat genau eine H1 (Quelle + Build, kein toter "
                "Zweig, Audit ohne Stichprobe)",
         # C31 ist der Robustheits-Vertrag (robustheits_gate.py) – die
         # nächste freie Nummer nach C32 ist deshalb C33.
         "C33": "Maschinen-Artefakte werden gegengelesen (kein Artefakt-"
                "Defekt sieht mehr aus wie ein leerer Vorrat)"}
                "Zweig, Audit ohne Stichprobe; Stufe 2: Markdown-Wahrheit, "
                "H1-Inventar, Blätterseiten geprüft)"}


def render_md(checks, ok_notes=()):
    lines = [
        "# 🔒 Governance-Vertrag (automatisch geprüft)",
        "",
        f"**Stand:** {datetime.date.today().isoformat()} · erzeugt von "
        "`scripts/governance_contract.py` · geprüft in `link-check.yml` (Qualitäts-Gate) "
        "und als Preflight in `premium-governance.yml`.",
        "",
        "Dieser Vertrag hält die Regeln fest, die den Dauer-Alarm aus "
        "Governance-Report #206 ermöglicht haben. Jede Verletzung ist ein Build-Fehler.",
        "",
        "## Regeln",
        "",
    ]
    # Natürliche Reihenfolge: C2 vor C10 (lexikografisch wäre C1, C10, C11, C2 …)
    for code, label in sorted(LABEL.items(), key=lambda kv: int(kv[0][1:])):
        lines.append(f"- **{code} {label}** – {RULE_TEXT.get(code, '')}")
    lines += ["", "## Befund", ""]
    if not checks:
        lines.append("🟢 Alle Verträge erfüllt.")
    else:
        lines += ["| Regel | Befund |", "|---|---|"]
        for code, msg in checks:
            lines.append(f"| {code} {LABEL.get(code, '')} | {msg} |")
    if ok_notes:
        lines += ["", "## Geprüfte Nachweise", ""]
        lines += [f"- {n}" for n in ok_notes]
    return "\n".join(lines) + "\n"


def _selftest():
    """Die Prüf-Regeln selbst mit Kunst-Workflows – sonst prüft man Ins Blaue."""
    failures = []
    good = """
      - name: Core-Web-Vitals-Wächter
        run: |
          hugo --minify > /tmp/build.log 2>&1
          python3 scripts/governance_gate.py --emit build --require-green
      - name: CWV
        run: python3 scripts/cwv_guard.py --public public/ --strict-build
      - name: emit
        run: python3 scripts/governance_gate.py --emit cwv --report CWV-REPORT.md
      - name: emit decay
        run: python3 scripts/governance_gate.py --emit decay --report DECAY-REPORT.md
      - name: emit secrets
        run: python3 scripts/secrets_age_guard.py --verify && python3 scripts/governance_gate.py --emit secrets
      - name: emit pinperf
        run: python3 scripts/governance_gate.py --emit pinperf --report PINTEREST-PERF-REPORT.md
      - name: emit clicks
        run: python3 scripts/governance_gate.py --emit clicks --report CLICK-REPORT.md
      - name: emit awin
        run: python3 scripts/governance_gate.py --emit awin --report AWIN-REPORT.md
      - name: Chefredakteur-Scorecard
        run: python3 scripts/editorial_scorecard.py
      - name: decide
        run: python3 scripts/governance_gate.py --decide
      - name: issue
        run: |
          gh issue list --state open --label governance
          gh issue create --label governance
      - name: close
        run: gh issue close 1
      - name: commit
        run: |
          git add data/governance_status.json
          git add CWV-REPORT.md
"""
    if c1_ordering(good):
        failures.append(f"guter Workflow wird von C1 verworfen: {c1_ordering(good)}")
    if c2_build_not_swallowed(good):
        failures.append(f"guter Workflow wird von C2 verworfen: {c2_build_not_swallowed(good)}")
    if c4_issue_policy(good):
        failures.append(f"guter Workflow wird von C4 verworfen: {c4_issue_policy(good)}")
    if c8_commit_hygiene(good, {"ops-report.json"}):
        failures.append("guter Workflow wird von C8 verworfen")
    # --- C1: #206-Fall (Scorecard zuerst) muss gefunden werden
    bad_order = """
      - name: Chefredakteur-Scorecard
        run: python3 scripts/editorial_scorecard.py
      - name: emit cwv
        run: python3 scripts/governance_gate.py --emit cwv
"""
    if not c1_ordering(bad_order):
        failures.append("C1: Scorecard vor den Messungen wird nicht erkannt (#206-Fall)")
    # --- C2: `|| true` muss gefunden werden
    bad_build = '- name: Hugo-Build\n        run: hugo --minify > /dev/null 2>&1 || true\n'
    if not c2_build_not_swallowed(bad_build):
        failures.append("C2: verschluckter Build-Fehler bleibt unentdeckt")
    # --- C4: Issue ohne decide/close
    bad_issue = "- name: issue\n        run: github.rest.issues.create({ title: 'x' })\n"
    if len(c4_issue_policy(bad_issue)) < 2:
        failures.append("C4: Issue-Erzeugung ohne Gate/Dedupe/Close bleibt unentdeckt")
    # --- C5: Selbst-Waschen + fehlende Provenienz
    bad_rec = {"premium-governance.yml":
               "python3 scripts/secrets_age_guard.py --record-success GROQ_API_KEY || true\n"}
    res = c5_record_provenance(bad_rec, 'SECRETS = {\n    "GROQ_API_KEY": {"days": 60},\n}')
    if not any("Selbst-Waschen" in m for _, m in res):
        failures.append("C5: Selbst-Waschen im Governance-Lauf wird nicht gemeldet")
    if not any("--proof-by" in m for _, m in res):
        failures.append("C5: Nachweis ohne --proof-by wird nicht gemeldet")
    res_unknown = c5_record_provenance({"social-ai.yml":
                                        "--record-success NOPE_TOKEN --proof-by social-ai\n"},
                                        'SECRETS = {\n    "GROQ_API_KEY": {"days": 60},\n}')
    if not any("nicht in" in m for _, m in res_unknown):
        failures.append("C5: unregistriertes Secret wird nicht gemeldet")
    # --- C7: zwei Wahrheiten
    man = {"verdict": "GREEN", "generated": "2026-09-07", "build_measured": True}
    if c7_data_consistency({"CWV-REPORT.md": "## 🤖 Gesamt-Ampel: **GREEN**\n**Stand:** 2026-09-07"},
                           man):
        failures.append("C7: konsistenter Stand wird beanstandet")
    res = c7_data_consistency({"CWV-REPORT.md": "## 🤖 Gesamt-Ampel: **AMBER**\n**Stand:** 2026-09-07"},
                             man)
    if not res:
        failures.append("C7: Report ≠ Manifest bleibt unentdeckt")
    res = c7_data_consistency({"CWV-REPORT.md": "## 🤖 Gesamt-Ampel: **GREEN**\n**Stand:** 2026-09-07",
                               "EDITORIAL-SCORECARD.md": "| Core-Web-Vitals | AMBER | 🟡 |"}, man)
    if not res:
        failures.append("C7: Scorecard mit erfundener CWV-Ampel (#206) bleibt unentdeckt")
    res = c7_data_consistency({"CWV-REPORT.md": "## 🤖 Gesamt-Ampel: **GREEN**\n**Stand:** 2026-09-07",
                               "EDITORIAL-SCORECARD.md": "| Core-Web-Vitals | STALE (12d) | ⚪ |"},
                              {"verdict": "GREEN", "generated": "2026-09-07",
                               "build_measured": False})
    if res:
        failures.append(f"C7: ehrliche STALE-Kennzeichnung wird bestraft: {res}")
    # --- C8: git add auf ignorierte Datei
    res = c8_commit_hygiene("          git add ops-report.json\n", {"ops-report.json"})
    if not res:
        failures.append("C8: git add auf ignorierte Datei (#205) bleibt unentdeckt")
    if c8_commit_hygiene("          git add CWV-REPORT.md\n", set()):
        failures.append("C8: versionierter Report wird beanstandet (Ignore gilt für "
                        "getrackte Dateien nicht)")
    if c8_commit_hygiene("          git add data/x.json 2>/dev/null || true\n", set()):
        failures.append("C8: Shell-Reste werden als Pfad fehlinterpretiert")
    # --- C9: Leak-Erkennung
    res = c9_leak_wache({"X.md": "token: gsk_" + "A" * 32})
    if not res:
        failures.append("C9: Klartext-Secret im Report wird nicht erkannt")
    if c9_leak_wache({"X.md": "Pinterest-Status: ok, keine Daten"}):
        failures.append("C9: Fehlalarm bei normalem Text")
    # --- C3: fehlender Emit-Zweig
    res = c3_measure_chain_complete("- name: x\n        run: echo",
                                   'STEPS = {\n    "decay":   {"report": "x"},\n    "cwv":     {"report": "y"},\n}')
    if len(res) != 2:
        failures.append(f"C3: fehlende Emit-Zweige nur {len(res)}x gemeldet (erwartet 2)")
    # --- C10: eigene Token-Reihenfolge im Skript (der #206-Kern)
    bad_scripts = {"pinterest_dings.py":
                   'tok = os.environ.get("PINTEREST_ACCESS_TOKEN", "")\n'
                   'urllib.request.urlopen("https://api.pinterest.com/v5/boards")\n'}
    if not any(code == "C10" for code, _ in c10_token_broker(bad_scripts)):
        failures.append("C10: eigenmächtige Token-Quelle im Skript bleibt unentdeckt")
    good_scripts = {"pinterest_dings.py":
                    "import pinterest_token\n"
                    "tok = pinterest_token.get_token()\n"
                    'urllib.request.urlopen("https://api.pinterest.com/v5/boards")\n'}
    if c10_token_broker(good_scripts):
        failures.append("C10: sauberes Skript über den Broker wird beanstandet")
    if c10_token_broker({"pinterest_token.py": 'os.environ["PINTEREST_ACCESS_TOKEN"]'}):
        failures.append("C10: der Broker selbst darf nicht gegen seine eigene Regel laufen")
    # --- C11: fehlender/halber Erneuerungslauf
    if not c11_token_lifecycle({}):
        failures.append("C11: fehlender Token-Erneuerungslauf bleibt unentdeckt")
    halb = {".github/workflows/pinterest-token.yml":
            "on:\n  workflow_dispatch: {}\nsteps:\n  - run: python3 scripts/pinterest_token.py --status\n"}
    res = c11_token_lifecycle(halb)
    if len(res) < 4:
        failures.append(f"C11: unvollständiger Erneuerungslauf nur {len(res)}x gemeldet")
    voll = {".github/workflows/pinterest-token.yml":
            "on:\n  schedule:\n    - cron: \"40 2 * * *\"\n"
            "steps:\n  - run: python3 scripts/pinterest_token.py --selftest\n"
            "  - run: python3 scripts/pinterest_token.py --refresh\n"
            "  - run: git add data/pinterest_tokens.enc\n"
            "  - run: gh issue close 1\n"}
    if c11_token_lifecycle(voll):
        failures.append(f"C11: vollständiger Erneuerungslauf wird beanstandet: {c11_token_lifecycle(voll)}")
    # --- C12: Issue-Label ohne Anlegen (Ursache #209)
    bad_label = {"x.yml": 'run: gh issue create --title "T" --label pinterest --body "b"\n'}
    if not any(code == "C12" for code, _ in c12_label_guarantee(bad_label)):
        failures.append("C12: Issue-Label ohne `gh label create` bleibt unentdeckt (#209)")
    good_label = {"x.yml": 'run: |\n  gh label create pinterest --force\n'
                           '  gh issue create --title "T" --label pinterest --body "b"\n'}
    if c12_label_guarantee(good_label):
        failures.append("C12: abgesicherter Melder wird beanstandet")
    var_label = {"x.yml": 'env:\n  L: gov\nrun: |\n  gh label create "$L" --force\n'
                          '  gh issue create --label "$L" --body b\n'}
    if c12_label_guarantee(var_label):
        failures.append("C12: Label über Variable wird fälschlich beanstandet")
    js_label = {"x.yml": "issues.createLabel({name:'auto-report'})\n"
                         "issues.create({labels: ['auto-report']})\n"}
    if c12_label_guarantee(js_label):
        failures.append("C12: github-script mit createLabel wird beanstandet")
    kommentar = {"x.yml": "# Beispiel: gh issue create --label demo\njobs: {}\n"}
    if c12_label_guarantee(kommentar):
        failures.append("C12: Beispiel im Kommentar wird als echter Melder gezählt")
    # --- C13: Nachweis ohne Live-Probe (Ursache #219)
    no_probe = {".github/workflows/x.yml":
                "run: |\n  python3 scripts/secrets_age_guard.py --verify-only PINTEREST_ACCESS_TOKEN --quiet\n"}
    if not any(code == "C13" for code, _ in c13_proof_integrity(no_probe)):
        failures.append("C13: `--verify-only` ohne `--verify` bleibt unentdeckt (#219)")
    with_probe = {".github/workflows/x.yml":
                  "run: |\n  python3 scripts/secrets_age_guard.py --verify --verify-only PINTEREST_ACCESS_TOKEN \\\n    --quiet\n"}
    if c13_proof_integrity(with_probe):
        failures.append(f"C13: echter Nachweis wird beanstandet: {c13_proof_integrity(with_probe)}")
    fake_wache = {".github/workflows/pinterest-ai.yml": "env:\n  PINTEREST_TOKEN_WACHE: \"1\"\n"}
    if not c13_proof_integrity(fake_wache):
        failures.append("C13: zweiter Rotierer bleibt unentdeckt")
    no_flag = {f".github/workflows/{TOKEN_WORKFLOW}": "env:\n  X: y\n"}
    if not c13_proof_integrity(no_flag):
        failures.append("C13: Token-Wache ohne Wache-Flag bleibt unentdeckt")
    good_flag = {f".github/workflows/{TOKEN_WORKFLOW}": "env:\n  PINTEREST_TOKEN_WACHE: \"1\"\n"}
    if c13_proof_integrity(good_flag):
        failures.append("C13: korrekt markierte Token-Wache wird beanstandet")
    bad_scope = 'DEFAULT_SCOPES = "boards:read,pins:write,read_ads"\n'
    if not any("read_ads" in msg or "user_accounts" in msg
               for _, msg in c13_proof_integrity({}, auth_text=bad_scope)):
        failures.append("C13: ungültiger Scope `read_ads` / fehlender Profil-Scope bleibt unentdeckt")
    good_scope = 'DEFAULT_SCOPES = "boards:read,boards:write,pins:read,pins:write,user_accounts:read"\n'
    if c13_proof_integrity({}, auth_text=good_scope):
        failures.append("C13: korrekte v5-Scopes werden beanstandet")
    # --- C14: Alarm ohne Besitzer/Schließpfad (Ursache #272)
    bad_wf = {".github/workflows/bot-watchdog.yml":
              "run: |\n  gh issue create --label bot-watchdog --title \"Alarm\" --body \"x\"\n"}
    if not any(code == "C14" for code, _ in c14_alarm_routing(bad_wf, {})):
        failures.append("C14: Melde-Logik im YAML statt im Router bleibt unentdeckt (#272)")
    good_wf = {".github/workflows/bot-watchdog.yml":
               "run: |\n  python3 scripts/bot_watchdog.py --route\n"}
    router_src = _read(os.path.join(BLOG_DIR, "scripts", "alert_router.py"))
    watchdog_src = _read(os.path.join(BLOG_DIR, "scripts", "bot_watchdog.py"))
    if not router_src or not watchdog_src:
        failures.append("C14: Router oder Watchdog nicht lesbar – Vertrag nicht prüfbar")
    else:
        res = c14_alarm_routing(good_wf, {"alert_router.py": router_src,
                                          "bot_watchdog.py": watchdog_src})
        if res:
            failures.append(f"C14: sauberes Routing wird beanstandet: {res}")
    if not c14_alarm_routing({}, {}):
        failures.append("C14: fehlender Router (kein Besitz, kein Schließpfad) bleibt unentdeckt (#272)")

    # --- LABEL/Regeltext-Deckung: jede Regel ist erklärt (Doku gehört zum Vertrag)
    for code in LABEL:
        if code not in RULE_TEXT or len(RULE_TEXT[code]) < 40:
            failures.append(f"{code} ohne richtigen Regeltext")
    if "C1" not in LABEL or "C13" not in LABEL or "C18" not in LABEL:
        failures.append("Regel-Codes nicht vollständig gelabelt")
    if set(RULE_TEXT) != set(LABEL):
        failures.append(f"Regeltext und Label decken sich nicht: {sorted(set(RULE_TEXT) ^ set(LABEL))}")
    # C15: Beweisen ist nicht Heilen (Kunst-Skripte, der reale Bestand bleibt unbeteiligt)
    nacktt = 'import sys\nfor a in sys.argv:\n    pass\nopen("x", "w").write("1")\n'
    fund = c15_proof_not_healing({"fix_spaces.py": nacktt},
                                 {"a.yml": "run: python3 scripts/fix_spaces.py\n"})
    if not [f for f in fund if "keinen `--selftest`" in f[1]]:
        failures.append("C15 findet einen Nacktheiler ohne Beweispfad nicht.")
    fund = c15_proof_not_healing({"fix_spaces.py": nacktt},
                                 {"a.yml": "run: python3 scripts/fix_spaces.py --fix\n"})
    if [f for f in fund if "Kontrollauftrag" in f[1]]:
        failures.append("C15 meldet einen Heilauftrag als Kontrollauftrag.")
    sicher = (nacktt + 'if "--selftest" in sys.argv:\n    raise SystemExit\n'
              'def trocken(argv):\n    return True\n')
    if c15_proof_not_healing({"fix_spaces.py": sicher},
                             {"a.yml": "run: python3 scripts/fix_spaces.py\n"}):
        failures.append("C15 meldet einen ausgewiesenen Trockenlauf als Fehler.")
    leiter = 'import sys\nDO_FIX = "--fix" in sys.argv\nkinder_args("x")\n'
    if not [f for f in c15_proof_not_healing({"blog_doctor.py": leiter}, {}) if "weiter" in f[1]]:
        failures.append("C15 laesst einen Kettenleiter durch, der --fix im Selbsttest weitergibt.")
    # --- C16: Wache-Herzschlag (Lebenszeichen ≠ Befund, Ursache #281)
    guter_watchdog = ('def workflow_run_evidence(wf, hours=30):\n'
                      '    return 0, 0, 0, ""\n'
                      'AFFILIATE_STATE_ESCALATE_HOURS = 54\n')
    gute_liste = ("STATE_ONLY='^(docs/.*|\\.affiliate_integrity_state\\.json|"
                  "[A-Za-z0-9._-]+\\.md)$'\n")
    if c16_heartbeat(gute_liste, {"bot_watchdog.py": guter_watchdog}):
        failures.append("C16: sauberer Herzschlag-Aufbau wird beanstandet: "
                        f"{c16_heartbeat(gute_liste, {'bot_watchdog.py': guter_watchdog})}")
    # (a) Frische ohne Lauf-Evidenz / ohne Eskalationsgrenze
    ohne_evidenz = "AFFILIATE_STATE_ESCALATE_HOURS = 54\n"
    if not [f for f in c16_heartbeat(gute_liste, {"bot_watchdog.py": ohne_evidenz})
            if "Lauf-Evidenz" in f[1]]:
        failures.append("C16: fehlende Lauf-Evidenz im Watchdog bleibt unentdeckt (#281).")
    ohne_grenze = "def workflow_run_evidence(wf, hours=30):\n    return 0\n"
    if not [f for f in c16_heartbeat(gute_liste, {"bot_watchdog.py": ohne_grenze})
            if "Eskalationsgrenze" in f[1]]:
        failures.append("C16: fehlende Eskalationsgrenze bleibt unentdeckt.")
    # (b) Lebenszeichen würde deployen / Site-Pfad würde übersprungen
    if not [f for f in c16_heartbeat("STATE_ONLY='^(docs/.*)$'\n",
                                     {"bot_watchdog.py": guter_watchdog})
            if "Lebenszeichen" in f[1]]:
        failures.append("C16: Lebenszeichen-Pfad außerhalb der Negativliste bleibt unentdeckt.")
    site_uebersprungen = ("STATE_ONLY='^(content/.*|docs/.*|\\.affiliate_integrity_state"
                          "\\.json)$'\n")
    if not [f for f in c16_heartbeat(site_uebersprungen, {"bot_watchdog.py": guter_watchdog})
            if "Site-Pfad" in f[1]]:
        failures.append("C16: Site-Pfad in der Negativliste bleibt unentdeckt.")
    if not [f for f in c16_heartbeat("jobs: {}\n", {"bot_watchdog.py": guter_watchdog})
            if "Negativliste" in f[1]]:
        failures.append("C16: fehlende Negativliste bleibt unentdeckt.")
    if not c16_heartbeat(gute_liste, {}):
        failures.append("C16: fehlender Watchdog bleibt unentdeckt.")
    if "affiliate_integrity_gate.py" not in GUARDS:
        failures.append("C16: Gate-Selbsttest läuft nicht in der Governance (GUARDS).")
    # --- C18: Pflicht-Check-Vertrag (Kunst-Workflows; der echte steht in den Unittests)
    wf_pfad = f".github/workflows/{PFLICHT_CHECK_WORKFLOW}"
    gutes_gate = (
        "name: Integritäts-Lock (PR-Gate)\n\non:\n  pull_request:\n    branches: [main]\n"
        "  workflow_dispatch: {}\n\npermissions:\n  contents: read\n\njobs:\n  lock:\n"
        f"    name: {PFLICHT_CHECK_NAME}\n    runs-on: ubuntu-latest\n    steps:\n"
        "      - uses: actions/checkout@v4\n"
        "      - name: Siegel prüfen\n        run: python3 scripts/integrity_guard.py --gate\n"
        "      - name: Branch-Schutz prüfen\n"
        f"        run: python3 scripts/{PFLICHT_CHECK_WACHE}\n")
    if c18_pflicht_check({wf_pfad: gutes_gate}):
        failures.append(f"C18: sauberes Gate wird beanstandet: {c18_pflicht_check({wf_pfad: gutes_gate})}")
    if pflichtcheck_name_aus_workflow(gutes_gate) != PFLICHT_CHECK_NAME:
        failures.append("C18: Anzeigename wird nicht aus der Workflow-Datei gelesen.")
    if not c18_pflicht_check({}):
        failures.append("C18: fehlender Gate-Workflow bleibt unentdeckt.")
    # (a) der Ausgangsbefund: Job ohne Anzeigename meldet sich als Job-ID „lock"
    ohne_namen = gutes_gate.replace(f"    name: {PFLICHT_CHECK_NAME}\n", "")
    fund = c18_pflicht_check({wf_pfad: ohne_namen})
    if not [f for f in fund if "`lock`" in f[1] and PFLICHT_CHECK_NAME in f[1]]:
        failures.append("C18: Job ohne Anzeigename (meldet sich als `lock`) bleibt unentdeckt.")
    if pflichtcheck_name_aus_workflow(ohne_namen) != "lock":
        failures.append("C18: ohne Anzeigename muss die Job-ID als Check-Name gelten.")
    # (b) Umbenennung ohne Vertrag
    umbenannt = gutes_gate.replace(PFLICHT_CHECK_NAME, "Siegel-Check")
    if not [f for f in c18_pflicht_check({wf_pfad: umbenannt}) if "Siegel-Check" in f[1]]:
        failures.append("C18: umbenannter Pflicht-Check bleibt unentdeckt (main würde einfrieren).")
    # (c) Pfadfilter – der Workflow startet nicht, GitHub wartet ewig
    mit_pfaden = gutes_gate.replace("    branches: [main]\n",
                                    "    branches: [main]\n    paths:\n      - 'scripts/**'\n")
    if not [f for f in c18_pflicht_check({wf_pfad: mit_pfaden}) if "paths" in f[1]]:
        failures.append("C18: paths-Filter am Pflicht-Check bleibt unentdeckt.")
    # (d) falscher Zweig / kein PR-Trigger
    anderer_zweig = gutes_gate.replace("branches: [main]", "branches: [release]")
    if not [f for f in c18_pflicht_check({wf_pfad: anderer_zweig}) if "`main`" in f[1]]:
        failures.append("C18: PR-Trigger ohne main bleibt unentdeckt.")
    nur_push = gutes_gate.replace("  pull_request:\n    branches: [main]\n",
                                  "  push:\n    branches: [main]\n")
    if not [f for f in c18_pflicht_check({wf_pfad: nur_push}) if "pull_request" in f[1]]:
        failures.append("C18: fehlender pull_request-Trigger bleibt unentdeckt.")
    # (e) Scheingrün: if am Job, continue-on-error am Gate-Schritt, Gate-Schritt fehlt
    mit_if = gutes_gate.replace("    runs-on: ubuntu-latest\n",
                                "    if: github.actor != 'dependabot[bot]'\n    runs-on: ubuntu-latest\n")
    if not [f for f in c18_pflicht_check({wf_pfad: mit_if}) if "`if:`" in f[1]]:
        failures.append("C18: if-Bedingung am Pflicht-Check bleibt unentdeckt (Scheingrün).")
    verschluckt = gutes_gate.replace("      - name: Siegel prüfen\n",
                                     "      - name: Siegel prüfen\n        continue-on-error: true\n")
    if not [f for f in c18_pflicht_check({wf_pfad: verschluckt}) if "continue-on-error" in f[1]]:
        failures.append("C18: continue-on-error am Gate-Schritt bleibt unentdeckt.")
    ohne_gate = gutes_gate.replace("python3 scripts/integrity_guard.py --gate",
                                   "python3 scripts/integrity_guard.py --selftest")
    if not [f for f in c18_pflicht_check({wf_pfad: ohne_gate}) if "--gate" in f[1]]:
        failures.append("C18: Pflicht-Check ohne Gate-Aufruf bleibt unentdeckt.")
    # (f) Schreibrechte, fehlende Live-Wache
    schreibend = gutes_gate.replace("  contents: read\n", "  contents: write\n")
    if not [f for f in c18_pflicht_check({wf_pfad: schreibend}) if "Schreibrechte" in f[1]]:
        failures.append("C18: Schreibrechte am Gate bleiben unentdeckt.")
    ohne_wache = gutes_gate.replace(f"      - name: Branch-Schutz prüfen\n"
                                    f"        run: python3 scripts/{PFLICHT_CHECK_WACHE}\n", "")
    if not [f for f in c18_pflicht_check({wf_pfad: ohne_wache}) if PFLICHT_CHECK_WACHE in f[1]]:
        failures.append("C18: Gate ohne Live-Wache des Branch-Schutzes bleibt unentdeckt.")
    # Kommentare mit niedrigerer Einrückung dürfen einen Job-Block nicht beenden
    kommentiert = gutes_gate.replace("    runs-on: ubuntu-latest\n",
                                     "# Kommentar am linken Rand\n    runs-on: ubuntu-latest\n")
    if c18_pflicht_check({wf_pfad: kommentiert}):
        failures.append("C18: Kommentar am linken Rand zerreißt den Job-Block.")
    if PFLICHT_CHECK_WACHE not in GUARDS:
        failures.append("C18: Live-Wache steht nicht im vertraglichen Minimum (GUARDS).")
    # --- C18-Zusatz: dokumentierter Dauerzustand (20.09.2026, Option B) -----------
    def _dauer(**anderungen):
        z = dict(PFLICHT_CHECK_DAUERZUSTAND)
        z.update(anderungen)
        return z
    wache_ok = ('if "PFLICHT_CHECK_DAUERZUSTAND" not in zustand: pass\n'
                'ap.add_argument("--strict", action="store_true")\n')
    runbook_ok = "## " + str(PFLICHT_CHECK_DAUERZUSTAND.get("runbook_abschnitt")) + "\nText\n"
    if c18_dauerzustand(None, wache_ok, runbook_ok):
        failures.append("C18: fehlende Dauerzustand-Erklärung wird beanstandet "
                        "(ohne Erklärung muss die Wache hart rot melden – das ist kein Befund).")
    if c18_dauerzustand(_dauer(), wache_ok, runbook_ok):
        failures.append(f"C18: die hinterlegte Dauerzustand-Erklärung ist unvollständig oder "
                        f"unerklärt: {c18_dauerzustand(_dauer(), wache_ok, runbook_ok)}")
    for feld, erwartung in (("check", "Siegel-Anders"), ("branch", "develop"),
                            ("urteil_erwartet", "NICHT_PRUEFBAR"),
                            ("pruefung_bis", "31.12.2026"),
                            ("festgestellt", "2026-13-45")):
        fund = c18_dauerzustand(_dauer(**{feld: erwartung}), wache_ok, runbook_ok)
        if not fund:
            failures.append(f"C18: Dauerzustand mit `{feld}: {erwartung!r}` bleibt unbeanstandet "
                            f"(Erklärung würde ins Leere greifen).")
    if not [f for f in c18_dauerzustand(_dauer(pruefung_bis="2026-06-30"), wache_ok, runbook_ok)
            if "≤" in f[1]]:
        failures.append("C18: Frist vor dem Feststellungsdatum bleibt unbeanstandet.")
    if c18_dauerzustand(_dauer(pruefung_bis="2026-09-21"), wache_ok, runbook_ok):
        failures.append("C18: eine abgelaufene Frist ist im Vertrag KEIN Befund – die Uhr-Probe "
                        "(C6) würde den Selbsttest sonst je nach Kalendertag kippen.")
    if c18_dauerzustand(_dauer(), "", ""):
        failures.append("C18: unbrauchbare Wachen-/Runbook-Texte erfinden Befunde "
                        "(fehlende Einsicht ist keine Verletzung – C15-Maß).")
    if not c18_dauerzustand(_dauer(belege={"x": "war schon immer so"}), wache_ok, runbook_ok):
        failures.append("C18: Dauerzustand ohne brauchbare Belege bleibt unbeanstandet.")
    if not c18_dauerzustand(_dauer(belege={"x": "Regeln vor Ort geprüft, alle Rulesets lesen"
                                                  " nichts verlangt"}), wache_ok, runbook_ok):
        failures.append("C18: Belege ohne Issue-/PR-Nummer bleiben unbeanstandet "
                        "(Nachprüfbarkeit in sechs Monaten wäre erfunden).")
    if not c18_dauerzustand(_dauer(), 'ap.add_argument("--strict", action="store_true")\n',
                            runbook_ok):
        failures.append("C18: Dauerzustand-Erklärung ohne Verdrahtung in der Wache bleibt "
                        "unbeanstandet (totes Konfigurationsstück).")
    if not c18_dauerzustand(_dauer(), 'PFLICHT_CHECK_DAUERZUSTAND\n', runbook_ok):
        failures.append("C18: Dauerzustand ohne `--strict`-Ausweg bleibt unbeanstandet "
                        "(das wäre Scheingrün auf Dauer).")
    if not c18_dauerzustand(_dauer(), wache_ok, "anderer Text"):
        failures.append("C18: Runbook-Abschnitt der Dauerzustand-Erklärung fehlt, meldet nicht.")
    # --- C19: Release-Scorecard – die SSOT der Produktionswahrheit ---------------
    echtes_script = {RELEASE_ENGINE: _read(os.path.join(BLOG_DIR, "scripts", RELEASE_ENGINE))}
    if c19_release_ssot(echtes_script):
        failures.append(f"C19: der echte Zustand wird beanstandet: "
                        f"{c19_release_ssot(echtes_script)}")
    if not c19_release_ssot({}):
        failures.append("C19: fehlende Engine bleibt unentdeckt.")
    # --- C22: Publikations-Vertrag der Schreib-Seite (WF-54C4/#607, 07.10.2026)
    echte = {name: _read(os.path.join(BLOG_DIR, "scripts", name))
             for name in ("publikations_vertrag.py", "redaktions_standard.py",
                          "publish_gate.py")}
    if c22_publikations_vertrag(echte):
        failures.append(f"C22: der echte Zustand wird beanstandet: "
                        f"{c22_publikations_vertrag(echte)}")
    # (a) Schreiber ohne Vertrag: genau die Lücke, die #607 möglich machte.
    ohne_import = dict(echte, **{"redaktions_standard.py":
                                 echte["redaktions_standard.py"].replace(
                                     "from publikations_vertrag import", "import xyz")})
    if not [f for f in c22_publikations_vertrag(ohne_import) if "importiert" in f[1]]:
        failures.append("C22: loser Schreiber ohne Vertrags-Import bleibt unentdeckt (#607).")
    # (b) Aufruf entfernt / Bypass: `_vertrag_gruende` wird nicht mehr aufgerufen.
    ohne_aufruf = dict(echte, **{"redaktions_standard.py":
                                 echte["redaktions_standard.py"].replace(
                                     "vertrag = _vertrag_gruende(a, neu)",
                                     "vertrag = []  # Vertrag umgangen")})
    if not [f for f in c22_publikations_vertrag(ohne_aufruf) if "_vertrag_gruende" in f[1]]:
        failures.append("C22: umgangener Vertragsaufruf bleibt unentdeckt.")
    # (c) Schwelle kopiert statt importiert (zweiter Maßstab, Lehre #585).
    kopiert = dict(echte, **{"publikations_vertrag.py":
                             "NEW_FLESCH_MIN = 60.0\n" + echte["publikations_vertrag.py"]})
    if not [f for f in c22_publikations_vertrag(kopiert) if "SSOT" in f[1]]:
        failures.append("C22: kopierte Flesch-Schwelle bleibt unentdeckt (zweite Wahrheit).")
    # (d) Schreiber und Gate kennen verschiedene harte Regeln.
    eigene_regeln = dict(echte, **{"publikations_vertrag.py":
                                   echte["publikations_vertrag.py"].replace(
                                       "publish_gate.HARTE_REGELN", "EIGENE_REGELN")})
    if not [f for f in c22_publikations_vertrag(eigene_regeln) if "HARTE_REGELN" in f[1]]:
        failures.append("C22: eigene Regelliste statt Gate-SSOT bleibt unentdeckt (#607).")
    # (e) Vorfall-Material fehlt: Ohne den echten Text prüft der Vertrag gegen
    #     Nachbauten – dann verschwindet der Beweis mit dem nächsten Refactoring.
    if not [f for f in c22_publikations_vertrag(echte, root=os.path.join(BLOG_DIR, "nix"))
            if "wf54c4" in f[1]]:
        failures.append("C22: fehlende Vorfall-Fixtures bleiben unentdeckt.")
    blind = {RELEASE_ENGINE: "print('hallo')"}
    if not [f for f in c19_release_ssot(blind) if "Collector" in f[1] or "DRY_RUN" in f[1]]:
        failures.append("C19: eine Engine ohne Publish-Gate-Collectoren und ohne "
                        "Beweislauf-Erzwingung bleibt unentdeckt (zweite Messregel).")
    # --- C23: Zustandskanal (WF-1F8C #608, 07.10.2026) --------------------------
    # Der Kanal gehört seiner Messung: tägliche Kadenz, eine Kalenderquelle,
    # Schließpfad nur durch Messung, Wiederöffnen nach rotem Schließen.
    echte_waechter = {name: _read(os.path.join(BLOG_DIR, "scripts", name))
                      for name in ("engine_issue.py", "cadence_guard.py",
                                   "publication_check.py")}
    wflows_echt = {}
    for pfad in sorted(glob.glob(os.path.join(BLOG_DIR, ".github", "workflows", "*.yml"))):
        wflows_echt[pfad] = _read(pfad)
    if c23_zustandskanal(echte_waechter, wflows_echt):
        failures.append(f"C23: der echte Zustand wird beanstandet: "
                        f"{c23_zustandskanal(echte_waechter, wflows_echt)}")
    # (a) Ruhetag-Sprung zurückgebaut: genau die Lücke, die #608 möglich machte.
    mit_sprung = dict(echte_waechter, **{
        "engine_issue.py": echte_waechter["engine_issue.py"].replace(
            "    heute = dt.datetime.now(dt.timezone.utc).date()",
            "    heute = dt.datetime.now(dt.timezone.utc).date()\n"
            "    if heute.weekday() not in cg.PUBLICATION_DAYS:\n"
            "        print(\"Kein Publikationstag – Defizit-Wache übersprungen.\")\n"
            "        return 0")})
    if not [f for f in c23_zustandskanal(mit_sprung, wflows_echt)
            if "Ruhetage" in f[1]]:
        failures.append("C23: ein wieder eingebauter Ruhetag-Sprung bleibt unentdeckt (#608).")
    # (b) Zweiter Kalender: der Melder bestimmt seinen Tag selbst.
    eigene_uhr = dict(echte_waechter, **{
        "engine_issue.py": echte_waechter["engine_issue.py"].replace(
            "cg.letzter_publikationstag(heute)", "heute")})
    if not [f for f in c23_zustandskanal(eigene_uhr, wflows_echt)
            if "Kalender" in f[1] or "letzter_publikationstag" in f[1]]:
        failures.append("C23: ein zweiter Kalender im Melder bleibt unentdeckt (#608).")
    # (c) Wiederöffnen entfernt: ein Merge könnte den Zustand dann endgültig schließen.
    ohne_reopen = dict(echte_waechter, **{
        "engine_issue.py": echte_waechter["engine_issue.py"].replace(
            "wieder_oeffnen", "ignorieren")})
    if not [f for f in c23_zustandskanal(ohne_reopen, wflows_echt)
            if "wieder" in f[1].lower() or "Wieder" in f[1]]:
        failures.append("C23: ein fehlender Wiederöffnen-Pfad bleibt unentdeckt (#608).")
    # (d) Der tägliche Beleg verschwindet aus der Produktions-Wache.
    ohne_beleg = dict(wflows_echt, **{
        os.path.join(BLOG_DIR, ".github", "workflows", "produktions-wache.yml"):
            wflows_echt[os.path.join(BLOG_DIR, ".github", "workflows",
                                     "produktions-wache.yml")].replace(
                "engine_issue.py --deficit", "# Beleg entfernt")})
    if not [f for f in c23_zustandskanal(echte_waechter, ohne_beleg)
            if "Ruhetagen" in f[1]]:
        failures.append("C23: ein fehlender Tagesbeleg bleibt unentdeckt – an "
                        "Ruhetagen entstünde wieder #608.")
    # (e) Identität (Marker/Label) verändert: die Dedupe des Alertings erblindet.
    fremder_marker = dict(echte_waechter, **{
        "engine_issue.py": echte_waechter["engine_issue.py"].replace(
            "<!-- engine-deficit-id: tagesdefizit -->", "<!-- irgendwas -->")})
    if not [f for f in c23_zustandskanal(fremder_marker, wflows_echt)
            if "Marker" in f[1]]:
        failures.append("C23: ein veränderter Fachkanal-Marker bleibt unentdeckt "
                        "(die Stummschaltung aus #602 würde blind).")
    # (f) Kalender-SSOT in cadence_guard entfernt: alle Melder müssten raten.
    ohne_ssot = dict(echte_waechter, **{
        "cadence_guard.py": echte_waechter["cadence_guard.py"].replace(
            "def letzter_publikationstag(", "def _entfernt(")})
    if not [f for f in c23_zustandskanal(ohne_ssot, wflows_echt)
            if "letzter_publikationstag" in f[1]]:
        failures.append("C23: eine entfernte Kalender-SSOT bleibt unentdeckt.")
    # --- C25: Deckung heißt Wirkung (WACHE-609, 07.10.2026) ---------------
    # Von hier an prüft der SELFTEST die Regel mit Kunstbefunden: erst der
    # echte Baum (muss still bleiben), dann drei Sabotagen, die je genau
    # einen Zweig von c25_deckung_wirkung treffen müssen.
    echte_wirkung = {name: _read(os.path.join(BLOG_DIR, "scripts", name))
                     for name in ("reserve_healer_coverage.py",
                                  "reserve_finisher.py", "lesbarkeit_heiler.py")}
    if c25_deckung_wirkung(echte_wirkung):
        failures.append(f"C25: der echte Zustand wird beanstandet: "
                        f"{c25_deckung_wirkung(echte_wirkung)}")
    # (a) Wirkungsproben aus der Deckungs-Wache entfernt: die Deckung wäre
    #     wieder ein Name ohne Nachweis – genau der Zustand vor #609.
    ohne_proben = dict(echte_wirkung, **{
        "reserve_healer_coverage.py":
            echte_wirkung["reserve_healer_coverage.py"].replace(
                "WIRKUNGS_PROBEN", "WIRKUNGSTABELLE").replace(
                "def wirkungsdeckung(", "def _wirkungsdeckung_entfernt(")})
    if not [f for f in c25_deckung_wirkung(ohne_proben)
            if "Wirkungsproben" in f[1] or "Wirkungs" in f[1]]:
        failures.append("C25: entfernte Wirkungsproben bleiben unentdeckt (#609).")
    # (b) Schwelle kopiert statt importiert: zweite Wahrheit im Heiler (#585).
    kopiert = dict(echte_wirkung, **{
        "lesbarkeit_heiler.py": "NEW_FLESCH_MIN = 60.0\n"
                                + echte_wirkung["lesbarkeit_heiler.py"]})
    if not [f for f in c25_deckung_wirkung(kopiert) if "Wahrheit" in f[1]]:
        failures.append("C25: kopierte Flesch-Schwelle im Heiler bleibt "
                        "unentdeckt (#585).")
    # (c) Heiler aus der Reserve-Kette entfernt: das Tor wäre unerreichbar.
    ohne_kette = dict(echte_wirkung, **{
        "reserve_finisher.py": echte_wirkung["reserve_finisher.py"].replace(
            '("lesbarkeit_heiler.py"', '("x_lesbarkeit_heiler.py"')})
    if not [f for f in c25_deckung_wirkung(ohne_kette) if "HEALER_CHAIN" in f[1]]:
        failures.append("C25: ein aus der Kette entfernter Wirkungs-Heiler "
                        "bleibt unentdeckt (#609).")
    # --- C26: Ein Beleg gehört seinem Tag (WF-54C4 #610, 07.10.2026) ------
    echte_tagesakte = {name: _read(os.path.join(BLOG_DIR, "scripts", name))
                       for name in ("publication_incident.py",
                                    "publication_check.py",
                                    "publication_release.py", "reserve_pool.py",
                                    "reserve_custody.py", "reserve_janitor.py")}
    if c26_beleg_je_tag(echte_tagesakte, wflows_echt):
        failures.append(f"C26: der echte Zustand wird beanstandet: "
                        f"{c26_beleg_je_tag(echte_tagesakte, wflows_echt)}")
    # (a) Der Schließpfad wird wieder tagesblind (genau der Zustand vor #610).
    tagesblind = dict(echte_tagesakte, **{
        "publication_incident.py": echte_tagesakte["publication_incident.py"]
        .replace("if urteil in ('schliessen', 'quittung'):",
                 "if True:  # Tagesbindung umgangen")})
    if not [f for f in c26_beleg_je_tag(tagesblind, wflows_echt)
            if "Tages-Entscheidung" in f[1]]:
        failures.append("C26: ein tagesblinder Schließpfad bleibt unentdeckt "
                        "(#610).")
    # (b) Der tagesgenaue Beleg verschwindet – der generische überschreibt.
    ohne_tag = dict(echte_tagesakte, **{
        "publication_check.py": echte_tagesakte["publication_check.py"]
        .replace("publication-receipt-", "receipt-").replace(
            "def beleg_schreiben(", "def _beleg_entfernt(")})
    if not [f for f in c26_beleg_je_tag(ohne_tag, wflows_echt)
            if "tagesgenauen Beleg" in f[1]]:
        failures.append("C26: ein fehlender Tagesbeleg bleibt unentdeckt "
                        "(#610).")
    # (c) Die Nachweis-Pflicht in der Sichtung wird entfernt.
    ohne_nachweis = dict(echte_tagesakte, **{
        "reserve_custody.py": echte_tagesakte["reserve_custody.py"]
        .replace("ruecklaeufer_ohne_nachweis", "ruecklaeufer_wie_immer")})
    if not [f for f in c26_beleg_je_tag(ohne_nachweis, wflows_echt)
            if "eigenen Zustand" in f[1]]:
        failures.append("C26: eine entfernte Nachweis-Pflicht bleibt unentdeckt "
                        "(#610).")
    # (d) Der Rückweg aus dem Janitor wird entfernt (Löschen ohne Beweis).
    ohne_rueckweg = dict(echte_tagesakte, **{
        "reserve_janitor.py": echte_tagesakte["reserve_janitor.py"]
        .replace("zurueck_in_den_pool(", "_zurueck_entfernt(")})
    if not [f for f in c26_beleg_je_tag(ohne_rueckweg, wflows_echt)
            if "Löschen ohne Beweis" in f[1] or "nicht zurück" in f[1]]:
        failures.append("C26: ein entfernter Rückweg im Janitor bleibt "
                        "unentdeckt (#610).")
    # (e) Das Artefakt des Tagesbelegs fällt aus dem Workflow.
    wflows_ohne_beleg = dict(wflows_echt)
    for pfad in list(wflows_ohne_beleg):
        if os.path.basename(pfad) == "publication-delivery.yml":
            wflows_ohne_beleg[pfad] = wflows_ohne_beleg[pfad].replace(
                "publication-receipt*.json", "publication-receipt.json")
    if not [f for f in c26_beleg_je_tag(echte_tagesakte, wflows_ohne_beleg)
            if "Artefakt" in f[1]]:
        failures.append("C26: ein fehlendes Tages-Artefakt bleibt unentdeckt "
                        "(#610).")
    # --- C27: Beweisen ist nicht Fabrizieren (Nebenbefund #610, 07.10.2026) --
    echte_ledgerakte = {name: _read(os.path.join(BLOG_DIR, "scripts", name))
                        for name in ("audit_log.py", "repo_isolation.py")}
    if c27_ledger_isolation(echte_ledgerakte, wflows_echt):
        failures.append(f"C27: der echte Zustand wird beanstandet: "
                        f"{c27_ledger_isolation(echte_ledgerakte, wflows_echt)}")
    # (a) Der Engpass verliert die Umlenkung – der Zustand vor dem 07.10.2026.
    ohne_umlenkung = dict(echte_ledgerakte, **{
        "audit_log.py": echte_ledgerakte["audit_log.py"]
        .replace("FFC_AUDIT_DIR", "FFC_AUDIT_XXX")})
    if not [f for f in c27_ledger_isolation(ohne_umlenkung, wflows_echt)
            if "FFC_AUDIT_DIR" in f[1]]:
        failures.append("C27: ein Engpass ohne FFC_AUDIT_DIR bleibt unentdeckt "
                        "(Nebenbefund #610).")
    # (b) log_event() schreibt wieder fest ins Repo – Umlenkung wirkungslos.
    fest_verdrahtet = dict(echte_ledgerakte, **{
        "audit_log.py": echte_ledgerakte["audit_log.py"]
        .replace("audit_verzeichnis()", "AUDIT_DIR")})
    if not [f for f in c27_ledger_isolation(fest_verdrahtet, wflows_echt)
            if "wirkungslos" in f[1]]:
        failures.append("C27: ein fest verdrahteter Schreibpfad bleibt "
                        "unentdeckt (Nebenbefund #610).")
    # (c) SCHEIN-SICHERHEIT: Der Rückfall auf data/audit verschwindet. Diese
    #     „Isolation" wäre eine Abschaltung des Betriebs-Ledgers – sie würde
    #     Beweise vernichten statt zu fabrizieren, und ist der teurere Fehler.
    stumm = dict(echte_ledgerakte, **{
        "audit_log.py": echte_ledgerakte["audit_log.py"]
        .replace("return ziel or AUDIT_DIR", "return ziel or ''")})
    if not [f for f in c27_ledger_isolation(stumm, wflows_echt)
            if "still abgeschaltet" in f[1]]:
        failures.append("C27: eine als Isolation getarnte Abschaltung des "
                        "Betriebs-Ledgers bleibt unentdeckt (Nebenbefund #610).")
    # (d) Die Sandbox fehlt – jeder Test müsste das Ledger von Hand schützen.
    ohne_sandbox = dict(echte_ledgerakte, **{"repo_isolation.py": ""})
    if not [f for f in c27_ledger_isolation(ohne_sandbox, wflows_echt)
            if "repo_isolation.py fehlt" in f[1]]:
        failures.append("C27: eine fehlende Sandbox bleibt unentdeckt "
                        "(Nebenbefund #610).")
    # (e) Die empirische Leitplanke fällt aus dem Qualitäts-Gate.
    wflows_ohne_leitplanke = dict(wflows_echt)
    for pfad in list(wflows_ohne_leitplanke):
        if os.path.basename(pfad) == "publication-reliability-tests.yml":
            wflows_ohne_leitplanke[pfad] = wflows_ohne_leitplanke[pfad].replace(
                "git status --porcelain -- data/audit", "true")
    if not [f for f in c27_ledger_isolation(echte_ledgerakte, wflows_ohne_leitplanke)
            if "unberührt" in f[1]]:
        failures.append("C27: eine fehlende Ledger-Leitplanke im Qualitäts-Gate "
                        "bleibt unentdeckt (Nebenbefund #610).")
    # --- C28: Die Klasse geht dem Kanal vor (WF-7C1F #611, 07.10.2026) --------
    echte_klassenakte = {
        "publication_check.py": _read(os.path.join(BLOG_DIR, "scripts",
                                                   "publication_check.py"))}

    def _wf_variante(ersetzung, was):
        """Kopie der Workflows mit einer Sabotage im Auslieferungs-Nachweis."""
        kopie = dict(wflows_echt)
        for pfad, text_ in list(kopie.items()):
            if os.path.basename(pfad) == "publication-delivery.yml":
                kopie[pfad] = text_.replace(*ersetzung)
        return kopie

    if c28_klassen_routing(echte_klassenakte, wflows_echt):
        failures.append(f"C28: der echte Zustand wird beanstandet: "
                        f"{c28_klassen_routing(echte_klassenakte, wflows_echt)}")
    # (a) Der Beleg verliert seine Klasse – der Workflow hätte nichts zu lesen.
    ohne_klasse = dict(echte_klassenakte, **{
        "publication_check.py": echte_klassenakte["publication_check.py"].replace(
            "result['klasse'] = klasse(result)", "pass")})
    if not [f for f in c28_klassen_routing(ohne_klasse, wflows_echt)
            if "Beleg" in f[1]]:
        failures.append("C28: ein Beleg ohne Klasse bleibt unentdeckt (#611).")
    # (b) Die Historie verliert den Besitzer – ein roter Tag wäre später blind.
    ohne_historie = dict(echte_klassenakte, **{
        "publication_check.py": echte_klassenakte["publication_check.py"].replace(
            "'klasse':", "'keine_klasse':")})
    if not [f for f in c28_klassen_routing(ohne_historie, wflows_echt)
            if "Historie" in f[1]]:
        failures.append("C28: eine Historie ohne Klasse bleibt unentdeckt (#611).")
    # (c) Der Sammel-Boolean kehrt zurück – genau der Befund #611.
    sp = ("      - name: AUSLIEFERUNGS-DEFIZIT",
          "      - name: Missing public delivery is a failed run\n"
          "        run: exit 0\n"
          "      - name: AUSLIEFERUNGS-DEFIZIT")
    if not [f for f in c28_klassen_routing(echte_klassenakte, _wf_variante(sp, ""))
            if "Sammel" in f[1]]:
        failures.append("C28: der Sammel-Boolean ohne Ursache bleibt unentdeckt "
                        "(#611).")
    # (d) SCHEIN-SICHERHEIT: Der Frischebeweis wandert HINTER den roten Exit –
    #     der Kanal wäre belegt, aber zu spät für dieses Alerting (#602).
    spaet = ("          # Der Bestand trägt den gemessenen Tag nicht",
             "          exit 1\n"
             "          # Der Bestand trägt den gemessenen Tag nicht")
    if not [f for f in c28_klassen_routing(echte_klassenakte, _wf_variante(spaet, ""))
            if "NACH dem roten Exit" in f[1]]:
        failures.append("C28: ein Frischebeweis nach dem roten Exit bleibt "
                        "unentdeckt (#602).")
    # (e) Der Schrittname verliert die Kennwörter – die Stummschaltung des
    #     zentralen Fehler-Alertings greift nicht mehr.
    namen = ("- name: TAGESDEFIZIT – Fachmeldung engine-deficit ist zuständig "
             "(Auslieferungs-SLO)",
             "- name: Bestandsdefizit (Auslieferungs-SLO)")
    if not [f for f in c28_klassen_routing(echte_klassenakte, _wf_variante(namen, ""))
            if "Kennwörter" in f[1]]:
        failures.append("C28: ein Schrittname ohne die Alerting-Kennwörter bleibt "
                        "unentdeckt (#602).")
    # (f) Fail-open: Ein unbekannter Beleg wird still zu „ok“ erklärt.
    if not [f for f in c28_klassen_routing(echte_klassenakte,
                                           _wf_variante(("unbekannt", "ok"), ""))
            if "unbekannten Beleg" in f[1]]:
        failures.append("C28: ein stiller unbekannter Beleg bleibt unentdeckt "
                        "(#611).")
    # --- C29: Der Schreiber prüft, was über ihn entscheidet (#612) ----------
    # Von hier an prüft der SELFTEST die neue Regel mit Kunstbefunden. Der
    # echte Baum muss still bleiben; jede Sabotage muss GENAU ihren Zweig
    # treffen. Der Ruinen-Heiler läuft dabei EINMAL echt (Wirkungsprobe).
    echte_schreiber = {name: _read(os.path.join(BLOG_DIR, "scripts", name))
                       for name in ("generate_drafts.py", "engine_generate.py",
                                    "reserve_gate.py", "politur_ruine_heiler.py",
                                    "reserve_finisher.py",
                                    "reserve_healer_coverage.py")}
    echt_befunde = c29_geburts_tor(echte_schreiber, wflows_echt,
                                   python_bin=sys.executable or "python3")
    if echt_befunde:
        failures.append(f"C29: der echte Zustand wird beanstandet: {echt_befunde}")
    # (a) Das Geburts-Gate misst die Lesbarkeit nicht mehr: #612 kehrt zurück.
    ohne_messung = dict(echte_schreiber, **{
        "generate_drafts.py": echte_schreiber["generate_drafts.py"].replace(
            "lesbarkeits_befund(body)", "None")})
    if not [f for f in c29_geburts_tor(ohne_messung, wflows_echt,
                                       python_bin=sys.executable or "python3")
            if "Papier" in f[1] or "Lesbarkeit" in f[1]]:
        failures.append("C29: eine abgeschaltete Lesbarkeits-Messung im "
                        "Geburts-Gate bleibt unentdeckt (#612).")
    # (b) Der Retry verliert sein Gedächtnis – genau der Zustand vor #612.
    ohne_gedaechtnis = dict(echte_schreiber, **{
        "engine_generate.py": echte_schreiber["engine_generate.py"].replace(
            "hinweise=letzte_hinweise or None", "")})
    if not [f for f in c29_geburts_tor(ohne_gedaechtnis, wflows_echt,
                                       python_bin=sys.executable or "python3")
            if "Vorversuchs" in f[1]]:
        failures.append("C29: ein Retry ohne Gedächtnis bleibt unentdeckt (#612).")
    # (c) Die Chronik steht wieder NACH dem Commit: der Trend-Beweis wäre bei
    #     jedem roten Lauf verloren, obwohl der Heiler ihn liefern kann.
    yml_chronik = dict(wflows_echt)
    for pfad in list(yml_chronik):
        if os.path.basename(pfad) == "content-reserve.yml":
            yml_chronik[pfad] = yml_chronik[pfad].replace(
                "reserve_gate.py --chronik", "# Chronik entfernt")
    if not [f for f in c29_geburts_tor(echte_schreiber, yml_chronik,
                                       python_bin=sys.executable or "python3")
            if "VOR dem Commit" in f[1] or "Chronik" in f[1]]:
        failures.append("C29: eine fehlende Chronik-Vorverlagerung bleibt "
                        "unentdeckt (WF-D4E0 #612).")
    # (d) Der Ruinen-Heiler fällt aus der Kette: der Kandidat hängt wieder an
    #     einem „SATZ: “-Rest und der Vorrat fällt unter das Ziel (#612).
    ohne_heiler = dict(echte_schreiber, **{
        "reserve_finisher.py": echte_schreiber["reserve_finisher.py"].replace(
            '("politur_ruine_heiler.py"', '("x_politur_ruine_heiler.py"')})
    if not [f for f in c29_geburts_tor(ohne_heiler, wflows_echt,
                                       python_bin=sys.executable or "python3")
            if "HEALER_CHAIN" in f[1] or "Politur" in f[1]]:
        failures.append("C29: ein aus der Reserve-Kette entfernter "
                        "Politur-Ruinen-Heiler bleibt unentdeckt (#612).")
    # --- C30: Eine Seite hat genau eine H1 (#623) -------------------------
    # Der echte Baum muss still bleiben; jede Sabotage muss GENAU ihren
    # Zweig treffen. Die Wirkungsprobe der Wache läuft dabei einmal echt.
    h1_dateien = ("h1_wache.py", "a11y_audit.py")
    echte_h1 = {name: _read(os.path.join(BLOG_DIR, "scripts", name))
                for name in h1_dateien}
    echte_h1_befunde = c30_eine_h1(echte_h1, wflows_echt,
                                   python_bin=sys.executable or "python3")
    if echte_h1_befunde:
        failures.append(f"C30: der echte Zustand wird beanstandet: "
                        f"{echte_h1_befunde}")
    # (a) Die Wache prüft nur die Quelle: die gebaute Wahrheit fiele wieder
    #     durch – genau die Hälfte, die #623 sichtbar machte.
    ohne_build = dict(echte_h1, **{
        "h1_wache.py": echte_h1["h1_wache.py"].replace(
            '"--public"', '"--oeffentlich"')})
    if not [f for f in c30_eine_h1(ohne_build, wflows_echt,
                                   python_bin=sys.executable or "python3")
            if "gebauten Seiten" in f[1] or "--public" in f[1]]:
        failures.append("C30: eine Wache ohne Build-Prüfung bleibt unentdeckt "
                        "(#623).")
    # (b) Die Stichprobe kehrt zurück: 20 von 107 Seiten sahen die dritte
    #     Doppel-H1 nicht.
    stichprobe = dict(echte_h1, **{
        "a11y_audit.py": echte_h1["a11y_audit.py"].replace(
            "    return files", "    return files[:20]  # STICHPROBE")})
    if not [f for f in c30_eine_h1(stichprobe, wflows_echt,
                                   python_bin=sys.executable or "python3")
            if "STICHPROBE" in f[1]]:
        failures.append("C30: eine wieder eingeführte Stichprobe im Audit "
                        "bleibt unentdeckt (#623).")
    # (c) Eine lokale Ersatz-Ausnahmeliste oder ein blinder Asset-Filter
    #     darf das zentrale, begründete Register nicht umgehen.
    a11y_fallback = dict(echte_h1, **{
        "a11y_audit.py": echte_h1["a11y_audit.py"].replace(
            "from h1_wache import AUSNAHMEN_SEITE as AUSNAHMEN, h1_der_seite",
            "from h1_wache import h1_der_seite\nAUSNAHMEN = ((r'^go/', 'fallback'),)"
        ) + "\nSKIP_PATTERNS = ('BingSiteAuth',)\n"
    })
    if not [f for f in c30_eine_h1(a11y_fallback, wflows_echt,
                                   python_bin=sys.executable or "python3")
            if "Ersatz-Ausnahmeliste" in f[1]]:
        failures.append("C30: eine lokale Ersatzliste/Skip-Ausnahme im A11y-Audit "
                        "bleibt unentdeckt.")
    # (c) Die Wache fällt aus dem Deploy: geprüft wäre nur, was jemand von
    #     Hand ruft – und die Doppel-H1 stünde wieder live.
    def _deploy_variante(ersetzung):
        """Kopie der Workflows mit einer Sabotage in deploy.yml."""
        kopie = dict(wflows_echt)
        for pfad, text_ in list(kopie.items()):
            if os.path.basename(pfad) == "deploy.yml":
                kopie[pfad] = text_.replace(*ersetzung)
        return kopie

    if not [f for f in c30_eine_h1(echte_h1,
                                   _deploy_variante(("scripts/h1_wache.py --source-only",
                                                     "# Wache entfernt")),
                                   python_bin=sys.executable or "python3")
            if "source-only" in f[1] or "deploy.yml" in f[1]]:
        failures.append("C30: eine aus deploy.yml entfernte Quell-Prüfung der "
                        "H1-Wache bleibt unentdeckt (#623).")
    if not [f for f in c30_eine_h1(echte_h1,
                                   _deploy_variante(("scripts/h1_wache.py --public public",
                                                     "# Build-Prüfung entfernt")),
                                   python_bin=sys.executable or "python3")
            if "gebauten Seiten" in f[1] or "deploy.yml" in f[1]]:
        failures.append("C30: eine aus deploy.yml entfernte Build-Prüfung der "
                        "H1-Wache bleibt unentdeckt (#623).")

    # Änderungen an Wache/Audit und deren Tests müssen den E2E-Vertrag auslösen.
    def _e2e_variante(ersetzung):
        kopie = dict(wflows_echt)
        for pfad, text_ in list(kopie.items()):
            if os.path.basename(pfad) == "e2e.yml":
                kopie[pfad] = text_.replace(*ersetzung)
        return kopie

    if not [f for f in c30_eine_h1(
            echte_h1,
            _e2e_variante(('"scripts/a11y_audit.py"', '"# Audit-Pfad entfernt"')),
            python_bin=sys.executable or "python3")
            if "e2e.yml-Pfadfilter" in f[1]]:
        failures.append("C30: ein aus dem e2e.yml-Pfadfilter entfernter A11y-Audit "
                        "bleibt unentdeckt.")
    # (d) Eine Wache, die selbst heilt, vernichtet Sätze.
    mit_fix = dict(echte_h1, **{
        "h1_wache.py": echte_h1["h1_wache.py"].replace(
            'parser.add_argument("--json"',
            'parser.add_argument("--fix", action="store_true")\n'
            '    parser.add_argument("--json"')})
    if not [f for f in c30_eine_h1(mit_fix, wflows_echt,
                                   python_bin=sys.executable or "python3")
            if "--fix" in f[1]]:
        failures.append("C30: eine selbst heilende H1-Wache bleibt unentdeckt "
                        "(Content-Verlust, #623).")
    # (e) STUFE 2 (08.10.2026): Markdown-Wahrheit, Inventar und
    #     Startseiten-Blätterkopf sind eigene Zusagen der Wache – jede muss
    #     auffallen, wenn sie verschwindet.
    def _wache_variante(alt, neu):
        return dict(echte_h1, **{
            "h1_wache.py": echte_h1["h1_wache.py"].replace(alt, neu)})

    for alt, neu, marke, grund in (
            ("SETEXT_UNTERSTRICH", "X_UNTERSTRICH", "SETEXT_UNTERSTRICH",
             "die Setext-H1 (`Text` + `=====`) fiele aus der Quellprüfung"),
            ("markdown_roh_html_h1", "x_roh_html", "roh",
             "rohes `<h1 …>` (unsafe = true) fiele aus der Quellprüfung"),
            ("H1_QUELLEN", "X_QUELLEN", "H1_QUELLEN",
             "das H1-Inventar fehlte – eine neue H1-Quelle bliebe unbemerkt"),
            ("H1_BLAETTERKOPF", "X_BLAETTERKOPF", "H1_BLAETTERKOPF",
             "der Startseiten-Blätterkopf wäre nicht mehr gebunden")):
        if not [f for f in c30_eine_h1(_wache_variante(alt, neu), wflows_echt,
                                       python_bin=sys.executable or "python3")
                if marke in f[1]]:
            failures.append(f"C30: {grund} bleibt unentdeckt (#623, Stufe 2).")
    # Die pauschale Blätter-Ausnahme kehrt zurück: /page/2/ wäre wieder
    # unsichtbar – genau der Zustand, den Stufe 2 geheilt hat.
    pauschal = _wache_variante(
        "AUSNAHMEN_H1: tuple[tuple[str, str], ...] = (\n",
        "AUSNAHMEN_H1: tuple[tuple[str, str], ...] = (\n"
        "    (r\"^(?:[^/]+/)?page/[0-9]+/index\\.html$\", \"Sabotage\"),\n")
    if not [f for f in c30_eine_h1(pauschal, wflows_echt,
                                   python_bin=sys.executable or "python3")
            if "Blätterseiten" in f[1]]:
        failures.append("C30: eine wieder eingeführte pauschale "
                        "Blätter-Ausnahme bleibt unentdeckt (#623, Stufe 2).")
    # Und im Pull Request muss die gebaute Wahrheit gemessen werden.
    if not [f for f in c30_eine_h1(
            echte_h1,
            _e2e_variante(("scripts/h1_wache.py --public public",
                           "# Build-Wache entfernt")),
            python_bin=sys.executable or "python3")
            if "GEBAUTEN" in f[1]]:
        failures.append("C30: eine aus e2e.yml entfernte Build-Prüfung der "
                        "H1-Wache bleibt unentdeckt (#623, Stufe 2).")
    # --- C32: Doppelte Mapping-Schluessel (#643) ---------------------------
    # Der echte Baum muss still bleiben; jede Sabotage muss GENAU ihren Zweig
    # treffen. Selbsttest und Fixture-Beweis der Wache laufen dabei einmal echt.
    c32_dateien = ("fm_boundary_guard.py", "post_utils.py", "tag_governance.py",
                   "keyword_optimizer.py", "pinterest_pin_text_sync.py")
    echte_c32 = {name: _read(os.path.join(BLOG_DIR, "scripts", name))
                 for name in c32_dateien}
    echte_c32_befunde = c32_doppelte_schluessel(
        echte_c32, wflows_echt, python_bin=sys.executable or "python3")
    if echte_c32_befunde:
        failures.append(f"C32: der echte Zustand wird beanstandet: "
                        f"{echte_c32_befunde}")
    # (a) Die F7-Erkennung faellt aus dem Pruefpfad: der Build stuerbe wieder
    #     an einer Zeile, die PyYAML fuer gueltig haelt (#643).
    ohne_f7 = dict(echte_c32, **{
        "fm_boundary_guard.py": echte_c32["fm_boundary_guard.py"].replace(
            "doppel = doppelte_schluessel(fm_lines)", "doppel = []")})
    if not [f for f in c32_doppelte_schluessel(
            ohne_f7, wflows_echt, python_bin=sys.executable or "python3")
            if "F7-Erkennung" in f[1] or "doppelte" in f[1]]:
        failures.append("C32: eine abgeschaltete F7-Erkennung bleibt unentdeckt "
                        "(#643).")
    # (b) Der Parser-Kurzschluss steht wieder VOR der Erkennung: genau der
    #     Zustand, in dem alle PyYAML-Gates gruen waren und Hugo starb.
    alte_reihenfolge = dict(echte_c32, **{
        "fm_boundary_guard.py": echte_c32["fm_boundary_guard.py"].replace(
            "if not doppel and _yaml is not None and parse_ok(",
            "if _yaml is not None and parse_ok(")})
    if not [f for f in c32_doppelte_schluessel(
            alte_reihenfolge, wflows_echt, python_bin=sys.executable or "python3")
            if "Parser-Kurzschluss" in f[1] or "unsichtbar" in f[1]]:
        failures.append("C32: ein Parser-Kurzschluss vor der F7-Erkennung "
                        "bleibt unentdeckt (#643).")
    # (c) Der Deploy heilt nicht mehr VOR dem Build: die Bau-Falle kehrt zurueck.
    ohne_heilung = dict(wflows_echt)
    for pfad in list(ohne_heilung):
        if os.path.basename(pfad) == "deploy.yml":
            ohne_heilung[pfad] = ohne_heilung[pfad].replace(
                "scripts/fm_boundary_guard.py --fix", "# Heilung entfernt")
    if not [f for f in c32_doppelte_schluessel(
            echte_c32, ohne_heilung, python_bin=sys.executable or "python3")
            if "vorher geheilt" in f[1] or "Heilung" in f[1]]:
        failures.append("C32: ein Deploy ohne FM-Selbstheilung bleibt unentdeckt "
                        "(#643).")
    # (d) Ein Schreiber laesst die Schlussregel fallen: count=1 liesse die
    #     zweite Zeile stehen und machte die Falle nur unsichtbar (#643).
    ohne_regel = dict(echte_c32, **{
        "tag_governance.py": echte_c32["tag_governance.py"].replace(
            "return post_utils.doppel_freies_feld(ergebnis[:grenze], feld) + "
            "ergebnis[grenze:]", "return ergebnis")})
    if not [f for f in c32_doppelte_schluessel(
            ohne_regel, wflows_echt, python_bin=sys.executable or "python3")
            if "doppel_freies_feld" in f[1]]:
        failures.append("C32: ein FM-Schreiber ohne die Schlussregel bleibt "
                        "unentdeckt (#643).")
    # (e) Der PR-Pfad verliert die fail-closed Pruefung: doppelte Schluessel
    #     koennten unbemerkt nach main wandern.
    ohne_pr = dict(wflows_echt)
    for pfad in list(ohne_pr):
        if os.path.basename(pfad) == "publication-reliability-tests.yml":
            ohne_pr[pfad] = ohne_pr[pfad].replace(
                "python3 scripts/fm_boundary_guard.py --check",
                "# Pruefung entfernt")
    if not [f for f in c32_doppelte_schluessel(
            echte_c32, ohne_pr, python_bin=sys.executable or "python3")
            if "nach main tragen" in f[1] or "--check" in f[1]]:
        failures.append("C32: ein PR-Pfad ohne fail-closed FM-Pruefung bleibt "
                        "unentdeckt (#643).")
    # --- C33: Maschinen-Artefakte werden gegengelesen (#653) ---------------
    # Der echte Baum muss still bleiben; jede Sabotage muss GENAU ihren Zweig
    # treffen. Sechs Nächte „0/6 gate-fertig“ bei vollem Vorrat waren der
    # Preis dafür, dass niemand die Artefakte gegenlas.
    c33_dateien = ("artefakt_waechter.py", "reserve_gate.py",
                   "reserve_readiness.py")
    echte_c33 = {name: _read(os.path.join(BLOG_DIR, "scripts", name))
                 for name in c33_dateien}
    if c33_artefakt_waechter(echte_c33, wflows_echt,
                             python_bin=sys.executable or "python3"):
        failures.append(f"C33: der echte Zustand wird beanstandet: "
                        f"{c33_artefakt_waechter(echte_c33, wflows_echt, python_bin=sys.executable or 'python3')}")
    # (a) Eine Klasse fällt aus dem Prüfpfad: JSONL-Fehler blieben wieder
    #     unsichtbar – genau die Hälfte der Wahrheit, die #653 verschwieg.
    ohne_a3 = dict(echte_c33, **{
        "artefakt_waechter.py": echte_c33["artefakt_waechter.py"].replace(
            "A3", "A9")})
    if not [f for f in c33_artefakt_waechter(
            ohne_a3, wflows_echt, python_bin=sys.executable or "python3")
            if "A3" in f[1]]:
        failures.append("C33: eine fehlende Artefakt-Klasse bleibt unentdeckt "
                        "(#653).")
    # (b) Der PR-Pfad verliert den Wächter: ein strukturell kaputtes
    #     Artefakt könnte wieder unbemerkt nach main wandern.
    ohne_pr33 = dict(wflows_echt)
    for pfad in list(ohne_pr33):
        if os.path.basename(pfad) == "integrity-lock.yml":
            ohne_pr33[pfad] = ohne_pr33[pfad].replace(
                "python3 scripts/artefakt_waechter.py",
                "# Wächter entfernt")
    if not [f for f in c33_artefakt_waechter(
            echte_c33, ohne_pr33, python_bin=sys.executable or "python3")
            if "integrity-lock.yml" in f[1]]:
        failures.append("C33: ein PR-Pfad ohne Artefakt-Wächter bleibt "
                        "unentdeckt (#653).")
    # (c) Die Zertifizierung hängt wieder am Wachen-Selbsttest: die Messung
    #     wird übersprungen und der End-Gate liest die VORNACHT als heute.
    stufe3_gegängt = dict(wflows_echt)
    for pfad in list(stufe3_gegängt):
        if os.path.basename(pfad) == "content-reserve.yml":
            stufe3_gegängt[pfad] = stufe3_gegängt[pfad].replace(
                "        if: ${{ !cancelled() }}\n        continue-on-error: true\n"
                "        run: python3 scripts/reserve_readiness.py",
                "        if: ${{ !cancelled() && steps.wachen.conclusion != 'failure' }}\n"
                "        continue-on-error: true\n"
                "        run: python3 scripts/reserve_readiness.py")
    if not [f for f in c33_artefakt_waechter(
            echte_c33, stufe3_gegängt,
            python_bin=sys.executable or "python3")
            if "Stufe 3" in f[1]]:
        failures.append("C33: eine am Wachen-Selbsttest hängende "
                        "Zertifizierung bleibt unentdeckt (#653).")
    # (d) Der End-Gate verliert die Ursachenklassen: eine fehlgeschlagene
    #     Messung sieht wieder aus wie ein leerer Vorrat.
    ohne_klassen = dict(echte_c33, **{
        "reserve_gate.py": echte_c33["reserve_gate.py"].replace(
            "def zertifikat_lage(", "def _entfernt_zertifikat_lage(")})
    if not [f for f in c33_artefakt_waechter(
            ohne_klassen, wflows_echt,
            python_bin=sys.executable or "python3")
            if "zertifikat_lage" in f[1]]:
        failures.append("C33: ein End-Gate ohne Ursachenklassen bleibt "
                        "unentdeckt (#653).")
    # (e) Der Schreiber schreibt wieder unteilbar-falsch: ein halbes
    #     Zertifikat stünde wieder im Repo.
    ohne_atomar = dict(echte_c33, **{
        "reserve_readiness.py": echte_c33["reserve_readiness.py"].replace(
            "os.replace(", "os.rename(")})
    if not [f for f in c33_artefakt_waechter(
            ohne_atomar, wflows_echt, python_bin=sys.executable or "python3")
            if "os.replace" in f[1]]:
        failures.append("C33: ein nicht atomar schreibender Zertifikats-"
                        "Schreiber bleibt unentdeckt (#653).")
    if failures:
        print("❌ KONTRAKT-SELFTEST FEHLGESCHLAGEN:")
        for f in failures:
            print("   -", f)
        return 2
    print("✅ KONTRAKT-SELFTEST bestanden (C1–C33 mit Kunstbefunden: Fehler "
          "erkannt, gutes Setup bleibt still; Haus-Nummern C24/C31 gehören "
          "anderen Verträgen).")
    return 0


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--selftest" in argv:
        return _selftest()
    quick = "--quick" in argv
    pybin = argv[argv.index("--python") + 1] if "--python" in argv else sys.executable or "python3"
    checks = run_all(python_bin=pybin, quick=quick)
    if checks:
        print("🔒 GOVERNANCE-VERTRAG: verletzt\n")
        annotate = bool(os.environ.get("GITHUB_ACTIONS"))
        # C9-Meldungen nennen Datei und Muster-Label eines Befunds –
        # niemals den Inhalt oder Wert dahinter.
        for code, msg in checks:
            line = f"{code} {LABEL.get(code, '')}: {msg}"
            # LABEL/msg sind feste Regel-Bezeichner und Muster-Namen (z. B.
            # "API-Key im Klartext") aus LEAK_CHECK_PATTERNS – nie der gefundene
            # Geheimwert selbst (c9_leak_wache übernimmt nur `label`, nie den
            # Match-Text). Bis 05.10.2026 stand hier eine `# codeql[...]`-
            # Unterdrückung; sie ist entfallen, weil die Ursache geheilt wurde:
            # Die Wache heißt nicht mehr `c9_secret_leak`, und keine Quelle
            # dieses Datenflusses trägt noch einen Namen, der Zugangsdaten
            # behauptet. Dauerhaft bewacht durch test_clear_text_logging_security.py
            # und test_zugangs_namensvertrag.py.
            print(f"  ❌ {line}")
            if annotate:
                # ::error:: trägt denselben geprüften Befund-Text – kein Geheimwert.
                print(f"::error::{line}")
    else:
        count = len(RULE_TEXT)
        print(f"🔒 GOVERNANCE-VERTRAG erfüllt – alle {count} Regeln prüfen in beide "
              f"Richtungen (Fehler UND Schein-Sicherheit).")
    if "--md" in argv:
        target = argv[argv.index("--md") + 1]
        try:
            os.makedirs(os.path.dirname(os.path.join(BLOG_DIR, target)) or BLOG_DIR, exist_ok=True)
            # Markdown-Report der Vertragsprüfung: Befund-Texte ohne Werte.
            with open(os.path.join(BLOG_DIR, target), "w", encoding="utf-8") as f:
                # render_md() setzt nur LABEL/RULE_TEXT (feste Regel-Beschreibungen)
                # und dieselben wertfreien `msg`-Texte wie oben zusammen – niemals
                # einen gefundenen Geheimwert. Die frühere `# codeql[...]`-
                # Unterdrückung ist entfallen: Der Fund kam von der lokalen
                # Variablen `secrets` (jetzt `wachen_quelltext`), nicht vom
                # Inhalt. Siehe CODE-SCANNING-ALERT-78-DAUERHEILUNG-PREMIUM-2026-10-05.md.
                f.write(render_md(checks))
            print(f"→ geschrieben: {target}")
        except OSError as exc:
            print(f"⚠️  Markdown konnte nicht geschrieben werden: {exc}")
    return 1 if checks else 0


if __name__ == "__main__":
    sys.exit(main())

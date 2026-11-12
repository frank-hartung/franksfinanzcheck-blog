# Wartung · Betriebspflege · WF-E813 / #972 · 12.11.2026

## Ergebnis in einem Satz

Der Ablauf ist im Repository dauerhaft klarer und sicherer gemacht; **#972 ist
nicht betrieblich behoben und bleibt offen**. Der neueste belegbare produktive
Lauf (11.11.2026, Run
[43033350448](https://github.com/frank-hartung/franksfinanzcheck-blog/actions/runs/43033350448))
weist weiterhin zwei getrennte Live-Probleme aus: F-01 antwortet ohne
Cloudflare-Proxy-Kennung, und der Worker liefert kein vollständiges
Betriebsbild bzw. keinen aktuellen Build-Stempel. Die Live-Infrastruktur und
rechtlich notwendige Datenschutzfreigabe liegen außerhalb dieses Repositories;
keine davon wurde hier auf Verdacht geändert.

## Aktueller, belegter Befund

- Im Live-Lauf ist die Offline-Quellseitenprüfung erfolgreich. Der Live-Job
  schlägt bei F-01, Worker und Gesamtabschluss fehl; der nachgelagerte
  Selbstheilungsschritt wurde ebenfalls als fehlgeschlagen ausgewiesen.
- Die GitHub-Check-Annotationen belegen für `/` und `/methodik/` jeweils fünf
  fehlende Pflicht-Header. Die Proxy-Diagnose nennt ausdrücklich: weder
  `cf-ray` noch `server: cloudflare`; deshalb kann die Transform Rule nicht
  wirken. Eine Regeländerung allein wäre kein sachgerechter Fix.
- Die Worker-Annotationen nennen fehlende Felder `budget`, `turnstile`,
  `schluesselrollen` und `exporte`, sowie den fehlenden `/healthz`-Build-Stempel
  `bau`. Der Hinweis führt zum Environment-/Deploy-Pfad statt zu einer
  Änderung an Secrets oder Schutzfunktionen auf Verdacht.
- Read-only-Abfrage des GitHub-Environments `cloudflare-produktion`:
  `protection_rules=[]`, `can_admins_bypass=true`,
  `deployment_branch_policy=null` (zuletzt aktualisiert am 25.10.2026).
  Das Environment ist damit nicht deploy-sicher.
- `npm run edge:b7` besteht den Selbsttest, der eigentliche B7-Check ist aber
  rot: Die veröffentlichungsrelevante Datenschutzerklärung enthält noch
  Vor-Proxy-Aussagen (kein Cloudflare-Proxy / keine Informationen über
  Seitenaufrufe; Cloudflare nur als DNS-Empfänger). Der Heiler muss vor jedem
  Cloudflare-Schreibzugriff daran scheitern.
- Eine read-only-Abfrage der Repository-Variable `CF_EDGE_AUTOHEAL` wurde von
  GitHub mit HTTP 403 abgelehnt. Ob Variable und Secret eingerichtet sind,
  ist somit **nicht belegt**. Es wurde kein Secret gelesen oder geschrieben.

## Dauerhafte Repository-Änderung

Der Live-Heiler unterscheidet jetzt zwischen einem **bewusst gesperrten,
mutationsfreien Versuch** und einer fehlgeschlagenen technischen Reparatur:

- Fehlende Betreiberfreigabe sowie offener/fehlender B7-Text werden im
  Actions-Log und in der Zusammenfassung als „gesperrt“ ausgewiesen und als
  GitHub-Warnung gemeldet, statt den Selbstheilungsschritt mit einem zweiten,
  irreführenden Fehler rot zu markieren.
- Die ursprüngliche F-01-Messung und der Abschlussvertrag bleiben unverändert.
  F-01-BEFUND bleibt rot; diese Warnung kann weder den Live-Befund noch den
  Worker-Fehler in einen erfolgreichen Lauf umdeuten.
- Ungültige/unvollständige Messungen, nicht belegbare API-Zustände, tatsächliche
  API-/Nachmessfehler und Fehler nach Beginn eines Schreibversuchs bleiben
  Fehler. Token, Rohantworten und personenbezogene Inhalte werden nicht in die
  Warnung übernommen.
- Der Runbook-Abschnitt A1c hält diese Semantik und die Operator-Grenzen fest.

## Nächste Schritte für den Betreiber

1. B7 rechtlich und fachlich aktualisieren und veröffentlichen, bevor die
   Proxy-Umstellung wirksam wird. `npm run edge:b7` muss Exit 0 liefern; Code-
   und Textprüfung ersetzen keine juristische Freigabe.
2. Cloudflare-Dashboard: beide betroffenen DNS-Hosts korrekt proxied schalten,
   TLS auf `Full` oder bevorzugt `Full (strict)` belassen und die
   `FF Sicherheits-Header`-Regel gegen `cloudflare/edge-schutz.md` prüfen. Die
   Ursache ist laut Live-Messung die fehlende Proxy-Ebene; erst danach kann die
   Regel Wirkung zeigen.
3. Nach ausdrücklicher Betreiberfreigabe die separate, zonenbegrenzte
   `CF_EDGE_HEAL_TOKEN`-Berechtigung und `CF_EDGE_AUTOHEAL=true` gemäß Runbook
   A1c einrichten. Ob diese Einstellungen existieren, konnte nicht geprüft
   werden. Keine Worker- oder AI-Tokens wiederverwenden.
4. `cloudflare-produktion` durch den berechtigten Maintainer absichern:
   Required Reviewer, Deployment nur von exakt `main`, Admin-Bypass aus.
   Danach den bestehenden `newsletter-worker`-Deploy nach Runbook A1b/A4/D2
   freigeben und den Build-Stempel sowie das authentifizierte Betriebsbild
   erneut messen.
5. Erst danach den vollständigen Sicherheits-Wache-Live-Lauf auf `main`
   durchführen. Nur wenn F-01, Worker und Abschlussprüfung komplett grün sind,
   ist #972 nach dem vorhandenen Vertrag schließbar.

Keine Cloudflare-Regel, DNS-Einstellung, GitHub-Variable, Secret oder
Environment-Policy wurde geändert; kein Worker wurde deployt. #972 wurde weder
kommentiert noch geschlossen.

## Verifikation dieser Änderung

- `python3 -m unittest scripts.tests.test_live_selbstheilung -v` — 13 Tests
  erfolgreich, darunter neue CLI-Probe für die Warnungssemantik.
- `npm run test:sicherheit` — erfolgreich; die bestehenden Offline-Wachen,
  Gegenproben und Vertrags-Tests liefen durch (ein bestehender Test übersprungen).
- `python3 -m py_compile scripts/live_selbstheilung.py scripts/tests/test_live_selbstheilung.py`
  und `git diff --check` — erfolgreich.
- `python3 scripts/integrity_guard.py --gate` — 55 versiegelte Dateien
  unverändert; `python3 scripts/trigger_wache.py --check` — 103 Workflows,
  keine Befunde.
- `governance_contract.py --quick` konnte in dieser Sandbox nicht starten,
  weil das optionale Python-Paket `PyYAML` nicht installiert ist. Es wurde
  deshalb kein grüner Governance-Vertrag behauptet.
- Diese Offline-Ergebnisse sind kein neuer Live-Produktionsnachweis.

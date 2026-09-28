# 🚀 Blogautomatik-Optimierung – Traffic, Reichweite, erste Provisionen

**Datum:** 28.09.2026 · **Auftrag:** „Optimiere die Blogautomatik so, dass ich so
wenig wie möglich manuell tun muss, Traffic und Reichweite erhöhe und möglichst
bald erste Provisionen verdiene – auf Premium-Niveau einer Profi-Agentur."

---

## 1. Befund in einem Satz

Die Maschine (Content-Engine, 60+ Wachen, Newsletter-Eigenbetrieb, Social-Autopilot)
arbeitet bereits auf Agentur-Niveau – aber **die provisionsstärkste Saison des
Jahres lief ohne Kampagnen-Schalter**, die Rechtschreib-Wache lag unaktiviert in
der Schublade, und der Pinterest-Wiederanlauf war über vier Runbooks verstreut.

## 2. Was bereits auf Profi-Niveau läuft (nicht angetastet)

| Bereich | Zustand |
|---|---|
| Content-Produktion | Content-Engine v2: Mo/Mi/Fr, 2–3 Artikel/Tag, Multi-Fallback, nie ein Tag ohne Artikel |
| Qualität | 1096 Unit-Tests grün, Integritäts-Lock, Offenlegung artikelgenau, Faktenfrische mit Belegketten |
| SEO | Wöchentliches Audit, LSI-Keywords, interne Verlinkung, IndexNow, JSON-LD, CWV-Wache |
| Newsletter | Eigenbetrieb (Cloudflare-Worker + Resend), Di/Fr, Kadenz-Wache holt versäumte Läufe nach |
| Social | Mastodon aktiv (Token live verifiziert), 14-Tage-Plan, Kanal-Gates |
| Umsatz-Messung | Trichter aufgebaut (Views → Klicks → Antrag → Abschluss), ehrlich bei Messlücken |

## 3. Was ich geändert habe (heute, per PR)

### 3.1 Saison-Kampagne „Herbst-Energiewechsel 2026" AKTIVIERT 🔴→🟢

**Der größte einzelne Hebel auf erste Provisionen.** Okt/Nov ist die
Wechselsaison: Strom- und Gas-Nachzahlungen treffen ein, Haushalte vergleichen –
und CHECK24s Energie-Kategorien gehören zu den höchstvergüteten Abschlüssen.

- `data/campaigns.yaml`: `status: paused → active`
- Kampagnen-CTA **„Jetzt Strom- & Gaspreise vergleichen"** fließt ab sofort in
  jeden neuen Strom/Gas-Artikel (via `agc_context` → `claude_writer`)
- Die 4 Kalender-Slots ab 30.09. sind jetzt saisonale Kauf-Themen (statt z. B.
  „Strompreis-Anpassung im **Sommer** ausnutzen" am 05.10. – saisonal schief)
- **Wirkt automatisch** – der AGC-Autopilot (täglich 05:45 MESZ) baut den
  Kalender neu, die Content-Engine übernimmt Mo/Mi/Fr ohne jeden Handgriff

### 3.2 Drei Nachfolge-Kampagnen angelegt (starten von selbst)

Damit die Maschine im November/Dezember weiter Gas gibt, **ohne dass Frank
aktivieren muss** (Zeitfenster steuert den Start):

| Kampagne | Fenster | Pillar | Hochpunkt |
|---|---|---|---|
| `winter-energie-2026-27` | 01.11.–31.12. | strom-sparen | Grundversorgung raus, Ökostrom-Wechsel |
| `kfz-wechselsaison-2027` | 01.11.–15.12. | versicherungen | Kfz-Kündigung zum 1.1. (höchstintente Versicherungs-SEO-Zeit im DACH-Raum) |
| `black-friday-tarife-2026` | 17.11.–02.12. | internet-dsl | Black-Friday-DSL-Deals |

### 3.3 Bugfix: Kampagnen-Hints durcheinander (Duplikat-Schutz)

`campaign_manager._pick_topic` gab **jedem** Kalender-Slot denselben ersten
Kampagnen-Hint (`for h, c in hints: return …`). Eine aktive Kampagne hätte den
Monatskalender mit ein und demselben Thema geflutet. Jetzt:

- Hints zyklisch, jeder nur **einmal pro Lauf**
- Hints mit bereits existierendem Artikel werden **übersprungen** (Bestands-Abgleich)
- Selbsttest erweitert: Drei eingefrorene Verträge (Hint-Rotation, Bestands-Skip,
  keine Themen-Duplikate im Kalender) – der alte Code scheitert daran sichtbar

### 3.4 Saison-Themenpool: +12 hochintente Themen (Okt–Dez)

`data/topics.yaml`: 187 Themen. Neu sind die zwölf Themen mit Kaufabsicht, die im
Herbst/Winter tatsächlich gesucht werden – alle gegen Bestand **und** Pool
geprüft (keine Duplikate), mit Keywords und thematisch korrekten CHECK24-Deep-Links:

- **Strom/Gas:** Nachzahlung vermeiden · Abschläge winterfest · Strompreis-Herbst-Entscheidung · Grundversorgung raus · Ökostrom wechseln
- **Versicherungen:** Kfz-Wechselfristen zum 1.1. · Jahresrückblick Policen im Dezember
- **Tarife:** Black-Friday-DSL-Deals · Handy-Wechselbonus
- **Konto/Budget:** Weihnachtsgeld einsetzen · Weihnachtsbudget · Geld-Vorsätze 2027

### 3.5 ZEIT-Rechtschreib-Wache aktiviert (und dabei einen Bug gefunden)

Die fertige Vorlage lag seit heute Morgen in `workflow-ready/` und wartete auf
ein manuelles Kopieren durch einen Admin. Ich habe sie aktiviert
(`.github/workflows/zeit-rechtschreibung.yml`, montags 04:35 UTC) – und dabei
entdeckt: **Die Vorlage hätte nie gelaufen.** Der Schritt-Name
`Wachen-Lauf (Modus-Automatik: Premium → offline)` enthielt einen unquoteten
Doppelpunkt – ungültiges YAML, GitHub Actions hätte den Workflow abgelehnt.
Behoben in Vorlage **und** aktiver Kopie; Provider-Kette bleibt wie konzipiert
(Premium → offline, nie `--oeffentlich`, Kostendeckel unangetastet).

### 3.6 Pinterest-Restart: vier Handgriffe → ein geführter Lauf

Neuer Workflow **„Pinterest-Restart (geführt)"** (`.github/workflows/pinterest-restart.yml`):
Nach der Domain-Freigabe durch Pinterest genügt **ein** Lauf mit Bestätigungs-Haken
(+ optional OAuth-Code im selben Dialog). Der Lauf:

1. hebt die Domain-Notbremse belegt auf (`spam_guard --domain-unblock`, commit),
2. prüft die Token-Lage, zeigt bei totem Token die Autorisierungs-URL direkt in
   der Zusammenfassung (oder tauscht den Code gleich mit),
3. baut einen Pin-Plan im Trockenlauf (kein Pin-Burst – das Pinning läuft
   ohnehin über RSS-Auto-Publish),
4. dokumentiert alles als Kommentar in Issue #448 (Audit-Trail).

Fail-closed: ohne Haken `bestaetigt` passiert nichts.

## 4. Was nur Frank tun kann – priorisierte 5-Minuten-Liste 🎯

Die Maschine kann keine Konten authorisieren und keine Formulare bei Pinterest
absenden. Das hier ist die **komplette** Restliste, nach Wirkung sortiert –
alles andere erledigt die Automatik:

| # | Aktion | Aufwand | Wirkung auf Provisionen |
|---|---|---|---|
| 1 | **Pinterest-Formular „Link gesperrt" absenden** (Vorlage: `docs/PINTEREST-SPIELBUCH.md`), danach Pinterest-Restart-Workflow starten | ~10 Min + Wartezeit | 🔴 Hoch – Pinterest war der geplante Haupt-Traffic-Kanal (Themenpool ist darauf abgestimmt); jede Woche Sperre ≈ eine Woche weniger Reichweite |
| 2 | **Bluesky-Konto + 2 Secrets** (`BLUESKY_IDENTIFIER`, `BLUESKY_APP_PASSWORD` – Anleitung `docs/ANLEITUNG-SOCIAL-AUTOPILOT.md`) | ~5 Min | 🟠 Mittel – Social-Autopilot erkennt den Kanal automatisch, kostenloser Wachstumskanal, kein weiterer Wartungsaufwand |
| 3 | **Google Search Console**: Property `franksfinanzcheck.de` verifizieren + `sitemap.xml` einreichen (einmalig) | ~5 Min | 🟠 Mittel – beschleunigt Indexierung der ~2–3 neuen Artikel pro Publikationstag messbar |
| 4 | **CHECK24-Testklick-SOP** einmal durchziehen (`docs/UMSATZ-MESSUNG-PREMIUM.md`, Kap. 3) | ~5 Min | 🟡 Nachweis, dass SubID-Attribution (Artikel → Provision) sauber läuft – die Voraussetzung, um zu wissen, WELCHER Artikel Geld verdient |
| 5 | Optional: `UMAMI_API_TOKEN` + `umami_api_import_enabled: true` (Umami Pro) oder AWIN-Seiten, falls je genutzt | ~10 Min | 🟡 Schaltet den Trichter von „Dashboard-only" auf vollautomatische Kennzahlen (EPC, CTR je Platzierung) |

Offene Tickets, die das schon einfordern: #448 (Pinterest-Domain), #246
(Pinterest-Token – **erst nach** Domain-Freigabe sinnvoll, der Restart-Workflow
bündelt beides).

## 5. Erwartete Wirkung & wie sie messbar wird

- **Provisionen:** Wechselsaison-Artikel mit Kampagnen-CTA + Deep-Links auf die
  Converter-Kategorien; Kfz- und Black-Friday-Fenster decken Q4 komplett ab.
  Erste Klicks sind im Umami-Dashboard sofort sichtbar; Abschlüsse im
  CHECK24-Partnerportal (SubID = Artikel-Slug).
- **Traffic:** 12 saisonale Suchthemen + korrigierter Kalender treffen die
  Nachfrage Okt–Dez; GSC + RSS-Publish (sobald Pinterest frei) beschleunigen
  die Indizierung; Bluesky wäre Kanal Nr. 3.
- **Reichweite:** Newsletter (Di/Fr) und Mastodon laufen unverändert weiter;
  die Content-Kadenz bleibt bewusst bei Mo/Mi/Fr, 2–3 Artikeln (Scaled-Content-
  Schutz der Dauervorgabe – daran habe ich nichts gedreht).

## 6. Verträge, die ich eingehalten habe

- Keine Änderung an Dauervorgaben (Kadenz, AUTO_PUBLISH-Logik, Kosten-Regeln)
- Keine zweite Zahl/kein zweiter Besitz für Kampagnen-Ziele angelegt
- Alle Selbsttests erweitert (nicht geschwächt): `campaign_manager`, `autopilot`,
  1096 Unit-Tests grün
- Kampagnen-Hints gegen Bestand geprüft – die Maschine plant nie einen Artikel,
  dessen Titel schon existiert
- Maschinen-Artefakte (Integritäts-Lock) nicht angefasst: Lock deckt nur
  `custom.css`, `brand_lock.yaml`, `hugo.toml` – keine meiner Dateien

---

_Erstellt in der Arena-Session „Blogautomatik-Optimierung" am 28.09.2026.
Änderungen kommen per PR auf `main` – nach Merge wirken sie automatisch mit dem
nächsten AGC-Autopilot-Lauf (05:45 MESZ)._

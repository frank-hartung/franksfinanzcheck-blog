# Umami-Entfernung: Dauerheilung der Anbindung ohne Dienst (#806)

**Auftrag (Frank, 19.10.2026):** „Governance-Report: Redaktionelle & technische Handlungsfelder #806 – Bitte Umami dauerhaft auf Highend-Level einer Profi-Agentur im gesamten Blog entfernen. Bitte dauerhaft auf Highend-Level einer Profi-Agentur beheben.“

**Vorgeschichte:** Am 10.10.2026 beanstandete der Datenschutz-Audit die Fremdmessung (`DATENSCHUTZ-AUDIT-PREMIUM-2026-10-10.md`). Am 11.10.2026 wurden Tracking-Skript und Einwilligungs-Banner entfernt (`DATENSCHUTZ-UMSETZUNG-UND-FREIGABE-2026-10-10.md`). Dieser Vorgang behandelt die **Ursache** dahinter: Warum stand Umami eine Woche später noch in Workflows, Skripten, Daten, Doku und im Governance-Issue – und wie verhindern wir, dass es zurückkehrt?

**Prüfmaßstab:** Kein Dienstname in lebenden Dateien, kein Anbindungs-Merkmal im Quelltext und im ausgelieferten Baum, die Messkette bleibt ehrlich („unbekannt“ ≠ 0, Funnel grün), alle Gates und Tests grün, die Rückkehr technisch gesperrt.

---

## Kurzfassung

Das Frontend war sauber. Die **Anbindung** lebte weiter und hat jede Woche eine Messung vorgetäuscht, die es nicht gab:

- zwei Import-Skripte (941 Zeilen), je zwei Workflow-Schritte in zwei Workflows, ein Secret mit Live-Probe, vier Datenstände, eine Dashboard-Export-Brücke;
- ein Umsatz-Trichter, der behauptete „Klicks und Besuche werden im Umami-Dashboard erfasst“ – falsch, seit dem 11.10. wird nichts erfasst;
- zwei Info-Zeilen im Governance-Issue (#806: „Umami-Datenimport“, „Umami-Seitenaufrufe (Trichter-Nenner)“, beide „Datenlage offen“) und eine Runbook-Zeile, die zu `UMAMI_API_TOKEN` riet.

Alles ist entfernt, die Messkette läuft quellenehrlich ohne Umami, und eine neue Wache sperrt die Rückkehr.

| Kennzahl | vorher | nachher |
|---|---|---|
| Dateien, die „Umami“ nennen | 98 | 32 – davon 21 Historie (datierte Berichte, Archiv, Ledger, Patch-Archiv), 10 begründete Ausnahmen (Sperre, ihre Tests, Runbook, Regelwerk, Absenz-Tests, Sperrliste, 2 Siegel-Altlasten) und die Akte des Siegels (steht im Commit-Betreff dieses Vorgangs) |
| Skripte/Daten/Doku der Anbindung | 2 Skripte, 4 Datenstände, 1 Anleitung, 1 Konfig-Datei | 0 |
| Umami-Schritte in Workflows | 4 + Preflight + Secret-Env + Commit-Listen | 0 |
| Gate-Kennungen / Vertrags-Einträge / Secret-Registrierung | 2 / 4 / 1 (samt Live-Probe) | 0 / 0 / 0 |
| Ausgelieferter Baum (Hugo-Bau, 2.394 Dateien) | 1 Fund: `premium/ff-feedback.js` trug den Namen in einem Kommentar zu jedem Besucher | 0 Funde; **eine** Datei weicht ab (genau dieser Kommentar), alle übrigen 2.393 sind byte-gleich |
| Umami-Zeilen im Governance-Issue | 2 Info-Zeilen + Runbook-Zeile | 0 (Gate-Simulation, siehe unten) |
| Rückkehr technisch gesperrt | nein | ja: Vertrag C40, Regressionstest, `npm run test:fremdmessung` |
| Umsatz-Funnel | GREEN, „Umami Free aktiv“ (sachlich falsch) | GREEN, ehrliche Betriebsgrenzen, „unbekannt“ ≠ 0 |

---

## Ursachenanalyse

### Ursache 1: Die Entfernung des Frontends hat die Anbindung nicht mitgenommen

Am 11.10. wurde entfernt, was ein Besucher sieht. Was Betrieb und Berichte betrifft, blieb stehen: Skripte, die nichts mehr abrufen konnten, Workflow-Schritte, die „übersprungen“ meldeten, ein Secret, dessen Live-Probe „bewusst deaktiviert“ meldete. Jeder dieser Reste war für sich harmlos – zusammen erzeugten sie Info-Zeilen, die nie verschwanden, und ein Bild von Messung, wo keine war.

### Ursache 2: Es gab keinen Ort, an dem „Anbindung ohne Dienst“ auffällt

Kein Gate prüfte, ob eine Messquelle noch existiert. Alle Wachen setzen voraus, dass ein Dienst da ist, und melden „Datenlage offen“, wenn er schweigt. Ein Dienst, der **nie wieder antworten wird**, ist für sie ein dauerhafter Normalzustand.

### Ursache 3: Der Trichter machte aus „kein Dienst“ eine Aussage über die Welt

`revenue_funnel.py` schrieb „Klicks und Besuche werden im Umami-Dashboard erfasst“, sobald der API-Import abgeschaltet war – ohne zu prüfen, ob irgendwo erfasst wird. Die Hausregel „unbekannt ≠ 0“ wurde eingehalten, die **Begründung** dazu war erfunden.

---

## Was geändert wurde

### 1. Entfernt (restlos)

- **Skripte/Daten/Doku:** `scripts/umami_clicks.py`, `scripts/umami_views.py`, `data/umami_clicks.json`, `data/umami_clicks.meta.json`, `data/umami_views.meta.json`, `docs/ANLEITUNG-UMAMI-ANALYTICS.md`, `data/monetization.yaml` (enthielt nur noch den Umami-Schalter und zwei von niemandem gelesene Schlüssel).
- **Workflows:** `premium-governance.yml` (beide Umami-Schritte, Preflight-Einträge, `UMAMI_API_TOKEN`-Env, Commit-Liste), `revenue-import.yml` (Umami-Schritte, Dashboard-Brücke, Secret, Commit-Liste). Es wurden keine Rechte, Actions oder Trigger verändert.
- **Gate/Vertrag/Wachen:** Gate-Kennungen `umami` und `umami-views`, Vertrags-Signaturen und vertragliches Minimum, Secret `UMAMI_API_TOKEN` samt Live-Probe (`secrets_age_guard.py`), Sonderfälle im Cockpit, toter Code in `research_engine.py`.
- **Trichter:** Besuchs-Kennzahlen (Outbound-CTR, Provision je 100 Besuche) und `cta_click`-Platzierungen entfallen. Es gibt keine Besucherzählung; eine Kennzahl ohne Quelle wäre für immer „unbekannt“, also Dekoration. `offline_import.py` ist nur noch der Provisions-Import (kein Messstand-/Dashboard-Export mehr).

### 2. Quellenehrlich neu (Messkette ohne Umami)

| Zustand | Funnel zeigt | Ampel |
|---|---|---|
| Klickzähler aus (`aktiv: false` in `data/klickmessung.yaml`) | „unbekannt“ + INFO `operating_boundary` | 🟢 |
| Provisions-Tabelle noch nie befüllt | „unbekannt“ + INFO `operating_boundary` | 🟢 |
| Zähler an, Import frisch (auch 0 Klicks) | echte Zahlen, echte Null | 🟢 |
| Zähler an, Import fehlt / nicht konfiguriert / Fehler / > 14 Tage | `funnel_gap` | 🟠 |
| Tabelle befüllt, Import > 14 Tage alt | `funnel_gap` | 🟠 |

Ein ausgeschalteter Zähler zählt auch alte Zeilen nicht (ausgeschaltet heißt nicht gemessen). Der Schalter ist derselbe, den `click_chain_guard.py` und der `/go/`-Generator lesen (Test belegt die Gleichheit). Scorecard, `click_attribution.py` und die Runbook-Zeile im Governance-Issue folgen derselben Quelle. Der Design-Labor-Wert `cta_ohne_umami` heißt jetzt `cta_ohne_klickmarke` (er maß längst `data-klick`); die zwei Messprotokolle tragen nur den umbenannten Schlüssel, die Werte sind unverändert.

### 3. Die Sperre (dauerhaft)

`scripts/fremdmessung_sperre.py` liest den Quelltext (und mit `--public` den gebauten Baum), ohne etwas auszuführen:

| Klasse | Meldet |
|---|---|
| F1-DATEI | Dateiname trägt den Dienstnamen (Code, Daten, Doku – ein Foto nicht) |
| F2-ANBINDUNG | Skript-Host, `data-…-event`, `data-website-id` (auch bei selbst gehosteter Instanz), JS-API, Secret/Variable, Konfig-Schlüssel – überall, auch in `content/` und `data/` |
| F3-ERWAEHNUNG | der Name in lebenden technischen Dateien |
| F4-GEBAUT | Spur im ausgelieferten Baum (Anbindung überall, der Name in Skripten und Stilen) |
| F5-AUSNAHME | unbegründete, unbekannte oder **veraltete** Ausnahme |

Gestaltungsentscheidungen: Das Wort als **Geschmacksrichtung** in Artikeln (`content/`, `data/`, gebautes Artikel-HTML) ist erlaubt – ein Kochtipp im Sparratgeber legt das Gate nicht lahm; nur die Anbindungs-Merkmale bleiben dort verboten. **Historie** (datierte Berichte, `docs/archiv/`, Patch-Archiv, Ledger `data/**/*.jsonl`) wird nicht umgeschrieben. **Generierte Momentaufnahmen** (`COCKPIT.md`, `data/cockpit_status.json`, `data/governance_status.json`) werden nicht gescannt: Ihre Ursache läge im Code, den die Wache prüft; ein Lauf-Rückstand soll `main` nach einem Merge-Konflikt nicht grundlos rot färben. Jede Ausnahme einzeln, mit Grund, und sie **altert**: Deckt sie keinen Fund mehr, meldet F5 sie.

**Verdrahtung ohne Workflow-Änderung** (Haus-Muster „kein Workflow-Patch“):

- **C40 im Governance-Vertrag** – Wache vorhanden, im vertraglichen Minimum (C6), Regressionstest da, Qualitäts-Gate ruft den Vertrag, und der Live-Lauf über den echten Quelltext ist still. Läuft mit `link-check.yml` auf jeden Push und jede PR (kein Pfadfilter), täglich und montags in der Governance. Im Selbsttest des Vertrags in beide Richtungen bewiesen (sechs Sabotageproben).
- **Regressionstest** `test_fremdmessung_sperre.py` (26 Tests) – Sabotageproben je Merkmal, Quelltext, **gebauter Baum** (die PR-Regression baut vorher mit Hugo), Entfernung an den konkreten Stellen, Verdrahtung.
- `npm run test:fremdmessung`, Dauervorgabe in `CLAUDE.md`, Runbook `docs/ANLEITUNG-FREMDMESSUNG-SPERRE.md`, Vertragsdoku `docs/GOVERNANCE-KONTRAKT.md` neu erzeugt.

Dass die Sperre wirkt, hat sie noch während der Arbeit selbst gezeigt: Sie fand eine Lücke im eigenen Selbsttest (ein selbst gehostetes Snippet trägt `data-website-id`, aber nicht das Wort „umami“) und beanstandete einen meiner Sabotage-Fixtures im Vertrag.

---

## Verifikation

| Prüfung | Ergebnis |
|---|---|
| Hugo-Bau vorher/nachher, `diff -rq` über 2.394 Dateien | genau 1 Datei weicht ab (`premium/ff-feedback.js`, Kommentar) |
| Sperre über Quelltext, über `public/` (nachher) | 0 Funde; vorher 1 Fund im Bau |
| Governance-Vertrag | 38 Regeln inkl. C40, `--selftest` C1–C40 grün |
| Selbsttests (18 Skripte inkl. Funnel, Offline-Import, Gate, Scorecard, Secrets, Cockpit, Klick-Kette, Affiliate, Integrität, Robustheit, Newsletter-QA) | alle grün; Funnel zusätzlich unter der um 1.461 Tage vorgestellten Uhr |
| Gates gegen den neuen Bau: Klick-Kette, Affiliate-Integrität, Layout-Audit, Robustheits-Gate, Design-Gate | alle grün (Design-Gate mit den umbenannten Protokollen) |
| Governance-Simulation (Reset → Messschritte → Entscheidung), erzeugter Issue-Body | 0 Umami-Treffer, Funnel 🟢, kein Umami-Runbook mehr |
| Python-Suite | 3.424 Tests (Baseline 3.385). Rot bleiben genau die **zwei Fälle, die schon vor dieser Änderung rot waren**: `test_inhalts_register…test_live_wache_ist_gruen` (Artikel `2026-10-12-haushaltskosten…`: kein Rechner-Link) und `test_weiterleitungen…test_snapshot_ist_aktuell` (Weiterleitung für `/posts/2026-08-12-dein-haus-sicher-schuetzen…`). Beide sind redaktionell und unabhängig von Umami. |
| Integritäts-Siegel | Gate grün: 50 Kerndateien entsprechen dem signierten Stand; 59 Integritätstests grün |
| JS-Syntax aller geänderten Dateien (`node --check`) | grün |

---

## Entscheidungen und offene Punkte (für dich)

1. **Zwei Kommentar-Altlasten warten auf deine Signatur.** `layouts/_default/_markup/render-link.html` (zwei Kommentarzeilen) und `scripts/check24_links.yaml` (eine) nennen Umami noch in Kommentaren. Beide Dateien sind **KRITISCH gesiegelt**; jede Änderung – auch an einem Kommentar – verlangt die menschliche Neu-Signatur (`integrity_guard.py --set-current`). Das habe ich nicht stellvertretend getan. Sie sind als begründete Ausnahme in der Sperre geführt; beim nächsten Siegel-Termin bereinigen, signieren und die zwei Einträge löschen (F5 erinnert daran). Der Bau enthält sie nicht (Hugo-Kommentare werden nicht ausgeliefert). Die Formulierungen stehen im Runbook.
2. **Außerhalb des Repos (kann ich nicht sehen):** Falls das GitHub-Secret `UMAMI_API_TOKEN` oder die Variable `UMAMI_API_BASE` je gesetzt war: unter *Settings → Secrets and variables → Actions* löschen. Das Umami-Cloud-Konto samt Website bei Umami beenden. Mein Zugang darf Secrets nicht auflisten (HTTP 403) – ich kann also weder bestätigen noch ausschließen, dass eines existiert.
3. **Fünf FEST-Dateien wurden neu gesiegelt** (nur Kommentare): `affiliate_anchor_attrs.html`, `extend_footer.html`, `pillar/list.html`, `einspartabelle.html`, `affiliate_integrity_gate.py`. Der Repo-Test `test_ausgelieferter_baum_passt_zum_siegel` verlangt die Neu-Signatur im selben PR. Ich habe `integrity_guard.py --heal` benutzt (nur FEST, nur Committetes, byte-gleich; kein KRITISCH-Hash berührt). Es ist ein eigener Commit (`chore(integrity)`), einzeln rückholbar: Ohne ihn siegelt die Content-Engine beim nächsten Lauf selbst, das PR-Gate bliebe bis dahin rot.
4. **Alles gehört in einen Merge, auch die Workflow-Dateien.** Die Skripte `umami_*.py` sind gelöscht: Würde nur der Rest übernommen, scheiterte der Preflight von `revenue-import.yml` und `premium-governance.yml` am ersten Schritt. Workflow-Dateien dürfen laut CLAUDE.md nur mit einem vollwertigen Token gepusht werden (Agenten-Tokens haben keine `workflows`-Permission, README „Known Issue“).
5. **Zum Issue #806:** Er enthält zusätzlich den **Lesbarkeits-Befund** (`2026-10-19-urlaubskasse-clever-aufbessern` Flesch 54,2 und `2026-10-16-dns-server-aendern-fuer-schnelleres-internet` Flesch 54,9). Das sind redaktionelle Entwürfe und nicht Teil dieser Entfernung; ich habe sie nicht angefasst. Deshalb steht in den Commits `Refs #806`, nicht `Closes #806`: Ein `Closes` würde ein Issue schließen, dessen Befund offen ist, und der Montags-Lauf legte ein neues an. Der Issue-Body wird beim nächsten Governance-Lauf (Mo 26.10.) ohne die Umami-Zeilen neu geschrieben (`--reset` löscht vorher den Ledger, `changed` ist im CI deshalb praktisch immer wahr). Wer ihn früher aktualisieren will: `workflow_dispatch` auf `Premium-Governance`.
6. **Doku und Code widersprachen sich:** Die alte Doku (`UMSATZ-MESSUNG-PREMIUM.md` 5a) versprach „Laut statt still“ – AMBER, wenn keine Messbrücke misst. Der echte Lauf war aber GREEN (der Funnel stufte alle Quellen bei abgeschalteter API auf „deaktiviert“). Ich habe die Doku an das tatsächlich gelaufene Verhalten angeglichen (nie befüllte Tabelle = INFO, grün). Wer das „laute“ Verhalten will: eine Zeile in `revenue_funnel.lage()`.
7. **Nicht angefasst, aber auffällig:**
   - `revenue-import.yml` läuft 2×/Tag, obwohl sich seine Eingaben nur bei manuellem Import ändern (und künftig mit dem Klickzähler). Kandidat für einen Rückbau auf wöchentlich; `alert-on-failure.yml` überwacht ihn namentlich, deshalb habe ich ihn nicht verändert.
   - `layout_browser_check.js`: `TOLERANCE.headchildren = 2` stammte teils vom Umami-Loader. Der Grund ist weg, aber der Hover-Prefetch (`ff-premium.js`) hängt weiterhin Link-Knoten in den `<head>`. Ob 1 reicht, belegt nur eine Browser-Messung, die in dieser Umgebung nicht lief. Kommentar ist korrigiert, die Zahl nicht.
   - Die Wache selbst steht (anders als `wachen_vertrag.py`) nicht im Siegel. Ob sie dorthin soll, ist deine Entscheidung.
   - `data/revenue_funnel.json` trägt noch das alte Schema, bis `revenue-import.yml` das nächste Mal läuft (täglich). Ich habe es nicht von Hand erzeugt (Bot-Datei).

---

## Betrieb

```bash
npm run test:fremdmessung                                # Selbsttest + Quelltext + Regressionstests
python3 scripts/fremdmessung_sperre.py --public public/  # zusätzlich den gebauten Baum (erst `hugo --minify`)
python3 scripts/revenue_funnel.py --print                # Funnel auf stdout (schreibt keine Dateien)
npm run test:mess                                        # Messkette: Selbsttests + Regressionstests
```

Runbook der Sperre: `docs/ANLEITUNG-FREMDMESSUNG-SPERRE.md` · Messkette: `docs/UMSATZ-MESSUNG-PREMIUM.md` · Dauervorgabe: `CLAUDE.md`, Abschnitt „Keine Fremdmessung“.

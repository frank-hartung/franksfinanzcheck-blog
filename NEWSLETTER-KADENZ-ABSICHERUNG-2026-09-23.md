# Newsletter-Betriebsabsicherung – Report 23.09.2026

**Anlass:** Meldung „Run failed: Newsletter-Daily (Capture-Wache + Digest) –
main (988424d)“ — das ist **Lauf #14** (Run 35807422071, 01:42 UTC), dessen
Versand-Kette in `NEWSLETTER-VERSAND-REPARATUR-2026-09-23.md` bereits
repariert war (PR #356, 02:01 UTC gemergt). Der Auftrag lautete: **dauerhaft
auf Premium-Level beheben** – also nicht den einen Lauf grün malen, sondern
die Klasse schließen.

**Audit-Ergebnis nach der Reparatur (ehrlich):** Die Reparatur selbst war
vollständig und ist grün – aber sie hatte **nie einen CI-Lauf gesehen** (der
letzte Lauf des Workflows ist #14 um 01:43, der Merge kam um 02:01) und das
Umfeld hatte zwei Lücken, die den nächsten Vorfall nur verschoben hätten.
Dieses Audit prüft die Reparatur und schließt die Lücken drum herum.

---

## 1. Befunde (das Umfeld der Reparatur)

### B1 – Der Workflow, der E-Mails verschickt, war beim Fehler-Alerting NICHT angemeldet

`alert-on-failure.yml` beobachtet 39 Workflows namentlich –
`Newsletter-Daily (Capture-Wache + Digest)` fehlte. Lauf #14 ging rot,
ohne dass ein Issue entstand: genau der Workflow, der die Kundenzustellung
trägt, war die blende. Dieselbe Klasse wie die „PREM-AUDIT: war blind“-Nachträge
der letzten Wochen, nur am empfindlichsten Ende.

**Behoben:** Beide Newsletter-Workflows stehen jetzt in der Wacht-Liste
(`Newsletter-Daily`, `Newsletter-Kadenz-Wache`). Fehlt der Versand auf main,
entsteht ab sofort ein Issue mit Diagnose – automatisch, ohne dass jemand
die Actions-Seite aufklappen muss.

### B2 – Der planmäßige Cron fiel STILL aus, und niemand durfte es merken

Der 05:05-UTC-Cron des 23.09. (Werktag!) lief **nie** – kein roter Lauf,
keine Meldung, nichts. Am Vortag kam er erst ~10:05 UTC. GitHub verwirft
oder verschiebt `schedule`-Ereignisse unter Last; ein Lauf, der nie startet,
kann nicht rot werden und erzeugt kein Alerting-Ereignis. Ein täglicher
Newsletter, der still nicht läuft, ist die gefährlichste Fehlerart des
ganzen Systems: „ausgefallen ist nicht bestanden“ – diesmal für Workflows.

**Behoben:** Neue **Newsletter-Kadenz-Wache** (`newsletter-cadence.yml` +
`scripts/newsletter_cadence.py`): zählt jeden Werktag ~08:11 UTC nach, ob
seit 04:00 UTC überhaupt EIN Laufversuch existiert. Fehlt jeder Versuch,
holt sie den Lauf mit **`planmaessig=true`** nach – exakt die Freigabestufe
des verpassten Crons, nicht mehr (der Newsletter-Daily bleibt dreifach
verriegelt). Unfälle sind ausgeschlossen:

* Kommt der verschobene Cron doch noch, findet er einen leeren Digest vor –
  „nichts zu senden“, keine zweite Kampagne (Duplikatschutz des Skripts).
* Ein **fehlergeschlagener** Lauf ist bewusst KEIN Fall der Wache: er ist
  laut (Fehler-Alerting, B1), und ein automatischer zweiter Sendeversuch
  wäre eine Betreiber-Entscheidung, nicht eine Automatik.
* Die Wache steht selbst in der Wacht-Liste (B1) und ihr Selbsttest im
  Governance-Vertrag (GUARDS, C6) – sie kann nicht still veralten.

Der Trockenlauf der Wache erkannte den echten Vorfall dieses Tages sofort:
„Kein einziger Laufversuch seit 2026-09-23T04:00:00Z“.

### B3 – Die workflow_dispatch-Eingaben litten an Schadensvektoren

`test_adresse` (Freitext!) wurde als `${{ }}`-Interpolation direkt in den
Shell-Block eingesetzt – ein Eingabefeld als Code. Außerdem hätte ein
Leerzeichen in der Adresse die Argumente gesplittet.

**Behoben:** Beide Eingaben (`tage`, `test_adresse`) laufen als ENV-Variablen
in Anführungszeichen – Daten, nie Code. Nachgewiesen mit einer gezielten
Eingabe `a@b.de"; curl evil; #` und `1; rm -rf …`: sie bleibt stumm als
Argument. Argument-Form aller vier Freigabe-Varianten im Beweisstand (§ 3).

### B4 – Der Testversand konnte an der leeren Liste scheitern, für die er die Probe sein soll

Der dokumentierte Probeweg ist: *erst* `test_adresse` (Schritt 6a), *dann*
`live` – sobald die Liste Abonnenten hat. Wer aber `live` **und**
`test_adresse` zusammen an gab (oder die Kadenz-Wache mit Testadresse
lief), bekam die Vorprüfung mit `live=True` – und die bricht bei
**0 Abonnenten** ab. Der Testversand, der genau dafür da ist, die Kette
VOR den ersten Abonnenten zu beweisen, war an genau diesem Zustand
gescheitert (der Selbsttest prüfte `vorflug` isoliert – die Verdrahtung in
`versende()` nicht).

**Behoben:** `versende()` übergibt `live=False`, wenn eine Testadresse
gesetzt ist (sendTest trifft genau eine Adresse, nie die Liste).
Existenz-Prüfungen (Absender da? verifiziert? Liste vorhanden?) bleiben
auch für den Testversand an. Selbsttest-Fall 20b + Unit-Test frieren die
Verdrahtung ein.

### B5 – Nach dem erfolgreichen Versand konnte der Lauf die Unwahrheit melden

Scheiterte das Status-Schreiben (`data/newsletter_state.json`) NACH dem
erfolgreichen `sendNow`, meldete der Lauf rot – und die Annotation behauptete
„es ist nichts versandt“, während der Empfänger die Mail in der Hand hielt.

**Behoben:** Der Status-Schreibvorgang ist verriegelt und wird **nachgelesen**
(gelesen, was geschrieben wurde; trägt der Status die Kampagnen-ID nicht,
zählt er als nicht geschrieben). Im Fehlerfall lautet der Befund
„**VERSAND ERFOLGT** … Doppelungsgefahr“ mit rc 1, und die Annotation des
Workflows unterscheidet die beiden Wahrheiten („VERSAND IST RAUS, Status
unvollständig“ vs. „es ist nichts versandt“). Selbsttest-Fall 27 + Unit-Test.

### B6 – Reparatur nie in CI bewiesen (Beweispflicht nachgeholt)

PR #356 war um 02:01 gemergt, der letzte Workflow-Lauf war 01:43 – die
Reparatur lief nie gegen echte CI. **Erledigt durch diesen Auftrag:** alle
Beweise (§ 3) laufen gegen den gemergten Stand, und der erste Absicherungslauf
nach dem Merge wird den Workflow-Körper selbst end-to-end zeigen.

---

## 2. Was diese Absicherung NICHT ist

* **Kein Freischalten, kein neuer Versandzwang:** Der erste echte Versand
  bleibt an die Checkliste gebunden (Absender verifizieren, Liste prüfen –
  `docs/FREISCHALTUNG-NEWSLETTER-CHECKLISTE.md`). Die Kadenz-Wache wiederholt
  nur den planmäßigen Lauf, den der Cron ohnehin ausgeführt hätte.
* **Kein Auto-Retry nach rotem Lauf:** Ein fehlgeschlagener Versand wird
  gemeldet, nicht wiederholt. Der Versand ist fail-closed verriegelt und
  bleibt es.
* **Kein Stilllegen der Wachen:** QA (20 Regeln), Capture-Wache,
  Duplikatschutz, `NEWSLETTER_SEND`-Verriegelung – alles unverändert.

## 3. Beweise

| Prüfung | Ergebnis |
|---|---|
| `newsletter_digest.py --selftest` | **40 Fälle grün** – neu: Testversand-Verdrahtung (20b), Versand-Ehrlichkeit (27) |
| `newsletter_cadence.py --selftest` | **14 Fälle grün** – Ruhetag, Vorfall-Erkennung, Fenstergrenze 04:00, Vortags-Abgrenzung, laufender/roter Lauf, Müll-Timestamp, Trockenlauf, Fensterlogik |
| `scripts/tests/` gesamt | **701/701 OK** – neu: `test_newsletter_cadence.py` (7+4), 2 neue Digest-Tests (Verdrahtung, Status-Ehrlichkeit) |
| `governance_contract.py --quick` | **18/18 Regeln** – Kadenz-Wache ins vertragliche Minimum (GUARDS/C6) aufgenommen |
| Argument-Form aller Freigabe-Varianten | normal = nur bauen · `test_adresse` = `--send` ohne `--live` · `live`/`planmaessig` = `--send --live` · ohne Secrets wird alles Sendende gestrichen |
| Eingabe als Code (B3) | `test_adresse='a@b.de"; curl evil; #'` und `tage='1; rm -rf …'` bleiben stumme Daten (`--days 1`, Adresse als ein Argument) |
| Kadenz-Wache am echten Tag | erkennt den still ausgefallenen Cron des 23.09. live: „Kein einziger Laufversuch seit 2026-09-23T04:00:00Z“ (Trockenlauf, ohne Dispatch) |
| Digest-Bau + QA (netzfrei) | 2 Artikel, 100/100 · 20 Regeln · 0 Funde, 0 Warnungen |

## 4. Dateien dieser Absicherung

| Datei | Änderung |
|---|---|
| `.github/workflows/alert-on-failure.yml` | B1: beide Newsletter-Workflows in die Wacht-Liste |
| `.github/workflows/newsletter-cadence.yml` | B2: neu – zählt nach, holt still verlorene Crons nach |
| `.github/workflows/newsletter-daily.yml` | B2: `planmaessig`-Eingabe (Cron-Freigabestufe) · B3: Eingaben als ENV statt Interpolation · B5: ehrliche Annotation |
| `scripts/newsletter_cadence.py` | B2: neu – reine Entscheidungslogik + Selbsttest + Nachhol-Dispatch |
| `scripts/newsletter_digest.py` | B4: Vorprüfung bei Testversand ohne Leere-Liste-Sperre · B5: Status-Schreiben verriegelt + nachgelesen, „VERSAND ERFOLGT“-Befund |
| `scripts/governance_contract.py` | B2: Kadenz-Wache im vertraglichen Minimum (GUARDS/C6) |
| `scripts/tests/test_newsletter_cadence.py` | B2: 11 Regressionen |
| `scripts/tests/test_newsletter_digest.py` | B4/B5: 2 Regressionen |
| `docs/FREISCHALTUNG-NEWSLETTER-CHECKLISTE.md` | Schritt 6b nennt die Kadenz-Wache |

## 5. Der Weg zur ersten Mail (unverändert, Reihenfolge zählt)

1. **Brevo → Senders & IPs:** `news@franksfinanzcheck.de` existiert und ist
   verifiziert (Code bestätigt, SPF/DKIM grün)? – Checkliste Schritt 2.
2. **Brevo → Listen:** zeigt die Listen-URL dieselbe Zahl wie
   `BREVO_LIST_ID`? Stehen Abonnenten drin (Double-Opt-In durchlaufen)?
3. **Actions → Newsletter-Daily → Run workflow:** erst `test_adresse`
   (Probe auf genau eine Adresse), dann `live` – oder der nächste Cron
   (Mo–Fr 05:05 UTC), den die Kadenz-Wache jetzt garantiert.
4. Scheitert danach noch etwas, steht die Ursache in der roten Annotation,
   im Step-Summary **und ab sofort als Issue** (B1) – mit dem nächsten
   Schritt, nicht nur mit einer Fehlercode-Zeile.

# 🔔 Alarm-Routing – Besitz, Kadenz, Schließpfad

**Stand:** 12.09.2026 · **Anlass:** Issue #272 (Bot-Watchdog-Dauer-Alarm) ·
**SSOT:** `scripts/alert_router.py` · **Anwender:** `scripts/bot_watchdog.py --route` ·
**Vertrag:** `governance_contract.py` **C14** · **Tests:** `scripts/tests/test_alert_router.py`,
`scripts/tests/test_bot_watchdog_routing.py`

---

## 1. Der Befund hinter dem Befund

Am 12.09.2026 meldete der Bot-Watchdog zum wiederholten Mal
„⚠️ Probleme mit der Content-Automatisierung". Die Meldung war **inhaltlich falsch**
und **betrieblich unlösbar** – beides aus demselben Grund.

| Was der Watchdog meldete | Was wirklich los war |
|---|---|
| „Pinterest-Token kritisch (HTTP 401) – Automatisierung kaputt" | Kadenz 3/2 erfüllt, Live-Site aktuell, Reserve 6 Artikel – die Content-Automatisierung war **gesund**. Kaputt war ein OAuth-Zugang, den ausschließlich ein Mensch im Browser erneuern kann. |
| „Das Issue wird automatisch geschlossen, sobald der nächste Lauf alles grün meldet." | Grün setzte genau die Handlung voraus, auf die das Issue wartete. **Der Schließpfad war konstruktiv unmöglich** – das Issue kehrte täglich zurück (#251 → #272 → …). |
| Ein Ticket | Zwei Tickets für denselben Sachverhalt: das Fach-Ticket der Pinterest-Token-Wache (#246, Label `pinterest-token`, mit Runbook) und der generische Alarm. |

Dazu kam ein zweiter, bisher unverbundener Umstand: **Pinterest hat die Domain
`franksfinanzcheck.de` seit 27.08.2026 gesperrt** (`data/pinterest_domain_block.json`).
Der Betrieb pinnt deshalb bewusst nicht – Pins würden die Sperre verlängern
(`docs/PINTEREST-SPIELBUCH.md`). In diesem Zustand ist ein toter Token kein
Zwischenfall, sondern eine Notiz. Die richtige Reihenfolge ist:

> **Erst** die Domain bei Pinterest freibekommen, **dann** den Token neu autorisieren.

Der alte Watchdog kannte diese Reihenfolge nicht – er meldete die teurere
Handlung (Token) und verschwieg die eigentliche (Domain).

**Lehrsatz:** Ein Melder ohne Besitzer, ohne Kadenz und ohne Schließpfad ist
kein Melder, sondern ein Dauerläufer. Und ein Dauerläufer ist teurer als der
Ausfall, weil er die Aufmerksamkeit verbraucht, die der echte Ausfall braucht
(Alarm-Müdigkeit – genau das, was Governance-Vertrag C4 verhindern soll).

---

## 2. Das Modell: zwei Kanäle, ein Besitzer

Jeder Befund (`alert_router.Finding`) trägt drei Pflichtfelder:

| Feld | Werte | Bedeutung |
|---|---|---|
| `owner` | `auto` \| `human` | Kann eine **Maschine** das heilen (Wache, Wiederholungslauf, Auto-Fix) – oder braucht es zwingend einen **Menschen** mit Zugang? |
| `severity` | `P1` \| `P2` \| `P3` | P1 blockiert den Betrieb, P2 beeinträchtigt ihn, P3 ist ein Hinweis/geparkter Kanal. |
| `channel` | GitHub-Label | **Der Kanal besitzt das Ticket** – ein Besitzer pro Ticket, nie zwei Melder in einem. |

Daraus folgen genau zwei Meldewege:

```
Befund ── owner=auto  ──▶ Automations-Ticket   (Label `bot-watchdog`)
                          · öffnet, aktualisiert, kommentiert (Kadenz 72 h)
                          · schließt sich, sobald KEIN auto-Befund mehr offen ist
                          · PROBLEMS enthält ausschließlich diese Befunde

       ── owner=human ──▶ Fach-Ticket          (z. B. `pinterest-token`, `pinterest-parked`)
                          · ein Besitzer (Fach-Workflow oder Router als Fallback)
                          · Eskalationsleiter 0/3/7/14 Tage: EIN Kommentar pro Stufe
                          · hält das Automations-Ticket NIE offen
```

Die dritte Regel ist die wichtigste und der eigentliche Fix:

> **Menschliche Befunde öffnen kein Automations-Ticket und halten keines offen.**

Damit hat jedes Ticket einen Ausweg – unabhängig davon, ob ein Mensch gerade
Zeit hat oder nicht.

---

## 3. Eskalationsleiter statt Taktfeuer

| Stufe | Schwelle | Wirkung |
|---|---|---|
| 0 | Tag 0 | Ticket wird eröffnet (mit Runbook + nächstem Schritt) |
| 1 | Tag 3 | Erinnerung |
| 2 | Tag 7 | Eskalation (P1-würdig, sichtbar im Kommentar) |
| 3 | Tag 14 | Kanal-Review: heilen, parken oder Kanal abschalten |

Zwei Schutzregeln verhindern Rauschen:

* **Ein Kommentar pro Stufe** – die Stufe wird aus dem letzten Router-Kommentar
  gelesen (`<!-- alarm-router: <kanal> stufe:<n> -->`), nicht aus dem Tagesdatum.
* **Frühestens alle 72 Stunden** – auch bei Stufenwechsel.

Für langsame Sachverhalte gibt es eigene Leitern: der geparkte Pinterest-Kanal
(`pinterest-parked`) eskaliert nach **14/30** Tagen – eine Domain-Sperre bei
Pinterest dauert Wochen, nicht Tage.

Ändern sich die **Fakten** (nicht das Datum), wird der Ticket-Body
aktualisiert – ohne neuen Kommentar. Die Zugehörigkeit eines Tickets erkennt
der Router am Marker `<!-- alarm-router: <kanal> -->` im Body, nicht am Label:
geht ein Label verloren (eingeschränktes Token, HTTP-422-Klasse), entsteht
trotzdem kein zweites Ticket. Tickets von Menschen bleiben unangetastet.

---

## 4. So sieht das im Betrieb aus

**Vorher** (jeden Morgen, solange der Token tot war):

```
⚠️ Bot-Watchdog: Probleme mit der Content-Automatisierung   (#272)
   - Pinterest-Token kritisch: Token RED – …
   (kann nie zugehen; dupliziert #246)
```

**Nachher** (derselbe Zustand):

```
🤖 Bot-Watchdog-Report
   Maschinell behebbar: 0          → Automations-Ticket #272 schließt sich
   Menschlicher Besitz: 2          → ein Ticket im Kanal `pinterest-parked`:

📌 Pinterest-Kanal geparkt: Domain-Sperre aktiv            (P3, Mensch)
   Seit 2026-08-27 gesperrt … Solange die Sperre steht, pinnt der Betrieb
   bewusst nicht – Pins würden die Sperre verlängern.
   → Erst Domain frei (docs/PINTEREST-SPIELBUCH.md), dann --domain-unblock.
   → Die Token-Neu-Autorisierung lohnt erst DANACH.
   Erinnerung nach 14 Tagen, Eskalation nach 30 Tagen – ein Kommentar pro Stufe.
```

Der Roth-Zustand des Tokens bleibt sichtbar (Check 7 im Report, `HUMAN (…)`),
er steht nur nicht mehr im Weg.

---

## 5. Bedienung

```bash
python3 scripts/bot_watchdog.py --selftest          # Wache + Router prüfen (C6/C14)
python3 scripts/bot_watchdog.py --emit-env          # prüfen, Env schreiben, Findings sichern
python3 scripts/bot_watchdog.py --route             # melden (Besitz, Kadenz, Auto-Close)
python3 scripts/bot_watchdog.py --route --dry-run   # nur planen, nichts schreiben
python3 scripts/alert_router.py --status            # offene Tickets + Eskalationsstufe

# Für Fach-Workflows, die ihr Ticket selbst besitzen (z. B. pinterest-token.yml):
# „Darf ich heute erinnern?“ – verhindert das tägliche Nachfassen im eigenen Ticket.
python3 scripts/alert_router.py --should-notify pinterest-token --every-days 7
# Exit 0 = fällig · Exit 1 = noch nicht fällig (Kadenz nicht erreicht)
python3 scripts/alert_router.py --selftest          # Routing-Regeln prüfen
python3 -m unittest discover -s scripts/tests -p 'test_*alert*.py' -v
```

Im Workflow (`bot-watchdog.yml`, täglich 10:30 MESZ) sind es zwei Schritte:
`--emit-env` (prüfen) und `--route` (melden). Der Routing-Schritt ist **immer
grün**: ein Melder, der am Melden scheitert, ist der teuerste Fehler im Betrieb
(Lehre aus #209/#227) – Fehler erscheinen als `::error::`-Annotation im Lauf-Log,
nicht als roter Lauf mit eigenem Folge-Issue.

**Zustand:** `data/alert_router_state.json` hält Stufe, Ticketnummer und
Zeitpunkte je Kanal (wird vom Workflow committed).

---

## 6. Einen neuen Befund einbauen (Checkliste)

1. `Finding` mit **Besitzer** anlegen – das ist die eigentliche Entscheidung:
   ```python
   findings.append(_f("pinterest-token", "…", "P2", owner="human",
                      channel=PINTEREST_TOKEN_CHANNEL, next_step="…"))
   ```
2. Kanal wählen: existiert ein Fach-Workflow mit Runbook → dessen Label
   (`pinterest-token`). Sonst eigenen Kanal, dann besitzt der Router das Ticket.
3. Leiter wählen: Standard (0/3/7/14) oder – bei Sachverhalten, die Wochen
   brauchen – eine langsamere (`PINTEREST_PARKED_LADDER`).
4. Test schreiben: **mindestens** ein Test, der belegt, dass ein menschlicher
   Befund kein Automations-Ticket öffnet (`test_alert_router.py` macht das vor).
5. `governance_contract.py --selftest` + `bot_watchdog.py --selftest` grün.

---

## 7. Abgrenzung – wer besitzt welches Ticket

| Kanal (Label) | Besitzer | Inhalt |
|---|---|---|
| `bot-watchdog` | Bot-Watchdog (Maschine) | Nur maschinell behebbare Befunde: Wache steht, Kadenz, Live-Site, Affiliate-Integrität, Reserve, Syntax |
| `pinterest-token` | Pinterest-Token-Wache | Token-Lebenszyklus, einmalige Neu-Autorisierung (Runbook) |
| `pinterest-parked` | Bot-Watchdog (Router) | Kanal geparkt: Domain-Sperre – und der Token als Folge davon |
| `pinterest` | Pinterest-Watchdog | Pin-Signale: Duplikate, Rich-Pins, Profil |
| `engine-deficit`, `produktions-wache`, … | jeweilige Wache | eigene Fach-Tickets, unverändert |

Ein Kanal – ein Besitzer – ein Runbook – eine Kadenz. Genau diese Eindeutigkeit
hat gefehlt, als #272 entstand.

# Governance-Report #206 – Ursache beseitigt, Kanal trägt sich selbst

**Datum:** 07.09.2026 · **Auslöser:** Issue #206 (Ampel RED, Fingerabdruck `015cfde80d84`)
· **Folge-Issues derselben Ursache:** #153 (Pinterest-AI rot), #209 (Pinterest-Watchdog rot)

---

## 1. Der Befund und was wirklich dahinterstand

Der Premium-Governance-Lauf meldete genau eine handlungsbedürftige Zeile:

> `PINTEREST_ACCESS_TOKEN` – Pinterest Access-Token: Live-Check abgelehnt –
> Pinterest-Token abgelaufen/ungültig (401)

Das klingt nach „Token erneuern, fertig". Ein Blick auf die Betriebslage zeigt
aber, dass derselbe Befund **planmäßig alle 30 Tage** wiederkehrt und dabei
jedes Mal drei Alarme in drei Kanälen erzeugt. Der eigentliche Fehler war nicht
der abgelaufene Token, sondern **ein fehlender Lebenszyklus plus eine Wache,
die etwas anderes maß als der Betrieb benutzt**:

| # | Ursache | Wirkung |
|---|---|---|
| **U1** | **Kein Erneuerungslauf.** Pinterest-Access-Tokens leben 30 Tage. Es gab zwar eine Auto-Refresh-Mechanik (`pinterest_auth.py`, `data/pinterest_tokens.enc`), aber keinen Workflow, der sie regelmäßig benutzt – die Datei existierte im Repo nicht einmal. | Der Kanal stirbt jeden Monat. Jeder Tod erzeugt ein Governance-Issue, rote Läufe und Alarm-Müdigkeit. |
| **U2** | **Sechs Token-Wahrheiten.** `pinterest_engine`/`generate_pins` nahmen zuerst den Auto-Refresh-Speicher, `secrets_age_guard`/`spam_guard`/`pinterest_perf_feedback`/`pinterest_profile_audit` zuerst das Env-Secret. | Die Wache prüfte systematisch einen **anderen** Token als der Bot benutzt. Ein grüner Report konnte einen toten Kanal bedeuten – und ein roter einen gesunden. |
| **U3** | **Falscher Prüf-Endpunkt.** Die Live-Probe fragte `/v5/users/me` – ein Pfad aus der v3-Zeit, den die Pinterest-API v5 nicht kennt. | Die Wache befragte nicht den Kanal, sondern sich selbst. |
| **U4** | **Kein Failover, keine Vorwarnung.** 401 führte zum harten Abbruch statt zum Queue-Modus; das bekannte Ablaufdatum wurde nie zur Vorwarnung genutzt. | #153/#209: rote Läufe, Folge-Issues – für einen Wartungsfall mit vier Wochen Vorlauf. |
| **U5** | **Der Melder scheiterte am Melden.** `pinterest-watchdog.yml` erstellte Issues mit `--label pinterest`; das Label existierte im Repository nie → HTTP 422 → roter Lauf → Fehler-Alerting eröffnete #209 *über das Issue, das nicht geschrieben werden konnte*. | Ein Alarm, der selbst zum Zwischenfall wird. |
| **U6** | **Doppelte Pin-Beschreibung** (`P4` im Watchdog): Zwei Artikel trugen denselben Pin-Text – für Pinterest ein Repeat-Pin-/Spam-Signal, und zugleich der Grund, warum der Watchdog-Lauf überhaupt melden wollte. | Reichweitenverlust im wichtigsten Traffic-Kanal, plus der rote Lauf aus U5. |

---

## 2. Was jetzt anders ist

### 2.1 Ein Token-Broker statt sechs Meinungen — `scripts/pinterest_token.py` (neu)

Eine Quelle der Wahrheit für den gesamten Pinterest-Betrieb:

```
1. data/pinterest_tokens.enc   → Auto-Refresh (continuous refresh, verschlüsselt)
2. PINTEREST_REFRESH_TOKEN     → Bootstrap aus dem Env (legt Quelle 1 gleich an)
3. PINTEREST_ACCESS_TOKEN      → klassisches Secret (Notnagel)
```

* **Failover:** Jede Quelle wird live gegen `/v5/user_account` geprüft; die erste
  mit HTTP 200 gewinnt. Ein toter Env-Token blockiert den Betrieb nicht mehr.
* **Proaktive Erneuerung:** ab 20 Tagen Alter – nicht erst beim ersten 401.
* **Rotationssicher:** Erneuert wird nur, wenn nötig, und unter Dateisperre.
  (Vorher erneuerte *jeder* Aufruf blind; der Refresh-Token rotiert dabei, zwei
  parallele Läufe konnten sich gegenseitig aussperren.)
* **Sichtbar:** `data/pinterest_token_state.json` hält Quelle, Zustand,
  Restlaufzeiten und einen SHA-256-Fingerabdruck fest – **kein Token-Material**.
* **Selbsttest:** 12 eingefrorene Fälle, offline, ohne echte Secrets.

Alle Verbraucher wurden umgestellt: `pinterest_engine`, `generate_pins`,
`spam_guard`, `pinterest_perf_feedback`, `pinterest_profile_audit`,
`secrets_age_guard`. `pinterest_auth.get_access_token()` bleibt als
Altlast-Schnittstelle bestehen und delegiert.

### 2.2 Ein täglicher Erneuerungslauf — `.github/workflows/pinterest-token.yml` (neu)

Täglich 04:40 MESZ, vor allen anderen Pinterest-Jobs:
Selbsttest → erneuern → rotierten Refresh-Token verschlüsselt sichern →
Live-Nachweis für die Secrets-Wache → **Issue nur, wenn ein Mensch gebraucht
wird**, mit Selbstheilung (schließt sich, sobald der Kanal wieder trägt).

Die einmalige Erst-Autorisierung läuft komplett in GitHub Actions ab
(*Run workflow* → `show_auth_url` → Code in `auth_code`), ohne lokale Python-
Installation und ohne Secrets auf dem Laptop. Runbook:
**`docs/PINTEREST-TOKEN-RUNBOOK.md`**.

### 2.3 Die Wache misst jetzt den Betrieb — `scripts/secrets_age_guard.py`

* Live-Probe über den Broker statt über das Env-Secret (U2) und gegen den
  korrekten v5-Endpunkt (U3).
* Neuer Report-Block **„Pinterest-Zugang (Lebenszyklus)"**: aktive Quelle,
  Auto-Erneuerung scharf ja/nein, Restlaufzeiten, nächster Schritt.
* Neue Vorwarnungen, **bevor** der Kanal steht:
  * `manual_token` (AMBER) – „läuft, aber im 30-Tage-Handbetrieb"
  * `refresh_rotation` (AMBER → RED) – Refresh-Token nähert sich der
    Zwangs-Rotation, die Automatik läuft offenbar nicht
* `PINTEREST_REFRESH_TOKEN` ist als Erneuerungspfad registriert und damit im
  Cockpit sichtbar.

### 2.4 Degradation statt roter Läufe — `scripts/pinterest_engine.py`

Kein lebender Zugang heißt jetzt **Queue-Modus** (Pins werden vorbereitet, Exit 0,
Grund und nächster Schritt stehen in `PIN-STATUS.md`) statt HTTP-401-Abbruch.
Ein Wartungsfall erzeugt damit *einen* gezielten Hinweis statt einer Kette
roter Läufe mit Folge-Issues (#153/#209).

### 2.5 Der Melder scheitert nicht mehr am Melden — `pinterest-watchdog.yml`

Das Label `pinterest` wird vor jeder Meldung angelegt (`gh label create --force`).
Das war die konkrete Ursache des roten Laufs vom 07.09. und damit von #209.

### 2.6 Doppelte Pin-Beschreibung beseitigt und dauerhaft gesperrt

* Der Frugalismus-Artikel hat eigene Pinterest-Texte bekommen (Titel und
  Beschreibung waren vom Mindset-Artikel dupliziert).
* `scripts/pinterest_pin_text_sync.py` hat eine **Duplikat-Sperre**: Eine
  Beschreibung gehört genau einem Artikel. Der Konflikt wird gemeldet, statt
  still ein Spam-Signal zu erzeugen.

### 2.7 Regressions-Schutz: drei neue Vertragsregeln (C10–C12)

`scripts/governance_contract.py` prüft bei **jedem Push und in jedem
Governance-Lauf**:

| Regel | Inhalt | Verhindert |
|---|---|---|
| **C10 Token-Broker** | Jedes Pinterest-Skript holt seinen Token über `pinterest_token` – kein Skript baut sich eine eigene Reihenfolge. | U2 (Wache misst etwas anderes als der Bot) |
| **C11 Token-Lebenszyklus** | Es gibt einen geplanten Erneuerungslauf, der den rotierten Refresh-Token sichert, sich selbst testet und sein Issue bei Heilung schließt. | U1 (Handbetriebs-Secret stirbt alle 30 Tage) |
| **C12 Label-Garantie** | Jeder Workflow, der Issues mit Label erzeugt, legt das Label vorher an. | U5 (Melder scheitert am Melden) |

Jede Regel prüft in beide Richtungen: Sie muss den Fehlerfall erkennen **und**
beim sauberen Aufbau still bleiben (Selbsttest mit Kunstbefunden).

---

## 3. Nachweise

```bash
python3 scripts/pinterest_token.py --selftest      # 12 Fälle: Failover, Bootstrap, Rotation
python3 scripts/secrets_age_guard.py --selftest    # inkl. Lebenszyklus-Befunde
python3 scripts/governance_contract.py --selftest  # C1–C12 mit Kunstbefunden
python3 scripts/governance_contract.py --quick     # Vertrag gegen den echten Bestand
python3 scripts/governance_gate.py --rehearse      # Was würde der Lauf heute melden?
python3 scripts/pinterest_token.py --status        # Lagebild des Zugangs
```

Alle 14 Wachen-Selbsttests laufen grün, der Governance-Vertrag ist erfüllt.

---

## 4. Was noch von Hand passieren muss (genau einmal, 5 Minuten)

Ein abgelaufener OAuth-Zugang kann technisch nicht ohne den Kontoinhaber
wiederhergestellt werden – die Autorisierung ist an das Pinterest-Login gebunden.
Deshalb bleibt genau ein Handgriff, und der ist so klein wie möglich gemacht:

1. **Actions → „Pinterest-Token-Wache" → Run workflow** mit Haken bei
   `show_auth_url` → URL aus der Zusammenfassung im Browser öffnen und erlauben.
2. Aus der Adresszeile den Wert hinter `?code=` kopieren.
3. **Run workflow** erneut, Code in das Feld `auth_code` einfügen.

Danach erneuert sich der Zugang täglich selbst, das Governance-Issue #206
schließt sich beim nächsten grünen Lauf automatisch, und die Wache warnt
künftig **vor** einem Ausfall statt danach.

Voraussetzung sind die Secrets `PINTEREST_APP_ID`, `PINTEREST_APP_SECRET` und
`PINTEREST_TOKEN_KEY` (Details im Runbook). Wer bereits einen Refresh-Token
besitzt, hinterlegt stattdessen `PINTEREST_REFRESH_TOKEN` – dann läuft sogar
dieser Schritt automatisch.

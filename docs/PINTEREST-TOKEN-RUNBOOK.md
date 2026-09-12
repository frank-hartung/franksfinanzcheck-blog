# 🔑 Runbook: Pinterest-Zugang (Token-Lebenszyklus)

**Stand:** 12.09.2026 (Kommandozeilen-Form + Label-Schließung; Härtung #219 vom 08.09.2026) · Zuständig: `pinterest-token.yml` (täglich) ·
Broker: `scripts/pinterest_token.py` · Autorisierung: `scripts/pinterest_auth.py` ·
Wache: `scripts/secrets_age_guard.py` · Vertrag: `governance_contract.py` C10–C13

Dieses Runbook beantwortet drei Fragen: Warum stand der Pinterest-Kanal
regelmäßig still, was erledigt die Automatik jetzt allein – und was genau musst
du **einmalig** tun (5 Minuten), damit du es nie wieder tun musst.

---

## 0. Schnellstart – die einmalige Neu-Autorisierung (5 Minuten)

> Das ist der Weg, den das offene Autorisierungs-Issue (Label `pinterest-token`)
> verlangt. Alles andere macht die Automatik.

| # | Wo | Was |
|---|---|---|
| 1 | GitHub → *Actions* → **Pinterest-Token-Wache** → *Run workflow* | Haken bei **`show_auth_url`** → *Run*. In der Zusammenfassung des Laufs steht ein **anklickbarer Autorisierungs-Link**. |
| 2 | Browser | Link öffnen, mit dem Pinterest-Konto von FranksFinanzcheck **Erlauben**. Du landest auf `franksfinanzcheck.de/pinterest-oauth` – die Seite zeigt den **Code groß mit Kopier-Knopf**. |
| 3 | GitHub → *Actions* → **Pinterest-Token-Wache** → *Run workflow* | Code in **`auth_code`** einfügen (du darfst auch die **komplette Adresszeile** einfügen) → *Run*. **Zügig:** Der Code gilt nur wenige Minuten und genau einmal. |
| 4 | – | Fertig. Der Lauf tauscht den Code, legt `data/pinterest_tokens.enc` an, prüft live, committet – und **schließt das offene Issue von selbst** (der Lauf findet es über das Label `pinterest-token`; die Nummer ist nirgends eingebaut). Ab jetzt erneuert sich der Zugang täglich (continuous refresh). |

**Dasselbe von der Kommandozeile:**

```bash
gh workflow run pinterest-token.yml -f show_auth_url=true  # Schritt 1
gh workflow run pinterest-token.yml -f auth_code="<Code>"  # Schritt 3
```

**Voraussetzungen (einmalig, sonst scheitert Schritt 3):**

* Secrets `PINTEREST_APP_ID`, `PINTEREST_APP_SECRET`, `PINTEREST_TOKEN_KEY` (Kap. 3, Schritt 0).
  Fehlt eines, sagt es der Lauf in der Zusammenfassung und im Issue.
* In der Pinterest-App (developers.pinterest.com → My apps): Redirect-URI
  **exakt** `https://franksfinanzcheck.de/pinterest-oauth` (ohne Slash am Ende) und die
  Scopes `boards:read`, `boards:write`, `pins:read`, `pins:write`, `user_accounts:read`.

**Wenn Schritt 3 mit „HTTP 400" scheitert:** Der Code war schon verbraucht oder abgelaufen.
Schritt 1 erneut starten, neu erlauben, den **neuen** Code sofort einfügen. Weitere
Diagnosen (401 = App-Daten, 403 = Freigabe/Scopes) stehen im Lauf – Kap. 4.

---

## 1. Warum das nötig war (Governance-Report #206 → Issue #219)

Pinterest gibt drei Sorten Zugangsdaten aus:

| Ding | Präfix | Lebensdauer | Kommentar |
|---|---|---|---|
| Access-Token | `pina_…` | **30 Tage** | damit spricht der Bot mit der API |
| Refresh-Token | `pinr_…` | **60 Tage, rotiert bei jeder Erneuerung** | damit holt sich der Bot neue Access-Token |
| App-Zugangsdaten | – | dauerhaft | `PINTEREST_APP_ID` + `PINTEREST_APP_SECRET` |

Der Betrieb hing bis 07.09.2026 an einem **von Hand eingefügten Access-Token**.
Das heißt: Der Kanal war so gebaut, dass er nach spätestens 30 Tagen stirbt (#206).

Am 07.09. kam der Token-Broker + die tägliche Wache. Am 08.09. meldete die Wache
**#219** – und die erste Neu-Autorisierung scheiterte zweimal. Die Ursachenanalyse
fand **sechs** Fehler, alle behoben:

| # | Befund | Wirkung | Fix |
|---|---|---|---|
| a | Nachweis-Schritt rief `--verify-only` **ohne** `--verify` | nie eine Live-Probe; Lagebild `unverified/amber` – ein Zustand, der weder heilt noch schließt | `--verify-only` prüft jetzt immer live; Vertrag **C13** |
| b | **Jeder** Prozess schrieb `data/pinterest_token_state.json` – auch der Deploy ohne Secrets | Cockpit zeigte `absent/red`, obwohl ein Secret existierte | nur live geprüfte Lagebilder dürfen schreiben; „absent" überschreibt nie einen Befund |
| c | Code-Tausch als Shell-Argument, keine URL-Erkennung, HTTP 400 ohne Erklärung | zwei rote Läufe, keine Handlungsanweisung | Code über Env, URL/`&state=` werden erkannt, Fehler → Diagnose in Lauf + Issue |
| d | Tausch-Fehler riss den Lauf ab (kein Refresh, kein Issue-Update) | Mensch sieht nur „Exit 1" | jeder Schritt berichtet, keiner blockiert den nächsten |
| e | Scope `read_ads` (kein v5-Scope), `user_accounts:read` fehlte | Autorisierung kann abbrechen; Broker-Probe `/v5/user_account` liefert 403 | korrekte v5-Scopes; Probe mit `/v5/boards`-Gegenprobe für Alt-Tokens |
| f | jeder Prozess durfte proaktiv rotieren | zwei Runner entwerten sich den Refresh-Token | nur die Wache (`PINTEREST_TOKEN_WACHE=1`) rotiert proaktiv; Failover nach 401 bleibt für alle |

---

## 2. Was jetzt automatisch läuft

```
        ┌──────────────────────────── täglich 04:40 MESZ ───────────────────────────┐
        │  pinterest-token.yml  (einzige Instanz mit PINTEREST_TOKEN_WACHE=1)       │
        │    1. Selbsttests Broker + Autorisierung (ohne Grün wird nichts angefasst)│
        │    2. [optional] Code → Token-Speicher (nur bei auth_code)                │
        │    3. Access-Token erneuern → neuer 60-Tage-Refresh-Token (Rotation)      │
        │    4. verschlüsselt speichern (data/pinterest_tokens.enc, AES-256-GCM)    │
        │    5. LIVE-Nachweis für die Secrets-Wache (--verify)                      │
        │    6. Issue NUR, wenn ein Mensch gebraucht wird – schließt sich selbst    │
        └───────────────────────────────────────────────────────────────────────────┘
```

Alle Pinterest-Skripte holen ihren Token ausschließlich über den Broker
`scripts/pinterest_token.py`. Der probiert in dieser Reihenfolge:

1. **Auto-Refresh-Speicher** `data/pinterest_tokens.enc` (die Wache erneuert
   proaktiv ab 20 Tagen Alter; jeder Prozess repariert beim ersten 401)
2. **Bootstrap aus dem Env**: `PINTEREST_REFRESH_TOKEN` + `PINTEREST_APP_ID` +
   `PINTEREST_APP_SECRET` (legt den Speicher aus 1. gleich mit an)
3. **klassisches Secret** `PINTEREST_ACCESS_TOKEN` (Notnagel)

Die erste Quelle, die live antwortet, gewinnt. Die Live-Probe fragt
`/v5/user_account`; antwortet Pinterest 403 (Alt-Token ohne
`user_accounts:read`), entscheidet `/v5/boards` – ein lebender Token wird nie
als tot behandelt.

**Wenn gar nichts trägt**, geht der Betrieb nicht kaputt, sondern in den
Queue-Modus: Pins werden vorbereitet (`data/pin_queue.yaml`, `PIN-STATUS.md`),
der Lauf bleibt grün, und genau **ein** Issue erklärt, was zu tun ist.

---

## 3. Einmalige Ersteinrichtung – ausführlich

### Schritt 0 – Secrets anlegen (nur beim allerersten Mal)

In GitHub → *Settings* → *Secrets and variables* → *Actions*:

| Secret | Woher |
|---|---|
| `PINTEREST_APP_ID` | Pinterest → *Developers* → *My apps* → App-ID |
| `PINTEREST_APP_SECRET` | dieselbe Seite → App-Secret (nach einem Reset gilt nur das neue) |
| `PINTEREST_TOKEN_KEY` | selbst ausdenken: lange Zufallszeichenkette (≥ 32 Zeichen, z. B. `openssl rand -base64 48`). Damit wird der Token-Speicher verschlüsselt – ohne diesen Schlüssel ist `data/pinterest_tokens.enc` wertloser Datenmüll, auch im öffentlichen Repo. |

In der Pinterest-App: Redirect-URI `https://franksfinanzcheck.de/pinterest-oauth`
und die Scopes `boards:read, boards:write, pins:read, pins:write, user_accounts:read`.
(Optional `ads:read`, falls später Ad-Analytics gewünscht – per Repo-Variable
`PINTEREST_SCOPES` überschreibbar. Pin-Analytics brauchen laut Pinterest-Doku nur
`boards:read` + `pins:read`.)

### Schritt 1–3 – siehe Kap. 0 (Schnellstart)

### Alternative ohne Browser-Handschlag

Wer bereits einen gültigen Refresh-Token besitzt, hinterlegt ihn als Secret
`PINTEREST_REFRESH_TOKEN`. Der nächste Lauf holt daraus einen frischen
Access-Token und legt den verschlüsselten Speicher automatisch an.

### Lokal (ohne GitHub Actions)

```bash
export PINTEREST_APP_ID=… PINTEREST_APP_SECRET=… PINTEREST_TOKEN_KEY=…
python3 scripts/pinterest_auth.py --auth-url          # URL öffnen, erlauben
python3 scripts/pinterest_auth.py --exchange "<Code oder komplette URL>"
PINTEREST_TOKEN_WACHE=1 python3 scripts/pinterest_token.py --refresh
git add data/pinterest_tokens.enc data/pinterest_token_state.json && git commit && git push
```

---

## 4. Kontrolle und Fehlersuche

```bash
python3 scripts/pinterest_token.py --status     # Lagebild (ohne Token-Material)
python3 scripts/pinterest_token.py --json       # dieselbe Wahrheit, maschinenlesbar
python3 scripts/pinterest_token.py --offline    # ohne Netz, nur Bestand
python3 scripts/pinterest_auth.py  --status     # Speicher: Scopes, Zeitstempel, Ablauf
python3 scripts/pinterest_token.py --selftest   # Broker-Logik (offline)
python3 scripts/pinterest_auth.py  --selftest   # Code-Erkennung, Scopes, Diagnosen
python3 scripts/secrets_age_guard.py --verify-only PINTEREST_ACCESS_TOKEN   # Live-Probe
gh run list --workflow=pinterest-token.yml      # läuft die Wache täglich?
```

Das Lagebild liegt versioniert in `data/pinterest_token_state.json` –
**ohne Token-Material**, mit Fingerabdruck (SHA-256-Kürzel), Quelle, Zustand,
Scopes, Restlaufzeiten, `verified` (live geprüft?) und `written_by` (welcher Lauf).

| Symptom | Bedeutung | Maßnahme |
|---|---|---|
| Code-Tausch **HTTP 400** | Code verbraucht/abgelaufen, falsch ausgeschnitten oder Redirect-URI weicht ab | neue URL, neu erlauben, neuen Code sofort einfügen (ganze Adresszeile erlaubt) |
| Code-Tausch **HTTP 401** | App-ID/Secret falsch | Secrets prüfen (Developer-Portal → My apps) |
| Code-Tausch **HTTP 403** | App nicht freigegeben oder Scope nicht aktiviert | Trial access abwarten / Scopes in der App aktivieren |
| `state: live`, `auto_renew_armed: false` | Handbetrieb – stirbt in ≤ 30 Tagen | Kap. 0 durchlaufen |
| `state: live`, Nachweis „ohne Scope user_accounts:read" | Alt-Token funktioniert, Profil-Audit eingeschränkt | nichts Dringendes; bei nächster Neu-Autorisierung automatisch dabei |
| `state: dead`, `renewable: true` | Refresh schlug fehl (App-Daten falsch / Zugriff entzogen) | App-Secrets prüfen, dann Kap. 0 |
| `state: dead`, `renewable: false` | keine Erneuerung möglich | Kap. 0 |
| `state: unreachable` | Pinterest gestört / Rate-Limit | nichts tun, nächster Lauf prüft erneut |
| `state: unverified` im Cockpit | ein Lauf hat ohne Live-Probe geschrieben – seit 08.09. nicht mehr möglich | `gh run list --workflow=pinterest-token.yml`, Vertrag C13 prüfen |
| `refresh_days_left` < 20 | Automatik läuft nicht täglich | Workflow aktiv? `gh run list --workflow=pinterest-token.yml` |
| „Fehlende Secrets" im Lauf | Schritt 0 unvollständig | Secrets anlegen |

---

## 5. Sicherheitszusagen

* **Kein Token im Klartext im Repo.** Der Speicher ist AES-256-GCM-verschlüsselt,
  der Schlüssel liegt nur als GitHub-Secret.
* **Kein Token in Logs, Reports oder Issues.** Ausgegeben wird ausschließlich ein
  12-stelliger SHA-256-Fingerabdruck; `--status` zeigt keine Präfixe mehr;
  Fehlermeldungen werden vor der Ausgabe von Secret-Material bereinigt; der
  Autorisierungs-Code wird im Workflow maskiert (`add-mask`) und nur über das Env
  übergeben.
* **Landeseite `/pinterest-oauth`** liest den Code nur im Browser, sendet nichts,
  ist `noindex`, `no-referrer` und entfernt den Code aus der Browser-History.
* **Regel C9** durchsucht Reports und `data/*.json` nach Token-Mustern – ein Leak
  bricht den Build. **C10/C11** sichern Broker und täglichen Erneuerungslauf.
  **C13** (neu) sichert: Nachweise laufen live, nur die Wache rotiert proaktiv,
  und die Autorisierung fordert echte v5-Scopes.

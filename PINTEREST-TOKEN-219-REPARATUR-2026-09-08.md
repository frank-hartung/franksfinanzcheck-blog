# 🔑 Pinterest-Token Reparatur #219 – Profi-Agentur-Level (08.09.2026)

**Issue:** #219 – `🔑 Pinterest-Zugang braucht eine einmalige Neu-Autorisierung`
**Run:** [34199196303](https://github.com/frank-hartung/franksfinanzcheck-blog/actions/runs/34199196303) (Wache, 07:24 UTC) · Vorläufe [34124589383](https://github.com/frank-hartung/franksfinanzcheck-blog/actions/runs/34124589383) / [34124699527](https://github.com/frank-hartung/franksfinanzcheck-blog/actions/runs/34124699527) (Code-Tausch **rot**, 07.09.)
**Schwere:** P1 – Pinterest ist der reichweitenstärkste Affiliate-Zubringer; ohne Token keine API-Pins, kein Dedup-Sync, keine Performance-Daten, Profil-Audit blind.

---

## 1. Befund – was wirklich passiert ist

Das Issue sagt „einmalige Neu-Autorisierung nötig". Das ist die **richtige
Handlung** – aber sie wurde am 07.09. **zweimal versucht und scheiterte beide
Male** im Schritt „Erst-/Neu-Autorisierung (Code → Token-Speicher)". Der Lauf
wurde rot, meldete nichts Verwertbares, und die Wache blieb auf `unverified`.
Der Mensch stand vor einem „Exit 1".

### Root-Cause-Analyse (5 Whys)

1. **Warum stand das Issue auf `unverified/amber`?**
   Das Lagebild `data/pinterest_token_state.json` wurde zuletzt vom Schritt
   „Nachweis für die Secrets-Wache" geschrieben – der ruft
   `secrets_age_guard.py --verify-only PINTEREST_ACCESS_TOKEN` auf **ohne
   `--verify`**. In `main()` gilt `live = "--verify" in argv` → **es lief nie
   eine Live-Probe**. Der Broker wurde mit `verify=False` gefragt und schrieb
   ehrlich „ohne Live-Probe übernommen". Drei Workflows (Token-Wache, Watchdog,
   Pinterest-AI) hatten denselben Aufruf; der Mastodon-Nachweis in `social-ai.yml` ebenso.
2. **Warum zeigte das Cockpit zwischendurch `absent/red`, obwohl ein Secret existierte?**
   Jeder Prozess, der `pinterest_token.get_token()` aufruft, schrieb das
   Lagebild – auch `spam_guard` im **Deploy-Workflow**, der gar keine
   Pinterest-Secrets hat. Fünf der letzten sechs Commits an der Datei kamen vom
   Content-Bot (`fix(gate)`), nicht von der Wache. Das Cockpit zeigte den Stand
   des **am schlechtesten informierten Prozesses**.
3. **Warum scheiterte der Code-Tausch?**
   Der Code kam als Shell-Argument `--exchange "${{ inputs.auth_code }}"`
   (Sonderzeichen/Anführungszeichen brechen), eine eingefügte komplette URL oder
   `code&state=` wurde nicht erkannt, und HTTP 400 (`invalid_grant` = Code
   verbraucht/abgelaufen/falsche Redirect-URI) wurde als roher Traceback ohne
   Anleitung ausgegeben. Der Schritt riss den Lauf ab – kein Refresh, kein
   Lagebild, kein Issue-Update, dafür ein zweiter Fehler im Issue-Schritt
   (Label-Schritt war übersprungen).
4. **Warum ist die Autorisierung selbst fragil?**
   Scope-Liste `boards:read,boards:write,pins:read,pins:write,read_ads`:
   `read_ads` **ist kein v5-Scope** (v5 kennt `ads:read`), und
   `user_accounts:read` **fehlte** – genau der Scope, den die Live-Probe
   `/v5/user_account` braucht. Ein autorisierter Token hätte in der Probe **403**
   bekommen → Broker wertet 403 als „tot" → Rotation ins Leere, ROT für einen
   funktionierenden Kanal. Die Redirect-URI zeigte auf eine 404-Seite; der Code
   musste aus der Adresszeile geschnitten werden.
5. **Warum ist das systemisch teuer?**
   Der Refresh-Token rotiert. **Jeder** Prozess durfte proaktiv rotieren
   (Alter ≥ 20 d). Zwei parallele Runner (Watchdog 06:30 + Governance) hätten
   den frisch autorisierten Speicher gegenseitig entwerten können – der
   Verlierer committet einen toten Speicher, und der Mensch autorisiert erneut.

### Weitere Schwächen (Profi-Audit)

- `pinterest_auth.py --status` gab Token-**Präfixe** aus (`pina_…`/`pinr_…` erste 12 Zeichen) – in öffentlichen Logs unnötig.
- Kein `--selftest` für die Autorisierungsschicht (C6 galt nur für den Broker).
- Der Lagebild-JSON kannte weder Scopes noch Pinterests eigenes Ablaufdatum (`refresh_token_expires_at`) noch die Herkunft des Eintrags.
- Kein `continuous_refresh=true` im Code-Tausch (für Apps vor 25.09.2025 nötig – sonst 365-Tage-Token ohne Rotation, nach einem Jahr endgültig tot).
- Issue-Text nannte weder Voraussetzungen (Secrets, Redirect-URI, Scopes) noch die Fehlerursache des letzten Versuchs.

---

## 2. Reparatur – was jetzt anders ist

### 2.1 Broker `scripts/pinterest_token.py`

| Änderung | Wirkung |
|---|---|
| **Lagebild-Schreibrecht** `_may_persist()` | Nur live geprüfte Lagebilder (`verified: true`) schreiben; `absent` überschreibt nie einen vorhandenen Befund. Das Cockpit zeigt die Wahrheit der Wache, nicht den Deploy. |
| **Wache-Flag** `PINTEREST_TOKEN_WACHE=1` | Nur die Token-Wache (oder `--refresh`) rotiert proaktiv. Jeder andere Prozess repariert ausschließlich nach echtem 401 (Failover bleibt). Kein Rotations-Wettlauf. |
| **403-Gegenprobe** | `/v5/user_account` 403 → `/v5/boards` 200 = **live** („ohne Scope user_accounts:read"). Ein Alt-Token wird nie als tot gemeldet. |
| **OAuth-Metadaten** | `scope`, `refresh_expires_at` (aus `refresh_token_expires_at`/`_in`) werden gespeichert; `refresh_days_left` rechnet mit Pinterests Uhr. |
| Lagebild-Felder | `verified`, `written_by` (Workflow), `scopes`, `refresh_expires_at`. |
| Selbsttest | +9 Fälle: Wache vs. Fremdprozess, `--refresh`, 401-Failover ohne Flag, 403-Gegenprobe (4 Varianten), Schreibrecht (5 Varianten), Scope/Ablauf-Persistenz. |

### 2.2 Autorisierung `scripts/pinterest_auth.py`

| Änderung | Wirkung |
|---|---|
| **Scopes** `boards:read,boards:write,pins:read,pins:write,user_accounts:read` | Echte v5-Namen; Live-Probe und Profil-Audit funktionieren. Überschreibbar per `PINTEREST_SCOPES`. |
| **`extract_code()`** | Akzeptiert Code, `code&state=…`, komplette Redirect-URL, Anführungszeichen. |
| **Code über Env** `PINTEREST_AUTH_CODE` | Kein Shell-Bruch, kein Klartext in `ps`/Log. |
| **`continuous_refresh=true`** | Auch Alt-Apps bekommen den rotierenden 60-Tage-Token. |
| **Diagnose statt Traceback** | 400 → „Code verbraucht/abgelaufen/URI", 401 → App-Daten, 403 → Freigabe/Scopes, 429 → warten. Exit 1 sauber, kein halber Speicher. |
| **Scope-Abgleich** | Nach dem Tausch: erteilt vs. angefordert; fehlende Scopes werden benannt. |
| `--status` | Kein Token-Material mehr, dafür Scopes/Zeitstempel/Ablauf. |
| **`--selftest`** (neu) | Code-Erkennung (8 Fälle), Scope-Syntax, URL-Aufbau, Diagnosetexte. |
| `--auth-url` | `state`-Parameter, Klartext-Anleitung, Hinweis auf Einmaligkeit. |

### 2.3 Landeseite `static/pinterest-oauth.html` (neu)

Die Redirect-URI ist jetzt eine echte Seite: zeigt den Code groß, **Kopier-Knopf**,
Link direkt zur Token-Wache, erklärt `error=access_denied`. Liest nur
`location.search`, sendet nichts, `noindex`/`no-referrer`, entfernt den Code aus
der History. Der häufigste Bedienfehler („Code falsch ausgeschnitten") ist damit weg.

### 2.4 Workflow `pinterest-token.yml`

- `PINTEREST_TOKEN_WACHE: "1"` auf Job-Ebene (einzige Rotier-Instanz).
- Selbsttests **Broker + Auth** vor jeder Token-Berührung.
- **Voraussetzungs-Check**: fehlende Secrets werden benannt (Summary + Issue).
- `show_auth_url`: Summary enthält den **anklickbaren** Autorisierungs-Link.
- Code-Tausch: Env-Übergabe, `add-mask`, `PIPESTATUS`, Ergebnis in Summary, **kein Abbruch** des Laufs – Refresh, Nachweis, Commit und Issue laufen immer.
- Nachweis mit **`--verify --verify-only`** (echte Live-Probe).
- Issue-Schritt: Zustand/Ampel/Quelle, **Diagnose des letzten Tauschs**, fehlende Secrets, Voraussetzungen (URI + Scopes), direkte Workflow-Links; `unreachable` → nur Kommentar, kein Alarm; `live` → Issue schließt sich.

### 2.5 Wache `scripts/secrets_age_guard.py` + Workflows

- `--verify-only <VAR>` **impliziert** jetzt `--verify` (heilt Token-Wache, Pinterest-Watchdog, Pinterest-AI **und** den Mastodon-Nachweis in `social-ai.yml`).
- Aufrufe in `pinterest-watchdog.yml` / `pinterest-ai.yml` zusätzlich explizit auf `--verify --verify-only` gesetzt.

### 2.6 Governance-Vertrag – neue Regel **C13 „Nachweis-Echtheit"**

Prüft dauerhaft: (1) kein `--verify-only PINTEREST_ACCESS_TOKEN` ohne `--verify`,
(2) `pinterest-token.yml` setzt `PINTEREST_TOKEN_WACHE`, kein anderer Workflow tut
das, (3) `DEFAULT_SCOPES` sind syntaktisch gültige v5-Scopes und enthalten
`pins:write`, `boards:read`, `user_accounts:read`. `pinterest_auth.py` ist jetzt
Teil der C6-Selbsttest-Pflicht und des Governance-Preflights.

### 2.7 Doku

- `docs/PINTEREST-TOKEN-RUNBOOK.md`: Kap. 0 Schnellstart (Tabelle), Ursachen-Tabelle, Fehler-Matrix (400/401/403), Sicherheitszusagen aktualisiert.
- `ANLEITUNG-PINTEREST-API.md`: Scopes korrigiert, Actions-Weg als Standard.
- `README.md`: Abschnitt Pinterest-Zugang ergänzt.

---

## 3. Nachweise

| Prüfung | Ergebnis |
|---|---|
| `pinterest_token.py --selftest` | ✅ (inkl. 9 neue Fälle) |
| `pinterest_auth.py --selftest` | ✅ (neu) |
| `secrets_age_guard.py --selftest` | ✅ |
| `governance_contract.py --selftest` | ✅ C1–C13 |
| `governance_contract.py` (voll, Repo-Stand) | ✅ Vertrag erfüllt |
| `bot_watchdog.py --selftest`, `spam_guard.py --selftest` | ✅ |
| Workflow-YAML geparst, jeder `run:`-Block `bash -n` | ✅ 10/10 |
| Issue-Schritt mit gemocktem `gh` (Zustand absent, Tausch rot, Secret fehlt) | ✅ Body vollständig, Kommentar korrekt |
| **E2E gegen Fake-Pinterest** (lokaler OAuth+API-Server): falscher Code → Diagnose/Exit 1/kein Speicher · richtiger Code als URL → Speicher mit Scope+Ablauf · Fremdprozess rotiert nicht, Lagebild `live/verified` · Prozess ohne Secrets überschreibt nichts · Wache `--refresh` rotiert → `pinr_2`, Lagebild grün, kein Token-Material · 403-Alt-Token → live · 401 → Failover für jeden | ✅ |

---

## 4. Was Frank jetzt tun muss (5 Minuten, einmalig)

1. **Actions → Pinterest-Token-Wache → Run workflow → `show_auth_url`** → Link in der Zusammenfassung klicken.
2. **Erlauben** → auf `franksfinanzcheck.de/pinterest-oauth` **„Code kopieren"**.
   *(Die Seite ist nach dem Merge/Deploy live. Falls du vorher autorisierst: Der Code steht in der Adresszeile – einfach die ganze Adresszeile kopieren.)*
3. **Actions → Pinterest-Token-Wache → Run workflow → `auth_code` einfügen** → Run. Zügig – Code gilt Minuten, einmal.
4. Der Lauf tauscht, prüft live, committet `data/pinterest_tokens.enc` und **schließt #219 selbst**.

Vorher prüfen (einmalig): Secrets `PINTEREST_APP_ID`, `PINTEREST_APP_SECRET`,
`PINTEREST_TOKEN_KEY`; in der Pinterest-App Redirect-URI
`https://franksfinanzcheck.de/pinterest-oauth` und Scopes
`boards:read, boards:write, pins:read, pins:write, user_accounts:read`.
Scheitert Schritt 3, steht die Ursache **im Lauf und im Issue** – nicht mehr nur „Exit 1".

---

## 5. Affiliate-/Pinterest-Perspektive (warum das Geld kostet)

- Ohne API-Token läuft nur der RSS-Auto-Publish; **Dedup-Sync** (`spam_guard --sync-pins`) ist blind → Repeat-Pin-Risiko = Spam-Signal gegen das Konto, das 2026 bereits einmal gesperrt war.
- **Performance-Feedback** (`pinterest_perf_feedback.py --fetch`) und die Gewichtung der Pin-Themen nach Outbound-Clicks stehen still → Pins gehen nicht dorthin, wo die Provision entsteht.
- **Profil-Audit** (`/v5/user_account`) prüft Name/Bio/Website – Website-Claim und Rich Pins sind Voraussetzung für Outbound-Klicks auf `/go/`-Links.
- Mit dieser Reparatur trägt sich der Kanal nach **einer** Handlung dauerhaft selbst, und jede künftige Störung nennt Ursache und Schritt – kein monatlicher Blindflug mehr.

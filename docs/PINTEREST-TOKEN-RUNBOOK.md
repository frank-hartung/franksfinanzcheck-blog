# 🔑 Runbook: Pinterest-Zugang (Token-Lebenszyklus)

**Stand:** 07.09.2026 · Zuständig: `pinterest-token.yml` (täglich) ·
Broker: `scripts/pinterest_token.py` · Wache: `scripts/secrets_age_guard.py`

Dieses Runbook beantwortet drei Fragen: Warum stand der Pinterest-Kanal
regelmäßig still, was erledigt die Automatik jetzt allein – und was genau musst
du **einmalig** tun (5 Minuten), damit du es nie wieder tun musst.

---

## 1. Warum das nötig war (Governance-Report #206)

Pinterest gibt drei Sorten Zugangsdaten aus:

| Ding | Präfix | Lebensdauer | Kommentar |
|---|---|---|---|
| Access-Token | `pina_…` | **30 Tage** | damit spricht der Bot mit der API |
| Refresh-Token | `pinr_…` | **60 Tage, rotiert bei jeder Erneuerung** | damit holt sich der Bot neue Access-Token |
| App-Zugangsdaten | – | dauerhaft | `PINTEREST_APP_ID` + `PINTEREST_APP_SECRET` |

Der Betrieb hing bis 07.09.2026 an einem **von Hand eingefügten Access-Token**.
Das heißt: Der Kanal war so gebaut, dass er nach spätestens 30 Tagen stirbt.
Genau das ist passiert – und zwar mit drei Alarmen gleichzeitig:

* `#206` – Governance-Report: `PINTEREST_ACCESS_TOKEN` … 401
* `#153` – Pinterest-AI läuft rot (Engine bricht mit HTTP 401 ab)
* `#209` – Pinterest-Watchdog läuft rot (Folgefehler beim Melden)

Dazu kam ein Messfehler, der die Sache verschleiert hat: Die Wache prüfte das
Env-Secret, während die Engine mit einer anderen Quelle arbeitete. Ein grüner
Report konnte einen toten Kanal bedeuten – und ein roter einen gesunden.

---

## 2. Was jetzt automatisch läuft

```
        ┌──────────────────────────── täglich 04:40 MESZ ───────────────────────────┐
        │  pinterest-token.yml                                                      │
        │    1. Selbsttest des Brokers (ohne grünen Test wird nichts angefasst)     │
        │    2. Access-Token erneuern  → neuer 60-Tage-Refresh-Token (Rotation)     │
        │    3. verschlüsselt speichern (data/pinterest_tokens.enc, AES-256-GCM)    │
        │    4. Live-Nachweis für die Secrets-Wache                                 │
        │    5. Issue NUR, wenn ein Mensch gebraucht wird – schließt sich selbst    │
        └───────────────────────────────────────────────────────────────────────────┘
```

Alle Pinterest-Skripte holen ihren Token ausschließlich über den Broker
`scripts/pinterest_token.py`. Der probiert in dieser Reihenfolge:

1. **Auto-Refresh-Speicher** `data/pinterest_tokens.enc` (erneuert proaktiv ab
   20 Tagen Alter, spätestens beim ersten 401)
2. **Bootstrap aus dem Env**: `PINTEREST_REFRESH_TOKEN` + `PINTEREST_APP_ID` +
   `PINTEREST_APP_SECRET` (legt den Speicher aus 1. gleich mit an)
3. **klassisches Secret** `PINTEREST_ACCESS_TOKEN` (Notnagel)

Die erste Quelle, die live mit HTTP 200 antwortet, gewinnt. Fällt eine aus,
übernimmt die nächste – ohne roten Lauf.

**Wenn gar nichts trägt**, geht der Betrieb nicht kaputt, sondern in den
Queue-Modus: Pins werden vorbereitet (`data/pin_queue.yaml`, `PIN-STATUS.md`),
der Lauf bleibt grün, und genau **ein** Issue erklärt, was zu tun ist.

---

## 3. Einmalige Ersteinrichtung (5 Minuten)

### Schritt 0 – Secrets anlegen (nur beim allerersten Mal)

In GitHub → *Settings* → *Secrets and variables* → *Actions*:

| Secret | Woher |
|---|---|
| `PINTEREST_APP_ID` | Pinterest → *Developers* → *My apps* → App-ID |
| `PINTEREST_APP_SECRET` | dieselbe Seite → App-Secret |
| `PINTEREST_TOKEN_KEY` | selbst ausdenken: lange Zufallszeichenkette (≥ 32 Zeichen). Damit wird der Token-Speicher verschlüsselt – ohne diesen Schlüssel ist `data/pinterest_tokens.enc` wertloser Datenmüll, auch im öffentlichen Repo. |

Wichtig: In der Pinterest-App muss die Redirect-URI
`https://franksfinanzcheck.de/pinterest-oauth` hinterlegt sein.

### Schritt 1 – Autorisierungs-URL holen

GitHub → *Actions* → **Pinterest-Token-Wache** → *Run workflow* →
Haken bei `show_auth_url` → starten.
Die URL steht anschließend in der Lauf-Zusammenfassung.

### Schritt 2 – Erlauben und Code kopieren

URL im Browser öffnen (mit dem Pinterest-Konto eingeloggt) → *Erlauben*.
Du landest auf einer Fehlerseite – das ist richtig so. Aus der Adresszeile den
Wert hinter `?code=` kopieren (bis vor `&state=`).

### Schritt 3 – Code eintauschen

GitHub → *Actions* → **Pinterest-Token-Wache** → *Run workflow* → Code in das
Feld `auth_code` einfügen → starten.

Der Lauf legt `data/pinterest_tokens.enc` an, committet die Datei und bestätigt
den Zugang live. **Ab hier trägt sich der Kanal selbst** – solange der tägliche
Lauf aktiv ist, läuft er unbegrenzt weiter.

### Alternative ohne Browser-Handschlag

Wer bereits einen Refresh-Token besitzt, hinterlegt ihn als Secret
`PINTEREST_REFRESH_TOKEN`. Der nächste Lauf holt daraus einen frischen
Access-Token und legt den verschlüsselten Speicher automatisch an.

---

## 4. Kontrolle und Fehlersuche

```bash
# Lagebild (Quelle, Zustand, Restlaufzeiten – ohne Token-Material)
python3 scripts/pinterest_token.py --status

# maschinenlesbar (dieselbe Wahrheit, die Wache und Cockpit lesen)
python3 scripts/pinterest_token.py --json

# ohne Netz, nur Bestand (z. B. lokal ohne Secrets)
python3 scripts/pinterest_token.py --offline

# Erneuerung erzwingen (macht der tägliche Lauf automatisch)
python3 scripts/pinterest_token.py --refresh

# Gegenprobe der Wache
python3 scripts/secrets_age_guard.py --verify-only PINTEREST_ACCESS_TOKEN
```

Das Lagebild liegt versioniert in `data/pinterest_token_state.json` –
**ohne Token-Material**, nur mit Fingerabdruck (SHA-256-Kürzel), Quelle,
Zustand und Restlaufzeiten.

| Symptom | Bedeutung | Maßnahme |
|---|---|---|
| `state: live`, `auto_renew_armed: false` | Handbetrieb – stirbt in ≤ 30 Tagen | Kapitel 3 durchlaufen |
| `state: dead`, `renewable: true` | Refresh schlug fehl (App-Daten falsch/App-Zugriff entzogen) | App-Secrets prüfen, dann Kapitel 3 |
| `state: dead`, `renewable: false` | keine Erneuerung möglich | Kapitel 3 |
| `state: unreachable` | Pinterest gestört / Rate-Limit | nichts tun, nächster Lauf prüft erneut |
| `refresh_days_left` < 20 | Automatik läuft nicht täglich | `gh run list --workflow=pinterest-token.yml` |

---

## 5. Sicherheitszusagen

* **Kein Token im Klartext im Repo.** Der Speicher ist AES-256-GCM-verschlüsselt,
  der Schlüssel liegt nur als GitHub-Secret.
* **Kein Token in Logs, Reports oder Issues.** Ausgegeben wird ausschließlich ein
  12-stelliger SHA-256-Fingerabdruck; Fehlermeldungen werden vor der Ausgabe
  von Secret-Material bereinigt.
* **Regel C9 des Governance-Vertrags** durchsucht Reports und `data/*.json` nach
  Token-Mustern (`pina_`, `pinr_`, …) – ein Leak bricht den Build.
* **Regel C10/C11** stellen sicher, dass es bei einer Token-Quelle und einem
  täglichen Erneuerungslauf bleibt. Wer die Automatik ausbaut, bekommt einen
  roten Build statt eines stillen Kanaltods in 30 Tagen.

# 💬 Anleitung: Dialog-Autopilot (Kommentare & Antworten)

> Premium-Integration vom 29.09.2026 · Playbook: `data/social/dialog.yaml`
> Maschine: `scripts/social_dialog.py` · Workflow: `.github/workflows/social-dialog.yml`

**Was er tut:** Er sammelt dreimal täglich alle Kommentare, Erwähnungen und
Antworten auf deinen Kanälen, ordnet sie ein, formuliert die Antwort fertig aus
und stellt sie zu – entweder selbstständig oder zur Freigabe.

**Was du tust:** Ja oder Nein sagen. Nicht tippen.

---

## 1. Warum das hier kein normaler Auto-Reply-Bot ist

Ein Finanzblog darf keine individuelle Beratung geben. Beantwortet eine KI die
Frage „Soll ich meinen Vertrag kündigen?", entsteht genau dieser Anschein – mit
Haftungsfolge (Auskunftsvertrag nach § 675 BGB, UWG, je nach Thema RDG oder WpIG).

Deshalb arbeitet dieser Autopilot mit **abgestufter Autonomie** statt Vollautomatik:

| Modus | Was passiert | Welche Klassen |
|---|---|---|
| **auto** | Antwort geht sofort raus | Dank, Weiterempfehlung |
| **review** | Antwort wird **fertig formuliert** und wartet auf dein Ja | Sachfragen, Beratungsfragen, Kritik, Korrekturen, Kooperationen |
| **eskalation** | Nie eine Bot-Antwort, sofort Chefsache | Rechtliches (Abmahnung, DSGVO, Presserecht) |
| **mute** | Wird nur gezählt, nie beantwortet | Spam, Scam, Trolle |

Der entscheidende Punkt: **Review heißt nicht Arbeit.** Der Text steht schon da.
Du liest zwei Zeilen und entscheidest.

---

## 2. Der Ablauf eines Laufs

```
1 SAMMELN    neue Beiträge je Kanal (nur lesend, 72-Stunden-Fenster)
2 EINORDNEN  Signalwörter + optionale Gratis-KI als Zweitmeinung
3 BELEGEN    passenden EIGENEN Artikel suchen
4 ENTWERFEN  Vorlage je Klasse, danach optionale KI-Politur
5 PRÜFEN     hartes Gate
6 ZUSTELLEN  senden oder in die Freigabemappe legen
7 BERICHTEN  SOCIAL-DIALOG-STATUS.md
```

**Die Einordnung kennt eine Vorrangregel:** Gefahr schlägt Freundlichkeit.
„Danke, aber mein Anwalt meldet sich" ist keine Dankesnachricht, sondern Chefsache.
Die KI darf eine Einordnung **verschärfen, aber nie entschärfen** – ein
KI-Vorschlag in Richtung „harmloser" wird verworfen.

---

## 3. Das Gate – was nie rausgeht

Jede Antwort läuft durch `gate:` in `data/social/dialog.yaml`. Ein Verstoß
blockiert, **auch wenn die Klasse `auto` ist**:

| Prüfung | Beispiel, das blockiert wird |
|---|---|
| Beratungsanschein | „ich empfehle dir", „an deiner Stelle würde ich", „kündige" |
| Unzulässiges Versprechen | „garantiert", „risikofrei", „sichere Rendite" |
| Erlaubnispflichtige Auskunft | „das kannst du steuerlich absetzen", „da hast du Anspruch auf" |
| Fremde Links | alles außerhalb `franksfinanzcheck.de` |
| Affiliate-Links | `/go/`, `a.check24.net`, Kurz-URLs |
| Personenbezogene Daten | IBAN, Telefonnummer, E-Mail in der Antwort |
| Bot-Floskeln | „Vielen Dank für deine Nachricht", „als KI" |
| **Unbelegte Zahlen** | jede Zahl, die nicht im Beleg-Artikel oder im Kommentar steht |

Die letzte Zeile ist der Halluzinationsschutz. Eine erfundene Zahl unter einem
Finanzartikel ist der teuerste Fehler, den dieses System machen könnte – deshalb
prüft das Gate jede Ziffer gegen die Quelle.

**Auch eine Freigabe hebelt das Gate nicht aus.** Beim Senden läuft es erneut;
nur die Belegpflicht darfst du bewusst überstimmen.

---

## 4. Bedienung

### Freigeben (der Normalfall)

**Auf GitHub:** *Actions → „Dialog-Autopilot" → Run workflow*
→ `modus: freigeben` → `ids: m7f3a2,bl91cc` (oder `alle`) → **Run**.

Die IDs stehen im Cockpit und im Issue **„💬 Dialog: Freigaben und Chefsache"**,
das der Lauf automatisch anlegt, aktualisiert und schließt, sobald nichts mehr wartet.

**Lokal:**

```bash
python3 scripts/social_dialog.py --run              # sammeln + zustellen
python3 scripts/social_dialog.py --run --dry-run    # zeigt alles, sendet nichts
python3 scripts/social_dialog.py --freigeben m7f3a2
python3 scripts/social_dialog.py --freigeben alle
python3 scripts/social_dialog.py --verwerfen m7f3a2
python3 scripts/social_dialog.py --status           # nur Cockpit neu schreiben
python3 scripts/social_dialog.py --selftest         # offline, fail-closed
```

### Kanäle

| Kanal | Quelle | Zustand |
|---|---|---|
| Mastodon | Erwähnungen | aktiv |
| Bluesky | Erwähnungen + Antworten | aktiv |
| Telegram | Nachrichten/Diskussionsgruppe | aktiv |
| YouTube | Kommentare unter Shorts | aktiv |
| Facebook | Kommentare unter Seitenbeiträgen | aktiv |
| Instagram | Kommentare unter Beiträgen | aktiv |
| X | Erwähnungen | **aus** – Lesezugriff nur kostenpflichtig |
| LinkedIn | Kommentare | **aus** – nur für Partner-APIs |
| Threads, Reddit | – | **aus** – erst freischalten, wenn der Kanal bespielt wird |

Fehlt das Secret eines aktiven Kanals, ruht er sichtbar im Cockpit – **kein Fehler,
kein Alarm**. Genau wie beim Social-Autopiloten.

---

## 5. Die Bremsen (gegen Amoklauf und Endlosschleifen)

In `meta:` von `dialog.yaml`:

| Regel | Standard | Warum |
|---|---|---|
| `max_replies_per_run` | 8 | Ein Fehlverhalten bleibt klein |
| `max_replies_per_day_total` | 20 | Kein Bot-Eindruck im Feed |
| `user_cooldown_hours` | 20 | Nie zweimal am Tag an dieselbe Person |
| `lookback_hours` | 72 | Späte Antworten wirken schlechter als keine |
| `min_incoming_chars` | 12 | „👍" braucht keine Antwort |
| `draft_expiry_days` | 5 | Alte Entwürfe verfallen statt zu verwesen |

Zusätzlich: nie zweimal auf denselben Beitrag (State-Abgleich), nie auf eigene
Beiträge, nie auf Bots (Telegram-Flag).

---

## 6. Feineinstellung

**Sachfragen automatisch beantworten lassen** – erst nach ein, zwei Wochen Mitlesen.
In `dialog.yaml`:

```yaml
  frage_faktisch:
    modus: "auto"        # war: review
    belegpflicht: true   # UNBEDINGT so lassen
```

Mit `belegpflicht: true` antwortet der Bot nur, wenn er einen eigenen Artikel als
Beleg hat – sonst wandert die Frage weiter in die Mappe.

**`frage_beratung` niemals auf `auto` stellen.** Das ist die eine Zeile in diesem
ganzen System, bei der ein Klick echten Schaden anrichten kann.

**Ton ändern:** `haltung.tonalitaet` steuert die KI-Politur, `haltung.beratungsklausel`
den Pflichtsatz unter jeder Fragen-Antwort.

**Neue Signalwörter:** einfach unter `signale:` der passenden Klasse ergänzen –
kein Code nötig. Nach jeder Änderung `--selftest` laufen lassen.

---

## 7. Wenn etwas klemmt

| Befund | Ursache | Handgriff |
|---|---|---|
| Kanal meldet „Standby" | Secret fehlt | `docs/RUNBUCH-SOCIAL-SECRETS.md` |
| Alles landet in der Mappe | normal – nur `dank`/`lob` sind auf `auto` | so gewollt |
| „Belegpflicht: kein passender Artikel" | Frage passt zu keinem Beitrag | freigeben (überstimmt die Belegpflicht) oder verwerfen |
| „Cooldown" | Person wurde schon beantwortet | morgen erneut, oder freigeben |
| Telegram findet nichts | Kanal braucht eine verknüpfte Diskussionsgruppe | Gruppe anlegen, Bot als Admin |
| Antwort wirkt zu glatt | KI-Politur | Variable `DIALOG_LLM_MODE=off` → nur Vorlagen |

---

## 8. Dein tatsächlicher Aufwand

Drei Läufe am Tag, ein Issue, Freigabe per Workflow-Klick:
**etwa 5 Minuten, dreimal pro Woche.** Weniger sollte es bei einem Finanzblog
auch nicht werden – die Freigabe ist kein Umweg, sondern die Haftungsgrenze.

---

*Zugehörig: `scripts/social_dialog.py` · `data/social/dialog.yaml` ·
`.github/workflows/social-dialog.yml` · `SOCIAL-DIALOG-STATUS.md` (Lauf-Artefakt)*

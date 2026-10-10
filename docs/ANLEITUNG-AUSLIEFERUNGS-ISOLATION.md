# Anleitung: Auslieferungs-Isolation (ein Befund friert nicht die ganze Site ein)

**Vorgang:** Bot-Watchdog · Meldung #676 · Stand 09.10.2026
**Code:** `scripts/release_isolation.py` · **Tests:** `scripts/tests/test_release_isolation.py`
**Messung:** `scripts/release_scorecard.py` (unverändert die SSOT) · **Zustand:** `scripts/park_state.py`
**Vorgangsbericht:** `BOT-WATCHDOG-676-DAUERHEILUNG-PREMIUM-2026-10-09.md`

---

## 1. Wozu die Isolation da ist

Am 09.10.2026 meldete der Bot-Watchdog (#676): *„Neuester Artikel nicht live"* –
`/posts/2026-10-07-campingurlaub-2026-clever-sparen-ohne-komfortverlust/`
lieferte **HTTP 404**. Der Artikel lag veröffentlichungsreif im Repo
(`draft: false`, redaktionell geprüft, Cover, Quellen, Faktencheck).

Die Ursache stand nicht im Artikel und nicht im Deploy-Trigger:

```
deploy.yml · Job „deploy"
  Schritt „Release-Scorecard (Produktionswahrheit versiegeln, fail-closed)"
  → Exit 1 · 13 Fehlschläge in Folge (seit 02:12 UTC)
```

Der Befund war **ein Satz in einem Artikel**: `RD1-duplikate` maß den
End-CTA „👉 **Jetzt das Tagesgeld-Angebot der C24 Bank ansehen:** …" als
`D3-X` „Absatz wortgleich in 2 Artikeln" – obwohl
`affiliate_intent_contract.py` genau diesen Wortlaut verbindlich
vorschreibt und die Intent-Wache ihn prüft.

**Die eigentliche Schwäche war der Blustradius.** Die Scorecard steht vor
`upload-pages-artifact`. Ein roter Kandidat brach damit nicht *diesen
Artikel* zurück, sondern das komplette Pages-Deployment:

| | vorher | jetzt |
|---|---|---|
| 1 Kandidat blockiert | **0** Artikel ausgeliefert, 42 Live-Artikel eingefroren | dieser eine zurückgestellt, Quote nachgefüllt, **der grüne Rest ausgeliefert** |
| Vertonung, Suchindex, `deploy-pages` | liefen nie | laufen |
| Ticket-Aussage | „Deploy prüfen, ggf. Catchup triggern" | „Deploy stirbt seit N Läufen am Schritt X" |

Der Deploy-Catchup lief stündlich und hatte den Deploy sechsmal angestoßen –
alle sechs Läufe starben amselben Schritt. Der Ratschlag im Ticket beschrieb
also eine Maßnahme, die den Ausfall nachweislich verlängerte.

Dazu kam die Sackgasse: `RD1-duplikate` ist in `data/release_scorecard.yaml`
mit `entscheidung: auto` deklariert – eine Maschine könne ihn heilen.
Cross-Artikel-Duplikate werden aber nie auto-gefixed
(`duplikat_guard.py`: *„der Heilweg läuft über die Redaktion"*). Ein harter
Blocker ohne Heiler ist genau die Klasse aus Regel **C29**.

---

## 2. Was die Isolation tut (und was nicht)

`release_isolation.py` misst den Deploy-Scope über **dieselbe**
Scorecard-Engine (`release_scorecard.durchfuehren()` + `exit_code()`) – keine
zweite Messregel, keine zweite Ampel (Lektion #521, Regel C19).

Für jeden Kandidaten mit Urteil `blockiert` **oder** `nicht beweisbar`:

1. `park_state.hold()` → `draft: true` + `cadence_grund` mit Check-ID und
   Befund. **`hold`, nicht `park`**: ohne `cadence_wait` holt die Automatik
   den Artikel nicht in den nächsten Slot zurück. Die Blockade bleibt
   sichtbar, bis der Befund wirklich aufgelöst ist.
2. `publication_release.refill_until_min(finalize=False)` → Quote bis
   LIVE-Mindestziel (#287/#610).
3. `hugo --minify --destination public` → Render-Beweis erneuern. Ohne
   Rebuild würde die zweite Messung einen Build prüfen, in dem der isolierte
   Artikel noch steckt (Mess-Artefakt, C33).
4. Erneut messen. Begrenzte Konvergenz über `--runden` (Default 3).

**Ausdrücklich nicht:**

| Nicht | Warum |
|---|---|
| Kein `|| true`, kein `continue-on-error` | Exit 1 bleibt rot und stoppt den Deploy |
| Kein Umschreiben von Artikeltext | Isolation stellt zurück, sie redigiert nicht |
| Kein `park()` | Der Artikel käme automatisch wieder – die Blockade wäre unsichtbar |
| Keine Isolation bei Werkzeugfehler (Exit 2) | Eine ausgefallene Messung ist kein Inhalt (C33) |
| Keine unbegrenzte Runde | `MAX_ISOLATIONEN_PRO_LAUF = 6`: ein strukturelles Problem soll rot bleiben, nicht den Vorrat leerräumen |

**Exit-Codes (Vertrag):**

| Code | Bedeutung |
|---|---|
| `0` | Deploy-Scope freigabe-reif – Auslieferung darf laufen |
| `1` | nach allen Runden weiterhin blockiert – Deploy stoppt ehrlich |
| `2` | Werkzeugfehler – fail-closed, Isolation greift bewusst nicht |

---

## 3. Bedienung

```bash
npm run test:isolation          # Selbsttest + 21 Vertragstests
npm run release:isolation       # Trockenlauf: Befund zeigen, nichts schreiben
python3 scripts/release_isolation.py --runden 3     # Deploy-Pfad
python3 scripts/release_isolation.py --selftest
```

`FF_ISOLATION_OHNE_BUILD=1` überspringt den Rebuild (nur für Proben ohne
Hugo – in der Kette niemals setzen).

---

## 4. Einordnung in die Deploy-Kette

```
Build (Produktions-Build, public/)
  → Publish-Gate
  → Quote-Nachfüllung nach Gate-Verlust (#287)
  → Auslieferungs-Isolation (#676)          ← NEU
  → YMYL-Bestand
  → Gate-Heilungsdiff merken / committen    ← übernimmt den hold-Commit
  → Rebuild nach Heilungen                  ← sieht den isolierten Stand
  → finale Veröffentlichungs-Gates (Themenwelten, Werkzeuge, Anker …)
  → Release-Scorecard (hart, fail-closed)   ← unverändert der Endpunkt
  → Vorlese-Audio · Pagefind · gh-pages · deploy-pages
```

Die Isolation steht bewusst **vor** dem Gate-Heilungsdiff: Sie ändert
Content, und der bestehende Commit-/Rebuild-Pfad der Kette übernimmt genau
das. Die finale Scorecard bleibt der harte Endpunkt – was dort rot ist, geht
nicht live.

---

## 5. Wenn das Ticket trotzdem kommt

Der Watchdog-Befund `live-site` trägt seit #676 die Ursache mit:

```
DEPLOY_FEHLERSCHLAEGE=13
DEPLOY_SCHRITT=Release-Scorecard (Produktionswahrheit versiegeln, fail-closed)
DEPLOY_RUN=37963585911
```

Reihenfolge der Prüfung:

1. **`DEPLOY_SCHRITT` lesen.** Er nennt den Gate, nicht den Artikel.
2. **`RELEASE-SCORECARD.md`** – welcher Check, welcher Artikel.
3. **`cadence_grund` im Frontmatter** des isolierten Artikels – der Befund
   steht dort wörtlich, mit Check-ID.
4. Erst danach der Deploy selbst. Ein Catchup wiederholt nur denselben
   Fehlschlag, solange der Gate rot ist.

Ein Artikel im `hold` ist **Material, kein Abfall**: Er bleibt im Bestand,
der Grund steht im Frontmatter, und er geht wieder live, sobald der Befund
aufgelöst ist (`park_state.release()` – nie automatisch).

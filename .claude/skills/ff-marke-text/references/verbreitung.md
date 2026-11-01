# Verbreitung: Pinterest und Instagram-Winkel

> Wörtlich aus `CLAUDE.md` übernommen am 01.11.2026 (Skill-Umbau). Kein Satz wurde umformuliert, gekürzt oder erfunden; die Überschriften sind eine Ebene tiefer gehängt. Änderungen hier sind Änderungen am Regelwerk – sie brauchen denselben Nachweis wie vorher: Selbsttest der betroffenen Wache, dann Commit.

### Ein Befund ohne Heiler ist ein Dauerläufer (Pinterest P8, C37, seit #729, 13.10.2026)

Der Pinterest-Watchdog öffnete am 13.10.2026 das Issue #729 mit genau einem
offenen Posten – „5 Hashtags (max. 3)" in einer `pin_description` – und hätte
es nie wieder schließen können: Der Workflow schließt nur bei Exit 0, und P8
heilte nichts – es war der **einzige offene Posten** des Laufs. Der Befund
wurde täglich neu gemessen und täglich neu gemeldet. Dieselbe Bauart wie C29
– ein harter Blocker braucht einen Heiler, sonst wird der Melder zum
Dauerläufer.

Beim Heilen kamen zwei blinde Flecken derselben Prüfung ans Licht:

- Beide Prüfer zählten Hashtags mit einem Muster, das Umlaute ausschließt
  (`#([a-z0-9]+)` bzw. `[A-Za-z0-9]+`): `#zählerstand` galt als „#z",
  `#ersteWohnung` als „#erste" – die Umlaut-Regel dahinter war **toter Code**.
- `pinterest_seo_healer.py` (H6) sah die Klasse in seinem Audit, hielt den
  Text aber für gültig (nur Länge und `&`) und überschrieb ihn deshalb nie:
  Prüfer und Heiler widersprachen sich.

- **Eine Quelle.** `scripts/pinterest_hashtags.py` trägt die Regel H1–H6
  (max. 3, nur `[a-z0-9]`, 3–24 Zeichen, Zahlenschilder wie `#1` sind keine
  Tags, Block am Textende) und ist als Wache im vertraglichen Minimum
  eingetragen (C6: `--selftest`), mit `--wirkungsprobe` daneben.
- **Ein Schließpfad.** `pinterest_check.py --fix` heilt die `pin_description`
  an der QUELLE: falten, hinten auf drei kappen (die Reihenfolge im Text ist
  die Priorität – es wird nie ein Thema erfunden), Block ans Textende. Die
  Heilung ist idempotent und fail-closed: ändert sie nichts, bleibt der Befund
  stehen. Nach der Heilung ist der Build desselben Laufs älter als der Fix –
  das ist kein offener Befund, sondern wird als FIX belegt.
- **Keine zweite Zahl.** Alle Pinterest-Schreiber importieren die SSOT
  (`pinterest_check`, `pinterest_seo_healer`, `pinterest_duplicate_guard`,
  `pinterest_pin_text_sync`, `pinterest_engine`, `generate_pins`,
  `engine_generate`, `spam_guard`); der SEO-Heiler prüft die Gültigkeit jetzt
  ebenfalls über `ph.ist_konform` statt über Länge und `&`. Auch die
  API-Grenze gehört dazu: `generate_pins.build_api_description()` hängte
  früher drei CamelCase-Tags hinter jeden kuratierten Text (aus drei Tags
  wurden sechs, aus 478 + Block über 500 Zeichen).
- **Wirkung, nicht Absicht.** C37 prüft jede `pin_description` im Bestand
  gegen die SSOT – ein neuer Artikel mit fünf Tags macht den Vertrag rot,
  bevor der Watchdog ein Issue eröffnet. Der Quellfingerabdruck kennt die
  Regel (Report-Schema 4), und `pinterest_check.py` weist übersprungene
  HTML-Prüfungen im Report als „nicht gemessen" aus (C2), statt Grün zu
  behaupten.
- Tests: `python3 -m unittest scripts.tests.test_pinterest_hashtags scripts.tests.test_pinterest_check`
  (45) · Bericht: `PINTEREST-729-HASHTAG-DAUERHEILUNG-PREMIUM-2026-10-13.md`.

### Eine Prüfung muss die richtige Menge messen (Pinterest P10/P14, C43, seit #822, 24.10.2026)

Der Pinterest-Watchdog meldete vom 20. bis 24.10.2026 **jeden Tag denselben**
Posten: „[P10] 2026-08-12-dein-haus-sicher-schuetzen… Artikel-Seite ist ein
Meta-Refresh-Alias – nicht direkt pinnen“. Der Artikel **war** ein Alias – und
zwar der gewollte: Er ist seit 19.10.2026 nach dem Redaktions-Standard
(RS1–RS3) geparkt (`draft: true`), seine URL steht in
`data/weiterleitungen.yaml` als Regel C. Die Meta-Refresh-Seite unter
`static/posts/<slug>/` war die Auslieferung, nicht der Defekt. P10 maß die
falsche Menge: `_post_slugs()` kennt Entwürfe, P10 fragte aber nie, ob der
Slug überhaupt live ist. Ein Befund ohne Schließpfad – dieselbe Bauart wie C37.

Zwei Lehren, die über Pinterest hinausgehen:

- **Eine Prüfung ohne Mengen-Begriff ist ein Dauerläufer.** „Seite ist ein
  Redirect“ ist kein Defekt, solange nicht feststeht, *welche* Seiten Inhalt
  liefern müssen. Verbindlich ist jetzt: Live-Artikel (Hugo-Logik, `draft:
  true` zählt nicht) liefern Inhalt; eine geparkte URL darf weiterleiten, wenn
  die SSOT es erklärt – und dann steht das ausdrücklich im Report („kein
  Befund“ heißt nicht „nicht gemessen“, C2). Dieselbe Live-Definition benutzen
  `url_wache.py`, `weiterleitungen.py` und jetzt `pinterest_ziele.py`
  (`weiterleitungen.live_urls`) – keine zweite Draft-Erkennung.
- **Der Blick auf die Daten fand den eigentlichen Defekt.** Während P10 den
  Betriebszustand anzeigte, standen **7 von 46 Pins** im Masterplan auf
  Zielen, die keine Artikel-Seite mehr sind (4 geparkte Entwürfe, 3 URLs ohne
  Inhalt). Genau davor warnt P10 seit jeher – nur prüfte niemand den Plan.
  P14 misst jetzt jedes Pin-Ziel (Masterplan + Queue) und heilt **nur über die
  SSOT**: Regeln A/B (gleichwertiger, geprüfter Live-Nachfolger) werden
  umgeschrieben, alles andere wird geparkt (kein Content-Verlust), Queue-
  Einträge entfernt. Kein Ziel wird geraten, kein Pin gelöscht.
- **Eine Wache ohne Fahrer ist keine Wache.** `pinterest_link_guard.py`
  (L1/L2: jedes Pin-Ziel gegen den Bestand) hat den Befund am 24.10.2026
  unabhängig reproduziert – und wurde von **keinem** Workflow aufgerufen. Sie
  läuft jetzt im Pinterest-Watchdog (gleiches Issue, kein zweiter Kanal), und
  ihr `--selftest` steht im vertraglichen Minimum (C6).
- **Heilung in beide Richtungen, fail-closed.** Überdeckt eine Weiterleitung
  einen LIVE-Artikel, gewinnt der Artikel (SSOT-Eintrag + Alias-Seite weg,
  chirurgisch, nachgeparst, sonst nichts geschrieben). Handgebaute Alias-Seiten
  bleiben ein Befund für Menschen.
- **Vertrag C43** friert das ein (Quelle, Menge, Schließpfad, Wirkung am
  Bestand, Fahrer, Nachweis Report-Schema 5, Tests). Prüfung:
  `python3 scripts/governance_contract.py --selftest` ·
  `python3 -m unittest scripts.tests.test_pinterest_ziele scripts.tests.test_pinterest_check`.
  Bericht: `PINTEREST-822-DAUERHEILUNG-PREMIUM-2026-10-24.md`.

### Ein Falschurteil darf nie alle Winkel treffen (#716-Familie, seit 14.10.2026)

Der Ratgeber „DNS-Server wechseln“ war auf Instagram in **keinem** Winkel
sendbar (CI `regression` rot seit #743). Zwei Ursachen verstärkten sich:
L7 zählte die Fachkürzel DNS/HTTPS/TLS als Versalien-Geschrei (13 % > 12 %),
und die Instagram-Caption war winkelblind – alle sechs Winkel ergaben Wort für
Wort denselben Text, das Nachrücken auf einen anderen Winkel lief ins Leere.

- **Ein fail-closed-Gate urteilt mit Beleg.** L7 unterscheidet Fachkürzel von
  Geschrei wie L9 Zahlen: belegt ist, was der Haus-Kanon (`tag_casing`) in
  Versalien führt oder der Artikel selbst so schreibt. Schreiwörter
  (`meta.gate.schrei_woerter` + Standardliste), Versalwörter über sechs
  Buchstaben und Wörter, die der Artikel normal schreibt, bleiben Geschrei.
- **Belegmaterial = was der Texter zitieren darf.** Die FAQ zählt dazu, weil
  der Winkel `frage` sie wörtlich aus dem Artikel übernimmt.
- **Jeder Winkel ist ein eigener Zugang** (`_visual_winkel`): Fehlt einem
  Winkel sein Material, fällt er auf den Nutzen-Text zurück, statt etwas zu
  erfinden. `karussell` verspricht keine Folien, solange der Adapter ein
  Einzelbild sendet.
- **Frühwarnung statt Vollausfall:** `test_social_instagram_winkel` verlangt
  je Kanal und Artikel mindestens zwei sendbare Winkel, auf Instagram drei
  verschiedene sendbare Captions. Vorher stand Bluesky im selben Bestand bei
  einem einzigen.
- **Verbrauch ist kein Drift.** Ein veröffentlichter Reserve-Entwurf
  (`draft: false` + `reserve_published`) wird nicht „nachzertifiziert“ – es
  gibt keinen Entwurf mehr, an dem man messen könnte. `reserve_recert.py --fix`
  bucht ihn **ohne Messkette** aus; `generated_at`/`measured_at` bleiben
  unberührt, der Bestand kann dabei nur kleiner werden.
- Tests: `python3 -m unittest scripts.tests.test_social_instagram_winkel scripts.tests.test_social_gate_l9 scripts.tests.test_reserve_recert`
  · Bericht: `SOCIAL-INSTAGRAM-716-FAMILIE-DAUERHEILUNG-PREMIUM-2026-10-14.md`.

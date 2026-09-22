# Newsletter-Studio auf Agentur-Niveau – Report 22.09.2026

**Ziel (Frank, wörtlich):** „eine Newsletter-Funktion auf Premium-Level einer
Profi-Agentur von migma.ai in meinen Blog nachbauen, sodass mir keine Kosten
entstehen."

**Auftrag, so wie er umgesetzt wurde:** Migma ist kein Design-Tool, sondern eine
Arbeitsteilung – Creative → Design → QA → Versand, mit Marke aus dem Bestand statt
aus dem Kopf. Nachgebaut ist diese Kette, nicht ihr Preisschild. Der
Kosten-Parameter war keine Präferenz, sondern eine harte Kante: **kein KI-API-Key,
kein Bild-Dienst, kein SaaS-Sitz, kein Cookie-Zuwachs.** Alles hier läuft mit Hugo,
Python-Standardbibliothek, GitHub Actions – und dem Brevo-Free-Plan, der schon im
Repo verdrahtet war (300 Mails/Tag, reicht weit über diesen Blog hinaus).

Was am Ende **nicht** gebaut wurde, steht in § 7 – es ist die Liste der Dinge, die
Geld kosten würden, wenn man sie ehrlich baut.

---

## 1. Geliefert: fünf Schichten statt ein Formular

| Schicht | Neu/Geändert | Kern |
|---|---|---|
| Studio (Design-System + Textfabrik) | `scripts/newsletter_studio.py`, `data/newsletter_studio.json` | 28 Farbrollen, je hell/dunkel, **aus dem Build-CSS hergeleitet**; Block-Engine (kopf → hero → artikel → fuss); Betreff-Rotation in 3 Varianten (30–45 Zeichen), Preheader, Textalternative; `--brand`, `--build`, `--vorschau` |
| Vor-Versand-Wache | `scripts/newsletter_qa.py` | 20 Regeln, Score 100 − 10·Funde − 3·Warnungen; Exit 0/1/2; liest das gebaute Mail, nicht die Absicht |
| Versand-Gate | `scripts/newsletter_digest.py` | QA läuft **vor** jedem `--send` und blockiert; Betreff-Verlauf und Versandgedächtnis jetzt aus der Konfiguration |
| Capture + Journeys | `layouts/shortcodes/newsletter_{form,status,weg,themen,muster}.html`, `layouts/_partials/newsletter_{strip,studio_data}.html`, `content/newsletter*/`, `assets/css/extended/zz-newsletter.css`, `static/premium/ff-newsletter.js` | Drei-Zweig-Formular (Inline / Anbieter-Button / ehrlicher Leerzustand), Präferenz-Chips, Einwilligungs-Block, Bot-Falle ohne Drittanbieter, Bestätigungs-/Präferenz-/Abmeldeseite, Marken-Streifen an Artikel-Ende und im Fuß |
| Beweise | `scripts/tests/test_newsletter_{studio,qa,site}.py`, `e2e/newsletter.spec.mjs`, `docs/ANLEITUNG-NEWSLETTER-STUDIO.md` | 90 Unittests, 101 Selbsttest-Fälle in drei Wachen, Playwright-Spec, Werkstatt-Doku |

## 2. Funde, die dieser Lauf behoben hat

### F1 – Der Abmeldelink war toter Code (KRITISCH, latent)

`newsletter_digest.py` baute den Fuß mit Brevo-Markern der **alten** Vorlagen-Sprache:
einzelne Klammer, `{unsubscribe}`. Kampagnen aus `htmlContent` laufen bei Brevo seit
langem über die New Template Language – die ersetzt **`{{unsubscribe}}`** und
lässt eine Einzelklammer als sichtbaren Text stehen. Der Fehler war unsichtbar, weil
alles andere stimmt: Der Link ist da, der Satz klingt richtig, kein Tool meckert.
Verschickt hätte er eine Mail ohne Abmeldung – in DE der schnellste Weg zu einer
Beschwerde, und die erste Mail, die jemand im Postfach nicht abbestellen kann, wird
nicht abbestellt, sondern gemeldet.

**Behoben:** Das Studio besitzt jetzt das Markup und schreibt `{{unsubscribe}}`,
`{{mirror}}`, `{{update_profile}}`; QA **Q3** macht jede Einzelklammer und jeden
unbekannten Platzhalter zu einem Fund, der den Versand blockiert.

### F2 – Die Prüfung lief, wo sie nicht blockieren konnte

Der Workflow baute und prüfte Digeste, aber zwischen „geprüft" und „gesendet" lag
nichts. Jetzt ruft `newsletter_digest.versende()` `newsletter_qa.pruefe()` auf,
**bevor** die Kampagne bei Brevo als draft angelegt wird, und bricht bei einem Fund
mit Exit 1 ab; `--trotz-qa` existiert als Notausstieg und wird vom Workflow nicht
gesetzt. Der doppelte Boden: Die Wache prüft das gebaute Mail, nicht die Konfiguration –
ein Edit im Template kann sie nicht mehr umgehen.

### F3 – Ein Test, der am Tag der Freischaltung rot geworden wäre

`test_landingsseite_ist_gebaut_und_ohne_falsches_versprechen` setzte den *jetzigen*
Zustand als Invariante („kein `<form>`"). Sobald der Anmeldeweg gesetzt ist, wäre er
wegen Erfolgs fehlgeschlagen – die gefährlichste Testform, weil sie das Abgewöhnen
von Grün bedeutet. Jetzt liest der Test zuerst `newsletter_digest.params()` undprüft
dann in beiden Zweigen: geschaltet → `<form>`, `name="email"`, Double-Opt-In-Hinweis,
Datenschutz-Link; ungeschaltet → ehrlicher Leerzustand, kein Formular.
Gemeinsame Pflichten (noindex, kein Sitemap-Eintrag, kein erdachter
`/datenschutz/#newsletter`-Anker) gelten immer.

### F4 – Konfiguration, der niemand folgte

`data/newsletter_studio.json` hat einen `zustand`-Block mit `datei` und
`betreff_historie`; der Code hatte beides hardcoded (`STATE_REL`, `verlauf[-12:]`).
Eine Datei, die beschreibt, was ein Skript tut, ohne dass das Skript sie liest, ist
der Anfang von zwei Wahrheiten. Jetzt liest `zustand_konfig(root)` Datei **und**
beide Längen (neu: `artikel_historie: 400`), die Konstanten bleiben Default für
Checkouts ohne Studio-JSON. Selbsttest-Fall 9c verlagert die State-Datei und fällt
um, wenn jemand die Verdrahtung wieder löst.

### F5 – Die Zeitfalle hätte echte Anmeldungen gefressen

Der erste Wurf des Anmelde-Skripts blockierte stillschweigend, wenn das Formular in
unter 1,5 Sekunden abgeschickt wurde – und meldete „Danke". Ein Mensch mit
Autofill ist nach 1,2 Sekunden fertig. Ergebnis: zahlende Anmeldungen, spurlos
verschluckt, und niemand weiß es, weil die Meldung freundlich war. Jetzt ist die
Zeit ein **Merkmal für den Empfänger** (`_zeit` wird mitgeschickt), blockiert wird
allein durch den Honigtopf – ohne Begründung, denn ein Angreifer lernt aus der
Rückmeldung mehr als aus dem Schweigen.

### F6 – Drei kleine Lügen im großen Text

* `ANLEITUNG-NEWSLETTER.md` schrieb „Es fehlen ausschließlich die drei Klicks" und
  „§ 8 behauptet derzeit, es gebe keinen Newsletter" – beides war nach dem Bau von § 8
  falsch. Der Schritt-5-Text beschreibt jetzt, **warum** der Widerspruch nicht mehr
  baubar ist (Website, Wache und Rechtstext lesen `data/newsletter_studio.json`),
  und die Überschrift bleibt, weil die Wache den Abschnitt darüber findet.
* Die Rechtstext-Kurzform versprach „Versand-Statistik (Öffnungs-/Klickraten)".
  `email.tracking_oeffnungen` steht auf `false`, und Q19 bricht den Versand, falls die
  Mail trotzdem ein Pixel enthält. Der Text sagt jetzt die Wahrheit **und** verweist
  auf die eine Stelle, die beide Seiten gleichzeitig umstellt.
* `--varante` / `varanten` war auf beiden Seiten gleich falsch getippt – ein
  Config-Wert, den nur findet, wer den Tippfehler kennt. Umbenannt auf
  `--variante` / `varianten`.

### F7 – Design-Regeln, die ich selbst gebrochen hatte

Meine Formular-CSS transitionierte `border-color`, `background-color`,
`box-shadow`. DESIGN.md §7 erlaubt Übergänge nur auf `transform`/`opacity`/`color`.
Erledigt (Fokus-Ring jetzt bewusst ohne Übergang – eine Verzögerung beim
Tastaturfokus ist ein Barriere-Problem, kein Schönheitsfehler), und der Test
`test_dark_mode_und_tokens` hält die Regel jetzt mit einer Regex fest, die jeden
anderen Eigenschaftsnamen im Layer meldet.

Zwei winzige Dinge, die derselbe Test-Fundstrom gefischt hat: die Klasse
`.ff-nl-strip__cta-text` wurde gerendert, ohne dass eine Regel existierte
(Regel ergänzt: `white-space: nowrap`, damit „Anmelden" nie umbrochen wird), und
der Streifen setzte `ff-nl-strip--footer` für eine Variante, die das CSS nicht kennt
(Modifier wird nur noch gesetzt, wo er eine Regel hat).

### F8 – Doppelzweige und toter Code

`versende()` hatte zweimal `if not test_adresse:` untereinander (zwei Zustands-Updates
an einem Ort, eines davon unnötig lesbar); `konfiguration()` warf in beiden Zweigen
desselben `if not streng:` dasselbe. Zusammengeführt bzw. zu einer klaren Aussage
gemacht: **kaputtes JSON ist ein Fehler, kein Leerzustand** – wer hier still auf
Codewerte fiele, verschickt im ungünstigsten Fall ein Mail ohne eigene Marke.

## 3. Belege statt Adjektive

| Was | Wert | Wo nachzuprüfen |
|---|---|---|
| Unittests Newsletter | 90 OK (1 Skip: kein `public/-Build` hier) | `python3 -m unittest scripts.tests.test_newsletter_{studio,qa,site} scripts.tests.test_newsletter_digest` |
| Selbsttests der Wachen | Studio 41 · QA 35 · Digest 25 = **101 Fälle** | `--selftest` je Skript |
| Uhrfestigkeit | alle drei bestanden `selftest_runner` inkl. +97 und +1461 Tage | `python3 scripts/selftest_runner.py` |
| Vor-Versand-Prüfung am Live-Bestand | **100/100 · 20 Regeln · 0 Funde** (301 Wörter, 13 Links, 0 Bilder) | `python3 scripts/newsletter_qa.py --build --days 400` |
| Marken-Deckung | 28 Farbrollen aus dem Build-CSS hergeleitet, 6 Themenwelten deckungsgleich mit `data/themenwelten.json` | `python3 scripts/newsletter_studio.py --brand` |
| Kontrast gemessen (WCAG 2.1) | hell min 5.25:1, dunkel min 4.91:1 (Pflichtpaare, 2×8) | `--brand`-Ausgabe, Q11 |
| Eine gebaute Ausgabe | 5 Artikel-Blöcke, 14 161 Bytes, 63 `style`-Attribute, 2 Media-Queries, 2 VML-Knöpfe, 17 Links | `.cache`-Ausgabe von `--build --out` |
| Kein totes Versprechen | Formular-Zweig 3 (Leer) zeigt „nicht geschaltet" statt eines Felds; Streifen und CTA ausgeblendet, bis ein Weg konfiguriert ist | `e2e/newsletter.spec.mjs`, `newsletter_digest.py --check` |

## 4. Warum die Zahlen belastbar sind (drei Konstruktionsregeln)

1. **Regeln messen, nicht vergleichen.** Q11 rechnet Kontraste aus den aufgelösten
   Tokens; Q16 vergleicht Ziffernmengen (`2.800 €` = `2 800 €` = `2800 €`), weil ein
   Stringvergleich von formatierten Zahlen gegen Quelltext False-Positives produziert
   hat – der Fix sitzt jetzt in `zahlen_im_text()`.
2. **Jede Regel wird mit einer gezielten Manipulation geprüft.** QA-Selbsttest manipuliert pro Regel
   genau eine Eigenschaft (Einzelklammer, `<script>`, `display:flex`, 103 KB,
   Kontrast `#404040` auf Dunkel, fehlender Viewport, unbelegte `12.450 €`,
   Tracking-Pixel) und verlangt den **richtigen** Regelcode. Eine Wache, die bei allem
   Q1 meldet, ist keine.
3. **Warnung ≠ Blockade.** Nur Funde stoppen den Live-Versand; Warnungen stehen im
   Report. Sonst wird die Wache am ersten Montag deaktiviert, an dem nichts kaputt war.

## 5. Aktivierung – was dir bleibt, und warum es nicht erfunden wurde

Geschaltet wird über **einen** Eintrag (`capture.form_action` in
`data/newsletter_studio.json`, oder `params.newsletterFormAction` in `hugo.toml`,
das gewinnt): Formular, Streifen, Footer-CTA, Journeys und Rechtstext-Satz folgen
automatisch, weil alle dieselbe Quelle lesen. Dazu die drei Dinge, die ein Konto
brauchen und die kein Skript für dich erfinden darf: Brevo-Signup, SPF/DKIM für
`kontakt@franksfinanzcheck.de`, AVV/DPA abschließen. Reihenfolge und Wortlaut:
`docs/ANLEITUNG-NEWSLETTER.md` (Schritte 1–6) und
`docs/ANLEITUNG-NEWSLETTER-STUDIO.md` § 7.

## 6. Was im Repo gilt (und hier mitläuft)

`newsletter_studio.py` und `newsletter_qa.py` sind in `governance_contract.GUARDS`
aufgenommen – ihr `--selftest` läuft damit in jedem Push/PR durch
`selftest_runner.py` (Entdeckung im Dateibaum, nicht abgetippte Liste) und ist
uhrgeprüft. `hugo.toml`, `data/integrity_lock.json`, `extend_footer.html`,
`custom.css` und die Workflow-Dateien sind **unberührt**: `integrity_guard.py
--check` meldet „Kern entspricht exakt dem letzten signierten Zustand". Der
QA-Gate sitzt deshalb im Skript, nicht im Workflow – der Agent-Token hat keine
`workflows`-Berechtigung, und ein Gate, das eine Datei anfassen müsste, um zu
gelten, wäre keiner.

## 7. Was 0 € hier nicht kann (die ehrliche Liste)

* **Kein KI-Texten.** Betreff, Preheader und Anriss sind deterministisch aus
  `kurzantwort`/`description` gebaut; Zahlen kommen ausschließlich aus dem
  Artikeltext, mit Belegstelle (Q16 blockiert sonst). Ein LLM wäre eine zweite
  Kostenstelle und eine zweite Fehlerquelle – und für einen Blog, dessen Wert in
  nachrechenbaren Rechnungen liegt, die schlechtere der beiden.
* **Keine Echtgeräte-Render-Matrix** (Apple Mail/Gmail/Outlook-Screenshots, wie sie
  bezahlte Tools verkaufen). Ersatz: harte Regeln für genau das, was diese Clients
  zerlegen – Tabellenlayout, VML-Knopf, `max-width`, kein Flex/Grid/`@import`/Iframe,
  keine CDN-Schriften. Manuelle Stichprobe: `vorschau.html` in Outlook öffnen.
* **Keine KI-Bildgenerierung** für Header. `email.header_bild` ist leer gelassen;
  wenn du Bilder willst, liegen sie wie die Blog-Cover im Repo, und Q5 verlangt
  `alt`/Breite/Höhe.
* **Kein „competitor tracking"** (Migma abonniert im Namen des Kunden Newsletter der
  Konkurrenz). Abgesehen davon, dass es ein Abo-Feature ist: Listen über
  Proxy-Mails füllen ist der Weg in den Spam-Ordner des eigenen Absenders.
* **Kein eigenes Backend** für die Präferenzverwaltung. Präferenzen laufen über die
  Liste/Segmentierung des Anbieters; `capture.praferenz_url`/`abmelde_url` sind
  bewusst leer und die Shortcodes zeigen dann den Ersatztext statt eines toten Knopfs.

## 8. Verifikation hier vs. in CI

In dieser Arbeitsumgebung ist **kein Hugo-Binary** ladbar (GitHub-Releases und
Deb-Mirror sind blockiert), deshalb: kein `hugo`-Build, keine Playwright-Ausführung,
kein `dom_audit`/`layout_audit` gegen `public/`. Der eine Skip in den Unittests
dieses Laufs ist genau das. Alles andere ist hier gelaufen (101 Selbsttest-Fälle,
90 Unittests, `--brand`, `--build`, `--check`, QA am Live-Bestand,
`selftest_runner` gegen die Uhr). Die Render-Wahrheit – Shortcode-Auflösung,
`public/newsletter/index.html`, Kontrast im Browser, Formular-Interaktion –
liefert der CI-Lauf: Job *Newsletter-Wache* in `link-check.yml` und
`e2e/newsletter.spec.mjs` (beides spec- und testseitig so gebaut, dass es im
Leerzustand **und** nach der Freischaltung grün ist).

## 9. Dateien

```
scripts/newsletter_studio.py                    (neu)  Design-System, Material, Blöcke, HTML/Text, --brand
scripts/newsletter_qa.py                        (neu)  20 Regeln, Score, --md/--json, --selftest
scripts/newsletter_digest.py                    (geän.)  Studio-Delegation, QA-Gate, zustand-Konfig, 25 Fälle
scripts/governance_contract.py                  (geän.)  zwei Wachen registriert
scripts/tests/test_newsletter_studio.py         (neu)  28 Tests
scripts/tests/test_newsletter_qa.py             (neu)  21 Tests
scripts/tests/test_newsletter_site.py           (neu)  24 Tests (Vorlagen, CSS, JS, Journeys, Datenschutz)
scripts/tests/test_newsletter_digest.py         (geän.)  Landungsseiten-Test als Invariante
data/newsletter_studio.json                     (neu)  eine Quelle für Marke, Texte, Felder, Journeys
data/newsletter_state.json                      (unverändert gelassen – der Workflow schreibt sie)
layouts/shortcodes/newsletter_form.html         (neu)  3-Zweig-Formular
layouts/shortcodes/newsletter_status.html       (neu)  Schaltzustand für Rechtstexte
layouts/shortcodes/newsletter_weg.html            (neu)  konfigurierbarer Ausweg statt toter Knopf
layouts/shortcodes/newsletter_themen.html       (neu)  Präferenzwelten aus data/themenwelten.json
layouts/shortcodes/newsletter_muster.html       (neu)  Vorschau aus dem echten Bestand
layouts/_partials/newsletter_studio_data.html   (neu)  hugo.toml > JSON, ohne site.Data
layouts/_partials/newsletter_strip.html         (neu)  ein Streifen, drei Orte, Doppel-CTA-Schutz
layouts/single.html, layouts/_partials/footer.html (geän.)  Streifen-Hooks
assets/css/extended/zz-newsletter.css           (neu)  Formular, Chips, Streifen, Journeys, hell/dunkel
static/premium/ff-newsletter.js                 (neu)  Validierung, Honigtopf, same-tab-POST, Merker
content/newsletter/index.md                     (neu)  mit Muster-Ausgabe
content/newsletter-bestaetigung/-praeferenzen/-abmelden/ (neu)  Journeys, alle noindex
content/datenschutz/index.md                    (geän.)  § 8 liest den Zustand
docs/ANLEITUNG-NEWSLETTER-STUDIO.md             (neu)  Werkstatt: Befehle, Regeln, Freischalten, Grenzen
docs/ANLEITUNG-NEWSLETTER.md                    (geän.)  Schichttabelle, Rechtliches, Schritt 5
docs/NEWSLETTER-RECHTSTEXT-VORLAGE.md           (geän.)  Status statt offener Aufgabe
e2e/newsletter.spec.mjs                         (neu)  10 Browser-Tests, zustandsneutral
```

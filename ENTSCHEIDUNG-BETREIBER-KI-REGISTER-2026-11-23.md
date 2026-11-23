# Betreiber-Entscheidung: KI-Register, 12 Altartikel (Frist 02.12.2026)

**Datum:** 23.11.2026 · **Frist:** 02.12.2026 — **noch 9 Tage**
**Frist-ID:** `ki-vo-kennzeichnung-bestand`
**Ebene:** Beleg-Zusammenstellung und Technik. **Keine Rechtsberatung.**
**Gegenstand:** `data/ki_kennzeichnung.yaml`, die 12 vormals unter `menschlich` geführten Artikel
**Messstand:** `origin/main` = `96d0256`, gebaut mit Hugo 0.168.0 extended
(Exit 0, 3171 Dateien, 133 Seiten). Jede Zahl in diesem Dokument ist dort
gemessen, nicht abgeschrieben.

---

## 1. Die eine Frage, die nur Sie beantworten können

Das Register führt diese 12 Artikel seit dem 02.08.2026 als `menschlich`. Belege
dafür gibt es keine — das Register sagte es selbst, wörtlich:

> „Unter dem Konto des Betreibers committet (frank-hartung), Herkunft aus dem
> Repo allein NICHT belegbar – teils lauten die Commits ‚optimize articles …‘,
> was auf KI-Agenten hindeutet. BITTE PRÜFEN: Herkunft und tatsächliche
> inhaltliche Prüfung für die veröffentlichte Fassung klären.“

**Am 23.11.2026 wurde diese Lücke geschlossen.** Alle 12 wurden nach
`maschinell` überführt, `menschlich` steht jetzt auf `[]`. Die Wache ist damit
grün, nachgemessen: **Exit 0**, 0 Eskalationen, 0 Funde, Deckung 123/123 Seiten,
50 Feed-Items.

Die Richtungsentscheidung ist konservativ und damit vertretbar: Wer keinen
menschlichen Erstentwurf belegen kann, kennzeichnet lieber. Über-Kennzeichnen
ist rechtlich unschädlich, eine erfundene Positivaussage nicht.

**Aber der Register-Kommentar behauptet eine „konservative
Betreiber-Entscheidung“.** Aus dem Repo allein lässt sich nicht lesen, ob Sie
diese Einordnung selbst vorgenommen haben: PR #1329 trägt
`Co-authored-by: arena-agent`. Dagegen steht, dass im Faktenfrische-Ledger
**47 Entscheidungen** desselben Tages mit dem Vermerk „Betreiber-Freigabe über
Arena-Session, 23.11.2026“ liegen — Sie waren also an dem Tag im Haus, und
zehn dieser Freigaben betreffen zwei der 12 Artikel, ausdrücklich „nach
KI-Kennzeichnungs-Update“ (Abschnitt 4.1). Ob die Register-Umstellung selbst
auf Ihre Anweisung zurückgeht, weiß das Repo nicht.

**Abzeichnen heißt hier nicht, etwas zu ändern.** Es heißt, eine bereits
vollzogene, konservative Einordnung zu Ihrer eigenen zu machen — oder, wo Sie
menschliche Verantwortungsübernahme belegen können, diese benannt
zurückzunehmen. Für zwei der 12 liegt ein solcher Beleg inzwischen vor.

---

## 2. Was bereits geschehen ist, mit Fundstelle

| | |
|---|---|
| Entscheidung | Commit `3718357`, PR **#1329**, merged **2026-11-23T13:01:53Z** |
| Titel | „Vollständige Umsetzung der Profi-Agentur-Empfehlungen (KI-VO, #1263, #1248, Lesbarkeit, Cornerstone, Orphans)“ |
| Autor | `frank-hartung` |
| Mitautor | **`Co-authored-by: arena-agent`** |
| Register vorher | `menschlich`: **12** · `maschinell`: **23** |
| Register nachher | `menschlich`: **[]** · `maschinell`: **35** |
| Wachzustand | `ungeklaert_erstmals: {}` · `revision: 48da9e8` · `zuletzt: 2026-11-23` |
| Begründung im Register | „konservative Betreiber-Entscheidung vor Frist 02.12.2026, EU-KI-VO Art. 50 Abs. 4: alle 12 bislang ungeklärten Altartikel werden transparent als KI-unterstützt gekennzeichnet“ |
| PR-Body, wörtlich | „Alle 12 bisher als `menschlich` **ohne Nachweis** geführten Alt-Artikel konservativ in `data/ki_kennzeichnung.yaml` nach `maschinell` überführt (`menschlich: []`).“ |

**Der einzige Punkt, der Ihre Aufmerksamkeit braucht:** Die Begründung nennt
eine *Betreiber*-Entscheidung, der Commit nennt einen *Agenten* als Mitautor.
Beides kann stimmen — wenn Sie PR #1329 selbst gelesen und gebilligt haben. Wenn
nicht, steht im Register eine Behauptung ohne Beleg, und dann ist Ihre
Unterschrift unter Abschnitt 8 der Beleg.

---

## 3. Rechtlicher Rahmen, wie das Haus ihn dokumentiert hat

Aus `KI-VO-MASCHINENLESBAR-1028-DAUERHEILUNG-HIGHEND-2026-11-05.md`, der
maßgeblichen Haus-Akte. Keine Rechtsberatung, sondern die dort dokumentierte
Rollenteilung:

* **Art. 50 Abs. 2** verpflichtet den **Anbieter** des generativen Systems zur
  maschinenlesbaren Markierung, mit Nachfrist bis 02.12.2026 für Systeme, die vor
  dem 02.08.2026 in Verkehr gebracht wurden (Art. 113 i. d. F. der Verordnung
  (EU) 2026/1744). **Ein Betreiber kann diese Pflicht nicht selbst erfüllen** —
  er kann aber seine eigene Erklärung maschinenlesbar machen und die
  Anbieter-Markierung erhalten, statt sie zu zerstören.
* **Art. 50 Abs. 4** verlangt für **Text**, der die Öffentlichkeit über Fragen
  von öffentlichem Interesse informiert, die Offenlegung künstlicher Erzeugung —
  **außer** der Inhalt war Gegenstand menschlicher Überprüfung und
  redaktioneller Verantwortungsübernahme.

**Genau diese Ausnahme ist der Unterschied zwischen `menschlich` und
`maschinell` im Register.** `menschlich` behauptet die Ausnahme, `maschinell`
verzichtet auf sie und kennzeichnet. Wer die Ausnahme behauptet, braucht den
Beleg. Für diese 12 gibt es keinen — Abschnitt 4.

---

## 4. Beleg-Lage je Artikel

Vier unabhängige Quellen je Artikel: Entstehungs-Commit (über die GitHub-API
geholt, der lokale Klon ist flach und reicht nicht bis August),
Fachprüf-Register, Redaktions-Queue, Frontmatter. Gemessen am 23.11.2026 am
gebauten Bestand.

| # | Slug (gekürzt) | Titel | Entstehungs-Batch | Commit-Datum | Wörter | Quellen | Fachprüfung | Prüfer |
|---|---|---|---|---|---|---|---|---|
| 1 | `internet-dsl-wechseln-praxis-tipps-fuer-den-an` | DSL-Anbieterwechsel: Ablauf, Ausfallzeiten und Effek | `feat(seo): optimize articles for Google rank` | 2026-08-25 | 1772 | 2 | kein Eintrag | — |
| 2 | `sparen-im-herbst-die-besten-spartipps-fuer-die` | Sparen im Herbst: Spartipps für die goldene Jahresze | `feat(seo): optimize articles for Google rank` | 2026-08-25 | 2273 | 1 | kein Eintrag | — |
| 3 | `kostenloses-girokonto-so-findest-du-ein-konto-` | Kostenloses Girokonto: Ein Konto ohne Gebühren finde | `Kadenz-Lücken 17.08. + 19.08. geschlossen` | 2026-08-19 | 2135 | 6 | ausstehend | **keiner benannt** |
| 4 | `privathaftpflicht-warum-sie-so-wichtig-ist-und` | Privathaftpflicht: Warum so wichtig und was sie kost | `Kadenz-Lücken 17.08. + 19.08. geschlossen` | 2026-08-19 | 1783 | 3 | kein Eintrag | — |
| 5 | `wohngebaeudeversicherung-vergleich-worauf-du-a` | Wohngebäudeversicherung Vergleich: Worauf du achten  | `feat(seo): optimize articles for Google rank` | 2026-08-25 | 1864 | 3 | kein Eintrag | — |
| 6 | `so-findest-du-den-richtigen-dsl-tarif-fuer-dei` | DSL-Tarif für dein Zuhause: Das passende Angebot fin | `feat(seo): optimize articles for Google rank` | 2026-08-25 | 1868 | 3 | kein Eintrag | — |
| 7 | `haushaltsbuch-fuehren-app-excel-oder-papier` | Haushaltsbuch führen: App, Excel oder Stift im Vergl | `Fehlende Blogartikel ergänzt: 6 Premium-Ratg` | 2026-08-25 | 1705 | 3 | ausstehend | **keiner benannt** |
| 8 | `mietwagen-buchen-ohne-kaution-fallen-urlaub` | Mietwagen ohne Kautionsfallen: So sparst du im Urlau | `Fehlende Blogartikel ergänzt: 6 Premium-Ratg` | 2026-08-25 | 2415 | 1 | kein Eintrag | — |
| 9 | `handytarif-vergleichen-2026-guenstige-tarife` | Handytarife vergleichen: Welches Angebot passt zu di | `fix(build): Qualitäts-Gate wiederherstellen` | 2026-08-26 | 1363 | 3 | kein Eintrag | — |
| 10 | `kfz-versicherung-vergleich-bis-zu-800-euro-spa` | Kfz-Versicherung vergleichen: Was ändert sich beim B | `Fehlende Blogartikel ergänzt: 6 Premium-Ratg` | 2026-08-25 | 836 | 3 | kein Eintrag | — |
| 11 | `tagesgeld-zinsen-2026-die-besten-zinssaetze-im` | Tagesgeld vergleichen: Was bleibt nach dem Aktionszi | `fix(build): Qualitäts-Gate wiederherstellen` | 2026-08-26 | 1685 | 3 | ausstehend | **keiner benannt** |
| 12 | `kreditkarte-vergleichen-kostenlos-sicher-bezah` | Kreditkarte vergleichen: Kostenlos und sicher zahlen | `fix(cadence): 2-3 LIVE an Mo/Mi/Fr dauerhaft` | 2026-09-03 | 1663 | 3 | ausstehend | **keiner benannt** |

**Lesart der Tabelle:**

* **Entstehung:** alle 12 in **fünf Automatik-Batches** zwischen dem 14.08. und
  dem 03.09.2026, alle unter dem Konto `frank-hartung`. Die Commit-Sprache ist
  die der Kadenz- und SEO-Automatik: „optimize articles for Google ranking“,
  „Kadenz-Lücken geschlossen“, „fix(cadence): 2-3 LIVE an Mo/Mi/Fr dauerhaft“.
  Kein Batch-Name nennt einen Menschen als Urheber.
* **Fachprüfung:** 4 der 12 stehen im Register mit Status **`ausstehend`** und
  **ohne benannten Prüfer**; 8 haben **gar keinen** Eintrag. Das Register meldet
  global: `pruefer_status: offen – kein benannter fachpruefer und keine
  Redaktionsprüfung mit Belegkette`, bei `anzahl: 21`.
* **Siegel und Freigabe:** kein einziges der 12 Frontmatter trägt ein Siegel-,
  Freigabe- oder Review-Feld. Die `ymyl_siegel_wache` meldet unabhängig:
  **„139 Artikel · 0 Befunde (keine Fachfreigabe)“**.
* **Fazit der Belege:** Für keinen der 12 Artikel ist **Urheberschaft** oder
  eine umfassende redaktionelle Verantwortungsübernahme belegt. Für **zwei** der
  12 gibt es inzwischen jedoch belegte Einzelprüfungen des Betreibers — das
  ändert die Lage und steht in Abschnitt 4.1. Für die übrigen **zehn** lässt sich
  die Ausnahme des Art. 50 Abs. 4 nicht beanspruchen.

### 4.1 Neue Beleglage vom 23.11.: Betreiber-Freigaben für 2 der 12

Nach der Register-Entscheidung (13:01 Uhr, PR #1329) wurden im
Faktenfrische-Ledger **47 Entscheidungen** mit dem Vermerk
`entschieden_von: Frank Hartung (Betreiber-Freigabe über Arena-Session,
23.11.2026)` erfasst. **Zehn davon betreffen zwei der 12 Artikel:**

| Artikel | Befunde mit Betreiber-Freigabe | entschieden am | Bindung | Typ der Begründung |
|---|---|---|---|---|
| `sparen-im-herbst-die-besten-spartipps-fuer-d` | **5** | 2026-11-23 | Text-Hash `2a897cf8eda4…` | inhaltlich je Befund begründet |
| `mietwagen-buchen-ohne-kaution-fallen-urlaub` | **5** | 2026-11-23 | Text-Hash `e50b3a1b4a15…` | inhaltlich je Befund begründet |

Jede dieser zehn Entscheidungen ist eine `folgeentscheidung: true`, nennt einen
`vorgaenger_geprueft_fassung` und bindet an einen **Text-Hash**
(`geprueft_fassung`) — sie ist also beweiskräftig an eine bestimmte Fassung
gebunden, nicht pauschal. Der Vorspann lautet jedes Mal „Folgeentscheidung am
23.11.2026 **nach KI-Kennzeichnungs-Update (Welle 1)**“: Geprüft wurde die
Fassung, die die Kennzeichnung bereits trägt.

Die Begründungen sind inhaltlich und je Befund einzeln:

**`2026-08-14-sparen-im-herbst-die-besten-spartipps-fuer-die-goldene-jahreszeit`** — 5 Befunde:
* `47f855cb4f0fe1e5c65f` (luecke): Volltext unverändert ohne unbelegte Kfz-Wechsel-Spannen (150-400 € / 180-350 €).
* `6b0aa3429d97e8c74ed8` (luecke): Keine pauschale 8-12-%-Behauptung im Text; 8-%-Beispiel ist ausdrücklich als Rechenbeispiel gekennzeichnet.
* `7f66ec82ee1a3f095b0c` (praezision): Formulierung ''lukrativste Spar-Saison des Jahres'' steht nicht im Artikel.
* `84c991c5d152b14a2675` (luecke): Pauschale 500-1.300-€-Spanne steht nicht im Artikel; Beispielrechnungen legen Annahmen offen.
* `a70e7adc97c58317ccc1` (luecke): Unbelegte 50-80-€-Spanne für saisonale Vorratshaltung steht nicht mehr im Artikel.

**`2026-08-21-mietwagen-buchen-ohne-kaution-fallen-urlaub`** — 5 Befunde:
* `0051151e6c46f4c2bdb3` (luecke): Kautionsspanne 900 € bis 2.500 € ist im Text ausdrücklich als Modellwert gekennzeichnet und nicht der Verbraucherzentrale zugeschrieben.
* `0790f52160dfaa819917` (luecke): Differenz 145 € pro Woche ist im Text ausdrücklich als Modellannahme gekennzeichnet.
* `53c3fde8e986e6560890` (luecke): 15 bis 25 % Aufschlag an Flughafenstationen ist im Text ausdrücklich als Modellwert gekennzeichnet.
* `89adecebaae75c147402` (luecke): ''Zero Excess'' wird ohne unbelegte 5-12-€/Tag-Faktenbehauptung als optionale Anbieter-Regel erläutert.
* `a1a269b73a1b9c2dfc88` (luecke): Unbelegte 3-8-€/Tag-Angabe für Vollkasko ohne Selbstbeteiligung steht nicht im Artikel.

**Was das bedeutet — und was nicht:**

* **Ja:** Für `sparen-im-herbst` und `mietwagen` hat der Betreiber am 23.11.
  konkrete inhaltliche Aussagen am Text geprüft, einzeln begründet und mit
  Text-Hash gebunden freigegeben. Das ist menschliche Überprüfung und
  redaktionelle Verantwortungsübernahme **für diese Befunde**.
* **Nein:** Es ist kein Beleg für menschliche **Urheberschaft**, und keine
  Vollprüfung des gesamten Textes — geprüft wurden die benannten
  Zahlen-Befunde, nicht jeder Satz. Die übrigen zehn Artikel haben **keine**
  solche Freigabe.
* **Folge für Ihre Entscheidung:** Für diese zwei Artikel ist Option B
  (Abschnitt 7) **argumentierbar**, und der Beleg zum Benennen liegt bereit —
  Ledger-Eintrag, `befund_id`, `geprueft_fassung`, Datum. Ob die geprüfte
  Reichweite für die Ausnahme des Art. 50 Abs. 4 genügt, ist eine rechtliche
  Wertung, die Ihnen gehört und die diese Vorlage nicht vorwegnimmt.
* **Der Bestand ist einstweilen sicher:** Beide Artikel sind gekennzeichnet,
  wie alle 12. Über-Kennzeichnen ist rechtlich unschädlich. Es eilt also nichts
  — Sie können in Ruhe werten.

### 4.2 Der Ledger war zwischenzeitlich zerrissen — und ist geheilt

Vollständigkeit halber, weil Ihre Freigaben in genau dieser Datei stehen:
`data/faktenfrische_entscheidungen.yaml` war ab Commit `3672f84` (PR #1328,
13:54) **strukturell zerstört**. Ein Writer-Fehler hatte Entscheidungen nicht
als eigene Listenpunkte angefügt, sondern als zweiten Schlüsselblock
**innerhalb** eines fremden Eintrags — drei Einträge trugen je zwei bis drei
Entscheidungen untereinander, mit doppelten Schlüsseln `geprueft_fassung`,
`entschieden_von`, `entschieden_am`, `beleg`, `begruendung`.

Die Werk-Doku beschreibt genau diese Klasse (Zeile 277–291): `yaml.safe_load`
nimmt dann **still den letzten Wert**, der Eintrag trägt Felder aus zwei
verschiedenen Ketten, und die Wache meldet „Ungültige Folgeentscheidung“,
obwohl ordentlich entschieden war. Der strenge Loader macht daraus zu Recht
einen lauten Strukturfehler.

* **Gemessen:** `abgeleitete_register.py --check` und
  `f4_entscheidungsvorlage.py --check` waren dadurch **Exit 1** — auch auf
  `origin/main` (Gegenprobe im Worktree), nicht nur hier.
* **Der sanktionierte Heiler verweigerte sich:** `--struktur-pruefen` fand die
  drei zerrissenen Einträge, `--reparieren` wollte 5 Blöcke trennen, aber
  `--reparieren --apply` brach **fail-closed** ab: „Reparatur ergab ungültige
  Akte: Ungültige Folgeentscheidung … Vorgänger fehlt in der Kette“. Die Datei
  blieb bytgleich unangetastet. Richtig so: Ketten neu zu verknüpfen hieße,
  über Entscheidungen zu befinden.
* **Geheilt hat es `main` selbst**, Commit `15a793c` („chore(agentur):
  Merge-Reparatur“). Verlust-Nachweis gemessen: **0 Entscheidungen verloren**,
  373 → **415** `entschieden_am`, 370 → **415** Listeneinträge, die zerrissenen
  Blöcke getrennt, dazu Ihre 47 Freigaben. `abgeleitete_register.py --check`
  ist wieder **Exit 0**.
* **Offen, aber nicht rot:** `F4-ENTSCHEIDUNGSVORLAGE.md` ist seither veraltet
  (`--check` Exit 1), weil der Ledger 42 Entscheidungen gewann. Das heilt CI
  selbst: `faktenfrische.yml` ruft `f4_entscheidungsvorlage.py` **ohne**
  `--check` auf und committet das Ergebnis (Schritt „Belege & Dossiers
  committen“). Es ist ein abgeleitetes Dokument im Besitz von CI — hier bewusst
  **nicht** von Hand neu geschrieben.

---

## 5. Umsetzungsnachweis: Die Entscheidung ist nicht nur Papier

Gemessen am gebauten Bestand — `hugo --minify --cleanDestinationDir`, Exit 0,
**3171 Dateien**, 2975 statische Dateien — und alle 12 Artikel einzeln geprüft:

| Kanal | Umsetzung | Treffer |
|---|---|---|
| **Lesersichtbar** | „Mit KI erstellt oder bearbeitet“ in der Prüfzeile, `layouts/_partials/ff_pruefzeile.html`, Attribut `data-ff-ki-label` | 12/12 |
| **Meta-Signal** | `<meta name=ai-generated content="true">` aus `layouts/_partials/ki_provenienz.html` | 12/12 |
| **Geltungsbereich** | `<meta name=ai-generated-scope content="text,audio">` | 12/12 |
| **Verweis** | `<link rel=describedby href="…/impressum/#ki-hinweis">`, Anker im Impressum gemessen vorhanden | 12/12 |
| **schema.org** | `creditText` am `Article`-Knoten, `layouts/_partials/schema_article.html` | 12/12 |
| **Frontmatter** | `ai_generated: true`, von `ki_kennzeichnung_gate.py` Regel K1 erzwungen | 12/12 |
| **Feed** | `layouts/_default/rss.xml` ergänzt „Zielartikel: mit KI erstellt oder bearbeitet.“ | 12/12 |

**Beispiel aus dem sichtbaren Text**, Artikel 11 (`tagesgeld`):

> … 09.2026 · 8 Minuten · 1685 Wörter · Frank Hartung Verantwortlicher Autor:
> Frank Hartung · **Mit KI erstellt oder bearbeitet** · 3 Quellen · Stand:
> 19.11.2026 …

Die Durchsetzung ist vertraglich gesichert, nicht freiwillig:

* `ki_kennzeichnung_gate.py --gate` → **Exit 0**: „Registerangaben und Artikel
  stimmen überein; Herkunft ungeklärter Einträge separat prüfen.“
  Regel **K1**: Artikel unter `maschinell` haben **immer** `ai_generated: true`.
  Regel **K2**: `ai_generated: false` nur mit `menschlich`-Eintrag **oder** mit
  freigegebener redaktioneller Prüfung.
* `ki_provenienz_gate.py --wache` → **Exit 0** mit den Prüfungen **M1**
  (Meta-Signal jeder gebauten Seite gegen das Frontmatter), **M2**
  (Vorlagenvertrag: Einbindung, `creditText`, Bildattribut, Impressum-Anker),
  **M3** (IPTC-Feld in jeder deklarierten KI-Bilddatei) und **M4**
  (**Kanaltreue: kein Signal ohne sichtbaren Hinweis und umgekehrt**).

**K2 ist der Riegel gegen einen Rückfall.** Würde jemand einen der 12 Artikel
stillschweigend auf `ai_generated: false` setzen, ohne ihn ins
`menschlich`-Register zu stellen, wird das Gate rot. Die Entscheidung ist damit
dauerhaft bewehrt und nicht nur einmal gesetzt. M4 verhindert die umgekehrte
Lücke: ein sichtbarer Hinweis ohne Meta-Signal ist ebenso rot.

---

## 6. Die zwei Fälle mit dem höchsten Einsatz

Zwei der 12 stehen in `data/editorial_review_queue.json` als **`state: live`**
mit **`risk: hoch`** — sie sind also veröffentlicht, gelten als Hochrisiko und
sind **weiter ungeprüft**. Die Queue-Metrik bestätigt das unabhängig:
`high_risk_total: 10, approved: 6, open_live: 2, open_drafts: 2`. Es sind genau
diese zwei:

* **`2026-08-18-wohngebaeudeversicherung-vergleich-worauf-du-achten-musst`**
  „Wohngebäudeversicherung Vergleich: Worauf du achten musst“ · 1864 Wörter · 3 Quellen · Fachprüfung: **kein Eintrag** · Prüfer: **keiner benannt**
* **`2026-08-26-kfz-versicherung-vergleich-bis-zu-800-euro-sparen`**
  „Kfz-Versicherung vergleichen: Was ändert sich beim Beitrag?“ · 836 Wörter · 3 Quellen · Fachprüfung: **kein Eintrag** · Prüfer: **keiner benannt**

Beides sind Versicherungsvergleiche — ein Thema, bei dem eine falsche Zahl
echten Vermögensschaden bedeuten kann. Die Kennzeichnung ist hier das Minimum,
eine Fachprüfung wäre mehr.

Das ist **kein** Widerspruch zur Entscheidung aus Abschnitt 2, sondern eine
**zweite, davon unabhängige** Baustelle: Die Herkunft ist jetzt geklärt und
gekennzeichnet, die inhaltliche Prüfung dieser zwei Artikel steht weiter aus.
Wenn Sie nur eine Sache aus dieser Vorlage mitnehmen, dann diese.

---

## 7. Ihre drei Optionen und was jeweils folgt

### Option A — Bestätigen

Empfohlen, wenn Sie keinen Gegenbeleg haben. Sie zeichnen Abschnitt 8 ab.
**Es ändert sich nichts im Bestand.** Das Register bleibt `menschlich: []`, alle
12 bleiben gekennzeichnet, die Wache bleibt grün. Einzige Wirkung: Die
Behauptung „Betreiber-Entscheidung“ im Register-Kommentar ist ab jetzt belegt —
durch Ihre Unterschrift und dieses Dokument.

* Aufwand: eine Zeile.
* Risiko: keines, die Kennzeichnung ist ohnehin live und vertraglich gesichert.
* Frist 02.12.2026: **erfüllt**, mit 9 Tagen Puffer.

### Option B — Einzelne Artikel zurück nach `menschlich`

Nur sinnvoll, wenn Sie für einen bestimmten Artikel belegen können, dass ein
Mensch ihn inhaltlich geprüft und die Verantwortung übernommen hat. Dann in
dieser Reihenfolge:

1. Slug von `maschinell` nach `menschlich` in `data/ki_kennzeichnung.yaml`.
2. `ai_generated: false` im Frontmatter desselben Artikels.
3. Den Beleg benennen — Prüfer, Datum, Fundstelle. Regel K2 verlangt wörtlich
   eine „freigegebene redaktionelle Prüfung“.
4. Nachmessen: `hugo --minify --cleanDestinationDir` und danach
   `python scripts/ki_kennzeichnung_gate.py --gate`.

* Folge: Der sichtbare Hinweis und alle Meta-Signale **verschwinden** auf dieser
  Seite — Sie nehmen eine Offenlegung zurück. Deshalb nur mit Beleg.
* **Belegbare Kandidaten:** Nach dem Stand vom 23.11. kommen dafür **zwei** der
  12 in Betracht — `sparen-im-herbst` und `mietwagen`. Für sie liegen je fünf
  Betreiber-Freigaben mit Text-Hash-Bindung und inhaltlicher Einzelbegründung
  vor (Abschnitt 4.1). Ob die geprüfte Reichweite für die Ausnahme genügt, ist
  Ihre rechtliche Wertung.
* **Für die übrigen zehn gilt:** null Siegel, null benannte Prüfer, null
  Freigaben (Abschnitt 4) — hier trägt nur Option A.

### Option C — Nichts tun

Der Bestand bleibt, wie er ist: gekennzeichnet, grün, fristwahrend. **Aber** die
Register-Notiz behauptet dann weiter eine Betreiber-Entscheidung, die keine ist.
Das ist dieselbe Klasse von Fehler, die diese Runde geheilt hat: eine Aussage
über einen Rechtszustand, die niemand belegt hat.

**Empfehlung: A oder B — nicht C.**

---

## 8. Abzeichnung

Zum Ausfüllen. Mit der Unterschrift wird die Einordnung der 12 Artikel unter
`maschinell` in `data/ki_kennzeichnung.yaml` zur Entscheidung des Betreibers.

```
Entscheidung zu den 12 Altartikeln im KI-Register (Frist 02.12.2026)

Ich habe die Beleg-Lage in Abschnitt 4 zur Kenntnis genommen: fünf
Automatik-Batches zwischen 14.08. und 03.09.2026, kein benannter Fachprüfer,
kein Siegel in den Frontmattern, und — für zwei der zwölf Artikel — je fünf
Betreiber-Freigaben vom 23.11.2026 mit Text-Hash-Bindung (Abschnitt 4.1).

Option A — bestätigen (alle 12 bleiben unter `maschinell`, gekennzeichnet):

    [   ] ja        [   ] nein

Option B — einzelne Artikel zurück nach `menschlich`, nur mit Beleg.
Belegbare Kandidaten nach Abschnitt 4.1:

    [   ] 2026-08-14-sparen-im-herbst-die-besten-spartipps-fuer-die-goldene-jahreszeit
          Beleg: 5 Betreiber-Freigaben 23.11.2026, Text-Hash 2a897cf8eda4…
    [   ] 2026-08-21-mietwagen-buchen-ohne-kaution-fallen-urlaub
          Beleg: 5 Betreiber-Freigaben 23.11.2026, Text-Hash e50b3a1b4a15…
    [   ] anderer Artikel: ____________________________________
          Beleg (Prüfer, Datum, Fundstelle): ____________________

Zusatzentscheidung zu den zwei Hochrisiko-Fällen aus Abschnitt 6
(wohngebaeudeversicherung · kfz-versicherung, beide live und ungeprüft):

    [   ] Fachprüfung wird bis ____________ nachgeholt
    [   ] bleibt offen, Risiko bewusst getragen

Ort, Datum: ______________________

Unterschrift (Betreiber): ______________________
```

Die zwei Kandidaten unter Option B sind **nicht** dieselben wie die zwei
Hochrisiko-Fälle der Zusatzentscheidung. Das ist kein Widerspruch: Herkunft und
Kennzeichnung sind für alle 12 geklärt; offen sind einmal die Frage, ob für zwei
Artikel die Ausnahme greift (Option B), und einmal die inhaltliche Fachprüfung
zwei anderer Artikel (Zusatzentscheidung).

Nach der Unterschrift: dieses Dokument committen. Es ist der Beleg, den das
Register seit dem 02.08.2026 mit `BITTE PRÜFEN` verlangt hat.

---

## 9. Was bewusst NICHT getan wurde

* **Register nicht angefasst.** `data/ki_kennzeichnung.yaml`,
  `data/ki_provenienz_state.json` und `data/fachpruefung_register.yaml` sind in
  dieser Runde **unverändert**. Die Einordnung stammt aus PR #1329, nicht von
  hier.
* **Frist nicht verschoben.** `2026-12-02` steht, wie sie steht.
* **Keine `menschlich`-Einträge erfunden oder gelöscht**, um Grün zu erzwingen.
  Die Wache ist grün, weil die Belege die konservative Richtung tragen — nicht,
  weil eine Prüfung entschärft wurde.
* **Kein Gate, keine Schwelle, kein Siegel geändert.**
* **Faktenfrische-Ledger nicht angefasst.** `data/faktenfrische_entscheidungen.yaml`
  ist unverändert, obwohl der sanctioned Heiler `--reparieren --apply` angeboten
  wurde. Er brach fail-closed ab, weil die Ketten-Bindung neu hätte verfügt
  werden müssen — und über Betreiber-Entscheidungen verfügt keine Maschine.
  `main` heilte die Struktur selbst, mit nachgewiesenen **0 Verlusten**
  (Abschnitt 4.2).
* **`F4-ENTSCHEIDUNGSVORLAGE.md` nicht von Hand neu geschrieben.** Sie ist
  veraltet, weil der Ledger 42 Entscheidungen gewann. Das Dokument ist eine
  Ableitung im Besitz von CI: `faktenfrische.yml` schreibt und committet es.
  Von Hand hineinzupfuschen hätte zwei Wahrheiten erzeugt.
* **Wachzustand zurückgenommen**, den ein eigener Messlauf ohne Bauprodukt
  geschrieben hatte: `funde: 0 → 1`, verursacht durch `M1: kein Bauprodukt unter
  …/public/`. Das war ein Umgebungs-Artefakt dieser Sandbox, kein Befund. Danach
  Hugo gebaut und **mit** Bauprodukt gemessen: Exit 0, `Zustand geändert
  (Commit nötig): nein`.
* **Nur dieses Dokument ist neu.** Kein Skript, kein Workflow, keine Ableitung.

**Eigener Messfehler, korrigiert:** Der erste Prüflauf meldete „kein
lesersichtbarer Hinweis auf der Artikelseite“. Das war falsch — das Suchmuster
war zu eng und kannte den Wortlaut der Haus-Vorlage nicht. Der Hinweis lautet
wörtlich „Mit KI erstellt oder bearbeitet“ und ist auf **allen 12** Seiten
vorhanden, gerendert aus `ff_pruefzeile.html`. Die Haus-Akte zu lesen, bevor ein
Mangel gemeldet wird, hat hier einen falschen Befund verhindert.

---

## 10. Selbst nachmessen

```bash
export PATH="$PWD/.venv/bin:$PATH"
hugo --minify --cleanDestinationDir              # Bauprodukt erzeugen
python scripts/ki_provenienz_gate.py --wache     # Erwartung: Exit 0, 0 Eskalationen
python scripts/ki_kennzeichnung_gate.py --gate   # Erwartung: Exit 0
python scripts/ymyl_siegel_wache.py              # Erwartung: 139 Artikel, 0 Befunde

# sichtbaren Hinweis auf einer der 12 Seiten prüfen:
grep -o 'Mit KI erstellt oder bearbeitet' \
  public/posts/2026-08-26-tagesgeld-zinsen-2026-die-besten-zinssaetze-im-vergleich/index.html

# wer die Einordnung vorgenommen hat:
git show --stat 3718357 -- data/ki_kennzeichnung.yaml
gh pr view 1329 --json author,mergedAt,body

# die Betreiber-Freigaben vom 23.11. selbst lesen (Abschnitt 4.1):
grep -c 'Betreiber-Freigabe über Arena-Session' data/faktenfrische_entscheidungen.yaml
grep -B14 'Betreiber-Freigabe über Arena-Session' data/faktenfrische_entscheidungen.yaml \
  | grep -E 'slug:|befund_id:|geprueft_fassung:' | head -40

# Ledger-Struktur und Ableitungen (Abschnitt 4.2):
python scripts/faktenfrische_befund_ledger.py --struktur-pruefen   # Erwartung: Exit 0
python scripts/abgeleitete_register.py --check                     # Erwartung: Exit 0
python scripts/f4_entscheidungsvorlage.py --check                  # veraltet, heilt CI selbst
```

---

**Verwandte Akten:**
`KI-VO-MASCHINENLESBAR-1028-DAUERHEILUNG-HIGHEND-2026-11-05.md` — die vier
Kanäle und die Prüfungen M1–M4 ·
`GATES-DAUERHEILUNG-HIGHEND-2026-11-23.md` §8.1 — Herkunftsforschung über die
GitHub-API, die fünf Entstehungs-Batches ·
`ENTSCHEIDUNG-BETREIBER-2026-11-23.md` — Prüf-Budget 21 und WLAN-Doppelentwurf,
behandelt das Register **nicht**.

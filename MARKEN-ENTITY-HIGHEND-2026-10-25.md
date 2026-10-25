# Marken-Entity – FranksFinanzcheck als eindeutige Entität (Highend-Umsetzung)

> **Stand:** 25.10.2026 · **Auslöser:** `SERP-LIVE-PRUEFUNG-HIGHEND-2026-10-25.md` §3
> (Google korrigiert die Markensuche auf „Frank Finanzcheck“ → FINANZCHECK.de)
> **Vertrag:** `data/entity.yaml` · **Wache:** `scripts/entity_marken_gate.py` (E1–E9, CI: `entity-marken-gate.yml`)
> **Runbook:** `docs/ANLEITUNG-MARKEN-ENTITY.md` (Publisher Center, LinkedIn/Xing, Wikidata, Outreach)

---

## 1. Ausgangslage – drei Annahmen nachgemessen, zwei korrigiert

Der Maßnahmenplan ging davon aus, Marken-Präsenz im Snippet und `sameAs` seien „schon da“.
Die Messung am Bestand (102 Live-Seiten) sagt etwas anderes:

| Fläche | Annahme | Gemessen | Einordnung |
|---|---|---|---|
| `<title>` trägt „FranksFinanzcheck“ | „ist schon da“ | **12/102** (Build, indexierbar: **10/97**) | Das Marken-Suffix wird nur angehängt, wenn der Titel < 40 Zeichen ist (`seo_title.html`) – sonst sprengt es das 60-Zeichen-Fenster (M1). Nur **2** weitere (handgesetzte seoTitle) könnten die Marke überhaupt aufnehmen. Eine Massenänderung aller Titel ist damit strukturell unmöglich, ohne Titel zu kürzen oder abzuschneiden. |
| Description trägt die Marke | „ist schon da“ | **12/102**; 85 Seiten tragen sie in **weder** Titel noch Description | 22 Descriptions könnten ein Marken-Präfix im 100–160-Fenster aufnehmen. Bewusst **nicht** massenhaft geändert: Descriptions sind Teil hash-gebundener Artikel-Fassungen (Beweissystem), Google schreibt Snippets ohnehin häufig um, und der Markenträger im Snippet ist der Site-Name (s. u.). Die 22 bleiben eine redaktionelle Option, keine Automatik. |
| `sameAs` (Mastodon, Pinterest) | „bereits vorhanden“ | Im **Article-/Organization**-Schema ja – im siteweiten **Person**-Knoten stand hartkodiert **nur Pinterest** | Echter Bug: Ausgerechnet der Autoren-Knoten auf jeder Seite führte Mastodon nicht. Behoben (E5/E8 wachen darüber). |
| Social-Profile verlinkt | implizit angenommen | **Nirgends siteweit sichtbar** – `social_icons` wurde nur im (inaktiven) Profilmodus gerendert; der Footer hatte keine Profil-Links | Behoben: `rel=me`-Links im Footer jeder Seite. |
| Impressum nennt die Marke | – | Betreiberzeile nannte nur Person + Anschrift, **nicht** „FranksFinanzcheck“ | Ergänzt. |
| Tröstlich | – | `og:site_name` = Marke auf **97/97** indexierbaren Seiten; WebSite-Schema vorhanden | Genau hier setzt Maßnahme 1 an. |

**Die wirksame Korrektur zu Maßnahme 1:** In der modernen Google-SERP steht über dem Titel der
**Site-Name** – gespeist aus `WebSite.name`/`alternateName` im strukturierten Datensatz plus
Favicon. Der Markenträger ist also nicht das Titel-Suffix (das bei 87 % der Seiten physisch
nicht passt), sondern eine saubere, widerspruchsfreie Entity im Schema **und** im sichtbaren
Text der Startseite. Darauf zielt diese Umsetzung; die Titel-Quote weist die Wache ab jetzt
als ehrliche Messung aus (E9, weich), statt sie grün zu rechnen.

## 2. Maßnahme 1 – Konsistente Marken-Präsenz + Entity-Definition ✅ umgesetzt

**Kanonischer Identitätssatz** (neu: `data/entity.yaml` → `hugo.toml params.entityDefinition`):

> „FranksFinanzcheck (franksfinanzcheck.de) ist das unabhängige Fixkosten-Cockpit für deutsche
> Haushalte: ein redaktioneller Ratgeber von Frank Hartung, der Verträge, Fristen und laufende
> Kosten mit nachvollziehbarer Rechnung ordnet – kein Bankportal, kein Kreditvergleichsportal
> und keine Versicherungsmakler.“

**Bewusste Abweichung vom Formulierungsvorschlag** („kein Vergleichsservice“): Die Site
veröffentlicht eigene Vergleiche (`/so-entstehen-unsere-vergleiche/`) und verlinkt
gekennzeichnet auf Partner-Vergleiche – „kein Vergleichsservice“ wäre als Selbstaussage
angreifbar. „Kein **Kreditvergleichsportal**“ ist wahr (Verträge entstehen beim Anbieter,
Impressum/Transparenz) und trifft die Verwechslung exakt. („keine Versicherungsmakler“ ist
die grammatisch saubere Form.)

Umgesetzt:
- **Startseite:** sichtbare Entity-Box am Seitenende („Was ist FranksFinanzcheck?“:
  Definition, drei Einordnungs-Punkte, Abgrenzung, Links auf /ueber/, /presse/, /impressum/) –
  crawlbarer Text ohne Eingriff in Hero/LCP (`entity_box.html` + `zz-entity.css`).
- **Schema.org:** `Organization.description` = Identitätssatz (Startseite **und** jeder Artikel),
  dazu `founder` (Person-@id), `ContactPoint`, `publishingPrinciples`, `alternateName`
  „franksfinanzcheck.de“; WebSite trägt `name` + `alternateName` (Site-Name-Quelle).
- **Person-Schema repariert:** `sameAs` jetzt aus der einen Profil-Liste (Mastodon + Pinterest),
  plus `worksFor`; ProfilePage auf /ueber/ führt dieselbe Liste.
- **/ueber/:** Identitätssatz als erster Satz der Positionierung; **/presse/:** als
  kopierbare Boilerplate; **llms.txt:** Definition + Abgrenzung + offizielle Profile im
  Maschinen-Kopf (Generator + Datei regeneriert).
- Startseiten-Description beginnt bereits mit „FranksFinanzcheck ist das Fixkosten-Cockpit …“
  – jetzt gate-gesichert (E3). Die gesperrte `params.description` (brand_lock) bleibt unberührt.

## 3. Maßnahme 2 – Publisher Center / Knowledge Graph 🔧 vorbereitet (Frank-Aktion nötig)

Ehrlich getrennt, was Code kann und was nur Frank kann:

| Baustein | Stand |
|---|---|
| **Publisher Center-Profil** | **Vorbereitet, nicht angelegt.** Braucht Franks Google-Konto (GSC). Schritt-für-Schritt mit kopierfertigen Feldwerten (Name, Beschreibung = Identitätssatz, Feed `…/index.xml`, Logo `…/images/pwa/icon-512.png`, Kontakt) im Runbook §2. Repo-Voraussetzungen wacht E7. Nach Freigabe: Status + Beleg in `data/entity.yaml` (erzwingt E7). |
| **„Bevorzugte Quelle auf Google“** | Kein Publisher-Schalter, sondern eine Leser-Einstellung (Preferred Sources). Finanztip wirbt dafür bei seinen Lesern – unser Gegenstück wäre ein redaktioneller Hinweis (Newsletter/Artikelende), keine Technik. Im Runbook §2 eingeordnet, ohne Wirkungsversprechen. |
| **Wikipedia** | Realistisch: **nicht angestrebt** (Eigenartikel unzulässig, Relevanz fehlt). Grundlage-Leiter im Runbook §3: Erwähnungen verdienen → Wikidata mit Belegen → Wikipedia nur durch Dritte. Status wird im Register geführt; „aktiv“ nur mit Beleg (E7). |
| **`sameAs`: LinkedIn, Xing** | **Mechanismus fertig, Profile fehlen.** Es gibt kein belegtes Profil (Social-Kanäle: Standby ohne Zugangsdaten) – eine erfundene URL wäre ein falsches Entity-Signal, deshalb steht bewusst keine im Schema. Aktivierung = Profil anlegen (Bio = `definition_kurz`, Startseite verlinken) + **ein** Block in `hugo.toml [[params.socialIcons]]` + Eintrag ins Register heben. Theme-Icons existieren; Schema + Footer folgen automatisch. Anleitung Runbook §4, Platzhalter blockt E4. |

## 4. Maßnahme 3 – Brand-Signale systematisch ✅ Fundament gelegt, Outreach läuft über Bestandskadenz

- **Backlinks auf die Startseite:** Neue Kampagne `startseite-markenlinks`
  (`data/backlink_prospects.yaml`) mit Asset `startseite-markenprofil`
  (`data/backlink_assets.yaml`): Ziel ausnahmslos die Startseite, Anker = Marke/Domain
  (keine Keyword-Anker), Pitch über Fixkosten-Index + Expertise. Die kopierbare
  Boilerplate auf `/presse/` senkt die Hürde für Verzeichnisse/Autorenboxen.
  Kadenz und Ehrlichkeitsregeln bleiben die der Authority-Strategie (1 Medienziel/Woche,
  jede Erwähnung belegt). Externe Links selbst kann kein Repo erzeugen – das bleibt
  Franks wöchentliche Handarbeit; neu ist nur, dass sie jetzt ein eigenes, messbares
  Startseiten-Ziel hat statt zufällig auf Artikel zu zeigen.
- **Social Profile als `sameAs` und verlinkt:** Schema-Seite repariert (§2); sichtbar jetzt
  zusätzlich im **Footer jeder Seite** (`rel="noopener noreferrer me"`), plus Profil-Links
  auf `/presse/`. Quelle bleibt die eine Liste in `hugo.toml`.
- **Konsistenter Name (Audit):**

  | Fläche | Befund | Aktion |
  |---|---|---|
  | Impressum | Marke fehlte in der Betreiberzeile | ergänzt (E3) |
  | Newsletter-Absender | „Frank von FranksFinanzcheck“ – enthält die exakte Marke, ist aber eine Personen-Variante | **bewusst unverändert** (Wiedererkennung/Zustellbarkeit); Entscheidung + Kriterien im Runbook §6, E6 fordert die exakte Marken-Teilzeichenkette |
  | Newsletter-Abmeldung | Marke in Description + Formularwegen konsistent | ok, jetzt E6-geprüft |
  | Newsletter-Bestätigung/-Checkliste | Marke fehlte in beiden Descriptions | ergänzt (E6) |
  | Double-Opt-In-Mail | „Spar-Newsletter von FranksFinanzcheck“ | ok, E6-geprüft |
  | Kontakt | `kontakt@franksfinanzcheck.de` überall gleich | ok |
  | Schreibweise | 0 Falschschreibungen („Franks Finanzcheck“ u. ä.) in Content/Layouts | ok, E6 wacht |

## 5. Maßnahme 4 – Differenzierung zu FINANZCHECK.de ✅ umgesetzt

**Kanonische Abgrenzung** (`params.entityAbgrenzung` = Register), wortgleich auf Startseite,
`/ueber/` (eigener Abschnitt „Abgrenzung: Nicht FINANZCHECK.de“ mit Anker
`#abgrenzung-nicht-finanzcheckde`), `/impressum/` (Abschnitt „Abgrenzung zu ähnlich
klingenden Angeboten“, Stand auf 25.10.2026 aktualisiert), `llms.txt` und in Kurzform auf
`/presse/`:

> „FranksFinanzcheck steht in keiner geschäftlichen oder gesellschaftsrechtlichen Verbindung
> zum Kreditvergleichsportal FINANZCHECK.de. Trotz der ähnlich klingenden Namen handelt es
> sich um unterschiedliche, voneinander unabhängige Anbieter. Auf franksfinanzcheck.de werden
> Kredite, Konten und Versicherungen nicht selbst angeboten; ein Vertrag kommt – wenn du
> einem gekennzeichneten Partnerlink folgst – ausschließlich mit dem dort genannten Anbieter
> zustande.“

Das Impressum ergänzt sachlich: Der Betreiber ist weder Kreditinstitut noch Darlehens- oder
Versicherungsvermittler; die Verantwortlichkeit für vermittelte Angebote liegt wie bisher
beim Partner. **Empfehlung:** Diese Einordnung einmal juristisch gegenlesen lassen – sie ist
mit dem bisherigen Impressum konsistent, aber eine rechtliche Selbstklassifikation bleibt
eine Aussage, die ein Anwalt bestätigen sollte, keine Redaktionsmeinung.

## 6. Dauerabsicherung

`scripts/entity_marken_gate.py` (E1 Register · E2 Build-Quelle · E3 Wortlaut-Flächen ·
E4 Profil-Parität inkl. Platzhalter-Sperre · E5 Template-Verträge · E6 Namensflächen/
Schreibweise · E7 Publisher-Reife + Beleg-Zwang · E8 Build-Parität JSON-LD/rel=me ·
E9 og:site_name hart + Titel-Quote als Messung). Offline-Selbsttest mit 11 Sabotage-Proben
(jede Regel muss anschlagen). Verdrahtet als `npm run entity:check` und CI
`.github/workflows/entity-marken-gate.yml` (Push/PR auf allen Marken-Flächen, inkl. Build).

## 7. Verifikation (25.10.2026, Hugo 0.164.0 extended)

| Prüfung | Ergebnis |
|---|---|
| `entity_marken_gate.py --selftest` | ✅ 11/11 Proben (gutes Fixture sauber, jede Sabotage erkannt) |
| `entity_marken_gate.py --source-only` | ✅ 0 Fehler, 0 Warnungen |
| Hugo-Build + `--public public` | ✅ 0 Fehler; 1 ehrliche Mess-Warnung (Titel-Quote 10/97) |
| `schema_seo_gate.py` (Nachbar) | ✅ 260 Seiten, 0 harte Funde – neues JSON-LD valide |
| `brand_guard.py` | ✅ gesperrte Markenwerte unberührt |
| `saisonale_startseite_guard.py --public` | ✅ keine Funde (Hero/Lead unverändert) |
| `h1_wache.py --source-only`, `content_html_wache.py` | ✅ grün |
| `generate_llms_txt.py --check` | ✅ aktuell |
| `metadaten_wache.py` | ⚠️ **2 vorbestehende M3-Fremdbefunde** (`lastmod` vor `date` in `2026-08-12-dein-haus-…` und `2026-08-17-privathaftpflicht-…`) – Dateien liegen **nicht** in diesem Diff; separat zu heilen, hier nur ausgewiesen |

Beleg im Build: Startseite führt die Entity-Box, 5 `rel=me`-Treffer (Footer-Profile,
Pinterest-CTA, Mastodon-Head-Link), Person/Organization-`sameAs` deckungsgleich,
Anker `#abgrenzung-nicht-finanzcheckde` auf /ueber/ vorhanden.

## 8. Frank-Aktionen (der Teil, den kein Code erledigt)

1. **Publisher Center anlegen** (~20 Min, Runbook §2) → Status+Beleg in `data/entity.yaml` eintragen.
2. **LinkedIn (und ggf. Xing) entscheiden + Profil anlegen** (~30 Min/Profil, Runbook §4) →
   ein TOML-Block + Register-Eintrag; der Rest läuft automatisch.
3. **Absendername bestätigen** (1 Entscheidung): „Frank von FranksFinanzcheck“ behalten
   (Empfehlung) oder auf reine Marke umstellen.
4. **Abgrenzungs-/Vermittler-Formulierung juristisch gegenlesen** (Impressum).
5. **Outreach auf die Startseite** in die bestehende Wochenkadenz aufnehmen
   (Kampagne `startseite-markenlinks`); jede Erwähnung belegen.
6. Optional redaktionell: die 22 Descriptions, die ein Marken-Präfix aufnehmen könnten,
   bei künftigen Artikel-Revisionen mitpflegen – keine Massenaktion.

## 9. Geänderte/neue Dateien

Neu: `data/entity.yaml`, `layouts/_partials/entity_box.html`,
`assets/css/extended/zz-entity.css`, `scripts/entity_marken_gate.py`,
`.github/workflows/entity-marken-gate.yml`, `docs/ANLEITUNG-MARKEN-ENTITY.md`, dieser Bericht.
Geändert: `hugo.toml` (2 neue Params; gesperrte Werte unberührt),
`layouts/_partials/extend_head.html`, `layouts/_partials/schema_article.html`,
`layouts/_partials/footer.html`, `layouts/_default/list.html`,
`content/ueber/index.md`, `content/impressum/index.md`, `content/presse/index.md`,
`content/newsletter-bestaetigung/index.md`, `content/newsletter-checkliste/index.md`,
`scripts/generate_llms_txt.py` + `static/llms.txt` (regeneriert),
`data/backlink_prospects.yaml`, `data/backlink_assets.yaml`, `package.json`.

*Kein externer Status in diesem Bericht ist behauptet, der nicht im Repo belegt wäre:
Publisher Center, LinkedIn/Xing und Wikidata stehen im Register auf „offen“, bis Frank sie
mit Beleg aktiviert.*

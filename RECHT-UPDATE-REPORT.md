# Recht-Update-Report

**Zweck:** Abgleich-Historie der Rechtstexte und rechtlichen Einordnungen des Blogs
(FranksFinanzcheck). Jeder Eintrag ist datiert, nennt die zugehörige Frist-ID aus
`data/recht-fristen.yaml` und bleibt auch nach Erledigung stehen. Neue Einträge
stehen oben.

**Hinweis:** Dies ist eine dokumentierte Selbsteinschätzung des Betreibers, keine
Rechtsberatung. Bei Zweifeln oder einer Änderung der Geschäftsmodelle wird eine
fachanwaltliche Prüfung empfohlen (siehe Abschnitt „Nächste Schritte“).

---

## Nachtrag 2026-11-04 · Stand des Integritäts-Locks und CI (#1051)

Im aktuellen Ausgangsstand `038b04f` ist das Integritäts-Siegel nach
`--repair-lock --dry-run` gültig und verkettet; der historische Befund vom
03.11. bleibt als damalige Beobachtung bestehen. Das Gate meldet die drei
hier geänderten geschützten Dateien (`head.html`, `cover.html`,
`generate_covers.py`) als nicht signiert. Eine bewusste Freigabe und
Neu-Signatur durch den Betreiber bleibt erforderlich; ein grünes Siegel wird
nicht vorgetäuscht. Die Deployment-Schritte sind im Blustradius-Register erfasst.
Der neue Bestandsschutz läuft auch im PR-Test bei Änderungen an Originalbildern.

Aktuelle lokale Probe mit Pillow 13.0.0: 114 Referenzen auf 113 Dateien,
80 byteidentisch und 33 abweichend; keine als KI deklariert. Weder die
Bytegleichheit noch eine Abweichung beweist die tatsächliche Herkunft. Der
Hugo-Produktionsbuild und 29 gezielte Tests waren erfolgreich; der
Integritäts-Test bleibt wegen der unsignierten Kernänderungen rot. Eine
Live-Abnahme und Anbieterbestätigungen liegen nicht vor.

---

## Nachtrag 2026-11-03 · Reproduktionsprobe und Deploy-Blocker

Die dateigenaue Reproduktionsprobe
`python3 scripts/ki_cover_render_audit.py --json` erzeugt jedes referenzierte
Cover anhand des Manifest-Titels, Badges und der Spar-Pille in einem
Temp-Verzeichnis neu und vergleicht Hash und Pixel. Sie verändert keine
Originale. Der [Einzelbeleg](data/beweise/ki-cover-render-audit-2026-11-03.json)
enthält Quellpfade, Bildhash, Vergleichshash und Hashes von Generator, Schrift
und Manifest. Ergebnis im Checkout mit Pillow 13.0.0: **113 Referenzen auf
112 Dateien, davon 80 byteidentisch und 32 abweichend**. Betrachtet man nur
Dateien, die mindestens eine Seite ohne `draft: true` referenziert, sind es
81 Dateien: 61 byteidentisch, 20 abweichend. `draft: false` ist kein Nachweis
der tatsächlichen Live-Auslieferung. Bei byteidentischen Dateien kann die
regelbasierte Pipeline denselben Dateiinhalt reproduzieren; das ist ein
starkes technisches Indiz, aber weder ein historischer Erzeugungsnachweis noch
ein KI-Detektor. Die 32 Abweichungen sind nicht automatisch KI-Bilder. Die
Einzelprüfung und externe Herkunftsdaten bleiben erforderlich. Änderungen am
Bestand entwerten die Momentaufnahme; für neue Entscheidungen erneut prüfen.

Beim im letzten Nachtrag genannten Deploy-Fehler ließ sich der konkrete
Rückfallschutz im lokalen Checkout reproduzieren: Zwei Gasartikel trugen
wieder unbelegte Preis- und Ersparnisversprechen in `pin_description`. Die
Quelle `data/pinterest_plan.yaml` hätte sie beim Pin-Sync erneut eingespielt.
Frontmatter und alle drei betroffenen Plan-Beschreibungen zum ersten Artikel
sowie die Beschreibung zum zweiten Artikel wurden sachlich bereinigt; der
Rückfallschutz prüft jetzt auch die Planquelle. Der Test läuft lokal grün.
Dies belegt nicht, dass der vollständige nächste Deploy oder das
Auslieferungs-Siegel erfolgreich sein wird; Laufprotokolle des alten Jobs
waren aus der Sandbox nicht abrufbar.

Zusätzlicher Integritätsbefund: `scripts/integrity_guard.py --gate` meldet im
Checkout ein bereits beschädigtes `data/integrity_lock.json`; die
`--repair-lock --dry-run`-Probe fand im flachen Klon keine belegte gültige
Quelle. Ein gezielter lesender GitHub-API-Abgleich fand in Commit
`8af76b5520fba6a073d20630db356546f73237a4` vom 01.11.2026 ein strukturell
intaktes älteres Siegel (Kette und Map-Prüfsumme laut `lock_zustand`). Von
seinen 55 Dateihashes weichen sieben vom Arbeitsbaum ab oder fehlen, darunter
die in dieser Arbeit geänderten `cover.html`, `head.html` und
`generate_covers.py`; es wäre also kein unveränderter Wiederherstellungsstand.
Die beiden jüngeren geprüften Fassungen `c2c83bf` und `cf1b807` sind kein gültiges
JSON. Das ältere Siegel ist nicht auf Übereinstimmung mit dem heutigen Kern
freigegeben und wurde **nicht** übernommen. Zudem ist
`scripts/generate_covers.py` für den Schutz deklarierter KI-Originale geändert
und eine geschützte Kerndatei. **Keine** menschliche
Neu-Signatur oder Freigabe wurde fingiert. Betreiber muss den Lock anhand
vollständiger Historie prüfen/reparieren und die Änderung bewusst freigeben,
bevor ein grünes Integritäts-Gate behauptet werden darf.

---

## Nachtrag 2026-11-03 · Anbieter, Cover-Bestand und Live-Stand (#1028)

**Status: technische Sicherungen ergänzt; Fremdnachweise und Live-Abnahme offen.**

### Anbieter-Recherche: Beleglage, keine erfundene Anbieterbestätigung

`data/ki_redaktion.yaml`, `scripts/llm_client.py` und die Laufdaten im Repo
zeigen als konfigurierte Textpfade Groq, NVIDIA NIM und Cloudflare Workers AI
mit `openai/gpt-oss-120b` (Workers-AI-ID mit `@cf/`) sowie Gemini als Fallback.
Umgebungsvariablen können Modell/Anbieter ändern; Konfiguration ist kein Beweis,
dass ein bestimmter Dienst zuletzt produktiv genutzt wurde. Die Sprachpipeline
`ff_voice_audio.py` nennt ElevenLabs, Microsoft Edge TTS und Piper als mögliche
Backends; tatsächlich verwendete Varianten sind gesondert zu inventarisieren.

| Quelle des Anbieters | Was sie belegt | Was offen bleibt |
|---|---|---|
| [OpenAI: gpt-oss](https://openai.com/index/introducing-gpt-oss/) | Open-weight-Modell, anderweitig betreibbar. | Kein Beleg für eine Markierung beim konkreten Hosting. |
| [Groq Services Agreement, § 6](https://console.groq.com/docs/legal/services-agreement) | Verbietet u. a. das Verändern ggf. vorhandener Provenienzinformationen. | Ob konkret genutzte Ausgaben markiert sind, Methode, Erkennung und Zeitpunkt. |
| [Cloudflare Responsible AI](https://www.cloudflare.com/trust-hub/responsible-ai/) und [Cloudflare: Watermark-Forschung](https://blog.cloudflare.com/an-early-look-at-cryptographic-watermarks-for-ai-generated-content/) | Cloudflare beschreibt Drittanbieter-Modelle und technische Forschung. | Keine produktspezifische Bestätigung für unser Workers-AI-Modell. |
| [NVIDIA Risk Assessment](https://images.nvidia.com/content/pdf/NVIDIA-Frontier-AI-Risk-Assessment.pdf) | Beschreibt mögliche Markierungstechniken allgemein. | Kein Nachweis für unsere konkrete NIM-Ausgabe. |
| [Google DeepMind: SynthID für Text](https://deepmind.google/blog/watermarking-ai-generated-text-and-video-with-synthid/) | Erklärt Verfahren und Grenzen bei Umarbeitung. | Nicht der Nachweis, dass die konkret genutzte Gemini-API-Fassung markiert ist oder nach Bearbeitung erkennbar bleibt. |
| [Gemini API: Bilder](https://ai.google.dev/gemini-api/docs/image-generation) | Google beschreibt SynthID für dort generierte Bilder. | Nicht der Nachweis, dass irgendein Blog-Cover damit entstand oder nach Konvertierung erkennbar bleibt. |

Diese Quellen wurden am 03.11.2026 recherchiert. Es gibt hier **keine** belegte
Anfrage oder Antwort von Groq, NVIDIA, Cloudflare, Google oder TTS-Anbietern.
Anfragevorlage und Abnahmeverfahren: `docs/KI-TRANSPARENZ-ABNAHME.md`.
Die Rolle je konkretem Produkt und alle Ausspielwege sind noch zu klären.

### Cover und Auslieferung

Das reproduzierbare Inventar `python3 scripts/ki_cover_provenienz.py --json`
zählte im Checkout am 03.11.2026 **113 Cover-Referenzen** über alle Bereiche,
darunter 82 nicht als Entwurf markierte und 31 Entwürfe; keine Referenz war
als KI-Bild deklariert. Alle 82 nicht als Entwurf markierten Referenzen hatten
lokale Originale und einen namensgleichen Eintrag in `data/covers_manifest.json`.
Das Manifest allein ist ein Indiz für die Pillow-Cover-Pipeline, aber **kein**
Datei-Hash oder Herkunftsnachweis; die spätere dateigenaue Reproduktionsprobe
steht im Nachtrag darüber. Auch Entwurfsstatus ist keine Live-Zählung; Inline-Bilder,
Dateien ohne Cover-Referenz und externe Kanäle sind nicht enthalten.

Die neue Wache prüft für deklarierte KI-Cover Original-SHA-256, Quellenangabe,
Prüfdatum und ausdrückliche Deepfake-Einzelfallprüfung. Bei Deepfake oder
fehlendem/veraltetem Nachweis wird Deploy gestoppt, weil OG, Pinterest und
weitere Ausspielwege nicht automatisch eine sichtbare Kennzeichnung tragen.
Das Flag ist keine automatische Herkunftserkennung. Für diese Covers liefert
Hugo die lokale Originaldatei statt neu encodierter Varianten aus; der
Cover-Generator schützt deklarierte Originale auch bei `--force`. Diese
Maßnahmen bestätigen weder die Echtheit eines Nachweises noch die Erhaltung
unsichtbarer Wasserzeichen durch externe Dienste oder CDNs.

**Live-Baseline:** Am 03.11.2026 war das [Impressum](https://franksfinanzcheck.de/impressum/)
abrufbar und zeigte noch den alten KI-Wortlaut. Das jüngste über die
GitHub-Pages-API sichtbare Deployment vom 02.11.2026 trägt SHA
`69f08c40c654e63eda3d8030eec790ee85fdbaf1`, nicht diesen Arbeitsstand.
Der jüngste Deploy-Lauf [41592649761](https://github.com/frank-hartung/franksfinanzcheck-blog/actions/runs/41592649761)
endete mit Fehler in „Faktenfrische Gas – Rückfallschutz“ und im
Auslieferungs-Siegel. Die Live-Baseline ist daher **keine Abnahme dieser
Änderung**. Nach Integration und erfolgreichem Deployment müssen die im
Runbook genannten Text-, Cover-, Listen-, Datei- und Social-Proben erneut
an der live ausgelieferten Fassung erfolgen. Frist und Issue bleiben offen.

---

## Eintrag 2026-11-03 · KI-Transparenz und Bestandssysteme (Issue #1028)

**Frist-ID:** `ki-vo-kennzeichnung-bestand` · **Status: teilweise umgesetzt,
Betreiberprüfung und Anbieter-Nachweise offen; Frist nicht erledigt.**
Dies ist eine technische und redaktionelle Selbsteinschätzung, keine Rechtsberatung.

### Quellen und Einordnung (geprüft am 03.11.2026)

- [EU-Kommission: FAQ zu Art. 50](https://digital-strategy.ec.europa.eu/en/faqs/transparency-obligations-under-article-50-ai-act):
  Art. 50 Abs. 2 verpflichtet **Anbieter** generativer KI zur
  maschinenlesbaren Markierung und Erkennbarkeit ihrer Ausgaben; bei vor
  02.08.2026 in Verkehr gebrachten Systemen ist diese Pflicht bis 02.12.2026
  zu erfüllen. Für neue Systeme gilt kein solcher Aufschub. Maßgeblich ist
  das Inverkehrbringen des Systems, nicht das Alter eines Blogbeitrags.
- Dieselbe FAQ unterscheidet davon die seit 02.08.2026 anwendbare
  **Betreiberpflicht** aus Abs. 4: Deepfakes sichtbar bzw. hörbar offenlegen;
  bei KI-Texten zur Information der Öffentlichkeit über Angelegenheiten von
  öffentlichem Interesse entfällt die Offenlegung nur bei tatsächlicher
  menschlicher Überprüfung oder redaktioneller Kontrolle **und** wenn eine
  natürliche oder juristische Person die redaktionelle Verantwortung trägt.
  Bloße Rechtschreib- oder automatische Qualitätsprüfung genügt nicht.
  Finanzratgeber sind vorsorglich einzeln auf öffentliches Interesse zu prüfen.
- [eRecht24: Deepfakes und Textausnahme](https://www.e-recht24.de/ki/13539-deepfakes.html)
  und [IT-Recht Kanzlei: KI-Bilder und Produkttexte](https://www.it-recht-kanzlei.de/ki-bilder-online-shop-kennzeichnungspflicht.html)
  bestätigen die Differenzierung. Die Kommission erläutert zudem, dass vor
  02.08.2026 erzeugte Inhalte nicht rückwirkend gekennzeichnet werden müssen;
  freiwillige Kennzeichnung bleibt sinnvoll. Im Einzelfall Rechtsstand prüfen.

### Entscheidung und Umsetzung

Ein allgemeiner Impressum-Hinweis allein ist **kein Ersatz** für einen ggf.
notwendigen klaren Hinweis am konkreten Inhalt bei erster Wahrnehmung. Ein
HTML-Meta-Tag, ein `data-`Attribut oder ein Footer sind kein Nachweis für die
robuste, interoperable Anbieter-Markierung der Ausgabedatei nach Abs. 2.
Keine pauschale Behauptung einer erfüllten Anbieterpflicht oder C2PA-Signatur.

- Artikel mit `ai_generated: true` zeigen nun „Mit KI erstellt oder bearbeitet“
  am Artikelanfang, auch wenn eine redaktionelle Freigabe vorliegt. Der alte
  Wortlaut „Mit KI-Unterstützung recherchiert“ deckte das Erstellen nicht ab.
  Das `data-ff-ki-label` ist lediglich ein lokal maschinenlesbarer HTML-Haken,
  kein Wasserzeichen. Das Gate kann bei ungeklärter Herkunft vorsorglich
  `true` setzen: Das ist keine verifizierte Provenienz.
- Bild und Text werden getrennt behandelt: Nur bei **belegter** KI-Erzeugung
  oder -Bearbeitung eines Covers `cover.ai_generated: true` im Frontmatter
  setzen. Dann erscheint die sichtbare Bildunterschrift im Artikel **und** in
  Listen. Andere Covers bleiben unverändert; bestehende Bildunterschriften
  bleiben erhalten. Beispiel:

  ```yaml
  cover:
    image: images/covers/beispiel.jpg
    alt: Beschreibung des Bildinhalts
    ai_generated: true
    ki_pruefung:
      sha256: "<SHA-256 der unveränderten Originaldatei>"
      quelle: "<konkreter Herkunftsnachweis>"
      geprueft_am: 2026-11-03
      deepfake: false # nur nach tatsächlicher Einzelfallprüfung
  ```

  Die eigene `scripts/generate_covers.py`-Pipeline zeichnet Branding-Cover
  mit Pillow regelbasiert; KI-Text im Cover macht das Bild nicht automatisch
  zu einem KI-generierten Bild. Ein Flag wird deshalb nicht pauschal gesetzt.
  Ein neuer Bildnachweis muss sich auf die tatsächlich ausgelieferte Datei
  beziehen und bei Austausch/Neugenerierung aktualisiert werden. Es wurde
  kein einzelnes Bestandsbild als KI-generiert verifiziert.
- Der Hinweis gilt für das Hugo-Cover auf diesen Seiten, **nicht** automatisch
  für OG-/Pinterest-Dateien, externe Plattformen, RSS, einzelne andere Bilder
  oder heruntergeladene Bilddateien. Falls ein Deepfake dort erscheint, vor
  Veröffentlichung auf jedem Ausspielweg gesondert sichtbar kennzeichnen
  oder die Ausspielung unterbinden. Bildunterschrift ersetzt keine
  Provider-Markierung; Varianten und Metadaten nach Umwandlung prüfen.
- Das Widget ist in `layouts/baseof.html` eingebunden, aber laut
  `layouts/_partials/ki_assistent.html` ohne konfigurierten Endpoint deaktiviert;
  im eingecheckten `hugo.toml` ist keiner gesetzt. Eine Aussage über eine
  abweichende Live-/Deploy-Konfiguration ist damit nicht belegt. Vor
  Aktivierung Interaktionshinweis und Verantwortlichkeiten erneut prüfen.

### Offen vor Fristabschluss

1. Betreiber inventarisiert tatsächlich eingesetzte Text-/Bild-/Audio-Systeme,
   Anbieter, Versionen, Rolle (auch mögliche Eigenanbieterrolle) und Datum des
   Inverkehrbringens; fragt Anbieter nach Art.-50-Abs.-2-Markierung,
   Erkennbarkeit und deren Grenzen und dokumentiert Antworten. Das Repo nennt
   z. B. in `scripts/ki_shared.py` Groq, NVIDIA, Cloudflare und Gemini; welche
   davon aktuell produktiv genutzt werden und wie sie markieren, ist offen.
2. Betreiber prüft alle real verwendeten Bilder und Ausspielwege auf Herkunft
   und Deepfake-Risiko, setzt nur belegte Flags und dokumentiert Entscheidungen.
   Auch eine Bildgenerierung außerhalb des Repos ist möglich; aus dem Repo
   allein ist Vollständigkeit nicht belegbar.
3. Das Register `data/ki_kennzeichnung.yaml` enthält selbst als ungeklärt
   beschriebene `menschlich`-Einträge; ein bloßer `freigegeben`-Status im
   Kennzeichnungsgate beweist keine tatsächliche Prüfung. Betreiber muss diese
   Einträge und die jeweilige veröffentlichte Fassung prüfen, gegebenenfalls
   kennzeichnen; automatische Prüfungen nicht als menschliche Freigabe ausgeben.
4. Nach Merge/Deploy Live-Artikel, Listen und ggf. externe Ausspielungen prüfen;
   Freigabe und ggf. Rechtsberatung dokumentieren. Erst danach den vorgesehenen
   Workflow mit `erledigt=ki-vo-kennzeichnung-bestand` ausführen. Issue #1028
   und Fristenstatus bleiben bis dahin offen.

**Regression:** `scripts/tests/test_ki_transparenz_render.py` rendert echte
Hugo-Fixtures für KI-Text, Freigabe, KI-Bild und unbekannte Bildherkunft; der
Deploy führt den Test aus. Der Test belegt weder Bildinventar noch Rechtskonformität.

---

## Eintrag 2026-10-11 · Tarifcheck-Anbieterkennzeichnung im Impressum

| | |
|---|---|
| **Frist-ID** | keine (Umsetzung einer Programm-Vorgabe, kein Fristen-Eintrag) |
| **Kategorie** | Anbieterkennzeichnung / Datenschutz |
| **Ergebnis** | iframe des Tarifcheck-Partnerprogramms im Impressum, Datenschutzhinweis ergänzt |

Das Partnerprogramm verlangt die Einbindung von
`a.partner-versicherung.de/filestore/ad/1166/` mit der Partner-ID 47086.
Das Snippet allein wäre 150 px hoch und mit `scrolling="no"` abgeschnitten.
Es liegt deshalb in `layouts/shortcodes/partner_impressum.html` (nicht im
Markdown, damit der Affiliate-Shield die URL nicht auf eine `/go/`-Route
umbiegt), mit Titel, ausreichender Höhe, Fallback-Link und Hinweis auf den
Datenabruf.

Die Datenschutzerklärung nennt den Abruf beim Seitenaufruf, die Rechtsgrundlage
Art. 6 Abs. 1 lit. f DSGVO und die offene Prüfung zu Cookies und § 25 TDDDG.
Eine Einwilligungs-Wand vor dem Dokument wurde nicht gesetzt: die Kennzeichnung
soll im Impressum sichtbar sein. Ob das Dokument Cookies setzt, ist an der
Live-Antwort noch nicht geprüft.

Dies ist eine dokumentierte Umsetzung, keine Rechtsberatung.

---

## Eintrag 2026-10-10 · BFSG-Scope-Bewertung

| | |
|---|---|
| **Frist-ID** | `bfsg-barrierefreiheit-bewertung` (Issue #689) |
| **Kategorie** | Barrierefreiheit |
| **Gewicht** | Empfehlung (einmalig) |
| **Fällig am** | 31.10.2026 |
| **Ergebnis** | Kein BFSG-Scope. Die Bewertung stützt sich auf zwei unabhängige Gründe. |

### Kurz-Bewertung

Das Barrierefreiheitsstärkungsgesetz (BFSG, in Kraft seit 28.06.2025) erfasst
Dienstleistungen im elektronischen Geschäftsverkehr, also digitale Dienste, die
auf individuelle Anfrage eines Verbrauchers im Hinblick auf den Abschluss eines
Verbrauchervertrags erbracht werden. FranksFinanzcheck schließt selbst keine
Verbraucherverträge ab. Die Werkzeuge rechnen im Browser, die Artikel informieren,
und die Partnerlinks führen zu Verträgen, die Dritte (CHECK24, Tarifcheck) mit den
Lesern schließen. Selbst wenn ein Teil davon als Dienstleistung im Sinne des BFSG
gälte, greift für Kleinstunternehmen die Ausnahme des § 3 Abs. 3 Satz 1 BFSG für
Dienstleistungen, sofern die Schwellen (weniger als zehn Beschäftigte, Jahresumsatz
oder Bilanzsumme jeweils höchstens 2 Mio. €) erfüllt sind. Diese Angaben sind vom
Betreiber noch zu bestätigen (siehe unten). Der Blog verkauft keine Produkte, auf
die die Ausnahme nicht anwendbar wäre.

### Prüfrahmen

- **Rechtsgrundlage:** BFSG (Fassung ab 28.06.2025), insbesondere
  - § 1 Abs. 3 Nr. 5: Dienstleistungen im elektronischen Geschäftsverkehr,
  - § 2 Nr. 26: Definition (digitale Dienste über Webseiten oder Apps, elektronisch
    und auf individuelle Anfrage eines Verbrauchers im Hinblick auf den Abschluss
    eines Verbrauchervertrags),
  - § 3 Abs. 3 Satz 1: Ausnahme für Kleinstunternehmen, die Dienstleistungen
    anbieten oder erbringen (gilt nicht für Produkte),
  - § 2 Nr. 17: Definition Kleinstunternehmen (weniger als zehn Personen und
    Jahresumsatz oder Jahresbilanzsumme jeweils höchstens 2 Mio. €).
- **Quellenstand:** Abgleich über Fachkommentierungen (u. a. IHK München, Stand
  2026; sitebrunch-Überblick). Vor einer Veröffentlichung ist der amtliche
  Gesetzestext zu prüfen. Die Paragrafen sind in dieser Fassung aus der
  Sekundärliteratur übernommen.

### Prüfung der Angebotsbestandteile

| Bestandteil | Vertragsabschluss durch den Betreiber? | Einordnung |
|---|---|---|
| Ratgeber-Artikel (`content/posts`, Pillar-Seiten) | nein | Kein BFSG-Scope |
| Werkzeuge (Rechner, Kündigungsfristen-Kalender, Tarifwechsel-Entscheidungsbaum, Budget) | nein, Berechnung im Browser | Kein BFSG-Scope |
| Fixkosten-Cockpit | nein, Speicherung lokal im Browser | Kein BFSG-Scope |
| Newsletter (kostenlose Anmeldung) | nein, kein Entgelt | Kein BFSG-Scope; Restrisiko gering |
| Affiliate-Links zu CHECK24 und Tarifcheck | nein, der Vertrag kommt bei Dritten zustande | Grauzone bei der Vermittlung; hier trägt die Kleinstunternehmen-Ausnahme |
| Verkauf von Produkten (Shop, E-Books, Merchandise) | nicht vorhanden | Ausnahme gilt nicht für Produkte, daher Neubewertung bei Einführung |

### Tragende Begründung

1. **Kein eigener Verbraucher-Vertragsabschluss.** Die Angebote informieren oder
   rechnen. Ein Vertrag entsteht immer bei einem Dritten.
2. **Kleinstunternehmen-Ausnahme (§ 3 Abs. 3 Satz 1 BFSG).** Der Betreiber tritt
   als natürliche Person auf (Impressum: Frank Hartung, ohne Firmenzusatz). Die
   Schwellen sind nachzuweisen (siehe „Zu bestätigen“).

### Zu bestätigen (Betreiber)

- [ ] Anzahl der Beschäftigten (einschließlich Inhaber) unter zehn.
- [ ] Jahresumsatz oder Jahresbilanzsumme jeweils höchstens 2 Mio. €
  (Nachweis: letzter Steuerbescheid bzw. Jahresabschluss oder EÜR).

Solange diese Punkte nicht bestätigt sind, gilt die Bewertung als vorläufig.

### Neubewertung auslösen, wenn …

- ein Shop oder Produktverkauf eingeführt wird (auch E-Books, Printprodukte, Merchandise),
- Terminbuchungen oder Vertragsabschlüsse direkt auf der Website angeboten werden,
- ein Vermittlungsangebot mit eigenem Abschluss im Haus entsteht (keine reinen
  Affiliate-Links),
- die Kleinstunternehmen-Schwellen überschritten werden,
- das BFSG oder die Auslegung durch die Marktüberwachung geändert wird.

### Goodwill-Nachweis: Stand Barrierefreiheit (Verweis)

Der Blog betreibt unabhängig von der Pflicht ein laufendes Barrierefreiheits-Audit:

- **Automatisches Audit:** `scripts/a11y_audit.py` prüft gebaute Seiten auf
  lang-Attribut, Seitentitel, genau eine H1, alt-Texte, Skip-Link, sichtbare
  Fokus-Styles, `prefers-reduced-motion` und Kontrast der Branding-Farben
  (WCAG-2.1-Teilmenge). Seit der Härtung vom 07.10.2026 läuft es über alle gebauten
  Seiten statt über eine Stichprobe von 20 Seiten.
- **Stand 08.10.2026:** 85 Seiten vollständig geprüft, 0 Befunde, 0 Kontrast-Fehler
  (Quelle: `A11Y-EINE-H1-DAUERHEILUNG-PREMIUM-2026-10-08.md`, Abschnitt „Nachweis“).
  Vorgängerbericht: `A11Y-EINE-H1-DAUERHEILUNG-PREMIUM-2026-10-07.md`.
- **Grenzen:** Ein automatisches Audit deckt nur einen Teil der WCAG ab. Der Blog
  veröffentlicht daher keine Konformitätsaussage und keine Barrierefreiheitserklärung,
  weil diese nur für in Scope befindliche Angebote verpflichtend und nur mit
  manueller Prüfung belastbar wären.

### Quellen im Repo

- `data/recht-fristen.yaml` (Frist `bfsg-barrierefreiheit-bewertung`)
- `docs/INFRASTRUKTUR.md` (Fristen-Übersicht, BFSG-Scope-Bewertung einmalig)
- `scripts/a11y_audit.py`, `scripts/h1_wache.py`
- `A11Y-EINE-H1-DAUERHEILUNG-PREMIUM-2026-10-07.md`, `A11Y-EINE-H1-DAUERHEILUNG-PREMIUM-2026-10-08.md`

### Nächste Schritte

1. Beschäftigten- und Umsatzschwellen bestätigen (Betreiber, bis 31.10.2026).
2. Bewertung bei jedem Neubewertungs-Auslöser erneut prüfen.
3. Die Bewertung im quartalsweisen Rechtslage-Screening mitführen.
4. Bei Zweifeln eine fachanwaltliche Prüfung (IT-/Medienrecht) einholen.

---

*Verantwortlich: Frank Hartung. Pflege gemäß Frist `bfsg-barrierefreiheit-bewertung`.*

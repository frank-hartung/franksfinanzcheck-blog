---
name: ff-marke-text
description: "Benutzen für jeden Text und jede Text-Nebenfläche dieses Blogs: Artikel schreiben oder umformulieren, Überschrift, Description/Snippet, Cover-Bild, lastmod, Tags und Kategorien, Keyword-Optimierung, Werbe-Offenlegung und Affiliate-Kennzeichnung, Rechtschreibung/Grammatik/Lesbarkeit, Faustregeln, Pinterest-Pins und Instagram-Winkel, README-Text, Abschlussvermerk an ein Issue, 'zu lang für Google', 'Snippet abgeschnitten', 'Tag fehlt', 'muss hier eine Offenlegung hin'. Dieser Skill enthält die sprachlichen und ausweisenden Verträge inklusive der einen Zahlengrenze. Nicht für Layout/CSS (ff-oberflaeche) und nicht für Produktionszählung (ff-produzieren)."
metadata:
  version: 1.0.0
  besitz: repo-eigen – kein Eintrag in skills-lock.json, nie von `npx skills update` anfassen
  quelltext: CLAUDE.md-Kernregeln, wörtliche Details in references/
---

# Marke und Text: was draußen steht, ist die Wahrheit

Der Anspruch dieses Blogs ist an zwei Stellen messbar, nicht im Textgefühl:
**sprachlich mindestens auf dem Niveau von ZEIT.de**, jedoch mit eigenständiger
Stimme und ohne Nachahmung – und **nach außen hin vollständig ausgewiesen**
(Offenlegung, Quellen, Tag-Register, Snippet-Fenster des Marktes). Alles hier
ist wörtlich aus `CLAUDE.md` übernommen.

## Wann dieser Skill zählt

- Du schreibst oder glättest Fließtext, Titel, Description, Pin-Text.
- Ein Befund nennt Länge, Breite, Lesbarkeit, Großschreibung, Grammatik.
- Ein Artikel braucht Tags, Quellen, Offenlegung oder ein Cover.
- Du willst dem `README.md` etwas hinzufügen oder ein Issue kommentieren.
- Ein Pinterest-/Instagram-Kanal soll senden.

## Die harten Kernregeln

1. **Form folgt dem Thema**, nicht umgekehrt: Einstiege, Übergänge,
   Überschriftenrhythmus und Schlüsse werden nicht schematisch wiederholt. Jeder
   Artikel braucht einen eigenen Blick, eine konkrete Beobachtung oder ein
   tragfähiges Bild. Die maschinenlesbare Leitplanke steht in
   `data/schreibstil.yaml` unter `eigenstaendigkeit`.
2. **Eine Zahl, zwei Messstellen:** `scripts/serp_limits.py` (100/155 Zeichen,
   985 px in Arial 14 px). `metadaten_wache` und `seo_cockpit` **importieren**;
   auch `keyword_optimizer`, `meta_optimizer` und `quality_score` tun das. Eine
   zweite Grenze im Code ist ein Befund.
3. **Breite ist nicht Zeichenzahl.** 135 breite Wörter laufen über 985 px.
   Zeichen ohne Metrik (Emoji, CJK) werden nicht geschätzt: `breite_px()` gibt
   `None`, die Wache meldet „nicht prüfbar“.
4. **Ein Link braucht Text, nicht nur `aria-label`** – `sr-only`-Spanne im Link.
   „Mehrere H2“ ist kein Befund, eine übersprungene Rangstufe ist einer.
5. **Tags kommen aus dem Register, nie aus Keywords.**
   `tag_governance.tags_fuer()` ist die einzige erlaubte Tag-Quelle; ein Tag
   wird nie erfunden. Es gibt keine Taxonomie-Archive mehr – wer Archive
   zurückholt, muss `max_tag_archive` in `index_hygiene_gate.py` mit anheben.
6. **Offenlegung ist artikelgenau und steht über dem ersten Partnerlink** (O1–O7,
   `offenlegung_gate.py`, **ohne** `--fix`). Eine Quelle:
   `data/affiliate_ziele.yaml`. Nie eine zweite Partnerliste anlegen.
7. **Ein Cover ist nur wahr, wenn es aus seinem Titel neu rendert.** Reparatur
   ausschließlich über `generate_covers.py`, nie am JPG von Hand.
8. **Das `README.md` ist Markenfläche:** dort steht nichts über die Maschine.
   Technik gehört nach `docs/ENTWICKLER-WERKZEUGE.md`. Vor jedem
   README-/Issue-Kommentar-Lauf die Marken-Wache.
9. **Vorgänge werden mit Nachweis geschlossen:** `Closes #<Nummer>` in den
   Vorschlag, den Vermerk schreibt der Workflow – nie von Hand nachkommentieren.
10. **Ohne Beleg kein Satz.** Zahlen mit Einheit brauchen den Quellenlink im
    selben Satz oder die Kennzeichnung als Beispiel-/Modellrechnung; „ca./rund“
    ist kein Beleg (RS5).

## Katalog

| Deine Frage | Antwort im Detail |
|---|---|
| Was darf ins README, wie schließt ein Vorgang? | `references/markenflaeche-und-abschluss.md` (#552, WF-A4E0) |
| Sprachlatte, Rechtschreib-Provider, Auto-Fix-Grenzen? | `references/sprache-und-rechtschreibung.md` (#806) |
| Snippet-Länge/-Breite, `lastmod`, Cover, Tags? | `references/metadaten-serp-tags.md` (#743, #925, 237 Seiten / 347 URLs) |
| Wo muss die Offenlegung hin, was genau muss sie sagen? | `references/kennzeichnung.md` (#623) |
| Pin-Ziel defekt, Hashtag-Zahl, Instagram-Winkel blind? | `references/verbreitung.md` (C37, C43, #716) |

## Fremd-Skills: Marketing-Pack

Diese Anlage liefert Handwerk, das `scripts/social_copywriter.py` und die
Redaktions-Engine nicht abdecken. **Sie ist Vorschlag, nicht Vertrag** – was in
diesem Skill und in `data/social/channels.yaml` steht, gilt (K3 verlangt seit
01.11.2026, dass **jeder** installierte Skill in einem Router steht: ein Skill,
den niemand nennt, kostet bei jedem Start Beschreibung und wird nie gewählt).

Das SEO-Paket `claude-seo` liegt nicht hier, sondern am Hub `seo` (siehe
`CLAUDE.md`, „Fremd-Skills mit eigenem Router"): es hat eigene Werkzeuge und eine
eigene Zuständigkeit.

### Marketing-Pack (`coreyhaines31/marketingskills`, MIT)

Elf Skills aus dieser Anlage. Sie decken
die Arbeit an Auffindbarkeit und Wettbewerb ab; die Grenze steht in der letzten
Spalte, weil diese Skills den Markt beschreiben, nicht dieses Haus.

| Auftrag | Skill | Grenze im Haus |
|---|---|---|
| Seitenaufbau, Navigation, interne Verlinkung | `site-architecture` | kein URL-Umbau ohne Redirect-Plan, keine Taxonomie-Archive (D17) |
| Technisches SEO-Audit | `seo-audit` | der Befund ist ein Vorschlag; Wahrheit sind die Gates (`npm run seo:check`) |
| Strukturierte Daten | `schema` | JSON-LD entsteht im Template, nicht als Text im Artikel |
| Viele Seiten aus einer Vorlage | `programmatic-seo` | nur über die Engine (`ff-produzieren`), nie als Textlawine |
| Auffindbarkeit in KI-Antworten | `ai-seo` | keine Zitierquoten behaupten, die niemand gemessen hat (D15) |
| Wettbewerber vergleichen | `competitor-profiling`, `competitors` | es gelten die Vergleichsgrundsätze, nicht die des Skills |
| Themenplan, Ideen, Kalender | `content-strategy` | Slots und Quote rechnet `ff-produzieren` |
| Werbetext, Headline, CTA | `copywriting` | ZEIT-Latte und eigene Stimme gewinnen (D3) |
| Bestehenden Text nachschärfen | `copy-editing` | Lesbarkeit misst `lesbarkeit_schreiber.py` (D14) |

Nicht hier geroutet: `analytics` (Messung – gesperrt, siehe `ff-pruefen`),
`cro` und `animate` (Oberfläche – siehe `ff-oberflaeche`).

### Pflege beider Anlagen

Nur über den CLI (`npx -y skills@1.7.4 add|update|remove`), danach Lizenztext und
Register nachziehen und `npm run skills:check` fahren. Wer verkleinert, entfernt
Skills; Beschreibungen kürzen hält nicht, weil `npx skills update` sie
überschreibt. Der K9-Vorrat ist mit dem SEO-Paket aufgebraucht: 56 KB sind die
Grenze, und sie wird nicht stillschweigend verschoben.

## Kommando-Notausgang

```bash
npm run metadaten:check              # M1–M6: Titel, Description, lastmod, Pflichtfelder, Zahlenversprechen
npm run offenlegung                  # O1–O7, artikelgenau, sichtbar
npm run test:grammatik               # LT1–LT6 (Wendungen + Kongruenz), Genus-Lexikon-Prüfung
npm run test:rechtschreibung         # ZEIT-Wache, offline
npm run marke:check                  # Markenfläche README (offline, < 1 s)
python3 scripts/metadaten_wache.py --fix   # kürzt zu breite Snippets an der Wortgrenze
```

## Nicht zuständig für

- **CSS, Dark Mode, Varianten, Figma-Handoff, Laufzeit-JS** → `ff-oberflaeche`
- **Wer wann produziert und mit welcher Belegkette** → `ff-produzieren`
- **Recherche, die ein Text braucht** → `ff-ki-automation`

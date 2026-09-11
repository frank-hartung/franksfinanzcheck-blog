# HUB-SEKTIONS-REPARATUR 2026-09-11 – /posts/ auf Premium-Level, dauerhaft

**Auftrag (Frank):** „Hier findest du alle Ratgeber … Bitte dauerhaft auf Premium-Level reparieren und optimieren.“
**Rollen-Lupe:** Agentur (Marken-Ton) · Pinterest (Pin-/Snippet-tauglicher Teaser) · Affiliate ( CHECK24-Transparenz, interne Klickpfade) · Chefredaktion (Struktur, Zusagen) · Lektorat (Rechtschreibung/Zeichen).

## 1 · Befund (live auf franksfinanzcheck.de/posts/ und /posts/page/2…4)

| # | Schaden | Schwere |
|---|---|---|
| 1 | `Hhierfindest du` – Klebe-Artefakt + fehlendes Leerzeichen im „Kurz & knapp“-Intro | Rot – auf ALLEN 4 Listenseiten sichtbar |
| 2 | `### Ddeine6 Themenwelten` – Inserter-Artefakt in der H3; öffentlicher Anker `#ddeine6-themenwelten` | Rot |
| 3 | Meta-Description 212 Zeichen (posts-Hub) / 195 (pillar-Hub) – Google kürzt hart, Kernbotschaften fielen aus dem Snippet | Orange |
| 4 | `Praxis-getestet` im Frontmatter (falsche Durchkopplung) | Orange |
| 5 | Hub-Links als `../../posts/…`-Relativpfade – funktionieren nur, solange Hugo die Page-Ref-Auflösung exakt so betreibt (stille Landmine bei Ref-/Pagination-Umbau) | Orange |
| 6 | Der komplette ~2,5-km-Intro-Block incl. H2/H3-Struktur wurde auf /posts/page/2/–/4/ dupliziert (Duplicate Content + „Such dir **oben** die Themenwelt“-Verweis, der auf Seite 2+ ins Leere zeigt) | Orange |
| 7 | Intro versprach „nutze die Suche (oben)“ – eine Suche existiert nicht (kein `content/search`-Page, kein fuseOpts) | Orange (UX-Lüge) |
| 8 | „WLAN in jede Ecke bringen“ stand ohne Link da, obwohl der passende Ratgeber existiert | Gelb (verschenkter interner Klick) |

## 2 · Reparatur (Inhalt)

`content/posts/_index.md`:
- Intro repariert UND geschärft: „Hier findest du alle Ratgeber … Jeder Artikel liefert konkrete Euro-Beträge, ehrliche Vor- und Nachteile und eine Schritt-für-Schritt-Anleitung – der Tarifwechsel dauert oft nur 15 Minuten.“ (349 Zeichen – Pin-/Snippet-tauglich, die 15-Minuten-Zusage deckt sich mit dem Fazit-Abschnitt, kein Widerspruch).
- `### Deine 6 Themenwelten` wiederhergestellt; alle 6 Themenwelten behalten (Zahl stimmt nach wie vor).
- Alle Post-Links auf wurzel-absolut `/posts/<slug>/` normalisiert; jeder Ziel-Slug gegen die Content-Struktur verifiziert (alle existieren, keiner Draft). WLAN-Hinweis mit echtem Link hinterlegt (interner Klickpfad zur vollen Themenwelt).
- Beschreibung auf 159 Zeichen getrimmt (SERP-Korridor 80–160), `praxisgetestet` korrekt gekoppelt, Keyword `Spartipps` ergänzt, `lastmod: 2026-09-11` (die Seite verspricht „sortiert nach Aktualität“ – da muss das Frische-Signal stimmen).
- Suche-Versprechen ersetzt durch das, was existiert: die Themenleiste direkt unter dem Text.
- Affiliate-Block (CHECK24-Transparenz + Disclaimer-Link) bewusst unverändert – Compliance-Beweis der Affiliate-Wachen bleibt unangetastet.

`content/pillar/_index.md`: Beschreibung 195 → 156 Zeichen, Spareffekt-Botschaft („bis zu 2.000 € Fixkosten pro Jahr“) bleibt im Snippet sichtbar.

`layouts/_default/list.html` (Hugo): Sektions-Intro rendert jetzt **nur auf Seite 1**; Seite 2+ erhalten einen kompakten Rückverweis auf die Übersichtsseite inkl. Themenwelt-Anker. Kein Duplicate Content mehr, alle „oben/unten“-Verweise bleiben wahr. Andere Sektionen/Taxonomien verhalten sich unverändert.

## 3 · Dauerschutz (neue Wache, kein Einzelfix)

Der Live-Schaden war kein Erkennungs-, sondern ein **Gate-Problem**: `textverstaendnis_guard.py` meldete R9-Funde auf Hub-Seiten nur im Report – und dort schnitten die ersten 60 Artikel-Funde die Hub-Zeilen ab. Zudem war die Zone „Sektions-Hub“ ohne jeden Blocker.

`scripts/textverstaendnis_guard.py` (R2–R9 → **R2–R14**):
- **R10-ZAHL-KLEBER** – Buchstabe klebt an Ziffer (`Ddeine6`, `zahlst20`); Marken/Akronyme (CHECK24, CAT7, MP3) und „90ern“ bleiben per Bauweise verschont.
- **R11-HUB-LINK** – `../`-ausbrechende Links in `content/**/_index.md` sind hart verboten (Hausstandard: wurzel-absolut).
- **R12-HUB-ZIEL** – jeder `/posts/<slug>/`- und `/pillar/<slug>/`-Link eines Hubs muss auf ein existierendes, nicht als Draft markiertes Content-Bundle zeigen (fängt auch künftige Slug-Umbauten).
- **R13-HUB-META** – Titel 10–130, Description 80–160 Zeichen, `lastmod` gültig & nicht in der Zukunft; posts-Hub braucht `lastmod` zwingend.
- **R14-KURZ-BLOCK** – das „> 💡 **Kurz & knapp:**“-Zitat muss erstes Element des posts-Hubs bleiben (Snippet-/Pin-/Vorlese-Kanon; die Vorlese-Engine erkennt genau diese Dachzeile und überspringt sie korrekt) und ≤ 420 Zeichen tragen.
- Report sortiert jetzt **harte Funde zuerst** (Hub-Zerfall wird nie wieder abgeschnitten); neuer Modus `--hub-gate` = reiner Blocker ohne Schreibzugriff.
- Nebenfunde bereinigt: `zzgl` war als Klebe-Artefakt gemeldet und hätte jeden neuen Artikel im Engine-Gate blockiert → in R9-Allowlist (DIN-Abkürzung), inkl. Negativ-Selbsttest.

**Verdrahtung (dauerhaft, doppelt gemoppelt – mit Absicht):**
1. `.github/workflows/link-check.yml` (Qualitäts-Gate): eigener harter Schritt `--hub-gate` nach dem Hugo-Build + Selbsttest des Guards in der Wachen-Liste (jetzt 12 Wachen) → **jeder Push/PR mit Hub-Rot wird blockiert**.
2. `.github/workflows/blog-health-daily.yml`: `--hub-gate` im täglichen Cron – fängt `[skip ci]`-Bot-Commits ab (Genau so ein Bot-Commit trug die Artefakte historically durch). Fund → roter Run → `alert-on-failure.yml` öffnet das Issue.

Sabotage-Beweis: beide Original-Bugs (`Hhierfindest`, `Ddeine6`) + ein `../`-Link + eine kaputte Description wurden testweise re-injiziert – `--hub-gate` meldete alle 5 Fundstellen und Exit 1; nach Rücknahme wieder Exit 0.

## 4 · Verifikation (Stand dieses Commits)

- `textverstaendnis_guard.py --selftest` ✅ (inkl. 11 neuer eingefrorener Hub-Fälle: Positiv + Negativ)
- `textverstaendnis_guard.py --hub-gate` ✅ (9 Hub-Seiten grün)
- Voll-Audit neu gelaufen: TEXTVERSTAENDNIS-REPORT.md mit Hub-Zählung, harte Funde zuerst; keine Hub-Funde mehr.
- Link-Ziel-Audit über alle 12 Hub-Links gegen content-Struktur ✅; pillar-Hub-Kinder `strom-sparen/` … validiert.
- Hugo-Bau ist in dieser Sandbox netzseitig nicht möglich (Release-Download blockiert) – der Push/PR-Workflow `link-check.yml` führt `hugo --minify` + internen Link-Check als echten Beweis; Layout-Änderung nutzt nur Standard-Template-Idiome (`with .Paginator` / `PageNumber`),if/else-Balance geprüft.

## 5 · Nach dem Merge zu beachten

- /posts/ und /posts/page/2+ rendern nach Deploy neu; Google-Snippet der Sektion nutzt die neue 159-Zeichen-Description.
- Pinterest-Feeds sind unberührt (Pin-Texte speisen sich aus Artikel-Frontmatter, nicht aus dem Hub) – der Hub-Teaser ist aber kuratiert kurz genug, falls er je als Abschnitts-Pin gezogen wird.
- Wer neue Ratgeber verlinkt: `../../../posts/…` war einmal – Guard R11/R12 erzwingt jetzt wurzel-absolut + existierendes Ziel.

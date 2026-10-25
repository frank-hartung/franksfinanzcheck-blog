# Anleitung: Marken-Entity pflegen (FranksFinanzcheck vs. FINANZCHECK.de)

> **Vertrag:** `data/entity.yaml` · **Wache:** `scripts/entity_marken_gate.py` (`npm run entity:check`) ·
> **Auslöser:** SERP-Live-Prüfung 25.10.2026 §3 – Google korrigiert „FranksFinanzcheck" auf
> „Frank Finanzcheck" und schlägt das Kreditvergleichsportal FINANZCHECK.de vor.
> **Bericht:** `MARKEN-ENTITY-HIGHEND-2026-10-25.md`

## 1. Das System in einem Bild

Ein Identitätssatz, eine Abgrenzung, eine Profil-Liste – überall wortgleich:

```text
data/entity.yaml  (Vertrag: definition, abgrenzung, profile_aktiv/geplant)
      │ wortgleich (Gate E2/E3)
      ├─ hugo.toml  params.entityDefinition / entityAbgrenzung   ← Build-Quelle
      │     ├─ Startseite: Entity-Box (sichtbar) + Organization-Schema
      │     └─ Artikel: Publisher-Schema (schema_article.html)
      ├─ content/ueber/, content/impressum/, content/presse/    ← Lese-Flächen
      └─ scripts/generate_llms_txt.py → static/llms.txt         ← KI-Fläche

hugo.toml [[params.socialIcons]]  (die EINE Profil-Liste, Gate E4)
      ├─ sameAs in Person + Organization + Article-Publisher
      └─ sichtbare rel=me-Links im Footer (jede Seite)
```

**Wortlaut ändern** (nur so bleibt alles synchron):
1. `data/entity.yaml` (`definition`/`abgrenzung`) anpassen
2. `hugo.toml` (`entityDefinition`/`entityAbgrenzung`) identisch nachziehen
3. `content/ueber/index.md`, `content/impressum/index.md`, `content/presse/index.md` nachziehen
4. `scripts/generate_llms_txt.py` nachziehen + `python3 scripts/generate_llms_txt.py` laufen lassen
5. `npm run entity:check` muss grün sein
6. Externe Bios/Verzeichnisse mit `definition_kurz` aus `data/entity.yaml` abgleichen

## 2. Google Publisher Center einrichten (Frank, ca. 20 Minuten)

Das kann kein Code übernehmen – es braucht das Google-Konto, dem die Search-Console-Property gehört.
Vorbereitet ist alles Repo-seitige (prüft Gate E7 laufend): RSS-Feed, Logo, Pressekontakt, Beschreibungstext.

1. **publishercenter.google.com** öffnen, mit dem GSC-Konto anmelden.
2. **Publikation hinzufügen** mit exakt diesen Werten:
   - **Name:** `FranksFinanzcheck`
   - **Primäre Domain:** `franksfinanzcheck.de` (Verifizierung läuft über die vorhandene Search Console)
   - **Land:** Deutschland · **Primärsprache:** Deutsch
   - **Beschreibung:** `FranksFinanzcheck (franksfinanzcheck.de) ist das unabhängige Fixkosten-Cockpit für deutsche Haushalte: ein redaktioneller Ratgeber von Frank Hartung, der Verträge, Fristen und laufende Kosten mit nachvollziehbarer Rechnung ordnet – kein Bankportal, kein Kreditvergleichsportal und keine Versicherungsmakler.`
   - **Kontakt:** `kontakt@franksfinanzcheck.de`
3. **Logo:** quadratisches Raster-Logo hochladen: `https://franksfinanzcheck.de/images/pwa/icon-512.png`
   (512 × 512, liegt bereits auf der Site). Das SVG-Markenlogo (`static/images/brand/logo.svg`)
   ist brand-lock-geschützt – Ableitungen nur über `scripts/bake_brand.py`, nie von Hand umbauen.
4. **Inhalte/Feed:** RSS-Quelle `https://franksfinanzcheck.de/index.xml` eintragen
   (Home-Feed mit den neuesten Artikeln).
5. **Nach der Freigabe:** In `data/entity.yaml` unter
   `externe_register.google_publisher_center` den Status auf `aktiv` setzen **und**
   `beleg` mit Datum füllen (Gate E7 verlangt den Beleg).

**„Bevorzugte Quelle auf Google" (Preferred Sources)** – ehrlich eingeordnet: Das ist **kein
Publisher-Schalter**, sondern eine Einstellung der *Leser* in der Google-Suche (Top Stories:
„Quelle bevorzugen"). Finanztip „nutzt" sie, indem es Leser aktiv darum bittet. Unser
Gegenstück ist redaktionell, nicht technisch: ein kurzer Hinweis an geeigneter Stelle
(z. B. Newsletter oder Artikelende: „Du kannst FranksFinanzcheck auf Google als bevorzugte
Quelle markieren"), sobald die Funktion für die eigenen Leser sichtbar ist. Kein Bauteil im
Repo kann sie erzwingen – wer das verspricht, verkauft Nebel.

**Erwartung richtig stellen:** Ein Publisher-Center-Profil erzeugt allein **kein Knowledge Panel**.
Es ist ein Konsistenz-Baustein (News-Oberflächen, saubere Publikationsdaten). Das Panel selbst
entsteht aus Erwähnungen + strukturierten Daten + Zeit.

## 3. Wikipedia-/Wikidata-Grundlage (die ehrliche Leiter)

Für eine junge Domain ist ein Wikipedia-Artikel unrealistisch – als *Eigenartikel* obendrein
unzulässig (Interessenkonflikt, Löschrisiko). Die Grundlage entsteht von unten:

1. **Erwähnungen verdienen** (läuft): `/presse/` mit Boilerplate, Fixkosten-Index als
   zitierfähiger Datensatz (`/studien/fixkosten-index-2026-q4/` + CSV), Kadenz in
   `data/authority_strategy.yaml`. Jede Erwähnung mit URL + Datum in
   `data/authority_evidence.yaml` belegen – ohne Beleg zählt sie hier nicht.
2. **Wikidata-Eintrag**, sobald mindestens zwei unabhängige, belegte Erwähnungen vorliegen.
   Mindestdaten dann: Label `FranksFinanzcheck`, Beschreibung (DE) = `definition_kurz` aus
   `data/entity.yaml`, Instanz: Website, offizielle Website `https://franksfinanzcheck.de/`,
   Betreiber/Gründer: Frank Hartung, Sprache: Deutsch, Land: Deutschland, Social-Handles
   (Mastodon, Pinterest). Danach `externe_register.wikidata` mit Beleg (Q-ID) auf `aktiv`.
3. **Wikipedia** nur, wenn Dritte die Relevanz herstellen (Presseberichte, Fachzitate).
   Niemals selbst schreiben oder schreiben lassen.

## 4. LinkedIn / Xing aktivieren (erst wenn das Profil existiert)

Stand 25.10.2026: kein belegtes Profil (Social-Kanäle stehen auf Standby ohne Zugangsdaten).
Deshalb führt das Schema bewusst **keine** LinkedIn-/Xing-URL – eine erfundene `sameAs`-URL
wäre ein falsches Entity-Signal. Sobald ein Profil steht, sind es vier Schritte:

1. **Profil anlegen/pflegen:** Name exakt `FranksFinanzcheck` (Unternehmensseite) bzw.
   Personenprofil `Frank Hartung` mit Rolle „Autor & Betreiber von FranksFinanzcheck".
   Bio = `definition_kurz` (data/entity.yaml). Website-Feld: `https://franksfinanzcheck.de/`
   (die Rückverlinkung macht `sameAs` erst glaubwürdig). Logo: `icon-512.png` wie in §2.
2. **hugo.toml:** einen Block ergänzen (Icons `linkedin`/`xing` existieren bereits im Theme):
   ```toml
   [[params.socialIcons]]
     name = "linkedin"
     url = "https://www.linkedin.com/company/…"   # echte Profil-URL
     title = "FranksFinanzcheck auf LinkedIn"
   ```
3. **data/entity.yaml:** Eintrag von `profile_geplant` nach `profile_aktiv` heben (mit URL).
4. **`npm run entity:check`:** Ab dann erscheinen das Profil automatisch in Person-,
   Organization- und Article-`sameAs` **und** als `rel=me`-Link im Footer jeder Seite.
   Gate E4 blockt Platzhalter (reine Domain ohne Profilpfad) und Vorab-Einträge.

## 5. Backlinks auf die Startseite (Marken-Anker statt Artikel-Anker)

Artikel-Links bauen Themen-Autorität; die **Marken**-Entität braucht Links auf die
Startseite mit Marken-Ankern. Dafür liegt die Kampagne
`startseite-markenlinks` in `data/backlink_prospects.yaml` (Asset:
`startseite-markenprofil` in `data/backlink_assets.yaml`):

- **Ziel-URL:** ausnahmslos `https://franksfinanzcheck.de/` (oder `/presse/` für Medien)
- **Anker:** `FranksFinanzcheck` · `franksfinanzcheck.de` · `Fixkosten-Cockpit von FranksFinanzcheck`
  – keine Keyword-Anker auf die Startseite, keine Exakt-Anker-Inflation
- **Kopier-Vorlage:** Der Boilerplate-Absatz auf `/presse/` („Kurztext zur Übernahme") –
  Journalisten und Verzeichnisse übernehmen ihn inkl. Link, ohne selbst formulieren zu müssen
- **Kadenz unverändert:** 1 Medienziel/Woche (`data/authority_strategy.yaml`), max. 5
  Outreach-Aktionen/Woche (`data/backlink_prospects.yaml`) – Qualität vor Volumen
- **Unverlinkte Erwähnungen** monatlich prüfen (Markensuche). Höfliche Link-Bitte, Kurzform:
  > „Vielen Dank für die Erwähnung von FranksFinanzcheck. Falls es in Ihren Beitrag passt,
  > freue ich mich über einen Link auf die Startseite franksfinanzcheck.de – so finden Ihre
  > Leser die Methodik hinter der Rechnung. Kein Muss, nur ein Angebot. – Frank Hartung"
- **Belegen:** Jede gewonnene Erwähnung mit URL + Datum in `data/authority_evidence.yaml`.

## 6. Namens-Konsistenz (wer prüft was)

| Fläche | Soll | Prüfung |
|---|---|---|
| Impressum (Betreiberzeile) | nennt „FranksFinanzcheck, franksfinanzcheck.de" | Gate E3 |
| /ueber/ (Definition + Abgrenzung) | wortgleich mit Register | Gate E3/E8 |
| Newsletter-Absendername | enthält exakte Marke – aktuell „Frank von FranksFinanzcheck" (`data/newsletter_studio.json`) | Gate E6 |
| Newsletter-Abmeldung/-Seiten | Marke in Title-Kette + Description | Gate E6 |
| Double-Opt-In-Mail (Worker) | „… von FranksFinanzcheck" | Gate E6 |
| Kontakt (Footer, /ueber/, /presse/) | `kontakt@franksfinanzcheck.de` | Gate E6/E8 (Flächen) |
| Schreibweise überall | `FranksFinanzcheck` – nie mit Leer-/Bindestrich | Gate E6 |
| Manifest/PWA | Name `FranksFinanzcheck` | schema_seo_gate S11 |

**Offene Entscheidung – Absendername:** „Frank von FranksFinanzcheck" (persönlich, mutmaßlich
bessere Wiedererkennung im Postfach) vs. rein „FranksFinanzcheck" (maximale Marken-Reinheit).
Beides enthält die exakte Marke; das Gate akzeptiert beides. Empfehlung: **behalten**, bis
Öffnungs-/Abmeldedaten eine Änderung stützen – ein Absenderwechsel ohne Beleg riskiert
Zustellbarkeit und Wiedererkennung für ein reines Formsignal.

## 7. Wenn das Gate rot wird

| Regel | Typische Ursache | Heilung |
|---|---|---|
| E1 | Register unvollständig | `data/entity.yaml` Pflichtfelder füllen |
| E2 | Wortlaut nur an einer Stelle geändert | Change-Protokoll §1 vollständig durchlaufen |
| E3 | Fläche hinkt hinterher (oft `static/llms.txt`) | Fläche nachziehen; llms: Generator laufen lassen |
| E4 | Profil erfunden/vorab eingetragen oder Liste driftet | §4-Reihenfolge: erst Profil, dann Register + hugo.toml |
| E5 | Template umgeht die zentrale Liste | `$entityProfiles`/`$profiles` nutzen, kein Literal |
| E6 | Falschschreibung oder Absender ohne Marke | Schreibweise korrigieren; Absender in `data/newsletter_studio.json` |
| E7 | Logo/RSS/Asset entfernt oder Status ohne Beleg | Voraussetzung wiederherstellen; Beleg eintragen |
| E8 | Build rendert alte/falsche Werte | Quelle (hugo.toml) prüfen, neu bauen |
| E9 | `og:site_name` fehlt irgendwo (hart) | Head-Kette prüfen – Titel-Quote ist nur Messung (weich) |

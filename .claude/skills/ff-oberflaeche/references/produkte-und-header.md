# Werkzeuge als Produkt und die Kopfzeilen-Wahrheit

> Wörtlich aus `CLAUDE.md` übernommen am 01.11.2026 (Skill-Umbau). Kein Satz wurde umformuliert, gekürzt oder erfunden; die Überschriften sind eine Ebene tiefer gehängt. Änderungen hier sind Änderungen am Regelwerk – sie brauchen denselben Nachweis wie vorher: Selbsttest der betroffenen Wache, dann Commit.

### Werkzeuge sind ein Produkt, kein Shortcode (Wache seit 02.10.2026)

Die neun Rechner unter `/werkzeuge/` sind der **zweite Produktkern** neben dem
Fixkosten-Cockpit. Ihr Wert hängt an Eigenschaften, die man einer Seite nicht
ansieht: vollständige Nutzbarkeit **ohne Affiliate-Klick**, Rechnen ohne
Datenabfluss, offengelegte Formeln und Quellen, Export als CSV/PDF/ICS.

**Eine Quelle:** `data/werkzeuge.yaml` → `werkzeuge_data.html` →
`ff_werkzeug.html` (Markup), `static/premium/ff-werkzeuge.js` (Rechenkern),
`layouts/werkzeuge/{single,list}.html`. Felder, Formeln, Annahmen und Quellen
nie ein zweites Mal pflegen.

**Harte Zusage im Text und im Gate:** „Du kannst das Tool vollständig nutzen,
ohne einen Affiliate-Link anzuklicken." – `python3 scripts/werkzeuge_gate.py`
prüft W1–W7 (Versprechen, Vollständigkeit, Werbefreiheit, Verdrahtung,
Nachvollziehbarkeit, Lokalität, offene Methodik), **ohne `--fix`** und zweimal
im Deploy: Quellvertrag vor dem Build, Produkt-Gate gegen `public/`. Skript und
Markup sprechen ausschließlich über `data-`-Hooks, nie über Klassen. Runbuch:
`docs/ANLEITUNG-WERKZEUGE.md`, Rollout-Report: `WERKZEUGE-PREMIUM-2026-10-02.md`.

### Kopfzeilen stehen an einer Stelle, auch für den Umzug (seit 27.10.2026)

`static/_headers` enthielt bis zum 27.10.2026 **nur Cache-Regeln** und galt
trotzdem als Migrationsweg. Wer damit auf Cloudflare Pages umgezogen wäre,
hätte HSTS, `nosniff`, Clickjacking-Schutz und CSP nicht mitgenommen – die
Datei ist wirkungslos auf GitHub Pages, aber sie ist die einzige Stelle, an
der ein anderer Hoster die Header findet.

- Die acht Kopfzeilen der Tabelle A1 (`cloudflare/edge-schutz.md`) stehen
  jetzt auch in `static/_headers`; der Sollstand wird **aus der Tabelle
  gelesen**, nicht abgetippt.
- `blog_header_gate --offline` prüft S1 (jeder Wert exakt wie in der Vorlage)
  und S2 (**kein Pfad erbt zwei verschiedene Werte** derselben Kopfzeile).
  S2 ist kein Formalismus: Cloudflare Pages führt alle passenden Regeln
  zusammen und verbindet gleiche Namen mit Komma – zwei `Cache-Control`-Werte
  ergäben `max-age=31536000, immutable, max-age=600`, also einen
  widersprüchlichen Cache-Header. Deshalb gibt es dort kein Catch-all
  `Cache-Control`.
- Live messen bleibt `npm run header:check:live` (Sicherheits-Wache); die
  Datei ist keine Messung, sondern der zweite Auslieferungsweg.

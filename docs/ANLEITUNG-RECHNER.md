# ANLEITUNG – Interaktive Ratgeber-Rechner (H6)

> **Seit:** 28.09.2026 · **Ursprung:** Quick Win H6 aus der
> Konkurrenz-Analyse Finanztip (`KONKURRENZ-ANALYSE-FINANZTIP-KI-TOOLS-2026-09-28.md`)
> **Teile:** `layouts/shortcodes/rechner.html` (Renderer + Optik) ·
> `static/premium/ff-rechner.js` (Rechenlogik) · Einbettungen in 3 Artikeln

---

## Warum genau diese drei Rechner?

Finanztip hat ein ganzes `/rechner/`-Verzeichnis. Frank braucht keinen
Rechner-Silo – sondern Werkzeuge **genau dort, wo Leser sie brauchen**,
in seinen Kern-Nischen (Anti-Blindspots: eigene Stärken ausbauen, nicht
Finanztips Breite kopieren):

| Rechner | Eingebettet in | Antwortet auf |
|---|---|---|
| `notgroschen` | Post „Finanzieller Puffer" | „Wie viel Notgroschen ist genug?" |
| `strom-abschlag` | Ratgeber Strom & Gas sparen | „Ist mein Abschlag fair?" |
| `dsl-effektiv` | Post „DSL-Wechselbonus sichern" | „Was kostet der Tarif WIRKLICH?" |

## Einbetten (Autoren-View)

```markdown
{{</* rechner typ="notgroschen"
    quelle="Verbraucherzentrale / Destatis (siehe Quellen unten)"
    stand="September 2026" */>}}
```

* `typ` (Pflicht): `notgroschen` | `strom-abschlag` | `dsl-effektiv`
* `quelle` / `stand` (optional): landen in der Methodik-Zeile.
  **Regel:** Werte nur aus dem `quellen:`-Frontmatter des Artikels
  belegen – nichts erfinden (Anti-Halluzinations-Statut).
* Ein kurzer Anreißer-Satz im Fließtext davor macht den Rechner zum
  Teil der Antwort (kein „nacktes Widget").
* Der Rechner lädt sein Skript selbst – bei mehreren Rechnern auf
  einer Seite trotzdem nur EINMAL (`.Store`-Wächter im Shortcode).
* Ohne JavaScript bleibt der Rechner unsichtbar (`noscript`-Fallback).

## Vertrag (CLAUDE.md / PRODUCT.md)

* **100 % lokal:** rechnet im Browser, kein Netz, kein Tracking, keine
  Cookies – bewusst KEIN Umami (consent-unabhängig, siehe H4-Doku).
* **Ehrlichkeit vor Buzz:** unter jedem Rechner steht ein Methodik-Block
  „So rechnet dieser Rechner" mit der offenen Formel. Keine versteckten
  Annahmen, keine erfundenen Durchschnitte – der Vorbelegungs-Preis
  37,0 ct/kWh ist der belegte BDEW-Haushaltsdurchschnitt 2026.
* **Keine Frameworks:** Vanilla JS, `defer` geladen, KEIN jQuery (H2).
* **Barrierefrei:** echtes `<form>` + `<label>`, Enter reicht, Ergebnis
  in `aria-live="polite"`, Touch-Ziele ≥ 44 px.
* **Dark Mode:** komplett über globale CSS-Variablen; Hinweis-Texte
  bleiben `var(--primary)` (Kontrast in beiden Themes gesichert).
* **Zielgruppe:** Eingaben verstehen deutsche Notation („1.500" und
  „37,5").

## Rechenlogik prüfen (ohne Browser)

`ff-rechner.js` hängt seinen DOM-freien Rechenkern an
`globalThis.FFRechnerLogik`:

```bash
node -e "
eval(require('fs').readFileSync('static/premium/ff-rechner.js','utf8'));
const r = globalThis.FFRechnerLogik.notgroschen({einkommen:'2.500',erspartes:'4.000',reserve:'3'});
console.log(r.ziel, r.luecke, r.rate12.toFixed(2));
// erwartet: 7500 3500 291.67
"
```

Verifizierte Referenzwerte (28.09.2026):

| Rechner | Eingaben | Erwartung |
|---|---|---|
| notgroschen | 2.500 € netto, 4.000 € erspart, 3× | Ziel 7.500 €, Lücke 3.500 €, Rate 291,67 €/Monat |
| strom-abschlag | 4.000 kWh, 37,0 ct, 12 €, 100 € aktuell | Jahreskosten 1.624 €, fair 135,33 €, Ampel „Nachzahlung" |
| dsl-effektiv | 40 €/Monat, 24 Mon., 150 € Bonus, 40 € Kosten | Gesamt 850 €, Effektiv 35,42 €/Monat |

## Ausbaustufen (bewusst NICHT jetzt)

* **Mehr Rechner** (Tagesgeld-Zinseszins, Ratenkredit-Gesamtkosten):
  neue Logik in `FF_RECHNER`-Block + Formular-Block im Shortcode +
  Methodik-Text. DOM-Budget vorher prüfen (`scripts/dom_audit.py`).
* **Ergebnis teilen/merken:** braucht localStorage/URL-Hash → dann
  Datenschutzhinweis erweitern (derzeit bewusst verzichtet).
* **Eingaben vorbefüllen aus dem Artikel-Beispiel:** schön, aber
  Placeholder (`z. B. 2.500`) leisten dasselbe ohne Magie.

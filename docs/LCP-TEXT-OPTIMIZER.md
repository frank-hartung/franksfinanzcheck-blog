# LCP Text Render Optimizer

Stand: 24.08.2026

## Problem

Lighthouse meldete in der LCP-Aufschlüsselung die Hero-Headline als LCP-Element:

```txt
Weniger Fixkosten, mehr vom Leben: Dein ehrlicher Check für Strom, Gas und Versicherungen
<h1>
Verzögerung beim Rendering des Elements: ca. 300 ms
```

Wenn eine Headline das LCP-Element ist, darf sie nicht erst durch JavaScript sichtbar gemacht oder per Transform bewegt werden.

## Lösung

Die Hero-Headline und der Hero-Absatz bleiben ab First Paint sichtbar und untransformiert.

Geändert wurde:

- Hero-H1 wird nicht mehr mit GSAP versteckt.
- Hero-Absatz wird nicht mehr mit GSAP versteckt.
- Hero-Text wird nicht mehr mit `y`/Transform bewegt.
- Nur CTA-/Trust-Chips erhalten weiterhin eine kleine opacity-only Enhancement-Animation.
- Der Geldbetrag im Hero wird nicht per JS umgeschrieben.
- Die Breite des Euro-Betrags wird per CSS reserviert.

## Neues Tool

```bash
python3 scripts/lcp_text_optimizer.py --fix
```

Das schreibt:

```txt
data/lcp_text_optimizer_manifest.json
```

Prüfung:

```bash
python3 scripts/lcp_text_optimizer.py --check
```

JSON-Report:

```bash
python3 scripts/lcp_text_optimizer.py --check --json
```

## Quality-Gates

Das Tool prüft:

- Hero-H1/Absatz sind nicht im GSAP-Hero-Selector,
- nur CTA-/Trust-Elemente werden als Enhancement animiert,
- kein `y: 24` / `y: 0` im Hero-Pfad,
- kein JS-Rewrite des Geldbetrags,
- CSS erzwingt sichtbaren, untransformierten Hero-Text,
- Geldbetrag reserviert Breite.

## Erwartetes Ergebnis

Die LCP-Renderverzögerung für das Hero-H1 sollte sinken, weil der Browser die Headline direkt beim ersten Paint rendern kann und nicht auf eine JS-Animation warten muss.

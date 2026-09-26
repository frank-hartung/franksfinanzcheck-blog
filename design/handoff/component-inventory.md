# Figma ↔ Hugo Komponenten-Inventar

> Generiert aus `data/design/handoff.yaml` · Stand 2026-09-26.

| ID | Figma-Komponente | Hugo/CSS-Vertrag | Pflichtzustände | A11y-Abnahme |
|---|---|---|---|---|
| `button-primary` | `Action/Button/Primary` | `.ff-btn-primary` | `default`, `hover`, `focus-visible`, `disabled`, `dark` | 44 px Soll-Trefferfläche; sichtbarer 3-px-Fokusring |
| `button-secondary` | `Action/Button/Secondary` | `.ff-btn-secondary` | `default`, `hover`, `focus-visible`, `disabled`, `dark` | 44 px Soll-Trefferfläche; kein Gelb als Text auf heller Fläche |
| `article-card` | `Content/Article card` | `.post-entry` | `default`, `hover`, `focus-within`, `dark` | Überschrift bleibt semantisch; Bild immer mit Alt-Text und Maßen |
| `trust-pill` | `Trust/Proof pill` | `.ff-trust-pill` | `default`, `dark` | Aussage nicht nur über Farbe vermitteln |
| `callout` | `Content/Callout` | `.ff-callout` | `tip`, `warning`, `info`, `dark` | Typ und Überschrift als Text; Kontrast mindestens 4,5:1 |
| `newsletter-form` | `Conversion/Newsletter form` | `.ff-newsletter-form` | `default`, `focus`, `error`, `success`, `disabled`, `dark` | Persistente Labels; verständliche Fehlertexte; Tastaturbedienung |
| `header` | `Navigation/Header` | `.header` | `desktop`, `mobile`, `keyboard`, `dark` | Skip-Link, Landmark und sichtbarer aktueller Navigationspunkt |
| `author-trust-box` | `Trust/Author box` | `.ff-trust-box` | `default`, `dark` | Autor und Prüfhinweis als echter Text |

## Benennungs- und Übergaberegel

Figma verwendet `Bereich/Komponente/Variante`; der Code-Vertrag bleibt die angegebene CSS-Klasse. Ein visueller Entwurf darf den semantischen HTML-Vertrag nicht ersetzen. Neue Komponenten brauchen vor dem Export einen Inventar-Eintrag mit Fokus-, Dark-Mode- und Fehlerzustand, sofern sie interaktiv sind.

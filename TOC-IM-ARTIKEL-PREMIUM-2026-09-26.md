# „Im Artikel“ – schwebende Artikel-Navigation auf Premium-Level (26.09.2026)

**Auslöser:** Frank, zum Artikel
`/posts/2026-09-21-tierkrankenversicherung-hund-katze-kosten/` –
*„IM ARTIKEL (rechts, Inhaltsverzeichnis) ist nicht optimal dargestellt“*
(aufgefallen auf Desktop **und** Mobil).

---

## Befund (reproduziert, nicht vermutet)

Der Artikel hat **23 H2-Abschnitte**. Die schwebende Navigation rechts
(`.ff-mini-toc`, erzeugt in `static/premium/ff-premium.js`) zeigte davon

| # | Problem | Wirkung für den Leser |
|---|---|---|
| 1 | `headings.slice(0, 9)` – harter Deckel bei **9 Einträgen** | Die Liste brach mitten im Text ab. **„Fazit“ und „Häufige Fragen“ tauchten nie auf** – genau die beiden Sprungziele, die ein Ratgeber-Leser sucht. Kein Hinweis, dass etwas fehlt. |
| 2 | Lesemarke per `IntersectionObserver` mit `rootMargin: -18%/-72%` | Bei langen Abschnitten lag kein Anker in der schmalen Beobachtungszone – dann blieb **gar kein Eintrag markiert**. |
| 3 | Kein Nachführen der Liste | Selbst ein markierter Eintrag konnte im abgeschnittenen Scrollbereich unsichtbar sein. |
| 4 | `right: max(20px, (100vw − 1120px)/2 − 220px)` | Die Zahl 1120 passt nicht zur echten Textspalte (`--main-width` 720 + 2 × `--gap` 24 = **768 px**). Zwischen ~1241 px und 1600 px rutschte das Kästchen dicht an den Text; ab 1600 px trieb es ohne Bezug weit nach rechts. |
| 5 | 190 px Breite, keine Zeilenbegrenzung | Lange deutsche Überschriften liefen dreizeilig – ein unruhiger Block statt einer Liste. |
| 6 | Titel nur als `strong`, keine Positionsangabe | Keine Orientierung „wo bin ich im Artikel“. |

Mobil/Tablet (< 1240 px) war und ist die schwebende Navigation bewusst
ausgeblendet – dort führt das aufklappbare `Inhaltsverzeichnis` oben im
Artikel. Das bleibt so (kein Platz neben der Textspalte), die Grenze liegt
jetzt sauber bei 1280 px, wo die Spalte rechnerisch erst hinpasst.

## Reparatur

**`static/premium/ff-premium.js` → `createMiniToc()` / `setupMiniTocSpy()`**

1. **Vollständig:** alle H2-Abschnitte, kein stilles Abschneiden mehr.
2. **Feste Kopfzeile** („Im Artikel“ + `7 / 23` + feiner Fortschrittsbalken),
   darunter ein **eigener Scroll-Container** nur für die Einträge.
3. **Ehrliche Lesemarke:** scrollbasiert – die letzte Überschrift oberhalb der
   Lesezone (28 % Viewport-Höhe, max. 180 px) gewinnt; am Seitenende immer der
   letzte Abschnitt. Ein Eintrag ist damit **immer** markiert.
4. **Selbstnachführung:** der aktive Eintrag wird innerhalb der Liste sichtbar
   gehalten (eigener `scrollTop`, **nie** `scrollIntoView` – die Seite bewegt
   sich dadurch nicht). `prefers-reduced-motion` wird respektiert.
5. **Ruhige Zeilen:** sichtbares Kurz-Etikett (Schnitt am Doppelpunkt, sonst an
   der Wortgrenze mit `…`), **voller** Überschriftentext in `aria-label` und
   `title`. Der Label-Vertrag der „§“-Wache bleibt damit erfüllt.
6. Gelesene Abschnitte treten dezent zurück (`.ff-mini-toc--past`).
7. Neu vermessen bei `resize`, `load` und nach `document.fonts.ready`.

**`assets/css/extended/z-premium-blog.css` → Block „Im Artikel“**

- Position an der **echten** Textspalte verankert:
  `right: max(16px, calc((100vw − var(--main-width) − var(--gap) * 2) / 2 − 216px − 24px))`
  → konstant 24 px Abstand rechts neben dem Text, auf 1280 px genauso wie auf 4K.
- 216 px Breite, `max-height: min(66vh, 100vh − 168px)`, Flex-Spalte
  (Kopf fix, Liste scrollt, `overscroll-behavior: contain`).
- Weiche Mask-Kanten bei langen Listen (`.ff-mini-toc--long`) – man *sieht*,
  dass es weitergeht; schlanke, getönte Scrollleiste.
- Zwei-Zeilen-Begrenzung je Eintrag (`line-clamp: 2`), aktiver Eintrag fett mit
  Akzentkante, Fortschrittsbalken über `--ff-toc-progress`.
- Breakpoint 1240 → **1279 px**; `@media print` blendet die Navigation aus.

**`scripts/ff_heading_glyph_guard_test.mjs`** – der Vertrag „Mini-TOC ≡
sichtbarer Überschriftentext“ prüft jetzt **alle** H2 statt der ersten 9.

## Verifikation

| Prüfung | Ergebnis |
|---|---|
| `node scripts/ff_heading_glyph_guard_test.mjs` | 40/40 grün |
| `node scripts/ff_voice_functional_test.mjs` | 252/252 grün |
| `python3 scripts/layout_audit.py` | keine neuen Befunde (nur die bekannten hreflang-/DOM-Frühwarnungen) |
| jsdom-Gegenprobe am echten Artikel | 23 Einträge = 23 H2, „Fazit“ + „Häufige Fragen“ enthalten, Kurz-Etiketten sauber, `title` trägt den vollen Text |
| `hugo v0.164.0` Build + lokale Vorschau | fehlerfrei |

Die Reparatur gilt **automatisch für jeden Artikel** des Blogs, nicht nur für
den Tierkrankenversicherungs-Ratgeber.

## Offene redaktionelle Empfehlung (nicht umgesetzt)

Der Artikel trägt vier fast deckungsgleiche Schluss-Abschnitte
(„Welche Rechnung du einmal nüchtern durchspielen solltest“, „Welche Reserve du
nicht doppelt verplanen solltest“, „Welche Monatsfrage dir zwischen Tarif und
Rücklage hilft“, „Welche zweite Rücklagenfrage viele Halter vergessen“).
Sie sagen dreimal dasselbe und blähen jedes Verzeichnis auf. Eine
Zusammenführung zu **einem** Abschnitt („Die drei Gegenproben vor dem
Abschluss“) wäre der nächste Premium-Schritt – das ist eine redaktionelle
Entscheidung und wartet auf Franks Freigabe.

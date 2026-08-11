# 🔤 Font-Entscheidung „Geld-G" – Vorschlag zur dauerhaften Lösung

**Stand:** 11.08.2026 (spät) · **Anlass:** Das G in „Geld" sieht ungewöhnlich aus (Überschrift + Cover)

## Was heute passiert ist
1. Deine heutigen zwei Font-Änderungen wurden **sauber zurückgenommen** (saubere `git revert`s,
   kein Hand-Gefrickel). Der Blog zeigt wieder den Stand von heute Nachmittag.
2. Diese Seite bleibt damit exakt in dem Zustand, den du zuletzt gut fandest.

## Das „G-Problem" – ehrlich benannt
- Montesserrats großes G ist **geometrisch mit flacher Spur**. Wer es einmal spitzfindig wahrnimmt,
  bergauf nie wieder vergessen. 😄 Das ist keine Übertreibung – das Auge mit Feingefühl
  spürt das und hat Recht damit.
- Fehler der Infrastruktur (Thin-122-Klon) war real existent – und ist **separat entdeckt,
  zurückgebaut, und kommt separat wieder**, wenn deine Font-Wahl gefallen ist.

## Die Palette (siehe `font-palette.png` im Repo – und hier oben im Chat)

| # | Font | Das „G" | Kommentar |
|---|---|---|---|
| 🥇 | **Inter Bold** | Humanistisch, ruhig, neutral, absolut „gewöhnlich im besten Sinn" | **Empfehlung**: ist ohnehin der Body-Font der Seite – eine Familie insgesamt, schneller Ladevorgang, null Bruch |
| 🥈 | Open Sans Bold | rund, freundlich, vertraut | Sehr populär in Finanz-/Ragteber-Medien (Trade Republic, N26 vibes) |
| 🥉 | Roboto Bold | sachlich, mechanisch | Neutral, aber generischer |
| 4. | Playfair Display SemiBold | serif-elegant, mit Abstrich | war der Look alter CI-Cover; sticht in grossen Headline-Groessen starker heraus |
| 5. | Montserrat Bold | **geometrisch, flache Spur** | Markenplan-Font – aber genu das „komische G", das dich stoert |

## Mein konkreter Vorschlag
**Inter Bold ueberall** (Ueberschriften + Cover). Vorteile:
- Eine Schriftfamilie -> 1 Download, einheitliche Optik, keine FOUT-Risse
- Inter wurde fuer Bildschirmlesen gebaut; besseres Lesbakeit-Niveau in Fliesstext UND Überschriften
- G ist das unauffaelligste der Runde – das war dein Kriterium

## Und die Automatik danach (Sabotage-Schutz bleibt!)
Sobald du waehlst (1-5):
1. Ich backe die gewaehlte Familie als einzige woff2-Quelle aus den gelockten Variable-Fonts
2. Reaktiviere `font_guard.py` + `bake_fonts.py` – Vertrag auf deine Wahl aktualisiert
   (Ueberschriften & Cover gleichen Kenner: name+weightClass aus dem Font-Koerper bewiesen)
3. Die 2 Titelbilder heute neu gerendert mit der Wahl-Font
4. Doku-Journal-Eintrag in QUALITAETS-REGELWERK

**Antworte einfach mit der Nummer (1-5) oder dem Namen – und es wird umgesetzt.** 🖋️

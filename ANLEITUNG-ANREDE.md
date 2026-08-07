# 🗣️ Anrede-Konfiguration (du/Sie) für Artikel

Der Blog spricht seine Leser standardmäßig mit **„du"** an – das ist der
Blog-Stil (siehe Strategie unten). Für einzelne Artikel, die sich bewusst an
eine Zielgruppe richten, die gesiezt wird (z. B. Senioren, Vorsorge-Themen),
gibt es ein **optionales Frontmatter-Flag**:

## Flag setzen

Im Frontmatter eines Artikels:

```yaml
---
title: "Private Altersvorsorge: So sichern Sie sich ab"
description: "Erfahren Sie, wie Sie Ihre Altersvorsorge optimal gestalten …"
date: 2026-08-07
anrede: "Sie"          # ← bewusste Sie-Form für diesen Artikel
---
```

Werte: `anrede: "Sie"` (oder `"sie"`, `"sie-form"`, `"höflich"`) aktiviert
die Sie-Form für den Artikel. **Kein Flag = du-Form** (Standard).

## Was das Flag steuert (vollautomatisch)

| Automatik | Verhalten mit Flag |
|---|---|
| **Rechtschreib-Prüfung** (`spellcheck.py`) | Überspringt die du-Konvertierung von Descriptions („Entdecken Sie…" bleibt) |
| **KI-Description-Generator** (`meta_optimizer.py --ai`) | Prompt: „Sprich den Leser mit der Höflichkeitsform 'Sie' an" |
| **Polish-Pass** (`profi_polish.py`) | Prompt: Sie-Form konsistent verwenden |
| **Content-Bot** (`generate_drafts.py`) | Per Env-Variable `BLOG_ANREDE=sie` lassen sich ALLE neuen Bot-Artikel auf Sie-Form umstellen (Standard: du) |
| Hugo-Build | `anrede` ist ein harmloses Frontmatter-Feld – kein Einfluss |

## Wichtig: Konsistenz innerhalb des Artikels

- Die Sie-Form muss **durchgehend** verwendet werden (kein Wechsel zu „du")
- Die automatischen Checks erkennen Sie-Artikel am Flag und greifen nicht
  ein – die Konsistenz liegt dann beim Autor/Bot-Prompt
- Titel, Description und Fließtext sollten dieselbe Anrede nutzen

## Strategische Empfehlung (Stand: August 2026)

**Standard bleibt „du"** – passend zu Zielgruppe (Pinterest, Frugalismus,
20–45-Jährige), Affiliate-Conversion (direkte Ansprache performt besser)
und Personenmarke („Frank"). Die Sie-Form ist die **Ausnahme** für gezielte
Zielgruppen-Artikel (z. B. Rentenvorsorge für 55+).

## Test-Checkliste

- [ ] Flag gesetzt: `anrede: "Sie"` im Frontmatter
- [ ] Description in Sie-Form → `python3 scripts/spellcheck.py` zeigt **keine** Anrede-Warnung
- [ ] Artikel ohne Flag → Warnung erscheint weiterhin (du-Stil geschützt)
- [ ] Hugo-Build OK

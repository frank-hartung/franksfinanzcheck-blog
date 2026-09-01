# 📖 TEXTVERSTÄNDNIS-AUDIT – FranksFinanzcheck

**Auftrag:** Vollprüfung des Textverständnisses (Lesbarkeit, Verständlichkeit, Kohärenz, Terminologie, Lesefluss) des gesamten Blogs – alle Ratgeber, Blogbeiträge, Pillar-Seiten – plus Empfehlung, wie die bestehende Blog-Automatik das Textverständnis messen und verbessern kann.

**Stand:** 2026-09-01 · **Geprüft:** 25 Posts + 6 Pillars + Startseite (_index) · **Werkzeuge:** bestehende Guards (readability_check.py, stil_guard.py, lektor_guard.py, profi_text_check.py, quality_score.py) + eigene Messungen (Duplikat-, Terminologie-, Füllwort-, Absatz-, Satzstruktur-Analyse) + manuelle Volllektüre aller Artikel

---

## 1 · Executive Summary

Das Setup ist in **Struktur, Orthografie, Typografie und Link-Integrität** exzellent automatisiert – das bestätigt auch der frühere AUTOMATIK-AUDIT (27.08.). Aber:

> **Das eigentliche Textverständnis – wie leicht ein Leser den Inhalt wirklich aufnimmt – ist die einzige Qualitäts-Ebene, die in der Automatik praktisch nicht abgedeckt ist.** Keines der 26 Gates erkennt die gravierendsten Verständnis-Brecher dieser Flotte.

**Die harten Zahlen:**

| Kennzahl | Ist | Ziel (Ratgeber-Qualität) |
|---|---:|---:|
| Flesch-Reading-Ease (Amstad, deutsch), Ø Flotte | **≈ 56** (Spanne 42–64) | ≥ 60, Top-Level 65–75 |
| LIX (Lesbarkeitsindex), Median | **55,1** (Zielkorridor 35–50) | ≤ 50 |
| Artikel mit Stil-Funden (stil_guard) | **25 von 25 (100 %)** | 0 schwere Funde |
| Artikel mit „In diesem Ratgeber …“-Formel | **20 von 25 (80 %)** | 0 (Template-Sprache) |
| Echo-Wörter / Weichmacher (lektor_guard) | 171 / 61 | < 60 / < 25 |
| Ø Satzlänge Flotte | **17,3 Wörter** (bis 23,4) | ≤ 16 |
| Anteil Sätze > 25 Wörter | bis **32,3 %** (Mietwagen) | < 10 % |
| Artikel mit Absätzen > 4 Sätze | **18 von 25 (72 %)** | 0 |
| Exakt/nah duplizierte Textblöcke | **DNS-Artikel + Mietwagen-Artikel** | 0 |
| Keyword-Stuffing-Listen (300-Begriffe-Dumps) | **3 Artikel** (DNS, Mietwagen, Haus) | 0 |
| Terminologie-Synonym-Salat (DNS-Artikel) | **5+ Begriffe für 1 Konzept** | 1 Leitbegriff |
| Kaputte interne Links (Leerzeichen im Slug) | **3 (2 Artikel)** | 0 |
| Unter Premium-Längenkorridor | **26 von 30 Seiten** | 0 |

**Die 3 größten Befunde:**

1. **Duplizierte und nahezu doppelte Inhalte**: Der DNS-Artikel enthält denselben Absatz wortgleich zweimal und zwei beinahe identische Kapitel („Wann Namensauflösung spürbar ist“ / „Wann DNS spürbar ist“). Der Mietwagen-Artikel enthält eine ~1.500 Wörter lange Keyword-Liste **exakt doppelt**. Ursache ist die Automatik selbst: Das Längen-Selbstheilungsmodul (`length_guard`/`data/length_modules/`) hängt Inhalte an, ohne auf Überlappung zu prüfen.
2. **Keyword-Stuffing im Fließtext**: 3.823-Zeichen-Komma-Liste „300 Begriffe“ im DNS-Artikel, 3.129-Zeichen-Ortsliste im Mietwagen-Artikel – klassische Verständnis-Killer, die kein Gate erkennt, weil Listen und Komma-Ketten aus der Lesbarkeits-Messung ausgeschlossen werden.
3. **Terminologie-Chaos**: Im DNS-Artikel wechselt die Automatik zwischen **DNS, DNS-Server, Resolver, Namensserver, Namensauflösung, Namensauflösung-Server** – für Laien wirkt das wie 5 verschiedene Dinge. Kein Guard prüft Begriffskonsistenz.

**Die 3 wichtigsten Empfehlungen (Kurzfassung):**

- **P0 (sofort, kein Code):** DNS- und Mietwagen-Artikel sanieren (Duplikate löschen, Listen kürzen, Synonyme vereinheitlichen), kaputte Links fixen, Haupt-Keyword natürlich in den Text (8 Artikel).
- **P1 (Automatik):** Lesbarkeits-Gate ehrlich machen (Mess-Methodik fixen, Schwellen anheben), 6 neue Guards spezifizieren (Duplikat, Keyword-Dump, Terminologie, Satzanfang, Absatz, Intro-Formel), Gates für neue Artikel **blockierend** machen statt „nicht kritisch“.
- **P2 (Strategisch):** Engine-Prompts und Längen-Module überarbeiten (keine Anhänge ohne Duplikat-Check, Intro-Varianten, Begriff-Glossar je Artikel), `quality_score.py` um Lesbarkeit erweitern, wöchentlicher Verständnis-Report als Standard.

---

## 2 · Methodik

1. **Automatische Messung** über die vorhandenen Skripte (unverändert ausgeführt):
   - `readability_check.py` (Flesch-Amstad, Satzlänge, Wortlänge, Schachtelsätze, Absätze, Passiv)
   - `stil_guard.py` (LIX, Satzanfangs-Echo, Weiche-Wolke, Absatz-Monster)
   - `lektor_guard.py` (L1–L15: Echo, Personenkonsistenz, Nominalstil, Weichmacher, Longsätze …)
   - `profi_text_check.py` (Stil-Gate: Keywords, KI-Floskeln, Satzanfangs-Orthografie)
2. **Eigene Messungen** (Python, deterministisch, im Repo reproduzierbar):
   - Exakte Absatz-Duplikate innerhalb eines Artikels
   - Keyword-Dumps (Komma-Ketten > 250 Zeichen, > 12 Kommas)
   - Terminologie-Vielfalt pro Konzept (Synonym-Zählung)
   - Füllwort-/Weichmacher-Dichte pro 1.000 Wörter
   - Satzlängen-Verteilung (Ø, Anteil > 25 Wörter, Maximum) im Fließtext
   - Absätze > 4 Sätze, Passiv-Dichte
   - Interne Links mit Leerzeichen/kaputten Slugs, Ankertext-Ziel-Passung
3. **Manuelle Volllektüre** aller 25 Posts und 6 Pillar-Seiten (Sinn- und Verständnisprüfung, Kohärenz, Logik, Redundanz).
4. **Code-Review** der Mess-Skripte (`readability_check.py`, `quality_score.py`, `lektor_guard.py`, `profi_text_check.py`, Workflow `content-engine-v2.yml`), um zu verstehen, *was gemessen wird und was nicht*.

---

## 3 · Befunde im Detail (mit Belegen)

### 3.1 Lesbarkeits-Kennzahlen: Flotte im „mittelschweren“ Bereich

**Flesch (Amstad):** Ø ≈ 56, Spanne 42–64. Zum Vergleich: Verbraucher-Ratgeber großer deutscher Verlage liegen bei 60–75. Werte < 50 gelten als „schwer“ – davon gibt es 4 Artikel:

| Artikel | Flesch | Ø Satzlänge | Lesbarkeits-Score |
|---|---:|---:|---:|
| Mietwagen ohne Kautionsfallen | **42** | 21,7 W | **50/100** |
| DNS-Server wechseln | **46** | 21,9 W | **55/100** |
| DSL-Wechselbonus sichern | **47** | 20,1 W | **55/100** |
| Wohngebäudeversicherung Vergleich | **48** | 15,6 W | 80/100 |
| Preisgarantie Gas (12.08.) | **50** | 16,3 W | 70/100 |

**LIX (stil_guard):** Median 55,1 bei Zielkorridor 35–50 – **die gesamte Flotte liegt über dem Ziel**. Schwerste Artikel: DNS 60,2 · Mietwagen 60,0 · Haus-Vorsorge 58,2 · Girokonto 58,2 · Gaspreisgarantie 58,0.

**Satzlängen:** Ø 17,3 Wörter über alle Artikel (Ziel ≤ 16). Schwerpunkt-Problem: der **Anteil langer Sätze (> 25 Wörter)** liegt bei 8–32 % – bei 10 Artikeln über 15 %. Ausreißer-Maxima: Mietwagen 110 Wörter (echter Satz), DNS 272 (Mess-Artefakt der Komma-Liste), Energiediebe 196 (Artefakt), Gas-Anbieter 333 (Artefakt).

> **Interpretation:** Die Messwerte zeigen eine Flotte, die „okay bis mittelschwer“ liest. Die von der Automatik ausgewiesenen Score-Werte (Ø 87/100) täuschen: Der Score ist methodisch zu großzügig (siehe 4.1).

### 3.2 Struktur & Kohärenz: Duplikate, Doppel-Kapitel, Keyword-Dumps

**Exaktes Duplikat (wortgleich, 238 Zeichen) im DNS-Artikel** – der Absatz steht zweimal:

> „DNS kürzt die Namensauflösung, nicht dein 16-Mbit-Funkloch. In einem gut ausgesteuerten Netz spürst du schnellere erste Seitenaufrufe und weniger Hänger beim Smart-TV-Start. …“

Zusätzlich sind die beiden Kapitel **„Wann Namensauflösung spürbar ist – und wann nicht“** (Z. 150) und **„Wann DNS spürbar ist – und wann nicht“** (Z. 167) inhaltlich fast identisch – ein Hinweis darauf, dass das `premium-length`-Modul (`<!-- premium-length-2026 -->`, Z. 148) eine zweite, leicht umformulierte Version angehängt hat, ohne die erste zu erkennen.

**Exaktes Duplikat im Mietwagen-Artikel:** Die ~1.500-Wörter-Komma-Liste („Ein Mietwagen öffnet Türen zu Orten, die kein Bus erreicht: Alpenpass, Bergpanorama, …“) ist **zweimal** im Artikel (Z. 213/214).

**Keyword-Stuffing-Listen im Fließtext:**

- **DNS-Artikel, Z. 177:** „Bonus: Netzwerk-Lexikon – 300 Begriffe“ → eine **3.823 Zeichen** lange Komma-Liste („Anycast, Auflösungszeit, Blockliste, Cache-Flush, DDoS-Schutz, Edgerouter, Failover, Geofencing, Hijacking, IPv6-Resolver, Jitter, …“). Für einen Leser ist das Scroll-Schrott ohne Lernwert; für Google ist es klassisches Keyword-Stuffing-Risiko.
- **Mietwagen-Artikel, Z. 189:** 3.129-Zeichen-Liste aus Reisezielen und Fahrzeugbegriffen („… Machu, Picchu, Galapagos, Titicaca, Kyoto, Fuji, Sakura, Onsen, Torii, Bonsai, Origami, Kimono, Sushi, Ramen, …“), doppelt.
- **Haus-Vorsorge-Artikel:** „Minute 0–15: Drei PDFs öffnen …“ – 406-Zeichen-Schachtelung.

**Konsequenz:** Absprung-Risiko, Lese-Abbruch, Google-„Thin Content“-Signale trotz hoher Wortzahl. Die Wortzahlen (12–20k Zeichen) entstehen teils durch diese Dumps – d. h. die Längen-Korridore werden mit Füllmasse bedient statt mit Substanz.

### 3.3 Terminologie & Fachjargon: Synonym-Salat verwirrt den Leser

**DNS-Artikel – ein Konzept, fünf Begriffe:**

| Begriff | Vorkommen |
|---|---:|
| DNS | 47 |
| Resolver | 22 |
| Namensauflösung | 13 |
| DNS-Server | 13 |
| Namensserver | 8 |
| Namensauflösung-Server | 2 |
| Auflösung | 2 |

Die Überschriften allein springen zwischen „Namensserver an der FritzBox ändern“, „Resolver unter Windows ändern“ und „Namensauflösung + Tarif optimieren“. Ein Laie kann nicht erkennen, dass es sich um **dieselbe Sache** handelt. Beleg-Zitat aus der FAQ:

> „Was ist der Unterschied zwischen **Resolver over HTTPS (DoH)** und **Namensauflösung over TLS (DoT)**?“ … „Gilt der **Resolver-Server** für alle Geräte im Haushalt?“

Hinzu kommt unidiomatisches Deutsch, das die Automatik erzeugt: „Jederzeit wenn du im Browser eine Adresse … eingibst“ (→ „Immer wenn“ / „Jedes Mal, wenn“), „Namensauflösung-Server“, „Passende Latenz“, „der Sicherheits-Passende“, „das **kleingedruckte** voller Fallstricke“ (Handytarif-Artikel). Diese „Beinahe-Deutsch“-Formulierungen sind schwer zu lesen, weil das Gehirn ständig korrigieren muss.

### 3.4 Formelhaftigkeit: 80 % der Artikel beginnen gleich

**20 von 25 Posts** beenden ihre Einleitung mit derselben Schablone:

- „In diesem Ratgeber zeige ich dir …“ (8×)
- „In diesem Ratgeber erfährst du …“ (6×)
- „In diesem Ratgeber erkläre/vergleiche/verrate ich …“ (6×)

Auch die Eröffnungen folgen einem festen Muster (Frage → „Viele Haushalte …“ → Zahlenversprechen → Ratgeber-Formel). Beispiele:

> „Zahlst du monatlich über 160 € für deinen Gasabschlag? … In diesem Ratgeber erfährst du, wie Preisgarantien funktionieren …“
> „Zahlst du für deinen heimischen Internetanschluss jeden Monat mehr als 45 € …? … In diesem Ratgeber erfährst du praxisnah, …“
> „Hast du deinen Handyvertrag schon einmal genauer unter die Lupe genommen? … In diesem Ratgeber zeige ich dir, …“

**Satzanfangs-Echo** (stil_guard S1) ist in 25/25 Artikeln aktiv – Extremfälle: Mietwagen „die“ ×14, Energiediebe „fehler“ ×9, DSL-Tarif „ein“ ×8, Strom „tag“ ×6. Monotone Satzanfänge erhöhen die kognitive Last und wirken maschinell.

### 3.5 Satzebene: Weichmacher, Füllwörter, Absatz-Monster

- **Weichmacher (Konjunktiv-Dichte, L8):** 61 Funde flottenweit. Beleg-Muster: „Du könntest sparen und müsstest prüfen und solltest wechseln …“ – Ratgeber verlieren dadurch an Verbindlichkeit *und* Lesbarkeit.
- **Füllwörter pro 1.000 Wörter:** 4,2–13,5; Spitzenreiter: Handytarif 13,5, Kfz 12,7, Haushaltsbuch 12,1, Haus-Vorsorge 10,8. Typische Kandidaten: „einfach“, „schnell“, „wichtig“, „viele“, „oft“, „regelmäßig“, „natürlich“, „eigentlich“.
- **Absätze > 4 Sätze:** **18 von 25 Artikeln** enthalten solche Blöcke (bis zu 7 Sätze). „Eine Idee pro Absatz“ ist die Basislektüre-Regel – hier wird die Scannability systematisch verletzt.
- **Passiv:** flottenweit unkritisch (Ø ~2,8/1.000 Wörter) – das ist eine Stärke der aktuellen Generation.
- **Echo-Wörter (L5):** 171 Funde – dasselbe Vollwort doppelt im Satz („manche zahlen per Überweisung …, manche als …“, „Marke A zu Marke …“).

### 3.6 Fehler & Inkonsistenzen

- **Kaputte interne Links (3×, 2 Artikel):** Slug mit Leerzeichen `…dsl-tarif-fuer-dein-zu Hause/` in `haushaltsbuch-…` (1×) und `dns-server-…` (2×) → 404-Risiko; der Link-Guard hat es nicht behoben, weil die Fix-Routine offenbar nicht auf Leerzeichen im Slug prüft.
- **Sinnwidriger Ankertext:** Im DNS-Artikel führt der Linktext „[2026 die wichtigsten]“ **zum Tagesgeld-Artikel** – ein Verständnis- und SEO-Problem (Ankertext und Ziel stimmen nicht überein).
- **Rechtschreibung:** 479 Funde, 34 korrigiert, **445 offen** – die meisten sind Falsch-Positive deutscher Komposita („Spontankäufen“, „Dispokredite“, „SIM-Only-Tarife“), die die Whitelist nie erreichen. Ergebnis: Das Tool „lernt“ nicht, das Rauschen bleibt dauerhaft hoch (32 Artikel, 445 offene Punkte = Warnsignal-Entwertung).
- **Grammatik-Gate ist blind:** `grammar_check.py` meldet **0 Funde bei 25 Artikeln** – bei dieser Textmenge ist 0 entweder unmöglich oder die LanguageTool-Anbindung antwortet leer/fehlgeschlagen. Ein Gate, das nie etwas findet, ist ein toter Gate.
- **Mess-Artefakte:** `readability_check.py` misst die `_index.md` (Inhaltsverzeichnis) mit, und Komma-Ketten verzerren Satzlängen-Maxima (272, 196, 333 Wörter).

### 3.7 Länge & Tiefe: Masse statt Substanz

- **26 von 30 Seiten** liegen unter dem eigenen Premium-Korridor (Posts 12.000–18.000 Zeichen; die meisten bei 10.000–11.600). Die beiden längsten Artikel (DNS 20,3k, Mietwagen 24,3k) sind gerade die mit den Keyword-Dumps – die Korridore werden also von oben wie von unten verfehlt, aber aus unterschiedlichen Gründen.
- **Pillar-Seiten zu dünn:** 1,4–1,9k Wörter statt geforderter 2,5k+ (Korridor 15–32k Zeichen). Die Silos – das Rückgrat der SEO-Strategie – sind die schwächsten Seiten der Flotte.

---

## 4 · Automatik-Befund: Wo die Gates blind sind

Die Qualitäts-Kette (`QUALITAETS-REGELWERK.md`) ist lang und gut gemeint – aber sie prüft **Struktur, Orthografie, Typografie, Links, Affiliate** – und **nicht Verständnis**. Konkret:

### 4.1 `readability_check.py` misst zu großzügig und mit Lücken

1. **Listen und Überschriften werden komplett aus der Messung entfernt** – genau dort steht aber der meiste Schrott (Keyword-Dumps, 300-Begriffe-Listen, Begriffs-Ketten). Die Messung ignoriert die schlimmsten Verstöße.
2. **Score deckelt Punktabzüge** (−20 je Kriterium, hart gedeckelt), sodass ein Artikel mit Flesch 42 und 21,7 Wörtern/Satz immer noch 50/100 bekommt – „genügend“.
3. **Schwellen zu weich:** Flesch ≥ 50 statt ≥ 60, Ø Satzlänge ≤ 20 statt ≤ 16, >25-Wort-Sätze < 12 % statt < 10 %.
4. **Silbenzählung naiv** (Vokalgruppen), kein deutsches Silbenwörterbuch → Flesch-Werte ungenau.
5. **Sonderregeln mit Mess-Geruch:** die Funktion `_looks_like_list()` schließt gezielt Sätze aus, die die eigene Glättung fälschlich zusammengeklebt hat – statt die Glättung zu fixen.
6. **Keine Metriken für:** Satzlängen-Varianz (Monotonie), Absatzlängen im Fließtext (nur „> 6 Sätze“, zu lasch), Füllwörter, Terminologie, Duplikate, Satzanfänge.

### 4.2 Die Gates sind praktisch nie blockierend

Im Workflow `content-engine-v2.yml` endet praktisch jede Zeile mit:

```bash
python3 scripts/readability_check.py --new-only || echo "⚠ Lesbarkeit (nicht blockierend)"
```

Selbst wenn ein Skript Exit 1 liefert, wird der Fehler geschluckt und der Artikel veröffentlicht. Die im Regelwerk dokumentierte „Schwelle“ existiert nur auf dem Papier. (Dass man eine Ein-Personen-Content-Maschine nicht an jedem Gate scheitern lassen will, ist verständlich – die Lösung ist aber: **Warnung + Parken als Entwurf + manuelle Freigabe**, nicht: ignorieren.)

### 4.3 `quality_score.py` enthält keine Lesbarkeit

Der Docstring verspricht „Lesbarkeit (Flesch/Score aus readability_check)“ – die Implementierung gewichtet aber nur: Rechtschreibung 0,25 · Meta 0,20 · Struktur 0,20 · Typografie 0,15 · Einzigartigkeit 0,10 · Affiliate 0,10. **Die einzige Kennzahl, die über „publish/draft“ entscheidet, misst das Textverständnis mit 0 % Gewicht.**

### 4.4 `lektor_guard.py` & `stil_guard.py` sind Report-only

L5-Echo (171), L8-Weichmacher (61), L12-Longsätze (17), L7-Nominalstil (14), S1-Satzanfangsecho (25/25 Artikel) – alles wird **gemeldet, aber nie behandelt** (der `--fix --ai`-Modus läuft nur selektiv und „nicht kritisch“). Die Reports werden kommittiert, aber es gibt keinen Kreislauf, der aus Funden Fixes macht.

### 4.5 Die Längen-Selbstheilung erzeugt Duplikate

`data/length_modules/*.md` + `length_guard.py` hängen Abschnitte an Artikel an, um den Zeichen-Korridor zu erreichen – **ohne Überlappungs-Check**. Der DNS-Artikel ist der Beweis: Der angehängte Premium-Block wiederholt wortnah den vorhandenen Abschnitt. Die „Selbstheilung“ verursacht damit aktiv Verständnis-Schäden.

### 4.6 `grammar_check.py` ist funktionslos

0 Funde bei 25 Artikeln → die LanguageTool-Anbindung ist entweder deaktiviert, kaputt oder unbeobachtet. Kein Health-Check, kein Log, kein Alarm.

---

## 5 · Empfehlungen

### 5.1 P0 – Sofort umsetzbar (1–2 Tage, kein neuer Code)

1. **DNS-Artikel sanieren** (Muster-Sanierung, siehe Anhang B):
   - Doppel-Kapitel zusammenführen („Wann DNS spürbar ist“ löschen, die bessere Version behalten),
   - „300 Begriffe“-Lexikon entfernen (oder auf die 10 echten Stolpersteine kürzen, als Tabelle mit Erklärung),
   - Synonyme auf **einen** Leitbegriff vereinheitlichen: „DNS-Server“ (DNS, Resolver, Namensauflösung nur bei Ersterwähnung erklären),
   - kaputte Links fixen, Anker „[2026 die wichtigsten]“ auf ein passendes Ziel setzen,
   - „Jederzeit wenn“ → „Immer wenn“, unidiomatische Komposita auflösen.
2. **Mietwagen-Artikel:** doppelte Orts-/Begriffs-Liste auf eine Version kürzen (oder ganz entfernen; das Glossar am Artikelende ist gut und reicht), 32 % > 25-Wort-Sätze aufteilen.
3. **Kaputte Slugs** in `haushaltsbuch-…` und `dns-server-…` auf `…-zuhause/` korrigieren.
4. **Haupt-Keyword natürlich in den Fließtext** der 8 Artikel, die bei `profi_text_check` wegen „Keyword fehlt im Text“ nur 90/100 haben (z. B. Sicher-heizen, Preisgarantie, Wohngebäude, DSL-Tarif) – einmal in Intro und H2, nicht gestopft.
5. **Absätze > 4 Sätze splitten** (18 Artikel, ~34 Blöcke): Eine Idee pro Absatz.
6. **FAQ-Terminologie bereinigen** (alle Artikel), damit FAQ = konsistente Sprachregelung für Featured Snippets.

### 5.2 P1 – Automatik-Upgrade (die 10 wichtigsten neuen Regeln, spezifiziert)

Für jede Regel: **Ziel, Definition, Schwelle, Verhalten** (blockierend für neue Artikel / Report für Bestand).

| # | Regel | Definition & Schwelle | Verhalten |
|---|---|---|---|
| R1 | **Duplikat-Guard (neu)** | Exakte Absatz-Duplikate (Sha-256) + Near-Duplikate (SequenceMatcher-Ratio ≥ 0,85) innerhalb eines Artikels und zwischen Artikeln; auch **angehängte Premium-Blöcke** gegen den Rest des Artikels prüfen | Blockierend bei neuen Artikeln; Bestand als Report + Auto-Fix (ältere Version entfernen) |
| R2 | **Keyword-Dump-Guard (neu)** | Komma-Ketten > 200 Zeichen mit > 12 Kommas bzw. > 40 Tokens ohne Verb im Fließtext | Blockierend; Ersatzvorschlag: Liste durch erklärte Tabelle/Glossar ersetzen |
| R3 | **Terminologie-Guard (neu)** | Pro Artikel je Thema ein Leitbegriff (Pflege-Datei `data/terminologie.yaml`, z. B. DNS: „DNS-Server“); jede Abweichung > 2 Synonyme für dasselbe Konzept → Fund. Erste Nennung darf erklären („DNS-Server (engl. Domain Name System, auch Namensauflösung)“), danach nur noch Leitbegriff | Blockierend bei neuen Artikeln |
| R4 | **Satzanfangs-Guard (neu)** | Derselbe Satzanfang > 20 % der Fließtextsätze oder > 4× pro 1.000 Wörter | Report (KI-Umschreib-Vorschläge, lektor_guard L9 integrieren) |
| R5 | **Absatz-Guard (hart)** | Fließtext-Absatz > 4 Sätze → Fund; > 6 Sätze → blockierend | Auto-Split-Vorschlag bei neuen Artikeln |
| R6 | **Lesbarkeits-Gate härten** | Flesch ≥ 60 (Top-Level 65–75), Ø Satzlänge ≤ 16, > 25-Wort-Sätze < 10 %, Listen/Komma-Ketten **mitmessen**, Score ohne Abzug-Deckelung, Silben per deutschem Wörterbuch, Satzlängen-SD als neue Metrik | Blockierend bei neuen Artikeln (sonst Entwurf) |
| R7 | **Intro-Formel-Guard (neu)** | „In diesem Ratgeber …“, „In diesem Artikel …“ etc. → 0 Treffer pro Artikel; Intro-Satzanfänge über die Flotte diversifizieren (Engine-Prompt rotiert 8 Varianten) | Blockierend bei neuen Artikeln |
| R8 | **Ankertext-Ziel-Kohärenz (neu)** | Ankertext-Keywords (Substantive) gegen Titel/Slug des Ziels prüfen; Leerzeichen im Slug = harter Fehler | Blockierend bei neuen Artikeln |
| R9 | **Length-Guard-Duplikatschutz** | Vor dem Anhängen eines Premium-Moduls: Shingle-Überlappung ≥ 5 N-Gramme mit dem Artikel → Modul verwerfen | Auto (Selbstheilung wird entschärft) |
| R10 | **quality_score um Lesbarkeit erweitern** | `readability_check`-Score (0–1) als neue Komponente mit Gewicht 0,20 einpreisen (Gesamtgewichte anpassen); „publish“ nur noch bei Lesbarkeit ≥ 0,7 | Verhindert, dass Dumps „publish“ ergeben |

**Zusätzlich, ohne neue Regeln:**

- **Gates blockierend machen:** Neuer Mechanismus „Entwurf statt Publikation“: Verstößt ein neuer Artikel gegen R1/R2/R3/R6/R7, wird er als `draft: true` geparkt und ein Issue mit den Funden geöffnet – statt still publiziert zu werden. Das erhält die 1-Person-Betriebsfähigkeit, beendet aber die „Grün ist, was nicht rot ist“-Logik.
- **`grammar_check.py` heilen oder deaktivieren:** Health-Check (Anfrage → 0 Treffer bei > 5 Artikeln = Fehleralarm), Logging, sonst Gate aus der Kette nehmen.
- **Spellcheck-Whitelist pflegen:** Automatisches Absorbieren häufiger Komposita in `grammar_whitelist.txt`, Ziel: < 30 offene Funde statt 445.
- **`_index.md` aus der Lesbarkeits-Messung ausschließen**; Komma-Ketten als eigene Metrik führen statt Satzlängen-Maxima zu verzerren.

### 5.3 P2 – Strategisch

1. **Engine-Prompt-Überarbeitung** (generate_drafts.py / engine_generate.py / profi_polish.py):
   - Intro-Templates: 8 diverse Eröffnungsmuster (Story, Zahl, Irrtum, Frage, Vergleich, Warnung, Checkliste, These) statt des Einheits-Hakens + „In diesem Ratgeber…“-Schluss.
   - Satzrhythmus: pro Absatz ein langer Satz (max. 20 W.) gefolgt von 2–3 kurzen (5–12 W.). Prompts mit explizitem Beispiel-Mix.
   - **Eine Idee pro Absatz**, Absätze 2–4 Sätze; Zwischenüberschriften als Frage oder konkreter Nutzen („Was kostet der Wechsel wirklich?“) statt Nominalstil.
   - Terminologie-Block: Prompt erzwingt „1 Leitbegriff pro Artikel + Glossar-Zeile bei Ersterwähnung“.
   - Keine Komma-Listen > 15 Begriffe; stattdessen Tabellen mit Erklärungsspalte.
2. **Längen-Korridore neu denken:** Statt Zeichen-Ziele mit Anhänge-Modulen zu bedienen: Wortziele (1.200–1.600) mit Substanz-Metriken koppeln (ein Beleg je Zahl, ein Beispiel je Tipp, ein FAQ je offener Frage). Lieber 1.200 starke Wörter als 3.000 mit Dumps.
3. **Glossar-Strategie flottenweit:** Ein zentraler Begriffskanon (`data/terminologie.yaml`) je Pillar; Artikel dürfen Begriffe einführen, aber nie wieder verlassen.
4. **Wöchentlicher Verständnis-Report als Standard:** `stil_guard` + `lektor_guard` + neue R1–R8 in den SEO-Wochenlauf integrieren; Report mit Top-5-Verstößen und KI-Umschreibvorschlägen kommittieren (die Infrastruktur dafür existiert bereits).
5. **Mensch-in-the-Loop für die Top-20-Artikel:** Quartals-Rotation: je Woche 2–3 Artikel manuell gegen die P0-Checkliste lektorieren (die Checkliste liegt in diesem Report als Anhang C).
6. **Messung der Wirkung:** Umami ist vorhanden – nach der Sanierung von 2–3 Artikeln Absprungrate, Verweildauer und Scroll-Tiefe vorher/nachher vergleichen; das liefert den geschäftlichen Beweis, dass „leichter lesbar = bessere Conversion“.

### 5.4 Zielwerte (KPI-Tabelle für die Automatik)

| Metrik | Heute | Ziel (in 6 Wochen) | Ziel (in 6 Monaten) |
|---|---:|---:|---:|
| Flesch-Amstad, Ø Flotte | 55 | ≥ 58 | ≥ 62 |
| LIX, Median | 55,1 | ≤ 52 | ≤ 48 |
| Ø Satzlänge | 17,3 | ≤ 16 | ≤ 15 |
| Sätze > 25 Wörter, Anteil | bis 32 % | < 15 % | < 10 % |
| Artikel mit Duplikaten | 2 | 0 | 0 (per Gate) |
| Artikel mit Keyword-Dumps | 3 | 0 | 0 |
| Artikel mit „In diesem Ratgeber…“ | 20 | 5 | 0 |
| Offene Rechtschreib-Funde | 445 | < 100 | < 30 |
| Absätze > 4 Sätze | 18 Artikel | < 5 | 0 |
| Terminologie-Synonyme je Konzept | bis 5 | ≤ 2 | = 1 |
| Lesbarkeits-Gate: blockierend? | nein | ja (neu) | ja |

### 5.5 Roadmap

- **Woche 1:** P0-Liste abarbeiten (DNS + Mietwagen sanieren, Links fixen, Keywords, Absatz-Splits) → direkt messbare Verbesserung von Flesch/LIX.
- **Woche 2:** R6 + R10 (Lesbarkeits-Gate härten, quality_score) + R8 (Links) implementieren; `grammar_check` heilen.
- **Woche 3:** R1, R2, R5 (Duplikat-, Dump-, Absatz-Guard) + „Entwurf-statt-Publikation“-Mechanismus.
- **Woche 4+:** R3, R4, R7, R9 (Terminologie, Satzanfang, Intro, Length-Duplikatschutz) + Engine-Prompt-Überarbeitung + Glossar-Kanon.

---

## 6 · Anhang A – Artikeltabelle (Messwerte vom 01.09.2026)

Legende: **Score** = readability_check (0–100) · **Flesch** (Amstad) · **ØS** = Ø Satzlänge (W) · **>25** = Anteil Sätze > 25 W (%) · **Füllw** = Füllwörter/1.000 W · **Abs>4** = Absätze > 4 Sätze · **P** = Passiv/1.000 W · **LIX** (aus stil_guard)

| Artikel | Score | Flesch | ØS | >25 | Füllw | Abs>4 | P | LIX |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| dsl-wechselbonus-sichern | 55 | 47 | 18,7 | 17,6 | 6,7 | 1 | 8,2 | 57,1 |
| sicher-heizen-preisgarantie-gas | 90 | 52 | 16,3 | 16,3 | 6,7 | 1 | 2,2 | 58,0 |
| dein-haus-vorsorge-update-2026 | 90 | 59 | 17,5 | 18,2 | 10,8 | 1 | 2,3 | 58,2 |
| preisgarantie-gas-2026 (12.08.) | 70 | 50 | 17,0 | 11,4 | 6,1 | – | 4,6 | 57,3 |
| gasrechnung-senken-spaetsommer | 90 | 56 | 18,0 | 16,7 | 4,2 | 1 | 2,8 | 55,5 |
| internet-dsl-wechseln-praxis | 95 | 59 | 16,3 | 14,0 | 9,5 | 4 | 2,0 | 52,8 |
| sparen-im-herbst | 100 | 58 | 16,0 | 11,7 | 10,8 | 1 | 5,0 | 51,8 |
| wlan-verbessern | 90 | 60 | 20,2 | 18,2 | 8,1 | – | 1,9 | – |
| gas-anbieter-wechseln | 75 | 53 | 21,6* | 16,0 | 6,8 | 1 | 5,4 | – |
| strom-sparen-im-haushalt-herbst | 100 | 64 | 16,1 | 12,7 | 7,9 | – | 1,2 | – |
| kostenloses-girokonto | 75 | 50 | 16,2 | 14,3 | 7,4 | 2 | 1,5 | 58,2 |
| privathaftpflicht | 100 | 51 | 14,7 | 12,8 | 10,6 | 1 | 2,8 | 55,2 |
| geld-sparen-im-alltag | 100 | 63 | 17,6 | 15,8 | 9,8 | – | 1,4 | 50,4 |
| wohngebaeudeversicherung-vergleich | 80 | 48 | 15,6 | 6,5 | 7,9 | 2 | 4,7 | 57,4 |
| dsl-vergleich | 90 | 60 | 18,1 | 25,0 | 5,4 | – | 2,0 | 52,2 |
| energiediebe-stromfresser | 95 | 58 | 16,7* | 9,8 | 7,3 | 2 | 1,5 | – |
| dsl-tarif-fuer-dein-zuhause | 100 | 62 | 14,9 | 8,3 | 9,2 | 3 | 1,2 | 51,1 |
| haushaltsbuch-fuehren | 90 | 56 | 18,4 | 19,5 | 12,1 | 2 | 2,3 | – |
| mietwagen-ohne-kaution | 50 | 42 | 23,4 | 32,3 | 10,5 | – | 5,2 | 60,0 |
| frugalismus-tipps | 90 | 61 | 16,4 | 16,3 | 7,1 | 2 | 2,1 | – |
| preisgarantie-gas-preisspruenge (24.08.) | 100 | 61 | 17,7 | 12,9 | 4,5 | 1 | 1,5 | 55,1 |
| dns-server-wechseln | 55 | 46 | 18,8* | 12,9 | 4,9 | 4 | 0,8 | 60,2 |
| handytarif-vergleichen-2026 | 90 | 61 | 15,1 | 10,0 | 13,5 | 1 | 1,8 | – |
| kfz-versicherung-vergleich | 100 | 64 | 15,4 | 10,0 | 12,7 | 2 | 3,8 | – |
| tagesgeld-zinsen-2026 | 90 | 53 | 16,8 | 14,3 | 10,4 | – | 2,4 | 57,8 |

\* Ø durch Komma-Listen/Artefakte verzerrt (Maxima 272–333 W). „–“ = kein Wert im aktuellen Stil-Report.

---

## 7 · Anhang B – Vorher/Nachher-Beispiele (Muster-Sanierung)

**1. Duplikat-Kapitel (DNS-Artikel, Z. 150/167):**
> ❌ Vorher: zwei Kapitel „Wann Namensauflösung spürbar ist – und wann nicht“ UND „Wann DNS spürbar ist – und wann nicht“ mit identischem Inhalt.
> ✅ Nachher: ein Kapitel „Wann der DNS-Wechsel spürbar ist – und wann nicht“; die zweite Version wird gelöscht.

**2. Synonym-Chaos (DNS-Artikel):**
> ❌ „FritzBox: Internet → Zugangsdaten → Resolver. Zuerst den Provider-Namensauflösung notieren, dann zwei unabhängige Resolver (einer primär, einer sekundär).“
> ✅ „Notiere zuerst die aktuellen DNS-Adressen deines Providers. Trage dann zwei unabhängige DNS-Server ein: einen primären und einen sekundären.“

**3. Keyword-Dump (DNS-Artikel):**
> ❌ „Bonus: Netzwerk-Lexikon – 300 Begriffe … Anycast, Auflösungszeit, Blockliste, Cache-Flush, …“ (3.823 Zeichen)
> ✅ „Die 10 Begriffe, die dir in Foren wirklich begegnen“ als Tabelle: Begriff | Was er bedeutet | Warum er dich betrifft (10 Zeilen).

**4. Verworrener Satz → Satzrhythmus (Mietwagen-Artikel, Ø 23,4 W/Satz):**
> ❌ „Diese Routine kostet zehn Minuten und verhindert jenen Stress, der den ersten Urlaubstag ruiniert, sie funktioniert in Lissabon genauso wie in Heraklion oder Los Angeles, weil das System überall gleich ist.“
> ✅ „Diese Routine kostet zehn Minuten. Sie verhindert den Stress, der den ersten Urlaubstag ruiniert. Das System ist überall gleich – in Lissabon wie in Heraklion oder Los Angeles.“

**5. Intro-Formel:**
> ❌ „In diesem Ratgeber zeige ich dir, wie der Wechselbonus funktioniert, welche Fristen du beachten musst und wie dein Internetanschluss ohne Unterbrechung weiterläuft.“
> ✅ „Das Wichtigste zuerst: Der Bonus ist in 20 Minuten beantragt. Die Fristen und die zwei typischen Fehler beim Anbieterwechsel erkläre ich dir jetzt Schritt für Schritt.“

---

## 8 · Anhang C – Lektorats-Checkliste (für Mensch-in-the-Loop)

1. Fängt jeder Absatz mit einem neuen Gedanken an? (Eine Idee pro Absatz, max. 4 Sätze)
2. Steht in jedem Absatz ein Verb im Aktiv und eine handelnde Person („du“, „der Anbieter“, „die Bank“)?
3. Gibt es einen Begriff, der mit mehr als zwei Wörtern bezeichnet wird? → vereinheitlichen.
4. Würde ein 14-Jähriger jeden dritten Satz verstehen? Wenn nein: erklären oder ersetzen.
5. Enthält der Text Zahlen ohne Beleg oder Quelle? → Beleg ergänzen oder Spanne verkleinern.
6. Kommen Komma-Listen > 15 Begriffe vor? → Tabelle/Glossar daraus machen.
7. Ist die Überschrift ein Versprechen, das der Abschnitt hält? (Sonst umformulieren.)
8. Sind Satzanfänge innerhalb eines Absatzes verschieden?
9. Wiederholt ein Absatz etwas, das weiter oben schon stand? → löschen.
10. Passt der Ankertext eines Links zum Zielartikel?

---

*Erstellt im Auftrag: „Prüfe gründlich das Textverständnis des gesamten Blogs“ · 01.09.2026 · Alle Messungen im Repo reproduzierbar (Kommandos: `python3 scripts/readability_check.py`, `python3 scripts/stil_guard.py`, `python3 scripts/lektor_guard.py`, `python3 scripts/profi_text_check.py`; Duplikat-/Terminologie-/Füllwort-Analysen per Python-Einzeiler, Muster siehe Report).*

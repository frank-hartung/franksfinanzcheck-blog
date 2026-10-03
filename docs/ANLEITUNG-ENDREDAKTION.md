# ✅ Endredaktion – Prüfen · Optimieren · Vollautomatisch freigeben

**Stand:** 03.10.2026 · **Zweck:** Das hochwertige, kostenlose KI-Qualitätstool
des Blogs: prüft **alle wartenden Entwürfe** (Content-Engine, KI-Redaktion,
Poppy-Werkbank) gegen die etablierten Wachen, optimiert sie und gibt grüne
Entwürfe **vollautomatisch** in die Veröffentlichungs-Queue frei – plus
Mastodon-Posting für freigegebene Poppy-Artikel. Kosten: **0 €** (nur die
Gratis-Keys Groq/Gemini, wie immer).

---

## 1. Die Idee in fünf Sätzen

Kommerzielle Lektorats-Tools (Grammarly, Jasper, Writer) verkaufen „prüfen,
optimieren, veröffentlichen“ als Abo. Dieses Repo besitzt jede Einzelprüfung
schon als Wache (Lesbarkeit, Grammatik, Titel, Länge, Floskeln, Taxonomie,
Offenlegung) – nur liefen sie verstreut, und am Ende wartete trotzdem immer
ein Mensch auf dem Freigabe-Knopf. Die Endredaktion bündelt die Wachen zu
EINEM Urteil je Entwurf, lässt die Gratis-KI gezielt die gefundenen Mängel
polieren (mit hartem Sicherheitsvertrag) und reiht grüne Entwürfe über den
bestehenden Park-Mechanismus ein. Sie ist damit **Einreicher, nie
Veröffentlicher**: cadence_guard bleibt der einzige Weg ins Live-Blog.

## 2. Die drei Schritte

| Schritt | Was passiert | Werkzeuge (SSOT, wiederverwendet) |
|---|---|---|
| **1. Prüfen** | 12 Gates je Entwurf → Urteil 🔴 blockiert / 🟡 optimieren / ✅ grün / 🔵 Hinweis | `length_policy`, `check_titles`, `readability_check`, `grammar_check`, `PROFI_FLOSKELN`, URL-Hygiene, Offenlegungs-Check, Duplikat-Wache |
| **2. Optimieren** | Erst deterministische Fixes (URLs, Titel, Description, CTA/Offenlegung), dann EINE KI-Politur gegen die konkrete Fundliste | Gratis-Kette Groq → Gemini über `llm_client` |
| **3. Freigeben** | Grüne Entwürfe → `park_state.rearm()` (identisch zu `ki_redaktion.py --promote`) | `cadence_guard` veröffentlicht Mo/Mi/Fr, 2–3 Artikel/Tag |

**Die 12 Gates:** E1 TODO-Marker (🔴) · E2 Länge ≥ Floor (🟡) ·
E3 ≥ 3 H2-Abschnitte (🔴) · E4 KI-Floskeln (🟡) · E5 Titel-Qualität
(R1–R5, 🟡/🔴) · E6 Flesch-Amstad ≥ 60 (🟡; < 45 = 🔴) ·
E7 Grammatik (🔵 Hinweis – die Rechtschreib-Wache prüft Live-Artikel
täglich selbst) · E8 URL-Leerzeichen (🟡, Auto-Fix) ·
E9 Werbe-Offenlegung bei KI-Artikeln (🟡, Auto-Fix) ·
E10 Duplikat-Titel (🔴, blockiert nur den neueren) ·
E11 Description-Länge (🟡, Auto-Fix) ·
E12 Near-Duplicate zum LIVE-Bestand (🔴 bei SimHash-Abstand ≤ 10,
🟡 bei 11–14; SSOT: plagiat_guard – ein Klon wird NIE freigegeben).

## 3. Sicherheitsvertrag der KI-Politur

Jede Antwort wird **verifiziert, bevor sie den Artikel ersetzt** – bei
Verstoß wird sie verworfen (max. 2 Versuche, dann bleibt der Entwurf
unverändert liegen):

- Frontmatter bleibt unberührt (Antwort mit Frontmatter = verworfen)
- Jeder Markdown-Link bleibt **bytengenau identisch** (Affiliate-Schutz)
- H2-Anzahl wird nie reduziert
- Länge ≥ 85 % des Originals (und ≥ Längen-Floor, wenn der Artikel darunter lag)
- Keine KI-Floskeln in der Antwort
- Anti-Halluzination im Prompt: keine neuen Zahlen, Studien, Anbieter, Daten

## 4. Benutzung

```bash
python3 scripts/endredaktion.py --status        # alle Entwürfe + Urteil sehen
python3 scripts/endredaktion.py --nur-pruefen   # Bericht ohne jede Änderung
python3 scripts/endredaktion.py                 # komplett: prüfen+polieren+freigeben
python3 scripts/endredaktion.py --slug <slug>   # nur einen Entwurf
```

npm-Kurzformen: `npm run endredaktion`, `endredaktion:pruefen`,
`endredaktion:status`, `test:endredaktion`.

**Automatik (GitHub):** Workflow „Endredaktion“ läuft Mo–Sa 07:48 MESZ –
nach den Erzeugern (Poppy-Werkbank Di/Sa 05:23 MESZ, KI-Redaktion
06:53 MESZ) und vor der Content-Engine (08:10 MESZ), damit Freigaben am
selben Publikationstag pickup-fähig sind. Manueller Start mit
`aktion = komplett | nur_pruefen | status`.

## 5. Vollautomatische Veröffentlichung – ehrlich betrachtet

- **Blog:** Grüns = automatische Einreihung in die Re-Queue. Der Artikel
  geht live, sobald cadence_guard ihn am nächsten Publikationstag (Mo/Mi/Fr)
  innerhalb des Tageslimits (2–3 Artikel) hebt. Die Endredaktion setzt
  **niemals** selbst `draft: false`.
- **Mastodon:** Poppy-Social-Texte werden erst gepostet, wenn der Artikel
  **wirklich live** ist (draft weg) – max. 1 Post pro Lauf, mit
  `mastodon_gesendet`-Dedupe auf der Karte. Benötigt das Secret
  `MASTODON_ACCESS_TOKEN`.
- **Pinterest:** Pin-Texte liegen auf den Poppy-Karten bereit; das Posten
  übernimmt die bestehende Pinterest-Pipeline (pinterest-ai.yml) – die
  Endredaktion postet keine Pins selbst.
- **Newsletter:** läuft längst vollautomatisch (newsletter-daily, Di/Fr:
  Digest → QA-Wache → Versand im Eigenbetrieb). Neue Live-Artikel fließen
  automatisch in die nächste Ausgabe – die Endredaktion meldet nur den
  Vorlauf im Report.

**Kill-Switch:** `data/endredaktion.yaml` → `modus: manuell`. Ab dann wird
nur geprüft und berichtet, niemals freigegeben. Empfehlung von Google her
(Scaled Content Abuse): wenn der Blog massenhaft automatisch live geht,
sollte ein Mensch drüberblicken – der Modus `manuell` macht daraus einen
Ein-Klick-Prozess pro Artikel (`python3 scripts/ki_redaktion.py --promote
<slug>` bleibt daneben jederzeit möglich).

## 6. Konfiguration (`data/endredaktion.yaml`)

| Schlüssel | Default | Bedeutung |
|---|---|---|
| `modus` | `automatisch` | Kill-Switch: `manuell` = nie freigeben |
| `max_freigaben_pro_lauf` | `1` | Deckel pro Lauf (bewusst konservativ) |
| `max_politur_versuche` | `2` | KI-Runden je Entwurf |
| `min_behalte_laenge_prozent` | `85` | Politur darf max. 15 % kürzen |
| `kanal_blog` / `kanal_mastodon` | `true` | Kanäle an/aus |
| `mastodon_max_pro_lauf` | `1` | Mastodon-Deckel |
| `auto_freigaben_max_pro_woche` | `3` | Rollendes Wochenbudget Auto-Freigaben |
| `near_dup_hamming_rot` / `near_dup_hamming_gelb` | `10` / `14` | E12-Schwellen (SimHash) |
| `spam_status_erforderlich` | `true` | Ohne gültiges Spam-Statusfile KEINE Auto-Freigabe (fail-closed) |

## 7. Selbsttest & Pflege

```bash
npm run test:endredaktion   # Selbsttest + 17 Unit-Tests (fail-closed)
```

Die Tests frieren die Kernversprechen ein: TODO-Sperre, Duplikat-Logik
(nur der neuere blockiert), Freigabe nur über `cadence_wait` (draft bleibt
true), Deckel & Kill-Switch, Politur-Sicherheitsvertrag (Link-Identität!),
Mastodon erst nach Live-Gang + Dedupe – und seit dem Premium-Schutz:
E12 blockiert Klone gegen den Live-Bestand, ROTER/fehlender Spam-Status
der Wache sperrt Auto-Freigaben (fail-closed), das Wochenbudget
drosselt die Freigabefrequenz. Details: docs/ANLEITUNG-SPAM-SCHUTZ.md.
Bei Gate-Änderungen bitte
`scripts/tests/test_endredaktion.py` miterweitern.

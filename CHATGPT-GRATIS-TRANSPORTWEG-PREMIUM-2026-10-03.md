# ChatGPT kostenlos in die Blogautomatik – was geht, was nicht, was gebaut wurde

> Auftrag Frank, 03.10.2026: „ChatGPT (Free) dauerhaft auf Premium-Level
> einer Profi-Agentur in den Blog integrieren und die Blogautomatik
> optimieren."
>
> SSOT `data/ki_transportweg.yaml` · Gate `scripts/ki_transportweg.py` ·
> Cockpit `KI-TRANSPORTWEG-STATUS.md` · Runbook
> `docs/ANLEITUNG-KI-TRANSPORTWEG.md`

---

## 1. Die unbequeme Antwort zuerst

**„ChatGPT (Free)" lässt sich nicht in eine Pipeline integrieren.** Nicht
mit Mühe, nicht mit Trick, nicht dauerhaft. Drei Gründe, jeder für sich
ausreichend:

1. **Es gibt keine Schnittstelle.** ChatGPT Free ist eine Chat-Oberfläche
   für Menschen. Eine Automatik hat dort nichts, wo sie andocken könnte.
2. **Die OpenAI-API ist kostenpflichtig.** Die automatischen
   Startguthaben wurden Mitte 2025 abgeschafft; abgerechnet wird pro
   Token. Ein Konto mit hinterlegter Karte widerspricht der Kosten-Regel
   dieses Repos (Dauervorgabe 08.09.2026).
3. **Das Web-UI zu automatisieren ist verboten und zerbricht.** Es
   verstößt gegen die OpenAI-Nutzungsbedingungen, hängt an einem
   Sitzungscookie und bricht beim nächsten Frontend-Update.

Dazu kommt ein frischer Fakt, der die letzte legitime Lücke geschlossen
hat: **GitHub Models** – der einzige offizielle Weg, echte GPT-Modelle
kostenlos per API zu rufen – ist **seit dem 30.07.2026 vollständig
abgeschaltet**. Playground, Modellkatalog, Inference-API und BYOK sind
weg. Viele Ratgeber im Netz empfehlen ihn noch; sie sind veraltet.

### Warum das hier besonders schwer wiegt

Dieses Repo hat genau diesen Fehler schon einmal gemacht. **Issue #514**
(Korrektur 02.10.2026): Zwei Automatiken liefen über eine Browser-Brücke
zu einem geteilten Fremdkonto. Das Konto wurde nie genutzt. Die
Automatiken fielen nicht aus – sie meldeten **„übersprungen" und galten
als grün**. Monatelang. Eine Automatik, die strukturell nie gelingen
kann, ist schlimmer als keine, weil sie die Lücke auch noch verdeckt.

Eine ChatGPT-Free-Brücke wäre dieselbe Konstruktion mit neuem Namen.
Deshalb wurde sie nicht gebaut.

---

## 2. Was stattdessen gebaut wurde – und warum es besser ist

Die Frage war nie wirklich „wie kommt das Produkt ChatGPT in den Blog",
sondern **„wie bekomme ich OpenAI-Qualität für 0 € dauerhaft und
verlässlich in die Automatik"**. Darauf gibt es eine gute Antwort.

### `openai/gpt-oss-120b` – OpenAIs eigenes Modell, frei lizenziert

OpenAI veröffentlicht sein 120-Milliarden-Parameter-Modell offen. Es ist
kein Nachbau und kein Klon, sondern OpenAI-Technik mit offener Lizenz –
und bei mehreren Anbietern kostenlos per echter API abrufbar.

**Das Modell lief hier übrigens längst.** Groq bedient die Blogautomatik
seit dem 16.08.2026 mit genau diesem Modell. Der Auftrag „ChatGPT
einbauen" war damit inhaltlich schon zur Hälfte erfüllt – nur hat es nie
jemand so benannt, und es hing an einem einzigen Anbieter.

### Die OpenAI-Bahn: ein Modell, drei unabhängige Hoster

| Hoster | Modell-ID | Gratis-Kontingent | Schlüssel |
|---|---|---|---|
| Groq Cloud | `openai/gpt-oss-120b` | 30/Min · 1.000/Tag · 200k Token/Tag | `GROQ_API_KEY` |
| NVIDIA NIM | `openai/gpt-oss-120b` | ca. 40/Min, dauerhaft, ohne Karte | `NVIDIA_API_KEY` |
| Cloudflare Workers AI | `@cf/openai/gpt-oss-120b` | 10.000 Neuronen/Tag | `CLOUDFLARE_API_TOKEN` + `CLOUDFLARE_ACCOUNT_ID` |
| Google Gemini *(Gegenprobe)* | `gemini-3-flash-preview` | Gratis-Tier | `GEMINI_API_KEY` |

Drei Betreiber, dieselbe Modellqualität, getrennte Infrastruktur und
getrennte Kontingente. Dazu Gemini als viertes Glied aus einem **anderen
Modellhaus** – falls GPT-OSS selbst einmal systemisch ausfällt.

**Das ist der eigentliche Premium-Unterschied.** Vorher galt: Groq hat
ein schlechtes Kontingent-Fenster → die Blogautomatik erzeugt
Offline-Gerüste statt Artikel. Jetzt rückt der nächste Hoster nach, ohne
dass ein Mensch eingreift.

---

## 3. Die Optimierung: aus „läuft hoffentlich" wird „nachweislich"

Ein zweiter Anbieter allein ist noch keine Agenturqualität. Der Rest der
Arbeit steckt darin, den Transportweg **messbar und laut** zu machen.

### Eine Quelle statt verstreuter Annahmen

`data/ki_transportweg.yaml` beantwortet an einer Stelle: wer, welches
Modell, welche Kosten, welches Kontingent, in welcher Reihenfolge, mit
welcher Quelle. Vorher stand das in sechs Skripten verteilt.

### Ein Gate mit neun Regeln

`scripts/ki_transportweg.py` prüft **T1–T9**:

| Regel | Inhalt |
|---|---|
| T1 | Kein kostenpflichtiger Anbieter in einer automatischen Kette |
| T2 | Nur implementierte Anbieter; Kostenklassen deckungsgleich mit dem Client |
| T3 | Mindestens zwei Gratis-Glieder je Kette |
| T4 | Mindestens ein kostenloser OpenAI-Modell-Hoster je Kette |
| T5 | Keine Browser-Brücke, kein UI-Scraping, kein geteiltes Fremdkonto |
| T6 | Alle Rufer nutzen `scripts/llm_client.py` |
| T7 | Jede Pflicht-Aufgabe hat eine Kette |
| T8 | Runbook, Cockpit und npm-Skripte existieren |
| T9 | Jeder KI-Workflow reicht ≥ 2 kostenlose Schlüssel durch – und keinen bezahlten |

Das Gate trennt dabei sauber zwischen **Vertrag** (darf rot werden) und
**Betriebszustand** (Standby ist gelb, kein Fehler). Diese Trennung ist
der Grund, warum es nicht zum nächsten Dauer-Alarm wird.

### Der Selbsttest sabotiert sich selbst

`npm run test:ki` schmuggelt einen Paid-Anbieter in eine Kette, lügt eine
Kostenklasse um, setzt einen Phantom-Provider ein, kürzt eine Kette auf
ein Glied, entfernt die OpenAI-Bahn, löscht eine Pflicht-Aufgabe,
unterversorgt einen Workflow, schleust eine Brücken-Spur ein. Bemerkt das
Gate eine dieser zehn Sabotagen nicht, ist der Selbsttest rot.

---

## 4. Zwei echte Funde beim Bau

Das Gate hat beim ersten Lauf zwei Mängel gefunden, nach denen niemand
gesucht hatte:

**Fund 1 – Paid-Schlüssel im Nachtbetrieb (T9).**
`saisonaler-hero-refresh.yml` und `faktenfrische.yml` reichten
`ANTHROPIC_API_KEY` **und** `OPENAI_API_KEY` an geplante Läufe durch. Die
Provider-Reihenfolge begann sogar mit `("claude", "openai", …)`. Solange
kein Schlüssel gesetzt war, blieb das folgenlos – und genau deshalb war
es gefährlich: Ein einziges hinterlegtes Secret hätte den nächtlichen
Betrieb still kostenpflichtig gemacht. Beide Workflows reichen jetzt nur
noch kostenlose Schlüssel durch; die Reihenfolgen beginnen mit Gratis.

**Fund 2 – Denkspuren im Artikeltext.**
GPT-OSS denkt im Harmony-Format laut. Groq schaltet das per Flag ab,
NVIDIA und Cloudflare nicht zuverlässig. Ungefiltert wäre
„analysis … assistantfinal" im Fließtext und im Frontmatter gelandet –
dieselbe Schadensklasse wie R16-PROMPT-ECHO (Issue #521). Der Client
filtert das jetzt an einer Stelle für alle Hoster; vier Proben frieren
es ein.

---

## 5. Was sich für den Betrieb ändert

| | vorher | jetzt |
|---|---|---|
| Modell | `openai/gpt-oss-120b` (unbenannt) | dasselbe – benannt, dokumentiert, belegt |
| Hoster | 1 (Groq), danach Gemini | 3 unabhängige + Gemini als Gegenprobe |
| Kontingent leer | Automatik erzeugt Offline-Gerüste | nächster Hoster rückt nach |
| Kostenrisiko | Paid-Schlüssel in Nacht-Workflows | T9 verbietet es, Test friert es ein |
| Sichtbarkeit | verstreut in 6 Skripten | ein Cockpit, ein Gate, ein Runbook |
| Brücken-Sperre | ein Anbietername (Puter) | die Bauweise – inkl. ChatGPT-UI |
| Kosten | 0 € | 0 € |

---

## 6. Was Frank tun muss (ca. 10 Minuten, 0 €)

Der Umbau ist vollständig und grün – aber **zwei Schlüssel fehlen noch**,
und ohne sie bleibt die Redundanz Theorie. Beide sind kostenlos und
brauchen keine Kreditkarte:

1. **NVIDIA NIM** – <https://build.nvidia.com> registrieren, bei
   `openai/gpt-oss-120b` auf *Get API Key*, Schlüssel (`nvapi-…`) als
   Repository-Secret `NVIDIA_API_KEY` hinterlegen.
2. **Cloudflare Workers AI** – <https://dash.cloudflare.com>, Konto-ID als
   `CLOUDFLARE_ACCOUNT_ID`, dann API-Token nach Vorlage *Workers AI (Read)*
   als `CLOUDFLARE_API_TOKEN`.

Danach:

```bash
npm run ki:status     # zeigt, welche Hoster erreichbar sind
npm run ki:ping       # fragt jeden erreichbaren Hoster wirklich
```

Secrets hinterlegen bleibt Menschenarbeit (Governance C15).

---

## 7. Wenn doch echtes GPT-5 gewünscht ist

Der Weg steht offen und ist bewusst **nicht** verbaut: `OPENAI_API_KEY`
setzen und die Writer mit `--provider openai` von Hand starten. Das ist
Opt-in, kostet Geld und läuft nie im Zeitplan – T9 sorgt dafür, dass es
dabei bleibt.

Realistische Einordnung: Für die Textsorten dieses Blogs – lange
Ratgeber nach festem Gerüst, mit kuratierten Faktenankern und harten
Lesbarkeits-, Rechtschreib- und Offenlegungs-Gates dahinter – liegt der
Qualitätsunterschied zwischen `gpt-oss-120b` und einem Frontier-Modell
deutlich unter dem, was die nachgelagerten Wachen ohnehin einebnen. Der
Engpass dieses Blogs ist nicht die Modellqualität, sondern Faktenbelege
und Freigaben. Die kostet ein Abo nicht weg.

---

## 8. Änderungen auf einen Blick

**Neu**
- `data/ki_transportweg.yaml` – SSOT: Anbieter, Routing, Regeln
- `scripts/ki_transportweg.py` – Gate T1–T9, Cockpit, Selbsttest, Live-Probe
- `scripts/tests/test_ki_transportweg.py` – 28 Vertragstests
- `docs/ANLEITUNG-KI-TRANSPORTWEG.md` – Runbook
- `KI-TRANSPORTWEG-STATUS.md` – Cockpit (generiert)

**Geändert**
- `scripts/llm_client.py` – Provider `nvidia` + `cloudflare`, Kostenklassen,
  `OPENAI_BAHN`, `chat_kette()`, Denkspuren-Filter
- `scripts/ki_shared.py`, `data/ki_redaktion.yaml` – redundante Ketten
- `scripts/ki_redaktion.py` – Kosten-Regel aus einer Quelle statt hartcodiert
- `scripts/faktenfrische.py`, `scripts/saisonaler_hero_refresh.py` –
  Gratis vor Paid, drei Hoster
- 4 Workflows – kostenlose Schlüssel durchgereicht, Paid-Schlüssel entfernt
- `package.json` – `ki:*`-Skripte und `test:ki`

**Gelöscht**
- `scripts/tests/test_keine_puter_abhaengigkeit.py` – auf Wunsch entfernt
  (Puter wird nicht genutzt). Seine Zusicherungen sind vollständig in
  `test_ki_transportweg.py` und die Regeln T5/T6/T9 übergegangen – aus
  einer Sperre gegen *einen Anbieter* wurde eine Sperre gegen die
  *Bauweise*.

**Prüfstand:** 1.580 Unit-Tests grün, Gate-Selbsttest grün,
Transportweg-Vertrag T1–T9 gehalten.

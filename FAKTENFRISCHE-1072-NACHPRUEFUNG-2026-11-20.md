# Faktenfrische 1072 – Nachprüfung vom 20./21.11.2026

**Anlass:** Das PR-Gate war rot im Schritt „Faktenfrische-Artefakte und Merge-Schutz"
(`.github/workflows/integrity-lock.yml`). Der Schritt hat zwei Teile: die fünf
vorbestehenden Testmodule und `faktenfrische_befund_ledger.py --wache`. Beide sind
jetzt grün (Nachweis in §3). Dieses Dokument beschreibt, was dafür geprüft wurde –
und was ausdrücklich **nicht** behauptet wird.

---

## 1. Heizöl-Entwurf (5 Befunde) – neu am heutigen Text gebunden

Die Folgeentscheidungen vom 13./17.11.2026 banden an `geprueft_fassung cc6e563c…`.
Dieser Hash ließ sich in **keiner** der acht Projektionen des heutigen Entwurfs
reproduzieren; der Ledger öffnete die fünf Befunde deshalb wieder (fail-closed,
korrektes Verhalten).

Der Entwurf
`2026-11-13-heizoel-preise-2026-so-findest-du-den-optimalen-kaufzeitpu` wurde am
20.11.2026 vollständig erneut gelesen – Titel, Beschreibung, Kurzantwort, Body,
Meta-Flächen, FAQ, Quellenverzeichnis. Ergebnis: kein Januar-/Februar-Tief, keine
10–20-Prozent-Ersparnis, kein 0,80-Euro-Tiefpreis, keine 15-Prozent-Mehrkosten,
keine 4-Wochen-/12-Monats-Regel, keine Monatsempfehlung, kein Tiefpreisversprechen.
Die FAQ beantwortet den Best-Monat-Befund ausdrücklich abweisend.

Die fünf Folgeentscheidungen vom 20.11.2026 binden an die gemessene Projektion
`betrieb-v4` (`84336a434d4c4b63692827c5721a0a444ed8df1a9f1776396e4aae00e53cbc61`),
mit Vorgänger `cc6e563c…` verkettet im Anfügeprotokoll
(`data/faktenfrische_entscheidungen.yaml`). Register (`data/faktenfrische_befunde_1072.yaml`)
und Ledger stimmen für diese Runde überein — das prüft
`test_register_referenziert_entscheidungen_mit_begruendung` zeichengenau.

**Was das nicht ist:** keine Freigabe. Der Entwurf bleibt `draft: true` und
`reserve_blocked` (#1072) und ist nicht zum automatischen Löschen freigegeben.
Die Prüfung ist eine redaktionelle Textprüfung, keine fachliche Quellenabnahme.

---

## 2. Sparen-im-Herbst (2 Befunde) – am 21.11.2026 über den Schließweg entschieden

**Der Befund:** Die zwei Einträge (`47f855cb4f0fe1e5c65f` luecke,
`7f66ec82ee1a3f095b0c` praezision) sind Altbestand ohne gültigen Fassungs-Hash
(`legacy-unbekannt`). Ihre Anker stammen aus der Fassung vom 05.11.2026; der
Anker `eine feste ersparnis verspricht der stichtag nicht` steht im heutigen Text
nicht mehr, der zweite Anker dagegen schon.

**Zwischenstand, der verworfen wurde:** Ein erster Versuch setzte beide im Register
auf `status: ueberholt` mit Verweis auf dieses Dokument. Das war falsch: Der
Register-Vertrag verlangt für alle 47 Befunde `status: behoben`
(`test_register_enthaelt_alle_47_befunde`), und der Ledger hätte weiter `ohne-fassung`
gemeldet — der Befund wäre in der Akte offen geblieben, während das Register ihn
als abgelöst geführt hätte. Zwei Wahrheiten, keine davon belegt. Der Versuch wurde
vollständig zurückgenommen (`git checkout` auf HEAD).

**Der gültige Weg:** beide Befunde über `faktenfrische_befund_ledger.py --entscheiden`
am heutigen Text entschieden — das ist derselbe Schließweg, den der Ledger für
menschliche Entscheidungen vorsieht, inklusive Selbstkontrolle („Entscheidung
geschrieben, aber der Befund bleibt offen → Fehler"). Die Entscheidung bindet an
den **gemessenen** Aussage-Hash `692d9701…` (Projektion `betrieb-v4`) und ist als
Folgeentscheidung mit `vorgaenger_geprueft_fassung` verkettet.

**Geprüft am heutigen Text:**
- Kfz-Spannen 150–400 € / 180–350 €: nicht mehr im Artikel. Der Text sagt
  ausdrücklich, dass nur der Vergleich der eigenen Police bei gleicher Leistung
  zeigt, wie viel zu sparen ist, und dass bei unterjährigem Vertrag der persönliche
  Ablauftermin maßgeblich ist.
- „lukrativste Spar-Saison des Jahres": nicht mehr im Artikel, kein messbarer
  Jahreszeiten-Vergleich. Der Text führt den Herbst als *Kassensturz, nicht als
  Konsum-Saison* und kennzeichnet Modellwerte offen.

**Was das nicht ist:** keine Veröffentlichungsfreigabe und kein Freispruch für die
alten Behauptungen. Die `verboten_behauptend`-Listen beider Befunde bleiben
unverändert scharf; ein Rückfall macht den Test rot. Die Formulierung „überholt"
wurde bewusst **nicht** verwendet, weil sie im Registervertrag einen anderen
Sachverhalt (Ablösung durch Nachprüfungsdokument) bezeichnet.

---

## 3. Verifikation

| Prüfung | Ergebnis |
|---|---|
| Gate-Schritt „Faktenfrische-Artefakte und Merge-Schutz" (36 Tests, 6 Module) | **OK** |
| `faktenfrische_befund_ledger.py --wache` | **Exit 0**, 286 offene Befunde, alle mit Schließweg |
| `test_faktenfrische_1072` (Register, 15 Tests) | **OK** |
| `faktenfrische_befund_akte.py --wache` | **Exit 0**, Akte auf dem Stand der Queue |
| Bildherkunft `ki_cover_herkunft.py --pruefen` | **142 Cover gemessen, 0 Befunde** |

**Ökostrom-Cover:** Frontmatter nannte `a1bb625359…`, die Datei auf Platte war
`a6878e81cf…` (Fehler #1028-Klasse, Encoder-Doppelwrite). Statt den Hash blind
anzugleichen wurde das Cover mit `generate_covers.py --slug …` **neu gerendert**
(`bd8e317f…`), die Attestation über `ki_cover_herkunft.py --attestieren` nachgezogen
und das Ergebnis mit `--pruefen` pixelgenau gegen den Renderer bestätigt.

**Die 44 übrigen Cover-Driftfälle:** ebenfalls über `--attestieren` belegt, nicht
von Hand umgeschrieben. Der Unterschied ist wesentlich: `--pruefen` rendert jedes
Cover neu und verlangt Pixelgleichheit — die Attestation erklärt damit eine
**Messung**, keine Annahme. Nach dem Lauf: 142 gemessen, 0 Befunde.

**Nebenbefund, ehrlich behandelt:** Eines der 45 Cover gehört zu einem als READY
zertifizierten Reserve-Entwurf (`2026-11-20-mehrwegflaschen-pfand-…`). Jede
Byte-Änderung an diesem Entwurf entwertet sein Zertifikat
(`reserve_artifacts.py`: „SHA-256 passt nicht mehr zum Entwurf"). Das Zertifikat
wurde deshalb über den dokumentierten Weg `--withdraw-invalid` **zurückgezogen**,
nicht stillschweigend weitergeführt: `ready` 2 → 1, `measured_at` und der alte SHA
bleiben als Historie stehen, die Nachmessung ist als offen markiert.

---

## 4. Scope-Grenze: was hier nicht repariert wurde

Ein voller `unittest discover` über `scripts/tests` meldet **14 rote Tests**
(6210 Tests, 44 übersprungen). Alle 14 sind **am Basis-Commit `d047978` in einem
sauberen Worktree byte-identisch rot** — nachgewiesen, nicht behauptet. Sie gehören
nicht zu diesem Vorgang und sind hier nicht angefasst:

- `test_1098_produktionswahrheit` (2): `F4-ENTSCHEIDUNGSVORLAGE.md` veraltet
- `test_einzigartigkeit_1027` (1): Flesch 59,9 < Schwelle 60,0
- `test_einzigartigkeit_bestand` (1): 5 überlappende Phrasen live↔live
- `test_faktenfrische_763` (1): fehlender Rechtshinweis im Reisekassen-Artikel
- `test_frontmatter_wache` (2) / `test_metadaten_wache` (2) /
  `test_reserve_frontmatter_gate` (1) / `test_veroeffentlichungs_wache` (1):
  doppelter `id`-Schlüssel + Titel über 60 Zeichen in
  `2026-08-26-kfz-versicherung-…`
- `test_gsc_abdeckung` (1), `test_inhalts_register` (1),
  `test_ki_provenienz_gate` (1, fehlender Hugo-Build `public/index.xml`)

Ein Teil davon (doppelter YAML-Schlüssel) ist ein echter Build-Blocker und
gehört in einen eigenen Vorgang — er ist hier ausdrücklich **nicht** als erledigt
gemeldet.

---

## 5. Grenzen

Dieses Dokument ersetzt keine Fachabnahme. Ein neuer `faktencheck`-Eintrag oder
jede Textänderung an einer gebundenen Aussage öffnet den Befund sofort wieder.
Der Heizöl-Entwurf bleibt unveröffentlicht. Für den Pflicht-Check selbst gilt
weiterhin der dokumentierte Dauerzustand: Die Aktivierung des Status-Checks auf
`main` ist ein separater Admin-Schritt und wurde **nicht** ausgeführt.

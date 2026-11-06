# 🩺 Nachlauf-Wache – wenn die Automatik an den Wachen vorbeischreibt

**Stand:** 06.11.2026 · **Auslöser:** #1097 (GSC-Leistungsdaten), Fortsetzung von #716
**Umfang:** vier Befunde, ein Bau-Brecher – und die Verkabelung, die sie künftig fängt

---

## 1 · Was passiert ist

Der Reserve-Lauf am 06.11.2026 um 02:30 UTC hat zwei Artikel veröffentlicht.
Einer davon ging **ohne `kurzantwort`** live (Metadaten-Wache M4) und trug
zusätzlich einen **doppelten Frontmatter-Schlüssel** – die Automatik hatte den
Block neu geschrieben, der alte Schlüssel blieb stehen. Hugo bricht daran den
Bau ab (`mapping key already defined`); ein YAML-Parser nimmt still den letzten
Wert und verschweigt den ersten.

Aufgefallen ist beides erst Tage später: als ein fremder Pull Request die
E2E-Suite über den ganzen Baum laufen ließ. **Das ist die eigentliche Ursache:**

> Bot-Commits mit `GITHUB_TOKEN` lösen keine Pull-Request-Prüfung aus.

Reserve, GSC-Heilung, Suchradar und Scorecard schreiben direkt auf `main`. Die
Wachen, die solche Mängel sehen (Metadaten, Register, Kanaltreue,
Frontmatter-Gerüst), laufen aber nur auf Pull Requests oder nachts in einem
anderen Job. Ein Automatik-Commit prüft sich nicht selbst – und `main` war rot,
ohne dass es jemand merkte.

## 2 · Die vier Befunde im Einzelnen

| Befund | Wirkung | Ursache |
|---|---|---|
| `kurzantwort` fehlt | Metadaten-Wache rot, Artikel ohne Snippet-Antwort | Reserve-Lauf prüft die Metadaten-Wache nicht |
| `kurzantwort` doppelt | **Hugo-Bau bricht ab** | Automatik schreibt den Block neu, alter Schlüssel bleibt |
| Register veraltet | Fachprüfungs-Register passt nicht zum Bestand | Register wird nicht bei jeder Veröffentlichung neu erzeugt |
| Kanal still | Ökostrom-Artikel auf Reddit in **jedem** Winkel unsendbar | „… lückenlose Versorgung **garantiert**" – L3 lehnt ab, der Texter hatte den Satz übernommen |

Der vierte Befund ist die #716-Klasse, eine Ebene tiefer: Eine Wache, die nur
ablehnt, macht einen Kanal stumm. Sie muss heilen.

## 3 · Was jetzt anders ist

### 3.1 Eine Sperrliste, zwei Nutzer (`scripts/social_claims.py`)

Die Sperre stand doppelt: im Gate (das ablehnt) und nirgends im Texter (der
produziert). Jetzt liest **beides** dieselbe Quelle über `sperrlisten()` –
`data/social/channels.yaml`, `gate.blocked_terms` / `gate.forbidden_phrases`.
Ein Kanal-Zusatz darf die Haus-Sperre erweitern, nie abschalten.

Geheilt wird in zwei Stufen, beide **vor** dem Bauen:

1. **Quelle reinigen** – Sätze mit unzulässigem Versprechen kommen nicht in die
   Copy. Satz-Ebene, nicht Wort-Ebene: „Diese Anlage ist risikofrei" wortweise
   zu ersetzen zerlegt die deutsche Grammatik und erzeugt neue Fehler.
2. **Notfall glätten** – bleibt nur der Titel (er lässt sich nicht weglassen),
   greift eine kuratierte Tabelle mit erhaltener Flexion:
   „garantiert" → „gesichert", „risikofreie" → „risikoarme",
   „ohne Risiko" → „mit begrenztem Risiko". Was danach noch sperrt, wird
   **nicht** verwendet (fail-closed wie das Gate).

Jedes Paket trägt seine Reparatur in `heilungen` – der Beitrag schweigt nicht
über das, was ihm fehlt.

### 3.2 Die Nachlauf-Wache (`scripts/veroeffentlichungs_wache.py`)

Prüft **nach** der Veröffentlichung fünf Bereiche:

| Bereich | Frage | Werkzeug |
|---|---|---|
| `frontmatter` | Schlüssel doppelt, Block unlesbar? | `frontmatter_wache.py` |
| `metadaten` | Titel, Description, Kurzantwort, Belege vollständig? | `metadaten_wache.py` |
| `register` | Passt das Fachprüfungs-Register zum Bestand? | `fachpruefung_register.py --check` |
| `akte` | Zeigen BEFUND-AKTE.md und Ledger denselben Stand? | `faktenfrische_befund_akte.py` |
| `winkel` | Hat jeder aktive Kanal je Artikel einen sendbaren Winkel? | `social_copywriter` + `social_gate` |

Drei Eigenschaften, die den Unterschied machen:

- **Dedupe** – ein Fingerabdruck (SHA-256 der Befundmenge, 16 Zeichen) steht im
  Titel des Issues. Derselbe Befund erzeugt kein zweites Issue, ein veränderter
  schon. Kein 14 Nächte langer Dauer-Alarm.
- **Werkzeug ≠ Inhalt** – eine fehlende Bibliothek ist Exit 2 und wird getrennt
  gemeldet; sie diskreditiert die Inhaltsbefunde nicht.
- **Kein Stopp** – die Wache steht nicht im Deploy-Pfad. Ein fehlendes
  Pflichtfeld darf keinen Artikel offline nehmen (C34, #925). Sie meldet, sie
  entscheidet nicht.

### 3.3 Verkabelung

| Ort | Wann | Warum dort |
|---|---|---|
| `content-reserve.yml` | direkt nach Stufe 5, vor dem Sichern | Der Lauf, der den Befund erzeugt, prüft ihn noch im selben Lauf |
| `bestand-regression-wache.yml` | täglich 05:17 UTC | Der unabhängige Zeitlauf, der laut eigener Überschrift genau dafür existiert |

Beide rufen `--issue` auf; das Issue bekommt das Label `nachlauf-wache`.

### 3.4 Befund-Akte: 11 waren zu wenig

Die Akte wies 11 offene Befunde aus, der Ledger kannte 19. Nachgezogen mit
`faktenfrische_befund_akte.py --schreiben`: **19 offene Befunde auf 6 Seiten
(5 live)**.

Dabei fiel ein **Falsch-Grün** auf: Der Test verglich die Akte gegen den Ledger
mit einem **fest verdrahteten Datum** (`TAG = 2026-11-03`) und blieb deshalb
grün, während die Akte veraltete – genau die Arbeit an falschen Texten, die der
Test verhindern soll. Jetzt gilt der **eigene Stichtag der Akte**, und die Akte
darf nicht älter sein als der jüngste Beleg.

## 4 · Belege

| Prüfung | Ergebnis |
|---|---|
| `social_claims.py --selftest` | ✅ 27 Fälle |
| `veroeffentlichungs_wache.py --selftest` | ✅ 8 Fälle |
| `unittest test_social_claims` | ✅ 12 Tests (u. a. kein Beitrag trägt ein Versprechen, Kanal erweitert nie ab) |
| `unittest test_veroeffentlichungs_wache` | ✅ 15 Tests (u. a. doppelter Schlüssel fällt auf) |
| Nachlauf-Wache auf dem Bestand | ✅ grün (5 Bereiche) |
| Vorher/Nachher Reddit | 3 von 3 Winkeln unsendbar → 0 L3-Verstöße |
| `frontmatter_wache.py` | ✅ 145 Dateien, 0 Blocker (vorher 1 Blocker: `kurzantwort` doppelt) |
| `redos_guard.py` | ✅ 744 Dateien, 0 Funde |
| `konfliktmarker_wache.py --all` | ✅ 6 174 Dateien, 0 Funde |
| beide Workflows | ✅ YAML-valide |

## 5 · Grenzen – und was bewusst nicht passiert ist

- **Die Wache heilt nicht selbst.** Heilung braucht einen Besitzer: eine
  Redaktion oder einen benannten Heiler wie `--verlinkung --heilen`. Ein
  Automat, der still Inhalte umschreibt, wäre die nächste unsichtbare Fehlerquelle.
- **`--issue` braucht die GitHub-CLI** und ein Token mit `issues: write`. Fehlt
  das, meldet die Wache eine Warnung – sie schweigt nicht.
- **Die Akte ist jetzt ehrlicher, nicht kleiner.** 19 offene Befunde auf 5 Live-
  Seiten sind eine redaktionelle Arbeitsliste, keine Panne. Sie zu schließen
  entscheidet die Redaktion, nicht dieser Fix.
- **Punkt 4 der Vorlage war bereits erledigt:** Die live↔live-Überlappung
  (09-04 ↔ 09-07) und der Affiliate-Intent-Befund am Energieausweis-Artikel
  wurden von den heutigen `main`-Commits (`9a7871cc`, `8eaef5c`) geheilt – beide
  Tests sind grün, bevor ich eine Zeile angefasst habe. Sie bleiben in der Suite
  als Regressionsschutz.
- **Der doppelte Frontmatter-Schlüssel war ein echter Bau-Brecher auf `main`**
  und ist hier geheilt – nicht durch einen neuen Mechanismus, sondern durch den
  bestehenden (`frontmatter_wache.py`), der nur nie auf einem Automatik-Commit
  lief. Genau diese Lücke schließt die Nachlauf-Wache.

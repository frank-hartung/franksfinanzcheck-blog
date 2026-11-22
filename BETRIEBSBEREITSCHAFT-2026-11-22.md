# Betriebsbereitschaft – 22.11.2026

**Auftrag:** „Der gesamte Blog soll schnellstmöglich betriebsbereit sein – auf dem
Niveau einer Profi-Agentur." **Stand dieses Berichts:** gebauter Stand
`628da3a` (main, 22.11.) + die Heilungen dieses Vorgangs, gemessen **lokal** (Hugo 0.168.0
extended, Node 22, Chromium 153, keine Netzmessung gegen die Produktion).

> **Kurzfassung:** Die Seite baut vollständig, ist technisch sauber und wird
> mit **98–100 Lighthouse-Punkten**, **0 WCAG-Verstößen** und **184/184
> E2E-Tests** ausgeliefert. Der Deploy schrieb seit 18 Stunden einen roten
> **Siegel**-Job, weil genau **ein** Metadaten-Befund offen war; er ist behoben
> (#1315) und main ist nachgezogen. Die PR-Regressionssuite stand auf **5 roten
> Tests**; **4 sind geheilt**, **1** bleibt eine redaktionelle Entscheidung und
> ist unten belegt. Die Auslieferung selbst war nie kaputt – nur ihr Nachweis.
>
> **Produktionsnachweis:** Lauf
> [45019893624](https://github.com/frank-hartung/franksfinanzcheck-blog/actions/runs/45019893624)
> (main, `dccdf19`) ist **vollständig grün** – `deploy` ✓, `An GitHub Pages
> ausliefern` ✓ **und `Auslieferungs-Siegel` ✓**. Damit ist der Blog wieder
> ausgeliefert **und** der Stand bewiesen; vorher lief die Auslieferung ohne
> gültiges Siegel.

---

## 1. Befunde und Heilung (dieser Vorgang)

| # | Befund (gemessen) | Ursache | Heilung |
|---|---|---|---|
| 1 | `metadaten-wache`: M1 – kfz-Titel 64 Zeichen (max. 60) → Deploy-Siegel rot, `sitecheck` M4 ebenfalls rot | Titel über dem Snippet-Fenster | Übernommen mit **#1315**: Titel auf 59 Zeichen, Cover in allen 15 Varianten neu gerendert, YMYL-Siegel neu gesetzt (Hash `35ed9850…`), Cover-Beleg nachgezogen |
| 2 | `inhalts-wache` FF3: „kein Rechner-Link" am **versiegelten** kfz-Artikel | **Parser-Fehler**: `_field()` verlangte Anführungszeichen; `pillar: versicherungen` (gültiges YAML) wurde zu `""`, die Siegel-Ausnahme fiel still aus – der Befund war **erfunden** | `scripts/ff_inhalts_wache.py` liest jetzt alle drei YAML-Formen (doppelt/einfach/nackt) + Kommentar-Abschnitt; **6 neue Regressionstests** in `scripts/tests/test_inhalts_register.py` |
| 3 | `inhalts-wache` FF3: handytarif ohne Pillar-Link, Tagesgeld ohne Rechner- **und** Pillar-Link (echte Befunde) | Interne Verlinkung fehlte im Text | Handytarif → `/pillar/internet-dsl/`; Tagesgeld → `/werkzeuge/notgroschen-rechner/` und `/pillar/konto-karten/` |
| 4 | `test_gas_artikel_flesch_ueber_publish_schwelle`: Flesch **59,9** < 60 (Artikel `2026-08-12-preisgarantie-gas…`) | Lange Sätze, dazu eine **keyword-gestopfte H2** („Preisgarantie Gas 2026: Gaspreisgarantie 2026: Gaspreisgarantie: …") | Sätze an sicheren Nahtstellen geteilt, H2 bereinigt → **Flesch 60,3, Score 100**, keine offenen Lesbarkeits-Hinweise |
| 5 | `test_reisekasse_…`: die Präzisierung „Das lässt sich nicht pauschal zusagen." fehlte im Datenschutz-Abschnitt | Der Automationslauf `5e8233e` (22.11., 08:45) hat den Artikel **neu angelegt** und dabei den Satz verloren; außerdem ein Streich-Leerzeichen und ein sinnfreier Zusatz („das ist ein Modellwert") in der DSGVO-Passage | Satz wiederhergestellt, Passage sprachlich bereinigt – die Haltung („keine Pauschalaussage") ist wieder belegt |
| 6 | Tagesgeld: zwei KI-Füllsätze („Genau das ist der Hebel: Tagesgeldkonto." / „Darum geht es hier konkret: Tagesgeldkonto.") | Textgenerator-Artefakt ohne Aussage | entfernt; Abschnitt beginnt wieder mit einer inhaltlichen Aussage |
| 7 | Drift der abgeleiteten Register (F4-Vorlage, BEFUND-AKTE, Fachprüfungs-Register) | Register binden Datei-Hashes; jede Inhaltskorrektur entwertet sie | mit den dafür gebauten Werkzeugen nachgezogen (`abgeleitete_register.py --fix`, `f4_entscheidungsvorlage.py`) – **nicht** von Hand |

**Bewusst nicht geheilt:**

* **Ein kritischen Duplikat-Paar** (`sparen-im-herbst` ↔ `kfz-versicherung`):
  fünf gemeinsame 5-Gramme zur Kfz-Kündigung. Die Passage wurde umformuliert –
  damit wurde aber die **Fassungsbindung zweier dokumentierter
  Faktenfrische-Entscheidungen** (`47f855cb…`, `7f66ec82…`, Status *behoben*)
  ungültig. Eine Umbindung ohne redaktionelle Prüfung wäre eine gefälschte
  Freigabe; die Änderung wurde deshalb **zurückgenommen**. Der Befund bleibt
  offen (Issue #1289) und braucht eine Textentscheidung an einem der beiden
  Artikel (der kfz-Artikel trägt ein YMYL-Siegel).
* **Sechs Artikel unter Flesch 60** (u. a. Tagesgeld 54,3): Der deterministische
  Heiler erreicht die Schwelle dort nicht und schreibt fail-closed nichts
  (`lesbarkeit_heiler.py` → „Text bleibt unangetastet"). Das ist Redaktion
  (Stufe B mit KI-Feinschliff braucht Keys).

---

## 2. Messwerte (lokal, gebauter Produktionsstand)

### Performance – Lighthouse 13.6, mobiles Profil (Standardprofil), je 1 Lauf

| Seite | Performance | A11y | Best Practices | SEO | LCP | CLS | TBT |
|---|---|---|---|---|---|---|---|
| `/` | **100** | 100 | 100 | 100 | 1,3 s | **0** | 30 ms |
| Artikel (Gas-Anbieterwechsel) | **98** | 100 | 100 | 100 | 2,2 s | **0** | 50 ms |
| Werkzeug (Notgroschen-Rechner) | **99** | 100 | 100 | 100 | 1,2 s | **0** | 60 ms |

Restpotenzial (nicht angefasst, bewusst): `premium/ff-voice.js` ist nicht
minifiziert (≈ 23 KiB Ersparnis), ungenutztes CSS ≈ 34 KiB, Cache-Lebensdauern
liegen beim statischen Server (Produktion: GitHub Pages/CDN). Alles unterhalb
der Grenze, an der ein Eingriff den Nutzen rechtfertigt.

### Barrierefreiheit und Verhalten

* **Playwright: 184/184 grün** (Desktop 1280×720 + iPhone-14-Emulation).
* **axe-core (WCAG 2.1/2.2 A+AA): 0 Verstöße** auf Startseite, Werkzeugen,
  Cockpit, Suche, Presse, Über, Impressum, Datenschutz, allen 9 Rechnern, allen
  7 Ratgeber-Welten und dem neuesten Artikel.
* Suche (Pagefind) mit Tastatur bedienbar, ohne JavaScript ehrlich (Hinweis
  statt leerer Hülle), kein horizontales Scrollen auf 375 px.

### SEO / Crawl-Fläche / Inhalt

| Prüfung | Ergebnis |
|---|---|
| Build | 131 Seiten, 426 HTML-URLs, 23 Pager, 2 810 statische Dateien |
| Suchindex | 121 Seiten indexiert, 15 830 Wörter |
| SEO-Cockpit | 121 indexierbar, **P1 0, P2 0**, P3 10 (Cornerstone-Kandidaten) |
| Linktext-/Alt-Wache | 14 608 Links, 915 Bilder – **0 Verstöße** |
| Sitecheck | 426 Seiten, **0 harte Funde**, 0 Hinweise |
| Index-Hygiene | Verhältnis 0,42 : 1 (Budget 1,0), jede URL gewollt |
| Weiterleitungen | 251 geprüft und verifiziert, 125 Live-URLs |
| Frontmatter | 174 Dateien – 0 Blocker, 0 Hinweise (YAML-Tiefenprüfung) |
| Metadaten | 145 Dateien – **0 Befunde** |
| Redaktionelle Prüfung | 90 Artikel, 4 Hochrisiko, **4 freigegeben, 0 blockiert** |
| Abhängigkeiten / Manifest | 0 Fehler, 0 Warnungen |

### Regressionssuite (PR-Gate)

`python3 -m unittest discover -s scripts/tests`

* **vorher:** 5 rote Tests (Metadaten M1, FF3, Flesch, Reisekasse, Duplikat)
* **nachher:** 4 geheilt, **1 offen** – das Duplikat-Paar aus Abschnitt 1
  (redaktionelle Entscheidung).

---

## 3. Was der Inhaber entscheiden muss (kein Code)

1. **Release-Scorecard 29/90** (Issue #1193): 59 Live-Artikel blockieren an
   `F4-fachbefund` (Faktenalter) – die Wiedervorlagen sind redaktionell, kein
   Werkzeugdefekt. Der Deploy hängt **nicht** daran.
2. **Duplikat-Paar** (Issue #1289, s. o.): eine Passage in
   `2026-08-14-sparen-im-herbst…` **oder** im versiegelten
   `2026-08-26-kfz-versicherung…` neu formulieren, danach Fassung neu
   entscheiden/versiegeln.
3. **Auslieferungs-SLO misst 403** (Issue #1279): `publication_check.py` ruft
   `https://franksfinanzcheck.de/sitemap.xml` mit einem Nicht-Browser-UA ab;
   Cloudflare antwortet 403. Die Folge ist eine **falsche Diagnose** („CDN"),
   obwohl die Quelle stimmt. Nötig ist eine WAF-Ausnahme für den Messweg
   (Cloudflare-Dashboard, `cloudflare/edge-schutz.md`) **oder** ein
   akzeptierter Beleg-Weg; beides ist Zugangs-/Entscheidungssache.
4. **10 Cornerstone-Kandidaten** (P3, `python3 scripts/cornerstone_wache.py --kandidaten`):
   markieren, welche Artikel eine Themenwelt tragen.
5. **Fünf offene Dependabot-PRs** (#1296–#1299): reguläre Wartung.

---

## 4. Nachvollziehen (Reproduktion)

```bash
hugo version                     # muss "extended" und 0.168.0 zeigen
npm ci --ignore-scripts
npm run build                    # Hugo + Pagefind
npx playwright test              # 184 Tests, Desktop + Mobil
python3 -m unittest discover -s scripts/tests -v
npm run seo:check && npm run sitecheck:check && npm run index:hygiene
python3 scripts/metadaten_wache.py && python3 scripts/ff_inhalts_wache.py
python3 scripts/abgeleitete_register.py --fix   # nur nach Inhaltsänderungen
```

**Ehrlichkeitshinweis:** Alle Zahlen sind lokal gemessen, nicht gegen die
Produktion. Die Produktionsauslieferung selbst ließ sich aus dieser Umgebung
nicht abrufen (kein Netz zu franksfinanzcheck.de).

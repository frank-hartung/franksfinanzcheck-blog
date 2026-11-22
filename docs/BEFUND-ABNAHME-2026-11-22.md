# Befund-Abnahme 22.11.2026 – Abschnitt „Weitere offene Befunde“

**Prüfstand:** 22.11.2026, lokaler Vollauf (Hugo 0.168.0 Extended, Node 22,
Chromium aus dem gepinnten npm-Paket). Kein Live-Deploy, keine Pinterest-,
Google- oder Partner-API erreichbar – externe Nachweise sind als solche
gekennzeichnet.

**Zweck:** Jede Zeile des Abschnitts „Weitere offene Befunde“ wird gegen den
tatsächlichen Stand geprüft. Ergebnis ist entweder ein belegter Fix, ein
belegter Restbefund mit Eigentümer – oder die klare Aussage, dass eine
Maschine ihn nicht heilen kann. Nichts wird „grün“ geredet, nichts ohne
Nachweis geschlossen.

---

## 1. Kurzurteil

| Befund | Stand 22.11. | Beleg | Aktion |
|---|---|---|---|
| #1248 Design-Budget | **behoben** | Tier A+B lokal, Gate `BESTANDEN`, 0 Befunde | Schließt mit dem nächsten geplanten Messlauf (23.11.); Observability verbessert |
| #1152 Web Vitals | **offen, aber anders als gemeldet** | Annotationen: Exit **2** = „nicht messbar“, nicht Exit 1 = „Werte schlecht“ | Ursache wird jetzt klassifiziert; kein Performance-Tuning |
| #1247 Klickmessung | **behoben** | 426 Seiten geprüft, 0 Messlücken | Wache deckt jetzt jede Seite; Befunde nennen die Quelle |
| #1247 Lesbarkeit | **teilweise** | benannter Entwurf jetzt 79,4; **5 Live-Artikel** unter Boden 60 | PR-Gate gegen neue Regressionen; 5 Artikel = Redaktionsaufgabe |
| #448 Pinterest | **Mensch** | Domain-Sperre + 401 | Nichts geändert – Kanal bleibt geparkt |
| #1232–#1234 Recht | **fällig 29.11.** | Prüfaufgaben, keine Defekte | KI-VO-Screening ergänzt; DPF/Partner brauchen Betreiberzugang |
| #1028 KI-Kennzeichnung | **offen, fachlich bestätigt** | unabhängiges Screening 22.11. | Kein Abschlussaufruf; Betreiberfreigabe fehlt |

---

## 2. #1248 – Design-Budget

**Gemeldet:** „Bewertung gegen die Budgets“ rot, „überschrittenes Design-Budget“.

**Prüfung:** Der vollständige Messlauf wurde lokal reproduziert:

```bash
python3 scripts/design_variant_lab.py --lauf alle
node e2e/variant-metrics.mjs --variante alle
python3 scripts/design_variant_lab.py --vergleich
python3 scripts/design_variant_gate.py
```

Ergebnis: 3 Varianten, Tier A und Tier B `ok`, **keine Befunde**,
`Ergebnis: BESTANDEN`, Exit 0. Kontrast 7,53; kleinstes Tap-Ziel 28,8 px;
CLS 0; Lighthouse mobil LCP 1.037–1.062 ms, TBT 56–86 ms; alle
Lighthouse-Kategorien 1,0. Es gibt kein gerissenes Budget.

**Warum das Issue trotzdem offen ist:** Der Fehllauf war der geplante Lauf
vom 16.11. Seither war jeder Lauf grün – aber es waren PR-Läufe, in denen
der Job „Bauen & messen“ absichtlich **übersprungen** wird. Die
Auto-Close-Regel (#809) verlangt einen grünen Lauf **desselben Jobs auf
`main`**. Dieser Beweis kommt mit dem nächsten planmäßigen Lauf am
23.11.2026. Ein manuelles Schließen würde die eigene Regel umgehen.

**Dauerhafte Verbesserung (Code):** `.github/workflows/design-varianten.yml`
sichert das Gate-Urteil jetzt als `gate.txt`, hebt es in die
Lauf-Zusammenfassung und legt es zum Artefakt. Bisher stand im Issue nur
„Schritt fehlgeschlagen“; welches Budget gerissen war, lag ausschließlich
im flüchtigen Log.

---

## 3. #1152 – Web Vitals

**Gemeldet:** „negatives Web-Vitals-Urteil“, Empfehlung „gezielt optimieren“.

**Prüfung:** Die Run-Annotationen sind eindeutig:

```
[failure] Feldmessung nicht durchführbar – ungeprüft ist nicht sauber (Exit 2).
[warning] Laborlauf ohne verwertbares Ergebnis (Exit '2')
```

Exit **2** heißt im Haus: *die Messung hat kein Urteil abgegeben*
(API, Netz, keine CrUX-Daten). Exit **1** wäre „echte Besucher erleben
schlechte Werte“. Es liegt **kein** Seitenbefund vor. Ein Performance-Tuning
der Seiten wäre die falsche Reaktion – es gäbe nichts zu verbessern.

**Dauerhafte Verbesserung (Code):** `scripts/cwv_feld_wache.py` klassifiziert
das Exit 2 jetzt selbst und schreibt die Klasse in Bericht, JSON, Verlauf,
stderr und damit in die Lauf-Zusammenfassung und Annotation:

| Klasse | Bedeutung | Richtiger nächster Schritt |
|---|---|---|
| `DROSSELUNG` | HTTP 429 von PageSpeed Insights | `PSI_API_KEY`-Secret / Google-Kontingent |
| `NETZ` | Timeout/Verbindung | Messweg wiederholen |
| `API` | anderer HTTP-Fehler | Antwortcode/Zielliste prüfen |
| `KEINE_FELDDATEN` | API antwortet, CrUX hat keine Daten | Reichweite/Zielliste; **kein** Performance-Tuning |
| `TEILWEISE` | einige Ziele gestört | nur die gestörten Ziele prüfen |

**Nicht geändert:** Der Exit-Code bleibt fail-closed (C2). Ohne Felddaten
gibt es kein Grün. Wer die Klasse `KEINE_FELDDATEN` sieht, weiß jetzt aber,
dass die Ursache Traffic/Datenlage ist und nicht die Seite.

---

## 4. #1247 – Klickmessung

**Gemeldet:** `/go/strom/` ohne `data-klick`, `data-klick-slug`,
`data-klick-placement` und `?subid=`.

**Prüfung:** Vollständiger Build, dann Wache über **jede** gebaute
HTML-Seite (426 Seiten), nicht nur über die bisher kuratierte Liste:

```
Klick-Messkette: Ampel GREEN · Messlücken: 0
```

Der genannte `/go/strom/`-Anlass ist im aktuellen Bestand nicht mehr
vorhanden; das Gateway reicht die SubID durch, alle CTAs tragen den
Vertrag.

**Dauerhafte Verbesserung (Code):**

* `scripts/click_chain_guard.py` prüft jetzt **alle** gebauten Seiten.
  Vorher waren home, `/pillar/` und Artikel kuratiert – eine neue
  Seitengattung lag außerhalb des Vertrags, ohne dass ein Lauf das gemerkt
  hätte.
* Jeder Befund nennt jetzt die **Seite**. Vorher wurde nur
  „`/go/strom/` ohne …“ gemeldet – ohne Herkunft war das eine Suchaufgabe
  über 400 Seiten.
* Die Anbieterkennzeichnung des Tarifcheck-Programms ist ausdrücklich als
  Pflicht-Dokument markiert (`data-ff-partner-dokument`) und wird nicht
  fälschlich als „roher Partnerlink“ gemeldet. Die Ausnahme hängt an der
  Marke, nicht an der Domain.

---

## 5. #1247 – Lesbarkeit

**Gemeldet:** ein Entwurf unter der Publish-Schwelle (Flesch 55,9).

**Prüfung:**

* Der benannte Entwurf
  `2026-11-16-e-auto-laden-so-senkst-du-deine-stromkosten` liegt heute bei
  **Flesch 79,4** – geheilt.
* Der **Live-Bestand** ist jedoch rot: **5 veröffentlichte Artikel** liegen
  unter dem Haus-Boden 60. Drei davon wurden am 19.11.2026 überarbeitet:

| Artikel | Flesch | lastmod |
|---|---:|---|
| `2026-08-26-kfz-versicherung-vergleich-bis-zu-800-euro-sparen` | 51,5 | 19.11.2026 |
| `2026-08-26-handytarif-vergleichen-2026-guenstige-tarife` | 53,8 | 19.11.2026 |
| `2026-08-26-tagesgeld-zinsen-2026-die-besten-zinssaetze-im-vergleich` | 54,0 | 19.11.2026 |
| `2026-10-12-haushaltskosten-reduzieren-so-gewinnst-du-die-kontrolle` | 59,7 | – |
| `2026-08-12-preisgarantie-gas-so-sicherst-du-dir-guenstige-tarife-fuer-2026` | 59,9 | 07.11.2026 |

* Zusätzlich zwei **Entwürfe** unter 60 (45,9 und 50,1). Der Heiler kann sie
  ohne KI-Antwort nicht heben; sie sind nicht live und blockieren nichts.

**Ursache der Regression:** Das Publish-Gate prüft nur Kandidaten, die
**heute live gehen** (`todays_live_candidates`: Ordner-Präfix heute oder
`date` = heute). Die Überarbeitung eines bereits veröffentlichten Artikels
läuft an dieser Prüfung vorbei. Die Wochen-Wache meldet den Schaden erst,
wenn er schon live ist.

**Dauerhafte Verbesserung (Code):**

* Neu: `.github/workflows/lesbarkeit-live-diff.yml` +
  `scripts/lesbarkeit_diff_wache.py`. Der PR-Lauf prüft genau die
  `content/posts`-Dateien, die der PR ändert:
  * neuer Live-Artikel unter 60 → **blockiert**,
  * Verschlechterung eines Live-Artikels unter 60 → **blockiert**,
  * Altbestand unter 60, der nicht schlechter wird → **kein** Fehlalarm,
  * Entwürfe → frei.
* Schwelle und Messung werden aus `readability_check` importiert (R6, eine
  Zahl). Regressionstests:
  `scripts/tests/test_lesbarkeit_diff_wache.py`.

**Restbefund (Redaktion, nicht Maschine):** Die fünf Live-Artikel tragen
`redaktionelle_pruefung` mit Siegel-Hash und fachlicher Freigabe. Ein
automatisches Umschreiben würde die Freigabe entwerten. Sie müssen
redaktionell neu gefasst und neu versiegelt werden – mit Fakten- und
Quellenprüfung. Reihenfolge nach Abstand zum Boden: 51,5 → 53,8 → 54,0 →
59,7 → 59,9.

---

## 6. #448 – Pinterest

**Gemeldet:** Domain-Sperre und ungültiger Token.

**Prüfung:** Beides ist ein Zustand bei Pinterest, nicht im Repo. Ohne
Kontozugang ist keine Maschine in der Lage, die Freigabe zu erwirken oder
einen Token zu autorisieren. Der Kanal ist korrekt geparkt; ein Pin würde
die Sperre verlängern.

**Aktion:** Keine Codeänderung. Reihenfolge bleibt: Domainfreigabe
(Pinterest-Kontaktformular, `docs/PINTEREST-SPIELBUCH.md`) → danach
`spam_guard.py --domain-unblock` → **erst dann** Token neu autorisieren
(`docs/PINTEREST-TOKEN-RUNBOOK.md`).

---

## 7. #1232–#1234 – Recht und Partner (Frist 29.11.2026)

Das sind Prüfaufgaben, keine nachgewiesenen Verstöße. Maschinell prüfbar ist
nur die Plausibilität der Fristen; die inhaltliche Prüfung braucht Zugang zu
`dataprivacyframework.gov`, zu den Partnerbereichen und eine fachliche
Bewertung.

* **#1232 (DPF GitHub/Cloudflare):** Betreiberaufgabe. Ohne Live-Abfrage
  keine Aussage. Danach ggf. § 2 der Datenschutzerklärung auf AVV/SCC
  umstellen.
* **#1233 (Partnerbedingungen CHECK24/Tarifcheck):** Betreiberaufgabe;
  Stichprobe der Werbekennzeichnung ist zusätzlich maschinell abgesichert
  (Affiliate-Integritäts-Wache, täglich).
* **#1234 (Rechtslage-Screening):** Für die KI-VO wurde das Screening am
  22.11.2026 nachgezogen (siehe `RECHT-UPDATE-REPORT.md`, Nachtrag
  22.11.2026). DPF und Digital-Omnibus bleiben am 29.11. zu prüfen.

**Aktion:** Fristen unverändert lassen; Ergebnisse am 29.11. über den
Workflow „Fristen-Check (Recht)“ dokumentieren und zurücksetzen.

---

## 8. #1028 – KI-Kennzeichnung

**Gemeldet:** Frist 02.12.2026, Rolle und Pflichten prüfen.

**Prüfung:** Ein unabhängiges Screening am 22.11.2026 bestätigt die
Kernaussage des Issues: Art. 50 KI-VO gilt seit 02.08.2026; die
Übergangsfrist nach Art. 111 Abs. 4 (eingefügt durch die Änderungs-VO
(EU) 2026/1744) bis 02.12.2026 betrifft **Anbieter** und die
maschinenlesbare Markierung von Bestandssystemen. Für einen redaktionell
verantworteten Blog ist die Betreiberpflicht nach Art. 50 Abs. 4
(Deepfakes, Texte zu Angelegenheiten öffentlichen Interesses) der
maßgebliche Punkt – mit der dokumentierten Ausnahme bei substanzieller
menschlicher Prüfung und übernommener redaktioneller Verantwortung.

**Wichtig:** Das ist eine Sekundärquellen-Prüfung, keine Rechtsberatung und
kein Anbieternachweis. Das Issue bleibt offen: Es fehlen weiterhin
Systeminventar, Anbieter-/Bildbelege, Live-Abnahme und die ausdrückliche
Betreiberfreigabe nach `docs/KI-TRANSPARENZ-ABNAHME.md` §5.

---

## 9. Geänderte Dateien

| Datei | Änderung |
|---|---|
| `scripts/click_chain_guard.py` | alle Seiten, Seitenname im Befund, Dokument-Ausnahme, Selbsttest |
| `layouts/shortcodes/partner_impressum.html` | Pflicht-Dokument ausdrücklich markiert |
| `scripts/cwv_feld_wache.py` | Klassifikation des Exit 2, Bericht/JSON/Verlauf, Selbsttest |
| `.github/workflows/web-vitals-woche.yml` | Diagnose in Annotation/Summary |
| `.github/workflows/design-varianten.yml` | Gate-Urteil in Summary + Artefakt |
| `scripts/lesbarkeit_diff_wache.py` | neu: PR-Gate gegen Lesbarkeits-Regression |
| `scripts/tests/test_lesbarkeit_diff_wache.py` | neu: Regressionstests |
| `.github/workflows/lesbarkeit-live-diff.yml` | neu: PR-Trigger für das Gate |
| `RECHT-UPDATE-REPORT.md` | Screening-Vermerk 22.11.2026 |
| `scripts/layout_browser_check.js` | Alias-Seiten aus dem Sample, fremder Ursprung als Hinweis, CSP-Beleg nur Hauptrahmen |
| `scripts/tests/test_layout_audit_csp_beleg.py` | Regressionstests für Alias- und iframe-Beleg |

---

## 10. Nachprüfbare Befehle

```bash
# Klick-Messkette über alle Seiten
hugo --destination public && python3 scripts/click_chain_guard.py --public public

# Lesbarkeit: Bestand und neue Regressionen
python3 scripts/readability_check.py --gate-bestand
python3 scripts/lesbarkeit_diff_wache.py --selbsttest

# Web-Vitals-Klassifikation (ohne Netz prüfbar)
python3 scripts/cwv_feld_wache.py --selftest

# Design-Budgets (vollständig, inkl. Browser)
python3 scripts/design_variant_lab.py --lauf alle
node e2e/variant-metrics.mjs --variante alle
python3 scripts/design_variant_gate.py
```

**Grenze dieses Nachweises:** Alle Läufe sind lokal und lesend. Sie
ersetzen weder einen grünen geplanten CI-Lauf auf `main` noch eine
Live-Abnahme oder eine rechtliche Freigabe.

---

## 11. Nachtrag 22.11.2026 – warum der Layout-Audit dauerhaft rot war

Der `layout-audit`-Check war seit dem 21.11. auf **jedem** PR und auf `main`
rot – mit einer Meldung, die scheinbar die Seite beschuldigte:

```
console: Loading the script 'https://static.cloudflareinsights.com/beacon.min.js/…'
violates the following Content Security Policy directive:
"script-src 'self' 'unsafe-inline' https://challenges.cloudflare.com"
```

Die Ursache lag im Messinstrument, nicht im Bau:

1. Die drei „neuesten" Verzeichnisse unter `public/posts/` waren
   **Hugo-Aliase** (`layouts/alias.html` → `<meta http-equiv="refresh">`).
   Der Browser folgte der Weiterleitung auf `https://franksfinanzcheck.de`
   und maß anschließend die **Live-Seite** – inklusive Cloudflare-Beacon,
   Edge-CSP und Fingerprint –, berichtete sie aber unter der
   `127.0.0.1`-URL. Die dortige CSP kennt
   `static.cloudflareinsights.com` nicht; der Konsolenfehler war also echt,
   gehörte aber nicht zu der Seite, die im Befund stand.
2. Zusätzlich zählte der Audit jede `document|iframe`-Antwort als
   CSP-Beleg – auch die eines fremden iframes (Turnstile). Damit wurde aus
   einem „unbelegten" Hinweis wieder ein harter Befund.

Behoben: Alias-Seiten fallen aus dem Sample (Startseite, Artikel und
Risiko-Seiten), der Hauptrahmen muss auf dem geprüften Ursprung bleiben
(sonst nur Hinweis, kein Befund), und CSP-Belege stammen ausschließlich aus
der Antwort des Hauptrahmens. `scripts/tests/test_layout_audit_csp_beleg.py`
hält beides fest.

**Offener Betriebspunkt (nicht im Repo lösbar):** Die Edge-Transform-Rule
in Cloudflare liefert weiterhin die alte CSP ohne
`static.cloudflareinsights.com`, obwohl `static/_headers` und
`cloudflare/edge-schutz.md` (A1) sie seit dem 21.11. führen. Solange die
Regel im Dashboard nicht nachgezogen ist, blockiert der Browser den
Beacon der Web-Analytics – die Messung selbst bleibt davon unberührt.

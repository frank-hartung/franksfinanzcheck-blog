# Vier rote Regressionstests – Ursachen, Heilung, Belege

Stand: 28.10.2026 · Branch `arena/cb2052bb-franksfinanzcheck-blog` (Basis `1e61f6d8`)
Anlass: „Wenn du willst, nehme ich mir die vier Regressionstests als eigenen,
kleinen Vorgang vor" – Umsetzung auf dem Niveau eines Profi-Vorgangs.

## Worum es ging

Der Job `regression` (`publication-reliability-tests.yml`, läuft bei jedem PR)
stand rot. Vier Tests waren betroffen; einer davon hatte sich zwischenzeitlich
von selbst erledigt. Kein Test wurde abgeschwächt, keine Freigabe erfunden –
jeder Befund wurde an seiner Ursache geheilt und mit einem Befehl belegt, den
jede:r nachfahren kann.

| # | Test | Befund | Ursache | Heilung |
|---|---|---|---|---|
| 1 | `test_inhalts_register.test_register_ist_aktuell` | Register veraltet (`anzahl: 18`) | Artikel vom 24.10. wurde nicht ins Register aufgenommen | `scripts/fachpruefung_register.py` neu erzeugt (`anzahl: 19`) |
| 2 | `test_reserve_artifacts.test_current_snapshot_is_whole_and_editorially_valid` | SHA-256 des Ökostrom-Entwurfs passte nicht mehr zum Zertifikat | Redaktioneller Eingriff am Entwurf (`ad0139d3`) | `reserve_recert.py --fix` – echte Nachmessung, `5/6` wieder belegt |
| 3 | `test_versicherungs_cluster_verlinkung.test_jeder_live_artikel_ist_im_pillar_verlinkt` | Wohngebäude-Vergleich live, im Pillar aber nicht verlinkt | Am 27.10. entlinkt, weil die Ziele Entwürfe waren | Link in der „Cluster-Reihenfolge" zurückgeholt |
| 4 | `test_konsolidierung.test_der_zwilling_hat_keine_belegte_nachfrage` | Aussage „kommt in den Top-Seiten nicht vor" | GSC-Lauf `35719ca1` (28.10.) liefert jetzt 4 Impressionen | Test auf die Eigenschaft umgestellt (Seite 1 vs. Restnachfrage) |
| (5) | `test_lcp_image_optimizer` | war auf `3f67b54` rot | Manifest war veraltet | bereits auf `main` geheilt – hier **nicht** angefasst |

Ergebnis: `python3 -m unittest discover -s scripts/tests` → **4244 Tests, 0
Fehlschläge** (4 übersprungen, Hugo-abhängig). Vorher: 4 Fehlschläge.

## Ein Commit, zwei Folgen: `ad0139d3`

Der Bot-Commit „chore: Pinterest-Selbstheilung + Report" (28.10., 10:42Z) hat
zwei Artikel angefasst und dabei drei Manifeste neu erzeugt
(`covers_manifest.json`, `fcp_images.json`, `lcp_images.json`). Das hat
gleichzeitig:

* **Test 5 geheilt** – die neuen LCP-Werte passen jetzt zur Quelle, der
  Preload-Vertrag stimmt wieder;
* **Test 2 erzeugt** – einer der beiden Artikel war der Reserve-Entwurf
  `2026-10-28-oekostrom-anbieter-wechseln-sicher-gruen-und-bezahlbar`. Zwei
  Zeilen Frontmatter (`keywords` von 5 auf 3 gekürzt) plus ein
  Affiliate-Transparenzabsatz genügen, um den Byte-Nachweis zu entwerten.

Das ist genau der Nachweis-Engpass, für den `reserve_recert.py` gebaut wurde:
Content-Pflege ist richtig, sie macht aber alte Zertifikate ungültig. Wer das
nicht nachzieht, meldet fachlich fertige Entwürfe als „nicht bereit".

## Befund 1 – Fachprüfungs-Register war veraltet

Beim Lauf am 24.10. ging der Artikel
`2026-10-24-etf-sparplan-starten-schritt-fuer-schritt-zum-monatlichen` live
(Pillar `frugalismus`, **Risikoklasse `erhoeht`**). Das Register ist die Liste
der Aussagen, die ein Mensch prüfen muss, bevor so ein Text als fachlich
freigegeben gilt – es wird aus dem Bestand erzeugt und muss deshalb bei jedem
neuen Artikel mitwandern.

Heilung: `python3 scripts/fachpruefung_register.py` (kein Handedit). Ergebnis:

* `anzahl: 18` → `19`
* neuer Eintrag mit 12 Zahlen-Fundstellen, `status: ausstehend`,
  `pruefer: null` – **keine Freigabe**, nur die Aufgabe dazu.

Beleg: `python3 scripts/fachpruefung_register.py --check` → „✅
Fachprüfungs-Register aktuell" (Exit 0).

## Befund 2 – Reserve-Zertifikat zeigte auf alte Bytes

Das Zertifikat `data/reserve-readiness.json` gilt ausdrücklich nur für genau
die Bytes, die am Gate gemessen wurden (sha256). Nach `ad0139d3`:

| Feld | vorher | nachher |
|---|---|---|
| `sha256` | `cc5dd94d…` | `026a4df7…` |
| `score` | 0.952 | 0.956 |
| `spelling` | 0.94 | 0.96 |
| `flesch` | 61.9 | 61.6 |
| `measured_at` | 2026-10-28T10:25:59Z | 2026-10-28T11:41:48Z |
| `ready` (Pool 6) | 5 | 5 |
| `measurement.kind` | `full` | `partial` (nur 1 Kandidat neu gemessen) |

Dazu ein `recert`-Block mit Zeitpunkt, erneuertem Slug und Werkzeug
(`scripts/reserve_recert.py`). Der Entwurf ist weiterhin gate-fertig, das
Publish-Gate meldete beim Lauf „würde geheilt (Score 83) – Keyword nicht in:
Erster Absatz"; `--fix` hat **nichts** am Artikel geändert, nur neu gemessen.

### Werkzeugmangel ist kein Befund – und keine Ausrede

`reserve_recert.py --fix` ist fail-closed: ohne vollständige Messkette (`hugo`
**und** `hunspell` + `de_DE`) schreibt es nichts und endet mit Exit 3. Grund
steht im Skript: `quality_score` wertet eine nicht lauffähige Rechtschreibprüfung
als „unbekannt" (`spelling = 0.5`) und drückt **jeden** Artikel bis zu 0.10
Punkte nach unten – quer unter die 0.85-Schwelle. Ein Lauf ohne Hunspell hätte
am 30.09.2026 acht gesunde Kandidaten als unreif ausgebucht.

In dieser Umgebung fehlte `hunspell`, und `apt-get` kommt nicht ins Netz
(nur npm/pypi/github erreichbar). Die Kette wurde deshalb **echt gebaut**, nicht
umschifft:

* `hunspell` 1.7.2 aus dem Quelltext (`hunspell/hunspell`, Tag `v1.7.2`) mit
  `g++` kompiliert und nach `/usr/local/bin/hunspell` installiert,
* deutsches Wörterbuch `de_DE_frami` aus `LibreOffice/dictionaries` (dieselbe
  Quelle, aus der auch das Debian-Paket `hunspell-de-de` stammt) nach
  `/usr/share/hunspell/de_DE.{aff,dic}`,
* Probe wie im Skript: `printf 'Haushalt\nRücklagen\nprüft\nbehält\nFheler\n' |
  hunspell -i UTF-8 -d de_DE -l` → genau `Fheler`. Damit ist die Probe aus
  `messkette_rechtschreibung()` erfüllt, das Werkzeug misst wirklich.

Kein Zertifikat wurde „trotzdem" geschrieben, kein `--withdraw-invalid` als
Abkürzung benutzt, kein Wert von Hand eingetragen.

Belege: `reserve_recert.py --selftest` → „✅ Selbsttest ok", `--check` → „✅
Zertifikat und Entwürfe stimmen überein (kein Drift)", `reserve_artifacts.py
--check` → „✅ Reserve-Snapshot vollständig".

## Befund 3 – Live-Artikel ohne Pillar-Link

Der Wohngebäude-Vergleich ist live (`draft: false`, `date: 2026-10-28`), der
Versicherungs-Pillar verlinkte ihn nicht mehr: Am 27.10. waren alle vier
Cluster-Artikel Entwürfe, die Links liefen ins Leere (Befund W11) und wurden
entlinkt – richtig, solange die Ziele Entwürfe sind. Genau dieser Übergang ist
die Lücke, und `test_versicherungs_cluster_verlinkung.py` ist die Wiedervorlage.

Heilung: Der Artikel steht jetzt in der „Cluster-Reihenfolge"
(`content/pillar/versicherungen/index.md`) als echter, wirksamer Link statt als
Text – mit einem Satz, der erklärt, warum die Klausel wichtiger ist als der
Beitrag. Die Wache prüft weiter beide Richtungen:

* live → muss verlinkt sein (dieser Fall),
* Entwurf → darf **nicht** verlinkt sein (sonst sofort wieder vier tote Ziele).

Beleg: 6 Tests grün, `scripts/link_guard.py` → „🎉 Alle internen Links
verifiziert – keine Totstellen". Der Vorgang ist in
`GSC-OPTIMIERUNGSPLAN-2026-10-27.md`, Abschnitt 14.4 als erledigt vermerkt.

## Befund 4 – ein Test, der das Wetter maß

`test_der_zwilling_hat_keine_belegte_nachfrage` hielt eine Momentaufnahme vom
19.10.2026 fest: die zweite P2-Seite kam in den Top-Seiten nicht vor
(0 Impressionen). Der GSC-Lauf vom 28.10. (`35719ca1`, „Leistungsdaten
2026-10-28") zeigt sie jetzt mit **4 Impressionen auf Position 39,25**. Die
alte Aussage ist damit falsch – nicht der Code.

Zwei Fehler steckten in dem Test, und beide sind geheilt:

1. **Er nagelte eine Tageszahl fest.** Jede GSC-Lieferung verschiebt sie; ein
   Test, der montags rot wird, weil der Bot Impressionen dazugezählt hat, misst
   das Wetter statt den Vertrag. Er prüft jetzt die Eigenschaft: belegt ist
   belegt (eine Zahl > 0), und die Seite liegt weiterhin weit hinter Seite 1
   (`position > 10`, `impressionen < 10`) – also keine Nachfrage, aus der ein
   Zusammenführen folgen würde. Verschiebt sie sich auf Seite 1, wird der Test
   rot **und dann ist das die richtige Nachricht**.
2. **Dieselbe Falle beim Nachbarn.** `test_nachfrage_ist_eine_zahl_nicht_eine_meinung`
   pinnte `impressionen == 1`. Behalten hat er den Punkt, um den es geht: die
   Quelle ist `top_seiten_28t.json` und der Wert ist eine Zahl > 0 – ein Gefühl
   wäre kein Beleg.

Was **nicht** passiert ist: Das Urteil selbst (Regel F, „keine Konsolidierung
der beiden P2-Seiten") bleibt unverändert falsch-positiv-frei, weil es schon an
der fehlenden Suchabsicht kippt (Titelüberschneidung 0, siehe Bericht §7.3).
Eine belegte Nachfrage von 4 Impressionen auf Position 39 ist keine Nachfrage.

## Was ausdrücklich nicht gemacht wurde

* Kein Test „grün geredet" (kein `skip`, keine gelockerte Schwelle, kein
  `assertTrue(True)`).
* Kein Zertifikat ohne Messung geschrieben, kein Hunspell-Ersatz als Attrappe.
* `test_lcp_image_optimizer` nicht angefasst – der Befund war auf `main` schon
  geheilt; ihn erneut zu „reparieren" wäre Arbeit an einem grünen Test.
* Keine Kerndatei neu versiegelt: `integrity_guard.py --gate` ist grün (50
  Kerndateien, HEAD `1e61f6d8`), die geänderten Dateien sind keine Kerndateien.

## Reproduktion (alles offline, ohne Netzzugang außer PyPI)

```bash
python3 scripts/fachpruefung_register.py --check        # 0 = aktuell
python3 scripts/reserve_recert.py --check               # 0 = kein Drift
python3 scripts/reserve_recert.py --selftest            # Sabotageschutz
python3 scripts/reserve_artifacts.py --check            # Snapshot vollständig
python3 -m unittest scripts.tests.test_versicherungs_cluster_verlinkung
python3 -m unittest scripts.tests.test_konsolidierung
python3 -m unittest discover -s scripts/tests           # 4244 Tests
npm run test:redos                                      # 98 Tests (ReDoS)
python3 scripts/link_guard.py                           # interne Links
python3 scripts/metadaten_wache.py                      # 107 Dateien, 0 Befunde
python3 scripts/integrity_guard.py --gate               # 50 Kerndateien
```

`reserve_recert.py --fix` braucht `hugo` im PATH **und** eine funktionierende
`hunspell`-Kette (`apt-get install -y hunspell hunspell-de-de` bzw. der
Quellbau oben). Fehlt eines davon, endet das Skript mit Exit 3 und schreibt
nichts – das ist die gewollte Sperre, kein Fehler.

## Offene Punkte

Keine aus diesem Vorgang. Der nächste der drei verbleibenden
Versicherungs-Artikel wird von `test_versicherungs_cluster_verlinkung.py`
gemeldet, sobald er live geht; die Reserve-Drift meldet `reserve_recert.py
--check` (läuft im Bot-Watchdog täglich).

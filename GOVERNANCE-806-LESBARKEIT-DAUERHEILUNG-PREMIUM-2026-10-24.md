# Governance-Report #806 · Lesbarkeit, Schreiber-Garantie und saubere Datenlagen – Dauerheilung auf Highend-Agentur-Niveau

**Datum:** 24.10.2026
**Auslöser:** Premium-Governance-Lauf vom 19.10.2026, Issue **#806** (`governance`, Ampel **AMBER**, Fingerabdruck `63facd5d7c6d`). Zwei Befundarten: die **Lesbarkeits-Wache (Bestand)** – zwei Entwürfe unter der Publish-Schwelle 60 – und unter **„Datenlagen & Status“** zwei INFO-Zeilen mit **„Datenlage offen“**.
**Stand vorher:** zwei Entwürfe unter der Schwelle (Flesch **54,2** und **54,9**), Bestands-Gate **AMBER**; zwei Datenlagen-Zeilen, deren Messquelle es nicht (mehr) gab.
**Stand nachher:** **0** Entwürfe unter der Schwelle (29 Entwürfe, Minimum **60,0**), Bestands-Gate **GREEN** (66 Live-Artikel, Ø Flesch **65,3**, kein Live-Artikel unter Floor 55); **0** Datenlagen-Zeilen ohne Erzeuger; Governance-Vertrag **40 Regeln grün**.

Dieser Bericht ersetzt `GOVERNANCE-806-ABSCHLUSS-LESBARKEIT-2026-10-22.md`. Jener Nachweis hat den **Bestand** geheilt (die zwei Entwürfe lagen am 22.10. bei 82,0 und 72,4). Er hat aber die **Ursache** nicht beseitigt: derselbe Befundstyp war drei Wochen später wieder da, und die Wachen, die ihn hätten verhindern müssen, hielten sich für grün. Was folgt, heilt die Ursache.

---

## 1. Forensische Ursachenkette (warum derselbe Befund in zwei Wochen wiederkam)

1. **Zwei Schreiberbahnen maßen nicht.** Die Lehre aus #612 und #712 („Wer schreibt, muss messen, was über ihn entscheidet“) war nach C36 nur an **eine** Rolle gehängt worden: `news_writer.py` hatte die Sicherung `lesbarkeit_sichern()`. Die Hauptproduzenten der langen Premium-Artikel (`claude_writer.py`) und die Werkbank-Recycling-Bahn (`poppy_repurpose.py`) schrieben unvermessen in die `content/posts/`-Ablage. Beide Entwürfe des Reports #806 stammen aus genau dieser Lücke – sie waren im Issue-Body nie namentlich als „Claude-Artikel“ markiert, weil der Generator sie nicht markieren konnte.
2. **Der Vertrag hätte es sehen müssen – hatte aber eine tote Zone.** Der Selbsttest von `scripts/governance_contract.py` **urteilte nur an einer einzigen Stelle** der Datei. Proben, die vor dieser Stelle arbeiteten, liefen ins Leere: Der Lauf meldete „bestanden“, ohne dass eine einzige Probe geprüft worden war. Nach der Reparatur (genau **eine** Urteilsstelle, unmittelbar vor der Erfolgsmeldung) meldete derselbe Lauf **sieben echte Verstöße** – aus C35, C36 und C37. Sieben Zusagen des Hauses waren unerfüllt, ohne dass jemand es merkte. Der Selbsttest war das sicherste Werkzeug im Haus und das blindeste.
3. **Ein Schritt ohne Erzeuger sieht nie.** Die beiden Zeilen „Datenlage offen“ im Report #806 kamen aus Gate-Schritten, deren Messquelle es nicht (mehr) gab. Ein solcher Schritt meldet **immer** „Datenlage offen“: er sieht nie, wird nie grün und beendet die Meldung nie. Das ist die Report-Form von „Deckung ohne Wirkung“ – im Report selbst, wo der Leser sie für einen aktuellen Zustand hält.
4. **Die Wache schrieb ihren Befund in die Datei, die sie belegt.** Die Fremdmessung-Sperre zitiert die Fundstelle im Klartext. Ihre Meldung landete im Vertrags-Report `docs/GOVERNANCE-KONTRAKT.md` – einer Datei, die die Sperre selbst wiederum scannt. Der Befund erzeugte damit die Spur, die er verbietet: eine Rückkopplung, die sich selbst speist und nie wieder still wird. Beim Bau der neuen Regel C42 hat die Sperre den Autor dieser Arbeit beim Namen erwischt; die Redaktion des Regeltextes musste zweimal zurück.
5. **Kein Bericht, was der Schreiber tat.** `claude_writer.py` und `poppy_repurpose.py` meldeten ihr Ergebnis als Text im Log, ohne Messwert und ohne Schwelle. Niemand konnte am Ergebnis erkennen, ob ein Artikel die Publish-Schwelle verfehlt hatte, bevor drei Wachen Wochen später ihn einsammelten.

---

## 2. Stand des Bestands (gemessen am 24.10.2026, nicht behauptet)

| Entwurf | Im Issue vom 19.10. | Am 22.10. geheilt | Heute gemessen |
|---|---:|---:|---:|
| `2026-10-19-urlaubskasse-clever-aufbessern/index.md` | 54,2 | 82,0 | **82,0** |
| `2026-10-16-dns-server-aendern-fuer-schnelleres-internet/index.md` | 54,9 | 72,4 | **72,4** |

`scripts/readability_check.py --gate-bestand` → **GREEN**: 66 Live-Artikel (Ø **65,3**), kein Live-Artikel unter Floor 55, **29 Entwürfe, 0 unter der Publish-Schwelle 60** (Minimum exakt 60,0). Die Heilung selbst ist in `GOVERNANCE-806-ABSCHLUSS-LESBARKEIT-2026-10-22.md` dokumentiert; dieser Bericht handelt vom Bau, der verhindert, dass die nächsten zehn Entwürfe denselben Weg gehen.

---

## 3. Systemische Dauerheilung (Code, Kette, Verträge)

| Ebene | Ort | Zusage |
|---|---|---|
| **Hausgarantie** | `scripts/lesbarkeit_schreiber.py` (neu) | Eine Garantie für **alle** Schreiberbahnen: messen über die SSOT (`readability_check.NEW_FLESCH_MIN` – importiert, keine eigene Zahl), heilen über die Stufe A des **versiegelten** `lesbarkeit_heiler.py` (als Bibliothek), prüfen am Tor T1–T4 (`verifiziere`), und **ehrlich** melden, wenn die deterministische Stufe nicht reicht: „deterministische Stufe reicht nicht, redaktionelle Nachsorge nötig“ samt Aufrufhinweis. Der CTA-/Disclaimer-Tail bleibt außerhalb von Messung und Heilung. Ein eigener `--selftest` beweist die Wirkung an der Heiler-Probe. |
| **Produzenten** | `scripts/news_writer.py`, `scripts/claude_writer.py`, `scripts/poppy_repurpose.py` | Alle drei rufen `lesbarkeit_schreiber.sichern()` **vor** `write_post` und geben Status und Messwert in ihre eigene Ausgabe durch. `news_writer` delegiert dabei an die Hausgarantie (keine zweite Wahrheit). |
| **Vertrag (Lesbarkeit)** | `scripts/governance_contract.py` | **C41 „Der Schreiber misst vor dem Schreiben“**: SSOT-Bindung ohne eigene Schwelle, Heiler als Bibliothek, **echter** Tor-Aufruf im Funktionsrumpf (nicht das Wort), die drei Bahnen samt Aufruf **vor** `write_post`, Regressionstest vorhanden, Modul-Selbsttest im vertraglichen Minimum. Fünf Sabotage-Proben (a–e) beweisen die Wirkung. |
| **Vertrag (Datenlagen)** | `scripts/governance_contract.py` | **C42 „Jeder Gate-Schritt hat einen lebenden Erzeuger“**: Jeder Report-Schritt des Governance-Gates braucht einen benannten Erzeuger, dessen Skript noch existiert; Schritte ohne Report sind namentliche Ausnahmen (`C42_OHNE_ERZEUGER`). Heute: 12 Schritte, davon 10 mit Report – **alle 10 mit existierendem Skript**. Drei Sabotage-Proben (Schritt ohne Signatur, Signatur ohne Skript, Schritt ohne Report und ohne Ausnahme). |
| **Selbsttest-Reparatur** | `scripts/governance_contract.py` | Die tote Zone ist beseitigt: genau eine Urteilsstelle vor der Erfolgsmeldung, keine frühe. Der Selbsttest prüft jetzt, was er behauptet – und meldete dabei sieben echte Hausverstöße, die einzeln behoben wurden. |
| **Rückkopplung** | `scripts/fremdmessung_sperre.py` | Die Sperre **schwärzt** den Namen des entfernten Dienstes in ihren Fundstellen (Pfad, Zeile und Klasse bleiben lesbar), und der vollständig neu geschriebene Vertrags-Report `docs/GOVERNANCE-KONTRAKT.md` ist erklärte generierte Zone. Ein Befund kann seine eigene Spur nicht mehr erzeugen. |
| **Dauervorgabe** | `CLAUDE.md` | Zwei neue Abschnitte („Wer schreibt, misst vor dem Schreiben“, „Jeder Schritt hat einen lebenden Erzeuger“) und eine Ergänzung der Fremdmessungs-Vorgabe: Der Regeltext benennt den Tatbestand, nicht die Tagesform. |
| **Tests** | `scripts/tests/test_lesbarkeit_schreiber.py` (neu, 9), `scripts/tests/test_news_writer_lesbarkeit.py` (6) | Regressionstests sichern SSOT-Bindung, Byte-Identität bei erfüllter Schwelle, Heilung oberhalb der Schwelle, ehrliche Restlücke, Modul-Selbsttest sowie die Verdrahtung aller drei Schreiber **vor** `write_post`. `npm run test:lesbarkeit` fährt Heiler-Selbsttest, Schreiber-Selbsttest und beide Testmodule. |

---

## 4. Beweise (alle Befehle am 24.10.2026 im Repo-Stand dieses Branches ausgeführt)

| Befehl | Ergebnis |
|---|---|
| `readability_check.py --gate-bestand` | ✅ **GREEN** – 66 Live-Artikel Ø **65,3**, kein Live-Artikel unter Floor 55, **29 Entwürfe, 0 unter Publish-Schwelle 60** |
| `readability_check.py --json` | ✅ 66 live / 29 Entwürfe / Minimum Entwurf **60,0**; die beiden #806-Entwürfe **82,0** und **72,4** |
| `readability_check.py --selftest` | ✅ Schwellen, Shortcode-Stripping, Trennung von Live-Bestand und Entwürfen |
| `lesbarkeit_heiler.py --selftest` | ✅ Wirkungsprobe und Tor T1–T4 weisen Sabotage ab |
| `lesbarkeit_schreiber.py --selftest` | ✅ Schwelle erfüllt / Stufe A heilt / ehrliche Restlücke – „SSOT-Schwelle · Stufe A + Tor T1–T4 · ehrliche Restlücke“ |
| `poppy_repurpose.py --selftest` | ✅ |
| `python3 -m unittest scripts.tests.test_lesbarkeit_schreiber` | ✅ **9 / 9** |
| `python3 -m unittest scripts.tests.test_news_writer_lesbarkeit` | ✅ **6 / 6** |
| `python3 -m unittest discover -s scripts/tests` | ✅ **3558 Tests**, 0 Fehlschläge; 12 Fehler stammen aus `test_faktenfrische_763` (der Artikel wurde umbenannt) und `test_newsletter_digest` (fehlende getrennte Schlüsselrollen) – auf dem Basisstand **identisch**, ohne Bezug zu dieser Änderung |
| `governance_contract.py --selftest` | ✅ **C1–C42** mit Kunstbefunden (Sabotage-Proben a–e für C41, drei für C42) |
| `governance_contract.py --quick --md docs/GOVERNANCE-KONTRAKT.md` | ✅ **alle 40 Regeln erfüllt** (C24/C31 gehören anderen Verträgen) |
| `governance_contract.py` (Voll-Audit) | ✅ **40 Regeln**, jede in beide Richtungen geprüft |
| `fremdmessung_sperre.py --selftest` | ✅ 16 Anbindungs-Merkmale einzeln, redaktionelles Wort erlaubt, Ausnahmen begründet und alternd |
| `fremdmessung_sperre.py` (Live) | ✅ **keine Spur** des entfernten Dienstes – weder in Quelltext noch im gebauten Baum |
| `manifest_guard.py` | ✅ **GRÜN** – 13 Dateien, keine Befunde |
| `wachen_vertrag.py` | ✅ **323 Skripte** geprüft, **0 Funde** |
| `integrity_guard.py --check` | ✅ Siegel gültig und verkettet, 50 Kerndateien gelockt, 6 kritische Knoten gesperrt |

---

## 5. Ehrliche Restlücke

- **Zwei Kommentar-Altlasten in gesiegelten Dateien.** `layouts/_default/_markup/render-link.html` und `scripts/check24_links.yaml` tragen je eine Zeile aus der Zeit vor der Entfernung des Reichweiten-Dienstes. Sie stehen als begründete Ausnahme in der Sperre (`ERLAUBT`). Ihre Bereinigung verlangt die **menschliche Neu-Signatur** (`integrity_guard.py --set-current`) – ein Agent darf sie nicht ersetzen, das Siegel weist jede stille Änderung zurück. Der Weg ist im Runbook `docs/ANLEITUNG-FREMDMESSUNG-SPERRE.md` (Zeilen 91–103) beschrieben: Kommentare bereinigen, neu signieren, dann die beiden Ausnahmen löschen. **Das ist eine Aufgabe des Inhabers, kein Rest der Automatik.**
- **Der Report im Issue-Body ist ein Snapshot.** Die beiden Zeilen „Datenlage offen“ stammen vom 19.10.2026 und beschreiben keinen heutigen Zustand: Die Schritte, die sie erzeugt haben, gibt es nicht mehr. Wer einen Report liest, prüft Laufdatum und Fingerabdruck – nicht die Zeile von damals.
- **Der Rollenlauf mit Modellen bleibt CI-Sache.** Die KI-Pfade der Rolle „Claude“ brauchen `GROQ_API_KEY`/`GEMINI_API_KEY`; lokal geprüft sind sie über die Attrappen-Proben des Heiler-Selbsttests und die neuen Regressionstests der Schreiber-Garantie.
- **Die harte Restlücke der Heilung bleibt ehrlich benannt.** Reicht die deterministische Stufe A nicht, meldet der Schreiber das und übergibt an `lesbarkeit_heiler.py --entwuerfe` (täglich in der Content-Engine). Ein Artikel, der dort liegen bleibt, ist kein Systemfehler, sondern eine redaktionelle Aufgabe – er steht dann aber **nicht** mehr still.
- **Zwei Testmodule sind unabhängig von dieser Arbeit rot.** `test_faktenfrische_763` erwartet einen Artikel unter einem older Namen (`2026-10-14-strategisch-sparen-so-kannst-du-deine-reisekasse-fuellen`), der im Bestand unter `2026-10-24-…` liegt; `test_newsletter_digest` braucht die getrennten Schlüsselrollen des Workers, die nur in CI gesetzt sind. Beide Fehler treten auf dem Basisstand **identisch** auf – sie sind kein Befund aus #806, gehören aber zu den offenen Enden des Hauses.
- **Der wöchentliche Governance-Lauf wurde nicht von hier ausgelöst.** Ein manueller Dispatch des Premium-Governance-Workflows auf dem Session-Branch wird von GitHub mit HTTP 403 („Resource not accessible by integration“) abgewiesen. Die Belege oben sind deshalb lokal und reproduzierbar; der nächste reguläre Wochenlauf bestätigt den Stand am Issue.

---

## 6. Was jetzt dauerhaft verhindert, dass der Befund zurückkommt

1. **Kein Schreiber kann den Ausschuss mehr erzeugen:** Alle drei Bahnen messen vor dem Schreiben und heilen deterministisch, bevor der Text in die Ablage geht. Der nächste unter der Schwelle gefangene Entwurf entsteht nicht mehr im Generator.
2. **Eine Zusage, eine Zahl, eine Implementierung:** Die Schwelle kommt importiert aus `readability_check`, die Heilung aus dem versiegelten Heiler, der Nachweis aus dem Tor. Es gibt keine zweite Messung und keine zweite Satz-Zerlegung (Lehre #585).
3. **Der Vertrag prüft wieder, was er behauptet:** Die tote Zone im Selbsttest ist beseitigt; Sabotage-Proben für C41 und C42 halten die Zusagen fest. Fällt eine Zusage, wird der Selbsttest im CI rot – nicht erst der nächste Report.
4. **Kein Schritt meldet mehr ohne Erzeuger:** Jeder Report-Schritt braucht ein lebendes Skript; ein Schritt ohne Quelle ist ein Befund (C42), kein INFO.
5. **Keine Wache erzeugt ihre eigene Spur:** Die Fremdmessung-Sperre schwärzt ihre Fundstellen, und der Vertrags-Report ist generierte Zone. „Datenlage offen“ kann sich nicht selbst reproduzieren.
6. **Die Regel steht im Haus, nicht nur im Report:** `CLAUDE.md` trägt beide Dauervorgaben; ein neuer Schreiber und ein neuer Gate-Schritt treffen auf eine geschriebene Regel statt auf eine Absicht.

**Schlussfolgerung:** Der Befund aus #806 ist an beiden Stellen behoben – im Bestand (0 Entwürfe unter der Publish-Schwelle) und in der Technik (Garantie statt Symptomheilung, Vertrag mit Sabotage-Proben, erzeugende Schritte, keine Rückkopplung). Was bleibt, ist eine menschliche Unterschrift: die Bereinigung der beiden gesiegelten Kommentarzeilen zum nächsten Siegel-Termin.

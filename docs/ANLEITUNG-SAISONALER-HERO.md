# Saisonaler Hero: Betrieb und Störungsbehebung

Stand: 30.10.2026 · Anlass: [Issue #891](https://github.com/frank-hartung/franksfinanzcheck-blog/issues/891)

## Was der Lauf tut

Der tägliche Workflow `Saisonaler Hero-Refresh (Agent Reach + KI-Feinschliff)` darf ausschließlich `hero_title` und `hero_lead` der aktiven Saison ändern. Layout, Links, CTAs und die übrigen Saisondaten bleiben unberührt. Eine bestehende, geprüfte Fassung bleibt bei einem Ausfall erhalten; es gibt keinen erfundenen KI- oder Fakten-Fallback.

1. Agent Reach erzeugt einen Tagesbrief **und** seine JSON-Beilage. Beides muss zum UTC-Stichtag passen; die Beilage muss eine Agent-Reach-Version und mindestens einen fehlerfrei abgerufenen Kanal melden. Ein fehlerfreier Abruf garantiert keine relevanten Treffer. Nur in den Treffertexten der JSON-Beilage gefundene, bereits kuratierte Themenwörter gelangen in den Prompt; Quellnamen und URLs zählen nicht. Web-Auszüge fehlen in der Beilage und werden dafür nicht ausgewertet. Rohmeldungen werden nicht übernommen; Brief und JSON erhalten getrennte SHA-256-Nachweise.
2. Die kostenlosen Anbieter werden in der bestehenden Reihenfolge Groq → NVIDIA → Cloudflare → Gemini geprüft. Nicht nur Transportfehler, sondern auch unvollständige, unlesbare oder fachlich verworfene Antworten führen zum nächsten verfügbaren Anbieter. Es gibt höchstens drei Runden, begrenzte Timeouts und eine Pause zwischen den Runden. Der Report nennt jeden verwendeten Anbieter, das Modell und die technische Fehlerklasse, aber weder Schlüssel noch rohe verworfene Antworten. „Schlüssel vorhanden“ bedeutet nicht, dass dieser gültig ist oder das Kontingent reicht.
3. Der Prompt nennt die tatsächlich geprüften Titel-Wortteile und die ausgeschlossenen Floskeln ausdrücklich; Korrekturauflagen und sämtliche bestehenden Prüfungen bleiben aktiv. Gemini erhält ein höheres Ausgabebudget (8192 Tokens), weil Denk- und Antworttokens gemeinsam zählen können. Auch damit bleibt `MAX_TOKENS` ein Fehler und ist kein Veröffentlichungsnachweis. Der Prompt fordert ein vollständiges JSON-Objekt mit `title` und `lead`. Eindeutige `TITLE:`/`LEAD:`-Antworten mit Zeilenumbrüchen bleiben kompatibel. Doppelte Felder, zusätzliche Absätze/Erklärungen und unvollständiges JSON werden verworfen. Zusätzlich muss der Provider einen erfolgreichen Finish-Code melden; Denkspuren werden bei Gemini nicht als Antwort übernommen.
4. Der Kandidat muss den SEO-/GEO-Vertrag, die Faktenbremse, Neuheit gegenüber der aktuellen Fassung und der Historie sowie die Startseiten-Quellwache bestehen. Die maschinellen Wort- und Formatprüfungen sind **keine vollständige Faktenprüfung**: Sie erkennen insbesondere Ziffern, Prozentzeichen, einige Zahlwörter und URLs, können aber nicht jede mögliche unbelegte Behauptung erkennen.
5. Erst wenn auch Hugo und beide Render-/Design-Gates erfolgreich sind, darf der Workflow Hero, State und Historie zusammen committen. Bei fehlendem Render-Nachweis setzt er diese auf den Ausgangsstand zurück und dokumentiert den Ausfall. Auch bei einem unerwarteten Abbruch oder einem Fehler beim Rollback lässt die Commit-Stufe keine ungeprüften Hero-Daten oder Erfolgs-Fingerprints durch. Recherche und ein sicher dokumentierter Fehlerzustand dürfen weiterhin gesichert werden.

Die Rotation bleibt bei 21 Tagen; nach drei aufeinanderfolgenden Ausfällen oder ab 35 Tagen Alter wird ein Kettenausfall rot. Ein gescheiterter, manuell erzwungener Lauf wird am nächsten Tag erneut versucht, selbst wenn die bisherige Fassung noch jung ist. Auch ein redaktionell geänderter, geprüfter Hero löscht eine laufende Ausfallserie nicht automatisch; die KI-Kette wird erneut versucht. Ohne offene Ausfallserie kann ein geprüfter Redaktionsstand weiterhin als Basis übernommen werden. Die Historie und der Ausfallzähler werden nicht künstlich auf „erfolgreich“ gesetzt.

## Diagnose

```bash
python3 scripts/saisonaler_hero_refresh.py --selftest
python3 scripts/saisonaler_hero_refresh.py --check --json
python3 scripts/saisonale_startseite_guard.py --source-only
```

`--check` ist rein lesend und gibt bei Fälligkeit Exit 1 zurück. Der Report `SAISONALER-HERO-REPORT.md` steht im Actions-Summary und im Artefakt. Dort zeigen der Kettennachweis und das Versuchsprotokoll, ob Recherche, Schlüsselkonfiguration, API-Transport, Finish-Code, Format, Kandidatenvertrag, Hugo oder Render-Gates scheiterten. HTTP-Status und Fehlerklassen sind Diagnosehinweise; Schlüsselwerte gehören weder in Reports noch in Issues.

Beispiele: `HTTP 401/403` deutet auf Zugangs-/Berechtigungsprobleme, `HTTP 429` auf eine Begrenzung, `MAX_TOKENS`/`length` auf eine unvollständige Antwort. Die genaue Ursache der kurzen Antworten aus #891 ist aus den vorhandenen Reports allein **nicht** beweisbar; insbesondere ist eine erschöpfte Denk-/Ausgabebegrenzung nur eine mögliche Erklärung.

Ein `--fix` ist kein reiner Test: Es kann bei Fälligkeit Daten und Fehlerzähler ändern und Anbieter aufrufen. Lokal daher nur gezielt mit frischer Recherche und gültigem Zugang ausführen. Ohne beide Voraussetzungen wird keine KI-Fassung veröffentlicht. `--set-current` ist eine ausdrückliche redaktionelle Basisbestätigung, kein Nachweis für einen reparierten KI-Anbieter; es darf nicht bloß zum Zurücksetzen der Störung verwendet werden.

## Wiederherstellung nach #891

1. Änderungen reviewen und auf den Standardbranch übernehmen. Der Lauf vom 29.10. meldete eine fällige Herbstrotation mit sechs aufeinanderfolgenden Fehlläufen; diese Nachweise werden durch den Fix nicht zurückdatiert oder gelöscht.
2. Den geplanten Lauf abwarten oder den Workflow auf dem **Standardbranch** manuell starten. Ein Branch-Test darf weder Daten committen noch das Produktions-Issue öffnen oder schließen; Report und Recherche stehen als Lauf-Artefakt zur Diagnose bereit. `force` ist für eine bereits fällige Rotation nicht nötig.
3. Im Lauf-Summary Anbieterprotokoll, neuen State/Recherche-Hash sowie Hugo und Render-Gates prüfen. Ein grüner lokaler Mock-Test beweist weder die Gültigkeit produktiver API-Schlüssel noch eine echte Veröffentlichung.
4. Das bestehende Issue bleibt offen, bis der Standardbranch-Lauf vollständig erfolgreich und die Politur-Ampel grün ist. Der Deploy-Catchup lauscht auf den tatsächlichen Workflow-Namen; den anschließenden Deploy bei Bedarf separat überprüfen.

Die Offline-Regressionen laufen im Workflow **vor** der Textpolitur und im allgemeinen PR-Testlauf:

```bash
python3 -m unittest scripts.tests.test_saisonaler_hero_refresh \
  scripts.tests.test_saisonaler_hero_workflow scripts.tests.test_llm_client_transport
```

Sie simulieren Providerfehler, Format-/Faktenverstöße, Erfolg und Rollback einschließlich der tatsächlichen Git-Staging-Entscheidungen. Für einen echten Produktionsnachweis sind dennoch der Lauf mit den dort konfigurierten Schlüsseln und seine Render-Gates nötig.

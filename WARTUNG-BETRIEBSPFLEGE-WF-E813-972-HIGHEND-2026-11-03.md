# Betriebspflege WF-E813 / #972 — Stand 3. November 2026

## Ergebnis und Grenze

**#972 bleibt offen.** Die letzte hier bekannte vollständige Live-Messung ist
[Run 41470449168](https://github.com/frank-hartung/franksfinanzcheck-blog/actions/runs/41470449168)
vom 2. November: Header **BEFUND**, Worker **STÖRUNG**. Auf `/` und
`/methodik/` fehlten Sicherheits-Header; der authentifizierte Worker-Bericht
war unvollständig und `/healthz` hatte keinen `bau`-Stempel. Die Messung ist
ein historischer Ist-Befund, keine neue Gegenmessung. Erfolgreiche
Pull-Request-Läufe der Sicherheits-Wache prüfen nicht den Live-Job und sind
kein Abschlussnachweis. Die Sandbox erreicht die Live-Domains nicht.

Am 3. November über GitHub erneut geprüft: Das Environment
`cloudflare-produktion` hat keine Protection Rules, Admin-Bypass ist aktiv und
keine Deployment-Branch-Policy gesetzt. `worker_environment_guard.py --check`
meldet deshalb Exit 1. Der vorausgegangene Einrichtungsversuch mit dem hier
verfügbaren GitHub-Zugang wurde mit HTTP 403 abgelehnt. Cloudflare-Zugang für
Änderungen steht hier nicht zur Verfügung. Weder Schutz noch Nachweis wurden
abgeschaltet; das Issue wurde nicht geschlossen.

## Zusätzlich behobene Repository-Blockaden

1. **Zerstörtes Integritäts-Siegel:** `data/integrity_lock.json` war seit
   Commit `cf1b8078` ungültiges JSON; die JSON-Bruchstelle liegt bei Byte
   13638. Mit vollständiger Git-Historie stellte `--repair-lock` die jüngste
   gültige Fassung `8af76b55` wieder her und verkettete die Reparatur in der
   Akte. `--heal` signierte anschließend die vier bereits committeten
   FEST-Abweichungen `publikations_vertrag.py`, `redaktions_standard.py`,
   `skills_vertrag.py`, `wachen_vertrag.py` nach den bestehenden Regeln;
   keine kritische oder uncommittete Abweichung wurde freigegeben. Die
   Einträge in `data/integrity_history.jsonl` dokumentieren beide Schritte.
   `merge=binary` war schon gesetzt; es ersetzt kein geprüftes PR-Gate und
   keine sorgfältige Konfliktauflösung. Ein erforderlicher Check schützt nur,
   soweit GitHub-Regeln und Bypass-Einstellungen ihn tatsächlich erzwingen.
2. **Faktenfrische-Rückfall #996:** Der tägliche Pin-Text-Sync übernahm alte
   Aussagen aus `data/pinterest_plan.yaml` wieder in vier Gasartikel; der
   Auto-Commit `7560bb2c` machte den Faktenfrische-Test und damit einen
   Deploy-Schritt rot. Sechs betroffene Planbeschreibungen wurden sachlich
   überarbeitet und die vier redaktionell korrigierten Pin-Beschreibungen
   aus `69f08c40` wiederhergestellt. `pin_text_sync: false` schützt diese
   Artikel im Sync auch bei der Duplikatheilung vor Überschreiben; andere
   Schreiber werden dadurch **nicht** gesperrt. Zusätzlich stoppt der Sync
   vor dem Schreiben, wenn der Plan die konkret bekannten #996-Phrasen
   enthält. Die Tests prüfen Plan, Sperre, Stop vor Schreibaktionen und
   Duplikatpfad. Das ist ein enger Rückfallschutz, kein Faktencheck und keine
   menschliche Freigabe der offenen Faktenfrische-Befunde. Auch ein anderer
   unbelegter Wortlaut kann weiterhin eine redaktionelle Prüfung erfordern.

Der rote Qualitäts-Gate-Schritt im
[Run 41599569588](https://github.com/frank-hartung/franksfinanzcheck-blog/actions/runs/41599569588)
enthält den Fremdmessungs-Test, der mit dem kaputten JSON lokal fehlschlug;
nach Reparatur besteht der gesamte entsprechende Testblock lokal. Da die
GitHub-Laufprotokolle hier nicht lesbar waren, ist der konkrete CI-Fehler
**plausibel, aber nicht abschließend belegt**. Ein neuer CI-Lauf muss es
bestätigen. Für den Deploy-Rückfall liegt der fehlgeschlagene #996-Test lokal
vor; auch hier ersetzt das keinen erneuten Deploy-Lauf.

## Verifikation

- `integrity_guard.py --gate`: 55 versiegelte Dateien stimmen überein.
- `governance_contract.py --quick`: 43 Regeln grün.
- Qualitäts-Gate-Unittestblock plus `test_faktenfrische_996`: 67 Tests,
  erfolgreich, ein Skip. #996 allein: 8 Tests grün.
- Pin-Sync zweimal mit `--apply`-Verhalten auf temporären Kopien aller 106
  Artikel ausgeführt: Exit 0, vier geschützte Artikel beide Male bytegleich.
- `selftest_runner.py` mit den gepinnten CI-Abhängigkeiten: 263 Wachen,
  526 Uhr-Proben, grün. Zwei Hinweise: `net_safety.py` und `safe_xml.py`
  erwähnen `--selftest`, implementieren es aber nicht; sie werden nicht
  fälschlich als Selbsttest ausgeführt.
- Sicherheits-Header offline grün; Selbsttests von Edge-Freigabe,
  Worker-Betriebswache, Sicherheitsnachweis und Worker-Freigabewache grün;
  Worker-Freigabe- und Alert-Scoping-Tests: 54 grün. Diese Ergebnisse
  belegen den Repository-Stand, **nicht** den Live-Zustand.

## Schritte für die verantwortliche Person

1. Änderungen zunächst prüfen und auf `main` übernehmen; CI-Ergebnisse
   insbesondere Integritäts-Siegel, Qualitäts-Gate und Deploy kontrollieren.
2. In [Settings → Environments → cloudflare-produktion](https://github.com/frank-hartung/franksfinanzcheck-blog/settings/environments)
   Frank Hartung als Required Reviewer setzen, Deployment auf den Branch
   `main` begrenzen und Admin-Bypass ausschalten. `npm run worker:environment`
   muss danach Exit 0 liefern. Den Bypass-Schalter im Dashboard setzen.
3. Im Environment `CF_WORKERS_DEPLOY_TOKEN` und `CLOUDFLARE_ACCOUNT_ID`
   hinterlegen und den Workflow „Deploy-Zugang prüfen“ ausführen. Anschließend
   „Cloudflare-Worker deployen“ für `newsletter-worker` auf `main` starten und
   die verlangte Freigabe erteilen. `/healthz` muss danach den Build-Stempel
   `bau: ff-newsletter-2026-10-24` ausweisen; bei abweichendem Zustand dem
   Runbook folgen, nicht Secrets oder Schutzfunktionen auf Verdacht ändern.
4. Mit einem passend berechtigten Cloudflare-Zonen-Token `npm run edge:freigabe`
   zur Diagnose ausführen. Nach Prüfung des Ist-Zustands
   `npm run edge:freigabe:apply`; danach `npm run edge:b7` prüfen und ggf.
   `npm run edge:b7:apply` ausführen und den geänderten Datenschutztext prüfen
   und committen. Bei Teilfehlern erneut messen statt blind zu wiederholen.
5. Danach `gh workflow run sicherheits-wache.yml --ref main` starten und den
   **vollständigen Live-Job** einschließlich beider Messungen prüfen. Nur ein
   erfolgreicher vollständiger Live-Nachweis rechtfertigt die Schließung von
   #972. Details und Rechte: `docs/SICHERHEIT-BETRIEB-RUNBOOK.md`.

Keine Zugangsdaten in Issues, Logs oder Chat veröffentlichen.

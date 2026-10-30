# Prüfqueue #826 – Nachprüfung der offenen Aufgaben

Stand: 30.10.2026. Dieser Bericht ersetzt den Zwischenstand in `YMYL-PRUEFQUEUE-826-NACHHALTIGKEIT-2026-10-30.md`. Eine technische Prüfung und ein Quellenabruf sind keine redaktionelle Fachfreigabe.

## 1. SEO korrigiert, ohne Freigabe vorzutäuschen

Die drei beanstandeten Descriptions von Haus, Privathaftpflicht und Zahnzusatz wurden redaktionell neu formuliert (137/143/128 Zeichen; 923/902/836 px nach `serp_limits`). Sie versprechen keine festen Sparbeträge. M2/M7 meldet keine Befunde mehr – auch nicht für Entwürfe. Die E2E-Quellprüfung wurde **nicht** abgeschwächt.

Da die Description Teil des Fachsiegels ist, sind diese drei Fassungen nicht mehr freigegeben: Sie bleiben `draft: true`, Status `ausstehend`, ohne aktiven Hash. Es wurde weder eine neue Fachprüfung noch ein neuer Audit-Eintrag erfunden. Der frühere Prüfer und die alten Termine stehen ausdrücklich unter historischen Feldnamen; das Gate verlangt für eine neue Freigabe erneut einen Prüfer, ein Prüfdatum und einen Review-Termin. Ein bloßer Statuswechsel genügt nicht zum Neusiegeln.

## 2. Vier Quellenbefunde: Inhalte extern abgerufen und gezielt abgeglichen

Am 30.10.2026 wurden die Inhalte der drei eindeutigen Adressen über den externen Seitenabruf geladen (vier Zuordnungen im Ticket, weil § 40 VVG zweimal zitiert wird). Dies ist **nicht** der Lauf der Belegketten-Wache auf einem GitHub-Runner und liefert hier keinen eigenen HTTP-Status-/Weiterleitungsnachweis. Die eigentliche Wache muss nach Übernahme weiterhin mit `--require-complete` laufen. Es wurden nur die genannten Abschnitte abgeglichen, keine vollständige Fachprüfung aller vier Artikel durchgeführt.

| Ticketzuordnung | Gelesener Primärtext | Befund und Behandlung |
| --- | --- | --- |
| Kfz Q3 und Versicherungsupdate Q3 | [§ 40 VVG](https://www.gesetze-im-internet.de/vvg_2008/__40.html) | Erhöhung aufgrund Anpassungsklausel ohne entsprechende Erweiterung des Schutzes; Frist ein Monat nach Zugang, Wirkung sofort, frühestens mit Wirksamwerden der Erhöhung. Im Kfz-Entwurf waren Aussagen über Klassenanpassungen und Beitragssteigerung zu pauschal. Die betroffenen Passagen wurden präzisiert. Das Versicherungsupdate enthält die vorsichtige Aussage „kann“; keine Vollfreigabe daraus abgeleitet. |
| Ratenkredit Q4 | [§ 502 BGB](https://www.gesetze-im-internet.de/bgb/__502.html) | Für Allgemein-Verbraucherdarlehen beziehen sich 1 % bzw. 0,5 % auf den **vorzeitig zurückgezahlten Betrag**; 0,5 % gelten bei höchstens einem Jahr, nicht nur darunter. Hinzu kommen die Begrenzung auf entfallende Sollzinsen und gesetzliche Ausschlüsse. Die zwei Passagen wurden eingegrenzt; Quellentitel korrigiert. |
| Tierkranken Q3 | [GOT Übersicht](https://www.gesetze-im-internet.de/got_2022/), [§ 2](https://www.gesetze-im-internet.de/got_2022/__2.html), [§ 4](https://www.gesetze-im-internet.de/got_2022/__4.html) | Regulär grundsätzlich ein- bis dreifach, im Notdienst zu den geregelten Zeiten zwei- bis vierfach. § 4 nennt 50 € Notdienstgebühr zuzüglich Umsatzsteuer und erlaubt ein Absehen im begründeten Einzelfall. 59,50 € ist bei 19 % Umsatzsteuer der Bruttobetrag, nicht der im Gesetz genannte Nettobetrag. Text und Quellentitel wurden präzisiert. |

Auch diese drei geänderten Artikel bleiben Entwürfe mit zurückgezogener Freigabe und historischen Prüferdaten. Das alte Protokoll ist als historisch gekennzeichnet, **nicht** an neue Aussagen angepasst oder als neu bestätigt ausgegeben. Die Gate-Befunde E13/E18/E19 weisen bei Kredit, Kfz und Tier auf die nötige Überarbeitung der Anker und Zahlenprotokolle hin. Vor einer neuen Freigabe müssen Fachprüfende die gesamte Fassung, die Quellen, weitere Aussagen und Rechenwege prüfen und dokumentieren. Insbesondere ist der Abruf einzelner Normen kein Beweis für alle übrigen Versicherungs- oder Kostenbehauptungen.

## 3. Merge-Schutz: sicherer Rollout statt vorzeitiger Sperre

Der neue Workflow hat den eindeutigen Jobnamen **YMYL-Siegelprüfung** und prüft PRs nach `main` und Pushes auf `main`. Im PR vergleicht er außerdem geänderte bestehende Post-Bundles mit der Git-Basis: Ein früheres Siegel darf nicht still durch Entfernen des Prüfblocks verschwinden. Ein ausdrücklicher Rückzug verlangt `draft: true`, `status: ausstehend` und getrennte historische Prüferdaten/Termine. Gelöschte Dateien und als Löschen/Neuanlage erkannte Umzüge sind von dieser Übergangsprüfung ausgenommen; Löschungen brauchen weiterhin gesonderte redaktionelle Kontrolle. Er ist im Arbeitszweig vorhanden, aber noch nicht in `main` und daher kein bereits erforderlicher Check. Die lesbaren Repository-Rulesets enthielten am 30.10.2026 keine Regel für erforderliche Statuschecks; der Abruf der klassischen Branch-Protection über die GitHub-API antwortete mit `403 Resource not accessible by integration`. Das belegt keine vollständige Sicht auf alle Schutzregeln und keine Änderungsberechtigung.

**Nach Übernahme dieses Workflows:**

1. Einen PR-Lauf auf der tatsächlichen Merge-Fassung erfolgreich ausführen und den genauen Statuscheck-Namen inklusive GitHub-App-Zuordnung in GitHub ablesen. Nicht mit einem gleichnamigen fremden Check verwechseln.
2. In der für `main` geltenden Branch Protection bzw. einem dafür vorgesehenen Ruleset die erfolgreiche **YMYL-Siegelprüfung** als erforderlichen PR-Check hinzufügen; bestehende Regeln, Bypass-Einstellungen und andere Checks beibehalten. Bei `403` muss ein Repository-Administrator die Berechtigung der GitHub-Integration anpassen oder die Einstellung vornehmen.
3. Mit einem Test-PR verifizieren: gültiges Siegel grün; Änderung einer gebundenen Description ohne neues Siegel rot; offener ungeprüfter Entwurf wird weiterhin durch das Veröffentlichungs-Gate abgefangen. Einen PR nicht anhand eines fehlenden oder übersprungenen Checks freigeben.

Die Regel wird bewusst **nicht vor der Übernahme** scharfgeschaltet: Ein erforderlicher Check, dessen Workflow auf `main` noch nicht existiert, könnte alle PRs ungewollt blockieren. Direkte Pushes lassen sich durch PR-Checks nicht vorab verhindern; dafür sind entsprechende Branch-Protection-Regeln und die bestehenden Deploy-/Schreibschutz-Gates notwendig.

## 4. Ausgeführte Nachweise und verbleibende Arbeit

- 82 Unit-Tests und Gate-Selbsttest bestanden; darunter Statuswechsel ohne neue Prüferdaten/Datum, verweigerte Neusiegelung und Git-Basisvergleich bei still entferntem Prüfblock.
- Metadaten-Wache: 107 Dateien, **0 Befunde**; Siegelwache: 100 Posts, **0 Driftbefunde** (kein Fachfreigabe-Nachweis).
- YMYL-Gate `--published --strict`: 72 Artikel, 0 blockiert. `--all --strict`: 100 Artikel, 10 Hochrisiko, 4 freigegeben und **6 Entwürfe offen**; Exit 1 ist hier beabsichtigt.
- Hugo 0.168.0 extended `--minify`: Build bestanden; SEO-Cockpit-Gate für Description-Länge, -Breite und Heading-Order Exit 0 (P2: 0; eine andere P1-Warnung außerhalb dieses selektiven Gates). Die vollständige E2E-/Browser-Suite wurde nicht ausgeführt.
- Der externe Seitenabruf ersetzt nicht den GitHub-Wachenlauf. Nach Übernahme: Workflow `Redaktionelle YMYL-Prüfung` ausführen und Bericht/Outcome prüfen; bei weiterhin unklaren Abrufen nicht automatisch schließen. Issue #826 bleibt bis zur tatsächlichen Fachprüfung und zum vollständigen Wachenlauf offen.

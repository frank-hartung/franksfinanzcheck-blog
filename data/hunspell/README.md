# Deutsches Hunspell-Wörterbuch (de_DE)

**Herkunft:** LibreOffice `dictionaries`, Datei `de_DE_frami`
**Autor:** Björn Jacke <bjoern@j3e.de>
**Lizenz:** GPLv2 oder GPLv3 (beide Texte liegen in diesem Verzeichnis)
**Größe:** ca. 4,2 MB, 258.220 Wörter

Diese Dateien sind **nicht** versioniert (siehe `.gitignore`). Sie werden
mit `scripts/hunspell_worterbuch_holen.py` hergestellt und von
`scripts/hunspell_ersatz.py` gelesen.

## Warum hier und nicht als Systempaket?

Die CI installiert `hunspell hunspell-de-de` per apt. Auf Rechnern ohne
root ist das nicht möglich; ohne Wörterbuch ist die Rechtschreibkette tot,
und `quality_score` wertet sie als `spelling = 0.5` („unbekannt") – das
drückt gesunde Artikel rechnerisch unter die Schwelle. Dieselbe Ursache
verhinderte die Reserve-Nachzertifizierung über Wochen.

## Weitergabe

Bei Weitergabe des Wörterbuchs sind `COPYING_GPLv2`/`COPYING_GPLv3`
mitzugeben (Copyleft). Das holt das Skript automatisch mit.

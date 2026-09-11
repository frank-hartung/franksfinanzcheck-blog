# 🧱 FM-GRENZEN-REPORT (fm_boundary_guard.py)

**Stand:** 2026-09-11 22:07 UTC · Modus: FIX
**Geprüfte Dateien:** 60 · **baukritisch:** 0 · **automatisch geheilt:** 0 · **unheilbar:** 0 · **offen nach Heilung:** 0 · **Kleber-Hinweise:** 8

**Regelkanon:** F1 Grenze oben · F2 Grenze unten · F3 Block/Zeile nicht YAML-parbar · F4 Quote/Flow nicht geschlossen · F5 Fallback-Regel ohne PyYAML · G Kleber an der Schlussgrenze (Hinweis)

**Gegenprüfung:** PyYAML aktiv (Block-Parse vor und nach jeder Heilung)

🎉 Alle Frontmatter-Blöcke sind baufest – Grenzen und Werte YAML-konform. `hugo --minify` kann am Frontmatter nicht mehr scheitern.

## Hinweise: Kleber an der FM-Schlussgrenze

Hugo schließt das Frontmatter an der ersten Zeile, die mit `---` beginnt – der Text dahinter ist damit NICHT Teil des Body (deshalb erscheint der Einstiegsabsatz doppelt, wenn er unter der Grenze noch einmal steht). Zerlegen ist Aufgabe der Umbruch-/Casing-Wache, hier nur gemeldet.

- `content/posts/2026-08-12-dein-haus-sicher-schuetzen-das-neue-vorsorge-update-2026/index.md` FM-Schlussgrenze zugeklebt: '---Starkregen, Sturm und Überschwemmungen zeigen: Dein Zuha'
- `content/posts/2026-08-12-preisgarantie-gas-so-sicherst-du-dir-guenstige-tarife-fuer-2026/index.md` FM-Schlussgrenze zugeklebt: '---Wer Heizkosten im Griff behalten will, denkt früh an die'
- `content/posts/2026-08-14-internet-dsl-wechseln-praxis-tipps-fuer-den-anbieterwechsel/index.md` FM-Schlussgrenze zugeklebt: '---Zahlst du für deinen heimischen Internetanschluss jeden '
- `content/posts/2026-08-16-gas-anbieter-wechseln-praxis-tipps-fuer-guenstige-tarife/index.md` FM-Schlussgrenze zugeklebt: '---Die Gaspreise ändern sich oft. Trotzdem bleiben viele im'
- `content/posts/2026-08-17-kostenloses-girokonto-so-findest-du-ein-konto-ohne-gebuehren/index.md` FM-Schlussgrenze zugeklebt: '---Zahlst du deiner Bank noch 7 €, 10 € oder gar 15 € im Mo'
- `content/posts/2026-08-17-privathaftpflicht-warum-sie-so-wichtig-ist-und-was-sie-kostet/index.md` FM-Schlussgrenze zugeklebt: '---Ein kurzer Moment der Unachtsamkeit kann dein [finanziel'
- `content/posts/2026-09-04-flugtickets-guenstig-buchen-strategien-fuer-deine-reise/index.md` FM-Schlussgrenze zugeklebt: '---Ein Sitznachbar im Flugzeug zahlt oft das Dreifache für '
- `content/posts/2026-09-10-energie-update-was-sich-jetzt-fuer-dich-aendert/index.md` FM-Schlussgrenze zugeklebt: '---**Stand: 10.09.2026.** Dieser News-Kompakt-Artikel ordne'

---
_Hartes Gate VOR `hugo --minify` (deploy.yml): FM-Fehler sind die einzige Klasse, die den gesamten Deploy stoppt – ohne Gate-Report, ohne verwertbares Fehler-Alerting, nur ein toter Build._

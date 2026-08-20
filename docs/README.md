# 📁 docs/ – Dokumentation & einmalige Arbeitsmaterialien

Dieser Ordner sammelt **einmalige** Dokumente, Pläne und Arbeitsdateien,
damit der Repo-Root sauber bleibt (Profi-Cleanup 20.08.2026).

**Was hier liegt:** Einmalige Anleitungen, Entscheidungsdokumente, Pläne,
Workbooks und Vorschau-Bilder – keine davon wird von der Blog-Automatik gelesen.

**Was bewusst NICHT hier liegt (bleibt im Root):**
- `README.md` – Pflicht im Root (GitHub rendert es dort)
- Live-Report-Dateien (`*-REPORT.md`, `*-STATUS.md`) – sie werden von den
  Workflows **geschrieben** und teils gelesen; Verschieben würde die Automatik brechen
- `ANLEITUNG-PINTEREST-API.md`, `ANLEITUNG-SOCIAL-MEDIA.md` – Skripte verweisen
  in Fehlermeldungen darauf
- `ANLEITUNG-CHECK24-LINKS.md` – im README verlinkt

> Hinweis: Edits in `docs/` triggern **keinen** Deploy
> (`deploy.yml` → `paths-ignore: docs/**`).

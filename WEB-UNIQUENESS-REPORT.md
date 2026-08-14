# 🔍 WEB-UNIQUENESS-REPORT (web_uniqueness_guard.py)

**Geprüfte Seiten:** 115 (57 real, 58 Alias-Redirects) · **Substantiell verglichen:** 19
**Heilung durchgeführt:** nein

## W2/W3 – Technischer Duplicate-Content- & Canonical-Crawl
🎉 Keine doppelten Titel/Descriptions, keine Canonical-Probleme.

## W4 – Indexierungs-Audit
🎉 robots-Meta/Sitemap/IndexNow konsistent.

_Hinweis: Dies prüft Einreichbarkeit/Konsistenz, NICHT die tatsächliche Aufnahme in den Google-Index (dafür wäre die Google Search Console API nötig, siehe ANLEITUNG-GOOGLE-SEARCH-CONSOLE.md)._

## W1 – Web-Duplikat-Suche (externe Kopien)
Kein GOOGLE_CSE_API_KEY/GOOGLE_CSE_CX gesetzt – Web-Duplikat-Suche übersprungen.
AKTIVIEREN (kostenlos, ~5 Minuten, 100 Anfragen/Tag gratis):
  1. https://programmablesearchengine.google.com/ -> Neue Suchmaschine ->
     'Gesamtes Web durchsuchen' aktivieren -> Suchmaschinen-ID (cx) kopieren.
  2. https://console.cloud.google.com/apis/library/customsearch.googleapis.com
     -> aktivieren -> API-Key erzeugen.
  3. GitHub-Repo -> Settings -> Secrets and variables -> Actions:
     Secret GOOGLE_CSE_API_KEY, Variable GOOGLE_CSE_CX.
  Details: ANLEITUNG-WEB-DUPLICATE-CHECK.md

---
_Aktueller Rechtsstand/Google-Richtlinien: siehe SEO-STANDARDS-2026.md. Selbstheilung nur für doppelte Meta-Descriptions (meta_optimizer.py --fix) – externe Kopien und Template-Bugs brauchen redaktionelles bzw. Entwickler-Urteilsvermögen.

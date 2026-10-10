# Datenschutz-Umsetzung und Freigabestatus · 10.10.2026

**Status: TECHNISCH VORBEREITET, RECHTLICH NICHT FREIGEGEBEN.** Die Nachfrage nach einer „rechtlichen Freigabe als Profi-Rechtsberater“ kann durch eine Repository-Prüfung nicht erfüllt werden. Es liegt weder eine anwaltliche Mandatierung noch Einsicht in Produktionskonten, Verträge oder Logdaten vor. Eine solche Freigabe wird hier ausdrücklich **nicht** erteilt. Der alte Auditbericht `DATENSCHUTZ-AUDIT-PREMIUM-2026-10-10.md` bleibt als Vorher-Befund bestehen.

## Umgesetzt im Quellcode

- **Analytics vorsorglich abgeschaltet:** `hugo.toml` hat keine Umami-Website-ID. Der Consent-Banner erscheint nur bei wieder aktivierter Instanz; ein altes Consent-Cookie wird bei deaktivierter Messung gelöscht. Für eine etwaige spätere Aktivierung ist der Loader auf ausdrückliches Opt-in umgestellt; bei Widerruf wird die Seite neu geladen, damit das bereits ausgeführte Fremdskript nicht weiterläuft. Die Banner-Texte suggerieren keine Steuerung fremder Partner-Cookies mehr. Eine Reaktivierung erfordert erneute Rechts-/Netzwerkprüfung.
- **Newsletter-Datenlebenszyklus:** Neue unbestätigte Einträge/Token erhalten 15 Tage TTL, abgemeldete 29 Tage TTL, abgelaufene 1 Tag TTL; aktive bleiben bis zur Abmeldung. Der tägliche Cron entfernt ältere abgemeldete und überfällige unbestätigte Bestandsdatensätze ohne TTL und räumt verwaiste Token-Zuordnungen auf. Wiederanmeldung entwertet den alten Token. Nachweise bleiben getrennt bis zu drei Jahre (TTL). Tests decken Bestand, aktive Einträge, verwaiste Tokens und Wiederanmeldung ab.
- **KV-Jurisdiktion:** Falsche `placement = "eu"`-Zeile entfernt; Dokumentation auf Erzeugung einer EU-Jurisdiktion bei Namespace-Anlage korrigiert. Ein **bestehendes** produktives Namespace wird dadurch nicht automatisch EU-lokal; Cloudflare weist darauf hin, dass selbst bei EU-Jurisdiktion Zugriff und Caching außerhalb der Region möglich sind.
- **Rechtstext:** Erklärt die derzeit deaktivierte Analyse, Browser-Speicher, Feedback, GitHub Actions im Newsletter-Versand und mögliche Drittlandverarbeitung; entfernt unbelegte AVV-/DPF-, Anonymitäts- und pauschale 7–14-Tage-Log-Zusagen. Angleichung des Newsletter-Formulartexts.

## Prüfungen

- `node --test newsletter-worker/test/index.test.js`: **64/64 bestanden**.
- `python3 -m unittest scripts.tests.test_datenschutz_freigabe scripts.tests.test_dom_audit scripts.tests.test_robustheits_gate`: **83 Tests bestanden, 1 übersprungen** (bestehende ResourceWarnings aus `layout_audit.py`).
- `python3 scripts/robustheits_gate.py --source-only`: **0 Befunde**.
- `git diff --check`: ohne Befund.
- **Nicht durchgeführt:** Hugo-Produktionsbuild und Browser-Network-Audit, weil Hugo in der Sandbox nicht installiert ist und der GitHub-Release-Binary-Download durch Netzwerkrestriktionen scheiterte; Live-Prüfung und Cloudflare-Deployment sind ebenfalls nicht erfolgt.

## Zwingende Freigabevoraussetzungen (Betreiber + fachkundige Rechtsprüfung)

1. **Vertragliche Grundlage / Empfänger:** Tatsächliche Verträge und Geltungsbereiche von GitHub Pages **und Actions**, Cloudflare CDN **und Workers KV**, Resend und ggf. SMTP im Betreiberkonto prüfen. DPA/AVV, Unterauftragsverarbeiter, aktuelle DPF-Zertifizierung der konkreten Gesellschaft oder SCC samt Transferbewertung schriftlich belegen; Aufbewahrung der Anbieterlogs klären. Keine Zugangsdaten oder Kundendaten ins Repo legen.
2. **Produktionsdaten:** Cloudflare-KV-Binding, Namespace-Jurisdiktion, Worker-/CDN-Routing, Datenzugriff und Caching verifizieren. Für einen globalen Bestands-Namespace ist Migration ein gesondertes Projekt, **nicht** durch die geänderte `wrangler.toml` erledigt. Bereits gespeicherte Newsletter-Daten auf abgelaufene/unbestätigte/abgemeldete Adressen prüfen und nach dokumentiertem Verfahren bereinigen.
3. **Deployment-Parität:** Erst nach Prüfung den Worker mit Cron und die Website gemeinsam ausrollen. In Cloudflare bestätigen, dass täglicher `13 2 * * *`-Cron ausgeführt wird und die neuen TTLs aktiv sind; Health und Newsletter-DOI testen. Prüfen, ob bestehende gecachte HTML-Seiten/Service Worker Umami noch nachladen; Cache-Versionen erneuern. Netzwerk im Browser ohne Auswahl, nach Ablehnung, nach Zustimmung und nach Widerruf kontrollieren.
4. **Textfreigabe:** Den tatsächlichen Transfermechanismus, Cloudflare-/GitHub-/Resend-Rollen und konkrete oder prüfbare Fristen in `content/datenschutz/index.md` vervollständigen; Verantwortlichkeit im Affiliate-Programm anhand der echten Partnerverträge klären. Vorher ist die Erklärung eine verbesserte **Arbeitsfassung**, kein zertifiziertes Endprodukt.
5. **Integritätsfreigabe:** `hugo.toml` ist im Repository **KRITISCH** gesiegelt; `layouts/_partials/extend_footer.html` **FEST**. Der `integrity_guard.py --verify` meldet daher erwartungsgemäß Abweichungen. Die Änderung darf erst nach ausdrücklicher Prüfung durch den hierfür zuständigen Betreiber gemäß Siegel-Prozess (`--set-current`) signiert werden. Eine neue Signatur wurde nicht stellvertretend als vermeintlich menschliche Freigabe erstellt.

**Bis dahin: keine Behauptung „rechtlich freigegeben“ und keine ungeprüfte Produktivsetzung.** Der Quellcode ist vorbereitet, der Live-Zustand und die Vertragslage sind unbekannt.

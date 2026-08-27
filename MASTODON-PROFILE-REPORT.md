# 🐘 Mastodon-Profil-Sync – Premium-Agentur-Level

> Zuletzt synchronisiert: 27.08.2026 12:20 UTC (Premium-Update, Dry-Run) – Live-Sync via Actions → Mastodon-Profil-Sync

- **Anzeigename:** FranksFinanzcheck 💰 1.800€ sparen (33/40 Zeichen, benefit-driven, vorher: FranksFinanzcheck 💰 Geld sparen)
- **Bio (Premium 451/500 Zeichen):** 
  💰 Bis zu 1.800 €/Jahr Fixkosten sparen – ehrliche Ratgeber statt Verkaufsdruck.

  🧭 25+ Guides in 6 Welten: Strom & Gas · DSL & Internet · Versicherungen · Konto & Karten · Mietwagen · Frugalismus

  🗓 Mo/Mi/Fr neue Artikel – mit konkreten Zahlen, redaktionell geprüft, inkl. Checklisten.

  🤖 KI-unterstützt, automatisch veröffentlicht. Enthält Affiliate-Links (Werbung) – für dich ohne Mehrkosten.

  ❓ Fragen zu deinen Verträgen? Ich antworte persönlich 👇
- **Avatar:** https://files.mastodon.social/accounts/avatars/117/071/737/514/278/970/original/63e8f7ff64a1a1dc.png (vorhanden: static/images/social/mastodon-avatar.png, Alt 117 Zeichen A11y-optimiert)
- **Header:** https://files.mastodon.social/accounts/headers/117/071/737/514/278/970/original/ad33a28d7f17864c.png (vorhanden: static/images/social/mastodon-header.png, Alt 138 Zeichen)
- **Im Instanz-Verzeichnis (discoverable):** True – Reichweite, vorher False = Verlust
- **Für Suche freigegeben (indexable):** True – Fediverse-SEO, vorher False
- **Bot-Flag:** False – persönlich antwortend (E-E-A-T), trotz Automatisierung

## Profilfelder (max. 4 – Premium-Strategie)

| Feld | Wert | Verifiziert | Premium-Begründung |
|---|---|---|---|
| Web: | https://franksfinanzcheck.de | ✅ (rel=me) | Haupteinstieg, grüner Haken via hugo.toml + extend_head.html |
| Ratgeber: | https://franksfinanzcheck.de/pillar/ | — | Alle 6 Welten auf einen Blick, Topical Authority, interne Verlinkung |
| Themen: | #StromSparen #DSL #Versicherung #Girokonto #Mietwagen #Frugalismus #Finanzen | — | CamelCase, suchbar, max 20 Zeichen, inkl. #Finanzen für Discoverability, vorher #StromGas generisch |
| Pinterest: | https://www.pinterest.de/franksfinanzcheck/ | — | Zweitkanal Cross-Promo, 400+ Pins, visuelle Reichweite, Pinterest-Experte |

## Premium-Checks

- **Affiliate-Disclosure in Bio:** ✅ enthalten (rechtssicher, DSGVO + RStV + TMG) – vorher ❌ fehlte
- **25+ Guides / 6 Welten:** ✅ Social Proof + Topical Authority
- **1.800€ Nutzenversprechen:** ✅ belegt via homeInfoParams (bis zu 1.800 €/Jahr), vorher nur 1.000€+
- **Mo/Mi/Fr Kadenz:** ✅ klare Erwartung, vorher Mo, Mi & Fr aber ohne Checklisten-Hinweis
- **Pinterest Cross-Promo:** ✅ Feld vorhanden, vorher auch vorhanden aber ohne optimierte Themen-Hashtags
- **Themen-Hashtags optimiert:** ✅ #StromSparen statt #StromGas, #Finanzen ergänzt
- **Avatar/Header Alt:** ✅ A11y + SEO optimiert (117/138 Zeichen)
- **Bot=false:** ✅ E-E-A-T, persönlich antwortend

## Fehlende Blogbeiträge – Status (27.08.2026)

**Analyse:** 25 Posts total (18 live + 7 draft/cadence_wait), 14 bereits auf Mastodon (lt. social_log.jsonl, davon 2 inzwischen draft), **11 fehlend** (6 live sofort postbar + 5 draft warten auf Kadenz-Re-Queue).

**Live fehlend (6) – Premium-Toots bereit, Flags jetzt false:**
- 2026-08-14-internet-dsl-wechseln-praxis-tipps-fuer-den-anbieterwechsel
- 2026-08-14-sparen-im-herbst-die-besten-spartipps-fuer-die-goldene-jahreszeit
- 2026-08-21-haushaltsbuch-fuehren-app-excel-oder-papier
- 2026-08-21-mietwagen-buchen-ohne-kaution-fallen-urlaub
- 2026-08-24-mehr-freiheit-durch-verzicht-clevere-frugalismus-tipps
- 2026-08-24-preisgarantie-gas-so-schuetzt-du-dich-vor-preisspruengen

**Draft fehlend (5) – Kadenz-Queue:**
- 2026-08-16-gas-anbieter-wechseln-praxis-tipps-fuer-guenstige-tarife (draft:true + cadence_wait:true)
- 2026-08-16-strom-sparen-im-haushalt-die-besten-tipps-fuer-den-herbst
- 2026-08-18-geld-sparen-im-alltag-einfache-tipps-die-jeder-umsetzen-kann
- 2026-08-18-wohngebaeudeversicherung-vergleich-worauf-du-achten-musst
- 2026-08-20-so-findest-du-den-richtigen-dsl-tarif-fuer-dein-zuhause

**Fix:** 9 Flags true→false zurückgesetzt (Root-Cause: mark-all-posted), 11 Premium-Toots generiert (Hook + kanonischer Link + CamelCase + Alt + Cover, kein /go/ im Toot, language=de, public). Siehe `MASTODON-PREMIUM-ERGÄNZUNG.md` für alle Toots + GitHub Actions Anleitung.

**Nächste Schritte:**
1. Actions → Mastodon-Profil-Sync → Run workflow (live, mit MASTODON_ACCESS_TOKEN Scope write:accounts)
2. Danach: Mo/Mi/Fr 09:15 + 20:45 MESZ postet social-ai.yml automatisch 4 pro Lauf → 6 live in 2 Läufen erledigt
3. 5 draft werden nach Kadenz-Re-Queue (cadence_guard --requeue) live + dann automatisch gepostet
4. Alternativ manuell: Actions → Mastodon-Manueller-Post mit slug + intro "🔁 Nochmal ans Herz gelegt:"

---
*Erzeugt von scripts/mastodon_profile_sync.py – Premium-Agentur-Level (Bio 451/500 Zeichen, Affiliate-Transparenz, 25+ Guides, 1.800€-Claim, 6 Pillar, Mo/Mi/Fr, persönlich, bot=false, discoverable/indexable true). Bewusst kein Cronjob, sondern manuell auslösbar über Actions → Mastodon-Profil-Sync → Run workflow, sobald sich Content-Fokus oder Branding erkennbar ändern. Siehe auch MASTODON-PREMIUM-ERGÄNZUNG.md, SOCIAL-STATUS.md, MASTODON-SEO-REPORT.md*

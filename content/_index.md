---
title: "FranksFinanzcheck"
# BEWEISSYSTEM-ROLLOUT 01.10.2026, Beifang-Reparatur: Der Cockpit-Rollout
# hatte der Startseite denselben seoTitle wie /cockpit/ gegeben. Folgen:
# duplicate-title (SEO-Cockpit P2) und roter E2E-Vertrag
# (seo-pagination.spec.mjs erwartet „Geld sparen“ im Startseiten-Title).
# Eigener Title, ≤65 Zeichen (seo_cockpit.py-Regel), Cockpit bleibt positioniert.
seoTitle: "FranksFinanzcheck: Geld sparen bei Fixkosten & Verträgen"
description: "FranksFinanzcheck ist das Fixkosten-Cockpit für Haushalte: Verträge, Fristen und laufende Kosten mit klarer Rechnung statt Werbeversprechen prüfen."
startauswahl:
  - page: /posts/2026-08-14-gasrechnung-senken-fehler-im-spaetsommer-vermeiden
    teaser: "Wenn dein Abschlag steigt, vergleiche zuerst Verbrauch und Tarif mit der letzten Jahresrechnung."
  - page: /posts/2026-08-17-privathaftpflicht-warum-sie-so-wichtig-ist-und-was-sie-kostet
    teaser: "Wenn du eine Police prüfst, vergleiche nicht nur den Beitrag: Welche Schäden sind gedeckt, welche ausgeschlossen?"
  - page: /posts/2026-10-07-handyvertrag-kuendigen-raus-aus-der-kostenfalle-verlaengerung
    teaser: "Schau vor dem Tarifwechsel in deine Vertragsunterlagen. Notiere Kündigungsfrist und Vertragsende getrennt."
  - page: /posts/2026-08-21-haushaltsbuch-fuehren-app-excel-oder-papier
    teaser: "Papier, Tabelle oder App? Wähle ein Format, mit dem du regelmäßige Abbuchungen und variable Ausgaben getrennt erfassen kannst."
# Keine Pagination-Aliase: Bei pagerSize 8 und 25+ Posts existieren
# /page/2/–/page/4/ als echte Seiten. Ein Alias auf dieselbe URL
# bricht `hugo --minify` hart ab.
---
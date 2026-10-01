---
title: "FranksFinanzcheck"
# BEWEISSYSTEM-ROLLOUT 01.10.2026, Beifang-Reparatur: Der Cockpit-Rollout
# hatte der Startseite denselben seoTitle wie /cockpit/ gegeben. Folgen:
# duplicate-title (SEO-Cockpit P2) und roter E2E-Vertrag
# (seo-pagination.spec.mjs erwartet „Geld sparen“ im Startseiten-Title).
# Eigener Title, ≤65 Zeichen (seo_cockpit.py-Regel), Cockpit bleibt positioniert.
seoTitle: "FranksFinanzcheck: Geld sparen bei Fixkosten & Verträgen"
description: "FranksFinanzcheck ist das Fixkosten-Cockpit für deutsche Haushalte: Verträge, Fristen und laufende Kosten mit klarer Rechnung statt Werbeversprechen prüfen."
# Keine Pagination-Aliase: Bei pagerSize 8 und 25+ Posts existieren
# /page/2/–/page/4/ als echte Seiten. Ein Alias auf dieselbe URL
# bricht `hugo --minify` hart ab.
---
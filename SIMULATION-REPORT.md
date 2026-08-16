# 🧪 SIMULATION-REPORT (automation_simulator.py)

**Stand:** 2026-08-16 05:06 UTC
**Checks:** 7 · **Fehlgeschlagen:** 4 · **Selbstgeheilt:** 0

## ❌ SIM-A: Themen-Pool (data/topics.yaml)
```
Parse-Fehler UND Wiederherstellung fehlgeschlagen: while scanning a simple key
  in "<unicode string>", line 24, column 1:
    -title:"Die50-30-20-Regeleinfach ... 
    ^
could not find expected ':'
  in "<unicode string>", line 25, column 1:
    pillar:"frugalismus"
    ^
```

## ❌ SIM-B: Lade-Paritäts-Check (Kern-Regressionsschutz)
```
Grundwahrheit (unabhängig ermittelt): 75 live Artikel.
  ❌ seo_audit.load_posts(): 0
  ❌ keyword_optimizer.load_articles(): 0
  ✅ affiliate_profi_check._post_slugs(): 80
  ✅ internal_linker.load_pages(): 80
  ✅ quality_score.py --report: 80
```

## ❌ SIM-C: Synthetischer Artikel-Lifecycle (Tags/Keywords/Provider)
```
FEHLER: save_article() got an unexpected keyword argument 'quality_level'
```

## ❌ SIM-D: Mastodon-Hashtag/Cover-Regressionstest
```
3 aktuelle Artikel geprüft. zinseszinseffekt-formel-erklaert: Cover in Frontmatter referenziert, aber cover_path() findet die Datei nicht (Regression des Cover-Lade-Bugs?); zahnzusatzversicherung-lohnt-sich: Cover in Frontmatter referenziert, aber cover_path() findet die Datei nicht (Regression des Cover-Lade-Bugs?); wlan-verstaerker-vs-mesh-wlan: Cover in Frontmatter referenziert, aber cover_path() findet die Datei nicht (Regression des Cover-Lade-Bugs?)
```

## ✅ SIM-E: publish_gate.py --dry-run
```
Exit 0. Publish-Gate: keine heutigen Live-Kandidaten – nichts zu prüfen.

```

## ✅ SIM-E: cadence_manager.py --dry-run
```
Exit 0. Domain-Alter: 1 Wochen seit 2026-08-08
Ramp-Ziel (ohne Bremse): 3/Woche
Erfolgsquote: noch zu wenig Daten (3 Events in 14 Tagen) – Sicherheitsbremse inaktiv
→ Ziel-Frequenz: 3/Woche (Mo, Mi, Fr)
  Aktuell konfiguriert: 3/Woche
  Keine Änderung nötig.

```

## ✅ SIM-F: Report-Datei-Selbstheilung
```
Alle erwarteten Report-Dateien vorhanden.
```

---
⚠️ **Mindestens ein Check ist fehlgeschlagen und wurde NICHT automatisch behoben** (Code-Bugs/Redaktionsentscheidungen werden bewusst nicht blind gepatcht). Das bestehende Fehler-Alerting erstellt bei einem fehlgeschlagenen CI-Lauf automatisch ein Issue.

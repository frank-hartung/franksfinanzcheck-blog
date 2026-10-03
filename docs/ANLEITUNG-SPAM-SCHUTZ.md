# ANLEITUNG: Spam-Schutz-Wache (Google-Spam-Policy, Premium-Level)

> **Zweck:** Das Google-Spam-Risiko des Blogs wird nicht quartalsweise
> auditiert, sondern **jeden Tag automatisch geprüft** – und bei
> Gefahr greift eine **selbsttätige Notbremse**, die die
> Vollautomatik stoppt, bevor Google etwas zu sehen bekommt.
>
> Das ist genau die Kontrollschleife, die professionelle
> Content-Agenturen gegen die „Scaled Content Abuse“-Politik fahren:
> **messen → bewerten → bremsen → weiterlaufen lassen.**

---

## 1. Die Idee in einem Satz

Die Wache (`scripts/spam_schutz_wache.py`) misst täglich um **07:41 MESZ**
die Spam-Risiko-KPIs des LIVE-Bestands gegen kalibrierte Budgets
(`data/spam_schutz.yaml`); bei **ROT** stellt sie die Endredaktion
automatisch auf `modus: manuell` (Kill-Switch), bei **GRÜN** gibt sie
nur **eigene** Notbremsen wieder frei – Frank-Entscheidungen bleiben
immer unangetastet.

## 2. Die Kontrollschleife (wie alles zusammenspielt)

```
07:41  Spam-Schutz-Wache        misst KPIs, schreibt Status-JSON,
                               zieht bei ROT die Notbremse
05:48  Endredaktion             liest Status-File VOR jeder Freigabe
       (Mo–Sa)                  (fail-closed: kein File = keine
                               Auto-Freigabe), prüft E12 Near-Dup
                               gegen den Live-Bestand, respektiert
                               das Wochenbudget
Mo/Mi/Fr  cadence_guard         veröffentlicht wie gehabt 2–3 Artikel
                               aus der Re-Queue (alleiniger
                               Veröffentlicher – unverändert!)
```

**Zwei unabhängige Verteidigungslinien:**
1. **Notbremse** in `data/endredaktion.yaml` (Wache schaltet
   `modus: manuell` mit Marker `# NOTBREMSE (spam-schutz-wache …)`)
2. **Status-Handshake** `data/spam_schutz_status.json`: Die Endredaktion
   verweigert Auto-Freigaben, wenn das File fehlt, unlesbar oder ROT
   ist – selbst wenn jemand die Notbremse manuell entfernt hätte.

## 3. Die KPIs (K1–K7) und ihre Budgets

| KPI | Gelb ab | Rot ab | Warum |
|---|---|---|---|
| Tempo pro Tag | – | > 3 | Massenveröffentlichung an einem Tag |
| Tempo pro Woche | > 7 | > 10 | Getunneltes Massen-Tempo |
| KI-Anteil live | > 50 % | > 65 % | „Massenhaft unoriginärer Content“ |
| Auto-Freigaben/Woche | – | > 3 | Endredaktion außer Kontrolle |
| Near-Dup-Paare (SimHash) | ≥ 1 | > 3 | Duplicate Content / Kannibalisierung |
| Thin Content live | – | > 0 | Artikel ohne Wert unter dem Längen-Floor |
| Titel-Duplikate live | – | > 0 | Keyword-Kannibalisierung |
| KI ohne Werbe-Offenlegung | – | > 0 | Transparenz-Pflicht (Werbe-Kennzeichnung) |

**Kalibrierung (03.10.2026, kein Blind-Wert):** Ist-Zustand =
38 Live-Artikel, 32 % KI-Anteil, Tempo 5/Woche, 0 Near-Dups,
max 3/Tag. Die Budgets haben bewusst Luft nach oben – sie bremsen
**Pathologie**, nicht den normalen Betrieb.

**Wiederverwendete SSOTs** (keine zweite Messlogik!):
- `plagiat_guard.simhash/hamming/normalize` – Near-Dup-Erkennung
- `length_policy` – Thin-Content-Floor
- Frontmatter-Wahrheit (`draft`, `ai_generated`,
  `endredaktion_status`, `date`) – wie überall im Blog

## 4. Notbremse: was genau passiert bei ROT?

Die Wache editiert `data/endredaktion.yaml` **textuell per Regex**
(damit Franks Kommentare erhalten bleiben):

```yaml
modus: manuell  # NOTBREMSE (spam-schutz-wache 2026-10-03 – automatisch
                # gesperrt, siehe SPAM-SCHUTZ-REPORT.md)
```

- Ab dann: **keine automatischen Freigaben** mehr – die Endredaktion
  läuft weiter und berichtet, veröffentlicht aber nichts.
- Bei GRÜN löst die Wache **nur Marker-eigene** Bremsen
  (`modus: automatisch` wiederhergestellt).
- **Franks manuelles** `modus: manuell` (ohne Marker) wird von der
  Wache **niemals** angefasst – auch nicht durch Lösen.
- Der Workflow committet Statusfile + evtl. Notbremse; Exit-Code 2
  (ROT) feuert die bestehende Alert-Kette.

## 5. Endredaktion-Härtung (was ab jetzt zusätzlich greift)

| Schutz | Wirkung |
|---|---|
| **E12 – Near-Duplicate-Gate** | Entwurf vs. LIVE-Bestand: SimHash-Abstand ≤ 10 → ROT (nie freigeben), 11–14 → GELB (Politur muss eigenständig formulieren). Misslingt die Messung: GELB, keine Freigabe. |
| **Wochenbudget** | Max. 3 Auto-Freigaben in 7 Tagen (Zählung: `endredaktion_status: freigegeben` + `date` im 7-Tage-Fenster). Deckel pro Lauf (1) bleibt zusätzlich. |
| **Spam-Status-Handshake** | Kein/gültig-ROT Statusfile → keine Auto-Freigabe (fail-closed). `spam_status_erforderlich: false` nur im bewussten Ausnahmefall. |

## 6. Benutzung

```bash
npm run spam:check        # Messen + Bericht + Notbremse (wie der Cron)
npm run spam:messen       # nur messen, ändert KEINE Datei
npm run spam:status       # KPIs + Urteil als JSON
npm run spam:notbremse    # Urteil + Probleme des letzten Laufs
npm run test:spam         # 14 Unit-Tests der Wache

# GitHub: „Spam-Schutz-Wache“ → Run workflow → pruefen | nur_messen
```

**Reports:** `SPAM-SCHUTZ-REPORT.md` (gitignored, immer aktuell im
Repo-Root) · Maschinen-Wahrheit: `data/spam_schutz_status.json`.

## 7. Wenn die Notbremse ausgelöst hat (Playbook)

1. `SPAM-SCHUTZ-REPORT.md` lesen – welche KPI war ROT?
2. Beheben (z. B. Near-Dup-Paar überarbeiten, Tempo drosseln,
   Offenlegung nachreichen).
3. `npm run spam:check` – wird die Wache wieder GRÜN, löst sie ihre
   Notbremse im selben Lauf automatisch.
4. Nichts weiter tun – die Vollautomatik läuft ab dem nächsten
   Endredaktion-Lauf wieder.

## 8. Konfiguration

`data/spam_schutz.yaml` – alle Budgets mit Kommentaren (siehe
Tabelle oben). Änderungen wirken ab dem nächsten Wachen-Lauf;
`DEFAULT_BUDGETS` im Skript ist der Fallback, falls das YAML fehlt.

**Kosten: 0 €** – die Wache nutzt keine externen APIs, nur die
bestehenden Skripte und Dateien im Repo.

## 9. Selbsttest

```bash
python3 scripts/spam_schutz_wache.py --selftest   # Exit 2 bei Fehler
```

Prüft offline Budget-Logik (Tempo, KI-Anteil, Offenlegung,
Near-Dup), Notbremse setzen/lösen und den leeren Bestand. Der
GitHub-Workflow führt den Selbsttest vor jedem echten Lauf aus
(fail-closed).

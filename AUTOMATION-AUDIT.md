# 🔍 AUTOMATION-AUDIT – FranksFinanzcheck
**Erstellt:** 2026-08-10 · Umfang: alle 13 Workflows + 49 Skripte · Analyse auf Profi-/Betriebs-Level

---

## 1. Gesamturteil

**Note: Sehr gut (1,7)** – Das System ist weit über üblichem Hobby-Niveau: Staged-Publishing mit Commit-sofort-Deploy, weichen Qualitäts-Gates, Multi-Provider-Fallbacks, Idempotenz, Status-Dashboards, Issue-Alerting, Beobachtungs-Bot (Watchdog für „Bot schweigt ganz") und jetzt linguistische Selbstentscheidung (Dash-/Compound-/Emoji-Guard).

**Überblick der 13 Workflows:**

| Bereich | Workflow(s) | Rhythmus |
|---|---|---|
| Content-Erzeugung | `content-engine-v2` (aktiv; `daily-content` deaktiviert) | 9× Cron/Tag |
| Qualitäts-Kette | integriert in Engine (Polish, Rechtschreibung, Grammatik, **Dash**, **Compound**, **Emoji**, Lesbarkeit, Gates, Cover, Uniqueness, Affiliate) | bei jedem Artikel |
| Deploy | `deploy.yml` (gh-pages-Branch-Methode, Queue) | on push |
| SEO | `seo-weekly` (Mi) + IndexNow in Engine | wöchentlich/artikelweise |
| Verbreitung | `pinterest-ai`, `repin-weekly`, `social-ai` (Mastodon) | täglich/wöchentlich |
| Bestandspflege | `update-quarterly` (Top-10 Refresh) | quartalsweise |
| Layout/A11y | `layout-ai` (Mo), `a11y_audit` (Skript) | wöchentlich |
| Backlinks | `backlink-weekly` (Report; Versand bewusst manuell!) | wöchentlich |
| Ops/Metriken | `frankautoops-report`, `bot-watchdog` | täglich |
| Alerting | `alert-on-failure` | ereignisgesteuert |

---

## 2. Selbstheilung (vorhanden ✅ / was heute ergänzt wurde 🆕)

| Selbstheilungs-Fähigkeit | Mechanismus |
|---|---|
| Artikel-Verlust bei schwacher KI | 3-Ebenen-Fallback der Engine v2 ✅ |
| Deploy wird nicht getriggert | expliziter `workflow_dispatch` (Token-Rekursionssperre umgangen) ✅ |
| Pinterest-Token läuft ab | **Continuous Refresh** (pinterest_auth.py, AES-verschlüsselte Token-Datei) 🆕 |
| Veraltete Cover-Texte | Manifest-Abgleich (`check_covers --fix`) – praktisch bewiesen ✅ |
| Fehlende Bildvarianten | Auto-Nachzug in Engine + Layout-AI ✅ |
| Push-Race zwischen Bots | **heute gehärtet:** Rebase-Schutz in `repin-weekly`, `backlink-weekly`, `seo-weekly`, `update-quarterly` 🆕 |
| Workflow-Ausfall unsichtbar | **heute gehärtet:** Alerting-Liste ergänzt (s. u.) 🆕 |
| Komplette Bot-Stille | Bot-Watchdog ✅ |

## 3. Kritische Befunde & erledigte Fixes (2026-08-10)

1. **🕳️ Alerting-Blindspot (am schwersten):** Die Liste in `alert-on-failure.yml` überwachte den **alten, deaktivierten** „Automatische Content-Generierung"-Workflow – aber **nicht** die Nachfolgerin „Content-Engine v2"! Auch „Pinterest-AI", „Layout-AI" und „FrankAutoOps-Report" fehlten. → **ergänzt.**
2. **⏰ Zeitslot-Kollision:** `repin-weekly` und `pinterest-ai` liefen **beide Mo 17:30 MESZ**, beide pushen → Push-Race. → repin auf **Mo 16:00** verschoben.
3. **🏎️ Push-Races generell:** 4 Workflows pushten ohne `pull --rebase`-Schutz und ohne Concurrency-Gruppe. → in allen ergänzt (siehe Commits 2026-08-10).

Restrisiko (akzeptabel): Zwei Bots pushen zeitgleich → einer erleidet Rebase → Retry-Fallback eingebaut; Deploy-Queue (`pages-deploy`) verträgt das.

## 4. Verwaiste Skripte (bereinigen beim nächsten Frühjahrsputz)

Nicht in Workflows verdrahtet: `add_affiliate_urls.py`, `fix_cover_alts.py`, `fix_nbsp.py`, `make_workbook_pdf.py`, `publish.py`, `quality_score.py`, `set_check24_links.py`, `update_docs.py`.
*Kein Handlungsdruck – sie sind manuelle Werkzeuge/Altlasten. **Nicht** verwaist, obwohl in der Liste-fein nicht direkt aufgerufen: `post_utils.py`, `pinterest_auth.py` (werden von anderen Skripten importiert).* 
Empfehlung: in `scripts/_archiv/` verschieben oder im Kopf als „manuell" kennzeichnen.

## 5. Was noch fehlt (Priorisierung)

**P1 – bald sinnvoll:**
- [x] **Dependabot für GitHub Actions** – ERLEDIGT 2026-08-10 (`.github/dependabot.yml`, wöchentlich Mo 07:00 MESZ)
- [ ] **Uptime-Check** der Live-Domain (6h-Cron, `curl` auf franksfinanzcheck.de → Issue bei Ausfall; ergänzt Watchdog, der ja nur „Bot schweigt" prüft)
- [ ] Alt-Workflow `daily-content.yml` **löschen** (ist deaktiviert & verwirrt nur noch; History bleibt im Git)

**P2 – Reichweite/Ausbau (auf Wunsch):**
- [ ] LinkedIn-Aktivierung (Secret + URN liegen als Option bereit – Token 60-Tage-Pflege beachten)
- [ ] Newsletter-Automation (z. B. Buttondown RSS-Import – null Code nötig)
- [ ] Pinterest „Standard access" beantragen, sobald Trial läuft und Volumen wächst

**P3 – Feinschliff:**
- [ ] Meta-Skript `run_quality_chain.py` (ein einziger Einstiegspunkt statt 16 Einzel-Aufrufe in der Workflow-YAML; vereinfacht lokale Ausführung)
- [ ] Kunst-Regel: `OPS-REPORT.md` auf den SEO-Score erweitern (Klicks aus Search Console API, sobald eingerichtet)

## 6. Gegenseitige Behinderung – Gesamtmatrix

| Paar | Konflikt | Status |
|---|---|---|
| Engine v2 × daily-content | doppelte Artikel | ✅ gelöst (daily deaktiviert, gleiche Concurrency-Gruppe) |
| repin-weekly × pinterest-ai | Push-Race (Zeitslot + fehlender Rebase) | 🆕 gelöst (Zeit + Guards) |
| alle Bots × deploy.yml | viele Builds/Tag | ✅ OK (Queue `pages-deploy`, cancel-in-progress: false) |
| social-ai × pinterest-ai | Doppel-Freigabe neuer Artikel | ✅ getrennte Flags (`social_posted` / `pinned`) |
| Pinterest-Token-Datei (2 Workflows schreiben sie) | paralleles Refresh-Commit | ⚠️ Restrisiko (selten; Rebase-Guards fangen es) |
| Alerting × alle | komplette Abdeckung | 🆕 geschlossen |

---

*Nächstes Audit empfohlen: Quartalsweise (passt zum Artikel-Update-Rhythmus).*

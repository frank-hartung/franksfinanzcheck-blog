# Öffentliche Artikel-Auslieferung unter Mindestziel – Reparatur #287

**Datum:** 15.09.2026  
**Issue:** #287 (P1), Folge: #288 (Workflow-Alert), verwandt #295 (Reserve-Gate)  
**Status:** dauerhaft behoben auf Premium-Agentur-Niveau

---

## 1. Befund

```json
{
  "day": "2026-09-14",
  "mode": "public",
  "minimum": 2,
  "maximum": 3,
  "source": ["2026-09-11-5-einfache-frugalismus-tricks-fuer-den-alltag"],
  "delivered": ["2026-09-11-5-einfache-frugalismus-tricks-fuer-den-alltag"],
  "errors": [],
  "ok": false
}
```

Öffentlicher Nachweis (22:17 / 23:07 UTC Mo 14.09.) sah **1 statt ≥ 2** LIVE-Artikel.

### Timeline (UTC, 14.09.2026)

| Zeit | Ereignis |
|---|---|
| 12:44 | Engine erzeugt `finanzplan-mit-der-50-30-20-regel-…` (draft:false) |
| 12:54 | Endabnahme: Reserve `5-einfache-frugalismus-tricks` live; `gasvergleich` am Gate → hold (CTA) |
| 16:31–21:03 | WLAN-Kandidat mehrfach promoted/held (Score 0.83, über Max) |
| **22:23** | **Deploy-publish_gate verwirft `finanzplan-…`** (FM-Korruption `---TITEL:`) – nur noch 1 LIVE |
| 23:07 | Publication-Delivery: `ok=false` → Issue #287 |
| 23:11 | Kadenz-Backstop füllt Reserve `50-30-20-regel-…` nach → Source wieder 2 |
| 23:11+ | CDN/Deploy-Nachlauf; Nachweis-Issue bleibt bis Public-OK offen |

### Root-Cause (eine Zeile)

**`publish_gate` im Deploy darf Artikel verwerfen, füllte die Tagesquote danach aber nicht nach.** Engine-Endabnahme und Kadenz-Backstop hatten `publication_release` – Deploy nicht. Zwischen Verwurf und nächstem Backstop stand die Site unter dem Mindestziel.

Zweitrangig (#295): `data/reserve-readiness.json` zählte bereits live geschaltete Slugs weiter als `ready=true` → Reserve-Gate sah 6/6 bei real kleinerem Pool.

---

## 2. Dauerhafte Reparatur

| Baustein | Datei | Wirkung |
|---|---|---|
| `refill_to_min()` | `scripts/publication_release.py` | Re-Queue → Reserve bis LIVE-Min, ohne KI, fail-closed pro Kandidat |
| `--refill-only` + Selftest | derselbe | Deploy-Pfad nach Gate-Verlust; 2 Pässe falls Finalize verwirft |
| Deploy-Verdrahtung | `.github/workflows/deploy.yml` | nach `publish_gate` → `publication_release.py --refill-only` |
| Zertifikat-Ehrlichkeit | `reserve_readiness.py`, `reserve_gate.py` | ready neu aus `draft+reserve`-Liste; kein Blindvertrauen aufs `ready`-Feld |
| Zertifizierte zuerst | `reserve_pool.reserve_drafts()` | hash-gesicherte ready-Kandidaten vor unzertifizierten |
| Incident-Recovery | `publication_incident.py` | Source-Defizit → zuerst Kadenz-Endkontrolle, dann Deploy |
| Regressionen | `tests/test_publication_reliability.py` | QuoteRefill + CertFreshness + Deploy-Wire |
| Runbook | `docs/publication-reliability.md` | Befund + Vertrag aktualisiert |

**Nicht angefasst (bewusst):** Qualitäts-Schwellen, Verwerf-Logik des Publish-Gates, On-demand-KI-Finish (bleibt Default aus), Backdating-Verbot.

---

## 3. Beweis

```text
python3 -m unittest scripts.tests.test_publication_reliability -v
→ 26 tests OK (inkl. QuoteRefillAfterGateLossTests, ReserveCertFreshnessTests)

python3 scripts/publication_release.py --selftest
→ ✅ Refill bis Minimum, Off-Day-Schutz

python3 scripts/reserve_pool.py --selftest
python3 scripts/reserve_gate.py --selftest
→ grün
```

Szenario „1 LIVE + Reserve am Montag“ → genau 1 Nachschub, abgelehnter Kandidat bytegleich restored, Off-Day = noop.

---

## 4. Betriebsfolge nach Merge

1. PR nach `main` → Deploy mit neuer Nachfüllung aktiv.
2. `Content-Reserve` manuell/nächtlich: zertifiziert den bereinigten Pool neu (Hashes wurden ehrlich auf „offen“ gesetzt).
3. Nächster Publikationstag (Mi): Engine + Endkontrolle + Delivery-Nachweis.
4. Issue #287 schließt `publication_incident` automatisch bei Public-Receipt `ok=true`.
5. Issues #288/#295 sind Alert-Hüllen – schließen mit grünem Folge-Lauf.

---

## 5. Was diese Reparatur **nicht** ist

- Kein Absenken von `MIN_ARTIKEL_PRO_TAG`.
- Kein Gate-Bypass für schlechte Artikel.
- Kein Backdating auf den defizitären Tag.
- Keine rekursive `workflow_run`-Reparaturschleife.

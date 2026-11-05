"""Vertragstests des Authority-Radars.

Der Radar hat zwei Fehlerklassen, die sich nur mit Tests dauerhaft ausschließen
lassen:

1. **Falsche Forderungen** – z. B. ein Import für den laufenden Monat, den es
   am 5. noch gar nicht geben kann (Issue #1076). Ein Dauerbefund ohne Adressat
   erzieht dazu, den Radar zu ignorieren.
2. **Falsche Zahlen** – `0` statt „unbekannt“, Marken-Klicks aus einem Ledger,
   das keine Suchanfragen führt, oder eine Deklaration, die „belegt“ sagt,
   während die Messlage offen ist.

Jeder Test unten hält eine dieser beiden Klassen fest. Die Tests laufen offline
und schreiben nur in temporäre Verzeichnisse.
"""
import datetime as dt
import importlib.util
import json
import re
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("authority_engine", ROOT / "scripts/authority_engine.py")
ae = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ae)

AS_OF = dt.date(2026, 11, 5)


def voller_monat(period, klicks=0, impressionen=10):
    """Ledger-Zeilen für jeden Tag eines Monats."""
    jahr, monat = (int(teil) for teil in period.split("-"))
    tag = dt.date(jahr, monat, 1)
    zeilen = {}
    while tag.month == monat:
        zeilen[tag] = {"clicks": klicks, "impressions": impressionen}
        tag += dt.timedelta(days=1)
    return zeilen


def strategie(quellen=None, periods=None):
    return {
        "meta": {"minimum_linkable_assets_per_quarter": 1},
        "quarters": [{"quarter": "2026-Q4", "asset_id": "asset-1", "status": "live",
                      "release": "2026-10-02"}],
        "assets": [{"id": "asset-1", "title": "Asset", "status": "live",
                    "published": "2026-10-02", "refresh_days": 365}],
        "measurement": {
            "reporting_lag_days": 4,
            "manual_due_day": 5,
            "gsc_max_age_days": 5,
            "sources": quellen if quellen is not None else [
                {"id": "gsc", "label": "GSC", "mode": "automatisch",
                 "kpi": ["gsc_clicks", "gsc_impressions", "gsc_brand_clicks"],
                 "kpi_optional": ["gsc_brand_clicks"]},
                {"id": "newsletter", "label": "Newsletter", "mode": "manuell",
                 "kpi": ["newsletter_subscribers", "newsletter_click_rate"]},
                {"id": "retention", "label": "Retention", "mode": "nicht_messbar",
                 "kpi": ["returning_reader_rate"], "grund": "kein Zähler",
                 "entschieden": "2026-09-24"},
                {"id": "conversion", "label": "Conversion", "mode": "nicht_aktiv",
                 "kpi": ["conversions", "conversion_rate"], "grund": "Klickzähler aus",
                 "entschieden": "2026-10-14"},
            ],
            "periods": periods or [],
        },
    }


class TempRepo:
    """Kleines Repo im tmp-Verzeichnis – patcht alle Pfade des Moduls."""

    PFADE = ("ROOT", "MEASUREMENTS", "GSC_DIR", "GSC_LEDGER", "GSC_META", "GSC_QUERIES",
             "KLICKMESSUNG", "PROVISIONEN_AGGREGAT", "REPORT", "OUTREACH")

    def __init__(self, tmp):
        self.root = Path(tmp)
        self.original = {name: getattr(ae, name) for name in self.PFADE}

    def __enter__(self):
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / "data" / "gsc").mkdir(parents=True, exist_ok=True)
        (self.root / "data" / "authority_measurements").mkdir(parents=True, exist_ok=True)
        ae.ROOT = self.root
        ae.MEASUREMENTS = self.root / "data/authority_measurements"
        ae.GSC_DIR = self.root / "data/gsc"
        ae.GSC_LEDGER = ae.GSC_DIR / "tagesdaten.jsonl"
        ae.GSC_META = ae.GSC_DIR / "meta.json"
        ae.GSC_QUERIES = ae.GSC_DIR / "top_suchbegriffe_28t.json"
        ae.KLICKMESSUNG = self.root / "data/klickmessung.yaml"
        ae.PROVISIONEN_AGGREGAT = self.root / "data/provisionen_aggregat.json"
        ae.REPORT = self.root / "AUTHORITY-RADAR.md"
        ae.OUTREACH = self.root / "docs/outreach"
        return self

    def __exit__(self, *exc):
        for name, wert in self.original.items():
            setattr(ae, name, wert)
        return False

    def ledger(self, tage):
        zeilen = [json.dumps({"datum": tag.isoformat(), **werte}, ensure_ascii=False)
                  for tag, werte in sorted(tage.items())]
        ae.GSC_LEDGER.write_text("\n".join(zeilen) + "\n", encoding="utf-8")

    def meta(self, bis, status="ok"):
        ae.GSC_META.write_text(json.dumps({
            "stand": f"{bis}T13:00:00Z", "status": status, "grund": "",
            "site": "sc-domain:franksfinanzcheck.de",
            "zeitraum": {"von": "2026-09-20", "bis": bis},
        }), encoding="utf-8")

    def queries(self, eintraege):
        ae.GSC_QUERIES.write_text(json.dumps(eintraege, ensure_ascii=False), encoding="utf-8")

    def audience(self, period, metrics):
        (ae.MEASUREMENTS / f"{period}-audience.json").write_text(json.dumps({
            "schema": 1, "period": period, "source": "first-party-audience-aggregate",
            "imported": "2026-11-05", "metrics": metrics,
            "provenance": "Newsletter-Studio Monatsauszug",
        }), encoding="utf-8")


class AuthorityEngineTest(unittest.TestCase):
    # ---------------------------------------------------------- Zeit & Periode

    def test_quarters(self):
        self.assertEqual(ae.quarter_for(dt.date(2026, 12, 31)), "2026-Q4")
        self.assertEqual(ae.quarter_for(dt.date(2027, 1, 1)), "2027-Q1")

    def test_reporting_month_respects_lag_and_year_end(self):
        # Regression #1076: am 5. ist der Vormonat der Berichtsmonat …
        self.assertEqual(ae.reporting_month(dt.date(2026, 11, 5)), "2026-10")
        self.assertEqual(ae.reporting_month(dt.date(2026, 11, 9)), "2026-10")
        # … vor Ablauf der Verzögerung der Monat davor.
        self.assertEqual(ae.reporting_month(dt.date(2026, 11, 4)), "2026-09")
        self.assertEqual(ae.reporting_month(dt.date(2027, 1, 1)), "2026-11")
        self.assertEqual(ae.manual_due("2026-10", 5), dt.date(2026, 11, 5))
        self.assertEqual(ae.manual_due("2026-12", 5), dt.date(2027, 1, 5))
        self.assertEqual(ae.month_days("2028-02"), 29)

    # ------------------------------------------------------------- Repository

    def test_repository_contract_is_valid(self):
        errors = ae.validate(ae.load_yaml(ae.STRATEGY), ae.load_yaml(ae.EVIDENCE))
        errors += ae.validate_measurements(ae.load_measurements())
        self.assertEqual(errors, [])

    def test_repository_lage_derives_gsc_from_ledger(self):
        """Der echte Bestand muss belegt sein, ohne zweiten Import."""
        strategy = ae.load_yaml(ae.STRATEGY)
        lage = ae.build_lage(strategy, AS_OF)
        self.assertEqual(lage["errors"], [])
        self.assertEqual(lage["berichtsmonat"], "2026-10")
        self.assertEqual(lage["fakten"]["werte"].get("gsc_impressions") is not None, True)
        gsc_quelle = next(q for q in lage["quellen"] if q["id"] == "gsc")
        self.assertEqual(gsc_quelle["status"], "belegt")
        # Marken-Klicks bleiben unbekannt – das Ledger führt keine Suchanfragen.
        self.assertIsNone(lage["fakten"]["werte"].get("gsc_brand_clicks"))

    def test_current_quarter_has_live_asset(self):
        strategy = ae.load_yaml(ae.STRATEGY)
        quarter, actions, _, _ = ae.evaluate(strategy, {"evidence": []}, dt.date(2026, 10, 2))
        self.assertEqual(quarter, "2026-Q4")
        self.assertFalse(any("Quartals-Asset" in text for _, text in actions))

    # ------------------------------------------------------------ Importe/CSV

    def test_gsc_import_keeps_only_aggregates(self):
        with tempfile.TemporaryDirectory() as tmp, TempRepo(tmp) as repo:
            export = repo.root / "gsc.csv"
            export.write_text("Suchanfragen,Klicks,Impressionen\nFranks Finanzcheck,4,20\nstrom sparen,6,80\n",
                              encoding="utf-8")
            target = ae.import_gsc(export, "2026-10")
            data = json.loads(target.read_text(encoding="utf-8"))
            self.assertEqual(data["gsc"]["clicks"], 10)
            self.assertEqual(data["gsc"]["brand_clicks"], 4)
            self.assertNotIn("Franks Finanzcheck", target.read_text(encoding="utf-8"))
            self.assertEqual(ae.validate_measurements(ae.load_measurements()), [])

    def test_gsc_import_without_query_column_keeps_brand_unknown(self):
        """Ohne Suchanfragen-Spalte sind Marken-Klicks unbekannt – nicht 0."""
        with tempfile.TemporaryDirectory() as tmp, TempRepo(tmp) as repo:
            export = repo.root / "gsc.csv"
            export.write_text("Klicks,Impressionen\n3,40\n", encoding="utf-8")
            data = json.loads(ae.import_gsc(export, "2026-10").read_text(encoding="utf-8"))
            self.assertEqual(data["gsc"]["clicks"], 3)
            self.assertIsNone(data["gsc"]["brand_clicks"])
            self.assertIsNone(data["gsc"]["brand_impressions"])

    def test_measurement_contract_rejects_duplicates_bad_rates_and_unknown_kpi(self):
        docs = [
            {"schema": 1, "period": "2026-10", "source": "first-party-audience-aggregate",
             "imported": "2026-10-05", "metrics": {"conversion_rate": 1.2},
             "provenance": "dashboard", "_file": "a.json"},
            {"schema": 1, "period": "2026-10", "source": "first-party-audience-aggregate",
             "imported": "2026-10-05", "metrics": {"conversions": 2, "open_rate": 0.4},
             "provenance": "dashboard", "_file": "b.json"},
        ]
        errors = ae.validate_measurements(docs)
        self.assertTrue(any("doppelt" in error for error in errors))
        self.assertTrue(any("zwischen 0 und 1" in error for error in errors))
        self.assertTrue(any("unbekannte Kennzahl" in error for error in errors))

    def test_measurement_contract_rejects_impossible_brand_totals(self):
        docs = [{"schema": 1, "period": "2026-10", "source": "google-search-console-csv",
                 "imported": "2026-10-05", "gsc": {"clicks": 4, "impressions": 9,
                                                   "brand_clicks": 7, "brand_impressions": 12},
                 "_file": "x.json"}]
        errors = ae.validate_measurements(docs)
        self.assertTrue(any("Marken-Klicks" in error for error in errors))
        self.assertTrue(any("Marken-Impressionen" in error for error in errors))

    def test_import_rejects_impossible_period_and_negative_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            export = Path(tmp) / "gsc.csv"
            export.write_text("Klicks,Impressionen\n-1,10\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                ae.import_gsc(export, "2026-13")
            with self.assertRaises(ValueError):
                ae.import_gsc(export, "2026-10")

    def test_audience_import_rejects_unknown_fields_and_missing_provenance(self):
        with tempfile.TemporaryDirectory() as tmp, TempRepo(tmp) as repo:
            datei = repo.root / "audience.json"
            datei.write_text(json.dumps({"newsletter_subscribers": 12}), encoding="utf-8")
            with self.assertRaises(ValueError):
                ae.import_audience(datei, "2026-10")
            datei.write_text(json.dumps({"newsletter_subscribers": 12, "empfaenger": ["a@b.de"],
                                         "provenance": "Dashboard"}), encoding="utf-8")
            with self.assertRaises(ValueError):
                ae.import_audience(datei, "2026-10")
            datei.write_text(json.dumps({"newsletter_subscribers": 0,
                                         "provenance": "Worker-Export 2026-11-05"}), encoding="utf-8")
            ziel = ae.import_audience(datei, "2026-10")
            self.assertEqual(json.loads(ziel.read_text(encoding="utf-8"))["metrics"]["newsletter_subscribers"], 0)

    # --------------------------------------------------------------- Evidenz

    def test_evidence_contract_rejects_duplicate_ids_and_tracking_urls(self):
        strategy = strategie()
        evidence = {"evidence": [
            {"id": "x", "kind": "media_mention", "publisher": "Medium A", "title": "T",
             "url": "https://example.org/a?utm_source=x", "published": "2026-10-01"},
            {"id": "x", "kind": "interview", "publisher": "Medium B", "title": "T",
             "url": "https://example.org/b", "published": "2026-10-02"},
        ]}
        errors = ae.validate(strategy, evidence)
        self.assertTrue(any("Evidenz-IDs" in error for error in errors))
        self.assertTrue(any("Tracking-Parameter" in error for error in errors))

    def test_evidence_contract_rejects_own_domain_and_missing_publisher(self):
        strategy = strategie()
        evidence = {"evidence": [
            {"id": "a", "kind": "editorial_link", "title": "Eigener Post",
             "url": "https://franksfinanzcheck.de/blog/x/", "published": "2026-10-01"},
            {"id": "b", "kind": "editorial_link", "title": "Ohne Herausgeber",
             "publisher": " ", "url": "https://franksfinanzcheck.de/blog/x/",
             "published": "2026-10-01"},
        ]}
        errors = ae.validate(strategy, evidence)
        self.assertTrue(any("eigene Domain" in error for error in errors))
        self.assertTrue(any("publisher fehlt" in error for error in errors))
        self.assertTrue(any("Doppelmeldung" in error for error in errors))

    # ---------------------------------------------------------------- Vertrag

    def test_measurement_contract_rejects_unexplained_and_unimplemented_sources(self):
        strategy = strategie(quellen=[
            {"id": "gsc", "label": "GSC", "mode": "automatisch", "kpi": ["gsc_clicks"]},
            {"id": "geheim", "label": "Geheim", "mode": "automatisch", "kpi": ["conversions"]},
            {"id": "retention", "label": "Retention", "mode": "nicht_messbar",
             "kpi": ["returning_reader_rate"]},
            {"id": "newsletter", "label": "Newsletter", "mode": "manuell",
             "kpi": ["newsletter_subscribers"]},
        ])
        errors = ae.validate(strategy, {"evidence": []})
        self.assertTrue(any("automatische Quelle ist nicht implementiert" in e for e in errors))
        self.assertTrue(any("braucht grund" in e for e in errors))
        self.assertTrue(any("Entscheidungsdatum" in e for e in errors))

    def test_declaration_must_not_claim_unproven_values(self):
        strategy = strategie(periods=[{
            "period": "2026-10", "status": "belegt", "updated": "2026-11-05",
            "gsc_clicks": 5, "evidence": [],
        }])
        errors = ae.validate(strategy, {"evidence": []})
        self.assertTrue(any("Werte ohne Evidenz" in e for e in errors))
        strategy = strategie(periods=[{
            "period": "2026-10", "status": "belegt", "updated": "2026-11-05",
            "gsc_clicks": 5, "evidence": ["gibt-es-nicht"],
        }])
        errors = ae.validate(strategy, {"evidence": []})
        self.assertTrue(any("fehlt im Evidenzregister" in e for e in errors))

    def test_declaration_drift_becomes_action(self):
        """Steht „belegt“ im Vertrag, während Kennzahlen fehlen, meldet der Radar das."""
        with tempfile.TemporaryDirectory() as tmp, TempRepo(tmp) as repo:
            repo.ledger(voller_monat("2026-10"))
            repo.meta("2026-11-02")
            strategy = strategie(periods=[{
                "period": "2026-10", "status": "belegt", "updated": "2026-11-05", "evidence": [],
            }])
            lage = ae.build_lage(strategy, AS_OF)
            _, actions, _, _ = ae.evaluate(strategy, {"evidence": []}, AS_OF, lage=lage)
            self.assertTrue(any("Deklaration" in text and "belegt" in text for _, text in actions))

    # ------------------------------------------------------------------ Lage

    def test_ledger_month_aggregation_and_coverage(self):
        ledger = {**voller_monat("2026-10", klicks=1, impressionen=4)}
        oktober = ae.gsc_month(ledger, "2026-10")
        self.assertEqual(oktober["clicks"], 31)
        self.assertEqual(oktober["impressions"], 124)
        self.assertEqual((oktober["tage"], oktober["erwartet"]), (31, 31))
        self.assertIsNone(ae.gsc_month(ledger, "2026-08"))
        teil = {tag: werte for i, (tag, werte) in enumerate(sorted(ledger.items())) if i < 20}
        self.assertEqual(ae.gsc_month(teil, "2026-10")["tage"], 20)

    def test_ledger_health_marks_stale_data(self):
        with tempfile.TemporaryDirectory() as tmp, TempRepo(tmp) as repo:
            repo.ledger({dt.date(2026, 10, 30): {"clicks": 0, "impressions": 3}})
            repo.meta("2026-10-30")
            gesund = ae.gsc_health(ae.load_gsc(), AS_OF, 5)
            self.assertEqual(gesund["status"], "veraltet")
            self.assertEqual(gesund["alter_tage"], 6)
            strategy = strategie()
            lage = ae.build_lage(strategy, AS_OF)
            _, actions, _, _ = ae.evaluate(strategy, {"evidence": []}, AS_OF, lage=lage)
            self.assertTrue(any(prio == "P1" and "Ledger steht" in text for prio, text in actions))

    def test_ledger_line_is_validated(self):
        with tempfile.TemporaryDirectory() as tmp, TempRepo(tmp):
            ae.GSC_LEDGER.write_text('{"datum": "2026-10-01", "clicks": 5, "impressions": 3}\n',
                                     encoding="utf-8")
            self.assertTrue(any("Klicks übersteigen" in e for e in ae.load_gsc()["errors"]))
            ae.GSC_LEDGER.write_text('{"datum": "2026-10-99", "clicks": 1, "impressions": 3}\n',
                                     encoding="utf-8")
            self.assertTrue(any("datum" in e for e in ae.load_gsc()["errors"]))

    def test_evaluate_never_demands_the_running_month(self):
        """Regression #1076: am 5. darf kein Import für den laufenden Monat verlangt werden."""
        with tempfile.TemporaryDirectory() as tmp, TempRepo(tmp) as repo:
            repo.meta("2026-11-02", status="nicht_konfiguriert")
            strategy = strategie()
            lage = ae.build_lage(strategy, AS_OF)
            self.assertEqual(lage["berichtsmonat"], "2026-10")
            _, actions, _, _ = ae.evaluate(strategy, {"evidence": []}, AS_OF, lage=lage)
            self.assertTrue(actions)
            for _, text in actions:
                self.assertIsNone(re.search(r"(für|Für) 2026-11\b", text), text)
                self.assertNotIn("--period 2026-11", text)
            self.assertTrue(any("2026-10" in text for _, text in actions))
            self.assertTrue(any("Newsletter" in text for _, text in actions))

    def test_manual_export_is_only_demanded_after_its_due_date(self):
        with tempfile.TemporaryDirectory() as tmp, TempRepo(tmp) as repo:
            repo.ledger(voller_monat("2026-10"))
            repo.meta("2026-11-02")
            quellen = strategie()["measurement"]["sources"]
            strategy = strategie(quellen=quellen)
            strategy["measurement"]["manual_due_day"] = 10
            lage = ae.build_lage(strategy, AS_OF)
            quelle = next(q for q in lage["quellen"] if q["id"] == "newsletter")
            self.assertEqual(quelle["status"], "noch_nicht_faellig")
            self.assertEqual(quelle["faellig"], dt.date(2026, 11, 10))
            _, actions, _, _ = ae.evaluate(strategy, {"evidence": []}, AS_OF, lage=lage)
            self.assertFalse(any("Newsletter" in text for _, text in actions))

    def test_evaluate_is_quiet_when_every_source_is_proven(self):
        with tempfile.TemporaryDirectory() as tmp, TempRepo(tmp) as repo:
            repo.ledger(voller_monat("2026-10", klicks=2, impressionen=9))
            repo.meta("2026-11-02")
            repo.audience("2026-10", {"newsletter_subscribers": 42, "newsletter_click_rate": 0.08})
            strategy = strategie()
            lage = ae.build_lage(strategy, AS_OF)
            quarter, actions, _, _ = ae.evaluate(strategy, {"evidence": []}, AS_OF, lage=lage)
            self.assertEqual(actions, [])
            self.assertEqual(quarter, "2026-Q4")

    def test_not_active_source_with_signals_demands_contract_update(self):
        with tempfile.TemporaryDirectory() as tmp, TempRepo(tmp) as repo:
            repo.ledger(voller_monat("2026-10"))
            repo.meta("2026-11-02")
            repo.audience("2026-10", {"newsletter_subscribers": 1, "newsletter_click_rate": 0.0})
            ae.KLICKMESSUNG.write_text("aktiv: true\n", encoding="utf-8")
            strategy = strategie()
            lage = ae.build_lage(strategy, AS_OF)
            _, actions, _, _ = ae.evaluate(strategy, {"evidence": []}, AS_OF, lage=lage)
            self.assertTrue(any("Signale" in text for _, text in actions))

    def test_brand_window_is_rolling_and_never_a_month_value(self):
        with tempfile.TemporaryDirectory() as tmp, TempRepo(tmp) as repo:
            repo.meta("2026-11-02")
            repo.queries([
                {"suchbegriff": "Franks Finanzcheck", "clicks": 3, "impressions": 7,
                 "ctr": 0.4, "position": 1.0},
                {"suchbegriff": "strom sparen", "clicks": 1, "impressions": 3,
                 "ctr": 0.3, "position": 8.0},
            ])
            fenster = ae.brand_window(ae.load_gsc())
            self.assertEqual(fenster["marken_clicks"], 3)
            self.assertEqual(fenster["impressionen"], 10)
            self.assertEqual(fenster["anteil"], 0.7)
            self.assertEqual(fenster["von"], "2026-10-06")
            self.assertEqual(fenster["bis"], "2026-11-02")
            self.assertIsNone(ae.brand_window({"meta": {}, "queries": []}))

    # ---------------------------------------------------------------- Report

    def _report(self, strategy, lage, actions, evidence=None):
        ae.write_report(strategy, evidence or {"evidence": []}, lage, "2026-Q4", actions)
        return ae.REPORT.read_text(encoding="utf-8")

    def test_report_separates_zero_from_unknown(self):
        with tempfile.TemporaryDirectory() as tmp, TempRepo(tmp) as repo:
            repo.ledger(voller_monat("2026-10", klicks=0, impressionen=5))
            repo.meta("2026-11-02")
            strategy = strategie()
            lage = ae.build_lage(strategy, AS_OF)
            quarter, actions, _, _ = ae.evaluate(strategy, {"evidence": []}, AS_OF, lage=lage)
            text = self._report(strategy, lage, actions)
            self.assertIn("| GSC-Klicks | 0 |", text)
            self.assertIn("| GSC-Impressionen | 155 |", text)
            self.assertIn("| Marken-Klicks | — |", text)
            self.assertIn("| Newsletter-Abonnenten | — |", text)
            self.assertIn("| Wiederkehrende Leser | — |", text)
            self.assertIn("31/31 Tage", text)

    def test_report_without_data_claims_nothing(self):
        with tempfile.TemporaryDirectory() as tmp, TempRepo(tmp):
            strategy = strategie()
            lage = ae.build_lage(strategy, AS_OF)
            quarter, actions, _, _ = ae.evaluate(strategy, {"evidence": []}, AS_OF, lage=lage)
            text = self._report(strategy, lage, actions)
            self.assertIn("| GSC-Klicks | — |", text)
            self.assertIn("0/31", text)
            self.assertIn("Unbekannt bleibt unbekannt", text)
            self.assertNotIn("| Newsletter-Abonnenten | 0 |", text)

    def test_report_lists_verified_evidence_with_publisher(self):
        with tempfile.TemporaryDirectory() as tmp, TempRepo(tmp) as repo:
            repo.ledger(voller_monat("2026-10"))
            repo.meta("2026-11-02")
            repo.audience("2026-10", {"newsletter_subscribers": 5, "newsletter_click_rate": 0.1})
            evidence = {"evidence": [{
                "id": "beleg-1", "kind": "editorial_link", "title": "Strompreise erklärt",
                "publisher": "Beispielmedium", "url": "https://medium.example/beitrag",
                "published": "2026-10-20",
            }]}
            strategy = strategie()
            lage = ae.build_lage(strategy, AS_OF)
            quarter, actions, _, _ = ae.evaluate(strategy, evidence, AS_OF, lage=lage)
            text = self._report(strategy, lage, actions, evidence)
            self.assertIn("| 2026-10-20 | Redaktioneller Link | [Strompreise erklärt](https://medium.example/beitrag) | Beispielmedium |", text)
            self.assertIn("| Redaktionelle Links | 1 |", text)

    def test_json_output_contains_no_search_queries(self):
        with tempfile.TemporaryDirectory() as tmp, TempRepo(tmp) as repo:
            repo.ledger(voller_monat("2026-10"))
            repo.meta("2026-11-02")
            repo.queries([{"suchbegriff": "geheime suchanfrage", "clicks": 1, "impressions": 2}])
            strategy = strategie()
            lage = ae.build_lage(strategy, AS_OF)
            quarter, actions, _, _ = ae.evaluate(strategy, {"evidence": []}, AS_OF, lage=lage)
            daten = ae.radar_json(strategy, {"evidence": []}, lage, quarter, actions)
            text = json.dumps(daten, ensure_ascii=False)
            self.assertNotIn("geheime suchanfrage", text)
            self.assertEqual(daten["reporting_month"], "2026-10")
            self.assertEqual(daten["gsc"]["status"], "frisch")
            self.assertEqual(daten["kpis"]["gsc_clicks"], 0)

    def test_json_is_serializable_with_yaml_dates(self):
        """YAML liefert echte `date`-Objekte – das JSON muss trotzdem schreiben."""
        strategy = ae.load_yaml(ae.STRATEGY)
        evidence = ae.load_yaml(ae.EVIDENCE)
        lage = ae.build_lage(strategy, AS_OF)
        quarter, actions, _, _ = ae.evaluate(strategy, evidence, AS_OF, lage=lage)
        text = json.dumps(ae.radar_json(strategy, evidence, lage, quarter, actions), ensure_ascii=False)
        self.assertIn("2026-10", text)

    # ----------------------------------------------------------------- Assets

    def test_asset_readiness_needs_all_five_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp, TempRepo(tmp) as repo:
            (repo.root / "content/studien/asset/index.md").exists() or \
                (repo.root / "content/studien/asset").mkdir(parents=True)
            (repo.root / "content/studien/asset/index.md").write_text(
                "---\ntitle: Asset\n---\n\n## Methodik\n\nText\n", encoding="utf-8")
            (repo.root / "static/downloads").mkdir(parents=True)
            (repo.root / "static/downloads/asset.csv").write_text("a,b\n1,2\n", encoding="utf-8")
            asset = {"id": "asset-1", "status": "live", "canonical": "/studien/asset/",
                     "methodology": "/studien/asset/#methodik",
                     "dataset": "/downloads/asset.csv", "press_asset": "/downloads/asset.svg",
                     "published": "2026-10-02",
                     "source_urls": ["https://a.example/x", "https://b.example/y"]}
            strategy = {"meta": {"minimum_linkable_assets_per_quarter": 1},
                        "quarters": [], "assets": [asset],
                        "measurement": {"sources": strategie()["measurement"]["sources"],
                                        "periods": []}}
            errors = ae.validate(strategy, {"evidence": []})
            self.assertTrue(any("Presseformat" in e or "asset.svg" in e for e in errors))
            reife = dict(ae._asset_reife(asset))
            self.assertTrue(reife["Inhaltsseite"] and reife["Methodik-Anker"] and reife["Datensatz/CSV"])
            self.assertFalse(reife["Presseformat"])
            (repo.root / "static/downloads/asset.svg").write_text("<svg/>", encoding="utf-8")
            self.assertTrue(dict(ae._asset_reife(asset))["Presseformat"])

    def test_missing_methodology_anchor_is_a_contract_error(self):
        with tempfile.TemporaryDirectory() as tmp, TempRepo(tmp) as repo:
            (repo.root / "content/studien/asset").mkdir(parents=True)
            (repo.root / "content/studien/asset/index.md").write_text("## Quellen\n", encoding="utf-8")
            (repo.root / "static/downloads").mkdir(parents=True)
            for name in ("asset.csv", "asset.svg"):
                (repo.root / "static/downloads" / name).write_text("x", encoding="utf-8")
            asset = {"id": "asset-1", "status": "live", "canonical": "/studien/asset/",
                     "methodology": "/studien/asset/#methodik",
                     "dataset": "/downloads/asset.csv", "press_asset": "/downloads/asset.svg",
                     "published": "2026-10-02",
                     "source_urls": ["https://a.example/x", "https://b.example/y"]}
            strategy = {"meta": {"minimum_linkable_assets_per_quarter": 1},
                        "quarters": [], "assets": [asset],
                        "measurement": {"sources": strategie()["measurement"]["sources"],
                                        "periods": []}}
            errors = ae.validate(strategy, {"evidence": []})
            self.assertTrue(any("Methodik-Anker" in e for e in errors))


if __name__ == "__main__":
    unittest.main()

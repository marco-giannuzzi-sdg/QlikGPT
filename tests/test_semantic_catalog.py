"""Pure validation tests for multi-app Semantic Catalog (no Qlik credentials needed)."""
from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ci"))
import semantic_catalog as sc


class CatalogValidationTests(unittest.TestCase):
    def setUp(self):
        self.catalog = sc.read_json(sc.CATALOG)
        self.manifests = {key: sc.read_json(path)
                          for key, path in sc.MANIFESTS.items()}

    def test_all_current_master_measures_have_valid_semantic_format(self):
        cfg = sc.formatting_contract()
        self.assertEqual(cfg["locale"], "it-IT")
        styles = {m["id"]: sc.metric_style(m) for m in self.catalog["measures"]}
        self.assertEqual(styles["qlikgpt_shared_revenue"]["format"]["qType"], "M")
        self.assertEqual(styles["qlikgpt_shared_orders"]["format"]["qnDec"], 0)
        self.assertEqual(styles["qlikgpt_shared_margin_pct"]["format"]["qFmt"], "0,0%")
        self.assertEqual(styles["qlikgpt_shared_revenue"]["color"], "#142B49")

    def test_master_format_is_verified_in_full_not_only_pattern(self):
        item = self.catalog["measures"][0]
        expected = sc.qix_metric_properties(item)
        self.assertEqual(sc.format_differences(expected, item), [])
        altered = deepcopy(expected)
        altered["qMeasure"]["qNumFormat"]["qDec"] = "."
        self.assertIn("format", sc.format_differences(altered, item))
        altered = deepcopy(expected)
        altered["qMeasure"]["qNumFormat"]["qUseThou"] = 0
        self.assertIn("format", sc.format_differences(altered, item))

    def test_color_drift_detected(self):
        item = self.catalog["measures"][0]
        stored = sc.qix_metric_properties(item)
        stored["qMeasure"]["coloring"]["baseColor"]["color"] = "#FF0000"
        self.assertIn("color", sc.format_differences(stored, item))

    def test_invalid_preset_and_color_role_rejected(self):
        for key, value in (("formatPreset", "unknown"), ("colorRole", "unknown")):
            invalid = deepcopy(self.catalog)
            invalid["measures"][0][key] = value
            with self.assertRaisesRegex(ValueError, "unknown"):
                sc.validate_catalog(invalid, self.manifests)

    def test_formatting_preset_changes_target_all_subscribers(self):
        definitions = sc.validate_catalog(self.catalog, self.manifests)
        self.assertEqual(
            sc.determine_impacted(
                definitions, self.manifests, {"catalog/formatting.json"}, False, False
            ),
            {"presentation", "presentation2"},
        )

    def test_unassigned_measure_still_has_format_without_being_deployed(self):
        item = next(m for m in self.catalog["measures"]
                    if m["id"] == "qlikgpt_shared_average_order")
        self.assertEqual(sc.metric_style(item)["format"]["qFmt"], "€ #.##0,00")
        self.assertFalse(any(item["id"] in v["catalogMeasures"]
                             for v in self.manifests.values()))

    def test_valid_catalog(self):
        values = sc.validate_catalog(self.catalog, self.manifests)
        self.assertGreaterEqual(len(values), 5)
        self.assertTrue(
            {"qlikgpt_shared_revenue", "qlikgpt_shared_orders",
             "qlikgpt_shared_margin", "qlikgpt_shared_margin_pct"}
            .issubset(self.manifests["presentation"]["catalogMeasures"])
        )
        self.assertTrue(
            {"qlikgpt_shared_revenue", "qlikgpt_shared_margin_pct"}
            .issubset(self.manifests["presentation2"]["catalogMeasures"])
        )

    def test_unassigned_measure_is_valid_and_unaffected(self):
        catalog = sc.validate_catalog(self.catalog, self.manifests)
        self.assertIn("qlikgpt_shared_average_order", catalog)
        hypothetical = deepcopy(self.manifests)
        for app in hypothetical.values():
            app["catalogMeasures"] = [
                x for x in app["catalogMeasures"]
                if x != "qlikgpt_shared_average_order"
            ]
        with patch.object(sc, "changed_metric_ids", return_value={"qlikgpt_shared_average_order"}):
            affected = sc.determine_impacted(
                catalog, hypothetical, {"catalog/measures.json"}, False, False)
        self.assertEqual(affected, set())

    def test_future_subscription_activates_existing_catalog_metric(self):
        catalog = sc.validate_catalog(self.catalog, self.manifests)
        future = deepcopy(self.manifests)
        future["presentation2"]["catalogMeasures"].append("qlikgpt_shared_average_order")
        self.assertEqual(
            sc.determine_impacted(catalog, future, {"apps/presentation2.json"}, False, False),
            {"presentation2"},
        )

    def test_inline_measure_in_app_is_rejected(self):
        invalid = deepcopy(self.manifests)
        # The actual dashboard JSON validation should fail if a qLibraryId
        # is missing, rather than silently allowing duplicated expressions.
        from unittest.mock import mock_open
        original = Path.read_text
        def read(path, *args, **kwargs):
            if str(path).endswith("apps/presentation1-objects.json"):
                content = json.loads(original(path, *args, **kwargs))
                visual = next(v for v in content[0]["qChildren"] if v.get("qHyperCubeDef"))
                visual["qHyperCubeDef"]["qMeasures"][0] = {"qDef":{"qDef":"Sum(Revenue)"}}
                return json.dumps(content)
            return original(path, *args, **kwargs)
        with patch.object(Path, "read_text", read):
            with self.assertRaisesRegex(ValueError, "inline measure"):
                sc.validate_catalog(self.catalog, invalid)

    def test_duplicate_id_rejected(self):
        invalid = deepcopy(self.catalog)
        invalid["measures"].append(deepcopy(invalid["measures"][0]))
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            sc.validate_catalog(invalid, self.manifests)

    def test_unknown_measure_subscription_rejected(self):
        invalid = deepcopy(self.manifests)
        invalid["presentation2"]["catalogMeasures"].append("missing_catalog_measure")
        with self.assertRaisesRegex(ValueError, "unknown subscribed"):
            sc.validate_catalog(self.catalog, invalid)

    def test_malformed_expression_rejected(self):
        invalid = deepcopy(self.catalog)
        invalid["measures"][0]["expression"] = "Sum(Revenue); DROP TABLE Sales;"
        with self.assertRaisesRegex(ValueError, "invalid/multiline"):
            sc.validate_catalog(invalid, self.manifests)

    def test_impact_analysis_shared_metric_targets_both(self):
        catalog = sc.validate_catalog(self.catalog, self.manifests)
        with patch.object(sc, "changed_metric_ids", return_value={"qlikgpt_shared_revenue"}):
            result = sc.determine_impacted(
                catalog, self.manifests, {"catalog/measures.json"}, False, False)
        self.assertEqual(result, {"presentation", "presentation2"})

    def test_impact_analysis_non_shared_targets_one(self):
        catalog = sc.validate_catalog(self.catalog, self.manifests)
        with patch.object(sc, "changed_metric_ids", return_value={"qlikgpt_shared_orders"}):
            result = sc.determine_impacted(
                catalog, self.manifests, {"catalog/measures.json"}, False, False)
        self.assertEqual(result, {"presentation"})

    def test_unrelated_frontend_has_no_semantic_changes(self):
        catalog = sc.validate_catalog(self.catalog, self.manifests)
        result = sc.determine_impacted(
            catalog, self.manifests, {"frontend/objects.json"}, False, False)
        self.assertEqual(result, set())

    def test_app2_manifest_targets_only_app2(self):
        catalog = sc.validate_catalog(self.catalog, self.manifests)
        result = sc.determine_impacted(
            catalog, self.manifests, {"apps/presentation2.json"}, False, False)
        self.assertEqual(result, {"presentation2"})


if __name__ == "__main__":
    unittest.main()

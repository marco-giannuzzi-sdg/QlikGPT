"""Pure validation tests for multi-app Semantic Catalog (no Qlik credentials needed)."""
from __future__ import annotations
from copy import deepcopy
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

    def test_valid_catalog(self):
        values = sc.validate_catalog(self.catalog, self.manifests)
        self.assertEqual(len(values), 5)
        self.assertEqual(
            set(self.manifests["presentation"]["catalogMeasures"]),
            {"qlikgpt_shared_revenue", "qlikgpt_shared_orders",
             "qlikgpt_shared_margin", "qlikgpt_shared_margin_pct"},
        )
        self.assertEqual(
            set(self.manifests["presentation2"]["catalogMeasures"]),
            {"qlikgpt_shared_revenue", "qlikgpt_shared_margin_pct"},
        )

    def test_unassigned_measure_is_valid_and_unaffected(self):
        catalog = sc.validate_catalog(self.catalog, self.manifests)
        self.assertIn("qlikgpt_shared_average_order", catalog)
        self.assertFalse(any(
            "qlikgpt_shared_average_order" in m["catalogMeasures"]
            for m in self.manifests.values()
        ))
        with patch.object(sc, "changed_metric_ids", return_value={"qlikgpt_shared_average_order"}):
            affected = sc.determine_impacted(
                catalog, self.manifests, {"catalog/measures.json"}, False, False)
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
        with patch.object(sc, "changed_metric_ids", return_value={"qlikgpt_shared_margin_pct"}):
            result = sc.determine_impacted(
                catalog, self.manifests, {"catalog/measures.json"}, False, False)
        self.assertEqual(result, {"presentation2"})

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

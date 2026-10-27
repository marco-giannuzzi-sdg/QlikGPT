"""QlikGPT Semantic Catalog 2.0 regressions: local, no Qlik API required."""
from __future__ import annotations
from copy import deepcopy
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"ci"))
import semantic_assets as assets
import catalog_report as report
import semantic_catalog as metrics


class CatalogV2Tests(unittest.TestCase):
    def setUp(self):
        self.dims,self.vars=assets.catalogs()
        self.manifests={key:metrics.read_json(path) for key,path in metrics.MANIFESTS.items()}

    def test_governed_dimensions_and_variables(self):
        assets.validate_subscriptions(self.manifests,self.dims,self.vars)
        self.assertEqual(len(self.dims),6)
        self.assertEqual(self.dims["qlikgpt_d_market"]["fields"],["Market"])
        self.assertEqual(len(self.manifests["presentation"]["catalogDimensions"]),5)
        self.assertEqual(len(self.manifests["presentation2"]["catalogDimensions"]),2)
        self.assertFalse(any("dimensionSource" in v for v in self.manifests.values()))

    def test_unused_items_available_for_future_subscription(self):
        self.assertTrue(all("qlikgpt_d_quarter" not in m["catalogDimensions"] for m in self.manifests.values()))
        self.assertTrue(all("qlikgpt_v_currency_label" not in m["catalogVariables"] for m in self.manifests.values()))
        future=deepcopy(self.manifests)
        future["presentation2"]["catalogDimensions"].append("qlikgpt_d_quarter")
        future["presentation2"]["catalogVariables"].append("qlikgpt_v_currency_label")
        assets.validate_subscriptions(future,self.dims,self.vars)

    def test_invalid_subscription_is_rejected(self):
        wrong=deepcopy(self.manifests)
        wrong["presentation"]["catalogDimensions"].append("qlikgpt_d_unknown")
        with self.assertRaisesRegex(ValueError,"unknown"):
            assets.validate_subscriptions(wrong,self.dims,self.vars)

    def test_changed_unused_dimension_has_zero_impacted_apps(self):
        with patch.object(assets,"changed_definitions",return_value={"qlikgpt_d_quarter"}):
            self.assertEqual(assets.impacted(self.manifests,{"catalog/dimensions.json"},
                                            self.dims,self.vars),set())

    def test_changed_shared_variable_impacts_both_apps(self):
        with patch.object(assets,"changed_definitions",return_value={"qlikgpt_v_target_margin"}):
            self.assertEqual(assets.impacted(self.manifests,{"catalog/variables.json"},
                                            self.dims,self.vars),
                             {"presentation","presentation2"})

    def test_qix_dimension_variable_readback(self):
        d=assets.dimension_properties(self.dims["qlikgpt_d_market"])
        self.assertEqual(assets.mismatch(d,d,"dimensions"),[])
        wrong=deepcopy(d)
        wrong["qDim"]["qFieldDefs"]=["Channel"]
        self.assertIn("qDim.qFieldDefs",assets.mismatch(wrong,d,"dimensions"))
        v=assets.variable_properties(self.vars["qlikgpt_v_target_margin"])
        self.assertEqual(assets.mismatch(v,v,"variables"),[])
        wrong=deepcopy(v)
        wrong["qDefinition"]="0.5"
        self.assertIn("qDefinition",assets.mismatch(wrong,v,"variables"))

    def test_usage_report_full_matrix_and_inline_warning(self):
        r=report.generate()
        self.assertEqual(len(r["apps"]),2)
        self.assertEqual(len(r["items"]),13)
        rev=next(m for m in r["items"] if m["id"]=="qlikgpt_shared_revenue")
        self.assertEqual(set(rev["apps"]),{"presentation","presentation2"})
        self.assertEqual(len(rev["visuals"]),4)
        unused=next(m for m in r["items"] if m["id"]=="qlikgpt_shared_average_order")
        self.assertEqual(unused["apps"],[])
        d=next(m for m in r["items"] if m["id"]=="qlikgpt_d_market")
        self.assertEqual(len(d["apps"]),2)
        self.assertEqual(d["visuals"],[])
        self.assertTrue(any("dimensione inline" in w for w in r["warnings"]))
        self.assertIn("Matrice delle dipendenze",report.render(r))

    def test_unsubscribed_library_measure_rejected(self):
        apps=report.read_apps()
        apps["presentation2"]["visuals"][0]["qChildren"][0]["qHyperCubeDef"]["qMeasures"][0]["qLibraryId"]="unknown"
        with patch.object(report,"read_apps",return_value=apps):
            with self.assertRaisesRegex(ValueError,"missing catalog subscription"):
                report.generate()


if __name__=="__main__":
    unittest.main()

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
        self.assertEqual(
            {(v["app"],v["visualId"]) for v in d["visuals"]},
            {("presentation","qlikgpt_chart_market"),
             ("presentation","qlikgpt_list_market")}
        )
        self.assertEqual(r["warnings"],[])
        ym = next(x for x in r["items"] if x["id"] == "qlikgpt_d_yearmonth")
        self.assertEqual(
            [(v["app"],v["visualId"]) for v in ym["visuals"]],
            [("presentation","qlikgpt_chart_month")],
        )
        self.assertIn("Matrice delle dipendenze",report.render(r))

    def test_unsubscribed_library_measure_rejected(self):
        apps=report.read_apps()
        apps["presentation2"]["visuals"][0]["qChildren"][0]["qHyperCubeDef"]["qMeasures"][0]["qLibraryId"]="unknown"
        with patch.object(report,"read_apps",return_value=apps):
            with self.assertRaisesRegex(ValueError,"missing catalog subscription"):
                report.generate()


    def test_chart_and_filter_dimensions_all_have_real_master_item_references(self):
        apps = report.read_apps()
        for key, app in apps.items():
            for sheet in app["visuals"]:
                for obj in report.nodes(sheet):
                    cube = obj.get("qHyperCubeDef", {})
                    for dim in cube.get("qDimensions", []):
                        self.assertIn(dim.get("qLibraryId"),app["catalogDimensions"])
                        self.assertFalse(any(
                            x.strip() for x in dim.get("qDef", {}).get("qFieldDefs", [])
                            if isinstance(x, str)
                        ))
                    for mea in cube.get("qMeasures", []):
                        self.assertIn(mea.get("qLibraryId"), app["catalogMeasures"])
            for filt in app["filters"]:
                self.assertIn(filt.get("dimensionId"),app["catalogDimensions"])
                self.assertNotIn("field",filt)

    def test_chart_inline_dimension_is_rejected_before_deployment(self):
        original = Path.read_text
        import json
        def patched(path,*args,**kwargs):
            body = original(path,*args,**kwargs)
            if str(path).endswith("apps/presentation1-objects.json"):
                sheets = json.loads(body)
                for child in sheets[0]["qChildren"]:
                    if child.get("qInfo",{}).get("qId")=="qlikgpt_chart_month":
                        child["qHyperCubeDef"]["qDimensions"][0]["qLibraryId"] = ""
                return json.dumps(sheets)
            return body
        with patch.object(Path,"read_text",patched):
            with self.assertRaisesRegex(ValueError,"inline dimension"):
                metrics.validate_catalog(metrics.read_json(metrics.CATALOG),self.manifests)

    def test_filter_without_master_item_is_rejected_by_impact_report(self):
        apps=report.read_apps()
        apps["presentation"]["filters"][0]["dimensionId"]="unknown"
        with patch.object(report,"read_apps",return_value=apps):
            with self.assertRaisesRegex(ValueError,"missing master dimension subscription"):
                report.generate()



if __name__=="__main__":
    unittest.main()

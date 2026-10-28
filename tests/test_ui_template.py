"""Reusable QlikGPT UI V1: colors, layout, navigation and app scaffold."""
from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"ci"))
import ui_template as ui

class NativeUITemplateTests(unittest.TestCase):
    def test_tokens_and_qext_theme_match(self):
        t=ui.tokens()
        self.assertEqual(t["templateId"],"qlikgpt-executive-v1")
        self.assertEqual(t["colors"]["navy"],"#142840")
        self.assertEqual(ui.read(ui.QEXT)["type"],"theme")
        self.assertEqual(t["colors"]["blue"],"#3365D5")
        self.assertEqual(t["colors"]["canvas"],"#F5F7FB")

    def test_existing_apps_conform_to_template(self):
        ui.check()
        for key,path in ui.MODEL.presentation_manifests().items():
            m=ui.read(path)
            self.assertEqual(m["uiTemplate"],"qlikgpt-executive-v1")
            sheets=ui.read(ui.ROOT/m["dashboardSource"])
            self.assertEqual(ui.validate_dashboard(sheets,ui.tokens(),key),1)

    def test_new_app_is_generated_without_touching_qvs_or_existing_apps(self):
        generated=ui.new_files(
            "presentation3","QlikGPT - PRODUCT ANALYTICS",
            ["qlikgpt_shared_revenue","qlikgpt_shared_margin_pct"]
        )
        self.assertEqual(len(generated),2)
        m=next(value for path,value in generated.items() if path.endswith("/presentation3.json"))
        sheet=next(value for path,value in generated.items() if path.endswith("-objects.json"))
        self.assertEqual(m["loadScript"],ui.MODEL.presentation_script)
        self.assertEqual(m["catalogMeasures"],["qlikgpt_shared_revenue","qlikgpt_shared_margin_pct"])
        self.assertEqual(ui.validate_dashboard(sheet,ui.tokens(),"new-app"),1)
        self.assertFalse(any("qDef" in child and child["qDef"] for child in sheet[0]["qChildren"]))
        self.assertEqual(sheet[0]["rows"],12)
        self.assertEqual(
            [x["qHyperCubeDef"]["qMeasures"][0]["qLibraryId"] for x in sheet[0]["qChildren"] if x["qInfo"]["qType"]=="kpi"],
            m["catalogMeasures"]
        )

    def test_no_unsafe_app_creation_or_invalid_subscriptions(self):
        with self.assertRaises(ValueError):
            ui.new_files("presentation2","Existing",["qlikgpt_shared_revenue"])
        with self.assertRaises(ValueError):
            ui.new_files("presentation3","New",["not_in_catalog"])
        with self.assertRaises(ValueError):
            ui.new_files("presentation3","New",["qlikgpt_shared_revenue"]*2)
        with self.assertRaises(ValueError):
            ui.new_files("presentation3","New",[])

    def test_layout_must_not_overlap(self):
        g=ui.new_files("presentation3","New",["qlikgpt_shared_revenue"])
        sheet=next(v for p,v in g.items() if p.endswith("-objects.json"))
        bad=deepcopy(sheet)
        bad[0]["cells"][2]["row"]=0
        with self.assertRaisesRegex(ValueError,"overlapping"):
            ui.validate_dashboard(bad,ui.tokens(),"overlap")

    def test_first_app_is_premium_18_row_grid_with_governed_objects(self):
        app=ui.read(ui.MODEL.root/"apps"/"presentation1-objects.json")[0]
        self.assertEqual(app["rows"],18)
        byid={o["qInfo"]["qId"]:o for o in app["qChildren"]}
        self.assertIn("qlikgpt_kpi_section",byid)
        self.assertIn("qlikgpt_insights_section",byid)
        self.assertNotIn("##",byid["qlikgpt_brand_header"]["markdown"])
        self.assertEqual(byid["qlikgpt_nav_shared_kpis"]["navigation"]["action"],"openWebsite")

    def test_navigation_is_native_and_https_only(self):
        t=ui.tokens()
        nav=ui.navigation_button("test_button","Go","https://tenant.qlikcloud.com/sense/app/some-app")
        self.assertEqual(nav["qInfo"]["qType"],"button")
        self.assertEqual(nav["navigation"]["action"],"openWebsite")
        with self.assertRaises(ValueError):
            ui.navigation_button("test_button","Go","http://unsafe/sense/app/x")

    def test_no_inline_measure_formulas_in_current_kpis(self):
        for key,path in ui.MODEL.presentation_manifests().items():
            m=ui.read(path)
            for sh in ui.read(ui.ROOT/m["dashboardSource"]):
                for obj in sh["qChildren"]:
                    if obj["qInfo"]["qType"]!="kpi":continue
                    measures=obj["qHyperCubeDef"]["qMeasures"]
                    self.assertTrue(measures)
                    for measure in measures:
                        self.assertIn(measure["qLibraryId"],m["catalogMeasures"])
                        self.assertFalse(measure.get("qDef",{}).get("qDef","").strip())

if __name__=="__main__":
    unittest.main()

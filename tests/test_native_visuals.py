"""Offline contract tests for native Qlik sheet geometry and theme-free UI."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import json
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"ci"))
from model_registry import ROOT
from deploy_visuals import sync_sheet_grid
import ui_template


class NativeSheetSyncTests(unittest.TestCase):
    def setUp(self):
        self.sheet=json.loads(
            (ROOT/"semantic-models/sales/apps/presentation1-objects.json")
            .read_text(encoding="utf-8")
        )[0]

    def test_grid_is_written_and_read_back(self):
        class FakeQix:
            def __init__(self):
                self.original={"qInfo":{"qId":"qlikgpt_sales_overview","qType":"sheet"},
                               "columns":24,"rows":13,"cells":[],"preserve":True}
                self.saved=deepcopy(self.original)
                self.calls=[]
            def call(self,handle,method,args):
                self.calls.append(method)
                if method=="GetProperties":return {"qProp":deepcopy(self.saved)}
                if method=="SetProperties":
                    self.saved=deepcopy(args[0]);return {}
                raise AssertionError(method)

        qix=FakeQix()
        sync_sheet_grid(qix,21,self.sheet)
        self.assertEqual(qix.saved["rows"],22)
        self.assertEqual(len(qix.saved["cells"]),12)
        self.assertTrue(qix.saved["preserve"])
        self.assertEqual(qix.saved["qInfo"],qix.original["qInfo"])
        self.assertEqual(qix.calls,["GetProperties","SetProperties","GetProperties"])

    def test_mismatched_grid_fails_loudly(self):
        class BrokenQix:
            def call(self,handle,method,args):
                if method=="GetProperties":
                    return {"qProp":{"qInfo":{"qId":"x"},"rows":18,
                                     "columns":24,"cells":[]}}
                if method=="SetProperties":return {}
                raise AssertionError(method)
        with self.assertRaisesRegex(RuntimeError,"dimensions did not persist"):
            sync_sheet_grid(BrokenQix(),10,self.sheet)

    def test_first_presentation_is_true_native_overview(self):
        sh=self.sheet
        self.assertEqual(sh["rows"],22)
        self.assertEqual(sh["background"]["color"],"#F5F7FB")
        ids={o["qInfo"]["qId"]:o for o in sh["qChildren"]}
        self.assertEqual(len(ids),12)
        self.assertEqual(
            ids["qlikgpt_chart_month"]["lineType"],"area"
        )
        for ident in ("qlikgpt_kpi_revenue","qlikgpt_kpi_orders",
                      "qlikgpt_kpi_margin","qlikgpt_kpi_margin_pct",
                      "qlikgpt_chart_month","qlikgpt_chart_market"):
            st=ids[ident]["style"]
            self.assertEqual(st["border"]["radius"],12)
            self.assertEqual(st["shadow"]["size"],"small")
            self.assertEqual(st["border"]["color"]["color"],"#E3E9F1")
        for o in ids.values():
            for m in o.get("qHyperCubeDef",{}).get("qMeasures",[]):
                self.assertTrue(m["qLibraryId"])
                self.assertFalse(m.get("qDef",{}).get("qDef","").strip())

    def test_generator_cannot_depend_on_custom_theme_files(self):
        self.assertEqual(ui_template.tokens()["grid"]["columns"],24)
        sc=ui_template.sheet(
            "presentation3","Independent Finance Overview",
            [("qlikgpt_shared_revenue","Revenue")],
            "https://tenant.qlikcloud.com/sense/app/known",
        )
        self.assertEqual(sc[0]["rows"],22)
        self.assertEqual(ui_template.validate_dashboard(sc,ui_template.tokens(),"future"),1)


if __name__=="__main__":
    unittest.main()

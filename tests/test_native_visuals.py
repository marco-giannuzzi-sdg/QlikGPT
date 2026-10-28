"""Offline contract tests for native Qlik sheet geometry and theme-free UI."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import json
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"ci"))
from model_registry import ROOT
from deploy_visuals import sync_sheet_grid, overview_tree, validate_tree, validate_retired, nodes, property_tree
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
        self.assertEqual(qix.saved["rows"],40)
        self.assertEqual(len(qix.saved["cells"]),14)
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
        self.assertEqual(sh["rows"],40)
        self.assertEqual(sh["background"]["color"],"#F2F2F2")
        ids={o["qInfo"]["qId"]:o for o in sh["qChildren"]}
        self.assertEqual(len(ids),14)
        self.assertEqual(
            ids["qlikgpt_chart_month"]["lineType"],"area"
        )
        for ident in ("qlikgpt_kpi_revenue","qlikgpt_kpi_orders",
                      "qlikgpt_kpi_margin","qlikgpt_kpi_margin_pct",
                      "qlikgpt_chart_month","qlikgpt_chart_market"):
            st=next(c for c in ids[ident]["components"] if c["key"]=="general")
            self.assertEqual(st["borderRadius"],"16px")
            self.assertEqual(st["borderWidth"],"1px")
            self.assertEqual(st["borderColor"]["color"],"#E5EBF3")
        for o in ids.values():
            for m in o.get("qHyperCubeDef",{}).get("qMeasures",[]):
                self.assertTrue(m["qLibraryId"])
                self.assertFalse(m.get("qDef",{}).get("qDef","").strip())

    def test_cli_adapter_preserves_json_and_adds_real_master_bound_filter_children(self):
        original=deepcopy(self.sheet)
        filters=json.loads((ROOT/"semantic-models/sales/apps/presentation1-filters.json").read_text())
        tree=overview_tree([self.sheet],filters)
        self.assertEqual(self.sheet,original)
        objects={p["qInfo"]["qId"]:p for p in nodes(tree)}
        self.assertEqual(len(objects),18)
        self.assertNotIn("qChildren",tree["qProperty"])
        for f in filters:
            self.assertEqual(objects[f["id"]]["qListObjectDef"]["qLibraryId"],f["dimensionId"])
        manifest=json.loads((ROOT/"semantic-models/sales/apps/presentation1.json").read_text())
        validate_tree(tree,manifest)

    def test_unmanaged_children_cannot_be_removed_by_cli_import(self):
        previous=property_tree(self.sheet)
        previous["qChildren"].append({"qProperty":{"qInfo":{"qId":"user-chart","qType":"kpi"}}})
        with self.assertRaisesRegex(RuntimeError,"Unmanaged child"):
            validate_retired(previous,{p["qInfo"]["qId"] for p in nodes(property_tree(self.sheet))})

    def test_missing_table_column_metadata_is_rejected_before_deploy(self):
        filters=json.loads((ROOT/"semantic-models/sales/apps/presentation1-filters.json").read_text())
        tree=overview_tree([self.sheet],filters)
        table=next(p for p in nodes(tree) if p["qInfo"]["qType"]=="table")
        table["qHyperCubeDef"]["columnWidths"].pop()
        manifest=json.loads((ROOT/"semantic-models/sales/apps/presentation1.json").read_text())
        with self.assertRaisesRegex(ValueError,"column metadata"):
            validate_tree(tree,manifest)

    def test_connection_retry_does_not_replay_engine_operations(self):
        from types import SimpleNamespace
        from unittest.mock import Mock, patch
        from deploy_visuals import Qix
        socket=Mock()
        connect=Mock(side_effect=[TimeoutError("network"),socket])
        with patch.dict(sys.modules,{"websocket":SimpleNamespace(create_connection=connect)}), \
             patch.dict("os.environ",{"QLIK_TENANT":"https://example.qlikcloud.com","QLIK_API_KEY":"test-only"}), \
             patch("deploy_visuals.time.sleep"):
            client=Qix("test-app")
        self.assertEqual(connect.call_count,2)
        socket.send.assert_not_called()
        self.assertEqual(client.request_id,0)

    def test_non_network_connection_error_is_not_retried(self):
        from types import SimpleNamespace
        from unittest.mock import Mock, patch
        from deploy_visuals import Qix
        connect=Mock(side_effect=ValueError("invalid handshake"))
        with patch.dict(sys.modules,{"websocket":SimpleNamespace(create_connection=connect)}), \
             patch.dict("os.environ",{"QLIK_TENANT":"https://example.qlikcloud.com","QLIK_API_KEY":"test-only"}):
            with self.assertRaises(ValueError):
                Qix("test-app")
        self.assertEqual(connect.call_count,1)

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

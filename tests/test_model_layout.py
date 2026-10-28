"""Regression tests for reorganized semantic-model directory without changing Qlik IDs."""
from __future__ import annotations
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"ci"))
import model_registry as registry
import deployment_plan as planner
import app_lineage


class ModelLayoutTests(unittest.TestCase):
    def test_sales_model_and_catalog_paths(self):
        m=registry.active_model()
        self.assertEqual(m.id,"sales")
        self.assertEqual(m.prefix,"semantic-models/sales")
        self.assertEqual(set(m.presentation_manifests()),{"presentation","presentation2"})
        self.assertEqual(len(m.etl_apps()),2)
        self.assertEqual(len(registry.discover_models()),1)
        for kind in ("measures","dimensions","variables","formatting"):
            self.assertTrue(m.catalog(kind).is_file())

    def test_app_ids_preserved(self):
        m=registry.active_model()
        ids=json.loads(m.state_path.read_text(encoding="utf-8"))
        self.assertEqual(ids["etl1"],"932480d2-415d-4535-9267-c699f44c55c6")
        self.assertEqual(ids["etl2"],"70ba9d05-24b7-46ec-8b8c-560e8169c3d1")
        self.assertEqual(ids["presentation"],"07dfa926-4895-4fb2-af4c-eac90e9eb2cb")
        self.assertEqual(ids["presentation2"],"04280b14-6ba5-4fe9-90d6-2ff8fa1c994f")
        for key,path in m.presentation_manifests().items():
            item=json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(item["loadScript"],m.presentation_script)
            self.assertTrue((registry.ROOT/item["dashboardSource"]).is_file())

    def test_flat_legacy_sources_removed(self):
        for name in ("scripts","apps","catalog","lineage","design","deployment"):
            self.assertFalse((registry.ROOT/name).exists(),name)

    def test_deploy_only_selective_with_moved_scripts(self):
        m=registry.active_model()
        graph=app_lineage.build(app_lineage.registry())
        plan=planner.plan(graph,{m.prefix+"/scripts/etl2.qvs"},"deploy-only")
        self.assertEqual(plan["scripts"],["etl2"])
        self.assertEqual(plan["reloads"],[])
        plan=planner.plan(graph,{m.presentation_script},"deploy-only")
        self.assertEqual(plan["scripts"],["presentation","presentation2"])
        self.assertEqual(plan["reloads"],[])

    def test_lineage_unchanged(self):
        graph=app_lineage.build(app_lineage.registry())
        self.assertEqual(len(graph["resources"]),2)
        self.assertEqual(len(graph["connections"]),3)
        self.assertEqual(graph["impact"]["etl1"]["transitive"],
                         ["etl2","presentation","presentation2"])

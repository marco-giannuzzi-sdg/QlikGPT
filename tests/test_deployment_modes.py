"""No reload on Git commits, explicit single-app and downstream chain plans."""
from __future__ import annotations

from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"ci"))

import app_lineage
import deployment_plan as planner
import reload_chain


class DeploymentPlanTests(unittest.TestCase):
    def setUp(self):
        self.graph = app_lineage.build(app_lineage.registry())

    def test_push_etl2_script_only_no_data_reload(self):
        p = planner.plan(self.graph, {"scripts/etl2.qvs"}, "deploy-only")
        self.assertEqual(p["scripts"], ["etl2"])
        self.assertEqual(p["reloads"], [])

    def test_push_etl1_only_does_not_regenerate_downstream(self):
        p = planner.plan(self.graph, {"scripts/etl1.qvs"}, "deploy-only")
        self.assertEqual(p["scripts"], ["etl1"])
        self.assertEqual(p["reloads"], [])

    def test_push_shared_presentation_script_updates_both_no_reload(self):
        p = planner.plan(self.graph, {"scripts/presentation.qvs"}, "deploy-only")
        self.assertEqual(p["scripts"], ["presentation", "presentation2"])
        self.assertEqual(p["reloads"], [])

    def test_catalog_ci_or_docs_commit_does_not_apply_any_script(self):
        p = planner.plan(self.graph, {"ci/deployment_plan.py", "catalog/measures.json"},
                         "deploy-only")
        self.assertEqual(p["scripts"], [])
        self.assertEqual(p["reloads"], [])

    def test_single_reload_does_not_touch_downstream(self):
        p=planner.plan(self.graph,set(),"reload-app","etl2")
        self.assertEqual(p["scripts"], ["etl2"])
        self.assertEqual(p["reloads"], ["etl2"])

    def test_single_presentation_reload_isolated(self):
        p=planner.plan(self.graph,set(),"reload-app","presentation2")
        self.assertEqual(p["reloads"], ["presentation2"])

    def test_chain_from_etl2_never_runs_etl1(self):
        p=planner.plan(self.graph,set(),"reload-chain","etl2")
        self.assertEqual(p["reloads"], ["etl2","presentation","presentation2"])
        self.assertEqual(p["scripts"], p["reloads"])
        self.assertNotIn("etl1",p["reloads"])

    def test_chain_from_etl1_reloads_all_in_dependency_order(self):
        p=planner.plan(self.graph,set(),"reload-chain","etl1")
        self.assertEqual(p["reloads"], ["etl1","etl2","presentation","presentation2"])

    def test_chain_from_presentation_does_not_touch_upstream(self):
        p=planner.plan(self.graph,set(),"reload-chain","presentation")
        self.assertEqual(p["reloads"],["presentation"])

    def test_explicit_deploy_selected_only(self):
        p=planner.plan(self.graph,set(),"deploy-only","etl2")
        self.assertEqual(p["scripts"],["etl2"])
        self.assertEqual(p["reloads"],[])

    def test_unknown_operation_and_unknown_app_are_rejected(self):
        with self.assertRaisesRegex(ValueError,"Unknown Qlik deployment mode"):
            planner.plan(self.graph,set(),"full","etl1")
        with self.assertRaisesRegex(ValueError,"requires a valid explicit target"):
            planner.plan(self.graph,set(),"reload-chain","")
        with self.assertRaisesRegex(ValueError,"Unknown deployment target"):
            planner.plan(self.graph,set(),"deploy-only","ghost")

    def test_cycle_in_reload_graph_blocks_plan(self):
        g={**self.graph}
        g["connections"]=list(self.graph["connections"])+[
            {"upstream":"presentation","downstream":"etl1","resources":["fake.qvd"]}
        ]
        with self.assertRaisesRegex(ValueError,"Cycle"):
            planner.plan(g,set(),"reload-chain","etl1")

    def test_reload_success_must_be_observed_before_next_enqueue(self):
        events=[]
        polls={}
        def rest(method,path,body=None):
            if method=="POST":
                ident=body["appId"]
                events.append("start:"+ident)
                return {"id":ident+"-reload"}
            if method=="GET":
                ident=path.split("/")[-1].removesuffix("-reload")
                polls[ident]=polls.get(ident,0)+1
                events.append("poll:"+ident)
                return {"status":"RELOADING" if polls[ident]==1 else "SUCCEEDED"}
            raise AssertionError(method)
        apps={
            "etl2":{"appId":"a"},
            "presentation":{"appId":"b"},
        }
        result=reload_chain.run_chain(
            apps,["etl2","presentation"],rest,
            execute_reload=lambda k,id,api: reload_chain.reload_one(
                k,id,api,sleep=lambda _:None,clock=lambda:0,
            ),
        )
        self.assertEqual([x["status"] for x in result],["SUCCEEDED","SUCCEEDED"])
        self.assertLess(events.index("poll:a",events.index("start:b")))
        self.assertEqual(events.count("poll:a"),2)

    def test_failed_reload_never_starts_downstream(self):
        posts=[]
        def rest(method,path,body=None):
            if method=="POST":
                posts.append(body["appId"])
                return {"id":"reload0"}
            return {"status":"FAILED","errorMessage":"Qlik data source unavailable"}
        with self.assertRaisesRegex(RuntimeError,"data source unavailable"):
            reload_chain.run_chain(
                {"etl2":{"appId":"a"},"presentation":{"appId":"b"}},
                ["etl2","presentation"],rest,
            )
        self.assertEqual(posts,["a"])

    def test_timeout_blocks_downstream_reload(self):
        with self.assertRaises(TimeoutError):
            reload_chain.reload_one(
                "etl2","x",
                lambda method,*args: {"id":"job-x"} if method=="POST" else {"status":"RELOADING"},
                sleep=lambda n:None,clock=iter([0,999]).__next__,
                max_wait=10,
            )


if __name__=="__main__":
    unittest.main()

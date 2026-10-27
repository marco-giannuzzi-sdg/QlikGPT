"""Regression tests for GitHub-driven application/QVD lineage. No Qlik credentials."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ci"))
import app_lineage as lineage


class AppLineageTests(unittest.TestCase):
    def test_real_script_derived_lineage(self):
        report = lineage.build(lineage.registry())
        self.assertEqual(set(report["apps"]), {"etl1", "etl2", "presentation", "presentation2"})
        self.assertEqual(len(report["resources"]), 2)
        self.assertEqual(
            {(edge["upstream"], edge["downstream"]) for edge in report["connections"]},
            {("etl1", "etl2"), ("etl2", "presentation"), ("etl2", "presentation2")},
        )
        self.assertEqual(report["impact"]["etl1"]["direct"], ["etl2"])
        self.assertEqual(
            report["impact"]["etl1"]["indirect"], ["presentation", "presentation2"]
        )
        self.assertEqual(
            report["impact"]["etl2"]["transitive"], ["presentation", "presentation2"]
        )
        self.assertEqual(report["impact"]["presentation"]["transitive"], [])
        self.assertEqual(report["warnings"], [])

    def test_asset_uri_matches_qvs_lineage(self):
        result = lineage.build(lineage.registry())
        asset = next(r for r in result["resources"] if r["uri"].endswith("/RawOrders.qvd"))
        self.assertEqual(asset["producer"], "etl1")
        self.assertEqual(asset["consumers"], ["etl2"])
        self.assertEqual(asset["format"], "qvd")
        transformed = next(r for r in result["resources"] if r["uri"].endswith("/Sales_Clean.qvd"))
        self.assertEqual(transformed["producer"], "etl2")
        self.assertEqual(transformed["consumers"], ["presentation", "presentation2"])
        self.assertEqual(len(transformed["writes"]), 1)
        self.assertEqual(len(transformed["reads"]), 2)

    def test_input_parser_ignores_comments_without_corrupting_lib_uris(self):
        s = (
            "// FROM [lib://DataFiles/commented.qvd] (qvd)\n"
            "/* STORE Fact INTO [lib://DataFiles/hidden.qvd] (qvd); */\n"
            "LOAD * FROM [lib://DataFiles/valid.qvd] (qvd);\n"
            "STORE Fact INTO [lib://DataFiles/output.qvd] (qvd);\n"
            "AUTOGENERATE 5000;\n"
            "LOAD * RESIDENT Fact;\n"
        )
        parsed = lineage.parse_qvs(s)
        self.assertEqual(
            [x["uri"] for x in parsed["reads"]],
            ["lib://DataFiles/valid.qvd"],
        )
        self.assertEqual(
            [x["uri"] for x in parsed["writes"]],
            ["lib://DataFiles/output.qvd"],
        )
        self.assertEqual(parsed["autogenerate"], [5000])
        self.assertEqual(parsed["residents"], ["Fact"])
        self.assertEqual(parsed["reads"][0]["line"], 3)

    def test_cycle_is_rejected_and_never_reported_as_lineage(self):
        with self.assertRaisesRegex(ValueError, "Cycle"):
            lineage.edges_and_impacts(["a", "b"], [
                {"upstream": "a", "downstream": "b"},
                {"upstream": "b", "downstream": "a"},
            ])

    def test_ambiguous_producers_fail_loudly(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "scripts").mkdir()
            (root / "deployment").mkdir()
            (root / "deployment/app-ids.json").write_text('{"tenant":"https://example.com"}')
            (root / "scripts/one.qvs").write_text(
                "STORE One INTO [lib://DataFiles/one.qvd] (qvd);"
            )
            (root / "scripts/two.qvs").write_text(
                "STORE Two INTO [lib://DataFiles/one.qvd] (qvd);"
            )
            applications = {
                key: {"key":key, "type":"etl", "name":key,
                      "script":f"scripts/{path}.qvs", "appId":None}
                for key,path in (("one", "one"), ("two", "two"))
            }
            with patch.object(lineage, "ROOT", root):
                with self.assertRaisesRegex(ValueError, "Ambiguous"):
                    lineage.build(applications)

    def test_external_or_unresolved_qvd_is_not_assigned_an_invented_producer(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "scripts").mkdir()
            (root / "deployment").mkdir()
            (root / "deployment/app-ids.json").write_text('{"tenant":"https://example.com"}')
            (root / "scripts/a.qvs").write_text(
                "LOAD * FROM [lib://DataFiles/outside.qvd] (qvd);"
            )
            with patch.object(lineage, "ROOT", root):
                report=lineage.build({
                    "presentation": {
                        "key":"presentation", "type":"presentation", "name":"Report",
                        "script":"scripts/a.qvs", "appId":None,
                    },
                })
            self.assertEqual(report["resources"][0]["producer"], None)
            self.assertEqual(report["connections"], [])
            self.assertTrue(any("no QVS producer" in w for w in report["warnings"]))

    def test_new_presentation_subscribing_same_qvd_extends_lineage(self):
        apps=lineage.registry()
        clone=deepcopy(apps["presentation2"])
        clone.update({"key":"presentation3", "name":"New Presentation", "appId":None})
        apps["presentation3"]=clone
        result=lineage.build(apps)
        self.assertIn("presentation3", result["impact"]["etl2"]["direct"])
        self.assertIn("presentation3", result["impact"]["etl1"]["transitive"])

    def test_mermaid_and_markdown_links_are_present(self):
        result=lineage.build(lineage.registry())
        md=lineage.render(result)
        self.assertIn("flowchart LR",md)
        self.assertIn("RawOrders.qvd",md)
        self.assertIn("Sales_Clean.qvd",md)
        self.assertIn("## Impact Analysis",md)
        self.assertIn("scripts/etl1.qvs#L",md)
        self.assertIn("## Data flow",md)

    def test_non_qvs_path_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "lib://"):
            lineage.parse_qvs("STORE Data INTO [/var/somefile.qvd] (qvd);")


if __name__=="__main__":
    unittest.main()

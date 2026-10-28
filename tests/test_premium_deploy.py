"""Premium deploy preserves semantic identities despite Engine-added defaults."""
import ast
import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ci"))
import deploy_premium as premium


class PremiumDeployTests(unittest.TestCase):
    def test_engine_defaults_do_not_invalidate_master_bindings(self):
        expected = [{"qLibraryId": mid} for mid in premium.MEASURES]
        actual = [{"qLibraryId": mid, "qDef": {"qDef": "", "qLabel": ""},
                   "qAttributeExpressions": []} for mid in premium.MEASURES]
        premium.verify_master_bindings(actual, expected)
        actual[0]["qLibraryId"] = "unexpected"
        with self.assertRaises(RuntimeError):
            premium.verify_master_bindings(actual, expected)
        actual[0] = {"qLibraryId": premium.MEASURES[0], "qDef": {"qDef": "Sum(Revenue)"}}
        with self.assertRaises(RuntimeError):
            premium.verify_master_bindings(actual, expected)

    def test_ids_exist_in_presentation_subscription(self):
        manifest = json.loads((premium.ROOT / "semantic-models/sales/apps/presentation1.json").read_text())
        self.assertTrue(set(premium.MEASURES) <= set(manifest["catalogMeasures"]))
        self.assertTrue(set(premium.DIMENSIONS) <= set(manifest["catalogDimensions"]))

    def test_deployer_has_no_script_semantic_or_reload_write_methods(self):
        tree = ast.parse(Path(premium.__file__).read_text())
        methods = {node.args[1].value for node in ast.walk(tree)
                   if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                   and node.func.attr == "call" and len(node.args) > 1
                   and isinstance(node.args[1], ast.Constant)}
        forbidden = {"SetScript", "DoReload", "DoReloadEx", "CreateMeasure", "DestroyMeasure",
                     "CreateDimension", "DestroyDimension", "DestroyObject"}
        self.assertFalse(methods & forbidden)

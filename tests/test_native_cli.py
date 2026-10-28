"""Real native hierarchy and semantic bindings for the CLI-only presentation."""
from pathlib import Path
import importlib.util
import json
import unittest
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("native_generator", ROOT / "ui/native-overview/generate.py")
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)

def walk(tree):
    yield tree["qProperty"]
    for child in tree.get("qChildren", []):
        yield from walk(child)

class NativeCliTests(unittest.TestCase):
    def setUp(self):
        self.tree = g.make()[0]
        self.objects = list(walk(self.tree))

    def test_native_types_and_real_child_entries(self):
        types = [p["qInfo"]["qType"] for p in self.objects]
        self.assertEqual(types.count("kpi"), 4)
        self.assertEqual(types.count("linechart"), 1)
        self.assertEqual(types.count("barchart"), 1)
        self.assertEqual(types.count("filterpane"), 3)
        self.assertEqual(types.count("listbox"), 3)
        self.assertEqual(set(types), {"sheet", "kpi", "linechart", "barchart", "filterpane", "listbox", "text-image"})
        self.assertTrue(all("qChildren" not in p for p in self.objects))
        ids = [p["qInfo"]["qId"] for p in self.objects]
        self.assertEqual(len(ids), len(set(ids)))

    def test_existing_catalog_only(self):
        m = json.loads((ROOT / "semantic-models/sales/apps/presentation1.json").read_text())
        for p in self.objects:
            cube = p.get("qHyperCubeDef", {})
            for measure in cube.get("qMeasures", []):
                self.assertIn(measure["qLibraryId"], m["catalogMeasures"])
                self.assertFalse(measure.get("qDef", {}).get("qDef", "").strip())
            for dim in cube.get("qDimensions", []):
                self.assertIn(dim["qLibraryId"], m["catalogDimensions"])
            if p.get("qListObjectDef"):
                self.assertIn(p["qListObjectDef"]["qLibraryId"], m["catalogDimensions"])

    def test_grid_cells_cover_exactly_native_sheet_children(self):
        sheet = self.tree["qProperty"]
        direct = {t["qProperty"]["qInfo"]["qId"] for t in self.tree["qChildren"]}
        self.assertEqual({c["name"] for c in sheet["cells"]}, direct)
        occupied = set()
        for cell in sheet["cells"]:
            self.assertLessEqual(cell["col"] + cell["colspan"], sheet["columns"])
            self.assertLessEqual(cell["row"] + cell["rowspan"], sheet["rows"])
            for x in range(cell["col"], cell["col"] + cell["colspan"]):
                for y in range(cell["row"], cell["row"] + cell["rowspan"]):
                    self.assertNotIn((x, y), occupied)
                    occupied.add((x, y))

    def test_supported_style_keys_and_fixed_kpi_behavior(self):
        for p in self.objects:
            if p["qInfo"]["qType"] == "listbox":
                continue
            general = next(c for c in p["components"] if c["key"] == "general")
            self.assertIn("bgColor", general)
            self.assertIn("borderRadius", general)
            self.assertNotIn("style", p)
            if p["qInfo"]["qType"] == "kpi":
                self.assertEqual(p["layoutBehavior"], "fixed")
                self.assertEqual(general["borderRadius"], "16px")

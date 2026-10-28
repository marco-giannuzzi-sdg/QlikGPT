"""Offline regression tests for Qlik theme packaging and tenant/app deployment."""
from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ci"))
import deploy_theme as th
import deploy_visuals


class ThemeDeployTests(unittest.TestCase):
    def test_contract_and_exact_zip_members(self):
        slug, version = th.contract()
        self.assertEqual(slug, "qlikgpt-executive-v1")
        self.assertEqual(version, "1.1.0")
        with tempfile.TemporaryDirectory() as root:
            archive = Path(root) / "theme.zip"
            th.build_archive(archive)
            from zipfile import ZipFile
            with ZipFile(archive) as z:
                self.assertEqual(set(z.namelist()),
                                 {"theme.json", "qlikgpt-executive-v1.qext"})
                self.assertIsNone(z.testzip())

    def test_parse_theme_list_shapes(self):
        self.assertEqual(th.list_themes("[]"), [])
        self.assertEqual(th.list_themes('{"data":[{"id":"a"}]}'), [{"id":"a"}])
        with self.assertRaises(ValueError):
            th.list_themes('{"unexpected":"format"}')

    def test_match_only_qext_identity_and_reject_ambiguous(self):
        mine = {"id": "one", "name": "Different Display Name",
                "qextFilename": "qlikgpt-executive-v1.qext"}
        other = {"id": "two", "name": "qlikgpt-executive-v1",
                 "qextFilename": "unrelated-theme.qext"}
        self.assertEqual(th.find_theme([other, mine], "qlikgpt-executive-v1"), mine)
        self.assertIsNone(th.find_theme([other], "qlikgpt-executive-v1"))
        with self.assertRaises(RuntimeError):
            th.find_theme([mine, mine], "qlikgpt-executive-v1")

    def test_create_and_readback_without_replacing_other_themes(self):
        calls = []
        replies = iter([
            '{"data":[]}',
            '{"id":"created"}',
            '{"data":[{"id":"created","qextFilename":"qlikgpt-executive-v1",'
            '"qextVersion":"1.1.0"}]}',
        ])

        def fake(*args):
            calls.append(args)
            return next(replies)

        with patch.object(th, "qlik", fake):
            out = th.publish_theme("qlikgpt-executive-v1", "1.1.0", Path("/tmp/theme.zip"))
        self.assertEqual(out, "qlikgpt-executive-v1")
        self.assertTrue(any(args[:2] == ("theme", "create") for args in calls))

    def test_existing_matching_version_skips_patch(self):
        listing = '{"data":[{"id":"original","qextFilename":"qlikgpt-executive-v1.qext","qextVersion":"1.1.0"}]}'
        calls = []
        def fake(*args):
            calls.append(args)
            return listing
        with patch.object(th, "qlik", fake):
            th.publish_theme("qlikgpt-executive-v1", "1.1.0", Path("/tmp/theme.zip"))
        self.assertEqual(len(calls), 2)
        self.assertTrue(all(args[:2] == ("theme", "ls") for args in calls))

    def test_qix_theme_setpreserves_existing_app_properties(self):
        class FakeQix:
            instance = None

            def __init__(self, app_id):
                self.doc_id = app_id
                self.saved = False
                self.closed = False
                self.props = {"qInfo": {"qType": "appprops", "qId": "clientprops"},
                              "theme": "horizon", "sheetTitleBgColor": "#000000"}
                FakeQix.instance = self

            def call(self, handle, method, params):
                if method == "OpenDoc":
                    return {"qReturn": {"qHandle": 10}}
                if method == "CreateSessionObject":
                    self.list_def = params["qProp"]
                    return {"qReturn": {"qHandle": 11}}
                if method == "GetLayout":
                    return {"qLayout": {"qAppObjectList": {
                        "qItems": [{"qInfo": {"qId": "clientprops"}}]
                    }}}
                if method == "GetObject":
                    return {"qReturn": {"qHandle": 12}}
                if method == "GetProperties":
                    return {"qProp": dict(self.props)}
                if method == "SetProperties":
                    self.props = dict(params[0])
                    return {}
                if method == "DoSave":
                    self.saved = True
                    return {}
                raise AssertionError(method)

            def close(self):
                self.closed = True

        with patch.object(deploy_visuals, "Qix", FakeQix):
            th.apply_theme("demo-app", "qlikgpt-executive-v1")
        instance = FakeQix.instance
        self.assertEqual(instance.list_def["qAppObjectListDef"]["qType"], "appprops")
        self.assertEqual(instance.props["theme"], "qlikgpt-executive-v1")
        self.assertEqual(instance.props["sheetTitleBgColor"], "#000000")
        self.assertTrue(instance.saved)
        self.assertTrue(instance.closed)


if __name__ == "__main__":
    unittest.main()

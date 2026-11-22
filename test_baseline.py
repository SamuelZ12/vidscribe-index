import hashlib
import json
import unittest

from pilot import ROOT


class SplitTests(unittest.TestCase):
    def test_frozen_panel(self):
        raw = (ROOT / 'split.json').read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),
                         '4fe7e54ae61ec0b79bf64651c132a394d5e055cedfec35fcdcd052eced0b395d')
        split = json.loads(raw)
        self.assertEqual([len(set(split[k])) for k in ('dev', 'holdout')], [100, 44])
        self.assertTrue(set(split['dev']).isdisjoint(split['holdout']))


class SetTests(unittest.TestCase):
    def test_repeat_resume_and_identity(self):
        from dataclasses import replace
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from types import SimpleNamespace
        from unittest.mock import patch
        from baseline import RunSet, pending
        from pilot import write_json
        spec = RunSet('a','vidscribe','/src','123','abc',2,'codex')
        item = SimpleNamespace(item_id='sample')
        with TemporaryDirectory() as tmp, patch('baseline.RUNS', Path(tmp)):
            self.assertEqual(len(pending(spec,[item])), 2)
            write_json(spec.record(item,1), {'status':'timeout'})
            self.assertEqual(pending(spec,[item]), [(spec,item,2)])
            write_json(spec.record(item,2), {'status':'ok'})
            self.assertEqual(pending(spec,[item]), [])
            with self.assertRaises(ValueError):
                pending(replace(spec, attempts=3),[item])

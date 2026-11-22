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

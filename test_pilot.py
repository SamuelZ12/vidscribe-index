import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from pilot import write_json
from runner import finished
from scoring import paired, score


class PilotTests(unittest.TestCase):
    def test_mixed_chance(self):
        key = {'a': 'A', 'b': 'B'}
        a = SimpleNamespace(item_id='a', chance=.5)
        b = SimpleNamespace(item_id='b', chance=.25)
        hit, adjusted = score(a, dict(status='ok', answer='A'), key)
        miss, penalty = score(b, dict(status='timeout', answer='B'), key)
        self.assertEqual((hit+miss)/2, .5)
        self.assertAlmostEqual((adjusted+penalty)/2, 1/3)
        self.assertEqual(paired([1, 0], [1, 0]), (0, 0, 0))

    def test_resume(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)/'run.json'
            path.with_suffix('.tmp').write_text('{')
            self.assertFalse(finished(path))
            for status in ('ok', 'timeout', 'error', 'no_answer'):
                write_json(path, {'status': status})
                self.assertTrue(finished(path))

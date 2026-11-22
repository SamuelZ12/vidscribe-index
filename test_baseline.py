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


class StatisticsTests(unittest.TestCase):
    def test_request_prices(self):
        from results import price
        request = dict(input_tokens=10000, cached_input_tokens=3000, cache_write_input_tokens=2000,
                       output_tokens=1000, reasoning_output_tokens=500)
        long = request | dict(input_tokens=300000)
        parts = price('gpt-6.2-sol',[request,long])
        for field, expected in dict(input=1.19,cached=.0009,write=.015,output=.025).items():
            self.assertAlmostEqual(parts[field],expected)

    def test_attempt_average_and_pairing(self):
        from types import SimpleNamespace
        from results import aggregate_item, compare
        item=SimpleNamespace(item_id='sample',chance=.25)
        record=dict(status='ok',answer='B',seconds=2,processing_seconds=3,model='gpt-6.2-sol')
        item_mean=aggregate_item(item,[record,record,record|{'status':'timeout'}],{'sample':'B'})
        self.assertEqual(item_mean['accuracy'],2/3)
        self.assertEqual(item_mean['seconds'],5)
        self.assertTrue(item_mean['disagree'])
        self.assertIsNone(item_mean['dollars'])
        point=dict(accuracy=.5,dollars=.2,seconds=5)
        left={'x':point,'y':point|dict(accuracy=1)}
        right={'y':point|dict(accuracy=.75,dollars=.1),'x':point|dict(accuracy=.25,dollars=.1)}
        result=compare(left,right)
        self.assertEqual(result['accuracy'],dict(interval=(.25,.25,.25),verdict='better'))
        self.assertEqual(result['dollars']['verdict'],'worse')
        self.assertEqual(result['seconds']['verdict'],'no measurable difference')

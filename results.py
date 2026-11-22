"""Aggregate attempts within each item before estimating uncertainty."""
from collections import Counter
from dataclasses import asdict
from itertools import combinations
import json
from math import sqrt
from statistics import mean, variance

from baseline import RunSet
from chart import charts
from media import cache, panel
from pilot import ROOT, RUNS, rows, write_json
from scoring import paired, score

PRICING = {'gpt-6.2-sol': dict(input=2., cached=.10, write=2.50, output=10.)}
SOURCE = 'https://developers.openai.com/api/docs/pricing'
PRICE_DATE = '2026-11-22'
AXES = ('accuracy','dollars','seconds')


def price(model, requests):
    dollars = Counter()
    for request in requests:
        inputs = request['input_tokens']
        cached = request['cached_input_tokens']
        write = request.get('cache_write_input_tokens', 0)
        tokens = dict(input=inputs-cached-write, cached=cached, write=write, output=request['output_tokens'])
        if min(tokens.values()) < 0:
            raise ValueError('Invalid request token counts')
        for kind, count in tokens.items():
            factor = (1.5 if kind == 'output' else 2) if inputs > 272000 else 1
            dollars[kind] += count * PRICING[model][kind] * factor / 1e6
    return dollars


def aggregate_item(item, records, key):
    scores = [score(item,r,key) for r in records]
    costs = [price(r['model'],r['requests']) for r in records if r.get('requests')]
    values = dict(accuracy=mean(s[0] for s in scores), normalized=mean(s[1] for s in scores),
                  attempts=[s[0] for s in scores], disagree=len({(r['status'],r['answer']) for r in records})>1,
                  agent=mean(r['seconds'] for r in records), processing=mean(r['processing_seconds'] for r in records))
    values['seconds'] = values['agent'] + values['processing']
    values['dollars'] = None
    if len(costs) == len(records):
        values['cost_parts'] = {k:mean(c[k] for c in costs) for k in costs[0]}
        values['dollars'] = sum(values['cost_parts'].values())
        values['tokens'] = mean(r['token_usage']['total_tokens'] for r in records)
    return values


def interval(values):
    if None in values:
        return None
    return paired(values,[0]*len(values))


def compare(left, right):
    if left.keys() != right.keys():
        raise ValueError('Sets have different items')
    result = {}
    for axis in AXES:
        values = [(left[k][axis],right[k][axis]) for k in left]
        ci = interval([None if None in pair else pair[0]-pair[1] for pair in values])
        verdict = 'unavailable'
        if ci:
            sign = 1 if ci[1]>0 else -1 if ci[2]<0 else 0
            verdict = 'no measurable difference' if not sign else (
                'better' if (sign==1)==(axis=='accuracy') else 'worse')
        result[axis] = dict(interval=ci, verdict=verdict)
    return result


def summarize(spec, sample, key):
    points = {}
    records = []
    for item in sample:
        attempts = [json.loads(spec.record(item,a).read_text()) for a in range(1,spec.attempts+1)]
        points[item.item_id] = aggregate_item(item,attempts,key)
        records.extend(attempts)
    data = list(points.values())
    summary = {axis:interval([p[axis] for p in data]) for axis in AXES}
    summary.update({k:mean(p[k] for p in data) for k in ('agent','processing','normalized','disagree')})
    statuses = Counter(r['status'] for r in records)
    summary.update(settings=asdict(spec), sessions=len(records), statuses={s:statuses[s] for s in
                   ('ok','timeout','error','no_answer')}, attempts=[mean(a) for a in zip(*(p['attempts'] for p in data))],
                   missing_usage=sum(not r.get('requests') for r in records),
                   long_context_sessions=sum(any(t['input_tokens']>272000 for t in r.get('requests',[])) for r in records),
                   image_sessions=sum(r['image_returns']>0 for r in records),
                   detail_sessions=sum(bool(r.get('detail_returned')) for r in records),
                   rollouts=sum(bool(r['rollout']) for r in records))
    if spec.arm != 'stock':
        prep = [json.loads((cache(i,spec.vidscribe_commit)/'preparation.json').read_text()) for i in sample]
        summary['preparation_load_1m_range'] = [min(p['load'][0] for p in prep),max(p['load'][0] for p in prep)]
    if summary['dollars']:
        summary['cost_parts']={k:mean(p['cost_parts'][k] for p in data) for k in data[0]['cost_parts']}
        summary['tokens']=mean(p['tokens'] for p in data)
    if spec.attempts>1:
        sd = sqrt(2*sum(variance(p['attempts']) for p in data)/spec.attempts)/len(data)
        summary.update(noise_sd=sd, noise_95=1.96*sd)
    return points, summary


def fmt(ci, scale=1, precision=3):
    if ci is None:
        return 'unavailable'
    center,lo,hi=(x*scale for x in ci)
    return f'{center:.{precision}f} [{lo:.{precision}f}, {hi:.{precision}f}]'


def comparison_lines(name, comparison):
    return [f'{name}, {axis} {fmt(row["interval"], 100 if axis=="accuracy" else 1)} '
            f'({row["verdict"]})' for axis,row in comparison.items()]


def output(command, names):
    sample = panel()
    ids = {i.item_id for i in sample}
    key = {r['item_id']:r['answer'] for r in rows() if r['item_id'] in ids}
    points, sets = {}, {}
    for name in names:
        spec = RunSet(**json.loads((RUNS/name/'set.json').read_text()))
        if spec.name != name:
            raise ValueError('Set name differs from recorded settings')
        points[name], sets[name] = summarize(spec,sample,key)
    if len({s['settings']['harness_commit'] for s in sets.values()}) != 1:
        raise ValueError('Different measuring revisions')
    comparisons = {f'{a} minus {b}':compare(points[a],points[b]) for a,b in combinations(names,2)}
    lines = [line for name,c in comparisons.items() for line in comparison_lines(name,c)]
    if command == 'compare':
        print('\n'.join(lines))
        return
    meter = {p.name:json.loads(p.read_text()) for p in RUNS.glob('*.meter.json')
             if p.name=='baseline.meter.json' or p.name in {'set-'+n+'.meter.json' for n in names}}
    chance = mean(i.chance for i in sample)
    docs = ROOT/'docs'
    summary = dict(sets=sets, comparisons=comparisons, chance=chance, meter=meter, prices=PRICING,
                   price_date=PRICE_DATE, price_source=SOURCE)
    write_json(docs/'baseline-summary.json',summary)
    (docs/'pareto.html').write_text(charts(sets,chance))
    report = ['# Video-Index development baseline','',
              'Each point averages attempts within each of the 100 questions. Brackets give 95% percentile intervals '
              'from 10,000 fixed-seed item resamples. Comparisons resample the same items together. '
              f'Uniform guessing averages {chance:.2%}.','',
              '| Set | Accuracy % | API $/question | Seconds/question | Agent s | Processing s | Tokens/question |',
              '|---|---:|---:|---:|---:|---:|---:|']
    for n,s in sets.items():
        tokens = f'{s["tokens"]:,.0f}' if 'tokens' in s else 'unavailable'
        report.append(f'| {n} | {fmt(s["accuracy"],100,2)} | {fmt(s["dollars"],1,4)} | {fmt(s["seconds"],1,1)} '
                      f'| {s["agent"]:.1f} | {s["processing"]:.1f} | {tokens} |')
    for n,s in sets.items():
        report.extend(['',f'## {n}','',
            f'{s["sessions"]} attempts. Accuracy by attempt: '+', '.join(f'{a:.2%}' for a in s['attempts'])+
            f'. Chance-normalized accuracy {s["normalized"]:.2%}. Answers or statuses differed on {s["disagree"]:.0%} of items.',
            '',', '.join(f'{v} {k}' for k,v in s['statuses'].items())+
            f'. {s["rollouts"]} rollouts, {s["image_sessions"]} sessions with images, {s["detail_sessions"]} with detail frames.',
            '', f'{s["long_context_sessions"]} sessions exceeded 272K request input. {s["missing_usage"]} missing usage. '+
            ', '.join(f'{k} ${v:.5f}' for k,v in s.get('cost_parts',{}).items())+'.'])
        if 'preparation_load_1m_range' in s:
            low, high = s['preparation_load_1m_range']
            report.extend(['', f'One-minute host load at preparation starts ranged from {low:.2f} to {high:.2f}.'])
        if 'noise_sd' in s:
            report.extend(['',f'Same-code SD for two independent {len(s["attempts"])}-attempt means on this fixed panel '
                            f'is {100*s["noise_sd"]:.2f} percentage points from within-item sample variances. '
                            f'A difference must exceed about {100*s["noise_95"]:.2f} points to clear estimated rerun '
                            'noise at 95%. This normal approximation assumes independent attempts and items. '
                            'It gives a significance threshold, not 95% detection power.'])
    report+=['','## Paired differences','','Accuracy differences are percentage points. Dollar and second differences are per question.','',
             *['- '+l for l in lines],'','## Sensitivity and limits','']
    for n,s in sets.items():
        if s['settings']['arm']!='transcript' and 'transcript' in points:
            result = compare(points[n],points['transcript'])['accuracy']
            report.append(f'{n} versus transcript: {result["verdict"]} in accuracy. ')
    report+=['','Transcript is charged full vidscribe processing, which overstates transcript-only latency. '
             'Time includes agent execution and host processing per use. It excludes downloads, sandbox staging and queueing. '
             'The cache reuses one timing per item and revision. Timing intervals omit variability between preparations. '
             'The Pareto lines use point estimates. Paired intervals that include zero leave both benefit and harm possible. '
             'Comparisons describe this dev panel. The holdout was not run.','',
             f'API-equivalent dollars use per-request token counts and the {PRICE_DATE} price table. '
             f'Reasoning is included in output. [OpenAI pricing]({SOURCE}).','']
    for name,m in meter.items():
        report.append(f'One-minute host load at session start: {m["checks"][0]["load"][0]:.2f}. ')
        report.append(f'{name}: account-wide weekly meter {m["before"]["usedPercent"]}% before, '
                      f'{m["checks"][-1]["meter"]["usedPercent"]}% after. Other account activity cannot be attributed.')
    (docs/'baseline-report.md').write_text('\n'.join(report)+'\n')

"""Rebuild the aggregate publication tables using local records and the pinned public key."""
import json
import re
from collections import Counter
from pathlib import Path
from statistics import mean

from arm_report import trace_counts
from full_run import (GUIDED, HISTORY, METER, PLAIN, REVISION, RUNS, VERSION, arms,
                      cache, historical, panel, read)
from pilot import ROOT, rows, write_json
from results import AXES, aggregate_item, compare, fmt, interval

PAIRS = [('vidscribe', 'stock'), (PLAIN, 'vidscribe'), (GUIDED, PLAIN), (PLAIN, 'stock')]
DOCS = ROOT / 'docs'
REBUILD = 'cd /Users/samuelzhang/dev/vidscribe-index\nuv run --python 3.13 full_report.py'


def rollout_inputs(record):
    prompt = profile = None
    with open(record['rollout']) as stream:
        for line in stream:
            event = json.loads(line)
            p = event['payload']
            if event['type'] == 'turn_context':
                raw = json.dumps(p['permission_profile'], sort_keys=True)
                profile = re.sub(r'codex-arg0\w+', 'codex-arg0', raw.replace(record['workspace'], '$WORK'))
            if p.get('type') == 'message' and p.get('role') == 'user':
                for block in p['content']:
                    if block.get('text', '').endswith('Reply with the letter.'):
                        prompt = block['text']
            if prompt and profile:
                return prompt, profile
    raise ValueError('Missing rollout evidence')


def original_files(arm, item):
    media = cache(item, REVISION)
    files = {'question.md'}
    for name in arms[arm].files:
        path = media / name
        if path.is_dir():
            files.update(str(p.relative_to(media)) for p in path.rglob('*') if p.is_file() or p.is_symlink())
        else:
            files.add(name)
    if arm == GUIDED:
        files.add('.agents/skills/watch-video/SKILL.md')
    if arm == 'vidscribe':
        files.add('bin/vidscribe')
    return sorted(files)


def table(lines, headers, records):
    lines.extend(['', '| ' + ' | '.join(headers) + ' |', '|' + '---|' * len(headers)])
    lines.extend('| ' + ' | '.join(map(str, row)) + ' |' for row in records)


def cells(metrics):
    return [fmt(metrics[k], 100 if k == 'accuracy' else 1, 4 if k == 'dollars' else 1) for k in AXES]


def main():
    if historical() != read(RUNS / 'full.legacy.json'):
        raise ValueError('Legacy records changed')
    key = {row['item_id']: row['answer'] for row in rows()}
    items = {part: panel(part) for part in ('dev', 'holdout')}
    all_items = items['dev'] + items['holdout']
    summary, points, dates, behavior = {}, {}, {}, {}
    layout_matches = {}
    versions, statuses, new_statuses = Counter(), Counter(), Counter()
    contexts = 0
    for arm, (name, old) in HISTORY.items():
        points[arm] = {}
        counts = Counter()
        mixed = []
        example = None
        old_layouts = {tuple(original_files(arm, i)) for i in items['dev']}
        layout_matches[arm] = 0
        for part, sample in items.items():
            for item in sample:
                records = []
                for attempt in (1, 2, 3):
                    legacy = part == 'dev' and attempt <= old
                    directory = name if legacy else f'full-{part}-{arm}'
                    r = read(RUNS / directory / f'{item.item_id}.{attempt}.json')
                    assert (r['arm'], r['item_id'], r['attempt']) == (arm, item.item_id, attempt)
                    assert r['vidscribe_commit'] == REVISION and r['codex_version'] == VERSION
                    records.append(r)
                    versions[r['codex_version']] += 1
                    statuses[r['status']] += 1
                    contexts += (r.get('turn_contexts') == [['gpt-6.2-sol', 'medium', 'workspace-write', False]]
                                 and r.get('rollout_cli_version') == VERSION.split()[1])
                    counts.update(trace_counts(r))
                    if legacy and example is None:
                        example = rollout_inputs(r)
                    if not legacy:
                        new_statuses[r['status']] += 1
                        if r.get('rollout'):
                            assert r['workspace_files'] == original_files(arm, item)
                            layout_matches[arm] += tuple(r['workspace_files']) in old_layouts
                            assert rollout_inputs(r) == (r['prompt'], example[1]) == example
                p = aggregate_item(item, records, key)
                points[arm][item.item_id] = p
                if part == 'dev' and old == 1:
                    first, second, third = p['attempts']
                    mixed.append((second + third) / 2 - first)
        if not layout_matches[arm]:
            raise ValueError('No historical layout matches a new session for ' + arm)
        summary[arm] = {k: interval([p[k] for p in points[arm].values()]) for k in (*AXES, 'disagree')}
        if mixed:
            dates[arm] = interval(mixed)
        behavior[arm] = counts
    pairs = {f'{a} minus {b}': {k: v['interval'] for k, v in compare(points[a], points[b]).items()}
             for a, b in PAIRS}
    lines = ['# Video-Index v1.1', '',
             'We compared five ways of answering a video question with one agent, Codex CLI 0.169.0, '
             'using gpt-6.2-sol at medium reasoning effort. Each setup answered all 144 questions three times. '
             'The four comparisons and the speech slice were fixed before collecting holdout answers.',
             '', '## All questions']
    table(lines, ['Setup', 'Accuracy %', 'API $/question', 'Seconds/question', 'Disagree %'],
          ([arm, *cells(m), fmt(m['disagree'], 100, 1)] for arm, m in summary.items()))
    lines += ['', 'Intervals are 95% percentile intervals from 10,000 fixed-seed question resamples, '
              'after averaging attempts within question. Disagreement counts different letters or statuses. '
              'Time includes agent execution and full host preparation for every setup except stock. '
              'This overcharges transcript delivery and excludes download, staging and queue time. '
              'API-equivalent dollars use the frozen November 22 per-request price table in results.py.',
              '', '## Paired differences']
    table(lines, ['Difference', 'Accuracy (pp)', 'API $/question', 'Seconds/question'],
          ([pair, *cells(m)] for pair, m in pairs.items()))
    lines += ['', '## Speech slice', '', 'Questions with audio and duration over 600 seconds. '
              'Dev suggested this slice. Only holdout independently checks it.']
    speech = []
    for group, sample in [('Holdout', items['holdout']), ('Dev', items['dev']), ('All', all_items)]:
        ids = [i.item_id for i in sample if i.has_audio and i.duration_s > 600]
        effects = [interval([points[a][i]['accuracy'] - points['stock'][i]['accuracy'] for i in ids])
                   for a in (PLAIN, 'vidscribe')]
        speech.append([group, len(ids), *(fmt(e, 100, 1) for e in effects)])
        if group == 'Holdout':
            verdict = ('holds' if all(e[1] > 0 for e in effects) else
                       'fails' if any(e[2] <= 0 for e in effects) else 'too small to tell')
    table(lines, ['Split', 'Questions', 'ffmpeg-transcript minus stock (pp)', 'vidscribe minus stock (pp)'], speech)
    lines += ['', f'Holdout verdict: **{verdict}**.', '', '## Audio, silent, dev and holdout']
    groups = [[i for i in all_items if i.has_audio], [i for i in all_items if not i.has_audio],
              items['dev'], items['holdout']]
    table(lines, ['Setup', *(f'{name} ({len(g)}), accuracy %' for name, g in zip(
        ['Audio', 'Silent', 'Dev', 'Holdout'], groups))],
        ([arm, *(f"{100 * mean(p[i.item_id]['accuracy'] for i in g):.1f}" for g in groups)] for arm, p in points.items()))
    lines += ['', '## Mixed dates', '', 'Mean of new dev runs 2 and 3 minus old run 1, paired by question.']
    table(lines, ['Setup', 'Accuracy difference (pp)'], ([a, fmt(x, 100, 1)] for a, x in dates.items()))
    lines += ['', 'vidscribe and ffmpeg-guided have only historical dev runs, so date drift cannot be checked '
              'for either. Split differences also reflect different questions.', '', '## What agents did']
    table(lines, ['Setup', 'Sessions', 'Sessions viewing images', 'Image returns', 'Dense requests', 'Crop requests'],
          ([a, *(c[k] for k in ['sessions', 'seen', 'images', 'dense_requested', 'crop_requested'])]
           for a, c in behavior.items()))
    meter = read(METER)
    checks = meter['checks']
    lines += ['', 'One sheet is one image return. Dense sampling and crops count sessions requesting them, '
              'including requests that failed.', '', '## Run integrity and limits', '',
              f'Historical sessions: 900, hash-checked before and after. New sessions: {sum(new_statuses.values())}. '
              f'All statuses: {dict(statuses)}. New statuses: {dict(new_statuses)}. No answer session was retried. '
              f'Recorded versions: {dict(versions)}. Rollout-confirmed settings: {contexts}/2160.',
              '', f'Account-wide weekly usage moved from {meter["before"]["usedPercent"]}% to '
              f'{checks[-1]["meter"]["usedPercent"]}%. The checkpoint window lasted '
              f'{(checks[-1]["time"] - checks[0]["time"])/3600:.2f} hours. Other account use cannot be separated.',
              '', 'For each setup we compared the new rollout prompts and effective permission profiles to a historical '
              'rollout, normalizing the temporary workspace and CLI paths. Historical sessions did not store input '
              'manifests. We reconstructed their staging rules against each new question’s cached media and checked '
              'the file list captured immediately before the new session. Every setup also had at least one '
              'new file list matching a reconstructed historical dev workspace entry for entry. '
              'The outside-read canary preceded collection.',
              '', 'These results cover one agent, model and effort, 144 questions, and three attempts. They do not '
              'establish equivalence or generalize to other agents. Intervals are per comparison and do not account '
              'for variability in host preparation times.', '', '## Rebuild', '',
              'Requires the saved local records, cached inputs, rollouts and access to the pinned dataset key.',
              '', '```sh', REBUILD, '```', '']
    write_json(DOCS / 'full-summary.json', dict(sets=summary, paired=pairs,
               interval_order=['estimate', 'lower95', 'upper95'], accuracy_unit='fraction', disagree_unit='fraction'))
    (DOCS / 'full-report.md').write_text('\n'.join(lines))


if __name__ == '__main__':
    main()

from collections import Counter
import json
import random
from pathlib import Path
from statistics import mean, median

from pilot import ARMS, DATA, RUNS, SEED, items, rows
from runner import run_file


def score(item, run, key):
    hit = int(run['status'] == 'ok' and run['answer'] == key[item.item_id])
    return hit, (hit - item.chance) / (1 - item.chance)


def paired(left, right):
    differences = [a-b for a, b in zip(left, right, strict=True)]
    rng = random.Random(SEED)
    draws = sorted(sum(rng.choices(differences, k=len(left))) / len(left) for _ in range(10000))
    return mean(differences), draws[249], draws[9749]


def report():
    sample = items()
    runs = {a.name: [json.loads(run_file(i, a).read_text()) for i in sample] for a in ARMS}
    key = {r['item_id']: r['answer'] for r in rows()}
    lines = ['# Video-Index v1.1 pilot', '',
             'Twenty paired questions, one fresh Codex session per arm and item. '
             'The score is the fraction answered correctly. Chance normalization subtracts '
             'each item’s chance and divides by its available improvement before averaging.', '',
             '| Arm | Correct | Accuracy | Chance-normalized | Timeout | Error | No answer | Median s | Max s | Median tokens |',
             '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    hits = {}
    for arm, records in runs.items():
        hits[arm], normalized = zip(*(score(i, r, key) for i, r in zip(sample, records, strict=True)))
        counts = Counter(r['status'] for r in records)
        times = [r['seconds'] for r in records]
        tokens = [r['token_usage']['total_tokens'] for r in records if r['token_usage']]
        token_median = f'{median(tokens):,.0f}' if tokens else 'unavailable'
        lines.append(f'| {arm} | {sum(hits[arm])}/{len(sample)} | {mean(hits[arm]):.1%} | {mean(normalized):.1%} | '
                     f'{counts["timeout"]} | {counts["error"]} | {counts["no_answer"]} | '
                     f'{median(times):.1f} | {max(times):.1f} | {token_median} |')
    lines.extend(['', '## Paired accuracy differences', ''])
    for arm in ('stock', 'transcript'):
        diff, lo, hi = paired(hits['vidscribe'], hits[arm])
        wins = sum(a>b for a,b in zip(hits['vidscribe'], hits[arm]))
        losses = sum(a<b for a,b in zip(hits['vidscribe'], hits[arm]))
        lines.append(f'- Against {arm}, vidscribe won {wins} and lost {losses}. Difference {100*diff:+.0f} percentage points '
                     f'(paired percentile bootstrap 95% interval {100*lo:+.0f} to {100*hi:+.0f}).')
    lines.extend(['', 'Each question moves accuracy by five points. The intervals resample the 20 paired items '
                  '10,000 times. One attempt leaves agent rerun variance unmeasured. A reliable gate for small '
                  'changes needs more items and repeated runs of the same revision.', '', '## Resources', ''])
    data = sum(runs.values(), [])
    wall = max(r['ended'] for r in data)-min(r['started'] for r in data)
    prep = sum(json.loads((DATA / (i.item_id + '.json')).read_text())['seconds'] for i in sample)
    batches = [json.loads(p.read_text()) for p in RUNS.glob('batch-*.json')]
    active = sum(b['end']-b['start'] for b in batches)
    lines.append(f'Up to four concurrent sessions took {active/60:.1f} minutes across active batches. '
                 f'First launch to last exit spanned {wall/60:.1f} minutes including waits for media. '
                 f'Host media preparation took {prep/60:.1f} minutes summed across items. Per-arm timing excludes preparation. '
                 f'Tokens include cached input and output ({sum(r["token_usage"].get("total_tokens",0) for r in data):,} total). '
                 f'Scaling active batch time and host preparation by 144/20 gives {active*7.2/3600:.1f} and '
                 f'{prep*7.2/3600:.1f} hours, respectively, before downloads. Clip lengths and scheduling affect both estimates.')
    before, after = [json.loads((RUNS/f'{t}.json').read_text()) for t in ('before','after')]
    assert before['resetsAt'] == after['resetsAt'], 'Weekly reset during measurement'
    change = after['usedPercent'] - before['usedPercent']
    lines.extend(['', f'The account-wide weekly meter went from {before["usedPercent"]}% to {after["usedPercent"]}% '
                  f'(a movement of {change:+d} pp). Scaling 60 sessions to 432 gives {change*7.2:.1f} points '
                  'under the same workload mix. The meter rounds to whole points and includes concurrent account activity. '
                  f'Rounding alone puts the linearly scaled account movement between '
                  f'{max(0,change-1)*7.2:.1f} and {(change+1)*7.2:.1f} points. '
                  'The difference cannot isolate this pilot’s consumption. A sibling-workspace canary also ran during the first batch.', '', '## Evidence and reproducibility', ''])
    trace_count = sum(bool(r['rollout']) for r in data)
    vids = runs['vidscribe']
    lines.append(f'Rollouts available for {trace_count}/{len(data)} runs. Of {len(vids)} vidscribe sessions, '
                 f'{sum(r["image_returns"]>0 for r in vids)} returned image content to the model, '
                 f'{sum(r["detail_requested"] for r in vids)} requested --at or --scan, '
                 f'and {sum(r["image_returns"]>0 and r["detail_requested"] for r in vids)} did both.')
    lines.extend(['', f'{sum(bool(r.get("detail_returned")) for r in vids)} vidscribe sessions returned a named detail frame or scan sheet in tool output. '
                  'Image count uses tool-returned image payloads. A detail request alone can fail.', '',
                  f'Distinct base and developer instruction hashes across {len(data)} rollouts: '
                  f'{len({r.get("common_instruction_sha256") for r in data})} after replacing workspace and runtime temp paths.'])
    revisions = ', '.join(sorted({r['harness_commit'][:12] for r in data}))
    flagged = [r for r in data if r['outside_paths']]
    paths = sorted({p.replace(str(Path.home()), '~') for r in flagged for p in r['outside_paths']})
    lines.extend(['', f'{len(flagged)} sessions referenced outside paths in recorded tool calls: ' + ', '.join(f'`{p}`' for p in paths) + '.', '', 'The read audit checks literal path operands in model tool calls. Paths include attempted accesses '
                  'and command destinations. The rollouts omit implicit library reads and dynamically constructed paths. '
                  'See the local run records for individual paths and instruction hashes.', '',
                  f'{sum(len(i.options)>4 for i in sample)} sampled items had more than four choices. The harness used the full option list. '
                  f'Sample seed {SEED}, proportional allocation across capability × audio strata, '
                  f'{sum(i.has_audio for i in sample)} audio and {sum(not i.has_audio for i in sample)} silent. '
                  f'{data[0]["codex_version"]}, {data[0]["model"]}, {data[0]["effort"]} effort. '
                  f'vidscribe `{data[0]["vidscribe_commit"][:12]}`, runner commits {revisions}.',
                  '', 'The workspace-write profile denies network, the development tree, existing rollouts and '
                  '/private/tmp (including the prototype key). The canary returned the local nonce and '
                  '“Operation not permitted” for a workspace symlink to an outside nonce. '
                  'Ignoring user config alone left personal skills in the prototype. The pilot also disables '
                  'host skill discovery, injected skill instructions, project documents, plugins and memories.'])
    print('\n'.join(lines))

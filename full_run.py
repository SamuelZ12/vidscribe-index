"""Complete the frozen public panel without writing to historical run sets."""
import concurrent.futures
import fcntl
import hashlib
import os
import random
import subprocess
import sys
import time
from dataclasses import asdict

from arms import GUIDE, GUIDED, PLAIN, arms, read
from baseline import RunSet, clean
from bounds import VIDSCRIBE, check_boundary
from media import cache, fetch, panel, prepare
from pilot import DATA, ROOT, RUNS, SEED, commit, write_json
from quota import weekly
from runner import finished, session

REVISION = '7a119b4786de1198ab533ebe85c0314ae35d90d7'
VERSION = 'codex-cli 0.169.0'
HISTORY = {'vidscribe': ('base', 3), GUIDED: (GUIDED, 3), 'stock': ('stock', 1),
           PLAIN: (PLAIN, 1), 'transcript': ('transcript', 1)}
METER = RUNS / 'full.meter.json'


def validate_tools():
    version = subprocess.check_output(['/opt/homebrew/bin/codex', '--version'], text=True).strip()
    if version != VERSION or clean(VIDSCRIBE) != REVISION:
        raise ValueError('Pinned CLI or vidscribe revision changed')
    if subprocess.check_output(['git', 'diff', '4e2c411', '--', str(GUIDE)]):
        raise ValueError('Guidance changed')


def historical():
    hashes = {}
    for name, repeats in HISTORY.values():
        for item in panel():
            for attempt in range(1, repeats + 1):
                path = RUNS / name / f'{item.item_id}.{attempt}.json'
                if not finished(path):
                    raise ValueError('Incomplete historical record')
                hashes[str(path.relative_to(RUNS))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return hashes


def checkpoint(done):
    now = weekly()
    state = read(METER) if METER.exists() else dict(before=now, checks=[])
    state['checks'].append(dict(done=done, meter=now, time=time.time(), load=os.getloadavg()))
    write_json(METER, state)
    used = now['usedPercent']
    print(f'{done} completed, weekly meter {used}%', flush=True)
    if (used > 88 or used - state['before']['usedPercent'] > 20
            or now['resetsAt'] != state['before']['resetsAt']):
        raise RuntimeError('Quota stop')


def launch(job):
    spec, item, attempt = job
    result = spec.record(item, attempt)
    if result.exists():
        raise ValueError('Record already exists')
    validate_tools()
    media = cache(item, REVISION)
    processing = 0 if spec.arm == 'stock' else read(media / 'preparation.json')['seconds']
    versions = {k: v for k, v in asdict(spec).items()
                if k not in ('arm', 'name', 'split', 'checkout', 'attempts')}
    session(item, arms[spec.arm], versions, result, media, VIDSCRIBE, attempt, processing,
            guidance=GUIDE if spec.arm == GUIDED else None, capture_inputs=True)


def run():
    ids = historical()
    path = RUNS / 'full.legacy.json'
    if path.exists() and ids != read(path):
        raise ValueError('Historical records changed')
    if not path.exists():
        write_json(path, ids)
    head = subprocess.check_output(['git', 'rev-parse', 'harness-v2^{commit}'], text=True).strip()
    if subprocess.check_output(['git', 'diff', head, '--', '*.py', 'split.json', str(GUIDE),
                                ':(exclude)full_report.py']):
        raise ValueError('Runner differs from tag')
    jobs = []
    for split in ('dev', 'holdout'):
        for arm, (_, old) in HISTORY.items():
            spec = RunSet(f'full-{split}-{arm}', arm, str(VIDSCRIBE), REVISION, head, 3, VERSION, split=split)
            for item in panel(split):
                if not (cache(item, REVISION) / 'preparation.json').exists():
                    raise ValueError('Incomplete preparation')
                for attempt in range(old + 1 if split == 'dev' else 1, 4):
                    spec.record(item, attempt).parent.mkdir(exist_ok=True)
                    jobs.append((spec, item, attempt))
    assert len(ids) == 900 and len(jobs) == 1260
    random.Random(SEED).shuffle(jobs)
    todo = [job for job in jobs if not finished(job[0].record(*job[1:]))]
    done = len(jobs) - len(todo)
    checkpoint(done)
    if not todo:
        return
    check_boundary()
    with concurrent.futures.ThreadPoolExecutor(4) as pool:
        while todo:
            batch = todo[:100 - done % 100]
            list(pool.map(launch, batch))
            del todo[:len(batch)]
            done += len(batch)
            checkpoint(done)
    if historical() != ids:
        raise ValueError('Historical records changed during measurement')


if __name__ == '__main__':
    with (DATA / 'measurement.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        validate_tools()
        if sys.argv[1:] == ['prepare']:
            fetch('holdout')
            prepare(panel('holdout'), VIDSCRIBE, REVISION)
        elif sys.argv[1:] == ['run']:
            run()
        else:
            sys.exit('usage: full_run.py prepare|run')

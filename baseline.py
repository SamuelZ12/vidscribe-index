"""Measure clean vidscribe revisions against the frozen development panel."""
import argparse
import concurrent.futures
import dataclasses
import fcntl
import json
import os
import random
import re
import subprocess
import time
from pathlib import Path

from bounds import MODEL, EFFORT, VIDSCRIBE, check_boundary
from media import cache, fetch, panel, prepare
from pilot import ARMS, DATA, ROOT, RUNS, SEED, commit, write_json
from quota import weekly
from runner import finished, session

ARMS_BY_NAME = {a.name: a for a in ARMS}


@dataclasses.dataclass(frozen=True)
class RunSet:
    name: str
    arm: str
    checkout: str
    vidscribe_commit: str
    harness_commit: str
    attempts: int
    codex_version: str
    model: str = MODEL
    effort: str = EFFORT
    split: str = 'dev'

    def record(self, item, attempt):
        return RUNS / self.name / f'{item.item_id}.{attempt}.json'


def clean(path):
    if subprocess.check_output(['git', '-C', path, 'status', '--porcelain']):
        raise ValueError(f'Dirty checkout: {path}')
    return commit(path)


def settings(name, arm, checkout, attempts, revision):
    if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_-]*', name) or attempts < 1:
        raise ValueError('Expected a simple set name and positive attempt count')
    try:
        harness = subprocess.check_output(['git', '-C', ROOT, 'describe', '--tags', '--abbrev=0',
                                          '--match', 'harness-v*'], text=True, stderr=subprocess.DEVNULL).strip()
    except subprocess.CalledProcessError:
        harness = 'HEAD'
    if subprocess.call(['git', '-C', ROOT, 'diff', '--quiet', harness, '--', '*.py','split.json']):
        raise ValueError('Measuring code differs from harness tag')
    return RunSet(name, arm, str(checkout), revision, subprocess.check_output(
        ['git','-C',ROOT,'rev-parse',harness+'^{commit}'], text=True).strip(), attempts,
        subprocess.check_output(['codex','--version'],text=True).strip())


def pending(spec, items):
    directory = RUNS / spec.name
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / 'set.json'
    value = dataclasses.asdict(spec)
    if path.exists():
        if json.loads(path.read_text()) != value:
            raise ValueError(f'Settings changed for {spec.name}')
    else:
        write_json(path, value)
    return [(spec, i, a) for i in items for a in range(1, spec.attempts+1)
            if not finished(spec.record(i, a))]


def launch(job):
    spec, item, attempt = job
    checkout = Path(spec.checkout)
    if clean(checkout) != spec.vidscribe_commit:
        raise ValueError('vidscribe revision changed')
    media = DATA if spec.arm == 'stock' else cache(item, spec.vidscribe_commit)
    processing = 0 if spec.arm == 'stock' else json.loads((media/'preparation.json').read_text())['seconds']
    versions = dataclasses.asdict(spec)
    for field in ('arm','name','split','checkout','attempts'):
        del versions[field]
    session(item, ARMS_BY_NAME[spec.arm], versions, spec.record(item, attempt),
            media, checkout, attempt, processing)


def measure(specs, ledger):
    items = panel()
    jobs = [job for spec in specs for job in pending(spec, items)]
    print(f'{len(jobs)} pending', flush=True)
    if not jobs:
        return
    for spec in specs:
        if spec.arm != 'stock':
            prepare(items, Path(spec.checkout), spec.vidscribe_commit)
    path = RUNS / (ledger + '.meter.json')
    state = json.loads(path.read_text()) if path.exists() else {'before': weekly(), 'checks': []}
    write_json(path, state)

    def checkpoint():
        now = weekly()
        done = sum(len(items)*s.attempts-len(pending(s, items)) for s in specs)
        state['checks'].append(dict(done=done, time=time.time(), meter=now, load=os.getloadavg()))
        write_json(path, state)
        if now['resetsAt'] != state['before']['resetsAt'] or now['usedPercent']-state['before']['usedPercent'] > 15:
            raise RuntimeError('Weekly meter reset or account movement exceeded 15 points')
        return done

    done = checkpoint()
    if done == 0:
        check_boundary()
    random.Random(SEED).shuffle(jobs)
    with concurrent.futures.ThreadPoolExecutor(4) as pool:
        while jobs:
            count = 100 - done % 100
            list(pool.map(launch, jobs[:count]))
            del jobs[:count]
            done = checkpoint()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('fetch')
    for name in ('prepare','run','baseline'):
        sub = commands.add_parser(name)
        sub.add_argument('--vidscribe', type=Path, default=VIDSCRIBE)
        if name == 'run':
            sub.add_argument('name')
            sub.add_argument('--arm', choices=ARMS_BY_NAME, default='vidscribe')
            sub.add_argument('--attempts', type=int, default=3)
    commands.add_parser('report').add_argument('sets', nargs='*', default=['base','stock','transcript'])
    sub = commands.add_parser('compare')
    sub.add_argument('sets', nargs=2, metavar='SET')
    args = parser.parse_args()
    DATA.mkdir(exist_ok=True)
    with (DATA/'measurement.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if args.command == 'fetch':
            return fetch()
        if args.command in ('report','compare'):
            from results import output
            return output(args.command, args.sets)
        checkout = args.vidscribe.expanduser().resolve()
        revision = clean(checkout)
        if args.command == 'prepare':
            return prepare(panel(), checkout, revision)
        presets = [('base','vidscribe',3),('stock','stock',1),('transcript','transcript',1)]
        if args.command == 'baseline':
            if revision != '7a119b4786de1198ab533ebe85c0314ae35d90d7':
                raise ValueError('Expected pinned baseline revision')
            sets = presets
        else:
            if args.name in {p[0] for p in presets}:
                if (args.name,args.arm,args.attempts) not in presets:
                    raise ValueError('Reserved baseline set settings')
                # All baseline attempts share one quota window.
                spec = settings(args.name, args.arm, checkout, args.attempts, revision)
                if pending(spec, panel()):
                    raise ValueError('Launch unfinished baseline sets together with baseline')
                print('0 pending')
                return
            sets = [(args.name,args.arm,args.attempts)]
        measure([settings(n,a,checkout,k,revision) for n,a,k in sets],
                'baseline' if args.command == 'baseline' else 'set-'+args.name)


if __name__ == '__main__':
    main()

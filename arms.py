"""Run the frozen ffmpeg comparisons. Raw records remain in ignored runs/."""
import concurrent.futures
import fcntl
import json
import os
import random
import subprocess
import sys
import time
from dataclasses import asdict
from pathlib import Path

from baseline import RunSet, clean, pending
from bounds import VIDSCRIBE, check_boundary
from media import cache, panel
from pilot import ARMS, Arm, ROOT, RUNS, DATA, SEED, write_json
from quota import weekly
from runner import session

GUIDE = ROOT / 'prototype/watch-video/SKILL.md'
PLAIN = 'ffmpeg-transcript'
GUIDED = 'ffmpeg-guided'
arms = {a.name: a for a in ARMS}
for name in (PLAIN, GUIDED):
    intro = 'A transcript with timestamps is in transcripts/. '
    if name == GUIDED:
        intro += 'Follow .agents/skills/watch-video/SKILL.md. '
    arms[name] = Arm(name, ('video.mp4', 'transcripts'), intro + arms['stock'].request)

def read(path):
    return json.loads(path.read_text())

def launch(job):
    spec, item, attempt = job
    media = cache(item, spec.vidscribe_commit)
    versions = {k:v for k,v in asdict(spec).items() if k not in ('arm','name','split','checkout','attempts')}
    processing = 0 if spec.arm == 'stock' else read(media/'preparation.json')['seconds']
    session(item, arms[spec.arm], versions, spec.record(item,attempt), media,
            VIDSCRIBE, attempt, processing, guidance=GUIDE if spec.arm == GUIDED else None,
            free_text=spec.split != 'dev')

def checkpoint(path, count):
    now = weekly()
    state = read(path) if path.exists() else dict(before=now, checks=[])
    state['checks'].append(dict(completed=count, time=time.time(), meter=now, load=os.getloadavg()))
    write_json(path,state)
    print('Completed', count, 'weekly usage', now['usedPercent'], flush=True)
    if now['resetsAt'] != state['before']['resetsAt'] or now['usedPercent']-state['before']['usedPercent'] > 20:
        raise RuntimeError('Quota window changed or movement exceeded 20 points')

def run(split):
    if split == 'dev':
        items = panel()
        schedule = [(GUIDED,3),(PLAIN,1)]
    else:
        from long_arms import prepared
        items = prepared(split)
        schedule = [(a,1) for a in ('vidscribe',GUIDED,PLAIN,'stock')]
    revision = clean(VIDSCRIBE)
    if revision != read(RUNS/'base/set.json')['vidscribe_commit']:
        raise ValueError('Different vidscribe revision')
    version = subprocess.check_output(['/opt/homebrew/bin/codex','--version'],text=True).strip()
    if version != read(RUNS/'base/set.json')['codex_version']:
        raise ValueError('Different agent CLI')
    jobs = []
    for arm,n in schedule:
        name = arm if split == 'dev' else split+'-'+arm
        # Pin the runner independently of subsequent analysis/report commits.
        head = subprocess.check_output(['git','log','-1','--format=%H','--','arms.py','runner.py','prototype/watch-video'],text=True).strip()
        spec = RunSet(name,arm,str(VIDSCRIBE),revision,head,n,version,split=split)
        jobs.extend(pending(spec,items))
    if not jobs:
        return
    path = RUNS/'arms.meter.json'
    count = sum(len(list(p.parent.glob('*.[123].json'))) for p in RUNS.glob('*/set.json')
                if read(p)['arm'] in (GUIDED,PLAIN) or p.parent.name.startswith('long-'))
    checkpoint(path,count)
    if count == 0:
        check_boundary()
    random.Random(SEED).shuffle(jobs)
    with concurrent.futures.ThreadPoolExecutor(4) as pool:
        while jobs:
            batch = jobs[:100-count%100]
            list(pool.map(launch,batch))
            del jobs[:len(batch)]
            count += len(batch)
            checkpoint(path,count)

if __name__ == '__main__':
    with (DATA/'measurement.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX | fcntl.LOCK_NB)
        run(sys.argv[1])

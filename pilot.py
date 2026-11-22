"""Run from the checkout with uv run pilot.py fetch|prepare|run|report."""
import concurrent.futures
import dataclasses
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import random
import shutil
import subprocess
import sys
import tempfile
import time
from collections import defaultdict

from bounds import VIDSCRIBE, environment

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data'
RUNS = ROOT / 'runs'
REV = 'e7404c468cd0ad83d7c96834c6eb4767fe831a72'
BASE = f'https://huggingface.co/datasets/Video-Index/Video-Index-v1-1/resolve/{REV}'
SEED = 20261121
LETTERS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'


@dataclasses.dataclass
class Item:
    item_id: str
    benchmark: str
    capability_group: str
    question: str
    options: list
    chance: float
    video_id: str
    duration_s: float
    has_audio: bool


Key = dict[str, str]


@dataclasses.dataclass(frozen=True)
class Arm:
    name: str
    files: tuple
    request: str


ARMS = (
    Arm('transcript', ('transcript.txt',), 'Read transcript.txt'),
    Arm('stock', ('video.mp4',), 'Watch video.mp4 using the installed ffmpeg and ffprobe tools'),
    Arm('vidscribe', ('video.mp4', 'frames', 'transcripts', 'notes.txt', '.agents'),
        'Watch the video. I already ran vidscribe. Continue from step 2 of .agents/skills/vidscribe/SKILL.md using frames/video with --at and --scan as needed'),
)


def rows():
    return [json.loads(line) for line in subprocess.check_output(
        ['curl', '-fsSL', '--retry', '3', BASE + '/items/test.jsonl']).splitlines()]


def write_json(path, value):
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(value, indent=2) + '\n')
    tmp.replace(path)


def sample():
    groups = defaultdict(list)
    for row in rows():
        fields = {f.name: row[f.name] for f in dataclasses.fields(Item) if f.name != 'has_audio'}
        item = Item(**fields, has_audio=bool(row['audio']))
        groups[item.capability_group, item.has_audio].append(item)
    # Largest remainder allocation across joint strata.
    target = {k: len(v) * 20 / sum(map(len, groups.values())) for k, v in groups.items()}
    counts = {k: math.floor(v) for k, v in target.items()}
    for k in sorted(groups, key=lambda k: (counts[k] - target[k], k))[:20 - sum(counts.values())]:
        counts[k] += 1
    rng = random.Random(SEED)
    return [i for k in sorted(groups) for i in rng.sample(groups[k], counts[k])]


def fetch():
    items = sample()
    write_json(DATA / 'items.json', [dataclasses.asdict(i) for i in items])

    def download(video):
        path = DATA / (video + '.mp4')
        if path.exists():
            with path.open('rb') as f:
                if hashlib.file_digest(f, 'sha256').hexdigest() == video:
                    return
        tmp = path.with_suffix('.part')
        subprocess.run(['curl', '-fsSL', '--retry', '3', '-o', tmp, BASE + '/videos/' + path.name], check=True)
        with tmp.open('rb') as f:
            if hashlib.file_digest(f, 'sha256').hexdigest() != video:
                raise ValueError(f'Invalid video digest for {video}')
        tmp.replace(path)
    with concurrent.futures.ThreadPoolExecutor(4) as pool:
        list(pool.map(download, sorted({i.video_id for i in items})))


def items():
    return [Item(**row) for row in json.loads((DATA / 'items.json').read_text())]


def commit(path):
    return subprocess.check_output(['git', '-C', path, 'rev-parse', 'HEAD'], text=True).strip()


def prepare():
    for i in items():
        manifest = DATA / (i.item_id + '.json')
        if manifest.exists():
            prior = json.loads(manifest.read_text())
            if prior['vidscribe_commit'] == commit(VIDSCRIBE) and (Path(prior['media']) / 'transcript.txt').exists():
                continue
        start = time.monotonic()
        desk = Path(tempfile.mkdtemp(prefix='clip-', dir='/private/tmp'))
        shutil.copyfile(DATA / (i.video_id + '.mp4'), desk / 'video.mp4')
        env = os.environ | {k: v for k, v in environment(desk).items() if k.startswith('VIDSCRIBE_')}
        with (desk / 'notes.txt').open('w') as log:
            subprocess.run([VIDSCRIBE / 'bin/vidscribe', 'video.mp4'], cwd=desk, env=env,
                           stdout=log, stderr=subprocess.STDOUT, check=True)
        assert (desk / 'frames/video/overview_01.jpg').is_file()
        shutil.copyfile(desk / 'transcripts/video.txt', desk / 'transcript.txt')
        skill = desk / '.agents/skills/vidscribe'
        skill.mkdir(parents=True)
        shutil.copyfile(VIDSCRIBE / 'skill/SKILL.md', skill / 'SKILL.md')
        write_json(manifest, dict(media=str(desk), seconds=time.monotonic()-start, vidscribe_commit=commit(VIDSCRIBE)))
        print('prepared', i.item_id, flush=True)


if __name__ == '__main__':
    DATA.mkdir(exist_ok=True)
    lock_name = 'sessions.lock' if sys.argv[1] in ('run','report') else 'lock'
    with (DATA / lock_name).open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if sys.argv[1] == 'run':
            from runner import run
            run(ready_only=sys.argv[2:] == ['--ready'])
        elif sys.argv[1] == 'report':
            from scoring import report
            report()
        else:
            {'fetch': fetch, 'prepare': prepare}[sys.argv[1]]()

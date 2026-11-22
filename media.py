"""Pinned inputs and reusable host preparations."""
import dataclasses
import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from bounds import environment
from pilot import DATA, ROOT, Item, download_videos, rows, write_json


def panel(partition="dev"):
    items = [Item(**row) for row in json.loads((DATA / (partition + '.json')).read_text())]
    expected = json.loads((ROOT / 'split.json').read_text())[partition]
    if sorted(i.item_id for i in items) != expected:
        raise ValueError('Panel metadata does not match frozen split. Run fetch.')
    return items


def fetch(partition="dev"):
    split = json.loads((ROOT / 'split.json').read_text())
    dataset = rows()
    ids = set(split[partition])
    assert len(ids) == {'dev': 100, 'holdout': 44}[partition] and len(dataset) == 144
    assert set(split['dev']).isdisjoint(split['holdout']) and set(split['dev']).union(split['holdout']) == {r['item_id'] for r in dataset}
    assert len({r['video_id'] for r in dataset}) == 144
    items = [Item(**{f.name: bool(r['audio']) if f.name == 'has_audio' else r[f.name]
                     for f in dataclasses.fields(Item)}) for r in dataset if r['item_id'] in ids]
    write_json(DATA / (partition + '.json'), [dataclasses.asdict(i) for i in items])
    download_videos(items)


def cache(item, revision):
    return DATA / 'prepared' / revision / item.item_id


def prepare(items, checkout, revision):
    for item in items:
        dest = cache(item, revision)
        if (dest / 'preparation.json').exists():
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=dest.parent) as staging:
            work = Path(staging) / 'media'
            work.mkdir()
            os.link(DATA / (item.video_id + '.mp4'), work / 'video.mp4')
            env = os.environ | {k: v for k, v in environment(work).items() if k.startswith('VIDSCRIBE_')}
            load = os.getloadavg()
            start = time.monotonic()
            with (work / 'notes.txt').open('w') as log:
                subprocess.run([checkout / 'bin/vidscribe', 'video.mp4'], cwd=work, env=env,
                               stdout=log, stderr=subprocess.STDOUT, check=True)
            seconds = time.monotonic() - start
            assert (work / 'frames/video/overview_01.jpg').is_file()
            shutil.copyfile(work / 'transcripts/video.txt', work / 'transcript.txt')
            skill = work / '.agents/skills/vidscribe'
            skill.mkdir(parents=True)
            shutil.copyfile(checkout / 'skill/SKILL.md', skill / 'SKILL.md')
            notes = work / 'notes.txt'
            notes.write_text(notes.read_text().replace(str(work), '.'))
            video = work / 'frames/video/video.mp4'
            video.unlink()
            video.symlink_to('../../video.mp4')
            write_json(work / 'preparation.json', dict(seconds=seconds, load=load))
            work.rename(dest)
        print('Prepared', item.item_id, flush=True)

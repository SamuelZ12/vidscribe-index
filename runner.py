import concurrent.futures
import json
import os
from pathlib import Path
import random
import shutil
import signal
import subprocess
import tempfile
import time

from audit import inspect_rollout
from bounds import EFFORT, MODEL, VIDSCRIBE, check_boundary, environment, options
from pilot import ARMS, DATA, LETTERS, ROOT, RUNS, SEED, commit, items, write_json
from quota import weekly


def run_file(item, arm):
    return RUNS / f'{item.item_id}.{arm.name}.1.json'


def finished(path):
    return path.exists() and json.loads(path.read_text())['status'] in ('ok', 'error', 'timeout', 'no_answer')


def one(item, arm, versions):
    result = run_file(item, arm)
    manifest = json.loads((DATA / (item.item_id + '.json')).read_text())
    if versions['vidscribe_commit'] != manifest['vidscribe_commit']:
        raise RuntimeError('Rerun prepare for this vidscribe revision')
    media = Path(manifest['media'])
    work = Path(tempfile.mkdtemp(prefix='clip-', dir=Path.home() / 'Movies'))
    for name in arm.files:
        src, dst = media / name, work / name
        if src.is_dir():
            shutil.copytree(src, dst, symlinks=True)
        else:
            shutil.copy2(src, dst)
    if 'frames' in arm.files:
        video = work / 'frames/video/video.mp4'
        video.unlink()
        video.symlink_to('../../video.mp4')
        notes = work / 'notes.txt'
        notes.write_text(notes.read_text().replace(str(media), '.'))
        (work / 'bin').mkdir()
        shutil.copy2(VIDSCRIBE / 'bin/vidscribe', work / 'bin/vidscribe')
    (work / 'question.md').write_text(item.question + '\n\n' + '\n'.join(
        f'{letter}. {text}' for letter, text in zip(LETTERS, item.options)) + '\n')
    allowed = list(LETTERS[:len(item.options)])
    with tempfile.TemporaryDirectory(dir='/private/tmp') as control:
        control = Path(control)
        schema = control / 'format.json'
        write_json(schema, dict(type='object', properties={'answer': dict(type='string', enum=allowed)},
                                required=['answer'], additionalProperties=False))
        out = control / 'answer'
        cmd = options(work) + ['--output-schema', str(schema), '-o', str(out),
                arm.request + ' and answer the question in question.md. Do not use the web. Reply with the letter.']
        start = time.time()
        proc = subprocess.Popen(cmd, cwd=work, env=environment(work), stdin=subprocess.DEVNULL,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
        status = 'ok'
        try:
            log, err = proc.communicate(timeout=1800)
            if proc.returncode:
                status = 'error'
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            log, err = proc.communicate()
            status = 'timeout'
        end = time.time()
        answer = None
        if out.exists():
            try:
                answer = json.loads(out.read_text()).get('answer')
            except (ValueError, AttributeError):
                pass
        if status == 'ok' and answer not in allowed:
            status = 'no_answer'
    events = [json.loads(l) for l in log.splitlines() if l.startswith(b'{')]
    thread = next((e['thread_id'] for e in events if e['type'] == 'thread.started'), None)
    traces = list((Path.home()/'.codex/sessions').glob(f'*/*/*/*-{thread}.jsonl')) if thread else []
    audit = inspect_rollout(traces[0], work) if traces else dict(rollout=None, used_percent=None,
        outside_paths=[], token_usage={}, image_returns=0, detail_requested=False, instruction_sha256=None)
    write_json(result, dict(item_id=item.item_id, arm=arm.name, attempt=1, workspace=str(work),
                            status=status, answer=answer, seconds=end-start, started=start, ended=end,
                            error=err.decode(errors='replace')[-2000:] if status=='error' else None,
                            **versions, **audit))
    print(item.item_id, arm.name, status, round(end-start), flush=True)


def run(ready_only=False):
    RUNS.mkdir(exist_ok=True)
    jobs = [(i, a) for i in items() for a in ARMS if not finished(run_file(i, a))]
    if ready_only:
        jobs = [(i, a) for i, a in jobs if (DATA / (i.item_id + '.json')).exists()]
    print(f'{len(jobs)} pending', flush=True)
    if not jobs:
        return
    if 'ChatGPT' not in subprocess.check_output(['codex', 'login', 'status'], stderr=subprocess.STDOUT, text=True):
        raise RuntimeError('ChatGPT login required')
    versions = dict(model=MODEL, effort=EFFORT, codex_version=subprocess.check_output(
        ['codex', '--version'], text=True).strip(), vidscribe_commit=commit(VIDSCRIBE), harness_commit=commit(ROOT))
    before = RUNS / 'before.json'
    if not before.exists():
        check_boundary()
    opening = weekly()
    if not before.exists():
        write_json(before, opening)
    start = time.time()
    random.Random(SEED).shuffle(jobs)
    with concurrent.futures.ThreadPoolExecutor(4) as pool:
        futures = [pool.submit(one, i, a, versions) for i, a in jobs]
        for f in concurrent.futures.as_completed(futures):
            f.result()
    closing = weekly()
    write_json(RUNS / 'after.json', closing)
    write_json(RUNS / f'batch-{int(start)}.json', dict(start=start, end=time.time(),
               count=len(jobs), before=opening, after=closing))

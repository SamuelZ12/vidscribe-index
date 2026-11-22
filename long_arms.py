"""Long-video inputs stay outside workspaces. Only the question text is staged."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import random
import re
import subprocess
import tempfile

from arms import arms, checkpoint, read
from baseline import clean
from bounds import VIDSCRIBE, environment, options
from media import cache, prepare
from pilot import DATA, RUNS, Item, SEED, write_json
from results import price
from statistics import mean

EVAL = VIDSCRIBE/'eval'
SRC = DATA/'long-src'
VIDEOS = re.findall(r'^\| `([\w-]{11})` \| [^|]+ \| (dev|holdout) \|$', (EVAL/'README.md').read_text(), re.M)
assert len(VIDEOS) == 12
LONG_ARMS = ('vidscribe','ffmpeg-guided','ffmpeg-transcript','stock')
GRADER = ('You grade answers to questions about a video. You get a question, the reference answer, and one candidate answer. '
          "Score: 1 = correct (matches the reference in substance), 0.5 = partially correct (some key part right, some missing or wrong), 0 = wrong, or 'unknown'. Return JSON.")

def inputs(split):
    for vid, label in VIDEOS:
        if split != 'long-'+label:
            continue
        questions = sum((read(EVAL/folder/(vid+'.json')) for folder in ('questions','hard/questions')), [])
        assert len(questions) == 9 and len({q['qid'] for q in questions}) == 9
        yield vid, questions

def download():
    SRC.mkdir(exist_ok=True)
    for vid,_ in VIDEOS:
        result = subprocess.run(['yt-dlp','-q','--no-warnings','-f','bv*[height<=720]+ba/b[height<=720]/b',
            '--merge-output-format','mp4','-o',str(SRC/'%(id)s.%(ext)s'),'https://www.youtube.com/watch?v='+vid])
        if result.returncode:
            print('Download failed',vid)

def item(vid,q):
    return Item('long_'+vid+'_'+q['qid'],'long',q['qid'],q['question'],[],0,vid,0,True)

def prep(split):
    rev = clean(VIDSCRIBE)
    for vid,qs in inputs(split):
        if not (SRC/(vid+'.mp4')).exists():
            print('Missing video',vid)
            continue
        link = DATA/(vid+'.mp4')
        if not link.exists():
            os.link(SRC/(vid+'.mp4'),link)
        first = item(vid,qs[0])
        prepare([first],VIDSCRIBE,rev)
        for q in qs[1:]:
            dest = cache(item(vid,q),rev)
            if not dest.exists():
                dest.symlink_to(cache(first,rev).name,target_is_directory=True)
        # Keep the verification image private and outside agent workspaces.
        subprocess.run(['ffmpeg','-nostdin','-v','error','-y','-ss',str(qs[0]['time_s']),'-i',str(link),
                        '-frames:v','1',str(SRC/(vid+'.jpg'))],check=True)

def prepared(split):
    rev = clean(VIDSCRIBE)
    return [item(v,q) for v,qs in inputs(split) if (SRC/(v+'.mp4')).exists()
            for q in qs if (cache(item(v,q),rev)/'preparation.json').is_file()]

def grade(job):
    path,q,candidate = job
    with tempfile.TemporaryDirectory(prefix='clip-', dir=Path.home()/'Movies') as desk, tempfile.TemporaryDirectory() as ctl:
        work = Path(desk)
        schema = Path(ctl)/'format.json'
        write_json(schema,dict(type='object',properties=dict(score=dict(type='number',enum=[0,.5,1]),reason=dict(type='string')),
                               required=['score','reason'],additionalProperties=False))
        out = Path(ctl)/'response'
        prompt = GRADER + f"\nQuestion: {q['question']}\nReference answer: {q['answer']}\nCandidate answer: {candidate or 'unknown'}"
        subprocess.run(options(work)+['--output-schema',str(schema),'-o',str(out),prompt],cwd=work,env=environment(work),
                       capture_output=True,stdin=subprocess.DEVNULL,timeout=1800,check=True)
        result = read(out)
        assert result['score'] in (0,.5,1)
        write_json(path,result)

def records(split):
    for vid,qs in inputs(split):
        if not (SRC/(vid+'.mp4')).exists():
            continue
        for q in qs:
            for arm in LONG_ARMS:
                path = RUNS/(split+'-'+arm)/(item(vid,q).item_id+'.1.json')
                yield vid,q,arm,read(path),path.with_suffix('.grade.json')

def grade_split(split):
    jobs = [(path,q,r['answer'] if r['status']=='ok' else 'unknown')
            for _,q,_,r,path in records(split) if not path.exists()]
    random.Random(SEED).shuffle(jobs)
    path = RUNS/'arms.meter.json'
    completed = sum(len(list(p.parent.glob('*.[123].json'))) + len(list(p.parent.glob('*.grade.json')))
                    for p in RUNS.glob('*/set.json') if p.parent.name.startswith(('ffmpeg-','long-')))
    with ThreadPoolExecutor(4) as pool:
        checkpoint(path, completed)
        while jobs:
            batch=jobs[:100-completed%100]
            list(pool.map(grade,batch))
            del jobs[:len(batch)]
            completed += len(batch)
            checkpoint(path,completed)

def cost_guard():
    def cost(r):
        if not r.get('requests'):
            raise RuntimeError('Cannot verify cost limit: missing usage')
        return sum(price(r['model'],r['requests']).values())
    short = mean(mean(cost(read(p)) for p in (RUNS/n).glob('*.[123].json'))
                 for n in ('base','stock','ffmpeg-guided','ffmpeg-transcript'))
    long = mean(cost(r) for _,_,_,r,_ in records('long-dev'))
    print(f'Dev long/short session cost ratio {long/short:.3f}')
    if long > 3*short:
        raise SystemExit('Dev complete. Stop before holdout under the 3x rule.')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action',choices=['download','prepare','grade','guard'])
    parser.add_argument('split',choices=['long-dev','long-holdout'],nargs='?')
    args = parser.parse_args()
    if args.action == 'download':
        download()
    elif args.action == 'guard':
        cost_guard()
    elif args.action == 'prepare':
        prep(args.split)
    else:
        grade_split(args.split)

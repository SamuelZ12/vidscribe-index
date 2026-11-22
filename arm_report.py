"""Print aggregate tables and paired intervals; never print question-level results."""
from collections import Counter, defaultdict
from itertools import combinations
import json
from pathlib import Path
import re
from statistics import mean

from arms import GUIDED, PLAIN, read
from baseline import RunSet
from long_arms import LONG_ARMS, records
from media import panel
from pilot import RUNS, rows
from results import AXES, aggregate_item, fmt, interval, price

def trace_counts(r):
    counts = Counter(sessions=1, images=r['image_returns'], seen=int(r['image_returns']>0))
    if not r.get('rollout'):
        return counts
    calls = {}
    for line in Path(r['rollout']).open():
        p = json.loads(line)['payload']
        kind = p.get('type')
        if kind in ('custom_tool_call','function_call'):
            calls[p['call_id']] = p.get('input') or p.get('arguments','')
        if kind not in ('custom_tool_call_output','function_call_output'):
            continue
        src = calls.get(p['call_id'],'')
        output = p.get('output',[])
        # Inspect text blocks only; image payloads can be several MB.
        out = ' '.join(b.get('text','') for b in output if isinstance(b,dict)) if isinstance(output,list) else str(output)
        viewed = (isinstance(output,list) and any(isinstance(b,dict) and
                  b.get('type') in ('input_image','image') for b in output))
        if viewed:
            for label, pattern in [('map_seen', r'(?:map|overview)_[^ /()]+?\.jpg'),
                                   ('burst_seen', r'(?:burst|scan)[^ /()]*?\.jpg'),
                                   ('crop_seen', r'crop[^ /()]*?\.(?:jpg|png)')]:
                if re.search(pattern,src,re.I):
                    counts[label]=1
        if 'Watching a video with ffmpeg' in out and 'watch-video' in src:
            counts['guide_returned']=1
        if 'ffmpeg' in src and re.search(r'tile=|tile\\?\s*=',src):
            counts['map_requested']=1
        if re.search(r'--scan\b|fps=(?:[2-9]\d*|1\d+)(?:[.,:/"]|\b)',src):
            counts['dense_requested']=1
        if re.search(r'crop=|sips\s+.*(?:--cropToHeightWidth| -c )|\.crop\(',src):
            counts['crop_requested']=1
    return counts

def table(title,points,comparisons):
    print('\n## '+title+'\n')
    print('| Arm | Score % [95% interval] | API $/question | Seconds/question |')
    print('|---|---:|---:|---:|')
    for arm,units in points.items():
        print('|',arm,'|',' | '.join(fmt(interval([u[a] for u in units.values()]),100 if a=='accuracy' else 1,
                    {'accuracy':1,'seconds':1,'dollars':4}[a]) for a in AXES),'|')
    print('\n| Difference | Score (pp) | $/question | Seconds/question |\n|---|---:|---:|---:|')
    for a,b in comparisons:
        left,right=points[a],points[b]
        assert left.keys()==right.keys()
        def differences(axis):
            return [None if left[k][axis] is None or right[k][axis] is None else left[k][axis]-right[k][axis] for k in left]
        print('|',a,'minus',b,'|',' | '.join(fmt(interval(differences(axis)),100 if axis=='accuracy' else 1,
                    {'accuracy':1,'seconds':1,'dollars':4}[axis]) for axis in AXES),'|')

def evidence(by_arm):
    print('\n| Arm | Sessions | With pictures | Image returns | Tiling requested | Dense sampling requested | Crop requested | Named map / burst / crop viewed | Guide returned | Errors / timeout / no answer |')
    print('|---|---:|---:|---:|---:|---:|---:|---|---:|---|')
    for arm,rs in by_arm.items():
        total=Counter()
        for r in rs:
            total.update(trace_counts(r))
        statuses=Counter(r['status'] for r in rs)
        print('|',arm,'|',' | '.join(str(total[k]) for k in ('sessions','seen','images','map_requested','dense_requested','crop_requested')),
              '|',' / '.join(str(total[k]) for k in ('map_seen','burst_seen','crop_seen')),'|',total['guide_returned'],
              '|',' / '.join(str(statuses[k]) for k in ('error','timeout','no_answer')),'|')

def short():
    items=panel()
    key={r['item_id']:r['answer'] for r in rows()}
    points,by_arm={},{}
    for name in ('base','stock','transcript',PLAIN,GUIDED):
        spec=RunSet(**read(RUNS/name/'set.json'))
        points[name]={}
        by_arm[name]=[]
        for i in items:
            rs=[read(spec.record(i,a)) for a in range(1,spec.attempts+1)]
            points[name][i.item_id]=aggregate_item(i,rs,key)
            by_arm[name].extend(rs)
    table('Video-Index dev',points,[(a,b) for a in (PLAIN,GUIDED) for b in ('base','stock')]+[(GUIDED,PLAIN)])
    evidence(by_arm)

def long(splits):
    data=[]
    for split in splits:
        for vid,q,a,r,path in records(split):
            data.append((split,vid,q['qid'],a,dict(accuracy=read(path)['score'] if r['status']=='ok' else 0,
                 dollars=sum(price(r['model'],r['requests']).values()) if r.get('requests') else None,
                 seconds=r['seconds']+r['processing_seconds']),r))
    for label in ['overall',*splits]:
        subset=[d for d in data if label=='overall' or d[0]==label]
        points,types={},{}
        for arm in LONG_ARMS:
            group=defaultdict(list)
            categories=defaultdict(list)
            for _,vid,qid,a,m,_ in subset:
                if a==arm:
                    group[vid].append(m)
                    categories[qid if not qid.startswith('h') else 'hard'].append(m['accuracy'])
            points[arm]={v:{k:None if any(r[k] is None for r in ms) else mean(r[k] for r in ms) for k in AXES}
                         for v,ms in group.items()}
            types[arm]=categories
        table('Long videos, '+label,points,[(PLAIN,'vidscribe'),(GUIDED,'vidscribe'),(GUIDED,PLAIN),(PLAIN,'stock'),(GUIDED,'stock')])
        cats=['v1','v2','v3','v4','mixed','speech','hard']
        print('\n| Arm | '+' | '.join(cats)+' |\n|---|'+'---:|'*len(cats))
        for arm,c in types.items():
            print('|',arm,'|',' | '.join(f'{mean(c[k]):.1%}' for k in cats),'|')
        print('\n| Paired score difference (pp) | '+' | '.join(cats)+' |\n|---|'+'---:|'*len(cats))
        for left,right in ((PLAIN,'vidscribe'),(GUIDED,'vidscribe'),(GUIDED,PLAIN)):
            cells=[]
            for cat in cats:
                scores=defaultdict(lambda:defaultdict(list))
                for _,vid,qid,a,m,_ in subset:
                    if (qid==cat or cat=='hard' and qid.startswith('h')) and a in (left,right):
                        scores[vid][a].append(m['accuracy'])
                cells.append(fmt(interval([mean(v[left])-mean(v[right]) for v in scores.values()]),100,1))
            print('|',left,'minus',right,'|',' | '.join(cells),'|')
    evidence({arm:[r for *_,a,m,r in data if a==arm] for arm in LONG_ARMS})

if __name__=='__main__':
    import sys
    if sys.argv[1:] == ['short']:
        short()
    else:
        long(sys.argv[1:])

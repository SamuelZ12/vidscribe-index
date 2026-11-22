"""Write a blinded 20-answer sample locally, then compare the reviewer's scores."""
import argparse
import random
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from long_arms import DATA, records
from pilot import SEED, write_json
from arms import read

def check(splits):
    sample = sorted((r['workspace'], q['question'],q['answer'],r['answer'],path)
                    for split in splits for _,q,_,r,path in records(split))
    chosen = random.Random(SEED).sample(sample,20)
    desk = DATA/'handcheck'
    desk.mkdir(exist_ok=True)
    write_json(desk/'blind.json', [dict(question=q,reference=ref,answer=answer)
                                   for _,q,ref,answer,_ in chosen])
    scores = desk/'review.json'
    if scores.is_file():
        manual = read(scores)
        if len(manual)!=20 or not all(x in (0,.5,1) for x in manual):
            raise ValueError('Expected 20 reviewer scores')
        print('Disagreements out of 20:',sum(score!=read(row[-1])['score']
                                              for score,row in zip(manual,chosen)))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('splits',nargs='+',choices=['long-dev','long-holdout'])
    check(parser.parse_args().splits)

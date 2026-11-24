"""List questions that every setup missed on every attempt, for a manual answer-key check.

Prints to stdout only, so the dataset's answer key never lands on disk.
"""
import sys
from collections import Counter

from full_run import HISTORY, RUNS, read
from media import panel
from pilot import LETTERS, rows
from scoring import score


def records(arm, part, item):
    name, old = HISTORY[arm]
    for attempt in (1, 2, 3):
        directory = name if part == 'dev' and attempt <= old else f'full-{part}-{arm}'
        yield read(RUNS / directory / f'{item.item_id}.{attempt}.json')


def main():
    key = {row['item_id']: row['answer'] for row in rows()}
    found = []
    total = 0
    for part in ('dev', 'holdout'):
        for item in panel(part):
            total += 1
            picks, hits = Counter(), 0
            for arm in HISTORY:
                for r in records(arm, part, item):
                    hits += score(item, r, key)[0]
                    picks[r['answer'] if r['status'] == 'ok' else r['status']] += 1
            if not hits:
                found.append((part, item, picks))
    print(f'{len(found)} of {total} questions missed by all {len(HISTORY)} setups on all 3 attempts\n')
    for part, item, picks in found:
        top, n = picks.most_common(1)[0]
        print(f'## {item.item_id} ({part}, {item.benchmark}, {item.capability_group}, '
              f'{item.duration_s:.0f}s, audio={item.has_audio})')
        print(f'video: {item.video_id}')
        print(item.question)
        for letter, option in zip(LETTERS, item.options):
            print(f'  {letter}. {option}')
        print(f'key: {key[item.item_id]} | agent answers: {dict(picks.most_common())} | '
              f'consensus: {top} {n}/15\n')


if __name__ == '__main__':
    sys.exit(main())

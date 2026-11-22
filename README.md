# vidscribe-index

Measure vidscribe quality, API-equivalent dollars and seconds per question on a frozen Video-Index v1.1 development panel. The local runner uses Samuel's ChatGPT login on the Mini, ffmpeg, ffprobe, uv and the host's installed vidscribe speech model. It keeps media, questions and attempt records under ignored directories. Only aggregate scores leave the machine.

## Reproduce the baseline

Use the tagged harness and a clean vidscribe checkout at `7a119b4786de`. From the harness directory:

```sh
uv run --python 3.13 baseline.py fetch
uv run --python 3.13 baseline.py prepare
uv run --python 3.13 baseline.py baseline
uv run --python 3.13 baseline.py report
uv run --python 3.13 baseline.py compare base stock
uv run --python 3.13 python -m unittest -v
```

Fetch hash-checks 100 dev videos. Prepare runs host speech and frame extraction once per item and vidscribe revision. A single run interleaves the three baseline sets with a fixed shuffle, runs up to four sessions at once and reads the weekly account meter every 100 completed sessions. Account movement above 15 points or a weekly reset interrupts the run. The meter includes other account activity. Repeating the baseline command skips all final records, including failures. A new harness clone creates fresh attempts. Keep the measured checkout and its ignored `runs/` directory for paired comparisons.

The 20 original pilot items are all in dev. The 100/44 assignment uses distinct videos and proportional capability × audio counts. Starting with the pilot IDs, the split generator shuffled each joint stratum with seed 20261122, then assigned the next item from the stratum furthest below its target (sorted stratum order breaks ties). The tracked ID manifest and its digest freeze the assignment.

## Measure a changed revision

With the changed code committed in a clean worktree at `../vidscribe-change`, run these commands from the same harness checkout as the baseline:

```sh
uv run --python 3.13 baseline.py prepare --vidscribe ../vidscribe-change
uv run --python 3.13 baseline.py run change-01 --vidscribe ../vidscribe-change --arm vidscribe --attempts 3
uv run --python 3.13 baseline.py compare change-01 base
uv run --python 3.13 baseline.py report base stock transcript change-01
```

Use a new set name per change. Positive paired accuracy and negative paired dollars or seconds favor the first set. A confidence interval crossing zero leaves the direction unresolved. The Pareto charts connect the undominated point estimates. Report regenerates the Markdown, JSON and self-contained HTML in `docs/`. Pricing happens at report time.

The [pilot report](docs/pilot-report.md) and original pilot records remain available. See the [baseline spec](docs/baseline-spec.md) for the measurement contract.

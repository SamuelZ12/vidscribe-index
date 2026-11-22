# vidscribe-index

The harness behind the [vidscribe benchmark](https://github.com/SamuelZ12/vidscribe/blob/master/docs/benchmark.md). It runs Codex CLI on video questions under five setups and records accuracy, API-equivalent dollars and seconds per question:

| Setup | What the agent gets |
|---|---|
| `transcript` | vidscribe's transcript, no video |
| `stock` | the video file, with `ffmpeg` and `ffprobe` installed |
| `ffmpeg-transcript` | the video file plus vidscribe's `.txt` and `.srt` transcript |
| `ffmpeg-guided` | the same, plus the guidance file in [`prototype/watch-video/SKILL.md`](prototype/watch-video/SKILL.md) |
| `vidscribe` | vidscribe's output, its skill, and its `--at` and `--scan` commands |

The prompts for each setup are in [`arms.py`](arms.py) and [`pilot.py`](pilot.py). Each session runs in a fresh folder under a Codex permissions profile that blocks the network and reads outside the folder ([`bounds.py`](bounds.py)).

## Results

- [Full run](docs/full-report.md): all 144 questions of [Video-Index v1.1](https://github.com/Espere-1119-Song/Video-Index), three attempts per setup, 2,160 sessions. Summary numbers are in [`docs/full-summary.json`](docs/full-summary.json).
- [Long talks](docs/ffmpeg-arms-report.md): 108 free-text questions on 12 long YouTube videos, graded blind. The questions are in [`long-questions/`](long-questions/).
- [Baseline](docs/baseline-report.md) and [pilot](docs/pilot-report.md): the earlier runs on the first 100 questions.

Every run used Codex CLI 0.169.0 with `gpt-6.2-sol` at medium effort, on a ChatGPT subscription. Dollars are computed from each request's token counts at API list prices ([`results.py`](results.py)).

## What this repository does not contain

No Video-Index videos, questions or answer keys, and no per-question results. `fetch` downloads the videos from the [Hugging Face dataset](https://huggingface.co/datasets/Video-Index/Video-Index-v1-1) at a pinned revision. The report scripts read the answer key from the same revision at report time and never write it to disk. Video-Index items keep the licences of their source benchmarks, several of them non-commercial. [`split.json`](split.json) lists only item IDs.

## Rerun the full panel

The harness was built for one Mac and pins its tools: Codex CLI 0.169.0 at `/opt/homebrew/bin/codex`, vidscribe at commit `7a119b4` in a sibling checkout, `ffmpeg`, `uv` and Python 3.13. Expect to edit those pins before it runs elsewhere.

```sh
uv run --python 3.13 baseline.py fetch       # the 100 dev videos
uv run --python 3.13 baseline.py prepare
uv run --python 3.13 baseline.py baseline    # dev: vidscribe, stock, transcript
bash prototype/run.sh                        # dev: the two ffmpeg setups, then the long talks
uv run --python 3.13 full_run.py prepare     # the 44 holdout videos
uv run --python 3.13 full_run.py run
uv run --python 3.13 full_report.py
```

Attempt records go to the ignored `runs/` folder. The full run used about 7 points of the weekly Codex meter. The sections below document the first baseline and the regression workflow it was built for.

## Baseline at harness-v1

The [report](docs/baseline-report.md), [Pareto charts](docs/pareto.html) and [summary](docs/baseline-summary.json) cover 500 sessions on vidscribe master at `7a119b4`. Both video arms beat transcript. Vidscribe's one-point accuracy lead over stock has a paired 95% interval from −6.7 to +9.0 points. The agent itself answered 7.3 seconds faster with vidscribe, but host processing added 35.6 seconds per question. Of 100 prepared transcripts, 65 contained no text. The transcript result measures an agent that still sees the question and options on those items.

The account meter rose from 40% to 42% during development and host preparation, before the baseline began. During the 64.6 minutes of sessions it moved from 42% to 46%. This implementation session shared the account. The meter cannot allocate usage between sessions. All 500 rollouts confirmed Codex 0.169.0, including the model, effort and network-disabled workspace policy. The pilot used this same session executable. Its report quoted the parent-shell version, 0.171.0.

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

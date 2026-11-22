# Baseline spec (Nov 22 2026)

## Goal

Samuel wants to improve vidscribe one change at a time and keep a change only when it is better on quality or on cost and no worse on the other. He wants the result shown the way Artificial Analysis shows its Coding Agent Index: score against cost, with a Pareto line. This step turns the pilot harness into the frozen measuring tool for that loop and records the baseline for vidscribe `main`.

The pilot (`docs/pilot-report.md`, harness `6ddfdc0`) stays as a frozen record. Read it and the pilot spec first. Everything the pilot spec says about isolation, the prompt, answer keys, `~/.codex` and failures counting as wrong still holds. Do not change the prompt text, the option schema, the permissions profile or the model settings: results must stay comparable with the pilot.

## What changes

### 1. A fixed split

- All 144 Video-Index v1.1 items, split once into `dev` (100) and `holdout` (44).
- The 20 pilot items all go in `dev` (their answers have been looked at).
- No `video_id` appears in both. Stratify by capability group and audio versus silent. Fixed seed. A test fails if the split ever changes.
- Fetch and prepare only what a command needs. Nothing in this step downloads or runs `holdout`.

### 2. Named run sets, repeat attempts

A run set is one point on the chart: `name`, `arm`, vidscribe checkout path (its commit is recorded and the checkout must be clean), model, effort, split, number of attempts.

- Records live at `runs/<name>/<item_id>.<attempt>.json`. A set's settings are written once in `runs/<name>/set.json`; rerunning the same name with different settings is an error.
- The vidscribe checkout is a command-line option, default `~/dev/vidscribe`, so a later change can be measured from a git worktree. Prepared media is keyed by item and vidscribe commit, lives under `data/` (not `/private/tmp`, which a reboot clears), and is reused across sets with the same commit.
- The set name never reaches the workspace, the prompt or the environment of a session.
- Rerunning a finished set does nothing. The pilot's 60 records stay readable (move them under `runs/pilot/` or leave them where the old report can find them; do not delete them).

### 3. Cost, the Artificial Analysis way

Reference: https://artificialanalysis.ai/methodology/coding-agents-benchmarking ("Efficiency Metrics"). Cost is pay-per-token API cost per task at provider list prices, not the subscription. Tokens and time are reported beside it.

- A price table in code, per model, with source URL and date. `gpt-6.2-sol` standard short-context prices per 1M tokens, read Nov 22 2026 from https://developers.openai.com/api/docs/pricing: input $2.00, cached input $0.10, 30-minute cache write $2.50, output $10.00 (reasoning tokens are billed as output). Requests above 272K input tokens are billed at long-context rates (input and cache doubled, output 1.5x).
- Dollars are computed at report time from the stored token counts, so a price change re-prices old runs. If the rollout gives per-request usage, price each request and apply the long-context rate where it applies; otherwise report how many sessions had a request above 272K.
- Time per question = agent seconds + the host's vidscribe processing seconds for that item. `stock` has no processing. `transcript` is charged the full processing time and the report says that overstates it.
- Run all preparation for a set before its sessions start, so processing time is not measured under session load. Record the load average at the start of preparation and of the sessions.

### 4. Statistics

- Per item, average its attempts. Per set, average items. Intervals resample items (10,000 draws, fixed seed).
- Per set: accuracy with 95% interval, chance-normalized accuracy, per-attempt accuracies, the share of items whose attempts disagree, counts of timeout / error / no answer, dollars per question with interval and split by token type, seconds per question with interval, agent seconds and processing seconds separately.
- Same-code noise, from the 3-attempt set: the standard deviation of the difference between two independent 3-attempt means, estimated from within-item attempt variance, and the smallest accuracy difference that clears it at 95%. Say plainly what it means for which changes can be detected.
- `compare <A> <B>`: paired by item, difference in accuracy, dollars and seconds, each with a 95% interval, and a one-line verdict on each axis (better, worse, no measurable difference).
- No per-item correctness in any printed or committed output. Aggregates only.

### 5. Report and charts

- `report` writes `docs/baseline-report.md` (numbers, limits, what surprised you) and `docs/pareto.html`: one self-contained page with two charts, accuracy against dollars per question and accuracy against seconds per question. Each set is a labelled point with 95% bars on both axes, the Pareto line is drawn, and the guessing level is marked. Also write the same aggregates to `docs/baseline-summary.json`.
- The report states the Codex weekly meter before and after and what else was running on the account if you can tell.

### 6. Cleanup

- A session's workspace is deleted once its record is written. The record keeps the rollout path.
- Do not delete the 65 existing `~/Movies/clip-*` folders or anything under `/private/tmp` from the pilot. Samuel has not approved that.

## The baseline run

On `dev`, vidscribe at `~/dev/vidscribe` `7a119b4` (`master`), `gpt-6.2-sol`, medium effort, at most 4 sessions at once:

| Set | Arm | Attempts | Sessions |
|---|---|---:|---:|
| `base` | vidscribe | 3 | 300 |
| `stock` | stock | 1 | 100 |
| `transcript` | transcript | 1 | 100 |

`stock` and `transcript` are the reference points and the sensitivity check: if the harness cannot separate `transcript` from the arms that see the video on 100 questions, say so prominently.

Budget: the pilot suggests about 7 points of the weekly Codex meter and under 2 hours of sessions. Check the meter every 100 sessions. Stop and report if this run alone has moved it more than 15 points.

## Done when

- One CLI covers fetch, prepare, run, report and compare from a clean clone on this Mini. A rerun of each baseline set reports nothing pending.
- Tests cover: the frozen split, scoring with several attempts, pricing on a hand-made example (including a long-context request), resume, and `compare` on a hand-made pair.
- `docs/baseline-report.md`, `docs/pareto.html` and `docs/baseline-summary.json` exist with real numbers from the 500 sessions.
- Small Conventional Commits pushed to `origin main`. Tag the commit the baseline was measured with as `harness-v1` and push the tag. After that tag, the measuring code does not change without a new tag.

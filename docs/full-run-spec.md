# Full run for publication: all 144 questions, three runs per setup

## Why

Samuel wants to publish what the index found, so other people can check it. The dev numbers are not fit to publish as they stand. Two setups have three runs per question and three have one. Only 100 of the 144 Video-Index v1.1 questions were run, so the scores do not sit beside the authors' table of 21 agents. This run fixes both. It changes no tool, prompt or guidance file.

## What to run

Five setups on all 144 questions of Video-Index v1.1 (100 `dev` and 44 `holdout` in `split.json`), three runs per question each.

| Setup | Have | Add |
|---|---|---|
| `vidscribe` (`runs/base`) | dev x 3 | holdout x 3 |
| `ffmpeg-guided` | dev x 3 | holdout x 3 |
| `stock` | dev x 1 | dev runs 2 and 3, holdout x 3 |
| `ffmpeg-transcript` | dev x 1 | dev runs 2 and 3, holdout x 3 |
| `transcript` | dev x 1 | dev runs 2 and 3, holdout x 3 |

That is 1,260 new sessions. The 44 holdout videos have not been fetched or processed yet: prepare them the same way as the dev ones, outside the sandbox, before any session. The 900 existing records stay as they are and count as runs. Never rewrite or delete an existing record file.

## Rules

- Start from `proto/ffmpeg-arms` (`d53b74b`) on branch `full-144`. Push the branch. Do not merge it and do not move `harness-v1`.
- Same agent, model and effort as every earlier record: Codex CLI 0.169.0 (the Homebrew binary), `gpt-6.2-sol`, medium. If the binary on this machine is no longer 0.169.0, stop and report before running anything.
- Same vidscribe commit (`7a119b4`), same prompts, same guidance file (`4e2c411`), same isolation, same processing-time charging as the earlier records. Any code change needed to run the holdout or to add runs to an existing set must leave what a session sees unchanged. Prove that by comparing a new record's prompt, workspace file list and permissions profile with an old record's for each setup, and say how you compared them.
- Tag the commit the new sessions ran from as `harness-v2` and push the tag.
- Interleave the five setups in one fixed shuffle, four workers, as before. A session that errors or times out scores zero and is reported, with one retry allowed only for an infrastructure failure (quota, network, sandbox start), never for a wrong or missing answer.
- All isolation, answer-key, `~/.codex` and aggregate-only rules from `docs/pilot-spec.md`, `docs/baseline-spec.md` and `docs/ffmpeg-arms-spec.md` still hold. Print and commit no per-question correctness.
- Budget: the weekly Codex meter read 63% when this spec was written. Read it before the first session and every 100 sessions. Stop and report if this work moves it more than 20 points or it passes 88%.

## What to report

Fixed before the run. Report each one whatever it shows.

1. **Main table.** Each setup on all 144 questions: accuracy with a 95% interval, API dollars per question, seconds per question, and the share of questions where the three runs disagreed.
2. **Paired differences** on all 144, with 95% intervals for accuracy, dollars and seconds:
   - `vidscribe` minus `stock`
   - `ffmpeg-transcript` minus `vidscribe`
   - `ffmpeg-guided` minus `ffmpeg-transcript`
   - `ffmpeg-transcript` minus `stock`
3. **The speech slice.** Questions whose video has audio and runs longer than 600 seconds. On dev (24 questions, one run for two of the setups) the setups with a transcript scored 42% and 46% against 29% for `stock`. That slice was chosen after seeing dev results, so dev cannot confirm it. Report `ffmpeg-transcript` minus `stock` and `vidscribe` minus `stock` on this slice three ways: holdout only, dev only, all 144. Give the number of questions in each. The holdout row is the check. Say plainly whether it holds, fails, or is too small to tell.
4. **Audio and silent rows.** Each setup's accuracy on questions with audio and on silent ones, all 144.
5. **Dev against holdout.** Each setup's accuracy on the 100 and on the 44, to show the holdout was not tuned on.
6. **Mixed dates.** Existing records ran on Nov 21 and 22 2026 and the new ones later. `vidscribe` and `ffmpeg-guided` get no new dev runs, so they have no such check; say so. For `stock`, `ffmpeg-transcript` and `transcript` compare old run 1 with new runs 2 and 3 on dev, paired, and report the difference with its interval.
7. **What agents did**, as in the earlier report: images viewed, dense sampling, crops, per setup.
8. **Run integrity.** Sessions run, failed, retried, the meter before and after, wall time, the Codex version in every record.

## Deliverables

- `docs/full-report.md`: the eight items above, the limits (one agent, one model, one effort level, 144 questions, three runs), and the commands to rebuild every table from the saved records.
- `docs/full-summary.json`: every number in the main table and the paired differences, with intervals, so a chart can be drawn without the run files.

# Pilot spec (Nov 21 2026)

## Goal

Samuel wants a "vidscribe video intelligence index": a score from public video benchmarks, run through a real coding agent, that he can use to check each vidscribe change against `main`. This pilot builds the smallest harness that produces a trustworthy number on one benchmark, and measures what a full run costs in time and Codex quota.

Out of scope for the pilot: other benchmarks, the weighted composite, the PR gate, a clean UI.

## Fixed choices

- Agent under test: `codex exec`, model `gpt-6.2-sol`, `model_reasoning_effort="medium"` (Samuel's choice), on his ChatGPT subscription login. Sandbox `workspace-write`, so no network for the agent.
- Benchmark: Video-Index v1.1, Hugging Face dataset `Video-Index/Video-Index-v1-1` (`items/test.jsonl`, `videos/<video_id>.mp4`). 144 four-or-fewer-option questions, 66 videos have audio. Research use only: never commit videos, questions or keys.
- Machine: this Mac mini. vidscribe is `~/dev/vidscribe` at `7a119b4` or later.
- Language: Python run with `uv`, standard library where it is enough. One CLI entry point.

## What a prototype already measured (throwaway, `/tmp/watch/run.sh`)

1. `codex exec --ignore-user-config --skip-git-repo-check -m gpt-6.2-sol -s workspace-write -C <dir> --json --output-schema <schema> -o <file> "<prompt>"` works headless and returns `{"answer":"B"}`. 15 to 28 s per short question.
2. Inside the sandbox there is no Metal device, so vidscribe's speech step fails (`No Metal device available`). Overview sheets on silent video, `--at` and `--scan` work inside it. So the harness runs `vidscribe <video>` itself, outside the sandbox, before the agent starts.
3. `--json` output does not show image views. The rollout file under `~/.codex/sessions/YYYY/MM/DD/` does (`view_image` inside code-mode `exec` calls) and also carries `token_count` events with `rate_limits.primary.used_percent`. `--ephemeral` writes no rollout.
4. The sandbox can read the whole disk. One agent read `~/dev/vidscribe/bin/vidscribe` unprompted.
5. Runs load Samuel's personal Codex setup (about 28k characters of instructions, pstack skills from `~/.agents/skills`) even with `--ignore-user-config`.
6. Two runs on files both named `video.mp4` share `/tmp/vidscribe/frames/video`. vidscribe honours `VIDSCRIBE_FRAMES_DIR` and `VIDSCRIBE_OUTDIR`.

## Data shapes (name these in code before writing logic)

- `Item`: `item_id`, `benchmark`, `capability_group`, `question`, `options`, `chance`, `video_id`, `duration_s`, `has_audio`. No answer field. The key lives in a separate `Key` map `item_id -> letter`.
- `Arm`: a table entry, not branches: `name`, what goes in the workspace, the sentence added to the prompt.
  - `transcript`: question plus the vidscribe transcript text only. No video, no frames.
  - `stock`: `video.mp4` plus the sentence that ffmpeg and ffprobe are installed. No transcript.
  - `vidscribe`: the output of the harness's own `vidscribe video.mp4` run (what it printed, the transcript, the frames folder with the video link inside), the vidscribe skill at `.agents/skills/vidscribe/SKILL.md` copied from `~/dev/vidscribe/skill/SKILL.md`, and the sentence that vidscribe was already run on the video with the frames folder path, so the agent continues from the skill's step 2 with `--at` and `--scan`.
- `Run`: one JSON file per `(item_id, arm, attempt)` holding `status` (`ok`, `timeout`, `error`, `no_answer`), `answer`, `seconds`, token usage, `used_percent` at end, model, effort, Codex version, vidscribe commit, harness commit, the rollout file path, and the list of paths the agent touched outside its workspace and frames folder. No `correct` field: scoring joins runs with the key at report time.

## Rules the harness must enforce

- Resumable and idempotent: a `Run` file that exists with a final status is skipped on rerun. A crash mid-run leaves no final file.
- Each run gets its own workspace, `VIDSCRIBE_FRAMES_DIR` and `VIDSCRIBE_OUTDIR`. Nothing two runs write is shared.
- The agent must not be able to tell it is being tested or reach the key. Workspace paths and prompt use ordinary words: none of `eval`, `test`, `judge`, `experiment`, `rubric`, `score`, `compare`, `benchmark`, `candidate`, `arena`, `index`, `pilot`, and no benchmark or item names. Keep keys and scored results out of any path a run can plausibly find: first check whether Codex can deny reads outside the workspace (a permissions profile or similar) and prove it with a canary file an agent is asked to print; if it cannot, keep the key off disk during runs (fetch it at report time) and rely on the out-of-workspace read audit above.
- Never copy, move or edit `~/.codex/auth.json`; a rotated refresh token would log Samuel out of Codex. Look for a supported way to run without his personal skills, `AGENTS.md` and memories. If there is no safe one, record a hash of the instructions each run received so every arm shares the same setup, and say so in the report.
- A timeout (30 minutes), an error, or a missing answer counts as wrong. Report those counts beside accuracy.
- The prompt is one organic request: watch the video (or read the transcript), answer the question in `question.md`, reply with the letter, do not use the web.

## The pilot run

- Sample 20 items with a fixed seed, stratified by capability group and by audio versus silent. Download only those videos.
- 3 arms, 1 attempt each, 60 runs, 3 or 4 at a time.
- Report (`docs/pilot-report.md`, committed, no questions or keys in it):
  - per arm: accuracy, chance-normalized accuracy (`(acc - chance)/(1 - chance)` averaged per item), counts of timeouts, errors and no-answers, median and max seconds, median tokens;
  - `vidscribe` minus `stock` and `vidscribe` minus `transcript` as paired differences with a paired bootstrap 95% interval, and a plain statement of what 20 items can and cannot show;
  - Codex weekly quota: `used_percent` before and after, and the estimate that gives for all 144 items times 3 arms;
  - whether every `vidscribe` run actually viewed images and used `--at` or `--scan`, and whether any run read outside its workspace, read from rollout files, not from the agent's own words;
  - what blocked or surprised you, and what the full run needs changed.

## Done when

- `uv run` commands for fetch, prepare, run and report work from a clean clone on this Mini, and a rerun of `run` after the pilot does nothing.
- A unit test covers scoring and the chance normalization on a hand-made example, and one covers resume.
- The pilot report exists with real numbers from the 60 runs.
- Commits are small, Conventional Commits, pushed to `origin main` (the repo is private and Samuel approved pushing).

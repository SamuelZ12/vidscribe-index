# vidscribe-index

Private harness that scores [vidscribe](https://github.com/SamuelZ12/vidscribe) on public video benchmarks, run through a real coding agent (Codex CLI on a ChatGPT subscription).

Status: pilot. First component: Video-Index v1.1 (144 questions). Benchmark videos, questions and answer keys are not committed; most are licensed for research use only.

## Run the pilot on the Mini

From a fresh checkout, with Codex logged in using ChatGPT, the vidscribe checkout at
`~/dev/vidscribe`, its speech model installed, ffmpeg on PATH, and uv installed:

```sh
uv run --python 3.13 pilot.py fetch
uv run --python 3.13 pilot.py prepare
uv run --python 3.13 pilot.py run
uv run --python 3.13 pilot.py report
uv run --python 3.13 python -m unittest -v
```

Fetch verifies each video's content hash against the pinned dataset. Prepare runs
speech recognition on the host, once per item, then run gives each session a
private copy of its arm's inputs. Run skips all completed statuses, including
failures. Use a fresh harness checkout for a new measurement, including after
changing vidscribe. Keep the vidscribe checkout clean at the intended commit.
Local inputs and per-session records live in ignored `data/` and `runs/`.
Prepared media lives in `/private/tmp/clip-*` and session workspaces in
`~/Movies/clip-*`. Report fetches the pinned keys into memory after all runs.

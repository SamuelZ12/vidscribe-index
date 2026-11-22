# Video-Index v1.1 pilot

Twenty paired questions, one fresh Codex session per arm and item. The score is the fraction answered correctly. Chance normalization subtracts each item’s chance and divides by its available improvement before averaging.

| Arm | Correct | Accuracy | Chance-normalized | Timeout | Error | No answer | Median s | Max s | Median tokens |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| transcript | 5/20 | 25.0% | -7.9% | 0 | 0 | 0 | 8.2 | 12.5 | 39,252 |
| stock | 7/20 | 35.0% | 7.9% | 0 | 0 | 0 | 21.3 | 112.0 | 86,269 |
| vidscribe | 8/20 | 40.0% | 14.6% | 0 | 0 | 0 | 20.8 | 79.6 | 97,404 |

## Paired accuracy differences

- Against stock, vidscribe won 3 and lost 2. Difference +5 percentage points (paired percentile bootstrap 95% interval -15 to +25).
- Against transcript, vidscribe won 5 and lost 2. Difference +15 percentage points (paired percentile bootstrap 95% interval -10 to +40).

Each question moves accuracy by five points. The intervals resample the 20 paired items 10,000 times. One attempt leaves agent rerun variance unmeasured. A reliable gate for small changes needs more items and repeated runs of the same revision.

## Resources

Up to four concurrent sessions took 8.6 minutes across active batches. First launch to last exit spanned 21.1 minutes including waits for media. Host media preparation took 10.0 minutes summed across items. Per-arm timing excludes preparation. Tokens include cached input and output (6,587,554 total). Scaling active batch time and host preparation by 144/20 gives 1.0 and 1.2 hours, respectively, before downloads. Clip lengths and scheduling affect both estimates.

The account-wide weekly meter went from 36% to 37% (a movement of +1 pp). Scaling 60 sessions to 432 gives 7.2 points under the same workload mix. The meter rounds to whole points and includes concurrent account activity. Rounding alone puts the linearly scaled account movement between 0.0 and 14.4 points. The difference cannot isolate this pilot’s consumption. A sibling-workspace canary also ran during the first batch.

## Evidence and reproducibility

Rollouts available for 60/60 runs. Of 20 vidscribe sessions, 20 returned image content to the model, 19 requested --at or --scan, and 19 did both.

19 vidscribe sessions returned a named detail frame or scan sheet in tool output. Image count uses tool-returned image payloads. A detail request alone can fail.

Distinct base and developer instruction hashes across 60 rollouts: 1 after replacing workspace and runtime temp paths.

3 sessions referenced outside paths in recorded tool calls: `/bin/bash`, `/dev/null`, `/opt/homebrew/Cellar`, `/opt/homebrew/bin`, `~/.cache`, `~/.cache/huggingface/hub`, `~/.cache/whisper`.

The read audit checks literal path operands in model tool calls. Paths include attempted accesses and command destinations. The rollouts omit implicit library reads and dynamically constructed paths. See the local run records for individual paths and instruction hashes.

9 sampled items had more than four choices. The harness used the full option list. Sample seed 20261121, proportional allocation across capability × audio strata, 9 audio and 11 silent. codex-cli 0.171.0, gpt-6.2-sol, medium effort. vidscribe `7a119b4786de`, runner commits 25c4832e4ea8, 38e41a699888, d2e9dc0b4928, d37f83dcb77c, dc856cfb7949.

The workspace-write profile denies network, the development tree, existing rollouts and /private/tmp (including the prototype key). The canary returned the local nonce and “Operation not permitted” for a workspace symlink to an outside nonce. Ignoring user config alone left personal skills in the prototype. The pilot also disables host skill discovery, injected skill instructions, project documents, plugins and memories.

## What the rollouts showed

All 60 recorded turn contexts used gpt-6.2-sol at medium effort with workspace writes enabled and network access disabled. The tool calls used shell execution, image viewing and shell-session polling. All 20 vidscribe sessions saw images. One answered after viewing an overview sheet. The other 19 also requested and received detail imagery.

Two stock sessions listed Homebrew directories while looking for speech tools. One received an explicit permission error for the home cache. The other probed model cache paths with stderr suppressed. A third stock session redirected stderr to `/dev/null`. The recorded calls showed no access to benchmark data, the key, other arms, or rollouts. A separate sibling-workspace canary also returned a permission error. The path audit is evidence about model-initiated tool calls rather than a complete filesystem trace.

Fourteen transcripts were empty or contained only whitespace, including all 11 silent clips. The transcript arm still received the options and could guess. The longest video was 2 hours 20 minutes. From the first fetch to the last agent exit, the pilot took 26.0 minutes on this Mini, with downloads, host preparation and sessions overlapping. The five runner revisions reflect work on preparation, auditing and reporting during the pilot. The agent prompt, option schema, model, effort and permissions stayed the same across batches.

For change checks, freeze this panel and the harness revision, run the base revision twice to measure same-code variation, then pair base and changed vidscribe on the same items. The 144-item run would improve resolution. A quieter quota window would narrow the cost estimate. The pilot establishes an executable baseline at `7a119b4786de`; it measures the three tool configurations at that revision.

## Reproduce on the Mini

```sh
uv run --python 3.13 pilot.py fetch
uv run --python 3.13 pilot.py prepare
uv run --python 3.13 pilot.py run
uv run --python 3.13 pilot.py report
uv run --python 3.13 python -m unittest -v
```

The measured checkout returns `0 pending`. Use a fresh checkout for another 60 attempts. The CLI prints the calculated portion of this report. A clean checkout reproduced it using the saved run records, a verified video cache with one fresh download, and one freshly prepared clip.

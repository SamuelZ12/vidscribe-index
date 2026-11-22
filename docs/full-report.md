# Video-Index v1.1

We compared five ways of answering a video question with one agent, Codex CLI 0.169.0, using gpt-6.2-sol at medium reasoning effort. Each setup answered all 144 questions three times. The four comparisons and the speech slice were fixed before collecting holdout answers.

## All questions

| Setup | Accuracy % | API $/question | Seconds/question | Disagree % |
|---|---|---|---|---|
| vidscribe | 38.2 [31.0, 45.4] | 0.0897 [0.0818, 0.0984] | 73.5 [60.9, 87.3] | 21.5 [15.3, 28.5] |
| ffmpeg-guided | 38.0 [31.0, 45.1] | 0.0923 [0.0850, 0.1003] | 80.2 [67.0, 94.7] | 25.7 [18.8, 32.6] |
| stock | 37.7 [30.8, 44.7] | 0.0728 [0.0636, 0.0835] | 42.4 [36.8, 48.7] | 33.3 [25.7, 41.0] |
| ffmpeg-transcript | 35.2 [28.2, 42.1] | 0.0591 [0.0528, 0.0657] | 70.3 [57.7, 84.0] | 27.1 [20.1, 34.7] |
| transcript | 17.6 [12.0, 23.6] | 0.0230 [0.0214, 0.0248] | 49.2 [37.8, 61.8] | 30.6 [23.6, 38.2] |

Intervals are 95% percentile intervals from 10,000 fixed-seed question resamples, after averaging attempts within question. Disagreement counts different letters or statuses. Time includes agent execution and full host preparation for every setup except stock. This overcharges transcript delivery and excludes download, staging and queue time. API-equivalent dollars use the frozen November 22 per-request price table in results.py.

## Paired differences

| Difference | Accuracy (pp) | API $/question | Seconds/question |
|---|---|---|---|
| vidscribe minus stock | 0.5 [-4.9, 5.8] | 0.0169 [0.0101, 0.0232] | 31.1 [22.0, 41.2] |
| ffmpeg-transcript minus vidscribe | -3.0 [-7.2, 0.9] | -0.0307 [-0.0359, -0.0257] | -3.1 [-5.1, -1.1] |
| ffmpeg-guided minus ffmpeg-transcript | 2.8 [-1.4, 6.9] | 0.0333 [0.0292, 0.0373] | 9.9 [8.0, 11.8] |
| ffmpeg-transcript minus stock | -2.5 [-7.6, 2.5] | -0.0137 [-0.0210, -0.0074] | 27.9 [18.7, 38.2] |

## Speech slice

Questions with audio and duration over 600 seconds. Dev suggested this slice. Only holdout independently checks it.

| Split | Questions | ffmpeg-transcript minus stock (pp) | vidscribe minus stock (pp) |
|---|---|---|---|
| Holdout | 10 | -23.3 [-50.0, 0.0] | -26.7 [-50.0, -6.7] |
| Dev | 24 | 15.3 [0.0, 31.9] | 13.9 [-1.4, 30.6] |
| All | 34 | 3.9 [-9.8, 18.6] | 2.0 [-12.7, 16.7] |

Holdout verdict: **fails**.

## Audio, silent, dev and holdout

| Setup | Audio (66), accuracy % | Silent (78), accuracy % | Dev (100), accuracy % | Holdout (44), accuracy % |
|---|---|---|---|---|
| vidscribe | 31.3 | 44.0 | 40.0 | 34.1 |
| ffmpeg-guided | 31.3 | 43.6 | 39.7 | 34.1 |
| stock | 31.3 | 43.2 | 37.0 | 39.4 |
| ffmpeg-transcript | 32.8 | 37.2 | 37.3 | 30.3 |
| transcript | 27.8 | 9.0 | 19.3 | 13.6 |

## Mixed dates

Mean of new dev runs 2 and 3 minus old run 1, paired by question.

| Setup | Accuracy difference (pp) |
|---|---|
| stock | -3.0 [-9.5, 3.0] |
| ffmpeg-transcript | 0.5 [-6.5, 7.5] |
| transcript | 3.5 [0.0, 7.5] |

vidscribe and ffmpeg-guided have only historical dev runs, so date drift cannot be checked for either. Split differences also reflect different questions.

## What agents did

| Setup | Sessions | Sessions viewing images | Image returns | Dense requests | Crop requests |
|---|---|---|---|---|---|
| vidscribe | 432 | 432 | 7671 | 118 | 7 |
| ffmpeg-guided | 432 | 432 | 4092 | 352 | 63 |
| stock | 432 | 432 | 2496 | 194 | 78 |
| ffmpeg-transcript | 432 | 432 | 1932 | 191 | 68 |
| transcript | 432 | 0 | 0 | 0 | 0 |

One sheet is one image return. Dense sampling and crops count sessions requesting them, including requests that failed.

## Run integrity and limits

Historical sessions: 900, hash-checked before and after. New sessions: 1260. Of 2,160 sessions, 2,160 returned valid answers. Errors: 0. Timeouts: 0. Missing answers: 0. No answer session was retried. Every record specifies codex-cli 0.169.0. Rollouts confirm CLI, model, effort, sandbox and network policy in 2,160 of 2,160 sessions.

Preflight weekly usage was 63%. During collection account-wide weekly usage moved from 64% to 70%. The checkpoint window lasted 2.85 hours. Other account use cannot be separated.

For each setup we compared the new rollout prompts and effective permission profiles to a historical rollout, normalizing the temporary workspace and CLI paths. Historical sessions did not store input manifests. We reconstructed their staging rules against each new question’s cached media and checked the file list captured immediately before the new session. Every setup also had at least one new file list matching a reconstructed historical dev workspace entry for entry. The outside-read canary preceded collection.

These results cover one agent, model and effort, 144 questions, and three attempts. They do not establish equivalence or generalize to other agents. Intervals are per comparison and do not account for variability in host preparation times.

## Rebuild

Requires the saved local records, cached inputs, rollouts and access to the pinned dataset key.

```sh
uv run --python 3.13 full_report.py
```

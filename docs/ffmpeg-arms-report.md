# Does an agent still need vidscribe's frame commands?

The experiment holds the timestamped transcript fixed and varies how an agent sees the picture. The decision is whether to keep the frame CLI for lectures, talks and podcasts, and whether an ffmpeg skill changes the answer. The 100 public questions and 108 long-video questions are separate measurements.

## Decision

Use plain ffmpeg and ffprobe with the timestamped transcript as the default picture interface for long-video questions. Keep media acquisition and transcription. On Samuel's 108 questions, plain ffmpeg scored 95.4% against vidscribe's 95.8%, with about 30% lower agent cost and essentially identical charged time. Plain ffmpeg minus vidscribe was −0.5 percentage points, with a paired 95% interval of −3.2 to +2.3. At 100 public questions the difference was −3.0 [−10.7, +4.7]. These panels support a cheaper default, while leaving room for a real accuracy loss. Only one model and effort were tested.

The guidance changed how agents watched. All 408 guided answer sessions returned the skill contents and images. On the long set it raised dense-sampling requests from 8 to 67 sessions out of 108 and image returns from 452 to 782. Its score difference against unguided ffmpeg was 0.0 [−2.8, +2.8] points. It added $0.0445 and 28.0 seconds per long question. On the public panel it added 2.7 [−3.7, +9.0] points at an extra $0.0267 and 9.3 seconds. I would leave the guide optional.

The narrower case for retaining the frame commands is visual search without a spoken anchor. On the 36 hard long questions, vidscribe earned 100.0%, guided ffmpeg 97.2%, and plain ffmpeg 94.4%. Plain minus vidscribe was −5.6 [−13.9, 0.0] points. With three such questions per video and one attempt per arm, this is a reason to keep the commands available for hard searches. The largest gain from supplying a transcript was on the 12 speech questions, where plain ffmpeg went from stock's 54.2% to 100%. Scores near the ceiling leave little room for another arm to improve.

The 54 dev questions gave every transcript-equipped arm 98.1%. The six holdout videos separated them slightly: vidscribe 93.5%, plain and guided ffmpeg 92.6%. Six clusters per split make the intervals particularly sensitive to the sampled videos. A zero-width paired interval means the observed cluster differences were identical. Equivalence on future videos would require a prespecified acceptable loss and more independent videos.

## Grading and run integrity

All 832 answer sessions returned valid answers and have verified rollout contexts. Each of the 432 long answers received one separate blind grade under the README rubric with the same fixed model and medium effort. I independently scored a fixed-seed sample of 20 with the arm and grader score hidden. I disagreed with 2. Reported scores retain the original grader decisions. No question or arm was skipped. The recorded tool-call path audit found zero long sessions naming the source repository or an eval directory in outside paths. That audit captures literal file operands.

The long-dev mean agent cost was 1.133 times the public mean, weighting each of the four matched arms equally. The weekly meter moved 52% → 56% over the 400 public sessions and finished at 63%, an 11-point account-wide increase. Grading is included in meter monitoring. It is excluded from the answer-session dollar and time tables. No budget stop fired. On long videos the shared full-preparation charge averaged 154.7 seconds. Agent execution alone averaged 29.2 seconds for vidscribe, 29.4 for plain ffmpeg with transcripts, 57.4 for guided ffmpeg and 67.9 for stock. Cached transcripts and repeated questions on the same video would amortize the host charge.

## Protocol

Guidance commit `4e2c411` predates all sessions. On a cached 537.886-second 1080p video, the probe read the streams, the mapping command produced three 4×4 sheets, and the seek to 8:14 produced a 1920×1080 frame, a 960×540 crop and a 16-tile burst. The commands worked as written. All 100 public preparations had both transcript files.

The account-wide weekly meter opened at 52%. The first canary actually denied the outside read, but its tool output was nested and the old parser could not verify it. The runner was restarted after adding a rollout fallback. Only the successful canary opened the answer sessions.

Public sessions interleave the two new arms with a fixed shuffle and four workers. The historical arms retain their original measurements. The two ffmpeg arms use the full cached processing charge because timing transcript-only runs would require retranscribing 34.7 hours of audio in the public panel alone. This overstates latency for transcript delivery. API-equivalent dollars cover the answer session, excluding grading. Seconds cover agent execution and host processing, excluding downloading, setup and queueing.

## Download verification

All 12 videos downloaded. The Food Network video returned HTTP 403 on its first attempt and succeeded with the same command on retry. I inspected one reference moment per video at full frame size. Eleven showed the expected detail at the recorded second. The podcast was in a card transition at that second, and the expected detail was legible one second later within the recorded visible span. This checks one moment per video.

## Reproduce

On this Mini, the frozen public preparation cache and the original 500 control records are in ignored local directories. From the prototype branch:

```sh
cd ~/dev/vidscribe-index
bash prototype/run.sh
```

To reproduce the tables and grade-audit count from the saved local records without launching sessions:

```sh
uv run --python 3.13 arm_report.py short
uv run --python 3.13 arm_report.py long-dev long-holdout
uv run --python 3.13 prototype/handcheck.py long-dev long-holdout
```

The run script resumes the recorded experiment. To take fresh measurements, use a separate checkout with the same baseline records and cached media. An account movement above 20 points stops the run. A mean answer-session cost above three times the public mean across the same four arms stops it after long-video dev.

## Measurements

## Video-Index dev

| Arm | Score % [95% interval] | API $/question | Seconds/question |
|---|---:|---:|---:|
| base | 40.0 [31.3, 48.7] | 0.0864 [0.0767, 0.0971] | 68.9 [54.6, 84.7] |
| stock | 39.0 [30.0, 49.0] | 0.0726 [0.0617, 0.0839] | 40.5 [33.9, 47.7] |
| transcript | 17.0 [10.0, 24.0] | 0.0250 [0.0221, 0.0280] | 45.8 [33.2, 59.9] |
| ffmpeg-transcript | 37.0 [28.0, 47.0] | 0.0645 [0.0562, 0.0735] | 66.3 [51.8, 81.9] |
| ffmpeg-guided | 39.7 [31.0, 48.7] | 0.0911 [0.0827, 0.1005] | 75.6 [60.6, 92.0] |

| Difference | Score (pp) | $/question | Seconds/question |
|---|---:|---:|---:|
| ffmpeg-transcript minus base | -3.0 [-10.7, 4.7] | -0.0220 [-0.0298, -0.0143] | -2.6 [-5.9, 1.0] |
| ffmpeg-transcript minus stock | -2.0 [-10.0, 6.0] | -0.0081 [-0.0172, 0.0008] | 25.8 [14.3, 38.3] |
| ffmpeg-guided minus base | -0.3 [-5.3, 4.7] | 0.0047 [-0.0014, 0.0105] | 6.7 [3.9, 9.4] |
| ffmpeg-guided minus stock | 0.7 [-7.0, 8.3] | 0.0186 [0.0110, 0.0254] | 35.0 [23.4, 47.7] |
| ffmpeg-guided minus ffmpeg-transcript | 2.7 [-3.7, 9.0] | 0.0267 [0.0207, 0.0327] | 9.3 [6.0, 12.4] |

| Arm | Sessions | With pictures | Image returns | Tiling requested | Dense sampling requested | Crop requested | Named map / burst / crop viewed | Guide returned | Errors / timeout / no answer |
|---|---:|---:|---:|---:|---:|---:|---|---:|---|
| base | 300 | 300 | 4842 | 15 | 71 | 3 | 298 / 52 / 0 | 0 | 0 / 0 / 0 |
| stock | 100 | 100 | 514 | 100 | 40 | 16 | 0 / 3 / 1 | 0 | 0 / 0 / 0 |
| transcript | 100 | 0 | 0 | 0 | 0 | 0 | 0 / 0 / 0 | 0 | 0 / 0 / 0 |
| ffmpeg-transcript | 100 | 100 | 444 | 100 | 48 | 17 | 0 / 0 / 0 | 0 | 0 / 0 / 0 |
| ffmpeg-guided | 300 | 300 | 2733 | 300 | 243 | 47 | 255 / 46 / 2 | 300 | 0 / 0 / 0 |

## Long videos, overall

| Arm | Score % [95% interval] | API $/question | Seconds/question |
|---|---:|---:|---:|
| vidscribe | 95.8 [92.1, 99.1] | 0.0834 [0.0711, 0.0974] | 183.8 [158.7, 213.9] |
| ffmpeg-guided | 95.4 [91.2, 99.1] | 0.1029 [0.0983, 0.1072] | 212.0 [187.5, 241.3] |
| ffmpeg-transcript | 95.4 [92.1, 98.6] | 0.0585 [0.0505, 0.0680] | 184.0 [159.9, 212.6] |
| stock | 89.8 [83.3, 95.8] | 0.1074 [0.0915, 0.1238] | 67.9 [58.9, 76.6] |

| Difference | Score (pp) | $/question | Seconds/question |
|---|---:|---:|---:|
| ffmpeg-transcript minus vidscribe | -0.5 [-3.2, 2.3] | -0.0249 [-0.0371, -0.0134] | 0.2 [-3.0, 3.4] |
| ffmpeg-guided minus vidscribe | -0.5 [-2.8, 1.4] | 0.0195 [0.0063, 0.0310] | 28.2 [24.5, 31.4] |
| ffmpeg-guided minus ffmpeg-transcript | 0.0 [-2.8, 2.8] | 0.0445 [0.0360, 0.0521] | 28.0 [24.2, 31.3] |
| ffmpeg-transcript minus stock | 5.6 [0.9, 9.7] | -0.0489 [-0.0620, -0.0358] | 116.1 [92.9, 141.8] |
| ffmpeg-guided minus stock | 5.6 [2.3, 8.8] | -0.0044 [-0.0191, 0.0093] | 144.1 [120.3, 170.5] |

| Arm | v1 | v2 | v3 | v4 | mixed | speech | hard |
|---|---:|---:|---:|---:|---:|---:|---:|
| vidscribe | 87.5% | 100.0% | 91.7% | 100.0% | 83.3% | 100.0% | 100.0% |
| ffmpeg-guided | 87.5% | 100.0% | 91.7% | 100.0% | 87.5% | 100.0% | 97.2% |
| ffmpeg-transcript | 87.5% | 100.0% | 100.0% | 100.0% | 87.5% | 100.0% | 94.4% |
| stock | 87.5% | 100.0% | 91.7% | 100.0% | 83.3% | 54.2% | 97.2% |

| Paired score difference (pp) | v1 | v2 | v3 | v4 | mixed | speech | hard |
|---|---:|---:|---:|---:|---:|---:|---:|
| ffmpeg-transcript minus vidscribe | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 8.3 [0.0, 25.0] | 0.0 [0.0, 0.0] | 4.2 [0.0, 12.5] | 0.0 [0.0, 0.0] | -5.6 [-13.9, 0.0] |
| ffmpeg-guided minus vidscribe | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 4.2 [0.0, 12.5] | 0.0 [0.0, 0.0] | -2.8 [-8.3, 0.0] |
| ffmpeg-guided minus ffmpeg-transcript | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | -8.3 [-25.0, 0.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 2.8 [0.0, 8.3] |

## Long videos, long-dev

| Arm | Score % [95% interval] | API $/question | Seconds/question |
|---|---:|---:|---:|
| vidscribe | 98.1 [94.4, 100.0] | 0.0878 [0.0678, 0.1108] | 186.9 [151.8, 234.1] |
| ffmpeg-guided | 98.1 [94.4, 100.0] | 0.1030 [0.0988, 0.1079] | 215.1 [183.6, 259.8] |
| ffmpeg-transcript | 98.1 [94.4, 100.0] | 0.0555 [0.0502, 0.0608] | 185.0 [152.9, 229.4] |
| stock | 91.7 [85.2, 97.2] | 0.1101 [0.0918, 0.1312] | 64.8 [56.5, 72.8] |

| Difference | Score (pp) | $/question | Seconds/question |
|---|---:|---:|---:|
| ffmpeg-transcript minus vidscribe | 0.0 [0.0, 0.0] | -0.0323 [-0.0515, -0.0165] | -1.9 [-6.0, 2.1] |
| ffmpeg-guided minus vidscribe | 0.0 [0.0, 0.0] | 0.0153 [-0.0070, 0.0340] | 28.1 [21.5, 33.5] |
| ffmpeg-guided minus ffmpeg-transcript | 0.0 [0.0, 0.0] | 0.0476 [0.0413, 0.0554] | 30.1 [25.6, 34.1] |
| ffmpeg-transcript minus stock | 6.5 [2.8, 10.2] | -0.0546 [-0.0724, -0.0377] | 120.2 [88.1, 158.5] |
| ffmpeg-guided minus stock | 6.5 [2.8, 10.2] | -0.0071 [-0.0276, 0.0115] | 150.3 [118.7, 190.0] |

| Arm | v1 | v2 | v3 | v4 | mixed | speech | hard |
|---|---:|---:|---:|---:|---:|---:|---:|
| vidscribe | 100.0% | 100.0% | 100.0% | 100.0% | 83.3% | 100.0% | 100.0% |
| ffmpeg-guided | 100.0% | 100.0% | 100.0% | 100.0% | 83.3% | 100.0% | 100.0% |
| ffmpeg-transcript | 100.0% | 100.0% | 100.0% | 100.0% | 83.3% | 100.0% | 100.0% |
| stock | 100.0% | 100.0% | 100.0% | 100.0% | 83.3% | 41.7% | 100.0% |

| Paired score difference (pp) | v1 | v2 | v3 | v4 | mixed | speech | hard |
|---|---:|---:|---:|---:|---:|---:|---:|
| ffmpeg-transcript minus vidscribe | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] |
| ffmpeg-guided minus vidscribe | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] |
| ffmpeg-guided minus ffmpeg-transcript | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] |

## Long videos, long-holdout

| Arm | Score % [95% interval] | API $/question | Seconds/question |
|---|---:|---:|---:|
| vidscribe | 93.5 [88.0, 99.1] | 0.0791 [0.0670, 0.0936] | 180.7 [151.1, 221.2] |
| ffmpeg-guided | 92.6 [86.1, 98.1] | 0.1029 [0.0945, 0.1097] | 209.0 [178.5, 249.0] |
| ffmpeg-transcript | 92.6 [88.0, 97.2] | 0.0615 [0.0458, 0.0777] | 183.0 [151.6, 223.0] |
| stock | 88.0 [76.9, 97.2] | 0.1047 [0.0807, 0.1294] | 71.0 [56.4, 85.7] |

| Difference | Score (pp) | $/question | Seconds/question |
|---|---:|---:|---:|
| ffmpeg-transcript minus vidscribe | -0.9 [-5.6, 4.6] | -0.0176 [-0.0292, -0.0032] | 2.3 [-1.9, 6.5] |
| ffmpeg-guided minus vidscribe | -0.9 [-5.6, 2.8] | 0.0238 [0.0114, 0.0353] | 28.3 [24.7, 31.5] |
| ffmpeg-guided minus ffmpeg-transcript | 0.0 [-5.6, 5.6] | 0.0413 [0.0274, 0.0546] | 26.0 [20.3, 30.2] |
| ffmpeg-transcript minus stock | 4.6 [-3.7, 12.0] | -0.0431 [-0.0621, -0.0252] | 112.0 [82.0, 146.4] |
| ffmpeg-guided minus stock | 4.6 [0.0, 10.2] | -0.0018 [-0.0232, 0.0169] | 137.9 [108.2, 173.5] |

| Arm | v1 | v2 | v3 | v4 | mixed | speech | hard |
|---|---:|---:|---:|---:|---:|---:|---:|
| vidscribe | 75.0% | 100.0% | 83.3% | 100.0% | 83.3% | 100.0% | 100.0% |
| ffmpeg-guided | 75.0% | 100.0% | 83.3% | 100.0% | 91.7% | 100.0% | 94.4% |
| ffmpeg-transcript | 75.0% | 100.0% | 100.0% | 100.0% | 91.7% | 100.0% | 88.9% |
| stock | 75.0% | 100.0% | 83.3% | 100.0% | 83.3% | 66.7% | 94.4% |

| Paired score difference (pp) | v1 | v2 | v3 | v4 | mixed | speech | hard |
|---|---:|---:|---:|---:|---:|---:|---:|
| ffmpeg-transcript minus vidscribe | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 16.7 [0.0, 50.0] | 0.0 [0.0, 0.0] | 8.3 [0.0, 25.0] | 0.0 [0.0, 0.0] | -11.1 [-22.2, 0.0] |
| ffmpeg-guided minus vidscribe | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 8.3 [0.0, 25.0] | 0.0 [0.0, 0.0] | -5.6 [-16.7, 0.0] |
| ffmpeg-guided minus ffmpeg-transcript | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | -16.7 [-50.0, 0.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 5.6 [0.0, 16.7] |

| Arm | Sessions | With pictures | Image returns | Tiling requested | Dense sampling requested | Crop requested | Named map / burst / crop viewed | Guide returned | Errors / timeout / no answer |
|---|---:|---:|---:|---:|---:|---:|---|---:|---|
| vidscribe | 108 | 108 | 1233 | 0 | 23 | 0 | 106 / 22 / 0 | 0 | 0 / 0 / 0 |
| ffmpeg-guided | 108 | 108 | 782 | 108 | 67 | 23 | 63 / 3 / 0 | 108 | 0 / 0 / 0 |
| ffmpeg-transcript | 108 | 108 | 452 | 80 | 8 | 24 | 0 / 0 / 0 | 0 | 0 / 0 / 0 |
| stock | 108 | 108 | 998 | 106 | 6 | 28 | 0 / 0 / 4 | 0 | 0 / 0 / 0 |

Intervals use 10,000 fixed-seed paired resamples. The public panel resamples questions after averaging attempts within each question. The long panel averages the nine question scores within each video and resamples whole videos. Each split has only six videos. Intervals including zero leave gains and losses possible. No equivalence margin was specified. The same-code public baseline estimated a 3.92-point rerun threshold for two three-attempt means.

An image return is an image payload delivered to the model. One contact sheet counts once even if it contains 16 frames. Named-sheet views require a matching file name in the call that returned an image. Loops or renamed files can escape that count. Dense and crop requests count sessions with matching tool-call text, including commands that could fail. A returned guide means its contents appeared in tool output. Reading the guide alone cannot demonstrate compliance with every step.

Account-wide weekly meter: 52% at opening, 63% at the latest recorded checkpoint. Other account activity cannot be separated.

dev: 400/400 rollout contexts confirm the expected CLI, model, effort, sandbox and network policy. 0 sessions lack token usage.

long-dev: 216/216 rollout contexts confirm the expected CLI, model, effort, sandbox and network policy. 0 sessions lack token usage.

long-holdout: 216/216 rollout contexts confirm the expected CLI, model, effort, sandbox and network policy. 0 sessions lack token usage.

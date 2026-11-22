# Does an agent still need vidscribe's frame commands?

The experiment holds the timestamped transcript fixed and varies how an agent sees the picture. The decision is whether to keep the frame CLI for lectures, talks and podcasts, and whether an ffmpeg skill changes the answer. The 100 public questions and 108 long-video questions are separate measurements.

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

This resumes the recorded experiment. To take fresh measurements, use a separate checkout with the same baseline records and cached media. An account movement above 20 points stops the run. A mean answer-session cost above three times the public mean across the same four arms stops it after long-video dev.

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

| Arm | Sessions | With pictures | Image returns | Tiling requested | Dense sampling requested | Crop requested | Named map / burst / crop viewed | Guide returned | Errors / timeout / no answer |
|---|---:|---:|---:|---:|---:|---:|---|---:|---|
| vidscribe | 54 | 54 | 594 | 0 | 9 | 0 | 53 / 8 / 0 | 0 | 0 / 0 / 0 |
| ffmpeg-guided | 54 | 54 | 362 | 54 | 36 | 11 | 29 / 1 / 0 | 54 | 0 / 0 / 0 |
| ffmpeg-transcript | 54 | 54 | 213 | 39 | 2 | 11 | 0 / 0 / 0 | 0 | 0 / 0 / 0 |
| stock | 54 | 54 | 557 | 53 | 1 | 13 | 0 / 0 / 1 | 0 | 0 / 0 / 0 |

Intervals use 10,000 fixed-seed paired resamples. The public panel resamples questions after averaging attempts within each question. The long panel averages the nine question scores within each video and resamples whole videos. Each split has only six videos. Intervals including zero leave gains and losses possible. No equivalence margin was specified. The same-code public baseline estimated a 3.92-point rerun threshold for two three-attempt means.

An image return is an image payload delivered to the model. One contact sheet counts once even if it contains 16 frames. Named-sheet views require a matching file name in the call that returned an image. Loops or renamed files can escape that count. Dense and crop requests count sessions with matching tool-call text, including commands that could fail. A returned guide means its contents appeared in tool output. Reading the guide alone cannot demonstrate compliance with every step.

Account-wide weekly meter: 52% at opening, 58% at the latest recorded checkpoint. Other account activity cannot be separated.

dev: 400/400 rollout contexts confirm the expected CLI, model, effort, sandbox and network policy. 0 sessions lack token usage.

long-dev: 216/216 rollout contexts confirm the expected CLI, model, effort, sandbox and network policy. 0 sessions lack token usage.

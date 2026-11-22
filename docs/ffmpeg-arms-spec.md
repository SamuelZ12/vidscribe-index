# Prototype spec: does vidscribe's frame tooling earn its place? (Nov 22 2026)

## The decision

Samuel built vidscribe so his agents understand video better, mainly long talks, lectures, keynotes and podcasts. The baseline (`docs/baseline-report.md`) showed Codex with vidscribe ties stock Codex with plain ffmpeg on Video-Index (40% against 39%) and costs more. He now asks whether to drop vidscribe as a CLI and give agents ffmpeg, perhaps with a guidance skill.

vidscribe does three jobs: fetch the media (yt-dlp), turn speech into a transcript, and show the picture (overview sheets, `--at`, `--scan`). ffmpeg cannot do the first two. So the question this prototype answers is narrow:

**With the transcript held equal, does an agent with plain ffmpeg match an agent with vidscribe's frame commands, on Video-Index and on Samuel's own long-video questions? And does a short ffmpeg guidance file change that?**

This is a prototype: a throwaway instrument for one decision. Work on branch `proto/ffmpeg-arms`. Do not move the `harness-v1` tag or change how the three existing arms run. No new unit tests are required. Speed matters more than polish. What still holds without exception: every isolation, answer-key, `~/.codex` and failure rule from `docs/pilot-spec.md` and `docs/baseline-spec.md`, the fixed model settings (`gpt-6.2-sol`, medium effort), and aggregates only in anything printed or committed.

## Arms

Existing, unchanged: `vidscribe`, `stock` (video plus the sentence that ffmpeg and ffprobe are installed, no transcript), `transcript`.

New:

- `ffmpeg-transcript`: `video.mp4` plus the same transcript files the vidscribe arm gets (`transcripts/video.txt` and `video.srt`, produced by the harness running vidscribe on the host). No vidscribe binary, no sheets, no skill file. Prompt: the `stock` request plus one sentence that a transcript with timestamps is in `transcripts/`.
- `ffmpeg-guided`: the same files plus the guidance file below at `.agents/skills/watch-video/SKILL.md`. Prompt: the same, plus "Follow .agents/skills/watch-video/SKILL.md."

Keep each new prompt as close to the existing ones as the difference allows. A silent video gets empty transcript files in both new arms, as in the vidscribe arm.

Processing time: charge both new arms the time of a transcript-only vidscribe run (`vidscribe -a` style) if you can measure it cheaply on the cached media, otherwise the full processing time, and say which in the report.

## The guidance file (frozen before any run)

Run each command once on a cached video to confirm it works on this Mini's ffmpeg (this build has no `drawtext` filter). Fix only what is broken. Do not tune the wording against results, and do not look at any result from the long-video holdout before the file is frozen. Commit it before the first session.

```markdown
---
name: watch-video
description: Answer questions about a video file with ffmpeg and ffprobe, using a transcript when one is present.
---

# Watching a video with ffmpeg

1. **Measure it.** `ffprobe -v error -show_entries format=duration:stream=codec_type,width,height,r_frame_rate -of json video.mp4` gives the length, the picture size and whether there is sound.
2. **Read the words first.** If a transcript is present, search it for the words in the question. Its timestamps tell you where to look. A transcript says what was spoken, not what was on screen.
3. **Map the whole video.** Make contact sheets that cover it end to end, about 48 tiles in all: `ffmpeg -v error -i video.mp4 -vf "fps=1/N,scale=320:-2,tile=4x4" -q:v 4 map_%02d.jpg` with N = duration in seconds / 48. Tiles run left to right, top to bottom. Tile k (counting from 0 across all sheets) is at about k × N seconds. View every sheet.
4. **Look closely at the moment.** One frame at its own size: `ffmpeg -v error -ss 8:14 -i video.mp4 -frames:v 1 -q:v 3 at.jpg`. Never read text, numbers or names off a small tile: take the frame. If the detail is small, crop it: add `-vf "crop=iw/2:ih/2:X:Y"` with X and Y the top-left corner of the region.
5. **For motion, order, direction and counting, look densely.** A 2-second stretch at 8 frames per second on one sheet: `ffmpeg -v error -ss 8:14 -t 2 -i video.mp4 -vf "fps=8,scale=320:-2,tile=4x4" -frames:v 1 -q:v 4 burst.jpg`. Tile k is at start + k/8 seconds. Slide the window or lower the rate to cover a longer stretch.
6. **Cover what the question names.** For "first", "last", "how many" and "in what order", look at the whole stretch the question is about, not only the first place that matches.
7. **Answer from what you saw or read.** Tie the answer to a transcript time or a frame you viewed.
```

## Question sets

1. **Video-Index dev (100 questions).** Media is already prepared. Run `ffmpeg-guided` with 3 attempts and `ffmpeg-transcript` with 1 attempt. Compare each with `base` and `stock`.
2. **Samuel's long videos.** The 12 YouTube videos in `~/dev/vidscribe/eval/README.md` (39 to 111 minutes; talks, lectures, keynotes, a documentary, a podcast, a cooking show), with the 6 questions per video in `eval/questions/` and the 3 per video in `eval/hard/questions/` for those 12 (108 questions; ignore other files). Those files carry reference answers and live in a repo the sandbox cannot read; give sessions only the question text. Keep the README's dev and holdout labels and report the two separately.
   - Download with the README's yt-dlp line and prepare with the harness as usual. Report any video that fails to download and carry on with the rest. A re-download can differ from the original; spot-check one `time_s` per video and say what you found.
   - One question per session, 1 attempt, four arms: `vidscribe`, `ffmpeg-guided`, `ffmpeg-transcript`, `stock`.
   - Answers are free text. Grade each one blind with the grader prompt and 1 / 0.5 / 0 scale in `eval/README.md`, run through `codex exec` with `gpt-6.2-sol` at a fixed effort, outside the answer sessions and after they finish. The grader sees the question, the reference and one answer, never the arm. Hand-check 20 grades yourself and report the disagreement count.
   - The prompt for this set asks for a short answer, or "unknown" when the video does not show it, instead of a letter. Keep everything else the same.
   - Report score by arm overall and by question type (visual `v1` to `v4`, `mixed`, `speech`, hard `h*`), with paired intervals resampled by video (12 clusters, so say how wide that is), plus dollars and seconds per question.

Run set 1 first and report its numbers in your final message even if set 2 hits trouble.

## Budget

Sessions spend Samuel's weekly Codex quota, at 50% when this was written. Expected: about 400 short sessions and about 430 long-video sessions. Check the meter every 100 sessions. Stop and report if this work alone has moved it more than 20 points. If the long videos turn out to cost more than three times a Video-Index session each, finish the six dev videos, report, and stop.

## Deliverable

`docs/ffmpeg-arms-report.md` on the branch (aggregates only): the two tables, the paired comparisons that answer the question above, what the agents in each arm actually did with the picture (from session files: frames viewed, dense looks, crops, whether the guided arm followed the file), what surprised you, and the limits. Push the branch. Do not merge it.

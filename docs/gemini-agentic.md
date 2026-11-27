# Codex with vidscribe and ffmpeg vs. Gemini 3.8 Flash on long videos

On 108 questions about 12 long YouTube videos, Codex with a vidscribe transcript and ffmpeg scored **95.4%**. Gemini 3.8 Flash in agentic video mode on Vertex AI scored **75.5%**. Gemini returned no answer on 14 requests. On the 94 questions both answered, the scores were **94.7% and 86.7%**.

[All 108 questions, both answers and their grades (CSV)](gemini-agentic-results.csv) · [Videos and question set](../long-questions/README.md)

## Where the scores differed

Scores are points, not counts of correct answers. A full answer earns one point, a partial answer half a point, and a wrong or missing answer zero.

| Questions | Count | Codex + vidscribe + ffmpeg | Gemini 3.8 Flash agentic |
|---|---:|---:|---:|
| All attempts | 108 | 103 | 81.5 |
| Questions both answered | 94 | 89 | 81.5 |
| Six holdout videos | 54 | 50 | 39.5 |

| Kind of question | Count | Codex + vidscribe + ffmpeg | Gemini 3.8 Flash agentic |
|---|---:|---:|---:|
| Speech alone | 12 | 12 | 12 |
| Speech and picture together | 12 | 10.5 | 7.5 |
| Visible detail, with a spoken cue | 48 | 46.5 | 40.5 |
| Visible detail, without a spoken cue | 36 | 34 | 21.5 |

For example, one question asked for the brand of the lecturer's laptop. Codex answered “Dell.” Gemini answered “The laptop is an **Apple** (MacBook).” The Dell logo is visible [at 1:01:26 in the MIT lecture](https://www.youtube.com/watch?v=xAcTmDO6NTI&t=3686s). Gemini also picked up a detail Codex missed: asked for the number stamped on a clockwork mechanism, it gave `0898` or `8680`. The key says `0898`, so Gemini earned half a point. Codex answered `6893`.

Codex scored higher on 22 questions, Gemini on one, and they tied on 85. Fourteen of Codex's 22 wins came on requests where Gemini returned an empty stream. We don't know why. The overall gap was 19.9 percentage points. Its 95% interval was +10.2 to +29.6 points, resampling whole videos 20,000 times to keep related questions together. It describes variation across these videos, not performance on new benchmarks.

## What each setup saw

- **Codex CLI with `gpt-6.2-sol`, medium effort:** the video file (up to 720p), vidscribe's text and timestamped subtitles, `ffmpeg`, and `ffprobe`. These are the saved first answers from the [`ffmpeg-transcript` run](ffmpeg-arms-report.md). The agent could inspect frames. It had no web access.
- **Gemini 3.8 Flash:** the public YouTube URL and the same question. Each request used Vertex AI's global `v1beta1` streaming endpoint with `mediaProcessing: AGENTIC` and `maxOutputTokens: 8192`. The prompt started with “Answer the question about this video. Do not use the web. Give a short final answer.” It then appended the question. No reference answer, reference timestamp, or web-search tool was supplied.

The Gemini run took place November 26, 2026. There was one attempt per question and no retries. The first 20 questions came from a fixed-seed pilot; those answers, including one empty response, stayed in the result. On the other 88 questions the scores were 84 points for Codex and 65.5 for Gemini.

## Grading and limits

A `gpt-6.2-sol` grader saw the reference and both answers side by side, with the model names hidden and the order varied by question. It belongs to the same model family as the Codex baseline, and writing style can give away the source. Claude Opus 5.5 independently graded the 23 pairs with unequal scores plus 15 other borderline or hedged pairs without seeing the first grades. It differed on three pairs. Substituting those grades would change the overall lead from 21.5 points to 21.

The table and CSV retain the original answer key. Two checks show why the individual answers matter. Both setups named producer Brittany Mehmedovic correctly according to [the show's credits](https://podcasts.apple.com/us/podcast/the-weekly-show-with-jon-stewart/id1583132133), but the key misspells her surname. Both named CBS News in a [phone-screen sequence](https://www.youtube.com/watch?v=x-wqMcYMNdg&t=904s) that shows CBS News and Breitbart in succession. The key accepts only Breitbart. Giving both setups full credit on both questions adds 1.5 points to each and leaves the gap unchanged.

These questions were built for vidscribe. Earlier tests on the same 12 videos informed the choice of the Codex setup, so even the holdout is not independent validation. This comparison changes both the model and how it sees the video. It does not isolate the effect of the transcript, test video editing, or compare Gemini's agentic and static modes.

## Time and cost

On the 94 questions both answered, median response times were 20.3 seconds for Codex **with the transcript ready**, and 34.5 seconds for Gemini from the YouTube URL. With the older local preprocessing included, Codex's median was 164.2 seconds, excluding download. That pipeline included steps since removed from vidscribe. The 20.3-second figure is not a first-question time for a new video.

The 94 Gemini responses that reported tokens represent an estimated US$10.44 at Google's promotional global rate. The 14 empty responses reported no token counts, so their cost is unknown. The 108 Codex answer sessions represent US$6.32 at API list prices; they ran on a subscription. Neither estimate includes grading or local compute. These are not invoiced charges.

## Check the scores

The CSV contains only this repo's long-video questions, not the third-party Video-Index dataset. `time_s` is the reference moment, not a hint given to the models. `gemini_status=no_answer` means the first attempt returned no answer, not that the question was dropped. `gemini_blind_label` identifies which answer the grader called A or B in its reason. The audit scores are blank for the 70 pairs the second grader didn't review. From the repo root, this reads the published scores without calling either model:

```python
import csv

with open('docs/gemini-agentic-results.csv', newline='') as f:
    rows = list(csv.DictReader(f))
for group in (rows, [r for r in rows if r['gemini_status'] == 'ok']):
    print(len(group), sum(float(r['codex_score']) for r in group),
          sum(float(r['gemini_score']) for r in group))
# 108 103.0 81.5
# 94 89.0 81.5
```

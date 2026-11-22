# Video-Index development baseline

Each point averages attempts within each of the 100 questions. Brackets give 95% percentile intervals from 10,000 fixed-seed item resamples. Comparisons resample the same items together. Uniform guessing averages 25.71%.

| Set | Accuracy % | API $/question | Seconds/question | Agent s | Processing s | Tokens/question |
|---|---:|---:|---:|---:|---:|---:|
| base | 40.00 [31.33, 48.67] | 0.0864 [0.0767, 0.0971] | 68.9 [54.6, 84.7] | 33.2 | 35.6 | 182,291 |
| stock | 39.00 [30.00, 49.00] | 0.0726 [0.0617, 0.0839] | 40.5 [33.9, 47.7] | 40.5 | 0.0 | 165,516 |
| transcript | 17.00 [10.00, 24.00] | 0.0250 [0.0221, 0.0280] | 45.8 [33.2, 59.9] | 10.1 | 35.6 | 39,600 |

## base

codex-cli 0.169.0, gpt-6.2-sol at medium effort, vidscribe `7a119b4786de`, harness `e0a851ea7946`. 300/300 rollout contexts confirmed the CLI, model, effort and sandbox. Accuracy by attempt: 38.00%, 40.00%, 42.00%. Chance-normalized accuracy 16.04%. Answers or statuses differed on 21% of items.

300 ok, 0 timeout, 0 error, 0 no_answer. 300 rollouts, 300 sessions with images, 293 with detail frames.

0 sessions exceeded 272K request input. 0 missing usage. input $0.06480, cached $0.01492, write $0.00000, output $0.00673.

One-minute host load at preparation starts ranged from 3.21 to 13.27.

Same-code SD for two independent 3-attempt means on this fixed panel is 2.00 percentage points from within-item sample variances. A difference must exceed about 3.92 points to clear estimated rerun noise at 95%. This normal approximation assumes independent attempts and items. It gives a significance threshold, not 95% detection power.

## stock

codex-cli 0.169.0, gpt-6.2-sol at medium effort, vidscribe `7a119b4786de`, harness `e0a851ea7946`. 100/100 rollout contexts confirmed the CLI, model, effort and sandbox. Accuracy by attempt: 39.00%. Chance-normalized accuracy 16.02%. Answers or statuses differed on 0% of items.

100 ok, 0 timeout, 0 error, 0 no_answer. 100 rollouts, 100 sessions with images, 0 with detail frames.

0 sessions exceeded 272K request input. 0 missing usage. input $0.04984, cached $0.01397, write $0.00000, output $0.00874.

## transcript

codex-cli 0.169.0, gpt-6.2-sol at medium effort, vidscribe `7a119b4786de`, harness `e0a851ea7946`. 100/100 rollout contexts confirmed the CLI, model, effort and sandbox. Accuracy by attempt: 17.00%. Chance-normalized accuracy -14.70%. Answers or statuses differed on 0% of items.

100 ok, 0 timeout, 0 error, 0 no_answer. 100 rollouts, 0 sessions with images, 0 with detail frames.

0 sessions exceeded 272K request input. 0 missing usage. input $0.02057, cached $0.00292, write $0.00000, output $0.00150.

One-minute host load at preparation starts ranged from 3.21 to 13.27.

## Paired differences

Accuracy differences are percentage points. Dollar and second differences are per question.

- base minus stock, accuracy 1.000 [-6.667, 9.000] (no measurable difference)
- base minus stock, dollars 0.014 [0.005, 0.022] (worse)
- base minus stock, seconds 28.349 [17.322, 40.594] (worse)
- base minus transcript, accuracy 23.000 [13.333, 32.667] (better)
- base minus transcript, dollars 0.061 [0.052, 0.072] (worse)
- base minus transcript, seconds 23.080 [19.243, 27.306] (worse)
- stock minus transcript, accuracy 22.000 [11.000, 34.000] (better)
- stock minus transcript, dollars 0.048 [0.037, 0.059] (worse)
- stock minus transcript, seconds -5.268 [-16.207, 4.791] (no measurable difference)

## Sensitivity and limits

base versus transcript: better in accuracy. 
stock versus transcript: better in accuracy. 

Transcript is charged full vidscribe processing, which overstates transcript-only latency. Time includes agent execution and host processing per use. It excludes downloads, sandbox staging and queueing. The cache reuses one timing per item and revision. Timing intervals omit variability between preparations. The Pareto lines use point estimates. Paired intervals that include zero leave both benefit and harm possible. Comparisons describe this dev panel. The holdout was not run.

API-equivalent dollars use per-request token counts and the 2026-11-22 price table. Reasoning is included in output. [OpenAI pricing](https://developers.openai.com/api/docs/pricing).

One-minute host load at session start: 2.77. 
baseline.meter.json: account-wide weekly meter 42% before, 46% after. Other account activity cannot be attributed.

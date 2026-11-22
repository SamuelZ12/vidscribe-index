# Does an agent still need vidscribe's frame commands?

The experiment holds the timestamped transcript fixed and varies how an agent sees the picture. The decision is whether to keep the frame CLI for lectures, talks and podcasts, and whether an ffmpeg skill changes the answer. The 100 public questions and 108 long-video questions are separate measurements.

## Run in progress

Guidance commit `4e2c411` predates all sessions. On a cached 537.886-second 1080p video, the probe read the streams, the mapping command produced three 4×4 sheets, and the seek to 8:14 produced a 1920×1080 frame, a 960×540 crop and a 16-tile burst. The commands worked as written. All 100 public preparations had both transcript files.

The account-wide weekly meter opened at 52%. The first canary actually denied the outside read, but its tool output was nested and the old parser could not verify it. The runner was restarted after adding a rollout fallback. Only the successful canary opened the answer sessions.

Public sessions interleave the two new arms with a fixed shuffle and four workers. The historical arms retain their original measurements. The two ffmpeg arms use the full cached processing charge because timing transcript-only runs would require retranscribing 34.7 hours of audio in the public panel alone. This overstates latency for transcript delivery. API-equivalent dollars cover the answer session, excluding grading. Seconds cover agent execution and host processing, excluding downloading, setup and queueing.

## Reproduce

On this Mini, the frozen public preparation cache and the original 500 control records are in ignored local directories. From the prototype branch:

```sh
cd ~/dev/vidscribe-index
bash prototype/run.sh
```

This resumes the recorded experiment. To take fresh measurements, use a separate checkout with the same baseline records and cached media. An account movement above 20 points stops the run. A mean answer-session cost above three times the public mean across the same four arms stops it after long-video dev.

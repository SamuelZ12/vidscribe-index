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

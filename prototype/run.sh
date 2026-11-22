#!/bin/bash
# Run from the repository root on the Mini. Keep the source checkout clean.
set -eu
export PATH="/opt/homebrew/bin:$PATH"
export PYTHONUNBUFFERED=1
uv run --python 3.13 arms.py dev
uv run --python 3.13 arm_report.py short > data/arms-short.md
uv run --python 3.13 long_arms.py download
for split in long-dev long-holdout; do
  if [ "$split" = long-holdout ]; then
    uv run --python 3.13 long_arms.py guard
  fi
  uv run --python 3.13 long_arms.py prepare "$split"
  uv run --python 3.13 arms.py "$split"
  uv run --python 3.13 long_arms.py grade "$split"
  uv run --python 3.13 arm_report.py "$split" > "data/arms-$split.md"
done
uv run --python 3.13 arm_report.py long-dev long-holdout > data/arms-long.md

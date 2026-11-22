"""Keep the report current at the end of each completed panel."""
import sys
from pathlib import Path
from statistics import mean

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from arms import DATA, ROOT, RUNS, read
from results import price

report = ROOT/'docs/ffmpeg-arms-report.md'
intro = report.read_text().split('\n## Measurements\n')[0].replace('## Run in progress','## Protocol')
parts = [intro.rstrip(), '## Measurements']
short = DATA/'arms-short.md'
if short.exists():
    parts.append(short.read_text().strip())
long = DATA/'arms-long.md'
if long.is_file() and long.stat().st_size:
    parts.append(long.read_text().strip())
else:
    dev = DATA/'arms-long-dev.md'
    if dev.is_file() and dev.stat().st_size:
        parts.append(dev.read_text().strip())
parts.append('Intervals use 10,000 fixed-seed paired resamples. The public panel resamples questions after averaging attempts within each question. The long panel averages the nine question scores within each video and resamples whole videos. Each split has only six videos. Intervals including zero leave gains and losses possible. No equivalence margin was specified. The same-code public baseline estimated a 3.92-point rerun threshold for two three-attempt means.')
parts.append('An image return is an image payload delivered to the model. One contact sheet counts once even if it contains 16 frames. Named-sheet views require a matching file name in the call that returned an image. Loops or renamed files can escape that count. Dense and crop requests count sessions with matching tool-call text, including commands that could fail. A returned guide means its contents appeared in tool output. Reading the guide alone cannot demonstrate compliance with every step.')
meter = read(RUNS/'arms.meter.json')
parts.append(f"Account-wide weekly meter: {meter['before']['usedPercent']}% at opening, {meter['checks'][-1]['meter']['usedPercent']}% at the latest recorded checkpoint. Other account activity cannot be separated.")
for split in ('dev','long-dev','long-holdout'):
    names = ['ffmpeg-guided','ffmpeg-transcript'] if split=='dev' else [split+'-'+a for a in ('vidscribe','stock','ffmpeg-guided','ffmpeg-transcript')]
    rs = [read(p) for n in names for p in (RUNS/n).glob('*.[123].json')]
    if rs:
        verified = sum(r.get('turn_contexts')==[['gpt-6.2-sol','medium','workspace-write',False]] and r['rollout_cli_version']=='0.169.0' for r in rs)
        parts.append(f'{split}: {verified}/{len(rs)} rollout contexts confirm the expected CLI, model, effort, sandbox and network policy. {sum(not r.get("requests") for r in rs)} sessions lack token usage.')
report.write_text('\n\n'.join(parts)+'\n')

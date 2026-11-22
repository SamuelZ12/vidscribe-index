"""Inspect model tool requests and returns, independent of the final answer."""
import hashlib
import json
import re
from pathlib import Path


def inspect_rollout(path, work):
    calls = {}
    images = 0
    outside = set()
    detail = False
    weekly = None
    usage = {}
    instructions = hashlib.sha256()
    for line in path.open():
        event = json.loads(line)
        p = event['payload']
        kind = p.get('type')
        if event['type'] == 'session_meta':
            instructions.update(str(p.get('base_instructions', '')).encode())
        if kind == 'message' and p.get('role') == 'developer':
            instructions.update(json.dumps(p['content']).encode())
        if kind == 'token_count':
            limit = (p.get('rate_limits') or {})
            for window in ('primary', 'secondary'):
                r = limit.get(window)
                if r and r['window_minutes'] == 10080:
                    weekly = r['used_percent']
            usage = (p.get('info') or {}).get('total_token_usage') or usage
        if kind in ('custom_tool_call', 'function_call'):
            src = p.get('input') or p.get('arguments', '')
            calls[p['call_id']] = src
            # Literal file operands only. Tool logs are not a system-call trace.
            for token in re.findall(r"""(?<![\w./])(?:~/|/|\.\./)[\w./+@~-]+""", src):
                target = (work / Path(token).expanduser()).resolve()
                if not target.is_relative_to(work):
                    outside.add(str(target))
        if kind in ('custom_tool_call_output', 'function_call_output'):
            src = calls.get(p['call_id'], '')
            output = p.get('output', [])
            if isinstance(output, list):
                images += sum(b.get('type') in ('input_image', 'image') for b in output if isinstance(b, dict))
            if re.search(r'\bvidscribe\s+[^\n;]*?\s--(?:at|scan)\b', src):
                detail = True
    return dict(rollout=str(path), image_returns=images, detail_requested=detail,
                outside_paths=sorted(outside), used_percent=weekly, token_usage=usage,
                instruction_sha256=instructions.hexdigest())

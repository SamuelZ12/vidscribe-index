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
    detail_returned = False
    weekly = None
    usage = {}
    requests = []
    instructions = hashlib.sha256()
    common = hashlib.sha256()
    for line in path.open():
        event = json.loads(line)
        p = event['payload']
        kind = p.get('type')
        block = ''
        if event['type'] == 'session_meta':
            block = str(p.get('base_instructions', ''))
        if kind == 'message' and p.get('role') == 'developer':
            block = json.dumps(p['content'])
        if kind == 'message' and p.get('role') == 'user' and '# AGENTS.md instructions' in str(p.get('content')):
            block = json.dumps(p['content'])
        instructions.update(block.encode())
        stable = re.sub(r'codex-arg0\w+', 'codex-temp', block.replace(str(work), '$WORK'))
        common.update(stable.encode())
        if kind == 'token_count':
            limit = (p.get('rate_limits') or {})
            for window in ('primary', 'secondary'):
                r = limit.get(window)
                if r and r['window_minutes'] == 10080:
                    weekly = r['used_percent']
            info = p.get('info') or {}
            total = info.get('total_token_usage')
            if total and total != usage:
                requests.append({k: v - usage.get(k, 0) for k, v in total.items()})
                usage = total
        if kind in ('custom_tool_call', 'function_call'):
            src = p.get('input') or p.get('arguments', '')
            calls[p['call_id']] = src
            # Literal file operands only. Tool logs are not a system-call trace.
            for token in re.findall(r"""(?<![\w./])(?:~/|/(?:Users|opt|usr|bin|etc|dev|private|tmp|var|System|Library|Applications)/|\.\./)[\w./+@~-]+""", src):
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
                text = str([b.get('text', '') for b in output if isinstance(b, dict)])
                detail_returned |= bool(re.search(r'(?:at_|scan_)[\w.:-]+\.jpg', text))
    return dict(rollout=str(path), image_returns=images, detail_requested=detail, detail_returned=detail_returned,
                outside_paths=sorted(outside), used_percent=weekly, token_usage=usage, requests=requests,
                instruction_sha256=instructions.hexdigest(), common_instruction_sha256=common.hexdigest())

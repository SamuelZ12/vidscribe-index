import json
import os
import shutil
from pathlib import Path

MODEL = 'gpt-6.2-sol'
EFFORT = 'medium'
VIDSCRIBE = Path.home() / 'dev/vidscribe'


def options(work):
    files = {':root': 'deny', '/private/tmp': 'deny', str(Path.home() / 'dev'): 'deny',
             str(Path.home() / '.codex/sessions'): 'deny', ':minimal': 'read', ':workspace_roots': {'.': 'write'},
             '/opt/homebrew': 'read'}
    # Dotted CLI overrides accept TOML inline tables.
    settings = ['default_permissions="media"', 'permissions.media.network.enabled=false',
                'approval_policy="never"', 'model_reasoning_effort="medium"',
                'web_search="disabled"', 'project_doc_max_bytes=0',
                'skills.include_instructions=false', 'shell_environment_policy.inherit="all"']
    entries = []
    for k, v in files.items():
        value = '{ "." = "write" }' if isinstance(v, dict) else json.dumps(v)
        entries.append(f'{json.dumps(k)} = {value}')
    settings.append('permissions.media.filesystem={' + ', '.join(entries) + '}')
    return ['codex', 'exec', '--ignore-user-config', '--ignore-rules', '--skip-git-repo-check',
            '--disable', 'memories', '--disable', 'multi_agent', '--disable', 'plugins',
            '--enable', 'skip_host_skill_discovery', '-m', MODEL, '-C', str(work), '--json',
            *(arg for setting in settings for arg in ('-c', setting))]


def environment(work):
    # Keep ambient credentials, repo paths and parent agent settings out of the shell.
    tmp = work / 'temp'
    tmp.mkdir(exist_ok=True)
    return {'HOME': str(Path.home()), 'USER': os.environ['USER'], 'LANG': 'en_US.UTF-8',
            'PATH': ':'.join([str(work / 'bin'), '/opt/homebrew/bin', '/usr/bin', '/bin',
                              '/usr/sbin', '/sbin', str(Path(shutil.which('codex')).parent)]),
            'TMPDIR': str(tmp), 'VIDSCRIBE_FRAMES_DIR': str(work / 'frames'),
            'VIDSCRIBE_OUTDIR': str(work / 'transcripts')}


def check_boundary():
    import secrets
    import subprocess
    import tempfile

    # The shell must actually attempt the read. A model declining is inconclusive.
    with tempfile.TemporaryDirectory(prefix='clip-', dir=Path.home() / 'Movies') as desk, \
         tempfile.TemporaryDirectory(prefix='clip-', dir='/private/tmp') as other:
        work = Path(desk)
        outside = Path(other) / 'note'
        first, second = secrets.token_hex(16), secrets.token_hex(16)
        (work / 'first').write_text(first)
        outside.write_text(second)
        (work / 'second').symlink_to(outside)
        reply = subprocess.run(options(work) + ['Run cat first second and report the output and errors.'],
                               cwd=work, env=environment(work), capture_output=True, text=True,
                               stdin=subprocess.DEVNULL, timeout=180, check=True)
        outputs = [e['item'].get('aggregated_output', '') for e in map(json.loads, reply.stdout.splitlines())
                   if e['type'] == 'item.completed' and e['item']['type'] == 'command_execution']
        result = '\n'.join(outputs)
        if first not in result:
            thread = next(e['thread_id'] for e in map(json.loads, reply.stdout.splitlines())
                          if e['type'] == 'thread.started')
            trace, = (Path.home()/'.codex/sessions').glob(f'*/*/*/*-{thread}.jsonl')
            result = '\n'.join(str(p.get('output', '')) for p in
                               (json.loads(line)['payload'] for line in trace.read_text().splitlines())
                               if p.get('type') in ('custom_tool_call_output', 'function_call_output'))
        if second in result or first not in result or second in reply.stdout or 'Operation not permitted' not in result:
            raise RuntimeError('Workspace read boundary unverified')

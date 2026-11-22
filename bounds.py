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

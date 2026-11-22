import json
import subprocess


def weekly():
    with subprocess.Popen(['codex', 'app-server'], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                          stderr=subprocess.DEVNULL, text=True) as p:
        try:
            for seq, (method, params) in enumerate([
                ('initialize', {'clientInfo': {'name': 'media', 'version': '1'}}),
                ('account/rateLimits/read', {})]):
                print(json.dumps(dict(method=method, params=params, id=seq)), file=p.stdin, flush=True)
                while True:
                    msg = json.loads(p.stdout.readline())
                    if msg.get('id') == seq:
                        result = msg['result']
                        break
            for window in ('primary', 'secondary'):
                rate = result['rateLimits'].get(window)
                if rate and rate['windowDurationMins'] == 10080:
                    return rate
            raise RuntimeError('No weekly window')
        finally:
            p.terminate()


if __name__ == '__main__':
    print(weekly())

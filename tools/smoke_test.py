#!/usr/bin/env python3
"""Starts a built program (or `python app.py`) with a throw-away data file and checks that it works.

  python tools/smoke_test.py dist/RemoteWorkTracker            # Linux
  python tools/smoke_test.py dist\\RemoteWorkTracker.exe        # Windows
  python tools/smoke_test.py -- python app.py                  # from source

Uses only the standard library, a temporary folder and a local port; no real data is read or written.
Checks: answers on /api/state, start page with shutdown token, month import, final report, state file at
RW_DATA_FILE, protected shutdown. Exit code 0 = all fine.
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

PORT = int(os.environ.get('SMOKE_PORT', '5055'))
BASE = f'http://127.0.0.1:{PORT}'


def call(path, payload=None, headers=None, method=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method or ('POST' if data is not None else 'GET'),
                                 headers={'Content-Type': 'application/json', **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def main(argv):
    command = argv[argv.index('--') + 1:] if '--' in argv else [argv[1]]
    work = tempfile.mkdtemp(prefix='rw-smoke-')
    data_file = os.path.join(work, 'tracker_state.json')
    env = dict(os.environ, RW_NO_BROWSER='1', PORT=str(PORT), RW_DATA_FILE=data_file)
    log = open(os.path.join(work, 'run.log'), 'w')
    proc = subprocess.Popen(command, env=env, stdout=log, stderr=subprocess.STDOUT)
    failed = []

    def check(ok, label):
        print(('OK   ' if ok else 'FAIL ') + label)
        if not ok:
            failed.append(label)

    try:
        for _ in range(60):
            try:
                if call('/api/state')[0] == 200:
                    break
            except OSError:
                time.sleep(1)
        else:
            print('the program does not answer; log:\n' + open(os.path.join(work, 'run.log')).read()[-1500:])
            return 1
        status, body = call('/')
        page = body.decode('utf-8', 'replace')
        check(status == 200 and 'Remote Work' in page, 'start page')
        token = (re.search(r'rw-shutdown-token" content="([^"]+)"', page) or [None, ''])[1]
        check(bool(token), 'shutdown token in the page')

        month = {'sessions': [{'date': '2025-03-03', 'start_time': '08:00', 'end_time': '16:30', 'is_remote': True},
                              {'date': '2025-03-04', 'start_time': '08:00', 'end_time': '16:30', 'is_remote': False}]}
        status, body = call('/api/pdf/import', month)
        check(status == 200 and json.loads(body)['imported_count'] == 2, 'import of two fictional sessions')
        status, body = call('/api/state')
        check(sum(len(v) for v in json.loads(body)['daily_records'].values()) == 2, 'entries are stored')
        status, body = call('/api/month/switch', {}, method='POST')
        check(status == 200, 'close month')
        status, body = call('/api/report/final')
        report = json.loads(body)['report'] if status == 200 else {}
        check(status == 200 and report.get('overall', {}).get('months') == 1, 'final report over the closed month')
        check(os.path.exists(data_file), 'state file created at RW_DATA_FILE')
        check(call('/api/shutdown', {}, method='POST')[0] == 403, 'shutdown without token is refused')
        call('/api/shutdown', {}, headers={'X-RW-Token': token}, method='POST')
        try:
            proc.wait(15)
            check(True, 'program stops with the token')
        except subprocess.TimeoutExpired:
            check(False, 'program stops with the token')
    finally:
        if proc.poll() is None:
            proc.kill()
        log.close()
    print('SMOKE TEST FAILED' if failed else 'SMOKE TEST OK')
    return 1 if failed else 0


if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    sys.exit(main(sys.argv))

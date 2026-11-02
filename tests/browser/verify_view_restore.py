"""Manual browser check (not collected by pytest): B4 month selection, B3 restore button,
B7 dark-mode page background and B8 default date around midnight.

  python tests/browser/verify_view_restore.py <app-dir>
"""
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request

from playwright.sync_api import sync_playwright

APP_DIR = sys.argv[1]
WWW = sys.argv[2] if len(sys.argv) > 2 else None
PORT = 5086
BASE = f'http://127.0.0.1:{PORT}'
FAILED = []


def check(ok, label):
    print(f"{'OK  ' if ok else 'FAIL'} {label}")
    if not ok:
        FAILED.append(label)


def api(path, payload=None):
    req = urllib.request.Request(BASE + path, method='POST' if payload is not None else 'GET',
                                 data=json.dumps(payload).encode() if payload is not None else None,
                                 headers={'Content-Type': 'application/json'})
    return json.load(urllib.request.urlopen(req))


work = tempfile.mkdtemp(prefix='rwview-')
app_python = os.environ.get('RW_APP_PYTHON', 'python3')   # Python of the app's environment (Flask installed)
proc = subprocess.Popen([app_python, 'app.py'], cwd=APP_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                        env=dict(os.environ, RW_DATA_FILE=os.path.join(work, 'tracker_state.json'), RW_NO_BROWSER='1', PORT=str(PORT)))
try:
    for _ in range(60):
        try:
            api('/api/state')
            break
        except Exception:
            time.sleep(0.5)

    page_base = BASE
    if WWW:
        import http.server
        import threading
        import urllib.error

        class Proxy(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *a, **k):
                super().__init__(*a, directory=WWW, **k)

            def log_message(self, *a):
                pass

            def _forward(self):
                body = self.rfile.read(int(self.headers.get('Content-Length') or 0))
                req = urllib.request.Request(BASE + self.path, data=body or None, method=self.command,
                                             headers={'Content-Type': self.headers.get('Content-Type', 'application/json')})
                try:
                    r = urllib.request.urlopen(req)
                    code, data, ctype = r.status, r.read(), r.headers.get('Content-Type')
                except urllib.error.HTTPError as e:
                    code, data, ctype = e.code, e.read(), e.headers.get('Content-Type')
                self.send_response(code)
                self.send_header('Content-Type', ctype or 'application/json')
                self.end_headers()
                self.wfile.write(data)

            def do_GET(self):
                return self._forward() if self.path.startswith('/api/') else super().do_GET()

            do_POST = do_PUT = do_DELETE = _forward

        httpd = http.server.ThreadingHTTPServer(('127.0.0.1', PORT + 1), Proxy)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        page_base = f'http://127.0.0.1:{PORT + 1}'

    # two statements in two different months, so the selector has something to show
    for month, day in ((1, 7), (2, 3)):
        api('/api/pdf/import', {'sessions': [{'date': f'2026-0{month}-0{day}', 'start_time': '08:00', 'end_time': '16:30', 'is_remote': True}]})

    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(timezone_id='Pacific/Kiritimati')
        page = ctx.new_page()
        page.clock.set_fixed_time('2026-11-03T00:30:00+14:00')
        page.goto(page_base + '/')
        page.wait_for_function("document.getElementById('display-month').textContent.includes('|')")

        check(page.input_value('#input-date') == '2026-11-03', f"B8 Standarddatum lokal: {page.input_value('#input-date')}")

        page.select_option('#view-year-select', '2026')
        page.select_option('#view-month-select', 'Januar')
        page.wait_for_function("document.getElementById('display-month').textContent.startsWith('Januar 2026')")
        check(page.inner_text('#display-ist-remote').startswith('8.50'), f"B4 Januar zeigt seine Stunden: {page.inner_text('#display-ist-remote')}")
        page.select_option('#view-month-select', 'Februar')
        page.wait_for_function("document.getElementById('display-month').textContent.startsWith('Februar 2026')")
        check(page.inner_text('#display-ist-remote').startswith('8.50'), 'B4 Februar zeigt seine Stunden')
        page.select_option('#view-year-select', '2025')
        page.wait_for_function("document.getElementById('display-month').textContent.startsWith('Februar 2025')")
        check(page.inner_text('#display-ist-remote').startswith('0.00'), 'B4 Vorjahresmonat ohne Einträge zeigt 0')
        check(page.locator('#btn-current-month').is_visible(), 'Knopf "Aktueller Monat" erscheint')
        page.click('#btn-current-month')
        page.wait_for_function("document.getElementById('display-month').textContent.startsWith('November 2026')")
        check(page.input_value('#view-month-select') == 'November', 'Auswahl folgt dem aktuellen Monat')

        # B3: backup, change the quote, restore from the file through the button
        backup_path = os.path.join(work, 'backup.json')
        with open(backup_path, 'w', encoding='utf-8') as f:
            json.dump(api('/api/backup'), f)
        api('/api/quote', {'quote': 55})
        page.once('dialog', lambda d: d.accept())
        page.set_input_files('#restore-file', backup_path)
        time.sleep(1.0)
        check(api('/api/state')['individuelle_quote_prozent'] == 40, f"B3 Restore stellt die Quote wieder her: {api('/api/state')['individuelle_quote_prozent']}")
        check(page.locator('#restore-btn').is_visible(), 'B3 Restore-Knopf sichtbar')

        page.evaluate("document.body.classList.add('dark-mode')")
        bg = page.evaluate('getComputedStyle(document.body).backgroundColor')
        check(bg == 'rgb(31, 41, 55)', f'B7 Dunkelmodus Seitenhintergrund {bg}')
        browser.close()
finally:
    proc.terminate()

sys.exit(1 if FAILED else 0)

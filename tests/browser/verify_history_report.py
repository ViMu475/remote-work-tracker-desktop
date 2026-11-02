"""Manual browser check (not collected by pytest): history order, red over-quota rows and the
quarterly final report in light and dark mode. Seeds the history shown in the user's screenshot.

  python tests/browser/verify_history_report.py <app-dir> [screenshot-dir]

With a third argument the page is served from that folder (android-capacitor/www) through a small
proxy that forwards /api/* to the Flask app, so the Capacitor front end is checked the same way.
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
SHOTS = sys.argv[2] if len(sys.argv) > 2 else None
PORT = 5083
BASE = f'http://127.0.0.1:{PORT}'
FAILED = []
WWW = sys.argv[3] if len(sys.argv) > 3 else None
PAGE_BASE = BASE

# (month, quartal, remote, limit, soll) as in the screenshot, deliberately unsorted
ROWS = [('Juli', 'Q3/2026', 130.25, 110.40, 184.0), ('Mai', 'Q2/2026', 80.43, 86.40, 144.0),
        ('Juni', 'Q2/2026', 107.63, 100.80, 168.0), ('April', 'Q2/2026', 101.62, 96.00, 160.0),
        ('Oktober', 'Q4/2026', 90.47, 105.60, 176.0), ('September', 'Q3/2026', 109.98, 105.60, 176.0),
        ('August', 'Q3/2026', 94.60, 100.80, 168.0)]
EXPECTED_ORDER = ['Oktober', 'September', 'August', 'Juli', 'Juni', 'Mai', 'April']
EXPECTED_OVER = {'Juli', 'Juni', 'April', 'September'}


def check(ok, label):
    print(f"{'OK  ' if ok else 'FAIL'} {label}")
    if not ok:
        FAILED.append(label)


def api(path, payload=None):
    req = urllib.request.Request(BASE + path, method='POST' if payload is not None else 'GET',
                                 data=json.dumps(payload).encode() if payload is not None else None,
                                 headers={'Content-Type': 'application/json'})
    return json.load(urllib.request.urlopen(req))


work = tempfile.mkdtemp(prefix='rwhist-')
env = dict(os.environ, RW_DATA_FILE=os.path.join(work, 'tracker_state.json'), RW_NO_BROWSER='1', PORT=str(PORT))
APP_PYTHON = os.environ.get('RW_APP_PYTHON', 'python3')   # Python of the app's environment (Flask installed)
proc = subprocess.Popen([APP_PYTHON, 'app.py'], cwd=APP_DIR, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    for _ in range(60):
        try:
            api('/api/state')
            break
        except Exception:
            time.sleep(0.5)
    state = api('/api/state')
    state['monatliche_historie'] = [
        {'monat': m, 'jahr': 2026, 'quartal': q, 'individuelle_quote': 60.0, 'soll_stunden_gesamt': soll,
         'ist_remote_stunden_laufend': r, 'ist_arbeitszeit_laufend': soll, 'max_remote_stunden': mx,
         'tatsaechliche_remote_quote': r / soll * 100} for m, q, r, mx, soll in ROWS]
    api('/api/restore', state)

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
        PAGE_BASE = f'http://127.0.0.1:{PORT + 1}'

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={'width': 900, 'height': 1400})
        page.goto(PAGE_BASE + '/')
        page.wait_for_selector('#history-list li')
        names = [li.locator('p.font-bold').first.inner_text().split()[0] for li in page.locator('#history-list li').all()]
        check(names == EXPECTED_ORDER, f'Historie neueste zuerst: {names}')
        over = {li.locator('p.font-bold').first.inner_text().split()[0] for li in page.locator('#history-list li[data-over-quota="true"]').all()}
        check(over == EXPECTED_OVER, f'rot markiert: {sorted(over)}')
        red_rows = page.locator('#history-list li[data-over-quota="true"]').first
        check(red_rows.evaluate('e => getComputedStyle(e).backgroundColor') == 'rgb(254, 226, 226)', 'Hintergrund der Überschreitung ist rot (hell)')
        ok_row = page.locator('#history-list li:not([data-over-quota])').first
        check(ok_row.evaluate('e => getComputedStyle(e).backgroundColor') in ('rgba(0, 0, 0, 0)', 'rgb(255, 255, 255)'), 'Monat im Limit bleibt ohne Rotton')
        if SHOTS:
            page.locator('#history-list').screenshot(path=os.path.join(SHOTS, 'historie-hell.png'))

        page.click('#btn-final-report')
        page.wait_for_selector('#final-report-body section')
        quarters = [s.get_attribute('data-quartal') for s in page.locator('#final-report-body section').all()]
        ratings = [s.get_attribute('data-rating') for s in page.locator('#final-report-body section').all()]
        check(quarters == ['Q2/2026', 'Q3/2026', 'Q4/2026'], f'Quartale geordnet: {quarters}')
        check(ratings == ['exceeded', 'exceeded', 'good'], f'Bewertung: {ratings}')
        check(page.locator('#final-report-body [data-overall-rating="exceeded"]').count() == 1, 'Gesamtbewertung überschritten')
        check(page.locator('#final-report-body section').nth(0).locator('li.over-quota').count() == 2, 'Q2: zwei Monate rot')
        check('unvollständig' in page.locator('#final-report-body section').nth(2).inner_text(), 'Q4 als unvollständig gekennzeichnet')
        if SHOTS:
            page.locator('#final-report-modal > div').screenshot(path=os.path.join(SHOTS, 'bericht-hell.png'))
        page.click('#final-report-close')
        check(page.locator('#final-report-modal').is_hidden(), 'Bericht lässt sich schließen')

        page.evaluate("document.body.classList.add('dark-mode')")
        dark = page.locator('#history-list li[data-over-quota="true"]').first.evaluate('e => getComputedStyle(e).backgroundColor')
        check(dark == 'rgb(74, 29, 29)', f'Dunkelmodus: dunkles Rot ({dark})')
        if SHOTS:
            page.locator('#history-list').screenshot(path=os.path.join(SHOTS, 'historie-dunkel.png'))
        page.click('#btn-final-report')
        page.wait_for_selector('#final-report-body section')
        if SHOTS:
            page.locator('#final-report-modal > div').screenshot(path=os.path.join(SHOTS, 'bericht-dunkel.png'))
        browser.close()
finally:
    proc.terminate()

sys.exit(1 if FAILED else 0)

"""Manual browser check (not collected by pytest): import of several time statements at once.

Needs Playwright + Firefox and reportlab in the Python that runs this script, and Flask etc. in the Python
of the app (RW_APP_PYTHON). Uses fictional statements made on the fly and an own state file; screenshots
go to <shots-dir> (PNG files are ignored by git).

  RW_APP_PYTHON=venv/bin/python python tests/browser/verify_batch_import.py <app-dir> <shots-dir>
"""
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
from datetime import date

from playwright.sync_api import sync_playwright
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

APP_DIR, SHOTS = sys.argv[1], sys.argv[2]
PORT = 5087
BASE = f'http://127.0.0.1:{PORT}'
FAILED = []
WEEKDAYS = ['MO', 'TU', 'WE', 'TH', 'FR', 'SA', 'SU']
os.makedirs(SHOTS, exist_ok=True)


def check(ok, label):
    print(f"{'OK  ' if ok else 'FAIL'} {label}")
    if not ok:
        FAILED.append(label)


def api(path, payload=None):
    req = urllib.request.Request(BASE + path, method='POST' if payload is not None else 'GET',
                                 data=json.dumps(payload).encode() if payload is not None else None,
                                 headers={'Content-Type': 'application/json'})
    return json.load(urllib.request.urlopen(req))


def statement(path, year, month, last_day, days, extra=()):
    """Fictional SAP-like statement: the first `days` weekdays of the month, 08:00-16:30, alternating remote/office."""
    lines = [f"Time statement from 01.{month:02d}.{year} to {last_day:02d}.{month:02d}.{year}",
             f"Flex. Bal. Prev. Period {month}", "Flextime Bal. Curr. Period 2,00", f"Flextime Balance Total {month + 2},00"]
    picked = [d for d in range(1, last_day + 1) if date(year, month, d).weekday() < 5][:days]
    for i, d in enumerate(picked):
        kind = 'Remote Work' if i % 2 == 0 else 'At work'
        lines.append(f"{d:02d} {WEEKDAYS[date(year, month, d).weekday()]} Time Postings : {kind} 08:00 16:30 8,00")
    for d, start, end in extra:
        lines.append(f"{d:02d} {WEEKDAYS[date(year, month, d).weekday()]} Time Postings : At work {start} {end} 3,00")
    pdf = canvas.Canvas(path, pagesize=A4)
    y = 800
    for line in lines:
        pdf.drawString(40, y, line)
        y -= 16
    pdf.save()


work = tempfile.mkdtemp(prefix='rwbatch-')
files = {
    'Nachweis_2025-12.pdf': (2025, 12, 31, 6, ()),
    'Nachweis_2025-10.pdf': (2025, 10, 31, 5, ()),
    'Nachweis_2025-11.pdf': (2025, 11, 30, 5, ()),
    'Nachweis_2026-01_fehlerhaft.pdf': (2026, 1, 31, 4, [(5, '09:00', '12:00')]),     # overlaps 2026-01-05
}
paths = []
for name, (year, month, last, days, extra) in files.items():
    path = os.path.join(work, name)
    statement(path, year, month, last, days, extra)
    paths.append(path)

app_python = os.environ.get('RW_APP_PYTHON', 'python3')
proc = subprocess.Popen([app_python, 'app.py'], cwd=APP_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                        env=dict(os.environ, RW_DATA_FILE=os.path.join(work, 'tracker_state.json'), RW_NO_BROWSER='1',
                                 PORT=str(PORT)))
try:
    for _ in range(60):
        try:
            api('/api/state')
            break
        except Exception:
            time.sleep(0.5)

    with sync_playwright() as p:
        browser = p.firefox.launch()
        page = browser.new_page(viewport={'width': 1280, 'height': 1500})
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.goto(BASE)
        page.wait_for_selector('#display-verbleibend')

        page.click('button[onclick="openDialog(\'batch-import-modal\')"]')
        check(page.is_visible('#batch-import-modal'), 'dialog opens')
        check(page.get_attribute('#batch-file-input', 'multiple') is not None, 'file input accepts several files')

        page.set_input_files('#batch-file-input', paths)
        page.click('#batch-analyze-btn')
        page.wait_for_selector('#batch-reports .tile')
        cards = page.locator('#batch-reports .tile')
        check(cards.count() == 4, f'four reports shown ({cards.count()})')
        text = page.inner_text('#batch-reports')
        order = [text.index(m) for m in ('Oktober 2025', 'November 2025', 'Dezember 2025', 'Januar 2026')]
        check(order == sorted(order), 'reports are ordered by month')
        check('Buchungen überschneiden sich' in text, 'overlap error is explained in German')
        # 2025-10-03 is a public holiday: October only warns, so it is not selected until the user confirms it
        check('Bitte prüfen' in text and 'Wochenende oder Feiertag' in text, 'the holiday booking of October is a warning')
        check(page.locator('#batch-reports input[type=checkbox]:checked').count() == 2, 'only the 2 clean months are pre-selected')
        check(page.locator('#batch-reports input[type=checkbox]:disabled').count() == 1, 'the faulty month cannot be selected')
        check(page.locator('#batch-reports input[type=number]').count() == 3, 'a quota field for each month that goes into the history')
        check('Ausgewählte Monate importieren (2)' in page.inner_text('#batch-import-btn'), 'import button counts the months')
        page.check('#batch-sel-0')                             # the user confirms October
        check('Ausgewählte Monate importieren (3)' in page.inner_text('#batch-import-btn'), 'confirming a warning adds the month')
        page.screenshot(path=os.path.join(SHOTS, 'batch-01-pruefbericht.png'))

        page.fill('#batch-quote-1', '50')                      # November gets its own quota
        page.click('#batch-import-btn')
        page.wait_for_selector('#batch-reports .badge:has-text("Importiert")')
        results = page.inner_text('#batch-reports')
        check(results.count('Importiert') == 3, 'three months reported as imported')
        page.screenshot(path=os.path.join(SHOTS, 'batch-02-ergebnis.png'))

        state = api('/api/state')
        history = state['monatliche_historie']
        check([(m['jahr'], m['monat']) for m in history] == [(2025, 'Oktober'), (2025, 'November'), (2025, 'Dezember')],
              'history holds the three months, sorted')
        check([m['individuelle_quote'] for m in history] == [40.0, 50.0, 40.0], 'own quota of November, others default')
        check(state['individuelle_quote_prozent'] == 40.0, 'the global quota is unchanged')
        check(not any(d.startswith('2026-01') for d in state['daily_records']), 'the faulty month wrote nothing')
        check(all(m.get('quartal_remote') is not None for m in history), 'Q4/2025 is complete: quarter summary written')

        page.click('#batch-import-modal button[onclick="closeBatchModal()"]')
        check(not page.is_visible('#batch-import-modal'), 'dialog closes')

        page.click('#btn-flex-chart')
        page.wait_for_selector('#flex-chart-modal[open] [data-flex-point]')
        check(page.locator('#flex-chart-body [data-flex-point]').count() == 3, 'flextime chart: one point per imported month')
        check(page.locator('#flex-chart-body [data-flex-bar]').count() == 3, 'flextime chart: one bar per imported month')
        check('Aktuell: +14.00h' in page.inner_text('#flex-chart-body [data-flex-summary]'), 'flextime chart: latest balance shown (December)')
        page.screenshot(path=os.path.join(SHOTS, 'batch-04-gleitzeit.png'))
        page.click('#flex-chart-close')
        page.click('#btn-final-report')
        page.wait_for_selector('#final-report-modal[open]')
        check('Gleitzeit Quartalsende: +14.00h' in page.inner_text('#final-report-body'), 'final report: flextime of the quarter')
        page.click('#final-report-close')
        page.click('#lang-toggle')
        page.click('button[onclick="openDialog(\'batch-import-modal\')"]')
        page.set_input_files('#batch-file-input', [paths[3]])
        page.click('#batch-analyze-btn')
        page.wait_for_selector('#batch-reports .tile')
        english = page.inner_text('#batch-reports')
        check('bookings overlap' in english and 'January 2026' in english, 'texts switch to English')
        page.screenshot(path=os.path.join(SHOTS, 'batch-03-english.png'))
        check(not errors, f'no JavaScript errors {errors}')
        browser.close()
finally:
    proc.terminate()

print('\nFAILED:' if FAILED else '\nALL OK', FAILED or '')
sys.exit(1 if FAILED else 0)

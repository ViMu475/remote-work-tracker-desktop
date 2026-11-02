"""Manual browser check (not collected by pytest): the header shows the quarter
of the VIEWED month, not the quarter of the open month.

Needs a running app and Playwright:
  python tests/browser/verify_header_quartal.py [base_url]
"""
import json
import sys
import urllib.request

from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:5000'
FAILED = []


def api(path, payload=None):
    req = urllib.request.Request(BASE + path, method='POST' if payload is not None else 'GET',
                                 data=json.dumps(payload).encode() if payload is not None else None,
                                 headers={'Content-Type': 'application/json'})
    return json.load(urllib.request.urlopen(req))


def check(page, label, expected):
    text = page.locator('#display-month').inner_text()
    ok = expected in text
    print(f"{'OK  ' if ok else 'FAIL'} {label}: {text.split(' | Monat')[0]}")
    if not ok:
        FAILED.append(label)


state = api('/api/state')
print('Offener Monat:', state['aktueller_monat'], state['aktuelles_jahr'], '| Ansicht:', state['view_month'], state['view_year'])

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto(BASE + '/')
    page.wait_for_selector('#display-month')
    page.wait_for_function("document.getElementById('display-month').textContent.includes('|')")
    quartal_of = lambda m, y: f"Quartal: Q{(['Januar','Februar','März','April','Mai','Juni','Juli','August','September','Oktober','November','Dezember'].index(m)//3)+1}/{y}"
    check(page, 'aktuelle Ansicht', quartal_of(state['view_month'], state['view_year']))
    browser.close()

sys.exit(1 if FAILED else 0)

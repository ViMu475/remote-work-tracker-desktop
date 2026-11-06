"""End to end: real PDF files (made here with reportlab, fictional data) through the real parser and routes."""
import io

import pytest
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from .test_statement_import import workdays

WEEKDAYS = ['MO', 'TU', 'WE', 'TH', 'FR', 'SA', 'SU']


def statement_pdf(header, bookings):
    """A SAP-like time statement as PDF bytes. bookings: list of (iso date, start, end, 'At work'|'Remote Work')."""
    from datetime import date
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    lines = list(header)
    for iso, start, end, kind in bookings:
        d = date.fromisoformat(iso)
        lines.append(f"{d.day:02d} {WEEKDAYS[d.weekday()]} Time Postings : {kind} {start} {end} 8,00")
    y = 800
    for line in lines:
        pdf.drawString(40, y, line)
        y -= 16
        if y < 40:
            pdf.showPage()
            y = 800
    pdf.save()
    return buffer.getvalue()


def month_pdf(year, month, days=5, last_day=28, header=True, extra=()):
    head = [f"Time statement from 01.{month:02d}.{year} to {last_day:02d}.{month:02d}.{year}"] if header else ['Time statement']
    bookings = [(d, '08:00', '16:30', 'Remote Work' if i % 2 == 0 else 'At work')
                for i, d in enumerate(workdays(year, month, days))]
    return statement_pdf(head, bookings + list(extra))


def analyze(client, files):
    data = {'files': [(io.BytesIO(content), name) for name, content in files]}
    return client.post('/api/pdf/batch/analyze', data=data, content_type='multipart/form-data').get_json()


def months_from(reports, **extra):
    return [dict({'year': r['year'], 'month': r['month'], 'filename': r['filename'], 'sessions': r['sessions'],
                  'flex_balance': r['flex_balance']}, **extra) for r in reports if r['status'] != 'error']


def test_three_statements_in_any_order_end_up_sorted_in_the_history(client):
    files = [('Nachweis_Dezember.pdf', month_pdf(2025, 12, last_day=31)),
             ('Nachweis_Oktober.pdf', month_pdf(2025, 10, last_day=31)),
             ('Nachweis_November.pdf', month_pdf(2025, 11, last_day=30))]
    reports = analyze(client, files)['reports']
    assert [(r['key'], r['status']) for r in reports] == [('2025-10', 'ok'), ('2025-11', 'ok'), ('2025-12', 'ok')]
    assert all(r['summary']['days'] == 5 and r['summary']['net_hours'] == 40.0 for r in reports)
    assert reports[0]['summary']['remote_hours'] == 24.0          # days 1, 3, 5 are "Remote Work"

    body = client.post('/api/pdf/batch/import', json={'months': months_from(reports)}).get_json()
    assert body['imported_count'] == 3
    history = body['state']['monatliche_historie']
    assert [(m['jahr'], m['monat']) for m in history] == [(2025, 'Oktober'), (2025, 'November'), (2025, 'Dezember')]
    assert all(m['quartal'] == 'Q4/2025' and m['ist_arbeitszeit_laufend'] == 40.0 for m in history)
    assert all(m['quartal_remote'] == 72.0 for m in history)
    assert body['state']['individuelle_quote_prozent'] == 40.0


def test_a_statement_with_an_error_is_held_back_completely(client):
    bad = month_pdf(2025, 11, last_day=30, extra=[(workdays(2025, 11, 1)[0], '09:00', '12:00', 'At work')])   # overlaps day 1
    files = [('ok.pdf', month_pdf(2025, 10, last_day=31)), ('bad.pdf', bad)]
    reports = {r['filename']: r for r in analyze(client, files)['reports']}
    assert reports['ok.pdf']['status'] == 'ok'
    assert reports['bad.pdf']['status'] == 'error' and reports['bad.pdf']['errors'][0]['code'] == 'overlap'

    body = client.post('/api/pdf/batch/import', json={'months': months_from(reports.values()) + [
        {'year': 2025, 'month': 11, 'filename': 'bad.pdf', 'sessions': reports['bad.pdf']['sessions'], 'confirmed': True}]}).get_json()
    assert {r['key']: r['status'] for r in body['results']} == {'2025-10': 'imported', '2025-11': 'rejected'}
    assert [m['monat'] for m in body['state']['monatliche_historie']] == ['Oktober']
    assert not any(d.startswith('2025-11') for d in body['state']['daily_records'])


def test_a_statement_without_a_month_is_not_guessed(client):
    report = analyze(client, [('scan.pdf', month_pdf(2025, 11, header=False))])['reports'][0]
    assert report['status'] == 'error' and report['errors'][0]['code'] == 'period_unknown'


def test_the_month_from_the_file_name_asks_for_a_check(client):
    pdf = month_pdf(2025, 11, header=False)
    report = analyze(client, [('TimeStatement_20251101_20251130.pdf', pdf)])['reports'][0]
    assert report['key'] == '2025-11' and report['status'] == 'warning'
    assert report['warnings'][0]['code'] == 'period_from_filename'


def test_a_pdf_without_bookings_and_a_file_that_is_no_pdf(client):
    empty = statement_pdf(['Time statement from 01.11.2025 to 30.11.2025', 'nothing was booked'], [])
    reports = {r['filename']: r for r in analyze(client, [('empty.pdf', empty), ('broken.pdf', b'%PDF-1.4 garbage')])['reports']}
    assert reports['empty.pdf']['status'] == 'error' and reports['broken.pdf']['status'] == 'error'
    assert reports['empty.pdf']['errors'][0]['code'] == 'parse_failed'


def test_statement_over_two_months_is_rejected(client):
    pdf = statement_pdf(['Time statement from 15.11.2025 to 14.12.2025'],
                        [(workdays(2025, 11, 1)[0], '08:00', '16:30', 'At work')])
    report = analyze(client, [('x.pdf', pdf)])['reports'][0]
    assert 'period_multi_month' in [e['code'] for e in report['errors']]


def test_importing_the_same_statements_twice_changes_nothing(client):
    reports = analyze(client, [('a.pdf', month_pdf(2025, 11, last_day=30))])['reports']
    first = client.post('/api/pdf/batch/import', json={'months': months_from(reports)}).get_json()['state']
    reports = analyze(client, [('a.pdf', month_pdf(2025, 11, last_day=30))])['reports']
    assert reports[0]['warnings'][0]['code'] == 'replaces_history'
    second = client.post('/api/pdf/batch/import', json={'months': months_from(reports, confirmed=True)}).get_json()['state']
    assert first['monatliche_historie'] == second['monatliche_historie']
    assert first['daily_records'] == second['daily_records']


@pytest.mark.parametrize('count', [1, 12])
def test_many_statements_at_once(client, count):
    files = [(f'm{i}.pdf', month_pdf(2024 + (i // 12), i % 12 + 1, days=3, last_day=28)) for i in range(count)]
    body = analyze(client, files)
    assert body['success'] and len(body['reports']) == count and all(r['status'] == 'ok' for r in body['reports'])
    imported = client.post('/api/pdf/batch/import', json={'months': months_from(body['reports'])}).get_json()
    assert imported['imported_count'] == count
    keys = [(m['jahr'], list(m_ for m_ in __import__('config').Config.MONATS_NUMMERN).index(m['monat'])) for m in imported['state']['monatliche_historie']]
    assert keys == sorted(keys)

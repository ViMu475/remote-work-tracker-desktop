"""/api/pdf/batch/analyze and /api/pdf/batch/import (fictional data; the parser is replaced by a fake)."""
import copy
import glob
import io
import os
import tempfile
import threading
from types import SimpleNamespace

import pytest

import routes.api as api_module

from .test_statement_import import analysis, month_sessions, session, workdays


@pytest.fixture
def parser(monkeypatch):
    """Fake parser: file name -> analysis. Records how it was called."""
    table, calls = {}, []

    def fake(path, allow_ai=True):
        name = os.path.basename(path)
        calls.append((name, allow_ai))
        if isinstance(table.get(name), Exception):
            raise table[name]
        if name not in table:
            return {'success': False, 'message': 'unknown file', 'sessions': []}
        return copy.deepcopy(table[name])

    monkeypatch.setattr(api_module.pdf_service, 'analyze_pdf', fake)
    return SimpleNamespace(table=table, calls=calls)


def upload(client, names):
    data = {'files': [(io.BytesIO(b'%PDF-1.4 fake'), n) for n in names]}
    return client.post('/api/pdf/batch/analyze', data=data, content_type='multipart/form-data')


def scratch_dirs():
    return set(glob.glob(os.path.join(tempfile.gettempdir(), 'rw_batch_*')))


def state_file_bytes():
    with open(api_module.state_service.data_file, 'rb') as f:
        return f.read()


def months_from(reports, **extra):
    return [dict({'year': r['year'], 'month': r['month'], 'filename': r['filename'], 'sessions': r['sessions'],
                  'flex_balance': r['flex_balance']}, **extra) for r in reports]


class TestAnalyze:
    def test_reports_come_back_sorted_by_month_with_their_status(self, client, parser):
        parser.table.update({'dez.pdf': analysis(2025, 12), 'okt.pdf': analysis(2025, 10), 'nov.pdf': analysis(2025, 11)})
        body = upload(client, ['dez.pdf', 'okt.pdf', 'nov.pdf']).get_json()
        assert body['success'] is True
        assert [r['key'] for r in body['reports']] == ['2025-10', '2025-11', '2025-12']
        assert all(r['status'] == 'ok' and r['target'] == 'history' for r in body['reports'])
        assert body['reports'][0]['summary']['net_hours'] == 40.0

    def test_a_statement_never_leaves_this_computer(self, client, parser):
        parser.table['a.pdf'] = analysis(2025, 11)
        upload(client, ['a.pdf'])
        assert parser.calls == [('a.pdf', False)]            # allow_ai=False: no Gemini fallback

    def test_nothing_is_saved_and_no_scratch_files_stay(self, client, parser):
        parser.table['a.pdf'] = analysis(2025, 11)
        before, dirs = state_file_bytes(), scratch_dirs()
        assert upload(client, ['a.pdf']).status_code == 200
        assert state_file_bytes() == before and scratch_dirs() <= dirs

    def test_file_name_keeps_its_period_for_the_parser_fallback(self, client, parser):
        parser.table['TimeStatement_20251101_20251130.pdf'] = analysis(2025, 11)
        upload(client, ['TimeStatement_20251101_20251130.pdf'])
        assert parser.calls[0][0] == 'TimeStatement_20251101_20251130.pdf'

    def test_the_same_file_name_twice_is_fine_and_reported_as_duplicate_month(self, client, parser):
        parser.table['a.pdf'] = analysis(2025, 11)
        reports = upload(client, ['a.pdf', 'a.pdf']).get_json()['reports']
        assert [r['status'] for r in reports] == ['error', 'error']
        assert reports[0]['errors'][0]['code'] == 'duplicate_month'

    def test_two_files_for_one_month_are_both_rejected(self, client, parser):
        parser.table.update({'a.pdf': analysis(2025, 11), 'b.pdf': analysis(2025, 11), 'c.pdf': analysis(2025, 12)})
        reports = upload(client, ['a.pdf', 'b.pdf', 'c.pdf']).get_json()['reports']
        assert {r['filename']: r['status'] for r in reports} == {'a.pdf': 'error', 'b.pdf': 'error', 'c.pdf': 'ok'}

    def test_no_files(self, client):
        assert client.post('/api/pdf/batch/analyze').status_code == 400
        assert client.post('/api/pdf/batch/analyze', data={'files': (io.BytesIO(b'x'), '')},
                           content_type='multipart/form-data').status_code == 400
        assert client.post('/api/pdf/batch/analyze', json={'files': []}).status_code == 400

    def test_too_many_files(self, client, parser):
        names = [f'{i}.pdf' for i in range(api_module.MAX_BATCH_FILES + 1)]
        assert upload(client, names).status_code == 400
        assert parser.calls == []

    def test_a_file_that_is_not_a_pdf_does_not_stop_the_others(self, client, parser):
        parser.table['a.pdf'] = analysis(2025, 11)
        reports = upload(client, ['notes.txt', 'a.pdf', 'evil.pdf.exe']).get_json()['reports']
        by_name = {r['filename']: r for r in reports}
        assert by_name['notes.txt']['errors'][0]['code'] == 'not_pdf'
        assert by_name['evil.pdf.exe']['errors'][0]['code'] == 'not_pdf'
        assert by_name['a.pdf']['status'] == 'ok'
        assert [c[0] for c in parser.calls] == ['a.pdf']

    def test_a_file_that_is_too_large(self, client, parser, monkeypatch):
        monkeypatch.setattr(api_module, 'MAX_STATEMENT_BYTES', 5)
        parser.table['a.pdf'] = analysis(2025, 11)
        report = upload(client, ['a.pdf']).get_json()['reports'][0]
        assert report['errors'][0]['code'] == 'file_too_large' and parser.calls == []

    def test_a_parser_crash_is_reported_for_that_file_only(self, client, parser):
        parser.table.update({'bad.pdf': RuntimeError('boom'), 'good.pdf': analysis(2025, 11)})
        by_name = {r['filename']: r for r in upload(client, ['bad.pdf', 'good.pdf']).get_json()['reports']}
        assert by_name['bad.pdf']['errors'][0] == {'code': 'parse_failed', 'detail': 'boom'}
        assert by_name['good.pdf']['status'] == 'ok'

    def test_an_unreadable_statement(self, client, parser):
        report = upload(client, ['never-seen.pdf']).get_json()['reports'][0]
        assert report['status'] == 'error' and report['errors'][0]['code'] == 'parse_failed'

    def test_warnings_and_state_information_are_in_the_report(self, client, parser):
        long_day = [session(workdays(2025, 11, 1)[0], '07:00', '19:00')]
        parser.table.update({'a.pdf': analysis(2025, 11, long_day), 'm.pdf': analysis(2026, 3, month_sessions(2026, 3, 1))})
        by_name = {r['filename']: r for r in upload(client, ['a.pdf', 'm.pdf']).get_json()['reports']}
        assert by_name['a.pdf']['status'] == 'warning' and by_name['a.pdf']['warnings'][0]['code'] == 'long_day'
        assert by_name['m.pdf']['status'] == 'error'            # 2026-03-02 clashes with an entry of the sample state
        assert by_name['m.pdf']['target'] == 'daily'

    def test_analysis_does_not_wait_for_the_state_lock(self, client, parser):
        parser.table['a.pdf'] = analysis(2025, 11)
        release, held, result = threading.Event(), threading.Event(), {}

        def hold():
            with api_module._state_lock:
                held.set()
                release.wait(10)

        def request():
            result['response'] = upload(client, ['a.pdf'])

        holder = threading.Thread(target=hold)
        holder.start()
        assert held.wait(5)
        worker = threading.Thread(target=request)
        worker.start()
        worker.join(5)
        finished = not worker.is_alive()
        release.set()
        holder.join()
        worker.join(5)
        assert finished and result['response'].status_code == 200


class TestImport:
    def test_end_to_end_months_land_sorted_in_the_history_and_are_saved(self, client, parser):
        parser.table.update({'dez.pdf': analysis(2025, 12), 'okt.pdf': analysis(2025, 10), 'nov.pdf': analysis(2025, 11)})
        reports = upload(client, ['dez.pdf', 'okt.pdf', 'nov.pdf']).get_json()['reports']
        body = client.post('/api/pdf/batch/import', json={'months': list(reversed(months_from(reports)))}).get_json()
        assert body['success'] and body['imported_count'] == 3 and body['rejected_count'] == 0
        assert body['message'] == '3 Monate importiert'

        saved = client.get('/api/state').get_json()
        assert [(m['jahr'], m['monat']) for m in saved['monatliche_historie']] == [
            (2025, 'Oktober'), (2025, 'November'), (2025, 'Dezember')]
        assert saved['individuelle_quote_prozent'] == 40.0                  # the quota is never changed by an import
        assert saved['aktueller_monat'] == 'März'
        assert all(m['quartal_remote'] == 120.0 for m in saved['monatliche_historie'])   # Q4/2025 is complete
        assert len([d for d in saved['daily_records'] if d.startswith('2025-1')]) == 15

    def test_the_final_report_uses_the_imported_months(self, client, parser):
        parser.table.update({'okt.pdf': analysis(2025, 10), 'nov.pdf': analysis(2025, 11), 'dez.pdf': analysis(2025, 12)})
        reports = upload(client, ['okt.pdf', 'nov.pdf', 'dez.pdf']).get_json()['reports']
        client.post('/api/pdf/batch/import', json={'months': months_from(reports)})
        report = client.get('/api/report/final').get_json()['report']
        assert report['overall']['months'] == 3 and report['quarters'][0]['quartal'] == 'Q4/2025'
        assert report['quarters'][0]['complete'] is True

    def test_rejected_months_are_reported_and_nothing_is_written_for_them(self, client, parser):
        parser.table.update({'nov.pdf': analysis(2025, 11), 'dez.pdf': analysis(2025, 12)})
        reports = upload(client, ['nov.pdf', 'dez.pdf']).get_json()['reports']
        months = months_from(reports)
        months[0]['sessions'] = months[0]['sessions'] + [session(workdays(2025, 11, 9)[8], '16:00', '08:00')]
        body = client.post('/api/pdf/batch/import', json={'months': months}).get_json()
        assert body['imported_count'] == 1 and body['rejected_count'] == 1
        assert body['message'] == '1 Monate importiert, 1 abgelehnt'
        assert {r['key']: r['status'] for r in body['results']} == {'2025-11': 'rejected', '2025-12': 'imported'}
        assert [m['monat'] for m in body['state']['monatliche_historie']] == ['Dezember']
        assert not any(d.startswith('2025-11') for d in body['state']['daily_records'])

    def test_warnings_need_the_confirmation_of_the_user(self, client, parser):
        long_day = [session(workdays(2025, 11, 1)[0], '07:00', '19:00')]
        parser.table['nov.pdf'] = analysis(2025, 11, long_day)
        months = months_from(upload(client, ['nov.pdf']).get_json()['reports'])
        before = state_file_bytes()
        refused = client.post('/api/pdf/batch/import', json={'months': months}).get_json()
        assert refused['imported_count'] == 0 and refused['results'][0]['codes'][0] == 'needs_confirmation'
        assert state_file_bytes() == before                                  # nothing imported: nothing saved
        accepted = client.post('/api/pdf/batch/import', json={'months': months_from(
            upload(client, ['nov.pdf']).get_json()['reports'], confirmed=True)}).get_json()
        assert accepted['imported_count'] == 1

    def test_own_quota_per_month(self, client, parser):
        parser.table['nov.pdf'] = analysis(2025, 11)
        months = months_from(upload(client, ['nov.pdf']).get_json()['reports'], quote=50)
        body = client.post('/api/pdf/batch/import', json={'months': months}).get_json()
        assert body['state']['monatliche_historie'][0]['individuelle_quote'] == 50
        assert body['state']['individuelle_quote_prozent'] == 40.0

    def test_importing_twice_gives_the_same_result(self, client, parser):
        parser.table['nov.pdf'] = analysis(2025, 11)
        months = months_from(upload(client, ['nov.pdf']).get_json()['reports'], confirmed=True)
        first = client.post('/api/pdf/batch/import', json={'months': months}).get_json()['state']
        second = client.post('/api/pdf/batch/import', json={'months': months}).get_json()['state']
        assert first['monatliche_historie'] == second['monatliche_historie']
        assert first['daily_records'] == second['daily_records']

    def test_english_message(self, client, parser):
        client.post('/api/language', json={'language': 'en'})
        parser.table['nov.pdf'] = analysis(2025, 11)
        months = months_from(upload(client, ['nov.pdf']).get_json()['reports'])
        assert client.post('/api/pdf/batch/import', json={'months': months}).get_json()['message'] == '1 months imported'

    @pytest.mark.parametrize('payload', [{}, {'months': []}, {'months': 'x'}, {'months': {}}, {'months': None}, []])
    def test_nothing_to_import(self, client, payload):
        assert client.post('/api/pdf/batch/import', json=payload).status_code == 400

    def test_too_many_months(self, client):
        assert client.post('/api/pdf/batch/import',
                           json={'months': [{}] * (api_module.MAX_BATCH_MONTHS + 1)}).status_code == 400

    def test_broken_json(self, client):
        assert client.post('/api/pdf/batch/import', data='{not json', content_type='application/json').status_code == 400

    def test_garbage_months_are_rejected_and_nothing_is_saved(self, client):
        before = state_file_bytes()
        body = client.post('/api/pdf/batch/import', json={'months': [None, 5, {}, {'year': 'x'}]}).get_json()
        assert body['imported_count'] == 0 and body['rejected_count'] == 2
        assert state_file_bytes() == before

    def test_a_failed_save_is_reported_as_an_error(self, client, parser, monkeypatch):
        parser.table['nov.pdf'] = analysis(2025, 11)
        months = months_from(upload(client, ['nov.pdf']).get_json()['reports'])
        before = state_file_bytes()
        monkeypatch.setattr(api_module.state_service, 'save_state', lambda state: False)
        response = client.post('/api/pdf/batch/import', json={'months': months})
        assert response.status_code == 500 and response.get_json()['success'] is False
        assert state_file_bytes() == before

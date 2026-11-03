"""The numbers the app shows must always match the entries of the viewed month.

Bug report: when several time statements (PDFs) for different months are loaded
and the view is switched, the values (actual remote hours, target hours, maximum
remote hours, bar) were not always updated. Cause: several endpoints returned a
state whose monthly totals had not been recalculated for the current view.

Oracle used here, independent of the code under test:
  * actual hours  = sum of the entries that fall into the viewed month
  * target hours  = working days of that month without Bavarian holidays x hours/day
  * max remote    = target hours x quota
  * every response must equal what GET /api/state reports right afterwards
"""
import calendar
import datetime
import os
import sys

import pytest
from freezegun import freeze_time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import Config
from tests.test_holidays import expected_holidays

MONTHS = list(Config.MONATS_NUMMERN)
TODAY = '2026-11-01 12:00:00'


# ── oracle ────────────────────────────────────────────────────────────

def view_records(state):
    month = MONTHS.index(state['view_month']) + 1
    year = state['view_year']
    out = []
    for value in state['daily_records'].values():
        for rec in (value if isinstance(value, list) else [value]):
            if rec['datum'].startswith(f'{year}-{month:02d}-'):
                out.append(rec)
    return out


def truth(state):
    month = MONTHS.index(state['view_month']) + 1
    year = state['view_year']
    holidays = expected_holidays(year)
    special = {(12, 24): 0.0, (12, 31): 0.5}   # company rule: 24 Dec off, 31 Dec half day
    workdays = sum(special.get((month, d), 1.0) for d in range(1, calendar.monthrange(year, month)[1] + 1)
                   if datetime.date(year, month, d).weekday() < 5
                   and datetime.date(year, month, d) not in holidays)
    target = workdays * state['soll_stunden_pro_tag']
    recs = view_records(state)
    return {
        'ist_remote_stunden_laufend': round(sum(r['remoteStundenHeute'] for r in recs), 2),
        'ist_arbeitszeit_laufend': round(sum(r['totalStundenHeute'] for r in recs), 2),
        'soll_stunden_gesamt': target,
        'max_remote_stunden': round(target * state['individuelle_quote_prozent'] / 100, 2),
    }


def assert_consistent(state, label=''):
    shown = state['current_month_data']
    for key, want in truth(state).items():
        assert shown[key] == pytest.approx(want, abs=0.011), (
            f"{label}: {key} shows {shown[key]}, correct for {state['view_month']} "
            f"{state['view_year']} is {want}")


def assert_same_as_get(client, state, label=''):
    fresh = client.get('/api/state').get_json()
    for key in ('current_month_data', 'quartal_data', 'view_month', 'view_year'):
        assert state[key] == fresh[key], f'{label}: response and GET /api/state differ in {key}'


# ── synthetic statements (no personal data) ───────────────────────────

def month_sessions(year, month, remote_every=2):
    holidays = expected_holidays(year)
    out = []
    for day in range(1, calendar.monthrange(year, month)[1] + 1):
        d = datetime.date(year, month, day)
        if d.weekday() < 5 and d not in holidays:
            out.append({'date': d.isoformat(), 'start_time': '08:00', 'end_time': '16:30',
                        'is_remote': day % remote_every == 0})
    return out


STATEMENTS = {
    'Apr 2026': month_sessions(2026, 4),
    'Aug 2026': month_sessions(2026, 8, remote_every=3),
    'Sep 2026': month_sessions(2026, 9),
    'Okt 2026': month_sessions(2026, 10, remote_every=2),
    'Dez 2025': month_sessions(2025, 12),
}


@pytest.fixture
def nov(client):
    """The app as it is on 2026-11-01 (current month: November 2026)."""
    with freeze_time(TODAY):
        yield client


def load(client, key):
    resp = client.post('/api/pdf/import', json={'sessions': STATEMENTS[key]})
    assert resp.status_code == 200
    return resp.get_json()


# ── the reported scenario ─────────────────────────────────────────────

class TestLoadingSeveralStatements:
    def test_each_import_shows_correct_values(self, nov):
        for key in ('Apr 2026', 'Aug 2026', 'Sep 2026', 'Okt 2026'):
            data = load(nov, key)
            assert data['imported_count'] == len(STATEMENTS[key])
            assert_consistent(data['state'], f'import {key}')
            assert_same_as_get(nov, data['state'], f'import {key}')

    def test_back_to_current_month_after_importing_other_months(self, nov):
        for key in ('Apr 2026', 'Aug 2026', 'Sep 2026', 'Okt 2026'):
            load(nov, key)
        resp = nov.post('/api/view/current_month').get_json()
        state = resp['state']
        assert (state['view_month'], state['view_year']) == ('November', 2026)
        assert_consistent(state, 'Aktueller Monat')
        assert state['current_month_data']['ist_remote_stunden_laufend'] == 0
        assert_same_as_get(nov, state, 'Aktueller Monat')

    @pytest.mark.parametrize('order', [
        ['Apr 2026', 'Aug 2026', 'Sep 2026', 'Okt 2026'],
        ['Okt 2026', 'Sep 2026', 'Aug 2026', 'Apr 2026'],
        ['Aug 2026', 'Dez 2025', 'Okt 2026', 'Apr 2026', 'Sep 2026'],
    ])
    def test_any_order_with_view_resets_in_between(self, nov, order):
        for key in order:
            data = load(nov, key)
            assert_consistent(data['state'], f'import {key}')
            back = nov.post('/api/view/current_month').get_json()['state']
            assert_consistent(back, f'Aktueller Monat nach {key}')
            assert_same_as_get(nov, back, f'Aktueller Monat nach {key}')
            again = nov.get('/api/state').get_json()
            assert_consistent(again, f'GET nach {key}')

    def test_reimporting_an_already_loaded_statement_keeps_values_correct(self, nov):
        load(nov, 'Okt 2026')
        second = load(nov, 'Okt 2026')
        assert second['imported_count'] == 0
        assert_consistent(second['state'], 'zweiter Import')

    def test_adding_a_manual_entry_after_imports_updates_the_view(self, nov):
        load(nov, 'Sep 2026')
        before = nov.get('/api/state').get_json()['current_month_data']['ist_remote_stunden_laufend']
        resp = nov.post('/api/protokoll', json={'datum': '2026-09-30', 'start': '17:00', 'end': '19:00', 'pause': 0})
        assert resp.status_code == 200, resp.get_json()
        state = resp.get_json()['state']
        assert_consistent(state, 'manueller Eintrag')
        assert state['current_month_data']['ist_remote_stunden_laufend'] == pytest.approx(before + 2.0)


# ── the statement that was loaded must be the one shown ───────────────

class TestImportShowsTheLoadedMonth:
    def test_duplicate_only_import_still_switches_to_that_month(self, nov):
        load(nov, 'Okt 2026')
        nov.post('/api/view/current_month')
        again = load(nov, 'Okt 2026')          # every session is a duplicate now
        assert again['imported_count'] == 0
        assert (again['state']['view_month'], again['state']['view_year']) == ('Oktober', 2026)
        assert_consistent(again['state'], 'Duplikat-Import')

    def test_partially_new_statement_switches_to_its_month(self, nov):
        first_half = STATEMENTS['Apr 2026'][:10]
        nov.post('/api/pdf/import', json={'sessions': first_half})
        nov.post('/api/view/current_month')
        resp = load(nov, 'Apr 2026')            # 10 duplicates, rest new
        assert resp['imported_count'] == len(STATEMENTS['Apr 2026']) - 10
        assert resp['state']['view_month'] == 'April'
        assert_consistent(resp['state'], 'teilweise neu')

    def test_import_without_usable_sessions_leaves_the_view_alone(self, nov):
        nov.post('/api/view/current_month')
        resp = nov.post('/api/pdf/import', json={'sessions': [{'date': '', 'start_time': '', 'end_time': ''}]}).get_json()
        assert resp['imported_count'] == 0
        assert resp['state']['view_month'] == 'November'


# ── every endpoint that returns a state ───────────────────────────────

class TestEveryEndpointReturnsConsistentValues:
    @pytest.fixture
    def viewing_october(self, nov):
        load(nov, 'Aug 2026')
        load(nov, 'Okt 2026')
        return nov

    @pytest.mark.parametrize('call', [
        lambda c: c.post('/api/darkmode', json={'darkMode': True}),
        lambda c: c.post('/api/language', json={'language': 'en'}),
        lambda c: c.post('/api/view/current_month'),
        lambda c: c.post('/api/quote', json={'quote': 50}),
        lambda c: c.post('/api/sollstunden', json={'sollStunden': 7.5}),
        lambda c: c.post('/api/protokoll', json={'datum': '2026-10-30', 'start': '17:00', 'end': '19:00', 'pause': 0}),
    ], ids=['darkmode', 'language', 'view-current-month', 'quote', 'sollstunden', 'protokoll'])
    def test_response_matches_the_viewed_month(self, viewing_october, call):
        resp = call(viewing_october)
        assert resp.status_code == 200, resp.get_json()
        state = resp.get_json()['state']
        assert_consistent(state, 'response')
        assert_same_as_get(viewing_october, state, 'response')

    def test_restore_returns_consistent_values(self, viewing_october):
        backup = viewing_october.get('/api/state').get_json()
        viewing_october.post('/api/view/current_month')
        # a backup written with stale totals must not poison the view
        backup['current_month_data']['ist_remote_stunden_laufend'] = 999.0
        backup['current_month_data']['soll_stunden_gesamt'] = 1.0
        resp = viewing_october.post('/api/restore', json=backup)
        assert resp.status_code == 200
        state = resp.get_json()['state']
        assert_consistent(state, 'restore')
        assert_same_as_get(viewing_october, state, 'restore')

    def test_month_switch_returns_consistent_values(self, client):
        # Realistic order: November is worked, then closed on the first day of December
        # (the app always resets the current month to the real system month on load).
        with freeze_time('2026-11-30 12:00:00'):
            client.post('/api/view/current_month')
            assert client.post('/api/protokoll', json={'datum': '2026-11-30', 'start': '08:00',
                                                       'end': '16:30', 'pause': 30}).status_code == 200
        with freeze_time('2026-12-01 09:00:00'):
            resp = client.post('/api/month/switch')
            assert resp.status_code == 200
            state = resp.get_json()['state']
            assert (state['view_month'], state['view_year']) == ('Dezember', 2026)
            assert_consistent(state, 'Monatswechsel')
            assert_same_as_get(client, state, 'Monatswechsel')

    def test_stale_totals_on_disk_never_reach_the_client(self, nov):
        """Even if the stored file carries wrong totals, every response is corrected."""
        import json
        import routes.api as api_module
        load(nov, 'Sep 2026')
        path = api_module.state_service.data_file
        with open(path, encoding='utf-8') as f:
            stored = json.load(f)
        stored['current_month_data'].update(ist_remote_stunden_laufend=12345.0, soll_stunden_gesamt=7.0)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(stored, f)
        state = nov.post('/api/darkmode', json={'darkMode': False}).get_json()['state']
        assert_consistent(state, 'beschädigte Summen')


# ── front end: a failed analysis must not leave the old statement ─────

class TestFrontendUploadState:
    @staticmethod
    def _function(name):
        js = open(os.path.join(os.path.dirname(__file__), '..', 'static', 'js', 'app.js'), encoding='utf-8').read()
        start = js.index(f'async function {name}')
        return js[start:js.index('\n}\n', start)]

    def test_new_analysis_starts_with_a_clean_slate(self):
        body = self._function('handlePdfUpload')
        assert 'extractedPdfSessions = []' in body
        assert "pdf-import-btn').style.display = 'none'" in body

    def test_failed_analysis_cannot_import_the_previous_statement(self):
        body = self._function('handlePdfUpload')
        # the reset must happen before the request is sent, so every failure path is covered
        assert 'extractedPdfSessions = []' in body
        assert body.index('extractedPdfSessions = []') < body.index("fetch('/api/pdf/analyze'")
